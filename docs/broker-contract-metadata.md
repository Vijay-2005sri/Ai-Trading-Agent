# Broker contract metadata

`OrderExecutor.instruments.get(canonical_id)` returns a validated immutable snapshot
for the connected verified demo account. Its default cache lifetime is 60 seconds;
the provider constructor accepts a positive finite lifetime for independent consumers.
Entries are invalid at the exact expiry boundary. Cache state is in memory, protected
by a lock, and cleared on context change, failed read, reconnect or disconnect.

Snapshots include UTC acquisition time, canonical/native identities, account/server,
account and symbol currencies, account leverage/margin mode, separate profit/loss
tick values, price/volume increments and limits, stops/freeze, trade/execution/order/
filling modes, calculation mode and initial/maintenance/hedged margin metadata.
Decimals are normalized before SHA-256 content fingerprinting; observation time is
excluded so unchanged content keeps the same revision. No USD assumption is made.
Fingerprint input is sorted-key compact UTF-8 JSON with nonfinite values forbidden.
The current validator conservatively requires volume min/max to be exact multiples
of volume step from zero. A broker advertising a different grid is rejected pending
an explicit supported-grid policy; values are never rounded into apparent validity.

Every native send refreshes independently of cache age, including retries and closes.
Account identity/context is checked around metadata acquisition and again before
send. Invalid or unavailable metadata blocks that operation without stale/static
fallback. A missing economic field can also block a protective close. There is no
automatic bypass; protective-operation policy is a later task.

The temporary compatibility check accepts only the current market/IOC request when
the broker's trade direction, market-order, SL/TP and filling permissions support it.
CLOSEONLY permits closes, not entries. This is not the full execution gateway: quote
freshness/drift, price and lot geometry, monetary risk, free margin and lifecycle
reconciliation remain tasks 1.3–1.7. Native MT5 read/check/send operations cannot be
made atomic; externally switching a terminal can still race the final check.

The executor's in-memory order log includes the snapshot and revision at each send
attempt. This is provenance for subsequent integration, not a durable intent or
broker acknowledgement. Durable submission records remain task 1.6.

`config/contract_specs.py` is unverified reference data only. Its exact-name lookup
returns a copy marked `source=unverified_reference` and `execution_eligible=False`;
unknown names raise instead of receiving guessed contracts. Legacy calculation
helpers remain illustrative and must not supply an executable trade size.

See [ADR 0005](decisions/0005-broker-contract-metadata.md) for official MT5 semantics,
reference comparison and the chosen validation rules.
