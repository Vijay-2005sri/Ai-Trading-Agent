"""Native MT5 is always patched; no terminal or real broker is used."""

from types import SimpleNamespace
from unittest.mock import Mock
import ast
from pathlib import Path
from datetime import datetime, timezone

import pytest

from agents.risk_agent import TradeRecord
from broker_mt5 import order_executor as module
from config.execution_mode import ModeError


@pytest.fixture
def broker(monkeypatch):
    account = SimpleNamespace(trade_mode=module.mt5.ACCOUNT_TRADE_MODE_DEMO,
                              login=12345, server="Fixture-Server", equity=9876.5,
                              currency="EUR", leverage=100, margin_mode=2,
                              margin_free=100000.0, trade_allowed=True, trade_expert=True)
    monkeypatch.setattr(module, "MT5_AVAILABLE", True)
    calls = {}
    for name, result in {
        "initialize": True, "account_info": account, "shutdown": None,
        "terminal_info": SimpleNamespace(connected=True, trade_allowed=True, tradeapi_disabled=False),
        "symbol_info_tick": SimpleNamespace(ask=1.10, bid=1.0999,
            time_msc=int(datetime.now(timezone.utc).timestamp() * 1000)),
        "order_send": SimpleNamespace(retcode=module.mt5.TRADE_RETCODE_DONE, order=71),
        "positions_get": (), "last_error": (0, "fixture"),
    }.items():
        calls[name] = Mock(return_value=result)
        monkeypatch.setattr(module.mt5, name, calls[name])
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    from tests.instrument_fixtures import native_symbol
    calls["symbol_info"] = Mock(side_effect=native_symbol)
    monkeypatch.setattr(module.mt5, "symbol_info", calls["symbol_info"])

    def profit(action, symbol, volume, opened, closed):
        spec = native_symbol(symbol)
        ticks = abs(opened - closed) / spec.trade_tick_size
        sign = -1 if ((action == module.mt5.ORDER_TYPE_BUY and closed < opened)
                      or (action == module.mt5.ORDER_TYPE_SELL and closed > opened)) else 1
        return sign * ticks * spec.trade_tick_value_loss * volume

    calls["order_calc_profit"] = Mock(side_effect=profit)
    calls["order_calc_margin"] = Mock(side_effect=lambda action, symbol, volume, price: volume * 1000)
    calls["order_check"] = Mock(return_value=SimpleNamespace(retcode=0))
    monkeypatch.setattr(module.mt5, "order_calc_profit", calls["order_calc_profit"])
    monkeypatch.setattr(module.mt5, "order_calc_margin", calls["order_calc_margin"])
    monkeypatch.setattr(module.mt5, "order_check", calls["order_check"])

    positions = []
    initial_positions = object()
    calls["positions_get"].return_value = initial_positions
    def read_positions(**kwargs):
        explicit = calls["positions_get"].return_value
        if explicit is not initial_positions:
            return explicit
        return [p for p in positions if not kwargs or p.ticket == kwargs.get("ticket")]
    calls["positions_get"].side_effect = read_positions

    def send(request):
        response = calls["order_send"].return_value
        if getattr(response, "retcode", None) == module.mt5.TRADE_RETCODE_DONE:
            if "position" in request:
                positions[:] = [p for p in positions if p.ticket != request["position"]]
            else:
                positions.append(SimpleNamespace(
                    ticket=response.order, symbol=request["symbol"], type=request["type"],
                    volume=request["volume"], price_open=request["price"],
                    price_current=request["price"], sl=request.get("sl", 0),
                    tp=request.get("tp", 0), profit=0, time=1,
                ))
        return response

    calls["order_send"].side_effect = send
    return SimpleNamespace(account=account, calls=calls)


@pytest.fixture
def executor(broker, tmp_path):
    instance = module.OrderExecutor(mode="demo_mt5", enable_demo_orders=True)
    assert instance.connect(12345, "fixture-password", "Fixture-Server")
    instance._fixture_state_path = tmp_path / "risk-state.json"
    return instance


@pytest.fixture
def trade():
    from uuid import uuid4
    from broker_mt5.instruments import InstrumentProvider
    from broker_mt5.symbols import SymbolRegistry
    from tests.instrument_fixtures import native_account, native_symbol
    spec = InstrumentProvider(symbol_registry=SymbolRegistry(), account_reader=native_account,
                              symbol_reader=native_symbol).get("EURUSD")
    return TradeRecord("fixture-1", "EURUSD", "BUY", 1.10, 1.09, 1.12, 0.01,
                       candidate_id=str(uuid4()), strategy_id="EMA_Crossover",
                       evidence_digest="a" * 64, contract_revision=spec.revision)


