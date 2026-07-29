"""
=============================================================================
RAG MEMORY SYSTEM — The Bot's Long-Term Brain
=============================================================================
This module gives the trading agent "long-term memory."
Instead of just reacting to the current 15-minute candle, it can remember:
- "Last time the Fed raised rates, Gold dropped 2%."
- "The SMC Liquidity Sweep strategy failed the last 3 times on EURUSD."
- "A month ago, the ECB mentioned easing policy."

How it works:
1. Every time a trade closes, the result is saved to the RAG database.
2. Every time major news hits, it is embedded into the RAG database.
3. Before the LLM makes a decision, it "queries" this database to find
   historically similar situations.
=============================================================================
"""

import os
import json
from pathlib import Path
from datetime import datetime

# RAG specific imports
try:
    import chromadb
    from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
    from langchain.docstore.document import Document
except ImportError:
    chromadb = None


class TradingRAG:
    """Retrieval-Augmented Generation (RAG) for historical trade context."""

    def __init__(self, db_path: str = "rag_system/chroma_db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        if chromadb is None:
            print("⚠️ [RAG] chromadb or langchain not installed. RAG will be disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # Initialize ChromaDB local client
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Use a small, fast local embedding model (no API cost)
        self.embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Create or load collections
        self.trade_memory = self.client.get_or_create_collection(
            name="trade_history",
            embedding_function=self.embedding_function.embed_documents
        )
        self.news_memory = self.client.get_or_create_collection(
            name="news_history",
            embedding_function=self.embedding_function.embed_documents
        )
        
        print("  🧠 RAG System initialized (Local Vector Database)")

    def memorize_trade(self, trade_data: dict, outcome_analysis: str):
        """Save a completed trade and its post-mortem analysis to memory."""
        if not self.enabled: return
        
        doc_id = trade_data.get("trade_id", f"trade_{datetime.now().timestamp()}")
        pair = trade_data.get("pair", "UNKNOWN")
        strategy = trade_data.get("strategy_used", "UNKNOWN")
        pnl = trade_data.get("pnl", 0.0)
        
        # The text the LLM will search against
        text_content = (
            f"Trade on {pair} using {strategy}. "
            f"Outcome: {'WIN' if pnl > 0 else 'LOSS'} (${pnl}).\n"
            f"Context: {trade_data.get('reasoning', '')}\n"
            f"Post-Mortem: {outcome_analysis}"
        )
        
        metadata = {
            "pair": pair,
            "strategy": strategy,
            "is_win": bool(pnl > 0),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            self.trade_memory.add(
                documents=[text_content],
                metadatas=[metadata],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"  ⚠️ [RAG] Failed to memorize trade: {e}")

    def recall_similar_trades(self, pair: str, strategy: str, current_context: str, n_results: int = 3) -> str:
        """Ask the memory: 'Have we seen a setup like this before?'"""
        if not self.enabled: return "RAG memory disabled."
        
        # Search query
        query = f"Trading {pair} using {strategy}. Context: {current_context}"
        
        try:
            results = self.trade_memory.query(
                query_texts=[query],
                n_results=n_results,
                # Optionally filter by pair
                where={"pair": pair}
            )
            
            if not results["documents"] or not results["documents"][0]:
                return "No similar historical trades found in memory."
                
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            
            memory_summary = "=== RAG MEMORY (Similar Past Trades) ===\n"
            wins = 0
            for doc, meta in zip(docs, metadatas):
                status = "✅ WIN" if meta["is_win"] else "❌ LOSS"
                if meta["is_win"]: wins += 1
                memory_summary += f"- {status}: {doc[:200]}...\n"
                
            memory_summary += f"\nHistorical win rate for this setup: {(wins/len(docs))*100:.1f}%\n"
            return memory_summary
            
        except Exception as e:
            print(f"  ⚠️ [RAG] Recall failed: {e}")
            return "Failed to access RAG memory."
