# 0008: Quote-bound, one-shot demo execution approval

Task 1.4 sizes a structurally constructed trade at its signal entry. That result
can become unsafe before a market order reaches MT5: the executable side, spread,
stop distance, reward/risk, contract, equity, permissions, and margin may change.
The current executor reads a new quote after risk approval, sends it with stale
geometry, and retries requests after ambiguous outcomes. Introduce a mandatory
pre-trade gateway between the candidate and the one native send.

For a BUY, use the current Ask; for a SELL, use the current Bid. Require a
positive, non-crossed quote with a UTC timestamp no older than the configured
maximum and not in the future; independently bound monotonic time between quote
capture and approval. No `last`, bar, signal-entry, or cached-price fallback is
allowed. Enforce configured maximum spread and deviation from the candidate
reference in broker points. Recalculate directional entry/SL/TP geometry and
minimum reward/risk using the executable price. Check stop/freeze distance from
the current closing side (BUY uses Bid; SELL uses Ask), tick alignment, symbol
trade/order/filling modes, and account trade permissions.

Main calls preparation and then runs the final risk check under its shared lock
with fresh equity, executable entry, structural SL/TP, and current verified
metadata. The risk result is only an upper bound. During approval, use MT5
`order_calc_profit` for the selected side from executable entry to stop, reserve
the configured account-currency cost allowance, derive and floor a volume no
greater than the RiskAgent volume, and recheck the exact final volume's loss.
Require a finite adverse P/L and estimated loss plus costs within the final
drawdown-adjusted risk budget. Then estimate margin with `order_calc_margin`,
compare with current free margin, and require a successful `order_check` on the
exact request (`retcode == 0`). A passing order check is not a fill guarantee.

Only the gateway can issue a random, opaque, in-memory, one-shot token. It stores
the immutable request digest and bound trade identity, candidate/evidence IDs,
account login/server/currency/leverage/margin mode, metadata revision, quote,
and expiry. It starts the short monotonic expiry before broker calculations.
After those calls, it rechecks account, permissions, contract revision and quote;
immediately before send it repeats those checks, consumes the token atomically,
and sends the exact order-check request once. Changed records, requests, account,
contract or quote, expired/replayed/foreign tokens, `None`, exceptions and
non-success returns cannot be retried under the same approval. Reconnection
clears approvals. MT5 cannot atomically combine a final quote/account read with
`order_send`; that external race remains. Market Execution may fill at a different
price, and the request deviation field does not guarantee a maximum fill price
for every execution mode. Stop loss and margin checks are estimates, not a hard
cap on realized loss after a gap, slippage, or conversion change.

Protective close remains a separate reduction path. Resolve the native position
by ticket immediately before approval and again before send; require ticket,
canonical/raw symbol, account, original side and remaining volume to match.
Close volume must be positive, step-aligned and no greater than the actual
position; the native order side must reduce that position. A `position` field
alone never authorizes a request. Persistent lifecycle state, partial-fill
reconciliation and restart-safe idempotency remain Tasks 1.6–1.8.

## Reference comparison

Pinned Nautilus Trader
`f3c5702f5c82872b9981c7859d47b667d4bcb999`,
`crates/risk/src/engine/mod.rs`, selects Ask for BUY and Bid for SELL in
`market_order_price`, and applies quote-aware risk checks. Its market-price helper
can fall back to Last or bar close; this gateway deliberately rejects missing or
stale live quotes because no fallback price can authorize a market order here.
Its margin/risk architecture is broader and does not provide MT5 request tokens.

Pinned TradingAgents
`8b22d43d01d9ddda5d686d093d5385884622f3de` provides analysis state handoffs but
does not submit broker orders. Pinned AI Trading Desk modules focus on research,
debate, and portfolio UI rather than an MT5 execution gateway. Neither is used
as money-moving authority.

Official MT5 behavior informs the broker adapter: Python `symbol_info_tick`
provides bid/ask and `time_msc`; `order_calc_profit` returns signed P/L in the
current account currency; `order_calc_margin` estimates margin but omits current
orders and positions; `order_check` success is retcode zero and does not promise
execution. The gateway therefore uses margin calculation plus the exact request
check, and treats all three as bounded pre-trade estimates/checks.

## Verification

The offline suite covers stale/future/crossed quotes, drift and reward/risk
erosion, stop/freeze and fill constraints, account/terminal/contract/quote
changes at every approval boundary, broker P/L/margin/order-check failures,
one-use request-bound approvals, unknown native outcomes, and ticket-backed
protective close reductions. These are deterministic native doubles only; no
broker session, provider, or order was started.
