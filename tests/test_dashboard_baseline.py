"""Test Flask in-process against temporary history, without starting a server."""

import json


def test_empty_dashboard_routes(dashboard):
    with dashboard.app.test_client() as client:
        assert client.get("/").status_code == 200
        response = client.get("/api/data")
    assert response.status_code == 200
    data = response.get_json()
    assert {"stats", "decisions", "debate", "server_time"} == data.keys()
    assert data["stats"]["total_decisions"] == 0
    assert data["decisions"] == []
    assert data["debate"] is None


def test_dashboard_projects_known_decisions(dashboard):
    records = [
        {"timestamp": "2026-01-01T10:00:00", "pair": "EURUSD", "action": "BUY",
         "outcome": "EXECUTED [TEST]", "grounding": {"grounding_score": 0.8},
         "rag_sources": ["fixture-1"], "llm_provider": "offline-fixture"},
        {"timestamp": "2026-01-01T11:00:00", "pair": "XAUUSD", "action": "HOLD",
         "outcome": "HOLD", "grounding": {"grounding_score": 1.0}},
        {"timestamp": "2026-01-01T12:00:00", "pair": "EURUSD", "action": "BUY",
         "outcome": "VETOED by Risk Agent", "grounding": {"grounding_score": 0.9}},
    ]
    dashboard.TRADE_LOG_PATH.write_text(json.dumps(records), encoding="utf-8")
    with dashboard.app.test_client() as client:
        data = client.get("/api/data").get_json()
    assert data["stats"]["total_decisions"] == 3
    assert data["stats"]["executed_trades"] == 1
    assert data["stats"]["holds"] == 1
    assert data["stats"]["vetoed"] == 1
    assert data["stats"]["avg_grounding_score"] == 0.9
    assert data["stats"]["active_providers"] == ["offline-fixture"]
    assert data["decisions"][0]["outcome"] == "VETOED by Risk Agent"
