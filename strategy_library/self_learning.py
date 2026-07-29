"""
=============================================================================
SELF-LEARNING ENGINE — Strategy Generator & Optimizer
=============================================================================
This module allows the AI to invent new trading strategies or tweak existing
ones based on its past failures/successes (from the RAG memory).

It generates Python code for a new strategy, saves it to `dynamic_strategies/`,
and then runs it through the Backtester. If it performs well, it gets added
to the live trading rotation.
=============================================================================
"""

import os
from pathlib import Path
from agents.llm_provider import LLMProvider
from backtest.vectorized_engine import VectorizedBacktester


class StrategyGenerator:
    """Invents and backtests new trading strategies autonomously."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.backtester = VectorizedBacktester()
        self.output_dir = Path(__file__).parent.parent / "strategy_library" / "dynamic_strategies"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure __init__.py exists so it can be imported dynamically
        init_file = self.output_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Dynamic Strategies Module\n")

    def analyze_market_regime(self, market_data_summary: str, recent_failures: str) -> str:
        """
        Ask the LLM to invent a new strategy logic based on recent market behavior
        and past failures.
        """
        prompt = (
            "You are a world-class Quantitative Researcher.\n"
            "Here is a summary of the current market regime:\n"
            f"{market_data_summary}\n\n"
            "Here are strategies that have FAILED recently:\n"
            f"{recent_failures}\n\n"
            "Task: Invent a NEW algorithmic trading strategy to exploit the current market. "
            "Describe the entry logic, stop loss, and take profit in detail. "
            "Do NOT write code yet, just the exact mathematical/indicator rules."
        )
        print("  🧠 [Self-Learning] Inventing new strategy concepts...")
        return self.llm.invoke(prompt)

    def generate_strategy_code(self, strategy_logic: str, name: str) -> Path:
        """
        Convert the LLM's strategy logic into a Python class that matches
        our strategy template.
        """
        prompt = (
            "You are an expert Python algorithmic trader.\n"
            "Convert the following strategy logic into a Python class.\n\n"
            f"Logic:\n{strategy_logic}\n\n"
            "Requirements:\n"
            f"1. Class name must be `{name}`.\n"
            "2. It must have an `__init__(self, pair: str)` method.\n"
            "3. It must have a `generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]` method.\n"
            "4. It must import and use our TradeSignal dataclass from `strategy_library.smc_concepts`.\n"
            "5. The code must be clean, safe, and ready to execute.\n\n"
            "Respond ONLY with the pure Python code block. No markdown, no explanations."
        )
        
        print(f"  💻 [Self-Learning] Writing Python code for {name}...")
        raw_code = self.llm.invoke(prompt)
        
        # Clean up the output if it has markdown ticks
        clean_code = raw_code.replace("```python", "").replace("```", "").strip()
        
        file_path = self.output_dir / f"{name.lower()}.py"
        with open(file_path, "w") as f:
            f.write(clean_code)
            
        print(f"  ✅ [Self-Learning] Strategy saved to {file_path}")
        return file_path
