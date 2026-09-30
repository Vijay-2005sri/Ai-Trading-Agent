from datetime import datetime, timezone
from decimal import Decimal

import pytest

from broker_mt5.instruments import InstrumentSnapshot
from core.position_sizer import SizingError, size_position


def snapshot(symbol="EURUSD", *, tick_size="0.0001", tick_loss="10", digits=5,
             volume_min="0.01", volume_max="100", volume_step="0.01",
             volume_limit="0", mode=0, currency="USD"):
    point = Decimal(10) ** -digits
    broker_names = {"XAUUSD": "GOLD.i#", "XAGUSD": "SILVER.i#", "USOIL": "OILCash#",
                    "BTCUSD": "BTCUSD#", "ETHUSD": "ETHUSD#"}
    broker = broker_names.get(symbol, symbol)
    return InstrumentSnapshot(
        instrument_id=symbol, broker_symbol=broker, server="Fixture", login=7,
        account_currency=currency, leverage=100, margin_mode=2,
        observed_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
        currency_base="EUR", currency_profit=currency, currency_margin=currency,
        digits=digits, point=point, trade_tick_size=Decimal(tick_size),
        trade_tick_value_profit=Decimal(tick_loss), trade_tick_value_loss=Decimal(tick_loss),
        trade_contract_size=Decimal("1"), volume_min=Decimal(volume_min),
        volume_max=Decimal(volume_max), volume_step=Decimal(volume_step),
        volume_limit=Decimal(volume_limit), trade_stops_level=0, trade_freeze_level=0,
        trade_mode=4, trade_exemode=2, filling_mode=2, order_mode=127,
        trade_calc_mode=mode, margin_initial=Decimal(0), margin_maintenance=Decimal(0),
        margin_hedged=Decimal(0), margin_hedged_use_leg=False,
    )


@pytest.mark.parametrize(("symbol", "tick", "tick_value", "digits", "entry", "stop", "expected"), [
    ("EURUSD", "0.0001", "10", 5, "1.1000", "1.0990", "0.10"),
    ("XAUUSD", "0.1", "1", 2, "2000", "1995", "0.20"),
    ("XAGUSD", "0.01", "0.5", 2, "25", "24.9", "2.00"),
    ("USOIL", "0.01", "0.5", 2, "80", "79", "0.20"),
    ("BTCUSD", "1", "0.2", 0, "60000", "59000", "0.05"),
])
def test_hand_calculated_fx_metals_oil_and_crypto(symbol, tick, tick_value, digits,
                                                  entry, stop, expected):
    spec = snapshot(symbol, tick_size=tick, tick_loss=tick_value, digits=digits,
                    mode=0 if symbol == "EURUSD" else 3)
    result = size_position(instrument=spec, direction="BUY", entry_price=Decimal(entry),
                           stop_loss=Decimal(stop), equity=1000, risk_fraction=Decimal("0.01"))
    assert result.volume == Decimal(expected)
    assert result.estimated_total_loss <= result.risk_budget == Decimal("10.00")
    assert result.account_currency == "USD"
    assert result.contract_revision == spec.revision


def test_sell_uses_stop_distance_and_loss_tick_value():
    spec = snapshot().model_copy(update={"trade_tick_value_profit": Decimal("1")})
    result = size_position(instrument=spec, direction="SELL", entry_price=Decimal("1.1000"),
                           stop_loss=Decimal("1.1010"), equity=1000, risk_fraction=Decimal("0.01"))
    assert result.volume == Decimal("0.10")


def test_floor_step_minimum_and_risk_cap():
    result = size_position(instrument=snapshot(), direction="BUY", entry_price=Decimal("1.1"),
                           stop_loss=Decimal("1.099"), equity=Decimal("1999"), risk_fraction=Decimal("0.01"))
    assert result.raw_volume == Decimal("0.1999")
    assert result.volume == Decimal("0.19")
    assert result.estimated_total_loss == Decimal("19.0")
    assert result.estimated_total_loss <= result.risk_budget


def test_volume_max_and_nonzero_symbol_limit_cap_each_order():
    spec = snapshot(volume_max="1.00", volume_limit="0.50")
    result = size_position(instrument=spec, direction="BUY", entry_price=Decimal("1.1"),
                           stop_loss=Decimal("1.099"), equity=100000, risk_fraction=Decimal("0.02"))
    assert result.volume == Decimal("0.50")
    assert result.estimated_total_loss <= result.risk_budget


def test_broker_minimum_is_never_rounded_up():
    with pytest.raises(SizingError, match="minimum"):
        size_position(instrument=snapshot(), direction="BUY", entry_price=Decimal("1.1"),
                      stop_loss=Decimal("1.099"), equity=1, risk_fraction=Decimal("0.01"))


def test_cost_allowance_reduces_volume():
    result = size_position(instrument=snapshot(), direction="BUY", entry_price=Decimal("1.1"),
                           stop_loss=Decimal("1.099"), equity=1000, risk_fraction=Decimal("0.01"),
                           cost_allowance_per_lot=Decimal("10"))
    assert result.volume == Decimal("0.09")
    assert result.estimated_total_loss == Decimal("9.9")
    assert result.cost_allowance_per_lot == Decimal("10")


