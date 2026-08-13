"""
=============================================================================
HARMONIC PATTERNS + FIBONACCI — FULL TRADING STRATEGY
=============================================================================
How this strategy works end-to-end:

GARTLEY PATTERN (most common harmonic):
1. SCAN for an XABCD pattern where each leg follows Fibonacci ratios:
   - AB retraces 61.8% of XA
   - BC retraces 38.2%–88.6% of AB
   - CD extends 127.2%–161.8% of BC
   - D lands at 78.6% retracement of XA (the Potential Reversal Zone)
2. ENTER at point D (the PRZ — Potential Reversal Zone).
3. STOP LOSS beyond point X.
4. TAKE PROFIT at 38.2% retracement of AD leg, then 61.8%.

FIBONACCI RETRACEMENT STRATEGY:
1. IDENTIFY a strong trend move (impulse wave).
2. DRAW Fibonacci retracement from swing low to swing high.
3. WAIT for price to retrace to the 50%–61.8% zone.
4. ENTER with a reversal candle confirmation.
5. STOP LOSS below the 78.6% level.
6. TAKE PROFIT at the previous swing high (100%) or 161.8% extension.
=============================================================================
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class TradeSignal:
    strategy: str
    direction: str
    pair: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: int
    reasoning: str
    timestamp: str


class FibonacciRetracementStrategy:
    """
    Fibonacci Retracement Pullback Strategy.

    Workflow:
    ┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
    │ 1. Find the  │ ──▶ │ 2. Draw Fibonacci│ ──▶ │ 3. Is price in   │
    │ last impulse │     │ from swing low   │     │ the 50%-61.8%    │
    │ (strong move)│     │ to swing high    │     │ retracement zone?│
    └──────────────┘     └──────────────────┘     └────────┬──────────┘
                                                           │ YES
    ┌──────────────┐     ┌──────────────────┐              │
    │ 5. SL below  │ ◀── │ 4. Reversal      │ ◀────────────┘
    │ 78.6% Fib.   │     │ candle confirms. │
    │ TP at 0% or  │     │ ENTER.           │
    │ -61.8% ext.  │     │                  │
    └──────────────┘     └──────────────────┘
    """

    def __init__(self, pair: str = "EURUSD", swing_lookback: int = 30):
        self.pair = pair
        self.swing_lookback = swing_lookback
        self.fib_levels = {
            "38.2": 0.382,
            "50.0": 0.500,
            "61.8": 0.618,
            "78.6": 0.786,
        }

    def _find_impulse(self, df: pd.DataFrame) -> Optional[dict]:
        window = df.iloc[-self.swing_lookback:]
        swing_high_idx = window["high"].idxmax()
        swing_low_idx = window["low"].idxmin()

        swing_high = window["high"].max()
        swing_low = window["low"].min()

        high_pos = window.index.get_loc(swing_high_idx)
        low_pos = window.index.get_loc(swing_low_idx)

        if low_pos < high_pos:
            return {"direction": "bullish", "swing_low": swing_low, "swing_high": swing_high}
        elif high_pos < low_pos:
            return {"direction": "bearish", "swing_high": swing_high, "swing_low": swing_low}
        return None

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < self.swing_lookback + 5:
            return signals

        impulse = self._find_impulse(df)
        if impulse is None:
            return signals

        current_price = df["close"].iloc[-1]
        fib_range = impulse["swing_high"] - impulse["swing_low"]

        if impulse["direction"] == "bullish":
            fib_50 = impulse["swing_high"] - 0.50 * fib_range
            fib_618 = impulse["swing_high"] - 0.618 * fib_range
            fib_786 = impulse["swing_high"] - 0.786 * fib_range

            # Price in the golden zone (50% – 61.8%)
            if fib_618 <= current_price <= fib_50:
                is_bullish = df["close"].iloc[-1] > df["open"].iloc[-1]
                if is_bullish:
                    entry = current_price
                    sl = fib_786 - 0.001
                    tp1 = impulse["swing_high"]
                    tp2 = impulse["swing_high"] + 0.618 * fib_range
                    rr = abs(tp1 - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                    signals.append(TradeSignal(
                        strategy="Fibonacci_Golden_Zone",
                        direction="BUY",
                        pair=self.pair,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5),
                        take_profit=round(tp1, 5),
                        risk_reward=round(rr, 2),
                        confidence=68,
                        reasoning=(f"Bullish impulse detected (Low={impulse['swing_low']:.5f}, High={impulse['swing_high']:.5f}). "
                                   f"Price retraced into Golden Zone (50%-61.8% Fib). "
                                   f"Bullish confirmation candle. SL below 78.6%. TP at swing high."),
                        timestamp=str(df.index[-1])
                    ))

        elif impulse["direction"] == "bearish":
            fib_50 = impulse["swing_low"] + 0.50 * fib_range
            fib_618 = impulse["swing_low"] + 0.618 * fib_range
            fib_786 = impulse["swing_low"] + 0.786 * fib_range

            if fib_50 <= current_price <= fib_618:
                is_bearish = df["close"].iloc[-1] < df["open"].iloc[-1]
                if is_bearish:
                    entry = current_price
                    sl = fib_786 + 0.001
                    tp1 = impulse["swing_low"]
                    rr = abs(entry - tp1) / abs(sl - entry) if abs(sl - entry) > 0 else 0

                    signals.append(TradeSignal(
                        strategy="Fibonacci_Golden_Zone",
                        direction="SELL",
                        pair=self.pair,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5),
                        take_profit=round(tp1, 5),
                        risk_reward=round(rr, 2),
                        confidence=68,
                        reasoning=(f"Bearish impulse detected (High={impulse['swing_high']:.5f}, Low={impulse['swing_low']:.5f}). "
                                   f"Price retraced into Golden Zone (50%-61.8% Fib). "
                                   f"Bearish confirmation candle. SL above 78.6%. TP at swing low."),
                        timestamp=str(df.index[-1])
                    ))

        return signals
