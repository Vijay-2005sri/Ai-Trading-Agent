"""
=============================================================================
PERFORMANCE MONITOR — Degradation Detection
=============================================================================
Continuously monitors the health of all LIVE strategies.
If a live strategy's rolling win rate or profit factor drops below its 
acceptable threshold, it is marked as DEGRADED and quarantined.

Pipeline position:
  Live Execution → [PERFORMANCE MONITOR] → Registry Update (Quarantine)
=============================================================================
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class PerformanceMonitor:
    """
    Monitors live strategy performance and enforces degradation thresholds.
    """

    def __init__(self, data_dir: str = None, registry_path: str = None):
        if data_dir:
            self.health_file = Path(data_dir) / "monitoring" / "strategy_health.json"
        else:
            self.health_file = Path(__file__).parent / "strategy_health.json"
            
        if registry_path:
            self.registry_path = Path(registry_path)
        else:
            self.registry_path = Path(__file__).parent.parent / "strategy_library" / "registry.json"
            
        # Degradation Thresholds
        self.degradation_win_rate = 50.0
        self.rolling_window_trades = 20

    def _load_health(self) -> Dict:
        if self.health_file.exists():
            with open(self.health_file, "r") as f:
                return json.load(f)
        return {"strategies": {}}

    def _save_health(self, data: Dict):
        with open(self.health_file, "w") as f:
            json.dump(data, f, indent=2)

    def record_trade_outcome(self, strategy_name: str, pnl: float):
        """Records a trade outcome for a live strategy."""
        data = self._load_health()
        strats = data.setdefault("strategies", {})
        
        if strategy_name not in strats:
            strats[strategy_name] = {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "rolling_outcomes": [], # 1 for win, 0 for loss
                "status": "HEALTHY"
            }
            
        s_data = strats[strategy_name]
        s_data["total_trades"] += 1
        
        is_win = 1 if pnl > 0 else 0
        if is_win:
            s_data["wins"] += 1
        else:
            s_data["losses"] += 1
            
        s_data["rolling_outcomes"].append(is_win)
        
        # Keep only the last N trades for rolling window
        if len(s_data["rolling_outcomes"]) > self.rolling_window_trades:
            s_data["rolling_outcomes"].pop(0)
            
        # Check for degradation
        if len(s_data["rolling_outcomes"]) >= self.rolling_window_trades:
            rolling_wr = (sum(s_data["rolling_outcomes"]) / self.rolling_window_trades) * 100
            
            if rolling_wr < self.degradation_win_rate:
                s_data["status"] = "DEGRADED"
                self._quarantine_strategy(strategy_name, rolling_wr)
                
        self._save_health(data)

    def _quarantine_strategy(self, strategy_name: str, rolling_wr: float):
        """Marks a strategy as DEGRADED in the registry to stop live trading."""
        if not self.registry_path.exists():
            print(f"  [WARN] Cannot quarantine {strategy_name}: registry not found.")
            return
            
        with open(self.registry_path, "r") as f:
            registry = json.load(f)
            
        if strategy_name in registry.get("strategies", {}):
            registry["strategies"][strategy_name]["status"] = "DEGRADED"
            registry["strategies"][strategy_name]["degradation_date"] = datetime.now().isoformat()
            registry["strategies"][strategy_name]["degradation_reason"] = f"Rolling win rate dropped to {rolling_wr:.1f}%"
            
            with open(self.registry_path, "w") as f:
                json.dump(registry, f, indent=2)
                
            print(f"  🛑 [MONITOR] Strategy {strategy_name} DEGRADED and quarantined! (WR: {rolling_wr:.1f}%)")
