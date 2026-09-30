"""Characterize the actual shared gate without a broker, provider or memory DB."""

import json
import ast
from pathlib import Path
from unittest.mock import Mock

import pytest


def test_both_active_analysis_callers_use_shared_gate():
    # Static characterization avoids external analysis calls and detects an
    # accidental inline broker bypass in either existing entry path.
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    engine_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "TradingEngine")
    for name in ("_process_gold_with_debate", "_process_secondary_market", "_analyze_symbol"):
        method = next(n for n in engine_class.body if isinstance(n, ast.FunctionDef) and n.name == name)
        called = [n.func.attr for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        assert called.count("_execute_validated_trade") == 1
        assert "place_order" not in called
        assert "order_send" not in called


def test_constructor_wires_external_boundaries_without_using_them(engine):
    app = engine.instance
    constructors = engine.constructors
    constructors["MT5DataFetcher"].assert_called_once()
    constructors["MT5DataFetcher"].return_value.connect.assert_called_once_with()
    constructors["OrderExecutor"].assert_called_once_with(
        mode="demo_mt5", enable_demo_orders=True, symbol_registry=app.symbol_registry,
        clock=app.clock, gateway_config=app.config["broker"]["pre_trade_gateway"],
    )
    constructors["OrderExecutor"].return_value.connect.assert_called_once()
    assert constructors["MT5DataFetcher"].call_args.kwargs == {
        **constructors["OrderExecutor"].return_value.connect.call_args.kwargs,
        "symbol_registry": app.symbol_registry,
    }
    constructors["TradingRAG"].assert_called_once_with(db_path=str(engine.root / "chroma"), symbol_registry=app.symbol_registry)
    constructors["LLMProvider"].assert_called_once_with()
    assert app.sentiment_analyzer is None
    assert app.trade_log == []
    assert app.trade_log_path == engine.root / "trade_log.json"
    assert app.risk_agent.streak_file.is_relative_to(engine.root)
    assert app.observation_logger.base_dir.is_relative_to(engine.root)
    app.executor.place_order.assert_not_called()


@pytest.mark.parametrize("case", ["hold", "cold_start", "risk_veto"])
def test_non_executable_decisions_never_reach_order_submission(engine, proposal_inputs, case):
    app = engine.instance
    if case == "hold":
        proposal_inputs["decision"].action = "HOLD"
    elif case == "cold_start":
        proposal_inputs["trade_recall"] = {"is_cold_start": True, "total_found": 0}
        from core.trade_constructor import bind_context
        proposal_inputs["candidate_context"] = bind_context(proposal_inputs["top_signal"],
            proposal_inputs["trade_recall"], proposal_inputs["news_recall"], 0.6, {"EMA_Crossover"})
    else:
        # Establish a real risk-engine hard drawdown veto with valid grounding.
        app.risk_agent.peak_equity = 20000.0
    original = app.risk_agent.evaluate_trade
    app.risk_agent.evaluate_trade = Mock(wraps=original)
    app._execute_validated_trade(**proposal_inputs)
    app.executor.place_order.assert_not_called()
    assert not app.risk_agent.open_positions
    assert len(app.trade_log) == 1
    outcome = app.trade_log[0]["outcome"]
    if case == "risk_veto":
        assert "VETOED" in outcome
        app.executor.authorize_trade.assert_called_once()
    else:
        app.executor.authorize_trade.assert_not_called()
        assert "HOLD" in outcome or "GROUNDING_OVERRIDE" in outcome
    assert json.loads(app.trade_log_path.read_text(encoding="utf-8")) == app.trade_log


@pytest.mark.parametrize("accepted", [True, False])
def test_grounded_trade_tracks_only_successful_orders(engine, proposal_inputs, accepted):
    app = engine.instance
    app.executor.place_order.return_value["success"] = accepted
    app._execute_validated_trade(**proposal_inputs)
    app.executor.place_order.assert_called_once()
    record = app.executor.place_order.call_args.args[0]
    assert record.pair == "EURUSD"
    assert record.direction == "BUY"
    assert record.entry_price == 1.1001  # approved BUY uses the executable Ask
    assert record.stop_loss == 1.09
    assert record.take_profit == 1.12
    assert len(app.risk_agent.open_positions) == int(accepted)
    assert len(app.risk_agent.trades_today) == int(accepted)
    assert ("EXECUTED" if accepted else "ORDER_FAILED") in app.trade_log[-1]["outcome"]
    assert len(list((engine.root / "observations").glob("*.jsonl"))) == 1


def test_streak_persistence_is_redirected(engine):
    risk = engine.instance.risk_agent
    risk._save_streak()
    saved = json.loads(risk.streak_file.read_text())
    assert saved["consecutive_wins"] == 0
    assert saved["start_of_day_equity"] == risk.start_of_day_equity


def test_old_streak_file_only_restores_same_day_equity(engine):
    risk = engine.instance.risk_agent
    risk.streak_file.write_text(json.dumps({
        "consecutive_wins": 99,
        "current_date": "2000-01-01",
        "start_of_day_equity": 12345.0,
    }))
    risk.start_of_day_equity = 0
    risk._load_streak()
    assert risk.start_of_day_equity == 0
    assert not hasattr(risk, "consecutive_wins")
