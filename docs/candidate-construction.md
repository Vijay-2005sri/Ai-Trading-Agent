# Candidate binding and construction

The strategy runner assigns a fresh UUID to each validated signal and uses the
registry key as its strategy identity. Original emitted names remain variant labels.
All seven strategy modules share `core.signals.TradeSignal`; validation at the
runner boundary rejects invalid prices, directions, confidence and geometry.
Equal-confidence signals have deterministic content-based ordering.

Each analysis path freezes the selected candidate before evidence collection and
prompt generation, then freezes its evidence before calling the LLM. Other signals
are context only. BUY/SELL responses must echo the selected candidate UUID,
instrument, registry strategy and direction. Missing or mismatched bindings produce
HOLD without risk sizing or submission. HOLD responses need no executable candidate;
provider-exhaustion HOLD records use the requested instrument.

The constructor uses the strategy's existing deterministic SL/TP levels, never the
LLM's suggested prices. Missing levels are rejected without synthetic fallback.
BUY entry rounds up, SL down and TP down to broker ticks; SELL entry rounds down,
SL up and TP up. Geometry and minimum reward/risk are checked again after rounding.
Risk, TradeRecord and observation prices use this constructed result. The source
entry is still a historical reference price, not a promised fill price.

New journal decisions carry source candidate geometry, variant, rounded geometry,
recomputed reward/risk, tick size, metadata observation time, revision and evidence
digest. Full LLM advisory prices remain labeled in the legacy JSON projection.
Entry TradeRecords require candidate UUID, strategy and metadata/evidence fingerprints.
The executor refreshes metadata and rejects revision changes rather than silently
re-rounding. Closes use current metadata without requiring the original entry revision.

Trade memory queries require exact registry strategy identity plus instrument aliases.
Old variant-labeled records are preserved but are not inferred into a strategy's
statistics. They can result in cold-start until explicit migration in task 7.1.
Other relevance/as-of grounding limitations remain pending that task.

Construction and provenance checks are not an unforgeable execution capability:
TradeRecord remains mutable and a trusted direct caller can copy provenance fields.
Full request binding, quote drift, stops/freeze constraints and margin checks remain
task 1.5; monetary sizing remains 1.4. Durable order intents remain 1.6. Strategy
detector correctness, closed-bar assumptions and source timestamp migration are
not certified by these construction tests.
