"""Single-owner SQLite journal and outbox. Replay never dispatches trading work."""

from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
import sqlite3
import threading

from pydantic import ValidationError

from core.events import EventEnvelope, RecordedEvent
from core.models import OrderIntent, RunRecord
from core.time_service import SystemClock, as_utc


class JournalError(RuntimeError):
    pass


def default_journal_path():
    # Keep an active SQLite database outside this OneDrive-backed source tree.
    base = Path(os.environ["LOCALAPPDATA"]) if os.environ.get("LOCALAPPDATA") else Path.home() / ".local/state"
    return base / "AITradingAgent" / "journal.db"


_DDL = (
    "CREATE TABLE schema_info(version INTEGER PRIMARY KEY CHECK(version=1))",
    "CREATE TABLE runs(id TEXT PRIMARY KEY, mode TEXT NOT NULL, document TEXT NOT NULL)",
    "CREATE TABLE intents(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), proposal_id TEXT NOT NULL, document TEXT NOT NULL)",
    """CREATE TABLE events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL UNIQUE, run_id TEXT NOT NULL REFERENCES runs(id),
        source TEXT NOT NULL, source_sequence INTEGER NOT NULL,
        causation_id TEXT REFERENCES events(event_id), intent_id TEXT REFERENCES intents(id),
        document TEXT NOT NULL, recorded_at TEXT NOT NULL,
        UNIQUE(run_id,source,source_sequence))""",
    "CREATE TABLE outbox(sequence INTEGER PRIMARY KEY REFERENCES events(sequence))",
)
_COLUMNS = {
    "schema_info": ("version",), "runs": ("id", "mode", "document"),
    "intents": ("id", "run_id", "proposal_id", "document"),
    "events": ("sequence", "event_id", "run_id", "source", "source_sequence", "causation_id", "intent_id", "document", "recorded_at"),
    "outbox": ("sequence",),
}
_IMMUTABLE = ("schema_info", "runs", "intents", "events")


def _trigger_sql(table, operation):
    return f"CREATE TRIGGER immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable journal record'); END"


