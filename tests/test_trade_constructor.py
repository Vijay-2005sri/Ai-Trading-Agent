from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from broker_mt5.instruments import InstrumentProvider
from broker_mt5.symbols import SymbolRegistry
from agents.risk_agent import RiskCheckResult
from core.trade_constructor import bind_context, construct_trade, ConstructionError
from tests.instrument_fixtures import native_account, native_symbol


def context(signal):
    return bind_context(signal, {}, {}, None, {"EMA_Crossover"})


def metadata(tick=0.00001, digits=5):
    provider = InstrumentProvider(symbol_registry=SymbolRegistry(), account_reader=native_account,
        symbol_reader=lambda symbol: native_symbol(symbol, trade_tick_size=tick, digits=digits, point=10 ** -digits))
    return provider.get("EURUSD")


@pytest.mark.parametrize("side,entry,stop,target,expected", [
    ("BUY", 100.03, 99.91, 100.41, ("100.05", "99.90", "100.40")),
    ("SELL", 100.03, 100.19, 99.61, ("100.00", "100.20", "99.65")),
])
def test_directional_rounding_and_recomputed_rr(proposal_inputs, side, entry, stop, target, expected):
    signal = dict(proposal_inputs["top_signal"], direction=side, entry_price=entry, stop_loss=stop, take_profit=target)
    result = construct_trade(context(signal), metadata(0.05, 2), minimum_rr=1.5)
    assert (result.entry_price, result.stop_loss, result.take_profit) == tuple(map(Decimal, expected))
    assert result.risk_reward == abs(result.take_profit-result.entry_price) / abs(result.entry_price-result.stop_loss)
    assert result.candidate_id == proposal_inputs["decision"].candidate_id


@pytest.mark.parametrize("field,value", [
    ("entry_price", 0), ("stop_loss", -1), ("take_profit", None), ("entry_price", float("inf")),
    ("stop_loss", float("nan")), ("take_profit", True), ("entry_price", "1.1"),
    ("direction", "HOLD"), ("direction", "sell"), ("stop_loss", 1.11),
    ("take_profit", 1.09), ("confidence", True), ("confidence", 101),
    ("candidate_id", "missing"), ("strategy", "invented"), ("pair", "FAKE"), ("reasoning", ""),
])
def test_invalid_candidate_has_no_geometry_fallback(proposal_inputs, field, value):
    signal = dict(proposal_inputs["top_signal"], **{field: value})
    with pytest.raises(ConstructionError):
        context(signal)


def test_missing_stop_and_tick_collapsed_geometry_rejected(proposal_inputs):
    signal = dict(proposal_inputs["top_signal"])
    del signal["stop_loss"]
    with pytest.raises(ConstructionError):
        context(signal)
    signal = dict(proposal_inputs["top_signal"], entry_price=1.101, stop_loss=1.099, take_profit=1.105)
    with pytest.raises(ConstructionError, match="collapsed"):
        construct_trade(context(signal), metadata(0.01, 2), minimum_rr=1.5)


@pytest.mark.parametrize("minimum", [0, -1, float("nan"), 3])
def test_invalid_or_unmet_rr_rejected(proposal_inputs, minimum):
    with pytest.raises(ConstructionError):
        construct_trade(context(proposal_inputs["top_signal"]), metadata(), minimum_rr=minimum)


@pytest.mark.parametrize("change", ["missing_id", "wrong_id", "strategy", "side", "signal", "evidence", "duplicate", "no_context", "unknown_action"])
def test_bad_binding_stops_before_risk_or_submission(engine, proposal_inputs, change):
    app = engine.instance
    decision = proposal_inputs["decision"]
    if change == "missing_id":
        decision.candidate_id = None
    elif change == "wrong_id":
        decision.candidate_id = uuid4()
    elif change == "strategy":
        decision.strategy_used = "Bollinger_Breakout"
    elif change == "side":
        decision.action = "SELL"
    elif change == "unknown_action":
        decision.action = "BUY_NOW"
    elif change == "signal":
        proposal_inputs["top_signal"]["entry_price"] = 1.101
    elif change == "evidence":
        proposal_inputs["trade_recall"]["doc_ids"].append("injected")
    elif change == "duplicate":
        proposal_inputs["strategy_signals"].append(deepcopy(proposal_inputs["top_signal"]))
    else:
        proposal_inputs["candidate_context"] = None
    app._execute_validated_trade(**proposal_inputs)
    app.executor.place_order.assert_not_called()
    app.executor.get_account_equity.assert_not_called()
    assert app.trade_log[-1]["action"] == "HOLD"
    assert "CONSTRUCTION_REJECTED" in app.trade_log[-1]["outcome"]


