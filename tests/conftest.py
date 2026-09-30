"""Install guards before collection, then inject only external boundaries."""

from copy import deepcopy
from dataclasses import replace
import importlib
import json
import os
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest

from tests.offline_guard import WriteGuard, deny

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
_patches = pytest.MonkeyPatch()
_guard = None
_temporary = None


def pytest_configure(config):
    global _guard, _temporary
    _temporary = tempfile.TemporaryDirectory(prefix="trading-offline-tests-")
    config.option.basetemp = str(Path(_temporary.name) / "pytest")
    _patches.setattr(tempfile, "tempdir", _temporary.name)
    if sys.platform == "win32":
        # Python's Windows platform probe shells out to `ver` when WMI is
        # unavailable. Give dependencies factual local OS data without a shell.
        version = sys.getwindowsversion()
        host = platform.uname_result("Windows", "offline-tests", str(version.major),
                                     f"{version.major}.{version.minor}.{version.build}", "AMD64")
        _patches.setattr(platform, "uname", lambda: host)
        _patches.setattr(platform, "processor", lambda: "AMD64")
    for name, value in {
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1", "ANONYMIZED_TELEMETRY": "False",
        "PYTHON_DOTENV_DISABLED": "1", "TOKENIZERS_PARALLELISM": "false",
        "HF_HOME": str(Path(_temporary.name) / "huggingface"),
    }.items():
        _patches.setenv(name, value)
    for name in list(os.environ):
        if name.endswith("_API_KEY") or name.startswith("MT5_") or name in {
            "HF_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TRADING_MODE"
        }:
            _patches.delenv(name, raising=False)

    # Block Python networking before importing third-party libraries.
    for name in ("connect", "connect_ex", "sendto", "bind"):
        _patches.setattr(socket.socket, name, deny)
    _patches.setattr(socket, "getaddrinfo", deny)
    _patches.setattr(socket, "create_connection", deny)
    # urllib3 probes IPv6 by binding at import. No network capability is needed
    # by this suite; prevent the probe without allowing any bind operations.
    _patches.setattr(socket, "has_ipv6", False)
    _patches.setattr(subprocess, "Popen", deny)
    _patches.setattr(os, "system", deny)
    for name in dir(os):
        if name.startswith(("exec", "spawn")) and callable(getattr(os, name)):
            _patches.setattr(os, name, deny)
    if hasattr(os, "startfile"):
        _patches.setattr(os, "startfile", deny)
    _guard = WriteGuard(_temporary.name)
    _guard.install()

    import dotenv
    import MetaTrader5 as mt5
    _patches.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    for name in dir(mt5):
        if not name.startswith("_") and callable(getattr(mt5, name)):
            _patches.setattr(mt5, name, deny)

    # Import SDK definitions without constructing clients, stores or models.
    # These imports run under the same network/process/write guards as tests.
    import openai
    import chromadb
    from chromadb.utils import embedding_functions
    import transformers
    import sentence_transformers
    import huggingface_hub
    import tavily
    import ddgs
    for module, names in (
        (openai, ("OpenAI", "AsyncOpenAI")),
        (chromadb, ("PersistentClient", "Client", "HttpClient")),
        (embedding_functions, ("SentenceTransformerEmbeddingFunction",)),
        (sentence_transformers, ("SentenceTransformer",)),
        (huggingface_hub, ("hf_hub_download", "snapshot_download")),
        (tavily, ("TavilyClient",)), (ddgs, ("DDGS",)),
    ):
        for name in names:
            _patches.setattr(module, name, deny)
    for model in (transformers.AutoTokenizer, transformers.AutoModelForSequenceClassification):
        _patches.setattr(model, "from_pretrained", deny)


def pytest_unconfigure(config):
    if _guard:
        _guard.active = False
    _patches.undo()
    if _temporary:
        _temporary.cleanup()


@pytest.fixture
def settings():
    import yaml
    return deepcopy(yaml.safe_load((ROOT / "config/settings.yaml").read_text()))


