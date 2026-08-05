"""
=============================================================================
RAG MEMORY SYSTEM — Verified Long-Term Brain (Anti-Hallucination Core)
=============================================================================
This is the SINGLE SOURCE OF TRUTH that the LLM must consult before any
trading decision. It prevents hallucination by grounding every decision in
historically verified data stored in ChromaDB.

Collections:
  1. trade_history  — Every completed trade with outcome + post-mortem
  2. news_history   — Every news event with sentiment + market impact

How Anti-Hallucination Works:
  1. Before LLM call  → RAG retrieves verified similar events from ChromaDB
  2. LLM prompt       → Forces LLM to cite RAG IDs it used
  3. After LLM call   → GroundingValidator checks citations are real
  4. Mismatch found   → Trade is automatically forced to HOLD
=============================================================================
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

# RAG-specific imports with graceful fallback
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class TradingRAG:
    """
    Retrieval-Augmented Generation (RAG) for grounded trading decisions.

    Two collections:
      - trade_history: past trades with Win/Loss outcomes
      - news_history:  past news events with market impact

    Every query returns documents WITH distance scores so the grounding
    validator knows how relevant the retrieved memory actually is.
    """

    # Distance threshold — memories beyond this are "too different" to be reliable
    MAX_RELEVANCE_DISTANCE = 1.2

    def __init__(self, db_path: str = "rag_system/chroma_db"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        if not CHROMADB_AVAILABLE:
            print("⚠️  [RAG] chromadb not installed. RAG will be disabled.")
            self.enabled = False
            return

        self.enabled = True

        # Use a fast, local embedding model — no API cost, no hallucination risk
        self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Persistent local ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.db_path))

        # Collection 1: Completed trades
        self.trade_memory = self.client.get_or_create_collection(
            name="trade_history",
            embedding_function=self._embed_fn,
            metadata={"description": "Historical trade outcomes by pair and strategy"}
        )

        # Collection 2: News events + their market impact
        self.news_memory = self.client.get_or_create_collection(
            name="news_history",
            embedding_function=self._embed_fn,
            metadata={"description": "News events and observed market reactions"}
        )

        trade_count = self.trade_memory.count()
        news_count = self.news_memory.count()
        print(f"  🧠 RAG System ready | Trades in memory: {trade_count} | News events: {news_count}")

    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================

    def memorize_trade(self, trade_data: dict, outcome_analysis: str):
        """
        Saves a completed trade and its outcome to the vector database.
        Called by main.py after a trade closes (win or loss).

        Args:
            trade_data: dict with keys: trade_id, pair, strategy_used,
                        direction, entry_price, stop_loss, take_profit,
                        lot_size, pnl, reasoning, open_time, close_time
            outcome_analysis: Human-readable post-mortem of what happened
        """
        if not self.enabled:
            return

        trade_id = trade_data.get("trade_id", f"trade_{datetime.now().timestamp()}")
        pair      = trade_data.get("pair", "UNKNOWN")
        strategy  = trade_data.get("strategy_used", "UNKNOWN")
        direction = trade_data.get("direction", "UNKNOWN")
        pnl       = float(trade_data.get("pnl", 0.0))
        is_win    = pnl > 0
        rr        = trade_data.get("risk_reward", 0.0)
        reasoning = trade_data.get("reasoning", "")

        # Build the searchable text that will be embedded in ChromaDB
        text_content = (
            f"[TRADE] {direction} {pair} via {strategy}. "
            f"Outcome: {'WIN' if is_win else 'LOSS'} (PnL: ${pnl:.2f}). "
            f"R:R achieved: {rr}. "
            f"LLM Reasoning: {reasoning[:300]}. "
            f"Post-mortem: {outcome_analysis}"
        )

        metadata = {
            "pair":       pair,
            "strategy":   strategy,
            "direction":  direction,
            "is_win":     str(is_win),  # ChromaDB requires str for bool
            "pnl":        round(pnl, 4),
            "timestamp":  datetime.now().isoformat(),
            "doc_type":   "trade"
        }

        try:
            # upsert handles duplicate trade_ids gracefully
            self.trade_memory.upsert(
                documents=[text_content],
                metadatas=[metadata],
                ids=[trade_id]
            )
            print(f"  💾 [RAG] Memorized trade: {trade_id} | {'✅ WIN' if is_win else '❌ LOSS'}")
        except Exception as e:
            print(f"  ⚠️  [RAG] Failed to memorize trade {trade_id}: {e}")

    def memorize_news(self, news_items: list[dict], pair: str, market_reaction: str = ""):
        """
        Saves news events and their observed market reaction to vector DB.
        Called by main.py after each news cycle.

        Args:
            news_items:      list of {title, body, url, sentiment, score}
            pair:            the pair most affected (e.g., 'EURUSD')
            market_reaction: short description of what price actually did
        """
        if not self.enabled or not news_items:
            return

        for item in news_items:
            title     = item.get("title", "")
            body      = item.get("body", "")[:300]
            sentiment = item.get("sentiment", "neutral")
            score     = float(item.get("score", 0.0))
            url       = item.get("url", "")

            if not title:
                continue

            # Unique ID based on title hash to avoid duplicates
            doc_id = "news_" + hashlib.md5(title.encode()).hexdigest()[:12]

            text_content = (
                f"[NEWS] Headline: {title}. "
                f"Summary: {body}. "
                f"FinBERT Sentiment: {sentiment} (score: {score:.2f}). "
                f"Affected pair: {pair}. "
                f"Observed market reaction: {market_reaction if market_reaction else 'Not recorded.'}"
            )

            metadata = {
                "pair":      pair,
                "sentiment": sentiment,
                "score":     round(score, 4),
                "url":       url[:200],
                "timestamp": datetime.now().isoformat(),
                "doc_type":  "news"
            }

            try:
                self.news_memory.upsert(
                    documents=[text_content],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
            except Exception as e:
                print(f"  ⚠️  [RAG] Failed to save news item: {e}")

        print(f"  💾 [RAG] Memorized {len(news_items)} news items for {pair}")

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    def recall_similar_trades(
        self,
        pair: str,
        strategy: str,
        current_context: str,
        n_results: int = 5
    ) -> dict:
        """
        Retrieves the most similar historical trades from ChromaDB.

        Returns:
            {
              "summary":       str (formatted block for LLM prompt),
              "win_rate":      float (0.0 to 1.0),
              "total_found":   int,
              "doc_ids":       list[str],  ← used by GroundingValidator
              "distances":     list[float],
              "is_cold_start": bool  (True if < 3 records found)
            }
        """
        if not self.enabled:
            return self._empty_recall("RAG disabled")

        # Minimum records needed for a statistically reliable win rate
        MIN_RECORDS = 3
        total_in_db = self.trade_memory.count()

        if total_in_db == 0:
            return self._empty_recall("No trade history yet (cold start)")

        query = (
            f"Trading {pair} using {strategy}. "
            f"Market context: {current_context[:200]}"
        )

        try:
            # Filter by pair when possible to improve relevance
            where_filter = {"pair": pair} if total_in_db >= MIN_RECORDS else None

            results = self.trade_memory.query(
                query_texts=[query],
                n_results=min(n_results, total_in_db),
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            docs      = results["documents"][0]
            metas     = results["metadatas"][0]
            distances = results["distances"][0]
            ids       = results["ids"][0]

            if not docs:
                return self._empty_recall("No similar trades found for this pair")

            # Filter out low-relevance results
            relevant = [
                (d, m, dist, id_)
                for d, m, dist, id_ in zip(docs, metas, distances, ids)
                if dist <= self.MAX_RELEVANCE_DISTANCE
            ]

            if not relevant:
                return self._empty_recall(
                    f"Retrieved {len(docs)} memories but none were sufficiently similar "
                    f"(all distances > {self.MAX_RELEVANCE_DISTANCE})"
                )

            wins      = sum(1 for _, m, _, _ in relevant if m.get("is_win") == "True")
            total     = len(relevant)
            win_rate  = wins / total

            # Build the formatted summary block for the LLM
            lines = [
                f"=== RAG VERIFIED TRADE MEMORY ({total} similar trades) ===",
                f"Historical Win Rate for {pair}/{strategy}: {win_rate*100:.1f}% ({wins}W/{total-wins}L)",
                ""
            ]
            for i, (doc, meta, dist, id_) in enumerate(relevant, 1):
                status = "✅ WIN" if meta.get("is_win") == "True" else "❌ LOSS"
                relevance = "HIGH" if dist < 0.6 else "MEDIUM" if dist < 1.0 else "LOW"
                lines.append(
                    f"[MEM-{i}] ID={id_} | {status} | "
                    f"Relevance: {relevance} (dist={dist:.3f})\n"
                    f"  {doc[:200]}..."
                )

            lines.append(
                f"\n⚠️  INSTRUCTION: You MUST cite the memory IDs above (e.g., 'MEM-1') "
                f"in your rag_sources_cited field. Do NOT invent win rates."
            )

            return {
                "summary":       "\n".join(lines),
                "win_rate":      win_rate,
                "total_found":   total,
                "doc_ids":       ids,
                "distances":     distances,
                "is_cold_start": total < MIN_RECORDS
            }

        except Exception as e:
            print(f"  ⚠️  [RAG] Trade recall failed: {e}")
            return self._empty_recall(f"Recall error: {e}")

    def recall_similar_news(
        self,
        query_text: str,
        pair: str,
        n_results: int = 3
    ) -> dict:
        """
        Retrieves historically similar news events and their market impacts.

        Returns same structure as recall_similar_trades.
        """
        if not self.enabled:
            return self._empty_recall("RAG disabled")

        total_in_db = self.news_memory.count()
        if total_in_db == 0:
            return self._empty_recall("No news history yet")

        try:
            results = self.news_memory.query(
                query_texts=[query_text],
                n_results=min(n_results, total_in_db),
                include=["documents", "metadatas", "distances"]
            )

            docs      = results["documents"][0]
            metas     = results["metadatas"][0]
            distances = results["distances"][0]
            ids       = results["ids"][0]

            if not docs:
                return self._empty_recall("No similar news events found")

            relevant = [
                (d, m, dist, id_)
                for d, m, dist, id_ in zip(docs, metas, distances, ids)
                if dist <= self.MAX_RELEVANCE_DISTANCE
            ]

            if not relevant:
                return self._empty_recall("News found but not sufficiently similar")

            sentiments = [m.get("sentiment", "neutral") for _, m, _, _ in relevant]
            bullish = sentiments.count("positive")
            bearish = sentiments.count("negative")

            lines = [
                f"=== RAG VERIFIED NEWS MEMORY ({len(relevant)} similar events) ===",
                f"Historical bias: {bullish} bullish events / {bearish} bearish events",
                ""
            ]
            for i, (doc, meta, dist, id_) in enumerate(relevant, 1):
                lines.append(
                    f"[NEWS-{i}] ID={id_} | Sentiment: {meta.get('sentiment','?').upper()} | "
                    f"dist={dist:.3f}\n"
                    f"  {doc[:200]}..."
                )

            lines.append(
                f"\n⚠️  INSTRUCTION: Reference these news memories by ID in rag_sources_cited."
            )

            return {
                "summary":       "\n".join(lines),
                "win_rate":      0.0,
                "total_found":   len(relevant),
                "doc_ids":       ids,
                "distances":     distances,
                "is_cold_start": len(relevant) < 2
            }

        except Exception as e:
            print(f"  ⚠️  [RAG] News recall failed: {e}")
            return self._empty_recall(f"News recall error: {e}")

    def get_strategy_win_rate(self, pair: str, strategy: str) -> Optional[float]:
        """
        Returns exact win rate for a given pair+strategy from ChromaDB.
        Used by GroundingValidator to verify LLM's stated win rate.
        Returns None if insufficient data (< 3 trades).
        """
        if not self.enabled:
            return None

        try:
            total_in_db = self.trade_memory.count()
            if total_in_db < 3:
                return None

            results = self.trade_memory.get(
                where={"pair": pair},
                include=["metadatas"]
            )

            if not results["metadatas"]:
                return None

            strat_trades = [
                m for m in results["metadatas"]
                if strategy.lower() in m.get("strategy", "").lower()
            ]

            if len(strat_trades) < 3:
                return None

            wins = sum(1 for m in strat_trades if m.get("is_win") == "True")
            return wins / len(strat_trades)

        except Exception as e:
            print(f"  ⚠️  [RAG] Win rate calc failed: {e}")
            return None

    def get_db_stats(self) -> dict:
        """Returns statistics about the RAG database state."""
        if not self.enabled:
            return {"enabled": False}
        return {
            "enabled":       True,
            "trade_records": self.trade_memory.count(),
            "news_records":  self.news_memory.count(),
            "db_path":       str(self.db_path)
        }

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _empty_recall(self, reason: str) -> dict:
        return {
            "summary":       f"=== RAG MEMORY ===\nNo verified history available: {reason}.",
            "win_rate":      0.0,
            "total_found":   0,
            "doc_ids":       [],
            "distances":     [],
            "is_cold_start": True
        }
