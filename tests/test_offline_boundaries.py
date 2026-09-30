"""Prove guards reject accidental I/O, including broad application fallbacks."""

import os
import socket
import subprocess

import pytest

from tests.offline_guard import OfflineViolation


def test_network_process_and_native_broker_are_blocked():
    import MetaTrader5 as mt5
    attempts = [
        lambda: socket.create_connection(("example.invalid", 443)),
        lambda: socket.getaddrinfo("example.invalid", 443),
        lambda: subprocess.Popen(["must-not-start"]),
        lambda: os.system("must-not-start"),
        lambda: os.execl("must-not-start", "must-not-start"),
        lambda: mt5.initialize(),
        lambda: mt5.order_send({}),
    ]
    for attempt in attempts:
        with pytest.raises(OfflineViolation):
            attempt()


def test_real_application_external_constructors_cannot_escape(tmp_path):
    from agents.llm_provider import OpenAI
    from data_feeds.news_sentiment import NewsSentimentAnalyzer
    from data_feeds.web_search import WebSearchAgent
    from rag_system.memory_engine import TradingRAG

    for attempt in (
        lambda: OpenAI(api_key="synthetic-test-key"),
        lambda: NewsSentimentAnalyzer(),
        lambda: TradingRAG(str(tmp_path / "rag")),
        lambda: WebSearchAgent().search_news("offline guard probe"),
    ):
        with pytest.raises(OfflineViolation):
            attempt()


def test_only_temporary_application_writes_are_allowed(tmp_path):
    from tests.conftest import ROOT
    (tmp_path / "safe.json").write_text("{}")
    assert (tmp_path / "safe.json").read_text() == "{}"
    with pytest.raises(OfflineViolation):
        (ROOT / "trade_log.json").write_text("must never be written")
    with pytest.raises(OfflineViolation):
        (ROOT / "agents/streak_tracker.json").write_text("must never be written")


def test_dotenv_loading_is_disabled(tmp_path, monkeypatch):
    import dotenv
    path = tmp_path / ".env"
    path.write_text("OFFLINE_SENTINEL=should-not-load\n")
    monkeypatch.delenv("OFFLINE_SENTINEL", raising=False)
    assert dotenv.load_dotenv(path) is False
    assert "OFFLINE_SENTINEL" not in os.environ
