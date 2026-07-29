"""
=============================================================================
STRATEGY MASTER — Unified Strategy Runner
=============================================================================
This module collects ALL strategies from the strategy_library and runs them
against the current market data. It returns a consolidated list of trade
signals from every strategy, ranked by confidence.

The Executive Agent reads this output to make its final decision.
=============================================================================
"""

from dataclasses import asdict

# Import all strategy classes
from strategy_library.smc_concepts import SMCStrategy
from strategy_library.ict_concepts import ICTSilverBulletStrategy, ICTOptimalTradeEntry
from strategy_library.trend_following import EMACrossoverStrategy, BreakoutStrategy
from strategy_library.mean_reversion import RSIMeanReversionStrategy, SupplyDemandZoneStrategy
from strategy_library.wyckoff_method import WyckoffStrategy
from strategy_library.harmonic_fibonacci import FibonacciRetracementStrategy
from strategy_library.scalping_price_action import VWAPScalpingStrategy, EngulfingCandleStrategy, NewsSpikeFadeStrategy

import pandas as pd


# Registry of ALL available strategies
STRATEGY_REGISTRY = {
    # --- Smart Money & Institutional ---
    "SMC_Liquidity_Sweep": SMCStrategy,
    "ICT_Silver_Bullet": ICTSilverBulletStrategy,
    "ICT_OTE": ICTOptimalTradeEntry,
    "Wyckoff_Spring_Upthrust": WyckoffStrategy,

    # --- Trend Following ---
    "EMA_Crossover": EMACrossoverStrategy,
    "Bollinger_Breakout": BreakoutStrategy,

    # --- Mean Reversion ---
    "RSI_Mean_Reversion": RSIMeanReversionStrategy,
    "Supply_Demand_Zone": SupplyDemandZoneStrategy,

    # --- Fibonacci & Harmonics ---
    "Fibonacci_Golden_Zone": FibonacciRetracementStrategy,

    # --- Scalping & Price Action ---
    "VWAP_Scalp": VWAPScalpingStrategy,
    "Engulfing_Candle": EngulfingCandleStrategy,
    "News_Spike_Fade": NewsSpikeFadeStrategy,
}


def run_all_strategies(df: pd.DataFrame, pair: str = "EURUSD") -> list[dict]:
    """
    Runs every registered strategy against the given OHLCV DataFrame.
    Returns a list of trade signal dicts, sorted by confidence (highest first).
    """
    all_signals = []

    for name, StrategyClass in STRATEGY_REGISTRY.items():
        try:
            strategy = StrategyClass(pair=pair)
            signals = strategy.generate_signals(df)
            for sig in signals:
                all_signals.append(asdict(sig))
        except Exception as e:
            print(f"[WARN] Strategy '{name}' failed: {e}")

    # Sort by confidence descending
    all_signals.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return all_signals


def get_strategy_summary() -> str:
    """
    Returns a human-readable summary of all loaded strategies.
    This is fed into the LLM Brain so it understands what tools it has.
    """
    summary_lines = [
        "=== LOADED TRADING STRATEGIES ===",
        f"Total strategies loaded: {len(STRATEGY_REGISTRY)}",
        ""
    ]

    descriptions = {
        "SMC_Liquidity_Sweep": "Detects institutional stop hunts (liquidity sweeps) and enters at Order Blocks / FVGs after the sweep reverses.",
        "ICT_Silver_Bullet": "Trades during London/NY Kill Zones. Waits for a Judas Swing (fake breakout) then enters opposite with displacement.",
        "ICT_OTE": "Fibonacci-based pullback entry at the 62%-79% retracement zone after a strong impulse move.",
        "Wyckoff_Spring_Upthrust": "Identifies accumulation (Spring = fake breakdown) and distribution (Upthrust = fake breakout) using volume confirmation.",
        "EMA_Crossover": "Classic trend following: EMA 20/50 crossover filtered by ADX > 25 to ensure a strong trend exists.",
        "Bollinger_Breakout": "Detects Bollinger Band squeeze (low volatility) and enters when price breaks out of the band with expanding volatility.",
        "RSI_Mean_Reversion": "Enters when RSI(14) crosses back from oversold (<30) or overbought (>70) territory, betting on reversion to the mean.",
        "Supply_Demand_Zone": "Identifies zones where institutional imbalance created a sharp move, enters when price returns to the zone with reversal confirmation.",
        "Fibonacci_Golden_Zone": "Enters at the 50%-61.8% Fibonacci retracement zone after a strong impulse, with SL at 78.6%.",
        "VWAP_Scalp": "Short-term scalping strategy: buys at VWAP when price is trending above it (VWAP = institutional fair value).",
        "Engulfing_Candle": "Trades bullish/bearish engulfing candlestick patterns at key support/resistance levels.",
        "News_Spike_Fade": "Fades abnormally large news spikes (>3x ATR), betting on a 50% retracement of the overreaction.",
    }

    for name in STRATEGY_REGISTRY:
        desc = descriptions.get(name, "No description available.")
        summary_lines.append(f"  [{name}]: {desc}")

    return "\n".join(summary_lines)
