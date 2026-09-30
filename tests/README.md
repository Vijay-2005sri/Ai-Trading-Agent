# Offline baseline tests

Task 0.1 characterizes existing interfaces; it does not certify trading safety.
Install runtime dependencies from `requirements-runtime.txt`, then development
tools from `requirements-dev.txt` into the project `.venv`.

From the project root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B scripts/test_offline.py -q
.\.venv\Scripts\ruff.exe check --no-cache tests scripts/test_offline.py
```

Use this runner: it disables unrelated third-party pytest plugin autoload before
pytest starts, prevents bytecode writes, and fixes the repository working directory.
Pytest only discovers `tests/`; reference repositories are excluded. The conftest
installs guards before project test collection, including while it imports SDK
definitions. Python's Windows platform detection is supplied local version data
without launching its fallback shell. Tests and library temporary files use a
session-owned temporary directory that is cleaned up on exit.

The suite denies sockets, subprocess/exec/spawn, native MT5 callable entry points,
real provider/search clients, Chroma clients, embeddings and FinBERT loading.
It disables dotenv loading and removes inherited broker/provider credentials.
A Python audit hook denies filesystem writes outside its temporary tree.
`OfflineViolation` deliberately escapes the application's broad exception handlers.
There is no marker that enables network or broker access.

These are guards against accidental I/O by trusted tests, not an OS sandbox.
They do not govern Python/pytest startup before conftest, hostile plugins or
arbitrary native libraries that bypass Python auditing. Use the prescribed runner;
future untrusted generated-code tests require the separate sandbox in task 7.4.

The engine fixture runs the real constructor with autospecced external adapters,
real risk/grounding components, and temporary observation/monitor/log/streak paths.
Tests inspect both analysis methods' shared execution call, then exercise that
method's HOLD, cold-start, risk-veto and mocked success/failure behavior. Flask
uses an in-process test client; no server is started. Strategy tests run synthetic
OHLCV through all 12 real baseline strategies and verify registry filtering.

Known issues are deliberately not declared fixed or hidden behind xfail:

- Identity, candidate geometry and monetary sizing are covered through Task 1.4.
  Fresh-quote authorization and portfolio exposure controls remain (1.5–1.8).
- Paper mode remains unavailable until the actual simulator exists (2.4).
  Task 0.2 removed the old simulated-success acknowledgements.
- Static calendar and provider/model routing limitations remain (4 and 6).
- Failed orders may still produce PENDING observations; automatic close feedback
  is absent (1.7 and 7.2).
- Dashboard corruption handling, hardcoded health and unsafe text insertion
  require later work (8).
- Native MT5 execution, real broker connectivity, provider compatibility, model
  inference, strategy profitability and browser rendering are not tested here.

Task 0.2 adds mocked mode/account tests: strict YAML/environment agreement, live
denial, unavailable paper/historical paths, startup cleanup, exact demo identity,
account switching before each send/retry/close, unavailable reads, and a single
guarded native submission site. The engine baseline uses an explicit mocked demo
profile; the shipped default remains blocked paper mode. No test enables live.

The initial registry count assertion is intentionally a baseline contract. A
later approved strategy migration must update that expectation with its evidence.
