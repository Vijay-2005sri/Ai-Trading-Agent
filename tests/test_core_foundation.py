"""Pure time/record contracts and disk-backed journal fault/replay tests."""

from contextlib import closing
from datetime import datetime, timedelta, timezone
import sqlite3
from uuid import uuid4

import pytest
from pydantic import ValidationError

from config.execution_mode import ExecutionMode
from core.events import EventEnvelope
from core.models import RunRecord, OrderIntent
from core.persistence import Journal, JournalError
from core.time_service import FakeClock, SystemClock

UTC = timezone.utc
NOW = datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC)


@pytest.fixture
def clock():
    return FakeClock(NOW)


@pytest.fixture
def run():
    return RunRecord(mode=ExecutionMode.DEMO_MT5, created_at=NOW, purpose="test")


def event(run, **kwargs):
    return EventEnvelope(run_id=run.run_id, mode=run.mode, source="test",
                         event_type="TestRecorded", occurred_at=NOW, **kwargs)


def test_clock_utc_day_boundary_and_monotonic(clock):
    start = clock.monotonic()
    clock.advance(timedelta(seconds=2))
    assert clock.now_utc() == datetime(2026, 10, 1, 0, 0, 1, tzinfo=UTC)
    assert clock.monotonic() - start == 2
    clock.set_wall_time(NOW)  # Wall-clock correction never reverses elapsed time.
    assert clock.monotonic() == start + 2
    with pytest.raises(ValueError):
        clock.advance(timedelta(seconds=-1))
    assert SystemClock().now_utc().utcoffset() == timedelta(0)


@pytest.mark.parametrize("bad", [datetime(2026, 1, 1), "2026-01-01", None])
def test_naive_or_untyped_timestamps_rejected(bad):
    with pytest.raises((ValidationError, ValueError)):
        RunRecord(mode=ExecutionMode.PAPER, created_at=bad, purpose="test")


def test_aware_time_is_normalized_and_expiry_checked():
    local = datetime(2026, 10, 1, 5, 29, 59, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    run = RunRecord(mode=ExecutionMode.PAPER, created_at=local, purpose="test")
    assert run.created_at == NOW and run.created_at.tzinfo == UTC
    for kwargs in (dict(expires_at=NOW), dict(market_snapshot_at=NOW + timedelta(seconds=1))):
        with pytest.raises(ValidationError):
            RunRecord(mode=ExecutionMode.PAPER, created_at=NOW, purpose="test", **kwargs)


@pytest.mark.parametrize("payload", [{"x": float("nan")}, {"x": [float("inf")]}, {"x": object()}, {1: "bad"}])
def test_payload_rejects_nonfinite_and_non_json(run, payload):
    with pytest.raises(ValidationError):
        event(run, payload=payload)


def test_schema_is_versioned_strict_and_roundtrips(run):
    item = event(run, payload={"confidence": 85, "reason": "fixture"})
    assert EventEnvelope.model_validate_json(item.model_dump_json()) == item
    assert item.event_id != event(run).event_id
    with pytest.raises(ValidationError):
        event(run, schema_version=2)
    with pytest.raises(ValidationError):
        event(run, unknown_field="no")
    with pytest.raises(ValidationError):
        item.event_type = "Changed"


def test_atomic_run_intent_event_outbox_reopens_and_replays(tmp_path, clock, run):
    path = tmp_path / "journal.db"
    intent = OrderIntent(run_id=run.run_id, proposal_id=uuid4(), created_at=NOW, mode=run.mode,
                         instrument_id="EURUSD", direction="BUY", request={"volume": 0.01})
    first = event(run, intent_id=intent.intent_id, proposal_id=intent.proposal_id)
    second = event(run, causation_id=first.event_id)
    with Journal(path, clock=clock) as journal:
        journal.commit(run=run, intent=intent, events=[first, second])
    with Journal(path, clock=clock) as journal:
        replay = journal.replay()
        assert [r.event.event_id for r in replay] == [first.event_id, second.event_id]
        assert [r.sequence for r in replay] == [1, 2]
        assert [r.source_sequence for r in replay] == [1, 2]
        assert replay[0].recorded_at == NOW
        assert journal.get_run(run.run_id) == run
        assert journal.get_intent(intent.intent_id) == intent
        assert journal.pending() == replay
        journal.acknowledge(first.event_id)
        assert journal.pending() == [replay[1]]
        assert journal.replay(after_sequence=1) == [replay[1]]


def test_duplicate_rolls_back_every_record_and_outbox(tmp_path, clock, run):
    first = event(run)
    with Journal(tmp_path / "journal.db", clock=clock) as journal:
        journal.commit(run=run, events=[first])
        another = RunRecord(mode=run.mode, created_at=NOW, purpose="other")
        with pytest.raises(JournalError):
            journal.commit(run=another, events=[event(another), first])
        assert journal.get_run(another.run_id) is None
        assert len(journal.replay()) == len(journal.pending()) == 1


def test_mid_transaction_failure_is_rolled_back(tmp_path, clock, run):
    path = tmp_path / "journal.db"
    with Journal(path, clock=clock) as journal:
        # Inject an actual SQLite failure after run/event insertion, at outbox.
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TRIGGER deny_outbox BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT, 'fixture'); END")
        with pytest.raises(JournalError):
            journal.commit(run=run, events=[event(run)])
        assert journal.get_run(run.run_id) is None
        assert journal.replay() == journal.pending() == []


def test_missing_run_and_cross_mode_event_rejected(tmp_path, clock, run):
    with Journal(tmp_path / "journal.db", clock=clock) as journal:
        with pytest.raises(JournalError):
            journal.commit(events=[event(run)])
        wrong = event(run).model_copy(update={"mode": ExecutionMode.PAPER})
        with pytest.raises(JournalError):
            journal.commit(run=run, events=[wrong])
        assert journal.get_run(run.run_id) is None


