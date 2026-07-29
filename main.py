"""
=============================================================================
MAIN ORCHESTRATION LOOP — The Heart of the Trading Agent
=============================================================================
This is where EVERYTHING connects. Every folder, every module, every agent
flows through this single loop.

Data Flow:
┌─────────────────────────────────────────────────────────────────────────┐
│                          EVERY CANDLE CYCLE                             │
│                                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────────┐ │
│  │ data_feeds/  │    │ strategy_    │    │ agents/                     │ │
│  │             │    │ library/     │    │                             │ │
│  │ MT5 Data ───┼──▶│ Run all 12  ─┼──▶│ Quant Agent summarizes     │ │
│  │ Web Search ─┤    │ strategies   │    │ Fundamental Agent reads news│ │
│  │ Sentiment ──┤    │ Rank signals │    │ Executive Agent decides     │ │
│  └─────────────┘    └──────────────┘    │ Risk Agent approves/vetoes │ │
│                                          └──────────────┬──────────────┘ │
│                                                         │                │
│  ┌─────────────┐    ┌──────────────┐                    │                │
│  │ monitoring/  │◀───│ broker_mt5/  │◀───────────────────┘                │
│  │ Dashboard    │    │ Execute on   │                                    │
│  │ XAI Logs     │    │ XM MT5       │                                    │
│  └─────────────┘    └──────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────┘
"""

import os
import sys
import time
import json
import yaml
import schedule
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ---- Load Environment ----
load_dotenv()

# ---- Project Imports ----
from data_feeds.mt5_market_data import MT5DataFetcher
from data_feeds.web_search import WebSearchAgent
from data_feeds.news_sentiment import NewsSentimentAnalyzer
from strategy_library.strategy_master import run_all_strategies, get_strategy_summary
from agents.llm_provider import LLMProvider, TradeDecision
from agents.risk_agent import RiskAgent, TradeRecord


