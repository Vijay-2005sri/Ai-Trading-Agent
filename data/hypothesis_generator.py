"""
=============================================================================
HYPOTHESIS GENERATOR — From Concept Combinations to Strategy Hypotheses
=============================================================================
Takes recurring patterns discovered by the PatternMiner and converts them
into formal, testable Strategy Hypothesis objects.

A hypothesis is NOT a strategy yet. It is a structured idea that must go
through the full validation pipeline (Backtest → Out-of-Sample → Paper
Trading → Approval) before it can become live code.

Pipeline position:
  PatternMiner → [HYPOTHESIS GENERATOR] → BacktestValidator → PaperTrader
=============================================================================
"""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


# Status flow:
# DISCOVERED → BACKTESTING → BACKTESTING_PASSED → VALIDATING →
# PAPER_TRADING → APPROVED → LIVE → DEGRADED → DISABLED → RETIRED
VALID_STATUSES = [
    "DISCOVERED",
    "BACKTESTING",
    "BACKTESTING_PASSED",
    "BACKTESTING_FAILED",
    "VALIDATING",
    "PAPER_TRADING",
    "APPROVED",
    "LIVE",
    "DEGRADED",
    "DISABLED",
    "RETIRED",
    "REJECTED",
]


@dataclass
class StrategyHypothesis:
    """
    A formal, testable strategy hypothesis.

    This is pure DATA — not executable code.
    It describes a potential strategy that the system discovered
    from recurring patterns in market observations.
    """

    # --- Identity ---
    hypothesis_id: str = ""             # e.g. "HYP-001"
    name: str = ""                      # Human-readable name
    version: str = "1.0"

    # --- Discovery Evidence ---
    discovered_date: str = ""
    discovery_source: str = ""          # "pattern_miner", "manual", "combination"
    evidence_summary: str = ""          # What recurring pattern was found
    observation_count: int = 0          # How many times the pattern was observed
    observed_win_rate: float = 0.0      # Win rate in observations

    # --- Strategy Definition ---
    concepts_used: list[str] = field(default_factory=list)
    # e.g. ["Liquidity_Sweep_SSL", "Bullish_FVG", "MSS", "London_Killzone"]

    trigger_conditions: list[str] = field(default_factory=list)
    # e.g. ["EQL sweep detected", "Displacement candle > 2x avg body"]

    context_filters: dict = field(default_factory=dict)
    # e.g. {"session": "london", "regime": "ranging", "instruments": ["EURUSD"]}

    entry_logic: str = ""               # Description of entry rules
    confirmation_rules: list[str] = field(default_factory=list)
    stop_loss_logic: str = ""
    take_profit_logic: str = ""
    invalidation_rules: list[str] = field(default_factory=list)

    # --- Testing Results ---
    backtest_results: dict = field(default_factory=dict)
    # e.g. {"win_rate": 62, "profit_factor": 1.8, "max_drawdown": 8.5, "total_trades": 150}

    oos_results: dict = field(default_factory=dict)       # Out-of-sample results
    paper_trade_results: dict = field(default_factory=dict)

    # --- Status ---
    status: str = "DISCOVERED"
    status_history: list[dict] = field(default_factory=list)
    # e.g. [{"status": "DISCOVERED", "date": "...", "reason": "Pattern found by miner"}]

    # --- Derived Strategy Info ---
    derived_from_strategies: list[str] = field(default_factory=list)
    # e.g. ["SMC_Liquidity_Sweep", "ICT_Silver_Bullet"] — which existing strategies inspired this

    # --- Live Code Reference (only after APPROVED) ---
    live_strategy_id: str = ""          # e.g. "STRAT_013"
    live_file_path: str = ""
    live_class_name: str = ""


