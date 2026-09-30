from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from broker_mt5.instruments import InstrumentProvider, InstrumentError, InstrumentSnapshot
from broker_mt5.symbols import SymbolRegistry
from core.time_service import FakeClock
from tests.instrument_fixtures import native_symbol, native_account


@pytest.fixture
def provider():
    clock = FakeClock(datetime(2026, 9, 30, tzinfo=timezone.utc))
    return InstrumentProvider(symbol_registry=SymbolRegistry(), clock=clock,
                              account_reader=Mock(return_value=native_account()),
                              symbol_reader=Mock(side_effect=native_symbol))


def test_non_usd_asymmetric_values_and_valid_zeros(provider):
    spec = provider.get("XAUUSD")
    assert spec.instrument_id == "XAUUSD" and spec.broker_symbol == "GOLD.i#"
    assert spec.account_currency == "EUR"
    assert spec.trade_tick_value_profit == Decimal("0.8")
    assert spec.trade_tick_value_loss == Decimal("0.9")
    assert spec.margin_initial == spec.margin_maintenance == spec.volume_limit == 0
    assert spec.trade_stops_level == spec.trade_freeze_level == 0
    assert spec.observed_at.utcoffset() == timedelta(0)
    assert InstrumentSnapshot.model_validate_json(spec.model_dump_json()) == spec
    with pytest.raises(ValidationError):
        spec.account_currency = "USD"


@pytest.mark.parametrize("field,value", [
    ("point", 0), ("point", True), ("point", "0.00001"), ("trade_tick_size", float("nan")),
    ("trade_tick_value_loss", 0), ("trade_tick_value_profit", None), ("volume_step", -1),
    ("volume_max", float("inf")), ("volume_min", 101), ("volume_limit", 0.001),
    ("volume_min", 0.015), ("trade_stops_level", True), ("trade_freeze_level", -1),
    ("digits", 3), ("digits", 5.0), ("filling_mode", 8), ("order_mode", 128),
    ("trade_mode", 5), ("trade_exemode", 4), ("trade_calc_mode", 999),
    ("currency_profit", ""), ("margin_initial", -1), ("margin_hedged_use_leg", 0),
    ("name", "WRONG"), ("trade_tick_size", 0.000015),
])
def test_invalid_metadata_is_never_cached(provider, field, value):
    provider.symbol_reader.side_effect = lambda symbol: native_symbol(**{**{"name": symbol}, field: value})
    with pytest.raises(InstrumentError):
        provider.get("EURUSD")
    assert provider._cache == {}


@pytest.mark.parametrize("field", ["trade_tick_value_loss", "trade_tick_value_profit", "volume_max", "currency_margin", "trade_mode"])
def test_missing_fields_fail_without_reference_fallback(provider, field):
    symbol = native_symbol()
    delattr(symbol, field)
    provider.symbol_reader.side_effect = lambda _: symbol
    with pytest.raises(InstrumentError):
        provider.get("EURUSD")


def test_cache_expiry_revision_and_forced_refresh(provider):
    first = provider.get("EURUSD")
    provider.clock.advance(timedelta(seconds=59))
    assert provider.get("EURUSD") is first
    assert provider.symbol_reader.call_count == 1
    provider.clock.advance(timedelta(seconds=1))
    second = provider.get("EURUSD")
    assert second is not first and second.observed_at > first.observed_at
    assert second.revision == first.revision
    provider.symbol_reader.side_effect = lambda symbol: native_symbol(symbol, trade_tick_value_loss=1.2)
    third = provider.get("EURUSD", refresh=True)
    assert third.revision != first.revision
    assert third.trade_tick_value_loss == Decimal("1.2")


def test_hash_normalizes_equal_native_numeric_representations(provider):
    first = provider.get("EURUSD")
    provider.symbol_reader.side_effect = lambda symbol: native_symbol(symbol, trade_contract_size=100000)
    assert provider.get("EURUSD", refresh=True).revision == first.revision


def test_revision_is_canonical_json_independent_of_input_order(provider):
    import hashlib
    import json
    snapshot = provider.get("EURUSD")
    data = dict(reversed(list(snapshot.model_dump(mode="json").items())))
    restored = InstrumentSnapshot.model_validate_json(json.dumps(data))
    assert restored.revision == snapshot.revision
    data.pop("observed_at")
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    assert snapshot.revision == hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("context", [dict(currency=""), dict(login=True), dict(leverage=0), dict(margin_mode=3)])
def test_invalid_account_metadata_never_reads_symbol(provider, context):
    provider.account_reader.return_value = native_account(**context)
    with pytest.raises(InstrumentError):
        provider.get("EURUSD")
    provider.symbol_reader.assert_not_called()


@pytest.mark.parametrize("field,value", [("login", 99), ("server", "Other"), ("currency", "JPY"), ("leverage", 200), ("margin_mode", 0)])
def test_cache_context_isolation(provider, field, value):
    first = provider.get("EURUSD")
    setattr(provider.account_reader.return_value, field, value)
    second = provider.get("EURUSD")
    assert second.revision != first.revision
    assert provider.symbol_reader.call_count == 2
    assert len(provider._cache) == 1


@pytest.mark.parametrize("field,value", [("login", 99), ("server", "Other"), ("currency", "JPY")])
def test_account_switch_during_read_rejects_snapshot(provider, field, value):
    def switch(symbol):
        setattr(provider.account_reader.return_value, field, value)
        return native_symbol(symbol)
    provider.symbol_reader.side_effect = switch
    with pytest.raises(InstrumentError, match="changed"):
        provider.get("EURUSD")
    assert provider._cache == {}


def test_failed_refresh_cannot_resurrect_previous_snapshot(provider):
    provider.get("EURUSD")
    provider.symbol_reader.side_effect = lambda _: None
    with pytest.raises(InstrumentError):
        provider.get("EURUSD", refresh=True)
    with pytest.raises(InstrumentError):
        provider.get("EURUSD")
    assert provider._cache == {}


def test_wall_clock_correction_and_slow_read(provider):
    first = provider.get("EURUSD")
    provider.clock.set_wall_time(first.observed_at - timedelta(seconds=1))
    assert provider.get("EURUSD") is not first
    def slow(symbol):
        provider.clock.advance(timedelta(seconds=60))
        return native_symbol(symbol)
    provider.symbol_reader.side_effect = slow
    with pytest.raises(InstrumentError, match="freshness"):
        provider.get("EURUSD", refresh=True)


def test_concurrent_cache_publication(provider):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: provider.get("EURUSD"), range(12)))
    assert all(spec is results[0] for spec in results)
    provider.symbol_reader.assert_called_once_with("EURUSD")


def test_reference_entries_are_copies_and_unknowns_not_guessed():
    from config.contract_specs import get_contract_spec
    reference = get_contract_spec("XAUUSD")
    assert reference["source"] == "unverified_reference" and not reference["execution_eligible"]
    reference["pip_value"] = 0
    assert get_contract_spec("XAUUSD")["pip_value"] > 0
    for symbol in ("GOLD.i#", "UNKNOWNJPY", "FAKEBTC", "FAKEXAU"):
        with pytest.raises(ValueError):
            get_contract_spec(symbol)
