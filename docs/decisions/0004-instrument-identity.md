# 0004: Canonical identity at internal boundaries

Task 1.1 repairs identity without changing sizing, contract metadata or execution
authority. Existing configuration lists broker spellings while Gold selection,
correlation groups and risk overrides use canonical names. This can route Gold
twice and skip metal/oil policies. Existing strategy registry entries are strategy
IDs, not instrument IDs; their schema requires no migration.

Use an immutable explicit registry for the nine supported instruments. Configuration
lists canonical active instruments and an explicit canonical-to-broker map. Accept
documented legacy aliases on ingress, but never guess using substrings, casing or
suffix stripping. Reject unknown, duplicate and colliding names before broker I/O.
Retain inactive instruments in the registry so historical positions can be identified.
The configured broker map is a name mapping, not proof of equivalent contracts;
broker contract validation belongs to task 1.2.

Main, risk state, strategy signals and new memory writes use canonical identities.
Only feed/execution adapters use broker names at native calls; position results carry
both canonical pair and raw broker symbol. Unknown positions fail closed, never vanish
from exposure. Historical memory queries include exact canonical/configured/legacy
aliases without rewriting stored evidence. Global news retains its explicit GLOBAL
scope. Unknown memory identities fail closed; no fuzzy alias search.

Pinned reference comparison: Nautilus `f3c5702f5c82872b9981c7859d47b667d4bcb999`,
`crates/model/src/instruments/currency_pair.rs` separates `id: InstrumentId` from
`raw_symbol: Symbol`. Adapt this boundary, without importing its venue-qualified identifier types
or execution framework. TradingAgents stock tickers and AI Trading Desk UI labels
do not provide a suitable MT5 alias authority. No reference runtime dependency is
introduced. Alias-aware lookups do not address the remaining point-in-time and
population/evidence issues scheduled in task 7.1.

The registry's compatibility resolver accepts historical aliases for old configuration,
risk exposure and memory ingress. Native send/close/feed translation accepts canonical
IDs or current broker names only, never an old broker name after remapping. Native
position reads use only the current inverse map. Configured aliases must not use the
reserved GLOBAL news scope. Main resolves compatibility names before internal use.
The injected map is scoped to the engine's configured, verified account/server session;
no cross-account auto-discovery or global suffix lookup exists.
