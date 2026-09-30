"""
=============================================================================
MAIN ORCHESTRATION LOOP — Fully Integrated AI Trading System
=============================================================================
Complete data flow every cycle:

┌──────────────────────────────────────────────────────────────────────────┐
│                        EVERY CANDLE CYCLE (15 min)                       │
│                                                                          │
│  ┌──────────────┐   ┌───────────────┐   ┌────────────────────────────┐  │
│  │ data_feeds/  │   │ strategy_     │   │ rag_system/                │  │
│  │              │   │ library/      │   │                            │  │
│  │ MT5 OHLCV ──┼──▶│ Run 12        │   │ 1. Recall similar trades   │  │
│  │ Web News ───┼──▶│ strategies ───┼──▶│ 2. Recall similar news     │  │
│  │ FinBERT ────┼──┘ │ Rank signals  │   │ 3. Get verified win rate   │  │
│  └──────────────┘   └───────────────┘   └────────────┬───────────────┘  │
│                                                       │ Grounded Context  │
│                                          ┌────────────▼───────────────┐  │
│                                          │ agents/llm_provider.py     │  │
│                                          │ LLM + GROUNDING CONTRACT   │  │
│                                          │ → Must cite RAG sources    │  │
│                                          └────────────┬───────────────┘  │
│                                                       │ TradeDecision     │
│                                          ┌────────────▼───────────────┐  │
│                                          │ GroundingValidator         │  │
│                                          │ Deterministic check:       │  │
│                                          │ - Sources cited?           │  │
│                                          │ - Win rate matches DB?     │  │
│                                          │ - Low hallucination risk?  │  │
│                                          └────────────┬───────────────┘  │
│                                                       │ HOLD or continue  │
│                                          ┌────────────▼───────────────┐  │
│                                          │ agents/risk_agent.py       │  │
│                                          │ - Drawdown checks          │  │
│                                          │ - Lot size calculation     │  │
│                                          │ - Trade count limits       │  │
│                                          └────────────┬───────────────┘  │
│                                                       │ APPROVED/VETOED   │
│  ┌──────────────┐   ┌───────────────┐                │                   │
│  │ monitoring/  │◀──│ broker_mt5/   │◀───────────────┘                   │
│  │ Dashboard    │   │ order_executor│                                    │
│  │ XAI Logs     │   │ Place order   │                                    │
│  └──────────────┘   └───────────────┘                                    │
│                                                                          │
│  ◀── After trade closes: memorize outcome in RAG DB ──────────────────── │
└──────────────────────────────────────────────────────────────────────────┘
=============================================================================
"""

import os
import sys
import hashlib
from broker_mt5.symbols import SymbolRegistry, SymbolError
from uuid import uuid4
from core.events import EventEnvelope
from core.models import RunRecord
from core.trade_constructor import (bind_context, candidate_from_signal, evidence_json,
                                    validate_binding, construct_trade, ConstructionError)
from core.persistence import Journal, JournalError, default_journal_path
from core.time_service import SystemClock

# Force UTF-8 encoding on Windows to prevent emoji crashes (cp1252 can't handle them)
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

import time
import json
import yaml
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from config.execution_mode import DevelopmentPolicy, ModeError, demo_credentials_from_environment

# ── Load environment ────────────────────────────────────────────────────────
load_dotenv()

# ── Suppress HuggingFace warnings ───────────────────────────────────────────
# HF_TOKEN is loaded from .env by load_dotenv() above.
# These env vars suppress noisy telemetry/auth warnings at import time.
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ── Project imports ─────────────────────────────────────────────────────────
from data_feeds.mt5_market_data import MT5DataFetcher
from data_feeds.web_search import WebSearchAgent
from data_feeds.news_sentiment import NewsSentimentAnalyzer
from data_feeds.economic_calendar import EconomicCalendar

from strategy_library.strategy_master import run_all_strategies, get_strategy_summary, STRATEGY_REGISTRY
from data.observation_logger import ObservationLogger
from monitoring.performance_monitor import PerformanceMonitor

from agents.llm_provider import LLMProvider, TradeDecision
from agents.risk_agent import RiskAgent, TradeRecord
from agents.debate_arena import DebateArena

from rag_system.memory_engine import TradingRAG
from rag_system.grounding_validator import GroundingValidator

from broker_mt5.order_executor import OrderExecutor
from broker_mt5.execution_gateway import GatewayError


# ===========================================================================
# CONFIGURATION
# ===========================================================================

def load_config() -> dict:
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        raise ModeError("Cannot read valid config/settings.yaml; startup blocked") from None


# ===========================================================================
# THE BRAIN — Grounded Executive Agent
# ===========================================================================

class TradingBrain:
    """
    The central intelligence. Combines RAG verified memory + LLM reasoning.

    Unlike a raw LLM call, every decision here is:
      1. Informed by verified ChromaDB history
      2. Forced to cite sources via GROUNDING_CONTRACT
      3. Verified by GroundingValidator after the response
    """

    SYSTEM_CONTEXT = (
        "You are the Executive AI of a quantitative hedge fund. You operate as a specialized Trading Gem.\n"
        "You receive verified data from four sources:\n"
        "  1. TRADING CONCEPTS KNOWLEDGE: Your fundamental understanding of market structure.\n"
        "  2. QUANT REPORT: Technical signals from our trading strategies.\n"
        "  3. FUNDAMENTAL REPORT: Live news headlines + FinBERT sentiment scores.\n"
        "  4. STRATEGY KNOWLEDGE: Summary of how the strategies operate.\n"
        "The RAG context above this message is your SOURCE OF TRUTH. "
        "It contains verified historical trades and news from our database. "
        "Rules:\n"
        "  - Actively apply your TRADING CONCEPTS KNOWLEDGE to evaluate if the QUANT REPORT makes logical sense.\n"
        "  - If strategies strongly disagree or the setup invalidates the concepts → HOLD.\n"
        "  - If RAG win rate < 50% → prefer HOLD or very low lot size.\n"
        "  - If cold-start (no RAG history) → HOLD (safety first).\n"
        "  - Always prioritize capital preservation over profit."
    )

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def evaluate(
        self,
        quant_report: str,
        fundamental_report: str,
        strategy_knowledge: str,
        concept_knowledge: str,
        rag_context: str,
        pair: str,
    ) -> TradeDecision:
        """
        Full grounded evaluation. RAG context is injected at the provider level
        via invoke_structured() which prepends the GROUNDING_CONTRACT.
        """
        base_prompt = (
            f"{self.SYSTEM_CONTEXT}\n\n"
            f"=== PAIR: {pair} ===\n\n"
            f"--- TRADING CONCEPTS KNOWLEDGE ---\n{concept_knowledge}\n\n"
            f"--- QUANT REPORT (Strategy Signals) ---\n{quant_report}\n\n"
            f"--- FUNDAMENTAL REPORT (News & Sentiment) ---\n{fundamental_report}\n\n"
            f"--- STRATEGY KNOWLEDGE ---\n{strategy_knowledge}\n\n"
            f"Based on ALL context (RAG verified history + above data), "
            f"what is your grounded trading decision for {pair}?"
        )

        try:
            decision = self.llm.invoke_structured(
                base_prompt=base_prompt,
                rag_context=rag_context,
                output_schema=TradeDecision
            )
            if decision.action == "HOLD":
                decision.pair = pair
            return decision

        except Exception as e:
            print(f"  [ERR] Brain evaluation failed: {e}")
            return TradeDecision(
                action="HOLD",
                pair=pair,
                confidence=0,
                reasoning=f"Brain error: {str(e)}. Defaulting to HOLD for safety.",
                suggested_sl=0.0,
                suggested_tp=0.0,
                strategy_used="ERROR_FALLBACK",
                rag_sources_cited=[],
                historical_win_rate=0.0,
                hallucination_risk="HIGH"
            )

    def evaluate_with_debate(
        self,
        quant_report: str,
        fundamental_report: str,
        strategy_knowledge: str,
        concept_knowledge: str,
        rag_context: str,
        pair: str,
        debate_arena: DebateArena,
    ):
        """
        Full grounded evaluation using the multi-LLM Debate Arena.
        Used ONLY for Gold (XAUUSD). All models debate, critique, and vote.

        Returns:
            (TradeDecision, DebateResult) tuple.
            DebateResult contains the full transcript for logging.
        """
        base_prompt = (
            f"{self.SYSTEM_CONTEXT}\n\n"
            f"=== PAIR: {pair} ===\n\n"
            f"--- TRADING CONCEPTS KNOWLEDGE ---\n{concept_knowledge}\n\n"
            f"--- QUANT REPORT (Strategy Signals) ---\n{quant_report}\n\n"
            f"--- FUNDAMENTAL REPORT (News & Sentiment) ---\n{fundamental_report}\n\n"
            f"--- STRATEGY KNOWLEDGE ---\n{strategy_knowledge}\n\n"
            f"Based on ALL context (RAG verified history + above data), "
            f"what is your grounded trading decision for {pair}?"
        )

        try:
            debate_result = debate_arena.run_debate(
                base_prompt=base_prompt,
                rag_context=rag_context,
                pair=pair,
            )

            if debate_result.winning_decision is not None:
                if debate_result.winning_decision.action == "HOLD":
                    debate_result.winning_decision.pair = pair
                return debate_result.winning_decision, debate_result

            # Debate failed (< 2 models available) — fallback to single model
            print(f"    [WARN] Debate failed -- falling back to single-model evaluation.")
            decision = self.evaluate(
                quant_report=quant_report,
                fundamental_report=fundamental_report,
                strategy_knowledge=strategy_knowledge,
                concept_knowledge=concept_knowledge,
                rag_context=rag_context,
                pair=pair,
            )
            return decision, debate_result

        except Exception as e:
            print(f"  [ERR] Debate Arena error: {e}. Falling back to single-model.")
            decision = self.evaluate(
                quant_report=quant_report,
                fundamental_report=fundamental_report,
                strategy_knowledge=strategy_knowledge,
                concept_knowledge=concept_knowledge,
                rag_context=rag_context,
                pair=pair,
            )
            from agents.debate_arena import DebateResult
            empty_debate = DebateResult(pair=pair, debate_successful=False)
            return decision, empty_debate


