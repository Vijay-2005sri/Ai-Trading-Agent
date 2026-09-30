"""Risk sizing integration with legacy daily state and verified metadata."""

from datetime import timedelta
from decimal import Decimal
import json

import pytest


def evaluate(engine, **updates):
    values = dict(pair="EURUSD", direction="BUY", entry_price=Decimal("1.1"),
                  stop_loss=Decimal("1.09"), take_profit=Decimal("1.12"),
                  confidence=85, equity=10000,
                  instrument_snapshot=engine.instance.executor.get_instrument_spec("EURUSD"))
    values.update(updates)
    return engine.instance.risk_agent.evaluate_trade(**values)


@pytest.mark.parametrize("equity", [0, -1, float("nan"), float("inf"), True])
def test_invalid_equity_cannot_mutate_daily_state(engine, equity):
    risk = engine.instance.risk_agent
    before = (risk.current_date, risk.peak_equity, risk.start_of_day_equity)
    result = evaluate(engine, equity=equity)
    assert not result.approved
    assert (risk.current_date, risk.peak_equity, risk.start_of_day_equity) == before
    assert not risk.streak_file.exists()


def test_cost_currency_mismatch_rejects_then_matching_allowance_reduces_size(engine):
    risk = engine.instance.risk_agent
    base = evaluate(engine)
    risk.cost_allowance_per_lot = 100
    risk.cost_allowance_currency = "USD"
    assert not evaluate(engine).approved  # fixture account is EUR
    risk.cost_allowance_currency = "EUR"
    with_cost = evaluate(engine)
    assert with_cost.approved
    assert with_cost.adjusted_lot_size < base.adjusted_lot_size
    assert Decimal(with_cost.sizing["estimated_total_loss"]) <= Decimal(with_cost.sizing["risk_budget"])


@pytest.mark.parametrize("direction,stop,target", [
    ("BUY", "1.11", "1.13"), ("BUY", "1.09", "1.08"),
    ("SELL", "1.09", "1.07"), ("SELL", "1.11", "1.12"),
])
def test_direct_risk_api_rejects_wrong_side_levels(engine, direction, stop, target):
    assert not evaluate(engine, direction=direction, stop_loss=Decimal(stop),
                        take_profit=Decimal(target)).approved


def test_missing_metadata_rejects(engine):
    assert not evaluate(engine, instrument_snapshot=None).approved


@pytest.mark.parametrize("saved", [None, [], "broken", {"current_date": "invalid"}])
def test_invalid_legacy_state_shape_does_not_restore_equity(engine, saved):
    risk = engine.instance.risk_agent
    risk.streak_file.write_text(json.dumps(saved))
    risk._load_streak()
    assert risk.start_of_day_equity == 0


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_only_same_day_equity_restored_and_streak_cannot_change_volume(engine, offset):
    risk = engine.instance.risk_agent
    risk.streak_file.write_text(json.dumps({
        "current_date": (risk.current_date + timedelta(days=offset)).isoformat(),
        "start_of_day_equity": 10100, "consecutive_wins": 99,
    }))
    risk._load_streak()
    assert risk.start_of_day_equity == (10100 if offset == 0 else 0)
    result = evaluate(engine)
    assert result.approved and result.adjusted_lot_size == 0.16
    assert risk._get_risk_pct(10000, "XAGUSD") == risk.risk_pct_high_capital


def test_new_day_resets_and_persists_equity_baseline(engine):
    risk = engine.instance.risk_agent
    risk.current_date -= timedelta(days=1)
    risk.start_of_day_equity = 20000
    assert evaluate(engine).approved
    saved = json.loads(risk.streak_file.read_text())
    assert saved["start_of_day_equity"] == 10000
    assert saved["current_date"] == risk.current_date.isoformat()