def test_mutated_nested_payload_revalidated_before_write(tmp_path, clock, run):
    item = event(run, payload={"x": []})
    item.payload["x"].append(float("nan"))
    with Journal(tmp_path / "journal.db", clock=clock) as journal:
        with pytest.raises((ValidationError, JournalError)):
            journal.commit(run=run, events=[item])
        assert journal.replay() == []


def test_recording_order_is_not_wall_clock_order(tmp_path, clock, run):
    with Journal(tmp_path / "journal.db", clock=clock) as journal:
        journal.commit(run=run, events=[event(run)])
        clock.set_wall_time(NOW - timedelta(seconds=30))
        journal.commit(events=[event(run)])
        records = journal.replay()
        assert records[1].recorded_at < records[0].recorded_at
        assert records[1].sequence > records[0].sequence


def test_backup_preserves_committed_records_and_outbox(tmp_path, clock, run):
    backup = tmp_path / "backup.db"
    with Journal(tmp_path / "journal.db", clock=clock) as journal:
        journal.commit(run=run, events=[event(run)])
        journal.backup(backup)
        with pytest.raises(JournalError):
            journal.backup(backup)  # Never overwrite an existing backup.
    with Journal(backup, clock=clock) as restored:
        assert restored.get_run(run.run_id) == run
        assert len(restored.pending()) == 1


@pytest.mark.parametrize("unknown", [False, True])
def test_unrecognized_or_future_schema_is_not_overwritten(tmp_path, unknown):
    path = tmp_path / "unknown.db"
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE unrelated(value TEXT)")
        if unknown:
            db.execute("PRAGMA user_version=99")
    with pytest.raises(JournalError):
        Journal(path)
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='unrelated'").fetchone()


def test_database_records_are_immutable_and_ack_is_idempotent(tmp_path, run):
    path = tmp_path / "journal.db"
    first = event(run)
    with Journal(path) as journal:
        journal.commit(run=run, events=[first])
        with closing(sqlite3.connect(path)) as db:
            for statement in ("DELETE FROM events", "UPDATE runs SET mode='paper'", "DELETE FROM schema_info"):
                with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                    db.execute(statement)
        journal.acknowledge(first.event_id)
        journal.acknowledge(first.event_id)
        with pytest.raises(JournalError):
            journal.acknowledge(uuid4())
        assert len(journal.replay()) == 1 and journal.pending() == []


def test_causation_must_precede_event_and_belong_to_same_run(tmp_path, run):
    first = event(run)
    second = event(run, causation_id=first.event_id)
    with Journal(tmp_path / "journal.db") as journal:
        with pytest.raises(JournalError):
            journal.commit(run=run, events=[second, first])
        assert journal.get_run(run.run_id) is None
        journal.commit(run=run, events=[first])
        other = RunRecord(mode=run.mode, purpose="other", created_at=NOW)
        with pytest.raises(JournalError):
            journal.commit(run=other, events=[event(other, causation_id=first.event_id)])
        assert journal.get_run(other.run_id) is None


def test_concurrent_writers_allocate_unique_ordered_sequences(tmp_path, run):
    from concurrent.futures import ThreadPoolExecutor
    with Journal(tmp_path / "journal.db") as journal:
        journal.commit(run=run)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: journal.commit(events=[event(run)]), range(20)))
        rows = journal.replay()
        assert [r.sequence for r in rows] == list(range(1, 21))
        assert [r.source_sequence for r in rows] == list(range(1, 21))
        assert len(journal.pending()) == 20


def test_nested_transaction_rejected_without_committing_outer_work(tmp_path, run):
    with Journal(tmp_path / "journal.db") as journal:
        with pytest.raises(JournalError, match="Nested"):
            with journal._transaction():
                journal.commit(run=run)
        assert journal.get_run(run.run_id) is None


def test_payload_size_depth_and_schema_boolean_rejected(run):
    deep = {}
    for _ in range(20):
        deep = {"nested": deep}
    for payload in (deep, {"text": "x" * 65537}):
        with pytest.raises(ValidationError):
            event(run, payload=payload)
    with pytest.raises(ValidationError):
        event(run, schema_version=True)


def test_same_named_but_weakened_trigger_is_refused(tmp_path):
    path = tmp_path / "journal.db"
    with Journal(path):
        pass
    with closing(sqlite3.connect(path)) as db:
        db.execute("DROP TRIGGER immutable_events_DELETE")
        db.execute("CREATE TRIGGER immutable_events_DELETE BEFORE DELETE ON events BEGIN SELECT 1; END")
    with pytest.raises(JournalError):
        Journal(path)


def test_additional_schema_behavior_is_refused_without_modification(tmp_path):
    path = tmp_path / "journal.db"
    with Journal(path):
        pass
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TRIGGER extra BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'extra'); END")
    with pytest.raises(JournalError):
        Journal(path)
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='extra'").fetchone() == ("extra",)


def test_failed_backup_removes_reserved_destination_and_can_retry(tmp_path, monkeypatch):
    from unittest.mock import Mock
    import core.persistence as module
    path = tmp_path / "backup.db"
    with Journal(tmp_path / "journal.db") as journal:
        connect = module.sqlite3.connect
        monkeypatch.setattr(module.sqlite3, "connect", Mock(side_effect=sqlite3.OperationalError("fixture")))
        with pytest.raises(JournalError):
            journal.backup(path)
        assert not path.exists()
        monkeypatch.setattr(module.sqlite3, "connect", connect)
        journal.backup(path)
        with Journal(path):
            pass
