# 0005: Broker-observed contract metadata

The static `config/contract_specs.py` table is not read by the current executor or
risk engine. Its claim of verified live economics and its generic unknown-symbol
fallback are misleading. Preserve known entries as explicitly unverified reference
data; remove guessed fallback. Reference sizing helpers are not execution authority.

Add an immutable version-1 broker snapshot with canonical and native identity,
server/login/account currency, leverage/margin mode, UTC observed time and a
content fingerprint. Preserve separate profit/loss tick values, tick size/point,
digits, contract size, volume min/max/step/limit, stops/freeze, trade/execution/
filling/order/calculation modes and currency/margin metadata. Use finite Decimal
values from native numerics; reject missing, contradictory or invalid fields.
Zero stops/freeze, margin initial/maintenance/hedged and volume limit are valid
metadata, not missing values or proof that no margin is required.

An executor-owned provider reads through the existing verified-demo account guard,
checks account identity/context before and after symbol_info, and caches only valid
snapshots by server/login/native symbol. TTL uses injected monotonic time; wall time
provides audit provenance and backward corrections invalidate cache hits. Context
changes and failed refreshes discard cached data. Every native send (including
retry and close) forces a fresh read; there is no stale or static fallback.

The current market/IOC request is checked against observed trade, execution, filling
and order permissions before send. Disabled trading blocks sends; CLOSEONLY permits
protective closes but not entries. This does not implement monetary sizing,
fresh-quote geometry, free-margin/order_calc_margin checks or reconciliation;
those remain 1.4–1.7. Full strict metadata may also block a close on missing economics;
do not silently bypass it. A separately validated protective policy belongs to 1.9.
Snapshot validation is not broker permission or an atomic account/read/send lock.

Reference comparison: pinned Nautilus `f3c5702f5c82872b9981c7859d47b667d4bcb999`,
`crates/model/src/instruments/currency_pair.rs` separates raw identity, price/size
increments and limits. Adapt validated value records without importing its model
or assuming venue rules match MT5. TradingAgents/Desk do not supply native MT5
contract validation. No reference runtime code or dependencies are introduced.

Official semantics checked 2026-09-30:
- https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants
- https://www.mql5.com/en/docs/python_metatrader5/mt5accountinfo_py

Filling mode is a symbol bitmask, not the ORDER_FILLING enum. IOC is allowed for
Request/Instant execution; for Market/Exchange it requires the IOC symbol flag.
Zero initial margin is valid for formula-based contracts; zero maintenance uses
initial margin according to MT5 semantics. Do not treat either as zero account risk.
