"""
=============================================================================
PATTERN MINER — Autonomous Strategy Discovery
=============================================================================
Scans the historical MarketObservations (stored as daily JSONL files in
data/market_observations/) and identifies recurring concept combinations
that correlate with winning trades.

Pipeline position:
  ObservationLogger → [PATTERN MINER] → HypothesisGenerator → BacktestValidator

This is an OFFLINE module. It is NOT part of the 15-minute live cycle.
Run it daily (e.g., via cron or manually) to mine for new patterns.
=============================================================================
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, Any, List


class PatternMiner:
    """
    Mines observation logs to discover repeating concept-combination patterns
    that have a statistically meaningful edge.
    """

    def __init__(self, data_dir: str = None):
        if data_dir:
            self.obs_dir = Path(data_dir) / "market_observations"
        else:
            self.obs_dir = Path(__file__).parent / "market_observations"

    def mine(self, days_to_lookback: int = 30) -> int:
        """
        Main entry point. Scans the last N days of observation files,
        extracts concept combinations, and returns count of discovered patterns.
        """
        print(f"  [MINER] Mining observations from last {days_to_lookback} days...")

        observations = self._load_observations(last_n_days=days_to_lookback)
        if not observations:
            print("  [MINER] No observations found to mine.")
            return 0
            
        print(f"  [MINER] Scanning {len(observations)} observations from last {days_to_lookback} days...")
        
        # 1. Extract successful setups
        winning_obs = [obs for obs in observations if obs.get("outcome") == "WIN"]
        losing_obs = [obs for obs in observations if obs.get("outcome") == "LOSS"]

        if not winning_obs:
            print("  [MINER] No winning observations yet. Need more data.")
            return 0

        # 2. Count concept combinations in winners vs losers
        win_combos = self._extract_concept_combos(winning_obs)
        loss_combos = self._extract_concept_combos(losing_obs)

        # 3. Find combos that appear frequently in wins but rarely in losses
        patterns = self._find_edge_patterns(win_combos, loss_combos, min_occurrences=3)

        if patterns:
            print(f"  [MINER] ✅ Discovered {len(patterns)} potential edge pattern(s):")
            for p in patterns:
                print(f"    → {p['combo']} | Win Rate: {p['win_rate']:.1f}% | Occurrences: {p['total']}")
        else:
            print("  [MINER] No statistically significant patterns found yet.")

        return len(patterns)

    def _load_observations(self, last_n_days: int = 30) -> List[Dict]:
        """Load observation JSONL files from the last N days."""
        observations = []
        today = datetime.now()

        for i in range(last_n_days):
            day = today - timedelta(days=i)
            filename = day.strftime("%d-%m-%Y") + ".jsonl"
            filepath = self.obs_dir / filename

            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                observations.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

        return observations

    def _extract_concept_combos(self, observations: List[Dict]) -> Counter:
        """Extract and count concept combinations from observations."""
        combos = Counter()

        for obs in observations:
            concepts = obs.get("concepts_present", [])
            if len(concepts) >= 2:
                # Sort to ensure consistent combo keys
                key = " + ".join(sorted(concepts))
                combos[key] += 1

        return combos

    def _find_edge_patterns(
        self,
        win_combos: Counter,
        loss_combos: Counter,
        min_occurrences: int = 3
    ) -> List[Dict]:
        """
        Find concept combinations that appear in wins more than losses.
        Returns patterns with a meaningful statistical edge.
        """
        patterns = []

        for combo, win_count in win_combos.items():
            loss_count = loss_combos.get(combo, 0)
            total = win_count + loss_count

            if total >= min_occurrences:
                win_rate = (win_count / total) * 100
                if win_rate >= 60.0:  # Only report combos with 60%+ win rate
                    patterns.append({
                        "combo": combo,
                        "win_count": win_count,
                        "loss_count": loss_count,
                        "total": total,
                        "win_rate": win_rate,
                    })

        # Sort by win rate descending
        patterns.sort(key=lambda x: x["win_rate"], reverse=True)
        return patterns


if __name__ == "__main__":
    miner = PatternMiner()
    found = miner.mine(days_to_lookback=30)
    print(f"\nTotal edge patterns discovered: {found}")
