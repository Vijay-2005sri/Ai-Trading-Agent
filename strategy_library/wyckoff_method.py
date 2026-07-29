"""
=============================================================================
WYCKOFF METHOD — FULL TRADING STRATEGY
=============================================================================
How this strategy works end-to-end:

The Wyckoff Method identifies the 4 phases of a market cycle:
  Accumulation → Markup → Distribution → Markdown

WYCKOFF SPRING STRATEGY (Buying at Accumulation):
1. DETECT a trading range (price consolidating between support and resistance).
2. WAIT for a "Spring" — price drops BELOW support briefly and reverses.
3. CONFIRM with Volume: Spring should have LOW volume (no real selling).
4. ENTER long when price re-enters the range with strength (SOS = Sign of Strength).
5. STOP LOSS below the Spring low.
6. TAKE PROFIT at the top of the range or the first extension target.

WYCKOFF UPTHRUST STRATEGY (Selling at Distribution):
1. DETECT a trading range at the TOP of a rally.
2. WAIT for an "Upthrust" — price spikes ABOVE resistance and reverses.
3. CONFIRM with Volume: Upthrust on HIGH volume but closes back below range.
4. ENTER short when price falls back into the range.
5. STOP LOSS above the Upthrust high.
6. TAKE PROFIT at the bottom of the range.
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


class WyckoffStrategy:
    """
    Wyckoff Spring & Upthrust — identifies institutional accumulation and distribution.

    Workflow (Spring Example):
    ┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
    │ 1. Detect a  │ ──▶ │ 2. Did price     │ ──▶ │ 3. Was volume LOW │
    │ trading      │     │ break below      │     │ during the break? │
    │ range (flat) │     │ support (Spring)? │     │ (no real selling) │
    └──────────────┘     └──────────────────┘     └────────┬──────────┘
                                                           │ YES
    ┌──────────────┐     ┌──────────────────┐              │
    │ 5. SL below  │ ◀── │ 4. BUY when      │ ◀────────────┘
    │ the Spring   │     │ price re-enters  │
    │ low. TP at   │     │ the range with   │
    │ range top.   │     │ strong close     │
    └──────────────┘     └──────────────────┘
    """

    def __init__(self, pair: str = "EURUSD", range_lookback: int = 40, atr_period: int = 14):
        self.pair = pair
        self.range_lookback = range_lookback
        self.atr_period = atr_period

    def _calc_atr(self, df: pd.DataFrame) -> float:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def _detect_range(self, df: pd.DataFrame) -> Optional[dict]:
        """Detect if recent price action is in a consolidation range."""
        window = df.iloc[-self.range_lookback:]
        range_high = window["high"].max()
        range_low = window["low"].min()
        range_size = range_high - range_low
        avg_price = (range_high + range_low) / 2

        # A range is 'flat' if the range is less than 3% of average price
        if range_size / avg_price < 0.03:
            return {"range_high": range_high, "range_low": range_low, "range_size": range_size}
        return None

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < self.range_lookback + 5 or "volume" not in df.columns:
            return signals

        trading_range = self._detect_range(df)
        if trading_range is None:
            return signals

        atr = self._calc_atr(df)
        current_price = df["close"].iloc[-1]
        prev_low = df["low"].iloc[-2]
        prev_close = df["close"].iloc[-2]
        avg_volume = df["volume"].iloc[-self.range_lookback:].mean()
        last_volume = df["volume"].iloc[-1]

        # --- SPRING DETECTION (Bullish) ---
        # Previous bar broke below range low, current bar closes back inside range
        spring_triggered = (prev_low < trading_range["range_low"] and
                            current_price > trading_range["range_low"])
        low_volume_spring = last_volume < avg_volume * 0.8  # Volume < 80% of average

        if spring_triggered and low_volume_spring:
            entry = current_price
            sl = df["low"].iloc[-2] - 0.3 * atr  # Below the spring low
            tp = trading_range["range_high"]
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append(TradeSignal(
                strategy="Wyckoff_Spring",
                direction="BUY",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=72,
                reasoning=(f"Wyckoff Spring detected. Price broke below range support "
                           f"({trading_range['range_low']:.5f}) and reversed back inside. "
                           f"Volume was {last_volume:.0f} vs avg {avg_volume:.0f} (low volume = no real selling). "
                           f"Institutional accumulation likely. TP at range top."),
                timestamp=str(df.index[-1])
            ))

        # --- UPTHRUST DETECTION (Bearish) ---
        prev_high = df["high"].iloc[-2]
        upthrust_triggered = (prev_high > trading_range["range_high"] and
                              current_price < trading_range["range_high"])
        high_volume_upthrust = last_volume > avg_volume * 1.2

        if upthrust_triggered and high_volume_upthrust:
            entry = current_price
            sl = df["high"].iloc[-2] + 0.3 * atr
            tp = trading_range["range_low"]
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append(TradeSignal(
                strategy="Wyckoff_Upthrust",
                direction="SELL",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=72,
                reasoning=(f"Wyckoff Upthrust detected. Price spiked above range resistance "
                           f"({trading_range['range_high']:.5f}) and failed back inside. "
                           f"Volume was {last_volume:.0f} vs avg {avg_volume:.0f} (high volume = distribution). "
                           f"Institutional distribution likely. TP at range bottom."),
                timestamp=str(df.index[-1])
            ))

        return signals
