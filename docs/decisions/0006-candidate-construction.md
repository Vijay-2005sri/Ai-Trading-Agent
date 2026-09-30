# 0006: One frozen candidate and deterministic geometry

The existing gate mixes top-signal entry and evidence with arbitrary LLM strategy,
direction and suggested prices. Seven strategy files duplicate TradeSignal, and
some emit variant labels instead of their registered strategy ID. The unused legacy
analysis method also has a separate order path using LLM prices.

Use one shared signal dataclass; the registry runner owns canonical strategy IDs
and fresh candidate UUIDs, retaining original variant labels. Validate finite,
positive prices and BUY/SELL geometry before publishing candidates. Freeze the
selected top candidate and serialized evidence before the LLM call. Other signals
are context only. BUY/SELL must echo that candidate UUID, pair, strategy and side;
HOLD needs no executable candidate. Never infer a missing ID from strategy text.
Evidence is bound to this selection, not re-used for an LLM-selected alternative.
Trade memory retrieval and win-rate lookup use exact canonical strategy IDs and
instrument aliases together. Old emitted variant names are not guessed into a
strategy population: they remain stored but may produce cold-start until an explicit
evidence migration in 7.1. Runner ties break by registry ID, side, prices, source
timestamp and reasoning, not mutable registry iteration order or generated UUID.

Construct from the strategy's existing deterministic structural/indicator stop and
target levels. Reject absent levels; do not invent ATR, fixed-pip or LLM fallbacks.
Use broker tick size and Decimal arithmetic: BUY entry rounds up, SL down and TP
down; SELL entry down, SL up and TP up. Revalidate strict SL/entry/TP ordering and
minimum reward/risk after rounding. LLM price suggestions remain advisory and do
not enter risk sizing, execution records or observation prices.

The selected candidate/evidence envelope is immutable; dict callers are checked
against it at the shared gate. Carry candidate, strategy, evidence digest and
contract revision into audit/TradeRecord. All three analysis entrypoints route the
same gate, moving duplicate-path retirement forward from 1.9 because leaving that
path would bypass this task's geometry guarantees.

Reference comparison: Nautilus `f3c5702f5c82872b9981c7859d47b667d4bcb999`,
`crates/model/src/instruments/currency_pair.rs` validates positive increments and
their precision. Its typed records support separating validated data from raw
adapter output; adapt its Decimal/increment discipline, not order authority.
TradingAgents `8b22d43d01d9ddda5d686d093d5385884622f3de`,
`tradingagents/graph/trading_graph.py` identity context and state handoffs motivate
freezing a selected analysis context, but its generated trading
text cannot authorize prices. Desk debate labels are observability only. No
reference runtime dependencies are introduced.

This task does not repair strategy detectors, migrate bar timestamps, prove closed
bars, implement quote-time geometry checks or monetary sizing. Those remain 3.1,
2.1, 1.5 and 1.4. A constructed trade is not a final approval or submission token.
