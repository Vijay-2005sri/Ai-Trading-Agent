# Instrument identity and broker mapping

Internal decisions, strategy inputs, risk state and new memory records use these
canonical IDs. The shipped MT5 profile uses the following explicit native names:

| Canonical ID | Broker symbol |
|---|---|
| EURUSD | EURUSD |
| GBPUSD | GBPUSD |
| USDJPY | USDJPY |
| AUDUSD | AUDUSD |
| XAUUSD | GOLD.i# |
| XAGUSD | SILVER.i# |
| USOIL | OILCash# |
| BTCUSD | BTCUSD# |
| ETHUSD | ETHUSD# |

Select enabled instruments in `broker.symbols`; configure native names in
`broker.symbol_map`. Keep all nine mapping keys, even if only some instruments are
enabled. Changes require engine restart. Empty/partial mappings, ambiguous aliases,
unknown instruments and duplicate enabled identities stop startup before broker
construction. An omitted map retains the shipped profile for legacy callers;
an explicitly null map is invalid. Names are exact and case sensitive.

For a broker rename, change only the native value and retain the former value in
`broker.legacy_symbol_aliases`, for example `XAUUSD: ["previous-name"]` under that
mapping. Shipped aliases are retained automatically. Old aliases permit historical
lookups; native adapters accept only canonical IDs or current broker names. This
mapping must be checked against the configured account/server. It does not certify
contract economics, sizes or trading permissions; task 1.2 supplies broker specs.

Gold runs only in the primary debate path when enabled and reported available by
health checks. It is never included in secondary scanning. Unknown native positions
raise an error rather than being omitted or returned as an empty portfolio.

Memory lookup uses one exact `$in` filter over canonical/current/historical names.
Chroma returns each stored ID once; no alias fan-out or in-place rewrite occurs.
Trade queries keep the instrument filter even during cold start. News queries
include the explicit non-tradable `GLOBAL` scope. Existing evidence quality and
as-of limitations remain scheduled for task 7.1.

New decision audits and native position results preserve `broker_symbol` alongside
canonical `pair`. Old JSON and memory records remain readable in their original
form; they are not silently assigned today's broker spelling as historical fact.
