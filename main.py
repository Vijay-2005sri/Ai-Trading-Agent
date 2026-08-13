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

# ── Load environment ────────────────────────────────────────────────────────
load_dotenv()

# ── Project imports ─────────────────────────────────────────────────────────
from data_feeds.mt5_market_data import MT5DataFetcher
from data_feeds.web_search import WebSearchAgent
from data_feeds.news_sentiment import NewsSentimentAnalyzer
from data_feeds.economic_calendar import EconomicCalendar

from strategy_library.strategy_master import run_all_strategies, get_strategy_summary
from data.observation_logger import ObservationLogger
from monitoring.performance_monitor import PerformanceMonitor

from agents.llm_provider import LLMProvider, TradeDecision
from agents.risk_agent import RiskAgent, TradeRecord

from rag_system.memory_engine import TradingRAG
from rag_system.grounding_validator import GroundingValidator

from broker_mt5.order_executor import OrderExecutor


# ===========================================================================
# CONFIGURATION
# ===========================================================================

def load_config() -> dict:
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


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
            decision.pair = pair  # Ensure pair is always set correctly
            return decision

        except Exception as e:
            print(f"  ❌ Brain evaluation failed: {e}")
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


# ===========================================================================
# MAIN TRADING ENGINE
# ===========================================================================

