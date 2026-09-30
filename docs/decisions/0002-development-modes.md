# 0002: Fail-closed development modes

Task 0.2, following task 0.1 and the approved roadmap. Live trading remains disabled.

The old `demo_mode=True` path fabricated a successful order and fixed $10,000
equity without a portfolio simulator. `demo_mode=False` accepted any connected
MT5 account, including live accounts. Both `place_order` and `close_order` call
`order_send`; the market-data adapter can reconnect MT5 independently.

Introduce explicit `historical`, `paper`, `demo_mt5`, and `live` modes. Reject
`live` unconditionally during foundational development. Recognize but reject
`paper` until task 2.4 supplies a real adapter; the current online engine/broker
adapter cannot run historical mode (the separate backtester remains available).
The shipped configuration selects unavailable paper with demo execution disabled,
so ordinary startup stops before broker/model/store initialization. This intentional
compatibility break is safer than relabeling old fake acknowledgements.

`demo_mt5` requires an explicit `enable_demo_orders: true` development test profile,
positive configured login, nonempty password/server and a verified broker account
whose trade mode is MT5's DEMO constant. Check requested login/server too: a server
name containing “demo” is not proof. A real or contest account, unknown account,
or identity mismatch must block. The existing `demo_mode`/`MT5_DEMO` flags, if
present, must be strict true values; false no longer selects live. An optional
`TRADING_MODE` environment setting must agree with YAML, never override it.

Connect and verify the executor before market-data/news/memory/provider creation.
After the data adapter connects, verify again because MT5 state is process-global.
Recheck mode, opt-in and actual account identity immediately before every send,
including entry retries and closing, and before account/position reads. Missing
account state or changed identity disconnects the executor logically and requires
explicit successful reconnect. Read failures raise instead of inventing account
values; connection failure never falls back to simulated success.

Reference: NautilusTrader revision
`f3c5702f5c82872b9981c7859d47b667d4bcb999`, `crates/system/src/config.rs`
(`KernelConfig.environment`) and `crates/system/src/kernel.rs` express a trading
environment explicitly. Adapt explicit environment
selection, not its service/kernel architecture or live-capable broker assumptions.
Our small MT5 adapter must verify actual account identity because process-global
terminal state can change outside our engine. No reference runtime or code copied.

Retain constructor compatibility parameters and existing method names; retired
ambiguous/unsafe calls fail with actionable errors. Do not change sizing, retry
classification, filling policy or order lifecycle in this task. Demo-only checks
are not account-bound atomic broker transactions: terminal state can still change
between a check and the native send. Lifecycle/reconciliation and operational
isolation remain later required work. No integration session is launched here;
tests use fake native responses under the offline harness.