def approve(executor, trade):
    """Use the real quote, risk and broker-check path for a successful send fixture."""
    from agents.risk_agent import RiskAgent
    risk = RiskAgent({"risk": {"min_risk_reward": 1.5}}, symbol_registry=executor.symbol_registry)
    risk.streak_file = executor._fixture_state_path
    executor.bind_risk_agent(risk)
    preparation = executor.prepare_trade(
        pair=trade.pair, direction=trade.direction, reference_entry=trade.entry_price,
        stop_loss=trade.stop_loss, take_profit=trade.take_profit, minimum_rr=1.5,
        contract_revision=trade.contract_revision, candidate_id=trade.candidate_id,
        strategy_id=trade.strategy_id, evidence_digest=trade.evidence_digest,
    )
    authorization = executor.authorize_trade(preparation, trade, confidence=85)
    assert authorization.approved, authorization.reason
    return authorization


def place_approved(executor, trade):
    authorization = approve(executor, trade)
    return executor.place_order(authorization.trade_record, approval_token=authorization.token)


@pytest.mark.parametrize("kwargs", [{}, {"demo_mode": True}, {"demo_mode": False},
                                       {"mode": "live", "enable_demo_orders": True},
                                       {"mode": "paper"}, {"mode": "historical"},
                                       {"mode": "demo_mt5"}])
def test_direct_executor_cannot_bypass_explicit_mode(broker, kwargs):
    with pytest.raises(ModeError):
        module.OrderExecutor(**kwargs)
    broker.calls["initialize"].assert_not_called()
    broker.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("change", ["real", "contest", "unknown", "wrong_login", "wrong_server"])
def test_connect_requires_verified_matching_demo(broker, change):
    if change == "unknown":
        broker.calls["account_info"].return_value = None
    elif change == "wrong_login":
        broker.account.login += 1
    elif change == "wrong_server":
        broker.account.server = "Other-Server"
    else:
        broker.account.trade_mode = getattr(module.mt5, "ACCOUNT_TRADE_MODE_" + change.upper())
    instance = module.OrderExecutor(mode="demo_mt5", enable_demo_orders=True)
    assert instance.connect(12345, "fixture-password", "Fixture-Server") is False
    assert instance.is_connected is False
    broker.calls["order_send"].assert_not_called()
    broker.calls["shutdown"].assert_called_once()


def test_verified_demo_can_place_close_and_read_real_equity(executor, broker, trade):
    assert executor.get_account_equity() == 9876.5
    assert executor.get_open_positions() == []
    opened = place_approved(executor, trade)
    closed = executor.close_order(71, "EURUSD", "BUY", 0.01)
    assert opened["success"] and closed["success"]
    assert opened["mode"] == closed["mode"] == "DEMO_MT5"
    assert broker.calls["order_send"].call_count == 2