class TradingEngine:
    """
    The fully connected orchestration engine.

    Pipeline: data_feeds → strategy_library → rag_system → agents → broker_mt5 → monitoring
    """

    def __init__(self):
        print("=" * 65)
        print("  🧠 ADVANCED AI TRADING AGENT — FULLY INTEGRATED SYSTEM")
        print("=" * 65)

        # ── Config ──────────────────────────────────────────────────────────
        self.config    = load_config()
        self.symbols   = self.config["broker"]["symbols"]
        self.demo_mode = self.config["broker"].get("demo_mode", True)

        # ── Data Feeds ──────────────────────────────────────────────────────
        print("\n[1/6] Initializing Data Feeds...")
        self.mt5_fetcher = MT5DataFetcher(
            login=int(os.getenv("MT5_LOGIN", "0")),
            password=os.getenv("MT5_PASSWORD", ""),
            server=os.getenv("MT5_SERVER", "XMGlobal-MT5"),
            path=os.getenv("MT5_PATH", None)
        )
        self.web_search = WebSearchAgent(use_tavily=bool(os.getenv("TAVILY_API_KEY")))
        self.sentiment_analyzer = None  # Lazy load — FinBERT is heavy
        self.calendar = EconomicCalendar()
        self.calendar.fetch_calendar()
        print("  ✅ MT5 Data Fetcher ready")
        print("  ✅ Web Search Agent ready")
        print("  ✅ Economic Calendar loaded")
        print("  ⏳ FinBERT will load on first news analysis")

        # ── RAG Memory System ───────────────────────────────────────────────
        print("\n[2/6] Initializing RAG Memory System...")
        rag_db_path = self.config.get("rag", {}).get("db_path", "rag_system/chroma_db")
        self.rag    = TradingRAG(db_path=rag_db_path)

        # ── Grounding Validator ─────────────────────────────────────────────
        self.validator = GroundingValidator()
        print("  ✅ Grounding Validator ready (hallucination guard active)")

        # ── Load Trading Concepts (The "Gem" Knowledge) ──────────────────────
        print("\n[5/6] Loading Trading Concepts Knowledge...")
        self.concept_knowledge = self._load_trading_concepts()
        self.strategy_knowledge = get_strategy_summary()

        # ── LLM Provider ────────────────────────────────────────────────────
        print("\n[3/6] Initializing LLM Providers...")
        self.llm_provider = LLMProvider()

        # ── Observation Logger & Monitor ─────────────────────────────────────
        self.observation_logger = ObservationLogger()
        self.performance_monitor = PerformanceMonitor()

        # ── Brain ────────────────────────────────────────────────────────────
        print("\n[4/6] Initializing Trading Brain...")
        self.brain = TradingBrain(self.llm_provider)
        print("  ✅ Brain ready (RAG-grounded mode)")

        # ── Risk Agent ───────────────────────────────────────────────────────
        print("\n[5/6] Initializing Risk Agent...")
        self.risk_agent = RiskAgent(self.config)
        print("  ✅ Risk Agent ready")

        # ── Order Executor (Broker) ─────────────────────────────────────────
        print("\n[6/6] Initializing Order Executor...")
        self.executor = OrderExecutor(demo_mode=self.demo_mode)
        self.executor.connect(
            login=int(os.getenv("MT5_LOGIN", "0")),
            password=os.getenv("MT5_PASSWORD", ""),
            server=os.getenv("MT5_SERVER", "XMGlobal-MT5"),
            path=os.getenv("MT5_PATH", None)
        )
        print("  ✅ Order Executor ready")

        # ── Trade Log ────────────────────────────────────────────────────────
        self.trade_log_path = Path(__file__).parent / "trade_log.json"
        self.trade_log      = self._load_trade_log()

        # ── Thread Safety ────────────────────────────────────────────────────
        self._lock = threading.Lock()  # Protects RAG DB, trade_log, risk_agent
        self._max_workers = min(4, len(self.symbols))  # Parallel threads

        # ── State Caching ────────────────────────────────────────────────────
        self.last_news_fetch_time = datetime.min
        self.cached_news_items = []
        self.cached_fundamental_report = "No news data available."
        
        # ── Summary ──────────────────────────────────────────────────────────
        rag_stats = self.rag.get_db_stats()
        print("\n" + "=" * 65)
        print(f"  🟢 SYSTEM ONLINE | Mode: {'DEMO' if self.demo_mode else '⚠️ LIVE'}")
        print(f"  📊 Scanning {len(self.symbols)} symbols: {', '.join(self.symbols)}")
        print(f"  🤖 LLM: {self.llm_provider.get_active_provider_name()}")
        print(f"  🧠 RAG: {rag_stats.get('trade_records', 0)} trades | "
              f"{rag_stats.get('news_records', 0)} news events in memory")
        print(f"  🛡️  Grounding Validator: ACTIVE")
        print("=" * 65 + "\n")

    def _load_trading_concepts(self) -> str:
        """Loads the foundational trading concepts for the LLM Gem."""
        concept_path = Path(__file__).parent / "trading_concepts" / "cheat_sheet.md"
        rules_path = Path(__file__).parent / "trading_concepts" / "next_action_rules.md"
        relationships_path = Path(__file__).parent / "trading_concepts" / "concept_relationships.md"
        fundamental_path = Path(__file__).parent / "trading_concepts" / "fundamental_news_events.md"
        
        knowledge = ""
        if concept_path.exists():
            knowledge += concept_path.read_text(encoding="utf-8")
        if rules_path.exists():
            knowledge += "\n\n" + rules_path.read_text(encoding="utf-8")
        if relationships_path.exists():
            knowledge += "\n\n" + relationships_path.read_text(encoding="utf-8")
        if fundamental_path.exists():
            knowledge += "\n\n" + fundamental_path.read_text(encoding="utf-8")
            
        if not knowledge:
            print("  ⚠️ Trading concepts not found. The Brain will run without fundamental concept knowledge.")
            
        return knowledge

    # =======================================================================
    # CORE CYCLE
    # =======================================================================

    def run_cycle(self, is_high_impact: bool = False):
        """
        One full analysis cycle. Called every 15 minutes.
              e. Run Grounding Validator (deterministic hallucination check)
              f. Risk Agent approval
              g. High Conviction Hold check (for cheap commodities)
              h. Execute trade via MT5
              i. Save news and outcomes to RAG DB
        """
        cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'─' * 65}")
        print(f"  ⏰ CYCLE START: {cycle_time}")
        print(f"{'─' * 65}")

        # ── STEP 1: Fundamental Data ──────────────────────────────────────
        print(f"\n  [STEP 1] 🌐 Gathering global news & sentiment... (High Impact: {is_high_impact})")
        news_items, fundamental_report = self._gather_fundamentals(is_high_impact)

        # Save news events to RAG memory for future cycles
        if news_items:
            with self._lock:
                self.rag.memorize_news(
                    news_items=news_items,
                    pair="GLOBAL",  # Global news affects all pairs
                    market_reaction="Recorded at cycle start — market reaction TBD"
                )

        # ── STEP 2: Scan each symbol IN PARALLEL ─────────────────────────
        print(f"\n  [STEP 2] 🚀 Parallel scan: {len(self.symbols)} symbols "
              f"across {self._max_workers} threads...")

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(
                    self._analyze_symbol, symbol, fundamental_report
                ): symbol
                for symbol in self.symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    future.result()  # Raise any exception from the thread
                except Exception as e:
                    print(f"    ❌ Unhandled error analyzing {symbol}: {e}")

        print(f"\n{'─' * 65}")
        print(f"  ✅ CYCLE COMPLETE: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'─' * 65}")

    # =======================================================================
    # PER-SYMBOL ANALYSIS (runs inside a thread)
    # =======================================================================

    def _analyze_symbol(self, symbol: str, fundamental_report: str):
        """
        Full analysis pipeline for a single symbol.
        Thread-safe: uses self._lock for shared resources.
        """
        print(f"\n  {'═' * 60}")
        print(f"  [THREAD] 📈 Analyzing {symbol}...")

        # ── Get market data from MT5 ────────────────────────────────
        try:
            import MetaTrader5 as mt5
            df = self.mt5_fetcher.get_historical_data(symbol, mt5.TIMEFRAME_H1, count=200)
            if df is None or df.empty:
                print(f"    ⚠️  No data for {symbol}. Skipping.")
                return
        except Exception as e:
            print(f"    ⚠️  MT5 data error for {symbol}: {e}. Skipping.")
            return

        # ── Run all strategies (12+) ─────────────────────────────────
        print(f"    [2a] Running all strategies on {symbol}...")
        strategy_signals = run_all_strategies(df, pair=symbol)

        if not strategy_signals:
            print(f"    📭 No signals from any strategy for {symbol}.")
            return

        top_signal = strategy_signals[0]
        print(
            f"    📊 {len(strategy_signals)} signal(s) | Top: "
            f"{top_signal['strategy']} ({top_signal['confidence']}% conf)"
        )
        quant_report = self._format_quant_report(strategy_signals)

        # ── STEP 3: RAG Memory Query (thread-safe) ────────────────────
        print(f"    [2b] 🧠 Querying RAG memory for {symbol}...")
        market_context = (
            f"Price action context: {top_signal.get('reasoning', '')[:200]}"
        )

        with self._lock:
            trade_recall = self.rag.recall_similar_trades(
                pair=symbol,
                strategy=top_signal["strategy"],
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
                strategy=top_signal["strategy"]
            )

        # Build the combined grounded context block for LLM
        rag_context = (
            f"{trade_recall['summary']}\n\n"
            f"{news_recall['summary']}\n\n"
            f"Verified DB win rate for {symbol}/{top_signal['strategy']}: "
            f"{f'{actual_win_rate*100:.1f}%' if actual_win_rate is not None else 'Insufficient data'}"
        )

        cold_start = trade_recall.get("is_cold_start", True)
        print(
            f"    📚 RAG: {trade_recall['total_found']} trade memories | "
            f"{news_recall['total_found']} news memories | "
            f"{'⚠️ COLD START' if cold_start else '✅ History found'}"
        )

        # ── STEP 4: Brain (LLM) Decision ─────────────────────────────
        print(f"    [2c] 🧠 Brain evaluating {symbol} with grounded context...")
        decision = self.brain.evaluate(
            quant_report=quant_report,
            fundamental_report=fundamental_report,
            strategy_knowledge=self.strategy_knowledge,
            concept_knowledge=self.concept_knowledge,
            rag_context=rag_context,
            pair=symbol,
        )

        print(
            f"    🧠 Raw decision: {decision.action} {symbol} "
            f"(Conf: {decision.confidence}% | "
            f"Hallucination: {decision.hallucination_risk} | "
            f"RAG sources cited: {decision.rag_sources_cited})"
        )

        # ── STEP 5: Grounding Validator ───────────────────────────────
        print(f"    [2d] 🛡️  Grounding Validator running...")
        grounding_result = self.validator.validate(
            decision=decision,
            trade_recall=trade_recall,
            news_recall=news_recall,
            actual_win_rate=actual_win_rate
        )

        grounding_log = self.validator.format_log_entry(grounding_result, decision.action)
        print(
            f"    🔍 Grounding score: {grounding_result.grounding_score:.2f}/1.00 | "
            f"Checks passed: {len(grounding_result.checks_passed)} | "
            f"Failed: {len(grounding_result.checks_failed)}"
        )

        if grounding_result.override_to_hold:
            print(f"    🛡️  GROUNDING OVERRIDE → HOLD")
            print(f"    📋 Reason: {grounding_result.override_reason[:200]}")
            decision.action = "HOLD"
            with self._lock:
                self._log_decision(decision, f"GROUNDING_OVERRIDE: {grounding_result.override_reason[:150]}", grounding_log=grounding_log)
            return

        print(
            f"    ✅ Grounding passed: {decision.action} {symbol} "
            f"(Win rate cited: {decision.historical_win_rate:.1%})"
        )

        # ── STEP 6: HOLD → skip ───────────────────────────────────────
        if decision.action == "HOLD":
            print(f"    ✋ HOLD — No trade for {symbol}.")
            with self._lock:
                self._log_decision(decision, "HOLD — Brain decided to wait", grounding_log=grounding_log)
                self.observation_logger.log_from_cycle_data(
                    symbol=symbol,
                    strategy_signals=strategy_signals,
                    decision_action=decision.action,
                    decision_reasoning=decision.reasoning,
                    decision_confidence=decision.confidence,
                    grounding_score=grounding_result.grounding_score,
                    rag_win_rate=actual_win_rate,
                    timeframe="H1"
                )
            return

        # ── STEP 7: Risk Agent (thread-safe) ─────────────────────────
        print(f"    [2e] 🛡️  Risk Agent evaluating...")

        is_trending = any(
            s["confidence"] >= 80 and "Trend" in s.get("strategy", "")
            for s in strategy_signals
        )
        equity = self.executor.get_account_equity()

        with self._lock:
            risk_result = self.risk_agent.evaluate_trade(
                pair=decision.pair,
                direction=decision.action,
                entry_price=top_signal.get("entry_price", 0),
                stop_loss=decision.suggested_sl,
                take_profit=decision.suggested_tp,
                confidence=decision.confidence,
                equity=equity,
                is_trending=is_trending,
            )

        print(f"    🛡️  Risk: {risk_result.reason}")

        if not risk_result.approved:
            with self._lock:
                self._log_decision(
                    decision,
                    f"VETOED by Risk Agent: {risk_result.reason}",
                    grounding_log=grounding_log
                )
            return

        # ── STEP 7b: High Conviction Hold Check ──────────────────────
        hold_check = self.risk_agent.check_high_conviction_hold(
            pair=symbol, confidence=decision.confidence
        )
        if hold_check["allow_extended_hold"]:
            print(f"    {hold_check['reason']}")

        # ── STEP 8: Execute Trade ─────────────────────────────────────
        print(
            f"    [2f] 🚀 EXECUTING: {decision.action} {symbol} "
            f"| Lots: {risk_result.adjusted_lot_size}"
        )

        trade_record = TradeRecord(
            trade_id=f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pair=symbol,
            direction=decision.action,
            entry_price=top_signal.get("entry_price", 0),
            stop_loss=decision.suggested_sl,
            take_profit=decision.suggested_tp,
            lot_size=risk_result.adjusted_lot_size,
            open_time=datetime.now().isoformat(),
        )

        order_result = self.executor.place_order(trade_record)

        with self._lock:
            if order_result["success"]:
                self.risk_agent.record_trade_opened(trade_record)
                self._log_decision(
                    decision,
                    f"EXECUTED [{order_result['mode']}]: Lots={risk_result.adjusted_lot_size} | "
                    f"Ticket={order_result.get('ticket')}"
                    f"{' | 🔥 HIGH CONVICTION HOLD ENABLED' if hold_check['allow_extended_hold'] else ''}",
                    trade=trade_record,
                    grounding_log=grounding_log
                )
                print(f"    ✅ Order placed: {order_result['reason']}")
            else:
                print(f"    ❌ Order failed: {order_result['reason']}")
                self._log_decision(
                    decision,
                    f"ORDER_FAILED: {order_result['reason']}",
                    grounding_log=grounding_log
                )

        # ── STEP 9: Log Observation for Pattern Miner ─────────────────
        with self._lock:
            self.observation_logger.log_from_cycle_data(
                symbol=symbol,
                strategy_signals=strategy_signals,
                decision_action=decision.action,
                decision_reasoning=decision.reasoning,
                decision_confidence=decision.confidence,
                grounding_score=grounding_result.grounding_score,
                rag_win_rate=actual_win_rate,
                entry_price=top_signal.get("entry_price", 0),
                stop_loss=decision.suggested_sl,
                take_profit=decision.suggested_tp,
                timeframe="H1"
            )

    # =======================================================================
    # HELPERS
    # =======================================================================

    def _gather_fundamentals(self, is_high_impact: bool = False) -> tuple[list[dict], str]:
        """
        Search web for news and run FinBERT sentiment analysis.
        Caches results for 15 minutes to save API credits, especially during sniper mode.
        Returns: (news_items_with_sentiment, formatted_report_string)
        """
        now = datetime.now()
        if (now - self.last_news_fetch_time).total_seconds() < 900:  # 15 minutes
            return self.cached_news_items, self.cached_fundamental_report

        # Optimize API credits: Only use premium Tavily search during high impact news
        if is_high_impact:
            self.web_search.use_tavily = bool(os.getenv("TAVILY_API_KEY"))
        else:
            self.web_search.use_tavily = False

        # If not high impact, limit to just 1 general query to save duckduckgo bandwidth too
        queries = [
            "forex market news today",
            "Federal Reserve interest rate decision",
            "gold price movement today",
            "Bitcoin cryptocurrency market today",
        ] if is_high_impact else ["forex and crypto market news today"]

        all_news: list[dict] = []
        for q in queries:
            try:
                results = self.web_search.search_news(q, max_results=3)
                all_news.extend(results)
            except Exception as e:
                print(f"    ⚠️  Web search failed for '{q}': {e}")

        if not all_news:
            return [], "No news data available. Technical analysis only."

        # Run FinBERT sentiment
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
            [f"  - {n.get('title', 'N/A')} [{n.get('sentiment', '?').upper()}]"
             for n in all_news[:8]]
        )
        
        upcoming_events = self.calendar.get_upcoming_high_impact_events(minutes_ahead=60)
        calendar_bias = self.calendar.generate_pre_event_bias(upcoming_events)
        
        report = ""
        if calendar_bias:
            report += f"{calendar_bias}\n\n"
            
        report += (
            f"=== LIVE NEWS HEADLINES ===\n{headlines}\n\n"
            f"=== SENTIMENT ===\n{sentiment_summary}"
        )
        
        self.last_news_fetch_time = now
        self.cached_news_items = all_news
        self.cached_fundamental_report = report
        
        return all_news, report

    def _format_quant_report(self, signals: list[dict]) -> str:
        """Format strategy signals into a readable report for the LLM."""
        lines = [f"Total signals generated: {len(signals)}\n"]
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
        grounding_log: dict = None
    ):
        """Log every decision with full XAI audit trail to trade_log.json."""
        entry = {
            "timestamp":       datetime.now().isoformat(),
            "pair":            decision.pair,
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
            }

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
                print(f"  💾 Trade {trade_id} memorized in RAG DB (PnL: ${pnl:.2f})")
                
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
        self.executor.disconnect()
        print("\n  🔌 All connections closed.")


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    engine = TradingEngine()

    print("\n🔁 Starting DYNAMIC trading loop.")
    print("   Normal Mode: 15 minutes | Sniper Mode: 2 minutes")
    print("   Press Ctrl+C to stop.\n")

    # Run immediately on startup
    engine.run_cycle(is_high_impact=False)
    last_normal_cycle = time.time()

    try:
        while True:
            # Check if we are near a high-impact news event
            is_sniper = engine.calendar.is_news_sniper_window()
            now = time.time()
            
            if is_sniper:
                print("\n⚡ HIGH FREQUENCY SNIPER MODE ACTIVE! (High-Impact News Imminent)")
                engine.run_cycle(is_high_impact=True)
                time.sleep(120)  # 2 minute loop during sniper window
                last_normal_cycle = time.time() # Reset normal timer so it doesn't trigger immediately after sniper ends
            else:
                # Normal 1 hour loop
                if now - last_normal_cycle >= 3600:
                    engine.run_cycle(is_high_impact=False)
                    last_normal_cycle = time.time()
                time.sleep(1)  # Sleep briefly to prevent 100% CPU usage
                
    except KeyboardInterrupt:
        print("\n\n🛑 Received stop signal. Shutting down...")
        print("   Open positions are NOT closed (SL/TP remain active at broker).")
        print("   Trade log saved to trade_log.json.")
    finally:
        engine.shutdown()


if __name__ == "__main__":
    main()