# ===========================================================================
# MAIN TRADING ENGINE
# ===========================================================================

class TradingEngine:
    """
    The fully connected orchestration engine.

    Pipeline: data_feeds → strategy_library → rag_system → agents → broker_mt5 → monitoring
    """

    def __init__(self, *, clock=None):
        self.clock = clock or SystemClock()
        self.journal = None
        self._active_run_id = None
        self._cycle_guard = threading.Lock()
        self.executor = None
        try:
            self._initialize()
        except BaseException:
            # A later feed/model/store failure must not leave a verified session
            # active after construction aborts. Preserve the original failure.
            if self.executor is not None:
                try:
                    self.executor.disconnect()
                except Exception:
                    pass
            if self.journal is not None:
                try:
                    self.journal.close()
                except Exception:
                    print("[ERR] Journal cleanup failed during startup failure")
            raise

    def _initialize(self):
        print("=" * 65)
        print("  ADVANCED AI TRADING AGENT — FULLY INTEGRATED SYSTEM")
        print("=" * 65)

        # ── Config ──────────────────────────────────────────────────────────
        self.config    = load_config()
        self.execution_policy = DevelopmentPolicy.from_config(self.config)
        self.execution_policy.require_demo_session()
        credentials = demo_credentials_from_environment()
        self.symbol_registry = SymbolRegistry.from_config(self.config)
        self.symbols = self.symbol_registry.active_symbols(self.config["broker"].get("symbols"))
        self.demo_mode = True  # Compatibility: only verified demo accounts are supported.
        storage = self.config.get("storage", {})
        if not isinstance(storage, dict):
            raise JournalError("storage must be a mapping")
        journal_path = storage.get("journal_path")
        if journal_path is not None and (not isinstance(journal_path, str) or not journal_path.strip()):
            raise JournalError("storage.journal_path must be a nonempty path or null")
        self.journal = Journal(journal_path or default_journal_path(), clock=self.clock)
        self.executor = OrderExecutor(
            symbol_registry=self.symbol_registry,
            clock=self.clock,
            mode=self.execution_policy.mode.value,
            enable_demo_orders=self.execution_policy.enable_demo_orders,
            gateway_config=self.config.get("broker", {}).get("pre_trade_gateway", {}),
        )
        if not self.executor.connect(**credentials):
            raise ModeError("Demo MT5 connection could not be verified; startup stopped")

        # ── Data Feeds ──────────────────────────────────────────────────────
        print("\n[1/7] Initializing Data Feeds...")
        # ── MT5 Auto-Connect & Health Check ──────────────────────────────
        print("\n  -- MT5 Auto-Connect & Health Check...")
        self.mt5_fetcher = MT5DataFetcher(**credentials, symbol_registry=self.symbol_registry)
        mt5_connected = self.mt5_fetcher.connect()
        if not mt5_connected:
            raise ModeError("Demo market-data connection failed; startup stopped")
        # Feed initialization can change the process-global terminal session.
        self.executor.assert_demo_session()
        if mt5_connected:
            health = self.mt5_fetcher.health_check(self.symbols)
            if health["issues"]:
                print("\n  [WARN] MT5 Health Check — Issues Found:")
                for i, issue in enumerate(health["issues"], 1):
                    print(f"     {i}. {issue}")
            else:
                print("  [OK] MT5 Health Check PASSED — all systems nominal.")

            # Report symbol status
            ok_symbols = [s for s, ok in health["symbols_status"].items() if ok]
            bad_symbols = [s for s, ok in health["symbols_status"].items() if not ok]
            if ok_symbols:
                print(f"  [OK] Symbols ready ({len(ok_symbols)}/{len(self.symbols)}): "
                      f"{', '.join(ok_symbols)}")
            if bad_symbols:
                print(f"  [ERR] Symbols FAILED ({len(bad_symbols)}): {', '.join(bad_symbols)}")
                print("     >> These symbols will be skipped. Remove from config/settings.yaml "
                      "or add them in MT5 Market Watch.")
                # Filter out unavailable symbols so the bot doesn't waste cycles
                self.symbols = [s for s in self.symbols if s in ok_symbols]

            # Report algo trading status
            if health.get("algo_trading_enabled"):
                print("  [OK] Algo Trading: ENABLED")
            else:
                print("  [WARN] Algo Trading: DISABLED — trades will be blocked!")
                print("     >> FIX: MT5 -> Tools -> Options -> Expert Advisors -> "
                      "Enable 'Allow algorithmic trading'")

            # Report account info
            acct = health.get("account_info")
            if acct:
                print(f"  [$] Account: {acct['login']} | Balance: ${acct['balance']:.2f} | "
                      f"Equity: ${acct['equity']:.2f} | Mode: {acct['trade_mode']}")
        print("  [OK] MT5 Data Fetcher ready (self-healing enabled)")
        self.executor.assert_demo_session()

        self.web_search = WebSearchAgent(use_tavily=bool(os.getenv("TAVILY_API_KEY")))
        self.sentiment_analyzer = None  # Lazy load — FinBERT is heavy
        self.calendar = EconomicCalendar()
        self.calendar.fetch_calendar()

        # ── RAG Memory System ───────────────────────────────────────────────
        print("\n[2/7] Initializing RAG Memory System...")
        rag_db_path = self.config.get("rag", {}).get("db_path", "rag_system/chroma_db")
        self.rag    = TradingRAG(db_path=rag_db_path, symbol_registry=self.symbol_registry)

        # ── Grounding Validator ─────────────────────────────────────────────
        self.validator = GroundingValidator()
        print("  [OK] Grounding Validator ready (hallucination guard active)")

        # ── Load Trading Concepts (The "Gem" Knowledge) ──────────────────────
        print("\n[3/7] Loading Trading Concepts Knowledge...")
        self.concept_knowledge = self._load_trading_concepts()
        self.strategy_knowledge = get_strategy_summary()

        # ── LLM Provider ────────────────────────────────────────────────────
        print("\n[4/7] Initializing LLM Providers...")
        self.llm_provider = LLMProvider()

        # ── Observation Logger & Monitor ─────────────────────────────────────
        self.observation_logger = ObservationLogger()
        self.performance_monitor = PerformanceMonitor()

        # ── Brain + Debate Arena ──────────────────────────────────────────────
        print("\n[5/7] Initializing Trading Brain + Debate Arena...")
        self.brain = TradingBrain(self.llm_provider)
        self.debate_arena = DebateArena(self.llm_provider)
        self._debate_model_names = self.llm_provider.get_all_available_names()
        print("  [OK] Brain ready (RAG-grounded mode)")
        print(f"  [OK] Debate Arena ready — {len(self._debate_model_names)} models for Gold debate")
        print(f"     Models: {', '.join(self._debate_model_names)}")

        # ── Risk Agent ───────────────────────────────────────────────────────
        print("\n[6/7] Initializing Risk Agent...")
        self.risk_agent = RiskAgent(self.config, symbol_registry=self.symbol_registry)
        self.executor.bind_risk_agent(self.risk_agent)
        print("  [OK] Risk Agent ready")

        # ── Order Executor (Broker) ─────────────────────────────────────────
        print("\n[7/7] Initializing Order Executor...")
        self.executor.assert_demo_session()
        print("  [OK] Order Executor ready")

        # ── Trade Log ────────────────────────────────────────────────────────
        self.trade_log_path = Path(__file__).parent / "trade_log.json"
        self.trade_log      = self._load_trade_log()

        # ── Thread Safety ────────────────────────────────────────────────────
        self._lock = threading.Lock()  # Protects RAG DB, trade_log, risk_agent
        self._max_workers = min(4, len(self.symbols))  # Parallel threads

        # ── State Caching ────────────────────────────────────────────────────
        self.last_news_fetch_time = datetime.min
        self.last_tavily_fetch_time = datetime.min  # Track Tavily usage separately for conservation
        self.cached_news_items = []
        self.cached_fundamental_report = "No news data available."
        
        # ── Two-Tier Market Tracking ─────────────────────────────────────────
        self.gold_symbol = "XAUUSD"               # Primary market — always traded with debate
        self.current_secondary_market = None       # Dynamically chosen each cycle
        self.non_gold_symbols = [s for s in self.symbols if s != self.gold_symbol]

        # ── Summary ──────────────────────────────────────────────────────────
        rag_stats = self.rag.get_db_stats()
        print("\n" + "=" * 65)
        print(f"  [ONLINE] Mode: {self.execution_policy.mode.value.upper()}")
        print(f"  [T1] Primary Market: {self.gold_symbol} (Multi-LLM Debate)")
        print(f"  [T2] Secondary Pool: {', '.join(self.non_gold_symbols)} ({len(self.non_gold_symbols)} candidates)")
        print(f"  [AI] Debate Models: {len(self._debate_model_names)} active")
        print(f"  [DB] RAG: {rag_stats.get('trade_records', 0)} trades | "
              f"{rag_stats.get('news_records', 0)} news events in memory")
        print(f"  [OK] Grounding Validator: ACTIVE")
        print("=" * 65 + "\n")

    def _load_trading_concepts(self) -> str:
        """Loads the foundational trading concepts for the LLM Gem."""
        concept_path = Path(__file__).parent / "trading_concepts" / "cheat_sheet.md"
        rules_path = Path(__file__).parent / "trading_concepts" / "next_action_rules.md"
        relationships_path = Path(__file__).parent / "trading_concepts" / "concept_relationships.md"
        fundamental_path = Path(__file__).parent / "trading_concepts" / "fundamental_news_events.md"
        mt5_knowledge_path = Path(__file__).parent / "trading_concepts" / "mt5_python_api_knowledge.md"
        
        knowledge = ""
        if concept_path.exists():
            knowledge += concept_path.read_text(encoding="utf-8")
        if rules_path.exists():
            knowledge += "\n\n" + rules_path.read_text(encoding="utf-8")
        if relationships_path.exists():
            knowledge += "\n\n" + relationships_path.read_text(encoding="utf-8")
        if fundamental_path.exists():
            knowledge += "\n\n" + fundamental_path.read_text(encoding="utf-8")
        if mt5_knowledge_path.exists():
            knowledge += "\n\n" + mt5_knowledge_path.read_text(encoding="utf-8")
            
        if not knowledge:
            print("  [WARN] Trading concepts not found. The Brain will run without fundamental concept knowledge.")
            
        return knowledge

    # =======================================================================
    # CORE CYCLE — Two-Tier System
    # =======================================================================

    def run_cycle(self, is_high_impact: bool = False):
        """Persist cycle boundaries; concurrent cycles cannot share correlation state."""
        if not self._cycle_guard.acquire(blocking=False):
            raise RuntimeError("An analysis cycle is already running")
        try:
            run = RunRecord(mode=self.execution_policy.mode, purpose="analysis_cycle", created_at=self.clock.now_utc())
            started = EventEnvelope(event_type="AnalysisRunStarted", source="engine", run_id=run.run_id,
                                    mode=run.mode, occurred_at=self.clock.now_utc())
            self.journal.commit(run=run, events=[started])
            self._active_run_id = run.run_id
            try:
                self._run_cycle_body(is_high_impact)
            except BaseException as error:
                try:
                    self.journal.commit(events=[EventEnvelope(
                        event_type="AnalysisRunFailed", source="engine", run_id=run.run_id,
                        mode=run.mode, occurred_at=self.clock.now_utc(), causation_id=started.event_id,
                        payload={"error_type": type(error).__name__})])
                except Exception:
                    print("[ERR] Failed to persist cycle failure; original error retained")
                raise
            else:
                self.journal.commit(events=[EventEnvelope(
                    event_type="AnalysisRunCompleted", source="engine", run_id=run.run_id,
                    mode=run.mode, occurred_at=self.clock.now_utc(), causation_id=started.event_id)])
        finally:
            self._active_run_id = None
            self._cycle_guard.release()

    def _run_cycle_body(self, is_high_impact: bool = False):
        """
        One full analysis cycle — TWO-TIER ARCHITECTURE:

        TIER 1: Gold (XAUUSD) — Multi-LLM Debate
          All available models independently analyze Gold, debate each
          other's decisions, and vote on a consensus before trading.

        TIER 2: Dynamic Secondary Market — Single Model Sniper
          Scan all non-Gold markets in parallel, score and rank them,
          pick the BEST one, and use a single primary model to trade it.
        """
        cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'═' * 65}")
        print(f"  CYCLE START: {cycle_time}")
        print(f"{'═' * 65}")

        # ── STEP 1: Fundamental Data ──────────────────────────────────────
        print(f"\n  [STEP 1] Gathering global news & sentiment... (High Impact: {is_high_impact})")
        news_items, fundamental_report = self._gather_fundamentals(is_high_impact)

        # Save news events to RAG memory for future cycles
        if news_items:
            with self._lock:
                self.rag.memorize_news(
                    news_items=news_items,
                    pair="GLOBAL",
                    market_reaction="Recorded at cycle start — market reaction TBD"
                )

        # ── STEP 2: TIER 1 — Gold Multi-LLM Debate ───────────────────────
        print(f"\n  {'═' * 60}")
        print(f"  [STEP 2] TIER 1: GOLD ({self.gold_symbol}) -- Multi-LLM Debate")
        print(f"  {'═' * 60}")
        if self.gold_symbol in self.symbols:
            self._process_gold_with_debate(fundamental_report)

        # ── STEP 3: TIER 2 — Secondary Market Selection ──────────────────
        if self.non_gold_symbols:
            print(f"\n  {'═' * 60}")
            print(f"  [STEP 3] TIER 2: Secondary Market Selection")
            print(f"  {'═' * 60}")
            self._process_secondary_market(fundamental_report)
        else:
            print(f"\n  [STEP 3] No secondary symbols configured -- Gold only mode.")

        print(f"\n{'═' * 65}")
        print(f"  CYCLE COMPLETE: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'═' * 65}")

    # =======================================================================
    # TIER 1: GOLD — Multi-LLM Debate
    # =======================================================================

    def _process_gold_with_debate(self, fundamental_report: str):
        """
        Full analysis pipeline for Gold (XAUUSD) using the Debate Arena.
        All available models debate before a trade is placed.
        """
        symbol = self.gold_symbol
        print(f"\n    >> Fetching {symbol} data from MT5...")

        # ── Get market data ──────────────────────────────────────────
        try:
            import MetaTrader5 as mt5
            df = self.mt5_fetcher.get_historical_data(symbol, mt5.TIMEFRAME_H1, count=200)
            if df is None or df.empty:
                print(f"    [WARN] No data for {symbol}. Skipping Gold this cycle.")
                return
        except Exception as e:
            print(f"    [WARN] MT5 data error for {symbol}: {e}. Skipping.")
            return

        # ── Run all strategies ───────────────────────────────────────
        print(f"    [2a] Running all strategies on {symbol}...")
        strategy_signals = run_all_strategies(df, pair=symbol)

        if not strategy_signals:
            print(f"    -- No signals from any strategy for {symbol}.")
            return

        top_signal = strategy_signals[0]
        selected_candidate = candidate_from_signal(top_signal, STRATEGY_REGISTRY)
        print(
            f"    {len(strategy_signals)} signal(s) | Top: "
            f"{top_signal['strategy']} ({top_signal['confidence']}% conf)"
        )
        quant_report = self._format_quant_report(strategy_signals, selected_candidate)

        # ── RAG Memory Query ─────────────────────────────────────────
        print(f"    [2b] Querying RAG memory for {symbol}...")
        market_context = f"Price action context: {top_signal.get('reasoning', '')[:200]}"

        with self._lock:
            trade_recall = self.rag.recall_similar_trades(
                pair=symbol, strategy=selected_candidate.strategy,
                current_context=market_context, n_results=5
            )
            news_recall = self.rag.recall_similar_news(
                query_text=fundamental_report[:300], pair=symbol, n_results=3
            )
            actual_win_rate = self.rag.get_strategy_win_rate(
                pair=symbol, strategy=selected_candidate.strategy
            )

        candidate_context = bind_context(selected_candidate, trade_recall, news_recall, actual_win_rate, STRATEGY_REGISTRY)
        rag_context = (
            f"{trade_recall['summary']}\n\n"
            f"{news_recall['summary']}\n\n"
            f"Verified DB win rate for {symbol}/{top_signal['strategy']}: "
            f"{f'{actual_win_rate*100:.1f}%' if actual_win_rate is not None else 'Insufficient data'}"
        )

        cold_start = trade_recall.get("is_cold_start", True)
        print(
            f"    RAG: {trade_recall['total_found']} trade memories | "
            f"{news_recall['total_found']} news memories | "
            f"{'[COLD START]' if cold_start else '[OK] History found'}"
        )

        # ── DEBATE: Multi-LLM Decision ───────────────────────────────
        print(f"\n    [2c] DEBATE ARENA: {symbol} -- All models evaluating...")
        decision, debate_result = self.brain.evaluate_with_debate(
            quant_report=quant_report,
            fundamental_report=fundamental_report,
            strategy_knowledge=self.strategy_knowledge,
            concept_knowledge=self.concept_knowledge,
            rag_context=rag_context,
            pair=symbol,
            debate_arena=self.debate_arena,
        )

        if debate_result.debate_successful:
            print(
                f"    >> Debate Consensus: {decision.action} {symbol} "
                f"(Conf: {decision.confidence}% | "
                f"Tally: {debate_result.vote_tally})"
            )
        else:
            print(
                f"    >> Single-model decision: {decision.action} {symbol} "
                f"(Conf: {decision.confidence}%)"
            )

        # ── From here, same pipeline as before: Grounding → Risk → Execute
        self._execute_validated_trade(
            candidate_context=candidate_context,
            symbol=symbol,
            decision=decision,
            strategy_signals=strategy_signals,
            top_signal=top_signal,
            trade_recall=trade_recall,
            news_recall=news_recall,
            actual_win_rate=actual_win_rate,
            fundamental_report=fundamental_report,
            debate_result=debate_result,
        )

    # =======================================================================
    # TIER 2: SECONDARY MARKET — Scan, Score, Snipe
    # =======================================================================

    def _process_secondary_market(self, fundamental_report: str):
        """
        Scan all non-Gold markets in parallel, score each one based on
        signal strength and agreement, then use a single model to trade
        the best one.
        """
        print(f"\n    >> Scanning {len(self.non_gold_symbols)} markets in parallel...")

        # ── Parallel scan: fetch data + run strategies ────────────────
        market_scores = {}
        market_data = {}  # Store data for the winner

        def _scan_symbol(symbol):
            """Quick scan: fetch data + run strategies + compute score."""
            try:
                import MetaTrader5 as mt5
                df = self.mt5_fetcher.get_historical_data(symbol, mt5.TIMEFRAME_H1, count=200)
                if df is None or df.empty:
                    return symbol, 0, None, None

                signals = run_all_strategies(df, pair=symbol)
                if not signals:
                    return symbol, 0, None, None

                # ── Score this market ────────────────────────────────
                # Higher score = better trade opportunity
                top_confidence = signals[0]["confidence"]
                signal_count = len(signals)

                # Signal agreement bonus: if most signals point same direction
                directions = [s.get("direction", "HOLD") for s in signals]
                buy_count = directions.count("BUY")
                sell_count = directions.count("SELL")
                agreement = max(buy_count, sell_count) / len(directions) if directions else 0

                score = (
                    top_confidence * 0.4 +         # Top signal strength (40%)
                    signal_count * 5 * 0.3 +       # More signals = clearer setup (30%)
                    agreement * 100 * 0.3           # Signal agreement (30%)
                )

                return symbol, score, signals, df

            except Exception as e:
                print(f"      [WARN] Scan error for {symbol}: {e}")
                return symbol, 0, None, None

        with ThreadPoolExecutor(max_workers=min(4, len(self.non_gold_symbols))) as executor:
            futures = {executor.submit(_scan_symbol, s): s for s in self.non_gold_symbols}
            for future in as_completed(futures):
                try:
                    symbol, score, signals, df = future.result()
                    market_scores[symbol] = score
                    if signals and df is not None:
                        market_data[symbol] = {"signals": signals, "df": df}
                    print(f"      {symbol}: Score = {score:.1f}")
                except Exception as e:
                    print(f"      [WARN] Scan future error: {e}")

        if not market_data:
            print(f"    -- No viable secondary markets found this cycle.")
            return

        # ── Pick the best secondary market ────────────────────────────
        best_symbol = max(market_scores, key=market_scores.get)
        best_score = market_scores[best_symbol]

        if best_score < 20:  # Minimum threshold — don't trade garbage setups
            print(f"    -- Best market ({best_symbol}: {best_score:.1f}) below threshold. Skipping.")
            return

        self.current_secondary_market = best_symbol
        print(f"\n    >> SELECTED: {best_symbol} (Score: {best_score:.1f})")

        # ── Run single-model analysis on the winner ───────────────────
        data = market_data[best_symbol]
        strategy_signals = data["signals"]
        top_signal = strategy_signals[0]
        selected_candidate = candidate_from_signal(top_signal, STRATEGY_REGISTRY)

        print(
            f"    {len(strategy_signals)} signal(s) | Top: "
            f"{top_signal['strategy']} ({top_signal['confidence']}% conf)"
        )
        quant_report = self._format_quant_report(strategy_signals, selected_candidate)

        # RAG query
        print(f"    [3b] Querying RAG memory for {best_symbol}...")
        market_context = f"Price action context: {top_signal.get('reasoning', '')[:200]}"

        with self._lock:
            trade_recall = self.rag.recall_similar_trades(
                pair=best_symbol, strategy=selected_candidate.strategy,
                current_context=market_context, n_results=5
            )
            news_recall = self.rag.recall_similar_news(
                query_text=fundamental_report[:300], pair=best_symbol, n_results=3
            )
            actual_win_rate = self.rag.get_strategy_win_rate(
                pair=best_symbol, strategy=selected_candidate.strategy
            )

        candidate_context = bind_context(selected_candidate, trade_recall, news_recall, actual_win_rate, STRATEGY_REGISTRY)
        rag_context = (
            f"{trade_recall['summary']}\n\n"
            f"{news_recall['summary']}\n\n"
            f"Verified DB win rate for {best_symbol}/{top_signal['strategy']}: "
            f"{f'{actual_win_rate*100:.1f}%' if actual_win_rate is not None else 'Insufficient data'}"
        )

        # Single-model Brain decision (no debate)
        print(f"    [3c] Single-model evaluating {best_symbol}...")
        decision = self.brain.evaluate(
            quant_report=quant_report,
            fundamental_report=fundamental_report,
            strategy_knowledge=self.strategy_knowledge,
            concept_knowledge=self.concept_knowledge,
            rag_context=rag_context,
            pair=best_symbol,
        )

        print(
            f"    >> Decision: {decision.action} {best_symbol} "
            f"(Conf: {decision.confidence}%)"
        )

        # ── Execute through the standard pipeline ─────────────────────
        self._execute_validated_trade(
            candidate_context=candidate_context,
            symbol=best_symbol,
            decision=decision,
            strategy_signals=strategy_signals,
            top_signal=top_signal,
            trade_recall=trade_recall,
            news_recall=news_recall,
            actual_win_rate=actual_win_rate,
            fundamental_report=fundamental_report,
            debate_result=None,  # No debate for secondary market
        )

    # =======================================================================
    # SHARED: Grounding → Risk → Execute Pipeline
    # =======================================================================

    def _execute_validated_trade(
        self,
        symbol: str,
        decision,
        strategy_signals: list,
        top_signal: dict,
        trade_recall: dict,
        news_recall: dict,
        actual_win_rate,
        fundamental_report: str,
        debate_result=None,
        candidate_context=None,
    ):
        """
        Shared pipeline for both Gold (Tier 1) and Secondary (Tier 2).
        Runs: Grounding Validator → Risk Agent → Execute Trade.
        """
        decision = decision.model_copy(deep=True)
        symbol = self.symbol_registry.canonical(symbol)
        decision.pair = self.symbol_registry.canonical(decision.pair)
        if decision.pair != symbol:
            raise SymbolError("Decision instrument does not match selected instrument")
        if decision.action != "HOLD":
            try:
                validate_binding(candidate_context, decision, top_signal, strategy_signals,
                                 evidence_json(trade_recall, news_recall, actual_win_rate), STRATEGY_REGISTRY)
            except (ConstructionError, ValueError) as error:
                decision.action = "HOLD"
                with self._lock:
                    self._log_decision(decision, f"CONSTRUCTION_REJECTED: {error}", debate_result=debate_result)
                return
        # ── Grounding Validator ───────────────────────────────────────
        print(f"    [V1] Grounding Validator running...")
        grounding_result = self.validator.validate(
            decision=decision,
            trade_recall=trade_recall,
            news_recall=news_recall,
            actual_win_rate=actual_win_rate
        )

        grounding_log = self.validator.format_log_entry(grounding_result, decision.action)
        print(
            f"    Grounding score: {grounding_result.grounding_score:.2f}/1.00 | "
            f"Checks passed: {len(grounding_result.checks_passed)} | "
            f"Failed: {len(grounding_result.checks_failed)}"
        )

        if grounding_result.override_to_hold:
            print(f"    [OVERRIDE] GROUNDING -> HOLD")
            print(f"    Reason: {grounding_result.override_reason[:200]}")
            decision.action = "HOLD"
            with self._lock:
                self._log_decision(
                    decision,
                    f"GROUNDING_OVERRIDE: {grounding_result.override_reason[:150]}",
                    grounding_log=grounding_log,
                    debate_result=debate_result,
                )
            return

        print(
            f"    ✅ Grounding passed: {decision.action} {symbol} "
            f"(Win rate cited: {decision.historical_win_rate:.1%})"
        )

        # ── HOLD → skip ──────────────────────────────────────────────
        if decision.action == "HOLD":
            print(f"    HOLD -- No trade for {symbol}.")
            with self._lock:
                self._log_decision(
                    decision, "HOLD — Brain decided to wait",
                    grounding_log=grounding_log, debate_result=debate_result,
                )
                self.observation_logger.log_from_cycle_data(
                    symbol=symbol, strategy_signals=strategy_signals,
                    decision_action=decision.action, decision_reasoning=decision.reasoning,
                    decision_confidence=decision.confidence,
                    grounding_score=grounding_result.grounding_score,
                    rag_win_rate=actual_win_rate, timeframe="H1"
                )
            return

        # ── Fresh quote preparation ──────────────────────────────────
        try:
            spec = self.executor.get_instrument_spec(symbol)
            validate_binding(candidate_context, decision, top_signal, strategy_signals,
                             evidence_json(trade_recall, news_recall, actual_win_rate), STRATEGY_REGISTRY)
            constructed = construct_trade(candidate_context, spec, minimum_rr=self.risk_agent.min_rr)
            preparation = self.executor.prepare_trade(
                pair=constructed.pair, direction=constructed.direction,
                reference_entry=constructed.entry_price, stop_loss=constructed.stop_loss,
                take_profit=constructed.take_profit, minimum_rr=self.risk_agent.min_rr,
                contract_revision=constructed.contract_revision,
                candidate_id=str(constructed.candidate_id), strategy_id=constructed.strategy,
                evidence_digest=constructed.evidence_digest,
            )
        except (ConstructionError, ModeError, GatewayError) as error:
            decision.action = "HOLD"
            with self._lock:
                self._log_decision(decision, f"PRE_TRADE_GATEWAY_REJECTED: {error}", grounding_log=grounding_log,
                                   debate_result=debate_result)
            return
        grounding_log["construction"] = {
            "candidate": candidate_context.candidate.model_dump(mode="json"),
            "constructed": constructed.model_dump(mode="json"),
            "broker_symbol": spec.broker_symbol, "tick_size": str(spec.trade_tick_size),
            "metadata_observed_at": spec.observed_at.isoformat(),
        }
        grounding_log["quote_preparation"] = {
            "bid": str(preparation.bid), "ask": str(preparation.ask),
            "entry_price": str(preparation.entry_price),
            "quote_time": preparation.quote_time.isoformat(),
            "risk_reward": str(preparation.risk_reward),
        }
        print(f"    [V2] Fresh quote and final risk approval...")

        is_trending = candidate_context.candidate.confidence >= 80 and "Trend" in constructed.strategy
        source_record = TradeRecord(
            trade_id=f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pair=constructed.pair, direction=constructed.direction,
            entry_price=float(preparation.entry_price), stop_loss=float(preparation.stop_loss),
            take_profit=float(preparation.take_profit), lot_size=0.0,
            open_time=preparation.quote_time.isoformat(),
            candidate_id=str(constructed.candidate_id), strategy_id=constructed.strategy,
            contract_revision=constructed.contract_revision, evidence_digest=constructed.evidence_digest,
        )
        try:
            # Serialize final risk, broker checks and the one-shot send together
            # so another analysis cannot spend the same in-memory risk state.
            with self._lock:
                authorization = self.executor.authorize_trade(
                    preparation, source_record, confidence=decision.confidence,
                    is_trending=is_trending,
                )
                risk_result = authorization.risk_result
                if authorization.approved:
                    trade_record = authorization.trade_record
                    order_result = self.executor.place_order(
                        trade_record, approval_token=authorization.token)
                    if order_result["success"]:
                        # Commit in-memory exposure before releasing the same
                        # lock that guarded sizing and the native send.
                        self.risk_agent.record_trade_opened(trade_record)
        except (GatewayError, ModeError) as error:
            with self._lock:
                self._log_decision(decision, f"PRE_TRADE_GATEWAY_REJECTED: {error}",
                                   grounding_log=grounding_log, debate_result=debate_result)
            return

        if risk_result is not None and risk_result.sizing is not None:
            grounding_log["position_sizing"] = risk_result.sizing
        grounding_log["gateway_approval"] = authorization.audit

        print(f"    Risk: {risk_result.reason}")

        if not risk_result.approved:
            with self._lock:
                self._log_decision(
                    decision, f"VETOED by Risk Agent: {risk_result.reason}",
                    grounding_log=grounding_log, debate_result=debate_result,
                )
            return

        if not authorization.approved:
            with self._lock:
                self._log_decision(
                    decision, f"PRE_TRADE_GATEWAY_REJECTED: {authorization.reason}",
                    grounding_log=grounding_log, debate_result=debate_result,
                )
            return

        if trade_record.sizing_provenance:
            grounding_log["position_sizing"] = trade_record.sizing_provenance

        # ── High Conviction Hold Check ────────────────────────────────
        hold_check = self.risk_agent.check_high_conviction_hold(
            pair=symbol, confidence=decision.confidence
        )
        if hold_check["allow_extended_hold"]:
            print(f"    {hold_check['reason']}")

        # ── Execute Trade ─────────────────────────────────────────────
        print(
            f"    [EX] EXECUTING: {decision.action} {symbol} "
            f"| Lots: {risk_result.adjusted_lot_size}"
        )

        with self._lock:
            if order_result["success"]:
                self._log_decision(
                    decision,
                    f"EXECUTED [{order_result['mode']}]: Lots={risk_result.adjusted_lot_size} | "
                    f"Ticket={order_result.get('ticket')}"
                    f"{' | HIGH CONVICTION HOLD ENABLED' if hold_check['allow_extended_hold'] else ''}",
                    trade=trade_record, grounding_log=grounding_log,
                    debate_result=debate_result,
                )
                print(f"    ✅ Order placed: {order_result['reason']}")
            else:
                print(f"    ❌ Order failed: {order_result['reason']}")
                self._log_decision(
                    decision, f"ORDER_FAILED: {order_result['reason']}",
                    grounding_log=grounding_log, debate_result=debate_result,
                )

        # ── Log Observation for Pattern Miner ─────────────────────────
        with self._lock:
            self.observation_logger.log_from_cycle_data(
                symbol=symbol, strategy_signals=strategy_signals,
                decision_action=decision.action, decision_reasoning=decision.reasoning,
                decision_confidence=decision.confidence,
                grounding_score=grounding_result.grounding_score,
                rag_win_rate=actual_win_rate,
                entry_price=trade_record.entry_price,
                stop_loss=trade_record.stop_loss, take_profit=trade_record.take_profit,
                timeframe="H1"
            )


    # =======================================================================
    # PER-SYMBOL ANALYSIS (runs inside a thread)
    # =======================================================================

    def _analyze_symbol(self, symbol: str, fundamental_report: str):
        """
        Full analysis pipeline for a single symbol.
        Thread-safe: uses self._lock for shared resources.
        """
        symbol = self.symbol_registry.canonical(symbol)
        print(f"\n  {'═' * 60}")
        print(f"  [THREAD] Analyzing {symbol}...")

        # ── Get market data from MT5 ────────────────────────────────
        try:
            import MetaTrader5 as mt5
            df = self.mt5_fetcher.get_historical_data(symbol, mt5.TIMEFRAME_H1, count=200)
            if df is None or df.empty:
                print(f"    [WARN] No data for {symbol}. Skipping.")
                return
        except Exception as e:
            print(f"    [WARN] MT5 data error for {symbol}: {e}. Skipping.")
            return

        # ── Run all strategies (12+) ─────────────────────────────────
        print(f"    [2a] Running all strategies on {symbol}...")
        strategy_signals = run_all_strategies(df, pair=symbol)

        if not strategy_signals:
            print(f"    -- No signals from any strategy for {symbol}.")
            return

        top_signal = strategy_signals[0]
        selected_candidate = candidate_from_signal(top_signal, STRATEGY_REGISTRY)
        print(
            f"    {len(strategy_signals)} signal(s) | Top: "
            f"{top_signal['strategy']} ({top_signal['confidence']}% conf)"
        )
        quant_report = self._format_quant_report(strategy_signals, selected_candidate)

        # ── STEP 3: RAG Memory Query (thread-safe) ────────────────────
        print(f"    [2b] Querying RAG memory for {symbol}...")
        market_context = (
            f"Price action context: {top_signal.get('reasoning', '')[:200]}"
        )

        with self._lock:
            trade_recall = self.rag.recall_similar_trades(
                pair=symbol,
                strategy=selected_candidate.strategy,
                current_context=market_context,
                n_results=5
            )

            news_recall = self.rag.recall_similar_news(
                query_text=fundamental_report[:300],
                pair=symbol,
                n_results=3
            )

            actual_win_rate = self.rag.get_strategy_win_rate(
                pair=symbol,
                strategy=selected_candidate.strategy
            )

        # Build the combined grounded context block for LLM
        candidate_context = bind_context(selected_candidate, trade_recall, news_recall, actual_win_rate, STRATEGY_REGISTRY)
        rag_context = (
            f"{trade_recall['summary']}\n\n"
            f"{news_recall['summary']}\n\n"
            f"Verified DB win rate for {symbol}/{top_signal['strategy']}: "
            f"{f'{actual_win_rate*100:.1f}%' if actual_win_rate is not None else 'Insufficient data'}"
        )

        cold_start = trade_recall.get("is_cold_start", True)
        print(
            f"    RAG: {trade_recall['total_found']} trade memories | "
            f"{news_recall['total_found']} news memories | "
            f"{'[COLD START]' if cold_start else '[OK] History found'}"
        )

        # ── STEP 4: Brain (LLM) Decision ─────────────────────────────
        print(f"    [2c] Brain evaluating {symbol} with grounded context...")
        decision = self.brain.evaluate(
            quant_report=quant_report,
            fundamental_report=fundamental_report,
            strategy_knowledge=self.strategy_knowledge,
            concept_knowledge=self.concept_knowledge,
            rag_context=rag_context,
            pair=symbol,
        )

        print(
            f"    >> Raw decision: {decision.action} {symbol} "
            f"(Conf: {decision.confidence}% | "
            f"Hallucination: {decision.hallucination_risk} | "
            f"RAG sources cited: {decision.rag_sources_cited})"
        )

        self._execute_validated_trade(
            candidate_context=candidate_context,
            symbol=symbol, decision=decision, strategy_signals=strategy_signals,
            top_signal=top_signal, trade_recall=trade_recall, news_recall=news_recall,
            actual_win_rate=actual_win_rate, fundamental_report=fundamental_report,
        )

    def _gather_fundamentals(self, is_high_impact: bool = False) -> tuple[list[dict], str]:
        """
        Search web for news and run FinBERT sentiment analysis.
        
        TAVILY CONSERVATION STRATEGY (3 tiers):
        ─────────────────────────────────────────────────────────────────
        TIER 1 — NORMAL MODE (no events near):
          • DuckDuckGo for all searches (free, unlimited)
          • Tavily used ONCE every 4-hour cycle for a quality check
          • Cache: 4 hours
        
        TIER 2 — PRE-EVENT MODE (high-impact event within 4 hours):
          • Tavily every 2 hours for premium news accuracy
          • DuckDuckGo between Tavily calls
          • Cache: 30 minutes (more frequent checks)
        
        TIER 3 — SNIPER MODE (event happening NOW / chairman addressing):
          • Tavily every 2 minutes for gunshot news
          • Maximum accuracy, burn credits aggressively
          • Cache: 2 minutes
        ─────────────────────────────────────────────────────────────────
        
        Returns: (news_items_with_sentiment, formatted_report_string)
        """
        now = datetime.now()
        has_tavily_key = bool(os.getenv("TAVILY_API_KEY"))
        
        # ── Determine search tier based on economic calendar ──────────
        upcoming_4hr = self.calendar.get_upcoming_high_impact_events(minutes_ahead=240)
        upcoming_1hr = self.calendar.get_upcoming_high_impact_events(minutes_ahead=60)
        
        if is_high_impact:
            # ═══ TIER 3: SNIPER MODE ═══
            # Event is happening NOW — Tavily every 2 minutes
            cache_seconds = 110           # ~2 min cache
            tavily_interval = 120         # Tavily every 2 min
            use_tavily_now = True         # Always try Tavily in sniper
            search_tier = "SNIPER"
            queries = [
                "forex market breaking news now",
                "Federal Reserve interest rate decision latest",
                "gold price breaking news",
                "Bitcoin cryptocurrency market breaking",
            ]
        elif upcoming_4hr:
            # ═══ TIER 2: PRE-EVENT MODE ═══
            # High-impact event within 4 hours — Tavily every 2 hours
            cache_seconds = 1800          # 30 min cache (check more often)
            tavily_interval = 7200        # Tavily every 2 hours
            time_since_tavily = (now - self.last_tavily_fetch_time).total_seconds()
            use_tavily_now = time_since_tavily >= tavily_interval
            search_tier = "PRE-EVENT"
            
            # Build targeted queries based on upcoming events
            event_names = [e['name'] for e in upcoming_4hr[:3]]
            queries = [f"{name} latest news" for name in event_names]
            if not queries:
                queries = ["forex economic event news today"]
        else:
            # ═══ TIER 1: NORMAL MODE ═══
            # No events near — DuckDuckGo default, Tavily 1x per 4hr cycle
            cache_seconds = 14300         # ~4 hrs cache
            tavily_interval = 14400       # Tavily once per 4 hours
            time_since_tavily = (now - self.last_tavily_fetch_time).total_seconds()
            use_tavily_now = time_since_tavily >= tavily_interval
            search_tier = "NORMAL"
            queries = ["forex and crypto market news today"]
        
        # ── Check cache — skip if fresh data exists ───────────────────
        if (now - self.last_news_fetch_time).total_seconds() < cache_seconds:
            return self.cached_news_items, self.cached_fundamental_report
        
        # ── Set search provider for this cycle ────────────────────────
        if use_tavily_now and has_tavily_key:
            self.web_search.use_tavily = True
            provider = "Tavily"
        else:
            self.web_search.use_tavily = False
            provider = "DuckDuckGo"
        
        event_info = ""
        if upcoming_4hr:
            next_event = upcoming_4hr[0]
            event_info = f" | Next: {next_event['name']} in ~{next_event['minutes_until']:.0f}min"
        
        print(f"    Search Tier: {search_tier} | Provider: {provider}{event_info}")

        # ── Execute searches ──────────────────────────────────────────
        all_news: list[dict] = []
        for q in queries:
            try:
                results = self.web_search.search_news(q, max_results=3)
                all_news.extend(results)
            except Exception as e:
                print(f"    [WARN] Web search failed for '{q}': {e}")

        if not all_news:
            return [], "No news data available. Technical analysis only."
        
        # ── Track Tavily usage timestamp ──────────────────────────────
        if provider == "Tavily":
            self.last_tavily_fetch_time = now

        # ── Run FinBERT sentiment ─────────────────────────────────────
        sentiment_summary = "Sentiment: N/A (FinBERT not loaded)"
        try:
            if self.sentiment_analyzer is None:
                print("    Loading FinBERT (first time — may take ~30s)...")
                self.sentiment_analyzer = NewsSentimentAnalyzer()

            sentiment_result = self.sentiment_analyzer.analyze_headlines(all_news)

            # Add sentiment data back into each news item for RAG storage
            for i, detail in enumerate(sentiment_result.get("details", [])):
                if i < len(all_news):
                    all_news[i]["sentiment"] = detail.get("sentiment", "neutral")
                    all_news[i]["score"]     = detail.get("score", 0.0)

            sentiment_summary = (
                f"Overall Sentiment: {sentiment_result['overall_sentiment'].upper()} "
                f"(Score: {sentiment_result['average_score']:.2f})"
            )
        except Exception as e:
            sentiment_summary = f"Sentiment analysis error: {e}"

        headlines = "\n".join(
            [f"  - {n.get('title', 'N/A')} [{n.get('sentiment', '?').upper()}] ({n.get('source', '?')})"
             for n in all_news[:8]]
        )
        
        upcoming_events = self.calendar.get_upcoming_high_impact_events(minutes_ahead=60)
        calendar_bias = self.calendar.generate_pre_event_bias(upcoming_events)
        
        report = ""
        if calendar_bias:
            report += f"{calendar_bias}\n\n"
            
        report += (
            f"=== LIVE NEWS HEADLINES ===\n{headlines}\n\n"
            f"=== SENTIMENT ===\n{sentiment_summary}\n"
            f"=== SEARCH MODE ===\n{search_tier} | Provider: {provider}"
        )
        
        self.last_news_fetch_time = now
        self.cached_news_items = all_news
        self.cached_fundamental_report = report
        
        return all_news, report

    def _format_quant_report(self, signals: list[dict], selected_candidate=None) -> str:
        """Format strategy signals into a readable report for the LLM."""
        lines = [f"Total signals generated: {len(signals)}\n"]
        if selected_candidate is not None:
            lines.append(f"SELECTED candidate_id={selected_candidate.candidate_id}; "
                         f"pair={selected_candidate.pair}; strategy={selected_candidate.strategy}; "
                         f"side={selected_candidate.direction}. BUY/SELL must echo this exact identity. "
                         "Otherwise choose HOLD. Other signals are context only. SL/TP suggestions are advisory.")
        for i, sig in enumerate(signals[:5]):
            lines.append(
                f"#{i+1} [{sig['strategy']}] {sig.get('direction','?')} | "
                f"Confidence: {sig['confidence']}% | "
                f"Entry: {sig.get('entry_price', 'N/A')} | "
                f"SL: {sig.get('stop_loss', 'N/A')} | "
                f"TP: {sig.get('take_profit', 'N/A')} | "
                f"R:R = {sig.get('risk_reward', 'N/A')}\n"
                f"   Reasoning: {str(sig.get('reasoning', 'N/A'))[:120]}..."
            )
        return "\n".join(lines)

    def _log_decision(
        self,
        decision: TradeDecision,
        outcome: str,
        trade: TradeRecord = None,
        grounding_log: dict = None,
        debate_result=None,
    ):
        """Commit audit evidence before updating the legacy JSON projection."""
        now = self.clock.now_utc()
        decision.pair = self.symbol_registry.canonical(decision.pair)
        run = None if self._active_run_id else RunRecord(
            mode=self.execution_policy.mode, purpose="decision", created_at=now)
        run_id = self._active_run_id or run.run_id
        event_id = uuid4()
        entry = {
            "timestamp":       now.isoformat(),
            "run_id":          str(run_id),
            "event_id":        str(event_id),
            "candidate_id":    str(decision.candidate_id) if decision.candidate_id else None,
            "advisory_prices": {"sl": str(decision.suggested_sl)[:100], "tp": str(decision.suggested_tp)[:100]},
            "pair":            decision.pair,
            "broker_symbol":   self.symbol_registry.broker_symbol(decision.pair),
            "action":          decision.action,
            "confidence":      decision.confidence,
            "reasoning":       decision.reasoning,
            "strategy_used":   decision.strategy_used,
            "rag_sources":     decision.rag_sources_cited,
            "win_rate_cited":  decision.historical_win_rate,
            "hallucination":   decision.hallucination_risk,
            "outcome":         outcome,
            "llm_provider":    self.llm_provider.get_active_provider_name(),
            "grounding":       grounding_log or {},
        }
        if trade:
            entry["trade"] = {
                "trade_id":    trade.trade_id,
                "lot_size":    trade.lot_size,
                "entry_price": trade.entry_price,
                "stop_loss":   trade.stop_loss,
                "take_profit": trade.take_profit,
                "sizing":      trade.sizing_provenance,
            }

        # Include debate transcript if this was a Gold debate decision
        if debate_result is not None:
            try:
                entry["debate"] = debate_result.to_log_dict()
            except Exception:
                entry["debate"] = {
                    "debate_successful": getattr(debate_result, "debate_successful", False),
                    "models_participated": getattr(debate_result, "models_participated", []),
                }

        # Full transcripts remain in the compatibility projection. Persist a
        # bounded summary plus a digest of the exact entry for correlation.
        document = json.dumps(entry, sort_keys=True, ensure_ascii=False, allow_nan=False)
        summary = {key: entry[key] for key in ("timestamp", "run_id", "event_id", "action", "confidence")}
        for key in ("pair", "broker_symbol", "outcome", "strategy_used", "llm_provider", "reasoning"):
            summary[key] = str(entry[key])[:1000]
        summary["entry_sha256"] = hashlib.sha256(document.encode("utf-8")).hexdigest()
        summary["candidate_id"] = entry["candidate_id"]
        if grounding_log and "construction" in grounding_log:
            summary["construction"] = grounding_log["construction"]
        if grounding_log and "position_sizing" in grounding_log:
            summary["position_sizing"] = grounding_log["position_sizing"]
        if "trade" in entry:
            summary["trade"] = entry["trade"]
        self.journal.commit(run=run, events=[EventEnvelope(
            event_id=event_id, event_type="DecisionRecorded", source="engine", run_id=run_id,
            mode=self.execution_policy.mode, occurred_at=now, payload=summary)])
        self.trade_log.append(entry)
        self._save_trade_log()

    def record_closed_trade(self, trade_id: str, pnl: float, outcome_analysis: str = ""):
        """
        Call this when a trade closes. Updates Risk Agent and saves to RAG.

        Args:
            trade_id:         The trade ID from the log
            pnl:              Final profit/loss in dollars
            outcome_analysis: Optional post-mortem text
        """
        # Update risk agent state
        self.risk_agent.record_trade_closed(trade_id, pnl)

        # Find the trade in the log and memorize in RAG
        for entry in reversed(self.trade_log):
            if entry.get("trade", {}).get("trade_id") == trade_id:
                trade_data = {
                    "trade_id":     trade_id,
                    "pair":         entry["pair"],
                    "broker_symbol": entry.get("broker_symbol"),
                    "strategy_used": entry["strategy_used"],
                    "direction":    entry["action"],
                    "entry_price":  entry.get("trade", {}).get("entry_price", 0),
                    "stop_loss":    entry.get("trade", {}).get("stop_loss", 0),
                    "take_profit":  entry.get("trade", {}).get("take_profit", 0),
                    "lot_size":     entry.get("trade", {}).get("lot_size", 0),
                    "pnl":          pnl,
                    "reasoning":    entry.get("reasoning", ""),
                }
                self.rag.memorize_trade(
                    trade_data=trade_data,
                    outcome_analysis=outcome_analysis or (
                        f"{'WIN' if pnl > 0 else 'LOSS'} of ${abs(pnl):.2f}"
                    )
                )
                print(f"  Trade {trade_id} memorized in RAG DB (PnL: ${pnl:.2f})")
                
                # Check Strategy Health and Degradation
                self.performance_monitor.record_trade_outcome(
                    strategy_name=entry["strategy_used"],
                    pnl=pnl
                )
                break

    def _load_trade_log(self) -> list:
        if self.trade_log_path.exists():
            try:
                with open(self.trade_log_path, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_trade_log(self):
        with open(self.trade_log_path, "w") as f:
            json.dump(self.trade_log, f, indent=2)

    def shutdown(self):
        """Graceful shutdown."""
        try:
            if self.executor is not None:
                self.executor.disconnect()
        except BaseException:
            if self.journal is not None:
                try:
                    self.journal.close()
                except Exception:
                    print("[ERR] Journal cleanup also failed")
            raise
        else:
            if self.journal is not None:
                self.journal.close()
        print("\n  All connections closed.")


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    try:
        engine = TradingEngine()
    except (ModeError, JournalError) as error:
        print(f"[BLOCKED] {error}")
        return 1

    print("\n>> Starting DYNAMIC trading loop.")
    print("   Normal Mode: 4 hours | Sniper Mode: 2 minutes")
    print("   Press Ctrl+C to stop.\n")

    try:
        engine.run_cycle(is_high_impact=False)
        last_normal_cycle = time.time()
        while True:
            # Check if we are near a high-impact news event
            is_sniper = engine.calendar.is_news_sniper_window()
            now = time.time()
            
            if is_sniper:
                print("\n[!] HIGH FREQUENCY SNIPER MODE ACTIVE! (High-Impact News Imminent)")
                engine.run_cycle(is_high_impact=True)
                time.sleep(120)  # 2 minute loop during sniper window
                last_normal_cycle = time.time() # Reset normal timer so it doesn't trigger immediately after sniper ends
            else:
                # Normal 4 hour loop
                if now - last_normal_cycle >= 14400:
                    engine.run_cycle(is_high_impact=False)
                    last_normal_cycle = time.time()
                time.sleep(1)  # Sleep briefly to prevent 100% CPU usage
                
    except KeyboardInterrupt:
        print("\n\n[STOP] Received stop signal. Shutting down...")
        print("   Open positions are NOT closed (SL/TP remain active at broker).")
        print("   Trade log saved to trade_log.json.")
    finally:
        engine.shutdown()


if __name__ == "__main__":
    sys.exit(main())
