# Local journal operations

The version-1 journal stores run metadata, draft intents, correlated events and
pending outbox entries. It provides ordered audit replay, not strategy resume,
financial state recovery, order submission or broker reconciliation.

`storage.journal_path: null` selects `%LOCALAPPDATA%/AITradingAgent/journal.db`
on Windows (otherwise `~/.local/state/AITradingAgent/journal.db`). An explicit
path must point to local storage outside cloud synchronization. Path selection
does not detect or enforce synchronization software exclusions.

Use `Journal(path).backup(destination)` through a context manager to obtain a
consistent snapshot. The destination must not exist. An unsuccessful backup can
leave an incomplete file; never restore it. Stop the engine before restoring a
verified snapshot to a new path and selecting that path in configuration. Opening
the snapshot validates schema metadata, integrity and foreign keys. Keep the
original database until validation succeeds. No migration tool is supplied:
unknown, partial and newer schemas are refused without upgrading them.

`replay(after_sequence=0, limit=1000)` returns events in durable sequence order;
page using the last returned sequence. Wall-clock corrections cannot reorder
records. `pending()` reads the outbox; `acknowledge(event_id)` removes only its
pending marker and is idempotent for known events. Consumers must deduplicate
event IDs. There is no dispatcher, and replay must never submit broker orders.

Cycle start/completion/failure and decision hooks use injected UTC time. Existing
market feeds, risk day accounting and legacy scheduler timestamps are not migrated
in this foundation task. A decision commits before its JSON projection is written.
Projection failure leaves durable evidence but can leave JSON stale; there is no
automatic projection rebuild yet. If the journal itself is unavailable, a failure
event may also be impossible to persist; the original cycle exception propagates.
An abrupt process exit can leave a started run without a terminal event.

Decision events contain a bounded summary and SHA-256 digest of the full canonical
JSON entry (`sort_keys=True`, `ensure_ascii=False`, `allow_nan=False`, default JSON
separators). Full reasoning and debate transcripts remain in the legacy projection;
the digest supports correlation, not recovery of missing content. A failed backup
removes its newly reserved destination where possible; if removal also fails, the
remaining file is incomplete and must not be restored.

Decision hooks currently record the existing pipeline's outcome, including orders
already submitted by that pipeline. This is not write-ahead execution protection;
durable pre-submission intent and reconciliation belong to tasks 1.6–1.7.