@pytest.fixture
def engine(tmp_path, monkeypatch, settings):
    """Run the real constructor with strict external collaborators and temp stores."""
    main = importlib.import_module("main")
    risk_module = importlib.import_module("agents.risk_agent")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    (tmp_path / "agents").mkdir()
    monkeypatch.setattr(risk_module, "__file__", str(tmp_path / "agents/risk_agent.py"))
    settings["rag"]["db_path"] = str(tmp_path / "chroma")
    settings["storage"] = {"journal_path": str(tmp_path / "journal.db")}
    settings["broker"].update(mode="demo_mt5", enable_demo_orders=True)
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "fixture-password")
    monkeypatch.setenv("MT5_SERVER", "Fixture-Server")
    monkeypatch.delenv("TRADING_MODE", raising=False)
    monkeypatch.setattr(main, "load_config", lambda: deepcopy(settings))

    doubles = {}
    for name in ("MT5DataFetcher", "WebSearchAgent", "TradingRAG", "LLMProvider", "OrderExecutor"):
        constructor = create_autospec(getattr(main, name), spec_set=True)
        monkeypatch.setattr(main, name, constructor)
        doubles[name] = constructor
    doubles["MT5DataFetcher"].return_value.connect.return_value = True
    doubles["MT5DataFetcher"].return_value.health_check.return_value = {
        "issues": [], "symbols_status": {s: True for s in settings["broker"]["symbols"]},
        "algo_trading_enabled": False, "account_info": None,
    }
    doubles["OrderExecutor"].return_value.connect.return_value = True
    doubles["TradingRAG"].return_value.get_db_stats.return_value = {"trade_records": 0, "news_records": 0}
    doubles["LLMProvider"].return_value.get_all_available_names.return_value = []
    doubles["LLMProvider"].return_value.get_active_provider_name.return_value = "offline-fixture"
    doubles["OrderExecutor"].return_value.get_account_equity.return_value = 10000.0
    from broker_mt5.instruments import InstrumentProvider
    from broker_mt5.symbols import SymbolRegistry
    from tests.instrument_fixtures import native_account, native_symbol
    specs = InstrumentProvider(symbol_registry=SymbolRegistry.from_config(settings),
                               account_reader=native_account, symbol_reader=native_symbol)
    doubles["OrderExecutor"].return_value.get_instrument_spec.side_effect = specs.get
    doubles["OrderExecutor"].return_value.place_order.return_value = {
        "success": True, "ticket": 123, "mode": "TEST", "reason": "offline broker fixture"
    }

    observation_class = main.ObservationLogger
    monitor_class = main.PerformanceMonitor
    (tmp_path / "monitoring").mkdir()
    registry_path = tmp_path / "registry.json"
    shutil.copyfile(ROOT / "strategy_library/registry.json", registry_path)
    monkeypatch.setattr(main, "ObservationLogger", lambda: observation_class(str(tmp_path / "observations")))
    monkeypatch.setattr(main, "PerformanceMonitor", lambda: monitor_class(str(tmp_path), str(registry_path)))
    instance = main.TradingEngine()
    # This fixture isolates the engine's lock/log behavior while preserving a
    # real deterministic RiskAgent decision behind the mocked broker boundary.
    from types import SimpleNamespace
    executor = instance.executor

    def prepare(**kwargs):
        spec = executor.get_instrument_spec(kwargs["pair"])
        direction = kwargs["direction"]
        entry = 1.1001 if direction == "BUY" else 1.0999
        return SimpleNamespace(
            pair=kwargs["pair"], direction=direction, entry_price=entry,
            stop_loss=kwargs["stop_loss"], take_profit=kwargs["take_profit"],
            bid=1.0999, ask=1.1001, quote_time=instance.clock.now_utc(),
            risk_reward=2.0, instrument=spec,
        )

    def authorize(preparation, record, *, confidence, is_trending=False):
        risk = instance.risk_agent.evaluate_trade(
            pair=preparation.pair, direction=preparation.direction,
            entry_price=preparation.entry_price, stop_loss=preparation.stop_loss,
            take_profit=preparation.take_profit, confidence=confidence,
            equity=executor.get_account_equity(), is_trending=is_trending,
            instrument_snapshot=preparation.instrument,
        )
        if risk.approved:
            record = replace(record, entry_price=preparation.entry_price,
                             lot_size=risk.adjusted_lot_size,
                             sizing_provenance=risk.sizing)
        return SimpleNamespace(approved=risk.approved, risk_result=risk,
                               trade_record=record if risk.approved else None,
                               token="fixture-approval" if risk.approved else None,
                               audit={"fixture": True})

    executor.prepare_trade.side_effect = prepare
    executor.authorize_trade.side_effect = authorize
    try:
        yield SimpleNamespace(instance=instance, constructors=doubles, root=tmp_path)
    finally:
        instance.shutdown()
