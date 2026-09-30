"""Ticket-backed protective reductions use native position state only."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from broker_mt5 import order_executor as module
from config.execution_mode import ModeError
from tests.instrument_fixtures import native_symbol


@pytest.fixture
def broker(monkeypatch):
    account = SimpleNamespace(
        trade_mode=module.mt5.ACCOUNT_TRADE_MODE_DEMO, login=12345,
        server="Fixture-Server", equity=9876.5, currency="EUR",
        leverage=100, margin_mode=2, trade_allowed=True, trade_expert=True,
        margin_free=100_000.0, tradeapi_disabled=False,
    )
    monkeypatch.setattr(module, "MT5_AVAILABLE", True)
    calls = {}
    for name, result in {
        "initialize": True, "account_info": account, "shutdown": None,
        "terminal_info": SimpleNamespace(connected=True, trade_allowed=True, tradeapi_disabled=False),
        "symbol_info_tick": SimpleNamespace(ask=1.10, bid=1.099),
        "order_send": SimpleNamespace(retcode=module.mt5.TRADE_RETCODE_DONE, order=72),
        "positions_get": [SimpleNamespace(ticket=71, symbol="EURUSD", type=0, volume=0.05)],
        "order_check": SimpleNamespace(retcode=0), "last_error": (0, "fixture"),
    }.items():
        calls[name] = Mock(return_value=result)
        monkeypatch.setattr(module.mt5, name, calls[name], raising=False)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    calls["symbol_info"] = Mock(side_effect=native_symbol)
    monkeypatch.setattr(module.mt5, "symbol_info", calls["symbol_info"])
    return SimpleNamespace(account=account, calls=calls)


@pytest.fixture
def executor(broker):
    instance = module.OrderExecutor(mode="demo_mt5", enable_demo_orders=True)
    assert instance.connect(12345, "fixture-password", "Fixture-Server")
    return instance


def position(*, ticket=71, symbol="EURUSD", side=0, volume=0.05):
    return SimpleNamespace(ticket=ticket, symbol=symbol, type=side, volume=volume)


@pytest.fixture
def close_ready(executor, broker, monkeypatch):
    """Supply fresh offline quotes and successful validation responses."""
    broker.calls["symbol_info_tick"].return_value = SimpleNamespace(
        ask=1.10, bid=1.099,
        time_msc=int(datetime.now(timezone.utc).timestamp() * 1000),
    )
    broker.calls["order_check"] = Mock(return_value=SimpleNamespace(retcode=0))
    monkeypatch.setattr(module.mt5, "order_check", broker.calls["order_check"], raising=False)
    broker.calls["positions_get"].return_value = [position()]
    return SimpleNamespace(executor=executor, broker=broker)


def module_mt5(executor):
    return executor._mt5


def test_close_public_api_validates_native_position_and_sends_reduction(close_ready):
    result = close_ready.executor.close_order(71, "EURUSD", "BUY", 0.02)

    assert result["success"] is True
    close_ready.broker.calls["positions_get"].assert_any_call(ticket=71)
    assert close_ready.broker.calls["order_check"].call_count == 1
    request = close_ready.broker.calls["order_send"].call_args.args[0]
    assert request["position"] == 71
    assert request["symbol"] == "EURUSD"
    assert request["volume"] == pytest.approx(0.02)
    assert request["type"] == module_mt5(close_ready.executor).ORDER_TYPE_SELL


@pytest.mark.parametrize(
    "ticket,pair,direction,positions",
    [
        (None, "EURUSD", "BUY", [position()]),
        (0, "EURUSD", "BUY", [position()]),
        (71, "EURUSD", "BUY", []),
        (71, "EURUSD", "BUY", None),
        (72, "EURUSD", "BUY", [position(ticket=71)]),
        (71, "GBPUSD", "BUY", [position()]),
        (71, "EURUSD", "SELL", [position()]),
        (71, "EURUSD", "BUY", [position(symbol="EURUSD.pro")]),
        (71, "EURUSD", "SELL", [position(side=7)]),
    ],
    ids=["null-ticket", "invalid-ticket", "missing", "unavailable", "mismatched-ticket", "mismatched-pair",
         "mismatched-original-side", "mismatched-native-symbol", "unknown-native-side"],
)
def test_close_rejects_missing_or_mismatched_native_identity(
    close_ready, ticket, pair, direction, positions
):
    close_ready.broker.calls["positions_get"].return_value = positions

    result = close_ready.executor.close_order(ticket, pair, direction, 0.02)

    assert result["success"] is False
    if type(ticket) is int and ticket > 0:
        close_ready.broker.calls["positions_get"].assert_called_once_with(ticket=ticket)
    close_ready.broker.calls["order_check"].assert_not_called()
    close_ready.broker.calls["order_send"].assert_not_called()


@pytest.mark.parametrize("volume", [0, -0.01, float("nan"), float("inf"), 0.06, 0.015])
def test_close_rejects_invalid_or_nonreducible_volume(close_ready, volume):
    result = close_ready.executor.close_order(71, "EURUSD", "BUY", volume)

    assert result["success"] is False
    close_ready.broker.calls["order_send"].assert_not_called()


def test_close_rejects_account_identity_change_during_native_position_read(close_ready):
    calls = 0

    def switch_account(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            close_ready.broker.account.currency = "JPY"
        return [position()]

    close_ready.broker.calls["positions_get"].side_effect = switch_account

    result = close_ready.executor.close_order(71, "EURUSD", "BUY", 0.02)

    assert result["success"] is False
    close_ready.broker.calls["positions_get"].assert_called_once_with(ticket=71)
    close_ready.broker.calls["order_send"].assert_not_called()


def test_close_rejects_position_shrink_before_native_send(close_ready):
    close_ready.broker.calls["positions_get"].side_effect = [
        [position(volume=0.05)], [position(volume=0.01)],
    ]

    result = close_ready.executor.close_order(71, "EURUSD", "BUY", 0.02)

    assert result["success"] is False
    assert close_ready.broker.calls["positions_get"].call_count >= 2
    assert close_ready.broker.calls["order_check"].call_count == 1
    close_ready.broker.calls["order_send"].assert_not_called()


def test_close_rejects_ticket_swap_before_native_send(close_ready):
    close_ready.broker.calls["positions_get"].side_effect = [
        [position(ticket=71, volume=0.05)],
        [position(ticket=71, volume=0.05)],
        [position(ticket=72, volume=0.05)],
    ]

    result = close_ready.executor.close_order(71, "EURUSD", "BUY", 0.02)

    assert result["success"] is False
    assert close_ready.broker.calls["positions_get"].call_count >= 3
    close_ready.broker.calls["order_check"].assert_called_once()
    close_ready.broker.calls["order_send"].assert_not_called()


def test_sell_position_close_rechecks_ask_before_native_send(close_ready):
    close_ready.broker.calls["positions_get"].return_value = [position(side=1)]
    now = int(datetime.now(timezone.utc).timestamp() * 1000)
    close_ready.broker.calls["symbol_info_tick"].side_effect = [
        SimpleNamespace(ask=1.10, bid=1.099, time_msc=now),
        SimpleNamespace(ask=1.10, bid=1.099, time_msc=now),
        SimpleNamespace(ask=1.1001, bid=1.099, time_msc=now),
    ]

    result = close_ready.executor.close_order(71, "EURUSD", "SELL", 0.02)

    assert result["success"] is False
    assert close_ready.broker.calls["positions_get"].call_count >= 2
    assert close_ready.broker.calls["symbol_info_tick"].call_count >= 3
    close_ready.broker.calls["order_check"].assert_called_once()
    close_ready.broker.calls["order_send"].assert_not_called()


def test_direct_send_cannot_bypass_ticketed_close_gateway(close_ready):
    spec = close_ready.executor.get_instrument_spec("EURUSD")
    request = {
        "action": module_mt5(close_ready.executor).TRADE_ACTION_DEAL,
        "symbol": "EURUSD", "volume": 0.02,
        "type": module_mt5(close_ready.executor).ORDER_TYPE_SELL,
        "position": 71, "price": 1.099,
        "deviation": 10, "magic": close_ready.executor.MAGIC_NUMBER,
        "comment": "caller-built", "type_time": module_mt5(close_ready.executor).ORDER_TIME_GTC,
        "type_filling": module_mt5(close_ready.executor).ORDER_FILLING_IOC,
    }

    with pytest.raises(ModeError):
        close_ready.executor._send_demo_request(request, contract_revision=spec.revision)

    close_ready.broker.calls["order_send"].assert_not_called()