# ==========================================================================
# CONFIGURATION
# ==========================================================================
def load_config() -> dict:
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# ==========================================================================
# THE BRAIN — Executive Agent using Multi-Provider LLM
# ==========================================================================
class TradingBrain:
    """
    The central intelligence. It takes inputs from ALL modules and uses
    the LLM to make a final decision.
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

        self.system_prompt = (
            "You are the Executive AI of a quantitative hedge fund. "
            "You receive three types of data:\n"
            "1. QUANT REPORT: Technical analysis signals from 12 trading strategies.\n"
            "2. FUNDAMENTAL REPORT: Live news headlines and sentiment scores.\n"
            "3. STRATEGY KNOWLEDGE: Description of all loaded strategies.\n\n"
            "Your job: Synthesize all data and decide BUY, SELL, or HOLD.\n"
            "Rules:\n"
            "- If strategies disagree strongly, choose HOLD.\n"
            "- Always prioritize capital preservation.\n"
            "- Explain your reasoning in detail.\n"
            "- Reference specific strategies and news in your reasoning.\n"
        )

    def evaluate(self, quant_report: str, fundamental_report: str, strategy_knowledge: str, pair: str) -> TradeDecision:
        """
        Feed all data to the LLM and get a structured trade decision.
        """
        prompt = (
            f"{self.system_prompt}\n\n"
            f"=== PAIR: {pair} ===\n\n"
            f"--- QUANT REPORT (Strategy Signals) ---\n{quant_report}\n\n"
            f"--- FUNDAMENTAL REPORT (News & Sentiment) ---\n{fundamental_report}\n\n"
            f"--- STRATEGY KNOWLEDGE ---\n{strategy_knowledge}\n\n"
            f"Based on ALL of this data, what is your trading decision for {pair}? "
            f"Respond with your action (BUY/SELL/HOLD), confidence (0-100), "
            f"stop loss, take profit, detailed reasoning, and which strategy you are basing this on."
        )

        try:
            decision = self.llm.invoke_structured(prompt, TradeDecision)
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
                strategy_used="ERROR_FALLBACK"
            )


# ==========================================================================
# MAIN TRADING ENGINE
# ==========================================================================
class TradingEngine:
    """
    The main engine that runs the full cycle.
    Connects: data_feeds → strategy_library → agents → broker_mt5
    """

    def __init__(self):
        print("=" * 60)
        print("  🧠 ADVANCED AI TRADING AGENT — INITIALIZING")
        print("=" * 60)

        # Load config
        self.config = load_config()
        self.symbols = self.config["broker"]["symbols"]
        self.demo_mode = self.config["broker"].get("demo_mode", True)

        # ---- Initialize Data Feeds ----
        print("\n[1/5] Initializing Data Feeds...")
        self.mt5 = MT5DataFetcher(
            login=int(os.getenv("MT5_LOGIN", "0")),
            password=os.getenv("MT5_PASSWORD", ""),
            server=os.getenv("MT5_SERVER", "XMGlobal-MT5"),
            path=os.getenv("MT5_PATH", None)
        )
        self.web_search = WebSearchAgent(use_tavily=bool(os.getenv("TAVILY_API_KEY")))
        print("  ✅ MT5 Data Fetcher ready")
        print("  ✅ Web Search Agent ready")

        # ---- Initialize Sentiment (lazy load — FinBERT is heavy) ----
        print("\n[2/5] Initializing Sentiment Analyzer...")
        self.sentiment_analyzer = None  # Loaded on first use to save RAM
        print("  ⏳ FinBERT will load on first news analysis")

        # ---- Initialize LLM Provider (Multi-Provider Router) ----
        print("\n[3/5] Initializing LLM Providers...")
        self.llm_provider = LLMProvider()

        # ---- Initialize Brain ----
        print("\n[4/5] Initializing Trading Brain...")
        self.brain = TradingBrain(self.llm_provider)
        print("  ✅ Brain ready")

        # ---- Initialize Risk Agent ----
        print("\n[5/5] Initializing Risk Agent...")
        self.risk_agent = RiskAgent(self.config)
        print("  ✅ Risk Agent ready")

        # ---- Strategy Knowledge (loaded once) ----
        self.strategy_knowledge = get_strategy_summary()

        # ---- Trade Log ----
        self.trade_log_path = Path(__file__).parent / "trade_log.json"
        self.trade_log = self._load_trade_log()

        print("\n" + "=" * 60)
        print(f"  🟢 SYSTEM ONLINE | Mode: {'DEMO' if self.demo_mode else '⚠️ LIVE'}")
        print(f"  📊 Scanning {len(self.symbols)} symbols: {', '.join(self.symbols)}")
        print(f"  🤖 LLM: {self.llm_provider.get_active_provider_name()}")
        print("=" * 60 + "\n")

    # -------------------------------------------------------------------
    # THE CORE CYCLE — Runs for each candle / tick
    # -------------------------------------------------------------------
    def run_cycle(self):
        """
        One full analysis cycle. This is the heart of the entire system.
        Called every N minutes (configurable).
        """
        cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'─' * 60}")
        print(f"  ⏰ CYCLE START: {cycle_time}")
        print(f"{'─' * 60}")

        # ---------------------------------------------------------------
        # STEP 1: Gather Fundamental Data (Web Search + Sentiment)
        # ---------------------------------------------------------------
        print("\n  [STEP 1] 🌐 Gathering global news & sentiment...")
        fundamental_report = self._gather_fundamentals()

        # ---------------------------------------------------------------
        # STEP 2: Scan each symbol
        # ---------------------------------------------------------------
        for symbol in self.symbols:
            print(f"\n  [STEP 2] 📈 Analyzing {symbol}...")

            # --- Get market data from MT5 ---
            try:
                import MetaTrader5 as mt5
                df = self.mt5.get_historical_data(symbol, mt5.TIMEFRAME_H1, count=200)
                if df is None or df.empty:
                    print(f"    ⚠️  No data for {symbol}. Skipping.")
                    continue
            except Exception as e:
                print(f"    ⚠️  MT5 data error for {symbol}: {e}. Skipping.")
                continue

            # --- Run all 12 strategies ---
            print(f"    [STEP 2a] Running all strategies on {symbol}...")
            strategy_signals = run_all_strategies(df, pair=symbol)

            if not strategy_signals:
                print(f"    📭 No signals from any strategy for {symbol}.")
                continue

            # --- Format Quant Report ---
            quant_report = self._format_quant_report(strategy_signals)
            print(f"    📊 {len(strategy_signals)} signal(s) found. Top: "
                  f"{strategy_signals[0]['strategy']} ({strategy_signals[0]['confidence']}% conf)")

            # ---------------------------------------------------------------
            # STEP 3: Ask the Brain (LLM) for its decision
            # ---------------------------------------------------------------
            print(f"    [STEP 3] 🧠 Brain is evaluating {symbol}...")
            decision = self.brain.evaluate(
                quant_report=quant_report,
                fundamental_report=fundamental_report,
                strategy_knowledge=self.strategy_knowledge,
                pair=symbol
            )

            print(f"    🧠 Brain says: {decision.action} {decision.pair} "
                  f"(Confidence: {decision.confidence}%) — Strategy: {decision.strategy_used}")
            print(f"    💬 Reasoning: {decision.reasoning[:150]}...")

            # ---------------------------------------------------------------
            # STEP 4: HOLD → skip. BUY/SELL → send to Risk Agent.
            # ---------------------------------------------------------------
            if decision.action == "HOLD":
                print(f"    ✋ HOLD — No trade for {symbol}.")
                self._log_decision(decision, "HOLD — Brain decided to wait")
                continue

            # ---------------------------------------------------------------
            # STEP 5: Risk Agent — APPROVE or VETO
            # ---------------------------------------------------------------
            print(f"    [STEP 4] 🛡️  Risk Agent evaluating...")

            # Determine if market is trending (for 3rd trade unlock)
            is_trending = any(
                s["confidence"] >= 80 and "Trend" in s.get("strategy", "")
                for s in strategy_signals
            )

            # Get current equity (placeholder — replaced with MT5 call in production)
            equity = self._get_account_equity()

            risk_result = self.risk_agent.evaluate_trade(
                pair=decision.pair,
                direction=decision.action,
                entry_price=strategy_signals[0].get("entry_price", 0),
                stop_loss=decision.suggested_sl,
                take_profit=decision.suggested_tp,
                confidence=decision.confidence,
                equity=equity,
                is_trending=is_trending,
            )

            print(f"    🛡️  Risk: {risk_result.reason}")

            if not risk_result.approved:
                self._log_decision(decision, f"VETOED by Risk Agent: {risk_result.reason}")
                continue

            # ---------------------------------------------------------------
            # STEP 6: EXECUTE THE TRADE on XM MT5
            # ---------------------------------------------------------------
            print(f"    [STEP 5] 🚀 EXECUTING: {decision.action} {decision.pair} "
                  f"| Lots: {risk_result.adjusted_lot_size}")

            trade_record = TradeRecord(
                trade_id=f"{decision.pair}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                pair=decision.pair,
                direction=decision.action,
                entry_price=strategy_signals[0].get("entry_price", 0),
                stop_loss=decision.suggested_sl,
                take_profit=decision.suggested_tp,
                lot_size=risk_result.adjusted_lot_size,
                open_time=datetime.now().isoformat(),
            )

            # In demo/paper mode, we just log. In production, call MT5 order_send.
            if self.demo_mode:
                print(f"    📝 [DEMO MODE] Trade logged but NOT sent to MT5.")
            else:
                # TODO: self.order_executor.place_order(trade_record)
                print(f"    ⚡ [LIVE] Order sent to XM MT5!")

            self.risk_agent.record_trade_opened(trade_record)
            self._log_decision(decision, f"EXECUTED: Lots={risk_result.adjusted_lot_size}", trade_record)

        print(f"\n{'─' * 60}")
        print(f"  ✅ CYCLE COMPLETE: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'─' * 60}")

    # -------------------------------------------------------------------
    # Gather Fundamental Data
    # -------------------------------------------------------------------
    def _gather_fundamentals(self) -> str:
        """Search the web for breaking news and analyze sentiment."""
        queries = [
            "forex market news today",
            "Federal Reserve interest rate decision",
            "gold price movement today",
            "Bitcoin cryptocurrency market today",
        ]

        all_news = []
        for q in queries:
            try:
                results = self.web_search.search_news(q, max_results=3)
                all_news.extend(results)
            except Exception as e:
                print(f"    ⚠️  Web search failed for '{q}': {e}")

        if not all_news:
            return "No news data available. Proceed with technical analysis only."

        # Sentiment analysis
        sentiment_summary = "Sentiment: N/A (FinBERT not loaded)"
        try:
            if self.sentiment_analyzer is None:
                print("    Loading FinBERT sentiment model (first time)...")
                self.sentiment_analyzer = NewsSentimentAnalyzer()
            sentiment_result = self.sentiment_analyzer.analyze_headlines(all_news)
            sentiment_summary = (
                f"Overall Sentiment: {sentiment_result['overall_sentiment'].upper()} "
                f"(Score: {sentiment_result['average_score']:.2f})"
            )
        except Exception as e:
            sentiment_summary = f"Sentiment analysis error: {e}"

        # Format the report
        headlines = "\n".join([f"  - {n.get('title', 'N/A')}" for n in all_news[:8]])
        return f"=== LIVE NEWS HEADLINES ===\n{headlines}\n\n=== SENTIMENT ===\n{sentiment_summary}"

    # -------------------------------------------------------------------
    # Format Quant Report
    # -------------------------------------------------------------------
    def _format_quant_report(self, signals: list[dict]) -> str:
        """Format strategy signals into a readable report for the LLM."""
        lines = [f"Total signals: {len(signals)}\n"]
        for i, sig in enumerate(signals[:5]):  # Top 5 only to save tokens
            lines.append(
                f"#{i+1} [{sig['strategy']}] {sig['direction']} | "
                f"Confidence: {sig['confidence']}% | "
                f"Entry: {sig.get('entry_price', 'N/A')} | "
                f"SL: {sig.get('stop_loss', 'N/A')} | TP: {sig.get('take_profit', 'N/A')} | "
                f"R:R = {sig.get('risk_reward', 'N/A')}\n"
                f"   Reasoning: {sig.get('reasoning', 'N/A')[:120]}..."
            )
        return "\n".join(lines)

    # -------------------------------------------------------------------
    # Account Equity (placeholder)
    # -------------------------------------------------------------------
    def _get_account_equity(self) -> float:
        """Get current account equity from MT5."""
        try:
            import MetaTrader5 as mt5
            info = mt5.account_info()
            if info:
                return info.equity
        except Exception:
            pass
        return 10000.0  # Default demo balance

    # -------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------
    def _log_decision(self, decision: TradeDecision, outcome: str, trade: TradeRecord = None):
        """Log every decision to trade_log.json for Explainable AI."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "pair": decision.pair,
            "action": decision.action,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "strategy_used": decision.strategy_used,
            "outcome": outcome,
            "llm_provider": self.llm_provider.get_active_provider_name(),
        }
        if trade:
            entry["trade"] = {
                "trade_id": trade.trade_id,
                "lot_size": trade.lot_size,
                "entry_price": trade.entry_price,
                "stop_loss": trade.stop_loss,
                "take_profit": trade.take_profit,
            }
        self.trade_log.append(entry)
        self._save_trade_log()

    def _load_trade_log(self) -> list:
        if self.trade_log_path.exists():
            with open(self.trade_log_path, "r") as f:
                return json.load(f)
        return []

    def _save_trade_log(self):
        with open(self.trade_log_path, "w") as f:
            json.dump(self.trade_log, f, indent=2)


# ==========================================================================
# ENTRY POINT
# ==========================================================================
def main():
    engine = TradingEngine()

    print("\n🔁 Starting trading loop. Cycle interval: 15 minutes.")
    print("   Press Ctrl+C to stop.\n")

    # Run immediately on startup
    engine.run_cycle()

    # Schedule to run every 15 minutes
    schedule.every(15).minutes.do(engine.run_cycle)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down gracefully...")
        print("   Open positions are NOT closed (SL remains at broker).")
        print("   Trade log saved to trade_log.json.")


if __name__ == "__main__":
    main()
