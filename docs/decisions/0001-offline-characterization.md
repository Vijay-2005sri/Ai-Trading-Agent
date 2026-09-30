# 0001: Offline characterization before foundation changes

Accepted for task 0.1 following roadmap approval. Scope: test infrastructure only.

`TradingEngine()` eagerly connects MT5, initializes Chroma/embeddings and provider
clients, reads a repository-relative trade log and creates observation storage.
The real `RiskAgent` reads a repository-relative streak file. The dashboard reads
the same trade log; the strategy registry imports eligible classes on import.
Both active analysis branches already call `_execute_validated_trade`.

Keep production constructors and interfaces unchanged in this task. Patch external
constructors at the orchestration module boundary with autospecced doubles, then
run the actual constructor and shared gate method. Redirect repository-relative
paths to temporary directories before construction. Keep real risk/grounding,
observation logging, strategy loading and Flask routes in characterization tests.
Do not use `__new__` to bypass the constructor we need to characterize.

Reference: TradingAgents revision
`8b22d43d01d9ddda5d686d093d5385884622f3de`, `tests/conftest.py`, isolates
cache paths and blocks network access. Adapt the isolation pattern natively.
Its network exemption for integration-marked tests does not fit this baseline:
our normal suite has no network opt-out. Its credential handling and research
providers also do not cover MT5's native IPC, terminal launches or model downloads.
We therefore deny native MT5 entry points, model/client construction, Python
networking and process launches before collecting project tests. This is an
accidental-I/O guard for trusted tests, not a sandbox for hostile generated code.

Canonical local and future CI command:
`.\.venv\Scripts\python.exe -B scripts/test_offline.py -q`.
The wrapper disables third-party pytest plugin autoload before importing pytest.
Raw `pytest` is not an equivalent isolation guarantee: plugins can load before
our conftest hooks. See `tests/README.md` for setup and scoped lint commands.

Use a session-owned temporary tree for pytest and application writes, disable
bytecode/cache writes, disable dotenv loading, and blank provider/broker secrets
without reading `.env`. A Python audit hook rejects writes outside that tree and
network/process events. Guard exceptions derive from BaseException so existing
broad `except Exception` fallbacks cannot turn forbidden I/O into a passing test.
Tests intentionally probing guards must explicitly catch that exception.

Baseline coverage: constructor wiring; grounded HOLD, cold-start override, risk
veto, accepted mocked order and failed mocked order; strategy registry loading,
quarantine filters and actual synthetic OHLCV execution; Flask routes/history API;
guard self-tests. Preserve known defects in documentation rather than asserting
unsafe behavior as a permanent requirement or hiding failures with xfail.

No new runtime architecture, no trading mode change, no reference dependencies,
no speculative production refactor. Task 0.2 will introduce the actual mode guard;
the present suite does not certify live execution safety or strategy profitability.
