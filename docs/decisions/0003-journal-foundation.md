# 0003: UTC records and a transactional local journal

Task 0.3 implements foundation seams, not an event-driven rewrite or broker recovery.

Current state is split between mutable JSON logs, streak state and Chroma memory.
The dashboard reads `trade_log.json`; both analysis callers share `_log_decision`.
Keep that interface/output, while adding journal hooks for cycle boundaries and
decisions. Strict version-1 records carry UUID identities and UTC timestamps.
Do not invent a market snapshot timestamp when the existing caller does not have
one. Optional snapshot/expiry fields remain absent until their owning stages supply
them. Intent records are storage only, never permission to execute or resend.

Use existing Pydantic 2 for strict schemas and stdlib SQLite for persistence. An
injected clock separates UTC wall time from monotonic timeout time. Normalize aware
timestamps to UTC, reject naive time and nonfinite/non-JSON data. Database records
are immutable; revalidate/copy records at persistence boundaries so mutation of a
Python payload dictionary cannot bypass validation.

SQLite uses foreign keys, explicit BEGIN IMMEDIATE transactions, FULL synchronous
writes and the rollback journal (DELETE mode). A local single-owner journal is the
initial deployment model, serialized by a connection lock. Do not use a database
actively synchronized by cloud software or shared over a network filesystem.
Run, intent, event and outbox inserts commit atomically. Duplicate IDs reject the
whole transaction. SQLite allocates total replay sequence and per-run/source
sequence within the same transaction; wall-clock ordering is not replay authority.
Event occurrence time and journal recording time remain distinct.

Outbox is a durable pending-event list with explicit acknowledgement, not a network
publisher or broker dispatcher. Replay/backup never call trading code. Delivery is
at least once; consumers must deduplicate event IDs. Acknowledgement means a caller
has completed its handling, not that a broker filled an order. No automatic resume
or migration from unversioned legacy financial state in this task.

Unknown/newer schema versions and unrecognized existing databases are rejected.
Version 1 requires exact stored table/trigger definitions as well as metadata,
column, integrity and foreign-key checks; same-name weakened definitions fail.
Use SQLite's backup API for a coherent snapshot; do not copy a running database
file. Tests cover reopen, interrupted writes, duplicate rollback, schema refusal,
ordered replay and pending-event recovery. Application persistence failures stop
the cycle; do not conceal failure behind an empty history or execute an outbox item.
Legacy JSON remains a separate compatibility projection, not transactionally atomic
with the database; document failures and preserve the durable journal.
Decision events use bounded summaries with a digest of the full entry, so large
debate transcripts do not exceed the journal payload limit after submission.

Reference comparison (source inspected, no runtime imports/copying):

- TradingAgents `8b22d43d01d9ddda5d686d093d5385884622f3de`,
  `tradingagents/graph/checkpointer.py`: SQLite per-analysis persistence. Adapt
  explicit ownership/close, not LangGraph state or ticker/date identity assumptions.
- NautilusTrader `f3c5702f5c82872b9981c7859d47b667d4bcb999`,
  `crates/event_store/src/entry.rs`: writer-assigned sequence is replay authority.
  Adopt sequence ordering, not the Rust/Redb platform, codecs or execution engine.
- AI Trading Desk `9dd59127ea785e3cf151f746a9b6c98835c9a2d8`, `web/bus.py`:
  structured publication but fire-and-forget failure behavior is unsuitable for
  mandatory trading audit. Keep durable local commit before optional future delivery.

Future schemas need explicit versioned migrations with backup and compatibility
tests. Risk budget semantics (1.8), executable proposal validation (1.3–1.5), durable
submission/reconciliation (1.6–1.7), and analysis resume/expiry (6.4) remain separate.
