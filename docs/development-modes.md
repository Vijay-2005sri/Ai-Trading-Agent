# Development execution modes

The default configuration is intentionally blocked at startup until the real
paper adapter exists. Running `main.py` prints `[BLOCKED] paper mode unavailable`
and exits with status 1 before creating broker, news, memory or provider objects.
It no longer reports simulated orders as successful trades.

| `broker.mode` | Current behavior |
|---|---|
| `paper` | Unavailable until task 2.4. No MT5 calls or synthetic fills/equity. |
| `historical` | Use the separate backtester. The online engine and MT5 executor reject this mode. |
| `demo_mt5` | Requires explicit `enable_demo_orders: true`, credentials and verified demo account identity. Intended for isolated development tests. |
| `live` | Always rejected during foundational development. There is no environment override. |

The shipped `config/settings.yaml` keeps `mode: paper`, `demo_mode: true` and
`enable_demo_orders: false`. Task 0.2 did not enable or run a demo session.

For a deliberately configured demo development profile, the executor requires a
positive integer `MT5_LOGIN`, nonempty `MT5_PASSWORD` and exact `MT5_SERVER`.
`MT5_PATH` is optional but must be nonempty if supplied. Broker account type must
equal MT5's DEMO constant; login and server must match the requested identity.
A demo-looking server name or environment flag is not verification.

Optional `TRADING_MODE` must exactly equal the YAML mode; remove it or change it
together with YAML when deliberately choosing a different profile. Optional
`MT5_DEMO` must be exactly `true`. YAML `demo_mode`, if present, must be boolean
`true`. False values, strings such as YAML `"true"`, missing modes and unknown
modes fail closed. These legacy flags no longer select live execution.

The old `OrderExecutor(demo_mode=True)` and `OrderExecutor(demo_mode=False)` calls
are rejected. A caller must explicitly select the demo mode and test opt-in:
`OrderExecutor(mode="demo_mt5", enable_demo_orders=True)`; construction alone
does not authorize orders. A successful `connect` must verify broker identity.
Entry, close and account/position reads revalidate the connected demo session;
each individual native send does so again immediately before submission.
Unavailable/mismatched account or position data invalidates the session and
requires explicit reconnect. Missing data is never a $10,000 balance or an empty
portfolio. Failed construction disconnects the partially initialized session.

This mode guard does not finish price/risk validation, safe retry classification,
reconciliation or the paper simulator. Demo forward qualification still belongs
to the later roadmap gates. MT5 cannot make a Python identity check and submission
atomic against an external terminal account change; operational isolation and the
later lifecycle work remain necessary.

Verification is entirely offline:

```powershell
.\.venv\Scripts\python.exe -B scripts/test_offline.py -q
.\.venv\Scripts\ruff.exe check --no-cache tests scripts/test_offline.py config/execution_mode.py broker_mt5/order_executor.py
```

See [ADR 0002](decisions/0002-development-modes.md) for the native design decision.
