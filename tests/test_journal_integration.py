"""Journal is authoritative; legacy JSON is a separate compatibility projection."""

from contextlib import closing
from unittest.mock import Mock

import pytest

from core.persistence import JournalError


def test_cycle_boundaries_share_run_and_use_utc(engine, monkeypatch):
    app = engine.instance
    monkeypatch.setattr(app, "_run_cycle_body", lambda _: None)
    app.run_cycle()
    rows = app.journal.replay()
    assert [r.event.event_type for r in rows] == ["AnalysisRunStarted", "AnalysisRunCompleted"]
    assert rows[0].event.run_id == rows[1].event.run_id
    assert rows[1].event.causation_id == rows[0].event.event_id
    assert rows[0].event.occurred_at.utcoffset().total_seconds() == 0
    assert app.journal.get_run(rows[0].event.run_id).market_snapshot_at is None


@pytest.mark.parametrize("error", [RuntimeError("fixture cycle error"), KeyboardInterrupt()])
def test_failed_or_interrupted_cycle_records_failure(engine, monkeypatch, error):
    app = engine.instance
    monkeypatch.setattr(app, "_run_cycle_body", Mock(side_effect=error))
    with pytest.raises(type(error)):
        app.run_cycle()
    assert [r.event.event_type for r in app.journal.replay()] == ["AnalysisRunStarted", "AnalysisRunFailed"]
    assert app._active_run_id is None


def test_decision_journal_precedes_json_and_keeps_evidence_if_projection_fails(engine, proposal_inputs, monkeypatch):
    app = engine.instance
    proposal_inputs["decision"].action = "HOLD"
    monkeypatch.setattr(app, "_save_trade_log", Mock(side_effect=OSError("fixture projection failure")))
    with pytest.raises(OSError):
        app._execute_validated_trade(**proposal_inputs)
    rows = app.journal.replay()
    assert len(rows) == 1
    assert rows[0].event.event_type == "DecisionRecorded"
    assert rows[0].event.payload["action"] == "HOLD"
    assert rows[0].event.payload["event_id"] == app.trade_log[0]["event_id"]
    app.executor.place_order.assert_not_called()


def test_journal_failure_does_not_claim_persisted_json_decision(engine, proposal_inputs, monkeypatch):
    app = engine.instance
    proposal_inputs["decision"].action = "HOLD"
    writer = Mock()
    monkeypatch.setattr(app, "_save_trade_log", writer)
    monkeypatch.setattr(app.journal, "commit", Mock(side_effect=JournalError("fixture disk failure")))
    with pytest.raises(JournalError):
        app._execute_validated_trade(**proposal_inputs)
    assert app.trade_log == []
    writer.assert_not_called()


def test_failed_start_event_prevents_cycle_work(engine, monkeypatch):
    app = engine.instance
    body = Mock()
    monkeypatch.setattr(app, "_run_cycle_body", body)
    monkeypatch.setattr(app.journal, "commit", Mock(side_effect=JournalError("fixture unavailable")))
    with pytest.raises(JournalError):
        app.run_cycle()
    body.assert_not_called()


def test_shutdown_closes_journal_even_when_executor_disconnect_fails(engine):
    app = engine.instance
    app.executor.disconnect.side_effect = RuntimeError("fixture disconnect failure")
    with pytest.raises(RuntimeError):
        app.shutdown()
    with pytest.raises(JournalError, match="closed"):
        app.journal.replay()
    app.executor.disconnect.side_effect = None


def test_journal_schema_failure_prevents_broker_construction(startup, tmp_path, monkeypatch):
    import sqlite3
    main, doubles = startup
    path = tmp_path / "future.db"
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA user_version=99")
    config = main.load_config()
    config["storage"] = {"journal_path": str(path)}
    monkeypatch.setattr(main, "load_config", lambda: config)
    with pytest.raises(JournalError):
        main.TradingEngine()
    doubles["OrderExecutor"].assert_not_called()


def test_failed_first_cli_cycle_still_shuts_down(monkeypatch):
    import main
    app = Mock()
    app.run_cycle.side_effect = RuntimeError("fixture first cycle failed")
    monkeypatch.setattr(main, "TradingEngine", Mock(return_value=app))
    with pytest.raises(RuntimeError):
        main.main()
    app.shutdown.assert_called_once()


@pytest.mark.parametrize("action", ["BUY", "HOLD"])
def test_large_debate_is_bounded_in_journal(engine, proposal_inputs, action):
    app = engine.instance
    proposal_inputs["decision"].action = action
    debate = Mock()
    debate.to_log_dict.return_value = {"transcript": "x" * 100000}
    app._execute_validated_trade(**proposal_inputs, debate_result=debate)
    payload = app.journal.replay()[0].event.payload
    assert payload["action"] == action
    assert len(payload["entry_sha256"]) == 64
    assert "debate" not in payload
    assert len(app.trade_log[0]["debate"]["transcript"]) == 100000
    if action == "BUY":
        app.executor.place_order.assert_called_once()
        assert payload["outcome"].startswith("EXECUTED")
    else:
        app.executor.place_order.assert_not_called()


def test_shutdown_preserves_primary_failure_when_journal_close_also_fails(engine, monkeypatch):
    app = engine.instance
    app.executor.disconnect.side_effect = RuntimeError("primary")
    with monkeypatch.context() as patch:
        patch.setattr(app.journal, "close", Mock(side_effect=OSError("secondary")))
        with pytest.raises(RuntimeError, match="primary"):
            app.shutdown()
    app.executor.disconnect.side_effect = None