@pytest.mark.parametrize("canonical", ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD", "XAGUSD", "USOIL", "BTCUSD", "ETHUSD"])
def test_all_instruments_translate_at_native_send_boundary(executor, broker, trade, canonical):
    trade.pair = canonical
    trade.contract_revision = executor.get_instrument_spec(canonical).revision
    native = executor.symbol_registry.broker_symbol(canonical)
    assert place_approved(executor, trade)["success"]
    assert broker.calls["order_send"].call_args.args[0]["symbol"] == native
    assert executor.close_order(71, canonical, "BUY", 0.01)["success"]
    assert broker.calls["order_send"].call_args.args[0]["symbol"] == native
    assert all(call.args == (native,) for call in broker.calls["symbol_info_tick"].call_args_list)
    assert trade.pair == canonical


def test_native_positions_preserve_raw_and_canonical_identity(executor, broker):
    position = SimpleNamespace(ticket=71, symbol="GOLD.i#", type=0, volume=0.01,
                               price_open=2000, price_current=2001, sl=1990, tp=2020, profit=1, time=1)
    broker.calls["positions_get"].return_value = [position]
    row = executor.get_open_positions()[0]
    assert row["pair"] == "XAUUSD" and row["broker_symbol"] == "GOLD.i#"
    position.symbol = "UNKNOWN.manual"
    with pytest.raises(ModeError, match="Unmapped"):
        executor.get_open_positions()


def test_unknown_order_symbol_never_reaches_native_send(executor, broker, trade):
    trade.pair = "GOLD.guessed"
    assert not executor.place_order(trade)["success"]
    broker.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("action", ["entry", "close", "equity", "positions"])
@pytest.mark.parametrize("change", ["real", "wrong_login", "missing"])
def test_account_change_blocks_all_operations_and_latches_disconnect(executor, broker, trade, action, change):
    approval = approve(executor, trade) if action == "entry" else None
    if change == "real":
        broker.account.trade_mode = module.mt5.ACCOUNT_TRADE_MODE_REAL
    elif change == "wrong_login":
        broker.account.login = 54321
    else:
        broker.calls["account_info"].return_value = None
    if action == "entry":
        assert executor.place_order(approval.trade_record, approval_token=approval.token)["success"] is False
    elif action == "close":
        assert executor.close_order(71, "EURUSD", "BUY", 0.01)["success"] is False
    else:
        with pytest.raises(ModeError):
            getattr(executor, "get_account_equity" if action == "equity" else "get_open_positions")()
    assert not executor.is_connected
    broker.calls["order_send"].assert_not_called()


def test_account_is_checked_after_quote_before_send(executor, broker, trade):
    approval = approve(executor, trade)
    def switch_account(_):
        broker.account.trade_mode = module.mt5.ACCOUNT_TRADE_MODE_REAL
        return SimpleNamespace(ask=1.10, bid=1.099)
    broker.calls["symbol_info_tick"].side_effect = switch_account
    assert executor.place_order(approval.trade_record, approval_token=approval.token)["success"] is False
    broker.calls["order_send"].assert_not_called()


def test_each_retry_rechecks_account(executor, broker, trade):
    approval = approve(executor, trade)
    def reject_then_switch(_):
        broker.account.trade_mode = module.mt5.ACCOUNT_TRADE_MODE_REAL
        return SimpleNamespace(retcode=module.mt5.TRADE_RETCODE_REQUOTE, comment="fixture requote")
    broker.calls["order_send"].side_effect = reject_then_switch
    assert executor.place_order(approval.trade_record, approval_token=approval.token)["success"] is False
    broker.calls["order_send"].assert_called_once()


@pytest.mark.parametrize("equity", [None, float("nan"), float("inf"), -1, "10000"])
def test_missing_or_invalid_equity_never_returns_fabricated_money(executor, broker, equity):
    broker.account.equity = equity
    with pytest.raises(ModeError):
        executor.get_account_equity()


@pytest.mark.parametrize("terminal", [None, SimpleNamespace(connected=False)])
def test_disconnected_terminal_blocks_send(executor, broker, trade, terminal):
    approval = approve(executor, trade)
    broker.calls["terminal_info"].return_value = terminal
    assert executor.place_order(approval.trade_record, approval_token=approval.token)["success"] is False
    broker.calls["order_send"].assert_not_called()
    assert not executor.is_connected


@pytest.mark.parametrize("field", ["login", "server", "trade_mode"])
def test_missing_account_fields_fail_closed(executor, broker, trade, field):
    delattr(broker.account, field)
    assert executor.place_order(trade)["success"] is False
    broker.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("failure", [False, RuntimeError("fixture initialization failure")])
def test_initialize_failure_does_not_fall_back_to_simulation(broker, trade, failure):
    if isinstance(failure, Exception):
        broker.calls["initialize"].side_effect = failure
    else:
        broker.calls["initialize"].return_value = failure
    instance = module.OrderExecutor(mode="demo_mt5", enable_demo_orders=True)
    assert instance.connect(12345, "fixture-password", "Fixture-Server") is False
    assert instance.place_order(trade)["success"] is False
    broker.calls["order_send"].assert_not_called()
    broker.calls["shutdown"].assert_called_once()


@pytest.mark.parametrize("overrides", [dict(login=0), dict(login=True), dict(login="12345"),
                                          dict(password=""), dict(server=""), dict(path="")])
def test_bad_credentials_fail_before_native_initialize(broker, overrides):
    instance = module.OrderExecutor(mode="demo_mt5", enable_demo_orders=True)
    credentials = dict(login=12345, password="fixture-password", server="Fixture-Server")
    credentials.update(overrides)
    with pytest.raises(ModeError):
        instance.connect(**credentials)
    broker.calls["initialize"].assert_not_called()


def test_positions_failure_is_not_an_empty_portfolio(executor, broker):
    broker.calls["positions_get"].return_value = None
    with pytest.raises(ModeError, match="unavailable"):
        executor.get_open_positions()
    assert not executor.is_connected


def test_native_positions_exception_requires_reconnect(executor, broker, trade):
    broker.calls["positions_get"].side_effect = RuntimeError("fixture native exception")
    with pytest.raises(ModeError, match="unavailable"):
        executor.get_open_positions()
    assert not executor.is_connected
    assert executor.place_order(trade)["success"] is False
    broker.calls["order_send"].assert_not_called()


def test_account_lookup_exception_latches_disconnected(executor, broker, trade):
    approval = approve(executor, trade)
    broker.calls["account_info"].side_effect = RuntimeError("fixture error")
    assert executor.place_order(approval.trade_record, approval_token=approval.token)["success"] is False
    assert not executor.is_connected
    broker.calls["order_send"].assert_not_called()


def test_identity_must_be_reconnected_after_failure(executor, broker, trade):
    approval = approve(executor, trade)
    broker.account.server = "Wrong-Server"
    assert executor.place_order(approval.trade_record, approval_token=approval.token)["success"] is False
    broker.account.server = "Fixture-Server"
    executor.is_connected = True  # A stale boolean alone cannot restore authority.
    executor.demo_mode = False  # Legacy mutable flag cannot turn on live trading.
    assert executor.place_order(trade)["success"] is False
    broker.calls["order_send"].assert_not_called()
    assert executor.connect(12345, "fixture-password", "Fixture-Server")
    assert place_approved(executor, trade)["success"] is True


def test_close_rechecks_after_quote(executor, broker):
    def change_account(_):
        broker.account.login += 1
        return SimpleNamespace(ask=1.10, bid=1.099)
    broker.calls["symbol_info_tick"].side_effect = change_account
    assert executor.close_order(71, "EURUSD", "BUY", 0.01)["success"] is False
    broker.calls["order_send"].assert_not_called()


def test_native_submissions_have_one_guarded_production_entrypoint():
    root = Path(__file__).resolve().parents[1]
    paths = [root / "main.py"]
    for directory in ("agents", "backtest", "broker_mt5", "config", "data", "data_feeds",
                      "monitoring", "rag_system", "strategy_library"):
        paths.extend((root / directory).rglob("*.py"))
    calls = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "order_send":
                calls.append((path, node))
    assert len(calls) == 1
    assert calls[0][0] == root / "broker_mt5/order_executor.py"
    tree = ast.parse(calls[0][0].read_text(encoding="utf-8"))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_send_demo_request")
    assert calls[0][1].lineno > method.lineno
    first = method.body[0]
    assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Call)
    assert first.value.func.attr == "assert_demo_session"
    assert isinstance(method.body[-1], ast.Return)
    assert method.body[-1].value.func.attr == "order_send"