class HypothesisManager:
    """
    Manages the lifecycle of all strategy hypotheses.

    Storage: data/strategy_pipeline/hypotheses.json
    """

    def __init__(self, pipeline_dir: str = None):
        if pipeline_dir:
            self.pipeline_dir = Path(pipeline_dir)
        else:
            self.pipeline_dir = Path(__file__).parent.parent / "data" / "strategy_pipeline"
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)
        self.hypotheses_file = self.pipeline_dir / "hypotheses.json"
        self._hypotheses: dict[str, StrategyHypothesis] = {}
        self._load()

    def _load(self):
        """Load hypotheses from disk."""
        if self.hypotheses_file.exists():
            with open(self.hypotheses_file, "r") as f:
                data = json.load(f)
            for hyp_id, hyp_data in data.items():
                self._hypotheses[hyp_id] = StrategyHypothesis(**hyp_data)

    def _save(self):
        """Save all hypotheses to disk."""
        data = {
            hyp_id: asdict(hyp) for hyp_id, hyp in self._hypotheses.items()
        }
        with open(self.hypotheses_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _next_id(self) -> str:
        """Generate the next hypothesis ID."""
        existing_nums = []
        for hyp_id in self._hypotheses:
            try:
                num = int(hyp_id.split("-")[1])
                existing_nums.append(num)
            except (IndexError, ValueError):
                pass
        next_num = max(existing_nums, default=0) + 1
        return f"HYP-{next_num:03d}"

    def create_hypothesis(
        self,
        name: str,
        concepts_used: list[str],
        trigger_conditions: list[str],
        entry_logic: str,
        stop_loss_logic: str,
        take_profit_logic: str,
        evidence_summary: str = "",
        observation_count: int = 0,
        observed_win_rate: float = 0.0,
        context_filters: dict = None,
        confirmation_rules: list[str] = None,
        invalidation_rules: list[str] = None,
        derived_from_strategies: list[str] = None,
        discovery_source: str = "pattern_miner",
    ) -> StrategyHypothesis:
        """Create a new hypothesis and save it."""
        hyp_id = self._next_id()

        hyp = StrategyHypothesis(
            hypothesis_id=hyp_id,
            name=name,
            discovered_date=datetime.now().isoformat(),
            discovery_source=discovery_source,
            evidence_summary=evidence_summary,
            observation_count=observation_count,
            observed_win_rate=observed_win_rate,
            concepts_used=concepts_used,
            trigger_conditions=trigger_conditions,
            context_filters=context_filters or {},
            entry_logic=entry_logic,
            confirmation_rules=confirmation_rules or [],
            stop_loss_logic=stop_loss_logic,
            take_profit_logic=take_profit_logic,
            invalidation_rules=invalidation_rules or [],
            status="DISCOVERED",
            status_history=[{
                "status": "DISCOVERED",
                "date": datetime.now().isoformat(),
                "reason": f"Created by {discovery_source}: {evidence_summary[:200]}"
            }],
            derived_from_strategies=derived_from_strategies or [],
        )

        self._hypotheses[hyp_id] = hyp
        self._save()
        print(f"  📋 Hypothesis {hyp_id} created: {name}")
        return hyp

    def update_status(self, hyp_id: str, new_status: str, reason: str = ""):
        """Update the status of a hypothesis with audit trail."""
        if hyp_id not in self._hypotheses:
            raise ValueError(f"Hypothesis {hyp_id} not found.")
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {VALID_STATUSES}")

        hyp = self._hypotheses[hyp_id]
        old_status = hyp.status
        hyp.status = new_status
        hyp.status_history.append({
            "status": new_status,
            "date": datetime.now().isoformat(),
            "reason": reason or f"Status changed from {old_status} to {new_status}",
        })
        self._save()
        print(f"  📋 {hyp_id}: {old_status} → {new_status} | {reason}")

    def record_backtest_results(self, hyp_id: str, results: dict):
        """Record backtest results for a hypothesis."""
        if hyp_id not in self._hypotheses:
            raise ValueError(f"Hypothesis {hyp_id} not found.")

        hyp = self._hypotheses[hyp_id]
        hyp.backtest_results = results
        self._save()

    def record_oos_results(self, hyp_id: str, results: dict):
        """Record out-of-sample validation results."""
        if hyp_id not in self._hypotheses:
            raise ValueError(f"Hypothesis {hyp_id} not found.")

        hyp = self._hypotheses[hyp_id]
        hyp.oos_results = results
        self._save()

    def record_paper_trade_results(self, hyp_id: str, results: dict):
        """Record paper trading results."""
        if hyp_id not in self._hypotheses:
            raise ValueError(f"Hypothesis {hyp_id} not found.")

        hyp = self._hypotheses[hyp_id]
        hyp.paper_trade_results = results
        self._save()

    def get_by_status(self, status: str) -> list[StrategyHypothesis]:
        """Get all hypotheses with a given status."""
        return [h for h in self._hypotheses.values() if h.status == status]

    def get_hypothesis(self, hyp_id: str) -> Optional[StrategyHypothesis]:
        """Get a specific hypothesis by ID."""
        return self._hypotheses.get(hyp_id)

    def get_all(self) -> list[StrategyHypothesis]:
        """Get all hypotheses."""
        return list(self._hypotheses.values())

    def get_summary(self) -> dict:
        """Returns a summary of the hypothesis pipeline."""
        status_counts = {}
        for hyp in self._hypotheses.values():
            status_counts[hyp.status] = status_counts.get(hyp.status, 0) + 1
        return {
            "total_hypotheses": len(self._hypotheses),
            "by_status": status_counts,
        }