@pytest.fixture
def decision():
    from agents.llm_provider import TradeDecision
    from uuid import uuid4
    return TradeDecision(
        candidate_id=uuid4(),
        action="BUY", pair="EURUSD", confidence=85, reasoning="Fixture evidence trade-1",
        suggested_sl=1.09, suggested_tp=1.12, strategy_used="EMA_Crossover",
        rag_sources_cited=["trade-1"], historical_win_rate=0.6, hallucination_risk="LOW",
    )


@pytest.fixture
def proposal_inputs(decision):
    from core.trade_constructor import bind_context
    signal = {"candidate_id": str(decision.candidate_id), "pair": "EURUSD", "strategy": "EMA_Crossover",
              "direction": "BUY", "confidence": 85, "entry_price": 1.10, "stop_loss": 1.09,
              "take_profit": 1.12, "reasoning": "Fixture structural levels", "timestamp": "fixture bar"}
    trades = {"is_cold_start": False, "total_found": 5, "doc_ids": ["trade-1"]}
    news = {"is_cold_start": True, "doc_ids": []}
    return dict(
        candidate_context=bind_context(signal, trades, news, 0.6, {"EMA_Crossover"}),
        symbol="EURUSD", decision=decision, strategy_signals=[signal], top_signal=signal,
        trade_recall=trades,
        news_recall=news,
        actual_win_rate=0.6, fundamental_report="Offline fixture; no news claim",
    )


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    from monitoring import dashboard as module
    path = tmp_path / "trade_log.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    monkeypatch.setattr(module, "TRADE_LOG_PATH", path)
    monkeypatch.setitem(module.app.config, "TESTING", True)
    return module


@pytest.fixture
def startup(monkeypatch, settings, tmp_path):
    import main
    settings["broker"].update(mode="demo_mt5", enable_demo_orders=True)
    settings["storage"] = {"journal_path": str(tmp_path / "journal.db")}
    monkeypatch.setattr(main, "load_config", lambda: deepcopy(settings))
    for key, value in {"MT5_LOGIN": "12345", "MT5_PASSWORD": "fixture-password", "MT5_SERVER": "Fixture-Server"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("TRADING_MODE", raising=False)
    doubles = {}
    for name in ("MT5DataFetcher", "OrderExecutor", "WebSearchAgent", "TradingRAG", "LLMProvider"):
        doubles[name] = create_autospec(getattr(main, name), spec_set=True)
        monkeypatch.setattr(main, name, doubles[name])
    doubles["OrderExecutor"].return_value.connect.return_value = True
    doubles["MT5DataFetcher"].return_value.connect.return_value = True
    doubles["MT5DataFetcher"].return_value.health_check.return_value = {
        "issues": [], "symbols_status": {}, "algo_trading_enabled": False,
    }
    monkeypatch.setattr(main.TradingEngine, "_load_trading_concepts", lambda _: "Fixture")
    return main, doubles
