"""
=============================================================================
DASHBOARD -- Vijay's Agent | Web-Based Live Monitor
=============================================================================
Flask-powered web dashboard that serves a premium 3D glassmorphism UI.
Reads trade_log.json and exposes live data via API endpoints.

Run: python monitoring/dashboard.py
Open: http://localhost:5050
=============================================================================
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify

# -- Resolve project root --
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADE_LOG_PATH = PROJECT_ROOT / "trade_log.json"

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


def load_trade_log() -> list:
    """Load trade decisions from trade_log.json."""
    if not TRADE_LOG_PATH.exists():
        return []
    try:
        with open(TRADE_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def compute_stats(logs: list) -> dict:
    """Compute dashboard KPI stats from trade log."""
    total = len(logs)
    executed = [l for l in logs if "EXECUTED" in l.get("outcome", "")]
    holds = [l for l in logs if l.get("action") == "HOLD"]
    vetoed = [l for l in logs if "VETOED" in l.get("outcome", "")]

    # Grounding scores
    g_scores = [
        l.get("grounding", {}).get("grounding_score", 0.0)
        for l in logs if l.get("grounding")
    ]
    avg_grounding = sum(g_scores) / len(g_scores) if g_scores else 0.0

    # Unique RAG sources
    all_sources = []
    for l in logs:
        all_sources.extend(l.get("rag_sources", []))
    unique_sources = len(set(all_sources))

    # Debate stats
    debates = [l for l in logs if l.get("debate", {}).get("debate_successful")]
    debate_models = set()
    for l in logs:
        debate_models.update(l.get("debate", {}).get("models_participated", []))

    # Provider usage
    providers = set(l.get("llm_provider", "") for l in logs if l.get("llm_provider"))

    return {
        "total_decisions": total,
        "executed_trades": len(executed),
        "holds": len(holds),
        "vetoed": len(vetoed),
        "avg_grounding_score": round(avg_grounding, 3),
        "unique_rag_sources": unique_sources,
        "debates_completed": len(debates),
        "debate_model_count": len(debate_models),
        "debate_models": list(debate_models),
        "active_providers": list(providers),
    }


def get_recent_decisions(logs: list, limit: int = 15) -> list:
    """Get recent decisions formatted for the frontend."""
    decisions = []
    for log in reversed(logs[-limit:]):
        ts = log.get("timestamp", "")
        time_str = ts.replace("T", " ").split(".")[0] if ts else "N/A"

        grounding = log.get("grounding", {})
        g_score = grounding.get("grounding_score", 0.0)

        rag_sources = log.get("rag_sources", [])

        decisions.append({
            "time": time_str,
            "pair": log.get("pair", "?"),
            "action": log.get("action", "?"),
            "confidence": log.get("confidence", 0),
            "grounding_score": round(g_score, 2),
            "rag_sources": rag_sources[:2],
            "outcome": log.get("outcome", "")[:60],
            "strategy": log.get("strategy_used", "?"),
            "provider": log.get("llm_provider", "?"),
        })
    return decisions


def get_latest_debate(logs: list) -> dict | None:
    """Get the most recent Gold debate for visualization."""
    for log in reversed(logs):
        if log.get("debate", {}).get("debate_successful"):
            debate = log.get("debate", {})
            return {
                "pair": log.get("pair", "?"),
                "timestamp": log.get("timestamp", "")[-8:],
                "models_participated": debate.get("models_participated", []),
                "round1_decisions": debate.get("round1_decisions", {}),
                "round2_critiques": debate.get("round2_critiques", []),
                "vote_tally": debate.get("vote_tally", {}),
                "consensus_action": debate.get("consensus_action", "?"),
                "consensus_confidence": debate.get("consensus_confidence", 0),
            }
    return None


# ========== ROUTES ==========

@app.route("/")
def index():
    return render_template("dashboard_template.html")


@app.route("/api/data")
def api_data():
    """Main API endpoint -- returns all dashboard data as JSON."""
    logs = load_trade_log()
    return jsonify({
        "stats": compute_stats(logs),
        "decisions": get_recent_decisions(logs),
        "debate": get_latest_debate(logs),
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  Vijay's Agent -- Live Dashboard")
    print("  http://localhost:5050")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5050, debug=False)