@pytest.mark.parametrize(("equity", "entry", "stop", "risk", "multiplier"), [
    (0, "1.1", "1.09", "0.01", 1), (-1, "1.1", "1.09", "0.01", 1),
    (float("nan"), "1.1", "1.09", "0.01", 1), (float("inf"), "1.1", "1.09", "0.01", 1),
    (1000, "1.1", "1.1", "0.01", 1), (1000, "1.1", "1.11", "0.01", 1),
    (1000, "NaN", "1.09", "0.01", 1), (1000, "1.1", "1.09", "NaN", 1),
    (1000, "1.1", "1.09", "0.01", 0),
])
def test_invalid_values_fail_closed(equity, entry, stop, risk, multiplier):
    with pytest.raises(SizingError):
        size_position(instrument=snapshot(), direction="BUY", entry_price=Decimal(entry),
                      stop_loss=Decimal(stop), equity=equity, risk_fraction=Decimal(risk),
                      drawdown_multiplier=multiplier)


def test_snapshot_is_required_and_revalidated():
    with pytest.raises(SizingError, match="InstrumentSnapshot"):
        size_position(instrument=object(), direction="BUY", entry_price=Decimal("1.1"),
                      stop_loss=Decimal("1.09"), equity=1000, risk_fraction=Decimal("0.01"))
    invalid = snapshot().model_copy(update={"trade_tick_value_loss": Decimal(0)})
    with pytest.raises(SizingError):
        size_position(instrument=invalid, direction="BUY", entry_price=Decimal("1.1"),
                      stop_loss=Decimal("1.09"), equity=1000, risk_fraction=Decimal("0.01"))


def test_unsupported_contract_calculation_mode_rejects():
    spec = snapshot(mode=2)
    with pytest.raises(SizingError, match="broker P/L"):
        size_position(instrument=spec, direction="BUY", entry_price=Decimal("1.1"),
                      stop_loss=Decimal("1.09"), equity=1000, risk_fraction=Decimal("0.01"))


def test_budget_and_drawdown_monotonicity_and_stop_distance():
    spec = snapshot()

    def sized(equity=1000, stop="1.099", multiplier=1):
        return size_position(instrument=spec, direction="BUY", entry_price=Decimal("1.1"),
                             stop_loss=Decimal(stop), equity=equity, risk_fraction=Decimal("0.01"),
                             drawdown_multiplier=multiplier).volume

    base = sized()
    assert sized(equity=2000) >= base
    assert sized(multiplier=Decimal("0.5")) <= base
    assert sized(stop="1.098") <= base


def test_nonzero_symbol_volume_limit_caps_order():
    spec = snapshot(volume_limit="0.05")
    result = size_position(instrument=spec, direction="BUY", entry_price=Decimal("1.1"),
                           stop_loss=Decimal("1.099"), equity=10000, risk_fraction=Decimal("0.02"))
    assert result.volume == Decimal("0.05")


@pytest.mark.parametrize("step", ["0.001", "0.25", "1"])
def test_nonstandard_volume_steps_floor_without_exceeding_budget(step):
    spec = snapshot(volume_min=step, volume_step=step)
    result = size_position(instrument=spec, direction="BUY", entry_price=Decimal("1.1"),
                           stop_loss=Decimal("1.099"), equity=12345, risk_fraction=Decimal("0.01"))
    assert result.volume % Decimal(step) == 0
    assert result.volume <= Decimal("1.2345")
    assert result.estimated_total_loss <= Decimal("123.45")


@pytest.mark.parametrize("field,bad", [
    ("equity", True), ("equity", "1000"), ("entry_price", 0),
    ("stop_loss", float("inf")), ("risk_fraction", 0), ("risk_fraction", 1.1),
    ("drawdown_multiplier", -1), ("drawdown_multiplier", 2),
    ("cost_allowance_per_lot", -1), ("cost_allowance_per_lot", float("nan")),
    ("direction", "HOLD"),
])
def test_each_bad_input_is_rejected_with_other_inputs_valid(field, bad):
    inputs = dict(instrument=snapshot(), direction="BUY", entry_price=Decimal("1.1"),
                  stop_loss=Decimal("1.099"), equity=1000, risk_fraction=Decimal("0.01"))
    inputs[field] = bad
    with pytest.raises(SizingError):
        size_position(**inputs)


@pytest.mark.parametrize("field,bad", [
    ("trade_tick_size", Decimal(0)), ("trade_tick_value_loss", Decimal("NaN")),
    ("volume_step", Decimal(0)), ("volume_limit", Decimal(-1)),
    ("volume_min", Decimal("0.015")), ("trade_calc_mode", True),
])
def test_mutated_snapshot_is_rejected(field, bad):
    with pytest.raises(SizingError):
        size_position(instrument=snapshot().model_copy(update={field: bad}), direction="BUY",
                      entry_price=Decimal("1.1"), stop_loss=Decimal("1.099"),
                      equity=1000, risk_fraction=Decimal("0.01"))


def test_exact_minimum_and_maximum_boundaries():
    for equity, expected in [(100, "0.01"), (10000000, "100")]:
        result = size_position(instrument=snapshot(), direction="BUY",
                               entry_price=Decimal("1.1"), stop_loss=Decimal("1.099"),
                               equity=equity, risk_fraction=Decimal("0.01"))
        assert result.volume == Decimal(expected)


def test_static_legacy_helper_cannot_supply_executable_volume():
    from config.contract_specs import calculate_lot_size
    with pytest.raises(ValueError, match="Static contract specs"):
        calculate_lot_size("EURUSD", 1, 100)
