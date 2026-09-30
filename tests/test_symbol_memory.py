"""Exercise memory filters without constructing a database or embedding model."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from broker_mt5.symbols import SymbolRegistry
from rag_system.memory_engine import TradingRAG


class Collection:
    def __init__(self, rows):
        self.rows = rows
        self.upsert = Mock()
        self.filters = []

    def count(self):
        return len(self.rows)

    def get(self, *, where, include):
        from chromadb.api.types import validate_where
        validate_where(where)
        self.filters.append(where)
        clauses = where.get("$and", [where])
        def matches_filter(row):
            return all(row.get(key) in value["$in"] if isinstance(value, dict) else row.get(key) == value
                       for clause in clauses for key, value in clause.items())
        matches = [(key, row) for key, row in self.rows.items() if matches_filter(row)]
        return {"ids": [key for key, _ in matches], "metadatas": [row for _, row in matches]}

    def query(self, *, where, n_results, **kwargs):
        result = self.get(where=where, include=[])
        ids = result["ids"][:n_results]
        return {"ids": [ids], "metadatas": [result["metadatas"][:n_results]],
                "documents": [["Fixture evidence " + key for key in ids]],
                "distances": [[0.1] * len(ids)]}


@pytest.fixture
def memory():
    instance = TradingRAG.__new__(TradingRAG)
    instance.symbol_registry = SymbolRegistry()
    instance.enabled = True
    instance.trade_memory = Collection({
        "old": {"pair": "GOLD.i#", "strategy": "fixture", "is_win": "True"},
        "new": {"pair": "XAUUSD", "strategy": "fixture", "is_win": "False"},
        "third": {"pair": "XAUUSD", "strategy": "fixture", "is_win": "True"},
        "other": {"pair": "XAGUSD", "strategy": "fixture", "is_win": "True"},
    })
    instance.news_memory = Collection({
        "global": {"pair": "GLOBAL", "sentiment": "neutral"},
        "oldnews": {"pair": "GOLD.i#", "sentiment": "positive"},
        "othernews": {"pair": "XAGUSD", "sentiment": "negative"},
    })
    return instance


def test_legacy_and_canonical_memory_union_preserves_ids_and_population(memory):
    before = deepcopy(memory.trade_memory.rows)
    result = memory.recall_similar_trades("XAUUSD", "fixture", "context")
    assert set(result["doc_ids"]) == {"old", "new", "third"}
    assert result["total_found"] == 3
    assert result["win_rate"] == pytest.approx(2 / 3)
    assert memory.get_strategy_win_rate("GOLD.i#", "fixture") == pytest.approx(2 / 3)
    assert memory.trade_memory.rows == before
    assert len(memory.trade_memory.filters) == 2  # One union query per call, no duplicated aliases.


def test_sparse_memory_does_not_mix_other_instruments(memory):
    memory.trade_memory.rows = {key: row for key, row in memory.trade_memory.rows.items() if key in {"old", "other"}}
    result = memory.recall_similar_trades("XAUUSD", "fixture", "context")
    assert result["doc_ids"] == ["old"]
    assert result["is_cold_start"]


def test_new_writes_canonicalize_without_mutating_input(memory):
    trade = {"pair": "GOLD.i#", "trade_id": "write", "pnl": 1, "broker_symbol": "GOLD.i#"}
    memory.memorize_trade(trade, "fixture outcome")
    metadata = memory.trade_memory.upsert.call_args.kwargs["metadatas"][0]
    assert metadata["pair"] == "XAUUSD" and metadata["broker_symbol"] == "GOLD.i#"
    assert trade["pair"] == "GOLD.i#"
    for pair in ("GOLD.i#", "GLOBAL"):
        memory.memorize_news([{"title": "fixture"}], pair)
        metadata = memory.news_memory.upsert.call_args.kwargs["metadatas"][0]
        assert metadata["pair"] == ("GLOBAL" if pair == "GLOBAL" else "XAUUSD")


def test_news_union_includes_global_but_not_unrelated_instruments(memory):
    result = memory.recall_similar_news("fixture", "XAUUSD")
    assert set(result["doc_ids"]) == {"global", "oldnews"}


def test_candidate_memory_requires_exact_strategy_identity(memory):
    memory.trade_memory.rows["variant"] = {"pair": "XAUUSD", "strategy": "fixture_variant", "is_win": "True"}
    recalled = memory.recall_similar_trades("XAUUSD", "fixture", "context")
    assert "variant" not in recalled["doc_ids"]
    assert memory.get_strategy_win_rate("XAUUSD", "fixture") == pytest.approx(2/3)