def test_llm_prices_are_advisory_and_journal_records_actual_geometry(engine, proposal_inputs):
    proposal_inputs["decision"].suggested_sl = 50000
    proposal_inputs["decision"].suggested_tp = -99
    engine.instance._execute_validated_trade(**proposal_inputs)
    record = engine.instance.executor.place_order.call_args.args[0]
    assert (record.entry_price, record.stop_loss, record.take_profit) == (1.1001, 1.09, 1.12)
    assert record.candidate_id == str(proposal_inputs["decision"].candidate_id)
    payload = engine.instance.journal.replay()[0].event.payload
    assert Decimal(payload["construction"]["constructed"]["stop_loss"]) == Decimal("1.09")
    assert payload["construction"]["candidate"]["candidate_id"] == record.candidate_id
    assert payload["construction"]["constructed"]["contract_revision"] == record.contract_revision


def test_broker_gateway_veto_after_risk_approval_never_submits(engine, proposal_inputs):
    app = engine.instance
    app.executor.authorize_trade.side_effect = None
    app.executor.authorize_trade.return_value = type("Authorization", (), {
        "approved": False,
        "reason": "Broker margin changed",
        "audit": {"fixture": True},
        "risk_result": RiskCheckResult(
            approved=True, adjusted_lot_size=0.16, reason="Risk approved",
            risk_pct_used=0.015, trades_today=0, max_trades_today=2,
            current_drawdown_pct=0.0, equity=10000.0, sizing={"fixture": True},
        ),
    })()

    app._execute_validated_trade(**proposal_inputs)

    app.executor.place_order.assert_not_called()
    assert "PRE_TRADE_GATEWAY_REJECTED: Broker margin changed" in app.trade_log[-1]["outcome"]


def test_hold_does_not_request_contract_or_equity(engine, proposal_inputs):
    proposal_inputs["decision"].action = "HOLD"
    proposal_inputs["decision"].candidate_id = None
    engine.instance._execute_validated_trade(**proposal_inputs)
    engine.instance.executor.get_instrument_spec.assert_not_called()
    engine.instance.executor.get_account_equity.assert_not_called()


def test_trade_decision_requires_uuid_for_executable_action(decision):
    from agents.llm_provider import TradeDecision
    data = decision.model_dump()
    for candidate_id in (None, "bad"):
        with pytest.raises(ValidationError):
            TradeDecision(**{**data, "candidate_id": candidate_id})
    with pytest.raises(ValidationError):
        TradeDecision(**{**data, "action": "BUY_NOW"})


def test_debate_retains_base_candidate_but_wrong_consensus_side_is_rejected(engine, proposal_inputs):
    from agents.debate_arena import DebateArena
    arena = DebateArena.__new__(DebateArena)
    base = proposal_inputs["decision"]
    result = arena._tally_votes([{"chosen_action": "SELL", "chosen_model": "fixture", "final_confidence": 90}], {"fixture": base})
    decision = result["winning_decision"]
    assert decision.candidate_id == base.candidate_id
    assert decision.action == "SELL"
    proposal_inputs["decision"] = decision
    engine.instance._execute_validated_trade(**proposal_inputs)
    engine.instance.executor.place_order.assert_not_called()