@pytest.mark.parametrize("change", ["missing", "static", "zero_loss", "disabled", "close_only", "no_market", "no_ioc", "no_sl", "short_only"])
def test_unusable_contract_blocks_entry_without_send(executor, broker, trade, change):
    from tests.instrument_fixtures import native_symbol
    from config.contract_specs import get_contract_spec
    raw = native_symbol()
    if change == "missing":
        raw = None
    elif change == "static":
        raw = get_contract_spec("EURUSD")
    else:
        field, value = {
            "zero_loss": ("trade_tick_value_loss", 0), "disabled": ("trade_mode", 0),
            "close_only": ("trade_mode", 3), "no_market": ("order_mode", 126),
            "no_ioc": ("filling_mode", 1), "no_sl": ("order_mode", 111),
            "short_only": ("trade_mode", 2),
        }[change]
        setattr(raw, field, value)
    broker.calls["symbol_info"].side_effect = lambda _: raw
    assert not executor.place_order(trade)["success"]
    broker.calls["order_send"].assert_not_called()


def test_each_send_refreshes_and_changed_retry_metadata_blocks(executor, broker, trade):
    from tests.instrument_fixtures import native_symbol
    approval = approve(executor, trade)
    broker.calls["symbol_info"].side_effect = [native_symbol(), native_symbol(trade_tick_value_loss=0)]
    broker.calls["order_send"].return_value = SimpleNamespace(retcode=module.mt5.TRADE_RETCODE_REQUOTE, comment="fixture")
    assert not executor.place_order(approval.trade_record, approval_token=approval.token)["success"]
    # The gateway refreshes contract metadata at each validation boundary.
    assert broker.calls["symbol_info"].call_count >= 2
    # The invalid refreshed contract blocks the first send.
    broker.calls["order_send"].assert_not_called()
    assert executor.instruments._cache == {}


