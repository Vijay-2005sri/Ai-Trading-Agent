"""Exercise the shared risk gate's broker-sized volume and durable audit trail."""

from decimal import Decimal

import pytest


@pytest.mark.parametrize(
    "equity,daily_drawdown,expected_volume,expected_budget",
    [
        (10_000.0, 0.0, 0.16, 150.0),
        (10_000.0, 0.025, 0.08, 73.125),
        (5_000.0, 0.0, 0.08, 75.0),
    ],
)
def test_shared_gate_sizes_order_from_cash_budget_and_drawdown(
    engine, proposal_inputs, equity, daily_drawdown, expected_volume, expected_budget
):
    app = engine.instance
    app.executor.get_account_equity.return_value = equity
    if daily_drawdown:
        app.risk_agent.peak_equity = equity
        app.risk_agent.start_of_day_equity = equity
        app.executor.get_account_equity.return_value = equity * (1 - daily_drawdown)

    app._execute_validated_trade(**proposal_inputs)

    app.executor.place_order.assert_called_once()
    record = app.executor.place_order.call_args.args[0]
    assert record.lot_size == pytest.approx(expected_volume)
    assert Decimal(record.sizing_provenance["risk_budget"]) == Decimal(str(expected_budget))
    assert float(record.sizing_provenance["estimated_total_loss"]) <= expected_budget
    assert record.sizing_provenance["account_currency"] == "EUR"


@pytest.mark.parametrize(
    "metadata_update",
    [
        {"volume_min": Decimal("1.0")},
        {"trade_calc_mode": 2},
    ],
    ids=["minimum-volume-unfunded", "unsupported-contract-mode"],
)
def test_unfundable_or_unsupported_sizing_never_reaches_executor(
    engine, proposal_inputs, metadata_update
):
    app = engine.instance
    from broker_mt5.instruments import InstrumentSnapshot

    snapshot = app.executor.get_instrument_spec("EURUSD")
    app.executor.get_instrument_spec.side_effect = None
    app.executor.get_instrument_spec.return_value = InstrumentSnapshot.model_validate(
        snapshot.model_dump() | metadata_update
    )

    app._execute_validated_trade(**proposal_inputs)

    app.executor.place_order.assert_not_called()
    assert "VETOED by Risk Agent" in app.trade_log[-1]["outcome"]
    assert app.journal.replay()[0].event.payload.get("position_sizing") is None


def test_sizing_provenance_is_durable_with_currency_revision_budget_and_estimate(
    engine, proposal_inputs
):
    app = engine.instance
    app._execute_validated_trade(**proposal_inputs)

    app.executor.place_order.assert_called_once()
    payload = app.journal.replay()[0].event.payload
    sizing = payload["position_sizing"]
    assert sizing["account_currency"] == "EUR"
    assert sizing["contract_revision"]
    assert float(sizing["risk_budget"]) == pytest.approx(150.0)
    # The gateway uses the executable ask (1.1001), not the advisory signal
    # price (1.1000), before the final sizing pass.
    assert float(sizing["estimated_total_loss"]) == pytest.approx(145.44)
    record = app.executor.place_order.call_args.args[0]
    assert record.sizing_provenance == sizing