@pytest.mark.parametrize("path", ["gold", "secondary", "legacy"])
@pytest.mark.parametrize("tamper", [False, True])
def test_all_analysis_paths_bind_before_llm_and_share_geometry(engine, proposal_inputs, monkeypatch, path, tamper):
    from types import SimpleNamespace
    import pandas as pd
    import main
    app = engine.instance
    symbol = "XAUUSD" if path == "gold" else "EURUSD"
    signal = dict(proposal_inputs["top_signal"], pair=symbol)
    app.mt5_fetcher.get_historical_data.return_value = pd.DataFrame({"close": [1.1]})
    monkeypatch.setattr(main, "run_all_strategies", lambda *args, **kwargs: [signal])
    app.rag.recall_similar_trades.return_value = dict(proposal_inputs["trade_recall"], summary="verified fixture")
    app.rag.recall_similar_news.return_value = dict(proposal_inputs["news_recall"], summary="no news", total_found=0)
    app.rag.get_strategy_win_rate.return_value = 0.6
    def response(**kwargs):
        assert f"SELECTED candidate_id={signal['candidate_id']}" in kwargs["quant_report"]
        if tamper:
            signal["entry_price"] = 1.105
        decision = proposal_inputs["decision"].model_copy(update={"pair": symbol, "suggested_sl": 999, "suggested_tp": -1})
        return decision
    monkeypatch.setattr(app.brain, "evaluate", response)
    monkeypatch.setattr(app.brain, "evaluate_with_debate", lambda **kwargs: (response(**kwargs), SimpleNamespace(debate_successful=False)))
    if path == "gold":
        app._process_gold_with_debate("fixture")
    elif path == "secondary":
        app.non_gold_symbols = [symbol]
        app._process_secondary_market("fixture")
    else:
        app._analyze_symbol(symbol, "fixture")
    assert app.executor.place_order.call_count == int(not tamper)
    assert app.rag.recall_similar_trades.call_args.kwargs["strategy"] == "EMA_Crossover"
    if not tamper:
        trade = app.executor.place_order.call_args.args[0]
        assert (trade.entry_price, trade.stop_loss, trade.take_profit) == (1.1001, 1.09, 1.12)
        assert trade.pair == symbol and trade.candidate_id == signal["candidate_id"]


def test_runner_owns_registry_id_and_breaks_ties_deterministically(monkeypatch):
    from core.signals import TradeSignal
    from strategy_library import strategy_master as master
    class Strategy:
        def __init__(self, pair):
            self.pair = pair
        def generate_signals(self, frame):
            return [TradeSignal("emitted-variant", "BUY", self.pair, 1.1, 1.09, 1.12, 999, 85, "fixture", "bar")]
    monkeypatch.setattr(master, "STRATEGY_REGISTRY", {"ZZ": Strategy, "AA": Strategy})
    first = master.run_all_strategies(None)
    monkeypatch.setattr(master, "STRATEGY_REGISTRY", {"AA": Strategy, "ZZ": Strategy})
    second = master.run_all_strategies(None)
    assert [s["strategy"] for s in first] == [s["strategy"] for s in second] == ["AA", "ZZ"]
    assert all(s["signal_label"] == "emitted-variant" and s["risk_reward"] == 2 for s in first)
    assert len({s["candidate_id"] for s in first + second}) == 4


def test_seven_modules_share_signal_contract():
    import importlib
    from core.signals import TradeSignal
    for name in ("smc_concepts", "ict_concepts", "wyckoff_method", "trend_following", "mean_reversion", "harmonic_fibonacci", "scalping_price_action"):
        assert importlib.import_module(f"strategy_library.live.{name}").TradeSignal is TradeSignal


def test_provider_exhaustion_hold_keeps_requested_instrument(engine, decision):
    app = engine.instance
    app.llm_provider.invoke_structured.return_value = decision.model_copy(update={"action": "HOLD", "pair": "UNKNOWN", "candidate_id": None})
    held = app.brain.evaluate(quant_report="fixture", fundamental_report="fixture",
        strategy_knowledge="fixture", concept_knowledge="fixture", rag_context="fixture", pair="EURUSD")
    assert held.action == "HOLD" and held.pair == "EURUSD"
    app.executor.place_order.assert_not_called()
