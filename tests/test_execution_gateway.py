"""Quote-bound gateway authorization; all native calls remain offline doubles."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from agents.risk_agent import RiskAgent, TradeRecord
from broker_mt5 import order_executor as module
from broker_mt5.execution_gateway import ExecutionGateway, GatewayError
from core.time_service import FakeClock
from tests.instrument_fixtures import native_symbol


@pytest.fixture
def ready(monkeypatch):
    clock = FakeClock(datetime(2026, 10, 1, tzinfo=timezone.utc))
    account = SimpleNamespace(trade_mode=module.mt5.ACCOUNT_TRADE_MODE_DEMO,
        login=12345, server="Fixture-Server", currency="EUR", leverage=100, margin_mode=2,
        equity=10000.0, margin_free=10000.0, trade_allowed=True, trade_expert=True)
    terminal = SimpleNamespace(connected=True, trade_allowed=True, tradeapi_disabled=False)
    tick = SimpleNamespace(bid=1.0999, ask=1.1, time_msc=int(clock.now_utc().timestamp() * 1000))
    spec = native_symbol()
    calls = {}
    for name, value in {
        "initialize": True, "shutdown": None, "account_info": account,
        "terminal_info": terminal, "symbol_info": spec, "symbol_info_tick": tick,
        "order_check": SimpleNamespace(retcode=0), "order_calc_margin": 50.0,
        "order_send": SimpleNamespace(retcode=module.mt5.TRADE_RETCODE_DONE, order=71),
    }.items():
        calls[name] = Mock(return_value=value)
        monkeypatch.setattr(module.mt5, name, calls[name])
    calls["order_calc_profit"] = Mock(side_effect=lambda action, symbol, volume, entry, stop:
        -float(abs(Decimal(str(entry)) - Decimal(str(stop))) * 100000 * Decimal(str(volume))))
    monkeypatch.setattr(module.mt5, "order_calc_profit", calls["order_calc_profit"])
    monkeypatch.setattr(module, "MT5_AVAILABLE", True)
    monkeypatch.setattr(RiskAgent, "_load_streak", lambda self: None)
    monkeypatch.setattr(RiskAgent, "_save_streak", lambda self: None)
    executor = module.OrderExecutor(mode="demo_mt5", enable_demo_orders=True, clock=clock)
    assert executor.connect(12345, "fixture", "Fixture-Server")
    risk = RiskAgent({"risk": {"sizing_cost_currency": "EUR"}})
    gateway = executor.execution_gateway
    gateway.bind_risk_agent(risk)

    def prepare(direction="BUY", **changes):
        snapshot = executor.get_instrument_spec("EURUSD")
        record = TradeRecord("fixture-1", "EURUSD", direction, 1.1,
            1.09 if direction == "BUY" else 1.11,
            1.12 if direction == "BUY" else 1.08, 99,
            candidate_id=str(uuid4()), strategy_id="EMA_Crossover",
            evidence_digest="a" * 64, contract_revision=snapshot.revision)
        args = dict(pair=record.pair, direction=direction, reference_entry=record.entry_price,
            stop_loss=record.stop_loss, take_profit=record.take_profit, minimum_rr=1.5,
            contract_revision=record.contract_revision, candidate_id=record.candidate_id,
            strategy_id=record.strategy_id, evidence_digest=record.evidence_digest)
        args.update(changes)
        return gateway.prepare_trade(**args), record

    def authorize(direction="BUY", **changes):
        preparation, record = prepare(direction, **changes)
        return gateway.authorize_trade(preparation, record, confidence=85)

    return SimpleNamespace(executor=executor, gateway=gateway, account=account, terminal=terminal,
        clock=clock, tick=tick, spec=spec, calls=calls, risk=risk, prepare=prepare, authorize=authorize)


@pytest.mark.parametrize("direction,price", [("BUY", 1.1), ("SELL", 1.0999)])
def test_executable_side_and_exact_checked_request_reach_native_send(ready, direction, price):
    authorization = ready.authorize(direction)
    assert authorization.approved
    assert authorization.trade_record.entry_price == price
    result = ready.executor.place_order(authorization.trade_record, approval_token=authorization.token)
    assert result["success"]
    ready.calls["order_send"].assert_called_once()
    assert ready.calls["order_check"].call_args.args[0] == ready.calls["order_send"].call_args.args[0]
    assert ready.calls["order_send"].call_args.args[0]["volume"] < 99
    sizing = authorization.trade_record.sizing_provenance
    assert Decimal(sizing["estimated_total_loss"]) <= Decimal(sizing["risk_budget"])


@pytest.mark.parametrize("value", [True, False, "2", None, 0, -1, float("nan"), float("inf")])
def test_invalid_configuration_is_not_coerced(ready, value):
    with pytest.raises(GatewayError):
        ExecutionGateway(ready.executor, config={"approval_ttl_seconds": value})


@pytest.mark.parametrize("change", ["stale", "future", "nan", "zero", "crossed", "spread", "drift", "rr", "stop-side", "stop-grid", "stops", "freeze"])
def test_quote_geometry_and_freshness_fail_closed(ready, change):
    kwargs = {}
    if change == "stale": ready.tick.time_msc -= 2001
    if change == "future": ready.tick.time_msc += 1
    if change == "nan": ready.tick.ask = float("nan")
    if change == "zero": ready.tick.bid = 0
    if change == "crossed": ready.tick.bid = 1.2
    if change == "spread": ready.tick.bid = 1.09
    if change == "drift": ready.tick.ask, ready.tick.bid = 1.1011, 1.101
    if change == "rr": kwargs["take_profit"] = 1.114
    if change == "stop-side": kwargs.update(stop_loss=1.09995, take_profit=1.101)
    if change == "stop-grid": kwargs["stop_loss"] = 1.090001
    if change == "stops": ready.spec.trade_stops_level = 1000
    if change == "freeze": ready.spec.trade_freeze_level = 1000
    with pytest.raises(GatewayError):
        ready.prepare(**kwargs)
    ready.calls["order_send"].assert_not_called()


def test_drift_erodes_previously_valid_rr(ready):
    ready.tick.ask, ready.tick.bid = 1.1005, 1.1004
    with pytest.raises(GatewayError, match="reward/risk"):
        ready.prepare(take_profit=1.115)


@pytest.mark.parametrize("kind", ["copy", "mutation", "foreign", "reuse"])
def test_preparations_require_issuer_identity_and_one_use(ready, kind):
    preparation, record = ready.prepare()
    gateway = ready.gateway
    if kind == "copy": preparation = replace(preparation)
    if kind == "mutation": object.__setattr__(preparation, "entry_price", Decimal("1.101"))
    if kind == "foreign":
        gateway = ExecutionGateway(ready.executor, clock=ready.clock)
        gateway.bind_risk_agent(ready.risk)
    if kind == "reuse": gateway.authorize_trade(preparation, record, confidence=85)
    with pytest.raises(GatewayError):
        gateway.authorize_trade(preparation, record, confidence=85)
    ready.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("where", ["before-risk", "risk", "profit", "margin", "check", "before-send"])
def test_whole_preparation_to_send_ttl(ready, where):
    preparation, record = ready.prepare()
    def delay(): ready.clock.advance(timedelta(seconds=4))
    if where == "before-risk": delay()
    elif where == "risk":
        original = ready.risk.evaluate_trade
        ready.risk.evaluate_trade = lambda **kwargs: (delay(), original(**kwargs))[1]
    elif where in ("profit", "margin", "check"):
        name = {"profit": "order_calc_profit", "margin": "order_calc_margin", "check": "order_check"}[where]
        original = ready.calls[name].side_effect
        result = ready.calls[name].return_value
        ready.calls[name].side_effect = lambda *a: (delay(), original(*a) if original else result)[1]
    if where == "before-send":
        auth = ready.gateway.authorize_trade(preparation, record, confidence=85)
        delay()
        with pytest.raises(GatewayError): ready.gateway.submit_entry(auth.trade_record, auth.token)
    else:
        with pytest.raises(GatewayError): ready.gateway.authorize_trade(preparation, record, confidence=85)
    ready.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("value", [None, True, "-1000", float("nan"), float("inf"), 0, 1, -1000000])
def test_broker_loss_invalid_or_unaffordable_minimum_blocks(ready, value):
    ready.calls["order_calc_profit"].side_effect = None
    ready.calls["order_calc_profit"].return_value = value
    with pytest.raises(GatewayError): ready.authorize()
    ready.calls["order_send"].assert_not_called()


def test_final_volume_loss_recalculation_catches_non_linear_excess(ready):
    ready.calls["order_calc_profit"].side_effect = [-1000, -151]
    with pytest.raises(GatewayError, match="risk budget"): ready.authorize()
    ready.calls["order_send"].assert_not_called()


def test_costs_and_drawdown_reduce_broker_sized_volume(ready):
    ready.risk.cost_allowance_per_lot = 100
    # Stay strictly inside the reduction band despite binary float rounding.
    ready.risk.start_of_day_equity = 10000 / 0.97
    ready.risk.current_date = date.today()
    authorization = ready.authorize()
    assert authorization.approved
    assert authorization.trade_record.lot_size == pytest.approx(0.06)
    assert Decimal(authorization.audit["estimated_total_loss"]) == Decimal("66")
    assert Decimal(authorization.audit["risk_budget"]) == Decimal("75")


def test_terminal_permission_change_during_quote_read_blocks_send(ready):
    def revoke_terminal(_):
        ready.terminal.trade_allowed = False
        return ready.tick

    ready.calls["symbol_info_tick"].side_effect = revoke_terminal
    with pytest.raises(GatewayError, match="Terminal trading API permissions changed"):
        ready.prepare()
    ready.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("kind", ["margin-none", "margin-negative", "margin-inf", "margin-excess", "check-none", "check-code", "check-bool", "check-mutation", "exception"])
def test_margin_and_exact_order_check_fail_closed(ready, kind):
    if kind.startswith("margin"):
        ready.calls["order_calc_margin"].return_value = {"margin-none": None, "margin-negative": -1,
            "margin-inf": float("inf"), "margin-excess": 10001}[kind]
    elif kind == "exception": ready.calls["order_check"].side_effect = RuntimeError("unavailable")
    elif kind == "check-mutation":
        def mutate(request):
            request["volume"] = 99
            return SimpleNamespace(retcode=0)
        ready.calls["order_check"].side_effect = mutate
    else:
        ready.calls["order_check"].return_value = {"check-none": None, "check-code": SimpleNamespace(retcode=10009),
            "check-bool": SimpleNamespace(retcode=False)}[kind]
    with pytest.raises(GatewayError): ready.authorize()
    ready.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("field", ["equity-down", "equity-up", "free-margin", "currency", "spec", "quote", "permission", "terminal"])
@pytest.mark.parametrize("when", ["order-check", "native-boundary"])
def test_state_changes_at_slow_callback_or_native_boundary_block(ready, monkeypatch, field, when):
    def mutate():
        if field == "equity-down": ready.account.equity -= 1
        if field == "equity-up": ready.account.equity += 1
        if field == "free-margin": ready.account.margin_free -= 1
        if field == "currency": ready.account.currency = "JPY"
        if field == "spec": ready.spec.trade_tick_value_loss += 0.1
        if field == "quote": ready.tick.ask = 1.10001
        if field == "permission": ready.account.trade_expert = False
        if field == "terminal": ready.terminal.tradeapi_disabled = True
    if when == "order-check":
        ready.calls["order_check"].side_effect = lambda request: (mutate(), SimpleNamespace(retcode=0))[1]
        with pytest.raises(GatewayError): ready.authorize()
    else:
        authorization = ready.authorize()
        original = ready.executor._send_demo_request
        def changed(*args, **kwargs):
            mutate()
            return original(*args, **kwargs)
        monkeypatch.setattr(ready.executor, "_send_demo_request", changed)
        with pytest.raises(GatewayError): ready.gateway.submit_entry(authorization.trade_record, authorization.token)
    ready.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("kind", ["forged", "foreign", "mutated", "replay"])
def test_approval_tokens_cannot_be_forged_changed_or_reused(ready, kind):
    authorization = ready.authorize()
    token, gateway = authorization.token, ready.gateway
    if kind == "forged": token = "caller-token"
    if kind == "foreign": gateway = ExecutionGateway(ready.executor, clock=ready.clock)
    if kind == "mutated": authorization.trade_record.lot_size += 1
    if kind == "replay": gateway.submit_entry(authorization.trade_record, token)
    with pytest.raises(GatewayError): gateway.submit_entry(authorization.trade_record, token)
    assert ready.calls["order_send"].call_count == int(kind == "replay")


@pytest.mark.parametrize("outcome", ["none", "exception", "rejected", "partial"])
def test_ambiguous_or_failed_native_attempt_never_retries(ready, outcome):
    authorization = ready.authorize()
    if outcome == "exception": ready.calls["order_send"].side_effect = RuntimeError("connection lost")
    else: ready.calls["order_send"].return_value = None if outcome == "none" else SimpleNamespace(retcode=10010 if outcome == "partial" else 10004)
    try:
        result = ready.gateway.submit_entry(authorization.trade_record, authorization.token)
        assert not result["success"]
    except GatewayError:
        assert outcome == "exception"
    with pytest.raises(GatewayError): ready.gateway.submit_entry(authorization.trade_record, authorization.token)
    ready.calls["order_send"].assert_called_once()


def test_native_permit_cannot_be_replayed_or_forged(ready, monkeypatch):
    authorization = ready.authorize()
    captured = {}
    original = ready.executor._send_demo_request
    def capture(request, **kwargs):
        captured.update(request=request, kwargs=kwargs)
        return original(request, **kwargs)
    monkeypatch.setattr(ready.executor, "_send_demo_request", capture)
    assert ready.gateway.submit_entry(authorization.trade_record, authorization.token)["success"]
    for permit in (captured["kwargs"]["gateway_permit"], object(), (object(), "close", {}, {}), None):
        with pytest.raises(module.ModeError):
            original(captured["request"], contract_revision=authorization.trade_record.contract_revision, gateway_permit=permit)
    ready.calls["order_send"].assert_called_once()


def test_direct_record_cannot_enter_without_gateway(ready):
    _, record = ready.prepare()
    assert not ready.executor.place_order(record)["success"]
    ready.calls["order_send"].assert_not_called()
