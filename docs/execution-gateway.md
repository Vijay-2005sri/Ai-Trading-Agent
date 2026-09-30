# Pre-trade execution gateway

Task 1.5 adds a mandatory current-quote check between candidate construction and
native demo submission. A `TradeRecord` alone cannot authorize an entry.

The shared engine path prepares a fresh executable quote, checks geometry and
broker constraints, then runs the final risk check under the engine lock. BUY
uses Ask; SELL uses Bid. Source stop and target remain structural levels. Spread,
entry drift, quote age, stop/freeze distance and reward/risk limits can veto the
trade. Missing or invalid broker information is a veto, not a fallback price.

The gateway estimates stop P/L through the broker in account currency, floors
volume within the risk agent's limit, and recalculates loss at the final size.
Configured cost allowance remains part of the budget. It checks margin and the
exact request with the broker before issuing a short-lived, single-use approval.
Approval binds the candidate, request, quote, account and contract metadata.
The final submission rejects changed or expired approval state and attempts the
native send once. Approval tokens are process-local and are not persisted as
reusable execution commands.

Protective closes resolve an actual native position by ticket and validate the
opposite side and requested reduction. A position ID on an arbitrary request
cannot bypass entry approval. Unavailable or changed positions block submission.

Broker checks are estimates and preconditions, not fill guarantees. A price or
account can change between the last local check and broker execution. Market
execution may not enforce a requested deviation as a strict fill-price bound.
No automatic retry follows an uncertain result. Durable intents, partial-fill
handling, UNKNOWN reconciliation and portfolio reservations remain Tasks 1.6–1.8.
The shipped paper configuration remains unavailable pending Task 2.4; live stays
disabled. Offline fixtures do not establish broker readiness or profitability.

See [ADR 0008](decisions/0008-quote-bound-execution-gateway.md) for the design and
reference comparison.
