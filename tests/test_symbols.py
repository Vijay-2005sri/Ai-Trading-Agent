from copy import deepcopy

import pytest

from broker_mt5.symbols import SymbolRegistry, SymbolError


def test_config_nine_instruments_roundtrip(settings):
    registry = SymbolRegistry.from_config(settings)
    symbols = registry.active_symbols(settings["broker"]["symbols"])
    assert len(symbols) == 9 and len(set(symbols)) == 9
    assert registry.broker_symbol("XAUUSD") == "GOLD.i#"
    for canonical in symbols:
        assert registry.canonical(registry.broker_symbol(canonical)) == canonical
        for alias in registry.aliases(canonical):
            assert registry.canonical(alias) == canonical


@pytest.mark.parametrize("name", ["GOLD", "gold.i#", "XAUUSD.fake", " XAUUSD", "", None])
def test_unknown_names_never_guessed(name):
    with pytest.raises(SymbolError):
        SymbolRegistry().canonical(name)


def test_duplicates_and_collisions_fail(settings):
    with pytest.raises(SymbolError):
        SymbolRegistry().active_symbols(["XAUUSD", "GOLD.i#"])
    config = deepcopy(settings)
    config["broker"]["symbol_map"]["XAGUSD"] = "GOLD.i#"
    with pytest.raises(SymbolError):
        SymbolRegistry.from_config(config)


def test_custom_mapping_preserves_legacy_without_suffix_guessing(settings):
    config = deepcopy(settings)
    config["broker"]["symbol_map"]["XAUUSD"] = "Gold.custom"
    registry = SymbolRegistry.from_config(config)
    assert registry.broker_symbol("XAUUSD") == "Gold.custom"
    with pytest.raises(SymbolError):
        registry.broker_symbol("GOLD.i#")
    assert registry.aliases("XAUUSD") == ("XAUUSD", "Gold.custom", "GOLD.i#")


def test_gold_has_one_internal_path(engine):
    app = engine.instance
    assert app.gold_symbol == "XAUUSD"
    assert "XAUUSD" in app.symbols
    assert "XAUUSD" not in app.non_gold_symbols
    assert "GOLD.i#" not in app.non_gold_symbols


@pytest.mark.parametrize("available", [True, False])
def test_cycle_only_runs_gold_once_when_available(engine, monkeypatch, available):
    from unittest.mock import Mock
    app = engine.instance
    if not available:
        app.symbols.remove("XAUUSD")
    gold, secondary = Mock(), Mock()
    monkeypatch.setattr(app, "_gather_fundamentals", lambda _: ([], "fixture"))
    monkeypatch.setattr(app, "_process_gold_with_debate", gold)
    monkeypatch.setattr(app, "_process_secondary_market", secondary)
    app.run_cycle()
    assert gold.call_count == int(available)
    secondary.assert_called_once_with("fixture")
    assert "XAUUSD" not in app.non_gold_symbols


def test_old_broker_name_is_read_compatible_but_not_current_position_identity(settings):
    settings["broker"]["symbol_map"]["XAUUSD"] = "Gold.new"
    registry = SymbolRegistry.from_config(settings)
    assert registry.canonical("GOLD.i#") == "XAUUSD"
    with pytest.raises(SymbolError):
        registry.from_broker("GOLD.i#")


def test_risk_aliases_share_correlation_and_overrides(engine):
    from agents.risk_agent import TradeRecord
    risk = engine.instance.risk_agent
    risk.record_trade_opened(TradeRecord("old", "GOLD.i#", "BUY", 2000, 1990, 2020, 0.01))
    assert risk.open_positions[0].pair == "XAUUSD"
    assert risk._count_correlated_positions("SILVER.i#") == 1
    assert risk._get_risk_pct(10000, "SILVER.i#") == risk._get_risk_pct(10000, "XAGUSD")
    assert risk.check_high_conviction_hold("OILCash#", 95) == risk.check_high_conviction_hold("USOIL", 95)
    with pytest.raises(SymbolError):
        risk._count_correlated_positions("FakeXAG")


@pytest.mark.parametrize("canonical", ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD", "XAGUSD", "USOIL", "BTCUSD", "ETHUSD"])
def test_feed_native_boundaries_and_canonical_health(monkeypatch, canonical):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from data_feeds import mt5_market_data as module
    feed = module.MT5DataFetcher(1, "fixture", "fixture")
    feed._connection_alive = True
    native = feed.symbol_registry.broker_symbol(canonical)
    info = Mock(return_value=SimpleNamespace(visible=False))
    select = Mock(return_value=True)
    rates = Mock(return_value=[{"time": 100, "open": 1, "high": 2, "low": 1, "close": 2}])
    tick = Mock(return_value=SimpleNamespace(bid=1, ask=2, time=100))
    monkeypatch.setattr(module.mt5, "symbol_info", info)
    monkeypatch.setattr(module.mt5, "symbol_select", select)
    monkeypatch.setattr(module.mt5, "copy_rates_from_pos", rates)
    monkeypatch.setattr(module.mt5, "symbol_info_tick", tick)
    assert feed.get_historical_data(canonical, 1) is not None
    assert feed.get_live_tick(canonical)["ask"] == 2
    info.assert_called_once_with(native)
    select.assert_called_once_with(native, True)
    rates.assert_called_once_with(native, 1, 0, 500)
    tick.assert_called_once_with(native)
    monkeypatch.setattr(feed, "_is_mt5_running", lambda: True)
    monkeypatch.setattr(module.mt5, "terminal_info", lambda: SimpleNamespace(trade_allowed=True))
    monkeypatch.setattr(module.mt5, "account_info", lambda: SimpleNamespace(login=1, balance=100, equity=100, trade_mode=0))
    assert feed.health_check([canonical])["symbols_status"] == {canonical: True}
    assert feed.health_check([native])["symbols_status"] == {canonical: True}


def test_mismatched_decision_identity_stops_before_risk_or_send(engine, proposal_inputs):
    proposal_inputs["decision"].pair = "XAUUSD"
    with pytest.raises(SymbolError, match="does not match"):
        engine.instance._execute_validated_trade(**proposal_inputs)
    engine.instance.executor.place_order.assert_not_called()


@pytest.mark.parametrize("bad", [{}, {"XAUUSD": "GOLD"}, [], None])
def test_incomplete_or_malformed_explicit_map_rejected_before_broker(startup, monkeypatch, bad):
    main, doubles = startup
    config = main.load_config()
    config["broker"]["symbol_map"] = bad
    monkeypatch.setattr(main, "load_config", lambda: config)
    with pytest.raises(SymbolError):
        main.TradingEngine()
    doubles["OrderExecutor"].assert_not_called()


def test_unknown_open_trade_does_not_partially_mutate_risk(engine):
    from agents.risk_agent import TradeRecord
    risk = engine.instance.risk_agent
    with pytest.raises(SymbolError):
        risk.record_trade_opened(TradeRecord("bad", "UNKNOWN", "BUY", 1, 0.9, 1.2, 0.01))
    assert risk.trades_today == risk.open_positions == []


def test_global_cannot_be_an_executable_alias(settings):
    settings["broker"]["legacy_symbol_aliases"] = {"XAUUSD": ["GLOBAL"]}
    with pytest.raises(SymbolError):
        SymbolRegistry.from_config(settings)
