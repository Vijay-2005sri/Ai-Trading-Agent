# 0007: Size volume from verified account-currency stop loss

The current risk gate reports percentage risk but assigns fixed symbol lots and
increases Forex/Gold size after winning streaks. Replace that sizing with a
deterministic Decimal calculation using the validated `InstrumentSnapshot`
already refreshed by Task 1.2. Preserve its verified account currency, losing
tick value, tick size, volume minimum/maximum/step, and metadata revision.

For an entry price and protective stop:

```text
stop_ticks = abs(entry - stop) / tick_size
stop_loss_per_lot = stop_ticks * trade_tick_value_loss
loss_budget = equity * configured_risk_fraction * drawdown_multiplier
cost_allowance_per_lot = configured account-currency allowance
raw_volume = loss_budget / (stop_loss_per_lot + cost_allowance_per_lot)
volume = floor(raw_volume / volume_step) * volume_step
```

Reject malformed/non-finite or non-positive equity/prices/tick fields, invalid
directional stop geometry, unsupported calculation modes, a nonpositive loss
denominator, and volume below the broker minimum. Cap to the lower of broker
maximum and a nonzero broker volume limit, then floor again to the step. Recompute
the estimated stop loss plus configured costs at the final volume and reject if
it exceeds the budget. Never round a minimum up, substitute a static contract
table, or infer an FX conversion. `trade_tick_value_loss` is supplied in the
observed account currency; currency mismatch for a nonzero cost allowance blocks
sizing. A zero cost allowance explicitly reserves no fees or slippage. The
account-currency threshold in `settings.yaml` is interpreted in the verified
account currency, not as USD.

The symbol `volume_limit` is an aggregate directional exposure ceiling.
Treating it as a per-order ceiling only bounds this order and does not enforce
the aggregate across existing or pending positions. Aggregate enforcement is
deferred to the portfolio/gateway work in Tasks 1.5 and 1.8.

The daily drawdown reduction multiplies the monetary budget before deriving
volume. A winning streak has no effect on risk. Silver no longer has a symbol
override that could raise its budget above the configured account rule.
Risk checks reject invalid equity before mutating peak/day state. Sizing result
fields (budget, tick loss per lot, configured allowance, raw and normalized
volume, estimated total loss, currency, and contract revision) are bounded
audit provenance carried in the decision log and trade record.

## Reference comparison

Pinned Nautilus Trader
`f3c5702f5c82872b9981c7859d47b667d4bcb999`,
`crates/risk/src/sizing.rs` and `python/tests/unit/risk/test_sizing.py`, uses
Decimal fixed-risk sizing, commission allowance, hard caps and flooring to a
unit batch; its tests cover zero equity/FX rate and sizes that floor to zero.
Adapt those arithmetic and rejection properties. Its instrument multiplier and
exchange-rate inputs do not match this broker's contract model, so use the
account-currency losing tick value from the verified MT5 snapshot instead.

Pinned TradingAgents
`8b22d43d01d9ddda5d686d093d5385884622f3de` exposes position context and textual
sizing guidance, but no deterministic stop-risk-to-volume authority. Pinned
AI Trading Desk risk-management modules are debate agents, not quantity
calculators. Neither is used as a sizing implementation.

MT5 offers `order_calc_profit` for account-currency P/L estimation at a given
side, volume and pair of prices. Using it requires a broker-native calculation
at the pre-trade boundary; that lifecycle belongs to Task 1.5. Task 1.4 therefore
uses verified `trade_tick_size` and `trade_tick_value_loss` and labels the result
an estimate. Tick conversion, future exchange rates, gaps, and costs beyond the
configured allowance can make realized loss differ from this estimate.

This task does not add a final quote-time authorization, margin check, live
order-calculation call, portfolio reservation, or guarantee against gaps. Those
remain Tasks 1.5–1.8.

MT5 references: [symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants)
define losing tick value, tick size, and volume bounds; [Python
`order_calc_profit`](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py)
estimates account-currency P/L for the current trading environment; [native
`OrderCalcProfit`](https://www.mql5.com/en/docs/trading/ordercalcprofit) warns
that estimates may differ across market environments.
