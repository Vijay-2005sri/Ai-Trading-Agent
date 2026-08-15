"""
=============================================================================
OBSERVATION LOGGER — Daily Market Observation Recording
=============================================================================
Records structured market observations after each trading cycle.

Each observation captures:
- What concepts appeared on the chart
- Which strategies produced signals
- Which conditions were satisfied / failed
- The outcome of each setup
- Market regime, session, and timeframe context

These observations feed the PatternMiner for autonomous strategy discovery.
The data is stored as JSON-Lines files, one per day (DD-MM-YYYY.jsonl),
inside data/market_observations/.
=============================================================================
"""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class MarketObservation:
    """A single structured observation from one symbol in one cycle."""

    # --- Identity ---
    timestamp: str = ""
    instrument: str = ""
    timeframe: str = ""

    # --- Context ---
    market_regime: str = ""       # "trending_bull", "trending_bear", "ranging", "volatile"
    session: str = ""             # "asian", "london", "new_york", "overlap"
    session_phase: str = ""       # "killzone", "off_hours"

    # --- Concepts Detected ---
    concepts_present: list[str] = field(default_factory=list)
    # e.g. ["Liquidity_Sweep_SSL", "Bullish_FVG", "BOS", "Displacement"]

    # --- Strategy Signals ---
    strategies_that_signaled: list[str] = field(default_factory=list)
    # e.g. ["SMC_Liquidity_Sweep", "ICT_Silver_Bullet"]

    top_strategy: str = ""
    top_confidence: int = 0

    # --- Conditions ---
    conditions_satisfied: list[str] = field(default_factory=list)
    conditions_failed: list[str] = field(default_factory=list)

    # --- Decision & Outcome ---
    decision_action: str = ""     # "BUY", "SELL", "HOLD"
    decision_reasoning: str = ""

    # Outcome tracking (filled later when trade closes)
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    outcome: str = ""             # "WIN", "LOSS", "PENDING", "NO_TRADE"
    pnl: float = 0.0
    max_favorable_excursion: float = 0.0
    bars_held: int = 0

    # --- Grounding ---
    grounding_score: float = 0.0
    rag_win_rate: Optional[float] = None

    # --- Metadata ---
    cycle_id: str = ""


class ObservationLogger:
    """
    Writes MarketObservation records to daily JSON-Lines files.

    File naming: DD-MM-YYYY.jsonl
    One line per observation (one symbol per cycle = one line).
    """

    def __init__(self, base_dir: str = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(__file__).parent.parent / "data" / "market_observations"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_today_file(self) -> Path:
        """Returns the path for today's observation file."""
        today = datetime.now().strftime("%d-%m-%Y")
        return self.base_dir / f"{today}.jsonl"

    def log_observation(self, obs: MarketObservation):
        """Append a single observation to today's JSONL file."""
        if not obs.timestamp:
            obs.timestamp = datetime.now().isoformat()
        if not obs.cycle_id:
            obs.cycle_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        file_path = self._get_today_file()
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(obs), default=str) + "\n")

    def log_from_cycle_data(
        self,
        symbol: str,
        strategy_signals: list[dict],
        decision_action: str,
        decision_reasoning: str,
        decision_confidence: int,
        grounding_score: float = 0.0,
        rag_win_rate: float = None,
        entry_price: float = 0.0,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        timeframe: str = "H1",
    ):
        """
        Convenience method: build a MarketObservation from raw cycle data.
        Called from main.py after each symbol is analyzed.
        """
        # Extract strategy names that fired
        strategies_that_signaled = list(set(
            s.get("strategy", "Unknown") for s in strategy_signals
        ))

        top = strategy_signals[0] if strategy_signals else {}

        # Determine session from current UTC hour
        from datetime import timezone
        utc_hour = datetime.now(timezone.utc).hour
        if 0 <= utc_hour < 7:
            session = "asian"
        elif 7 <= utc_hour < 12:
            session = "london"
        elif 12 <= utc_hour < 16:
            session = "overlap"
        elif 16 <= utc_hour < 21:
            session = "new_york"
        else:
            session = "off_hours"

        obs = MarketObservation(
            instrument=symbol,
            timeframe=timeframe,
            session=session,
            strategies_that_signaled=strategies_that_signaled,
            top_strategy=top.get("strategy", ""),
            top_confidence=decision_confidence,
            decision_action=decision_action,
            decision_reasoning=decision_reasoning[:500],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            outcome="PENDING" if decision_action in ("BUY", "SELL") else "NO_TRADE",
            grounding_score=grounding_score,
            rag_win_rate=rag_win_rate,
        )

        self.log_observation(obs)

    def get_observations(self, date_str: str = None) -> list[dict]:
        """
        Load all observations for a given date.
        date_str format: DD-MM-YYYY. Defaults to today.
        """
        if date_str is None:
            date_str = datetime.now().strftime("%d-%m-%Y")

        file_path = self.base_dir / f"{date_str}.jsonl"
        if not file_path.exists():
            return []

        observations = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    observations.append(json.loads(line))
        return observations

    def get_all_observations(self, last_n_days: int = 30) -> list[dict]:
        """
        Load observations from the last N days for pattern mining.
        Returns a flat list of all observation dicts.
        """
        from datetime import timedelta

        all_obs = []
        for i in range(last_n_days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%d-%m-%Y")
            all_obs.extend(self.get_observations(date_str))

        return all_obs

    def get_stats(self) -> dict:
        """Returns summary statistics of the observation database."""
        files = list(self.base_dir.glob("*.jsonl"))
        total_obs = 0
        for f in files:
            with open(f, "r") as fh:
                total_obs += sum(1 for _ in fh)

        return {
            "total_days_recorded": len(files),
            "total_observations": total_obs,
            "storage_path": str(self.base_dir),
        }
