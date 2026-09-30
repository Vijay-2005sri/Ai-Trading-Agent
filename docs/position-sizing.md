# Account-currency position sizing

Task 1.4 replaces fixed and winning-streak lots with a monetary stop-loss
estimate. The shared gate supplies the constructed entry/stop and fresh verified
instrument snapshot. The risk engine derives the budget from equity, configured
risk fraction and daily drawdown multiplier. It divides that budget by the
per-lot stop estimate plus the configured per-lot cost allowance, floors volume
to the broker step, and rejects an unaffordable minimum. It checks the final
estimated loss against the budget after applying broker volume caps.

For example, 1,000 account-currency units at 1% risk gives a budget of 10.
A per-lot stop estimate of 100 and allowance of 10 gives raw volume 0.0909...
With a 0.01 step, volume is 0.09 and the total estimate is 9.90.

`risk.sizing_cost_allowance_per_lot` represents estimated fees/slippage per lot.
When nonzero, `risk.sizing_cost_currency` must match the observed account currency.
The shipped zero allowance reserves no costs; it is not broker fee evidence.
`high_capital_threshold` uses account-currency units, not an assumed USD balance.
The Silver override is removed. Old winning-streak fields have no sizing effect;
the legacy state file retains only same-day equity continuity for this phase.

Decision JSON, journal events and new trade records preserve budget, raw/final
volume, estimated loss, allowance, currency and metadata revision. Static contract
tables cannot supply sizing; the historical `calculate_lot_size` helper now rejects.

Supported calculation modes use the broker's losing tick value as an estimate.
Unsupported modes reject pending a broker P/L calculator. Quote-time repricing,
margin, aggregate directional volume limits, durable risk reservations and restart
reconciliation remain later tasks. Stops and cost allowances do not guarantee
realized loss during gaps, slippage or exchange-rate changes. Live remains disabled.

See [ADR 0007](decisions/0007-account-currency-sizing.md) for reference comparisons.