def test_close_forces_refresh_but_accepts_close_only(executor, broker, trade):
    from tests.instrument_fixtures import native_symbol
    assert place_approved(executor, trade)["success"]
    broker.calls["symbol_info"].side_effect = lambda symbol: native_symbol(symbol, trade_mode=3)
    assert executor.close_order(71, "EURUSD", "BUY", 0.01)["success"]
    assert broker.calls["symbol_info"].call_count > 2
    broker.calls["symbol_info"].side_effect = lambda _: None
    assert not executor.close_order(71, "EURUSD", "BUY", 0.01)["success"]
    assert broker.calls["order_send"].call_count == 2


@pytest.mark.parametrize("execution", [0, 1])
def test_request_instant_execution_ioc_not_confused_with_symbol_bitmask(executor, broker, trade, execution):
    from tests.instrument_fixtures import native_symbol
    broker.calls["symbol_info"].side_effect = lambda symbol: native_symbol(symbol, trade_exemode=execution, filling_mode=0)
    trade.contract_revision = executor.get_instrument_spec(trade.pair).revision
    assert place_approved(executor, trade)["success"]


@pytest.mark.parametrize("field,value", [("login", 99), ("server", "Different"), ("currency", "JPY")])
def test_account_change_inside_metadata_read_blocks_send(executor, broker, trade, field, value):
    from tests.instrument_fixtures import native_symbol
    def switch(symbol):
        setattr(broker.account, field, value)
        return native_symbol(symbol)
    broker.calls["symbol_info"].side_effect = switch
    assert not executor.place_order(trade)["success"]
    broker.calls["order_send"].assert_not_called()
    assert executor.instruments._cache == {}


def test_disconnect_and_reconnect_clear_metadata(executor, broker):
    executor.instruments.get("EURUSD")
    executor.disconnect()
    assert executor.instruments._cache == {}
    assert executor.connect(12345, "fixture-password", "Fixture-Server")
    executor.instruments.get("EURUSD")
    assert executor.connect(12345, "fixture-password", "Fixture-Server")
    assert executor.instruments._cache == {}


def test_order_audit_captures_observed_contract_revision(executor, broker, trade):
    assert place_approved(executor, trade)["success"]
    row = next(row for row in executor.get_order_log() if row.get("event") == "ContractSpecObserved")
    from broker_mt5.instruments import InstrumentSnapshot
    import json
    snapshot = InstrumentSnapshot.model_validate_json(json.dumps(row["snapshot"]))
    assert snapshot.revision == row["revision"]
    assert snapshot.account_currency == "EUR" and snapshot.broker_symbol == trade.pair


def test_currency_changes_after_metadata_read_before_send(executor, broker, trade):
    from tests.instrument_fixtures import native_symbol
    reads_after_symbol = []
    def symbol_read(symbol):
        def read_account():
            reads_after_symbol.append(True)
            if len(reads_after_symbol) == 2:
                broker.account.currency = "JPY"
            return broker.account
        broker.calls["account_info"].side_effect = read_account
        return native_symbol(symbol)
    broker.calls["symbol_info"].side_effect = symbol_read
    assert not executor.place_order(trade)["success"]
    broker.calls["order_send"].assert_not_called()
    assert executor.instruments._cache == {}


def test_contract_revision_drift_after_construction_blocks_send(executor, broker, trade):
    from tests.instrument_fixtures import native_symbol
    trade.contract_revision = executor.get_instrument_spec("EURUSD").revision
    broker.calls["symbol_info"].side_effect = lambda symbol: native_symbol(symbol, trade_tick_size=0.00002)
    assert not executor.place_order(trade)["success"]
    broker.calls["order_send"].assert_not_called()


def test_legacy_entry_without_provenance_blocks_before_symbol_work(executor, broker):
    legacy = TradeRecord("legacy", "EURUSD", "BUY", 1.1, 1.09, 1.12, 0.01)
    assert not executor.place_order(legacy)["success"]
    broker.calls["symbol_info"].assert_not_called()
    broker.calls["symbol_info_tick"].assert_not_called()
    broker.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("field,value", [("candidate_id", "bad"), ("strategy_id", ""), ("evidence_digest", None), ("contract_revision", None)])
def test_missing_entry_provenance_fails_closed(executor, broker, trade, field, value):
    setattr(trade, field, value)
    assert not executor.place_order(trade)["success"]
    broker.calls["symbol_info"].assert_not_called()
    broker.calls["order_send"].assert_not_called()