class Journal:
    def __init__(self, path, *, clock=None):
        self.path = Path(path).resolve()
        self.clock = clock or SystemClock()
        self._lock = threading.RLock()
        self._closed = False
        self._connection = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.path, isolation_level=None, timeout=5,
                                               check_same_thread=False)
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._initialize_schema()
            self._connection.execute("PRAGMA journal_mode=DELETE")
            self._connection.execute("PRAGMA synchronous=FULL")
        except (OSError, sqlite3.Error, JournalError) as error:
            self.close()
            raise JournalError("Journal open/schema validation failed") from error

    def _initialize_schema(self):
        db = self._connection
        db.execute("BEGIN IMMEDIATE")
        try:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if version == 0 and not tables:
                for statement in _DDL:
                    db.execute(statement)
                db.execute("INSERT INTO schema_info VALUES(1)")
                for table in _IMMUTABLE:
                    for operation in ("UPDATE", "DELETE"):
                        db.execute(_trigger_sql(table, operation))
                db.execute("PRAGMA user_version=1")
            elif version != 1 or tables != set(_COLUMNS):
                raise JournalError("Unsupported or unrecognized journal schema")
            self._verify_schema()
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def _verify_schema(self):
        db = self._connection
        expected = list(_DDL) + [_trigger_sql(t, op) for t in _IMMUTABLE for op in ("UPDATE", "DELETE")]
        # Compare the definitions, not merely names or the integrity of current rows.
        actual = {sql for (sql,) in db.execute("SELECT sql FROM sqlite_master WHERE substr(name,1,7) != 'sqlite_'")}
        if set(expected) != actual:
            raise JournalError("Journal schema definitions do not match version 1")
        if db.execute("SELECT version FROM schema_info").fetchall() != [(1,)]:
            raise JournalError("Invalid schema metadata")
        for table, columns in _COLUMNS.items():
            if tuple(r[1] for r in db.execute(f"PRAGMA table_info({table})")) != columns:
                raise JournalError("Incomplete journal schema")
        triggers = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        if not {f"immutable_{table}_{op}" for table in _IMMUTABLE for op in ("UPDATE", "DELETE")} <= triggers:
            raise JournalError("Journal immutability triggers missing")
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise JournalError("Journal integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise JournalError("Journal reference integrity failed")

    def _ensure_open(self):
        if self._closed:
            raise JournalError("Journal is closed")

    @contextmanager
    def _transaction(self):
        with self._lock:
            self._ensure_open()
            if self._connection.in_transaction:
                raise JournalError("Nested journal transactions are not supported")
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield self._connection
                self._connection.execute("COMMIT")
            except BaseException as error:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                if isinstance(error, sqlite3.Error):
                    raise JournalError("Journal transaction rejected") from error
                raise

    @staticmethod
    def _snapshot(model, cls):
        # model_copy and nested mutable dicts must not bypass validation.
        return cls.model_validate(model.model_dump(mode="python"))

    def commit(self, *, run=None, intent=None, events=()):
        try:
            run = self._snapshot(run, RunRecord) if run is not None else None
            intent = self._snapshot(intent, OrderIntent) if intent is not None else None
            events = [self._snapshot(e, EventEnvelope) for e in events]
        except (ValidationError, AttributeError) as error:
            raise JournalError("Invalid journal record") from error
        recorded_at = as_utc(self.clock.now_utc()).isoformat()
        with self._transaction() as db:
            if run is not None:
                db.execute("INSERT INTO runs VALUES(?,?,?)", (str(run.run_id), run.mode.value, run.model_dump_json()))
            if intent is not None:
                self._check_run(db, intent.run_id, intent.mode)
                db.execute("INSERT INTO intents VALUES(?,?,?,?)", (str(intent.intent_id), str(intent.run_id), str(intent.proposal_id), intent.model_dump_json()))
            for event in events:
                self._check_run(db, event.run_id, event.mode)
                if event.intent_id is not None:
                    parent = db.execute("SELECT run_id,proposal_id FROM intents WHERE id=?", (str(event.intent_id),)).fetchone()
                    if parent != (str(event.run_id), str(event.proposal_id)):
                        raise JournalError("Event intent/proposal does not belong to its run")
                if event.causation_id is not None:
                    parent = db.execute("SELECT run_id FROM events WHERE event_id=?", (str(event.causation_id),)).fetchone()
                    if parent != (str(event.run_id),):
                        raise JournalError("Causation must precede event within the same run")
                source_sequence = db.execute("SELECT COALESCE(MAX(source_sequence),0)+1 FROM events WHERE run_id=? AND source=?", (str(event.run_id), event.source)).fetchone()[0]
                cursor = db.execute("INSERT INTO events(event_id,run_id,source,source_sequence,causation_id,intent_id,document,recorded_at) VALUES(?,?,?,?,?,?,?,?)", (
                    str(event.event_id), str(event.run_id), event.source, source_sequence,
                    str(event.causation_id) if event.causation_id else None,
                    str(event.intent_id) if event.intent_id else None, event.model_dump_json(), recorded_at))
                db.execute("INSERT INTO outbox VALUES(?)", (cursor.lastrowid,))

    @staticmethod
    def _check_run(db, run_id, mode):
        row = db.execute("SELECT mode FROM runs WHERE id=?", (str(run_id),)).fetchone()
        if row != (mode.value,):
            raise JournalError("Missing run or mismatched execution mode")

    def _get(self, table, identity, cls):
        with self._lock:
            self._ensure_open()
            try:
                row = self._connection.execute(f"SELECT document FROM {table} WHERE id=?", (str(identity),)).fetchone()
                return cls.model_validate_json(row[0]) if row else None
            except (sqlite3.Error, ValidationError) as error:
                raise JournalError("Journal record unreadable") from error

    def get_run(self, run_id):
        return self._get("runs", run_id, RunRecord)

    def get_intent(self, intent_id):
        return self._get("intents", intent_id, OrderIntent)

    def _read_events(self, after_sequence=0, limit=1000, pending=False):
        if type(after_sequence) is not int or after_sequence < 0 or type(limit) is not int or not 1 <= limit <= 10000:
            raise ValueError("Invalid replay cursor/limit")
        with self._lock:
            self._ensure_open()
            join = " JOIN outbox o ON o.sequence=e.sequence" if pending else ""
            try:
                rows = self._connection.execute(f"SELECT e.sequence,e.source_sequence,e.recorded_at,e.document FROM events e{join} WHERE e.sequence>? ORDER BY e.sequence LIMIT ?", (after_sequence, limit)).fetchall()
                return [RecordedEvent(sequence=seq, source_sequence=source_seq,
                                      recorded_at=datetime.fromisoformat(stamp),
                                      event=EventEnvelope.model_validate_json(document))
                    for seq, source_seq, stamp, document in rows]
            except (sqlite3.Error, ValueError) as error:
                raise JournalError("Journal replay unreadable") from error

    def replay(self, after_sequence=0, limit=1000):
        return self._read_events(after_sequence, limit)

    def pending(self, limit=1000):
        return self._read_events(limit=limit, pending=True)

    def acknowledge(self, event_id):
        with self._transaction() as db:
            row = db.execute("SELECT sequence FROM events WHERE event_id=?", (str(event_id),)).fetchone()
            if row is None:
                raise JournalError("Cannot acknowledge an unknown event")
            db.execute("DELETE FROM outbox WHERE sequence=?", row)

    def backup(self, destination):
        destination = Path(destination).resolve()
        reserved = False
        with self._lock:
            self._ensure_open()
            try:
                # Reserve destination exclusively: existing backups are never overwritten.
                with destination.open("xb"):
                    reserved = True
                target = sqlite3.connect(destination)
                try:
                    self._connection.backup(target)
                finally:
                    target.close()
            except (OSError, sqlite3.Error) as error:
                if reserved:
                    try:
                        destination.unlink()
                    except OSError:
                        pass
                raise JournalError("Journal backup failed; incomplete destination must not be used") from error

    def close(self):
        with self._lock:
            try:
                if not self._closed and self._connection is not None:
                    self._connection.close()
            finally:
                self._closed = True

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, *args):
        self.close()
