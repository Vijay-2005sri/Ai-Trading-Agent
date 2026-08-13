"""
=============================================================================
BACKTEST VALIDATOR — Verifying Miner Hypotheses
=============================================================================
Takes newly discovered Strategy Hypotheses and runs them through rigorous
historical backtesting and out-of-sample validation.

If a hypothesis passes both the in-sample (backtest) and out-of-sample (OOS)
phases with high enough metrics, it is promoted to the PAPER_TRADING status.

Pipeline position:
  PatternMiner → HypothesisGenerator → [BACKTEST VALIDATOR] → PaperTrader
=============================================================================
"""

import pandas as pd
from typing import Dict, Any

from backtest.vectorized_engine import VectorizedBacktester
from data.hypothesis_generator import HypothesisManager


class BacktestValidator:
    """
    Validates hypotheses by generating Python code for the strategy and
    running it through the VectorizedBacktester.
    """

    def __init__(self, data_dir: str = None):
        self.hyp_manager = HypothesisManager(pipeline_dir=f"{data_dir}/strategy_pipeline" if data_dir else None)
        self.backtester = VectorizedBacktester(initial_capital=10000.0, risk_per_trade=0.02)
        
        # Validation Thresholds
        self.min_win_rate = 55.0
        self.min_profit_factor = 1.3
        self.min_trades = 50
        self.max_drawdown = 15.0

    def validate_discovered_hypotheses(self, df_in_sample: pd.DataFrame, df_out_of_sample: pd.DataFrame):
        """
        Main runner: validates all hypotheses in DISCOVERED status.
        """
        discovered = self.hyp_manager.get_by_status("DISCOVERED")
        if not discovered:
            print("  [VALIDATOR] No new hypotheses to validate.")
            return

        print(f"  [VALIDATOR] Found {len(discovered)} hypotheses to validate.")
        
        for hyp in discovered:
            self.hyp_manager.update_status(hyp.hypothesis_id, "BACKTESTING")
            
            # Note: In a fully autonomous system, we would use an LLM here to 
            # generate the actual Python strategy class code based on the 
            # hyp.entry_logic and save it to strategy_library/experimental/
            # For now, we simulate this step.
            
            # 1. Generate Experimental Strategy Code (Simulated)
            strategy_class = self._generate_experimental_strategy(hyp)
            if not strategy_class:
                self.hyp_manager.update_status(hyp.hypothesis_id, "REJECTED", "Failed to generate strategy code.")
                continue

            # 2. Run In-Sample Backtest
            print(f"    ▶ Running In-Sample Backtest for {hyp.hypothesis_id}...")
            bt_results = self.backtester.run(strategy_class, df_in_sample)
            self.hyp_manager.record_backtest_results(hyp.hypothesis_id, bt_results)
            
            if not self._check_thresholds(bt_results):
                self.hyp_manager.update_status(hyp.hypothesis_id, "BACKTESTING_FAILED", "Failed in-sample thresholds.")
                continue
                
            self.hyp_manager.update_status(hyp.hypothesis_id, "BACKTESTING_PASSED")

            # 3. Run Out-Of-Sample Validation
            self.hyp_manager.update_status(hyp.hypothesis_id, "VALIDATING")
            print(f"    ▶ Running Out-Of-Sample Validation for {hyp.hypothesis_id}...")
            oos_results = self.backtester.run(strategy_class, df_out_of_sample)
            self.hyp_manager.record_oos_results(hyp.hypothesis_id, oos_results)
            
            if not self._check_thresholds(oos_results):
                self.hyp_manager.update_status(hyp.hypothesis_id, "REJECTED", "Failed out-of-sample thresholds.")
                continue
                
            # PASS! Promote to Paper Trading
            self.hyp_manager.update_status(
                hyp.hypothesis_id, 
                "PAPER_TRADING", 
                "Passed both In-Sample and Out-Of-Sample validation. Ready for forward testing."
            )

    def _check_thresholds(self, results: Dict[str, Any]) -> bool:
        """Checks if the backtest results meet minimum viable criteria."""
        if "error" in results:
            return False
            
        win_rate = results.get("win_rate_pct", 0)
        profit_factor = results.get("profit_factor", 0)
        trades = results.get("total_trades", 0)
        dd = results.get("max_drawdown_pct", 100)
        
        if (win_rate >= self.min_win_rate and 
            profit_factor >= self.min_profit_factor and 
            trades >= self.min_trades and 
            dd <= self.max_drawdown):
            return True
        return False
        
    def _generate_experimental_strategy(self, hyp) -> Any:
        """
        MOCK: In reality, we call LLM with self_learning.py logic here
        to generate the code in `strategy_library/experimental/`.
        For now, we return a mock class so the pipeline compiles.
        """
        from strategy_library.live.smc_concepts import SMCStrategy
        
        # We just return the SMC base strategy as a placeholder so the 
        # backtester has something to run during development/testing.
        return SMCStrategy
