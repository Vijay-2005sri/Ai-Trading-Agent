"""
=============================================================================
STRATEGY MASTER — Dynamic, Registry-Based Strategy Runner
=============================================================================
This module dynamically loads ALL strategies from registry.json that have
status = "LIVE". It runs them against the current market data and returns
a consolidated list of trade signals ranked by confidence.

SAFETY RULE: This module ONLY loads strategies from the strategy_library/
directory. It CANNOT and WILL NOT import from strategy_library/experimental/.
Experimental strategies are quarantined until they pass the full validation
pipeline and are promoted to LIVE status in registry.json.

CUMULATIVE GROWTH: When a new strategy is validated and added to
registry.json with status = "LIVE", the total count of active strategies
permanently increases. The next cycle evaluates the market against ALL
active strategies (12 + newly discovered ones).
=============================================================================
"""

import json
import importlib
from pathlib import Path
from dataclasses import asdict

import pandas as pd


# Path to the strategy registry
REGISTRY_PATH = Path(__file__).parent / "registry.json"

# SAFETY: Experimental strategies are BLOCKED from loading
BLOCKED_DIRS = {"experimental", "dynamic_strategies"}


def _load_registry() -> dict:
    """Load the strategy registry from registry.json."""
    if not REGISTRY_PATH.exists():
        print("[WARN] registry.json not found. Falling back to hardcoded registry.")
        return {}

    with open(REGISTRY_PATH, "r") as f:
        data = json.load(f)
    return data.get("strategies", {})


def _dynamic_import(module_path: str, class_name: str):
    """
    Dynamically import a strategy class from a module path.

    Args:
        module_path: e.g., "strategy_library.smc_concepts"
        class_name: e.g., "SMCStrategy"

    Returns:
        The class object, or None if import fails.
    """
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        print(f"[WARN] Could not import {class_name} from {module_path}: {e}")
        return None


def _build_strategy_registry() -> dict:
    """
    Build the STRATEGY_REGISTRY by reading registry.json and dynamically
    importing only LIVE strategy classes.

    Returns a dict: { "strategy_name": StrategyClass, ... }
    """
    registry_data = _load_registry()
    active_strategies = {}

    if not registry_data:
        # Fallback: hardcoded imports if registry.json is missing/empty
        print("[WARN] Using hardcoded strategy fallback.")
        from strategy_library.live.smc_concepts import SMCStrategy
        from strategy_library.live.ict_concepts import ICTSilverBulletStrategy, ICTOptimalTradeEntry
        from strategy_library.live.trend_following import EMACrossoverStrategy, BreakoutStrategy
        from strategy_library.live.mean_reversion import RSIMeanReversionStrategy, SupplyDemandZoneStrategy
        from strategy_library.live.wyckoff_method import WyckoffStrategy
        from strategy_library.live.harmonic_fibonacci import FibonacciRetracementStrategy
        from strategy_library.live.scalping_price_action import VWAPScalpingStrategy, EngulfingCandleStrategy, NewsSpikeFadeStrategy

        return {
            "SMC_Liquidity_Sweep": SMCStrategy,
            "ICT_Silver_Bullet": ICTSilverBulletStrategy,
            "ICT_OTE": ICTOptimalTradeEntry,
            "Wyckoff_Spring_Upthrust": WyckoffStrategy,
            "EMA_Crossover": EMACrossoverStrategy,
            "Bollinger_Breakout": BreakoutStrategy,
            "RSI_Mean_Reversion": RSIMeanReversionStrategy,
            "Supply_Demand_Zone": SupplyDemandZoneStrategy,
            "Fibonacci_Golden_Zone": FibonacciRetracementStrategy,
            "VWAP_Scalp": VWAPScalpingStrategy,
            "Engulfing_Candle": EngulfingCandleStrategy,
            "News_Spike_Fade": NewsSpikeFadeStrategy,
        }

    for name, meta in registry_data.items():
        status = meta.get("status", "DISABLED")
        if status != "LIVE":
            print(f"  ⏸️  Strategy '{name}' skipped (status: {status})")
            continue

        file_name = meta.get("file", "")
        class_name = meta.get("class", "")

        if not file_name or not class_name:
            print(f"  [WARN] Strategy '{name}' missing 'file' or 'class' in registry.")
            continue

        # SAFETY CHECK: Block experimental strategies
        if any(blocked in file_name for blocked in BLOCKED_DIRS):
            print(f"  🛑 BLOCKED: '{name}' references experimental directory. "
                  f"Cannot load untested strategies.")
            continue

        # Build the module path: strategy_library.live.<filename_without_.py>
        module_name = file_name.replace(".py", "")
        module_path = f"strategy_library.live.{module_name}"

        strategy_class = _dynamic_import(module_path, class_name)
        if strategy_class:
            active_strategies[name] = strategy_class
            version = meta.get("version", "?")
            print(f"  ✅ Loaded: {name} v{version} ({class_name})")

    return active_strategies


# Build the registry on module import
print("\n=== LOADING STRATEGY REGISTRY ===")
STRATEGY_REGISTRY = _build_strategy_registry()
print(f"=== {len(STRATEGY_REGISTRY)} STRATEGIES ACTIVE ===\n")


def run_all_strategies(df: pd.DataFrame, pair: str = "EURUSD") -> list[dict]:
    """
    Runs every registered LIVE strategy against the given OHLCV DataFrame.
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
    Dynamically reads from registry.json to include descriptions.
    """
    registry_data = _load_registry()

    # Strategy descriptions (static for the original 12, auto-generated for new ones)
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

    summary_lines = [
        "=== LOADED TRADING STRATEGIES ===",
        f"Total strategies active: {len(STRATEGY_REGISTRY)}",
        ""
    ]

    for name in STRATEGY_REGISTRY:
        # Try to get description from our static map, or from registry metadata
        desc = descriptions.get(name)
        if not desc:
            meta = registry_data.get(name, {})
            desc = meta.get("description", "Newly discovered and validated strategy.")
        summary_lines.append(f"  [{name}]: {desc}")

    return "\n".join(summary_lines)


def get_active_count() -> int:
    """Returns the number of currently active (LIVE) strategies."""
    return len(STRATEGY_REGISTRY)


def reload_registry():
    """
    Hot-reload the strategy registry from disk.
    Call this after adding a new validated strategy to registry.json.
    """
    global STRATEGY_REGISTRY
    print("\n=== RELOADING STRATEGY REGISTRY ===")
    STRATEGY_REGISTRY = _build_strategy_registry()
    print(f"=== {len(STRATEGY_REGISTRY)} STRATEGIES ACTIVE ===\n")
