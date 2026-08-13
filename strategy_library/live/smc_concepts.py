"""
=============================================================================
SMC (Smart Money Concepts) — FULL TRADING STRATEGY
=============================================================================
How this strategy works end-to-end:

1. DETECT the trend using Break of Structure (BOS) on the Higher Timeframe.
2. WAIT for a Liquidity Sweep — price hunts retail stop losses.
3. IDENTIFY an Order Block or Fair Value Gap left behind after the sweep.
4. ENTER when price returns to fill the FVG or retest the Order Block.
5. STOP LOSS placed beyond the sweep extreme (where institutions entered).
6. TAKE PROFIT at the next liquidity pool (opposing swing high/low).

The output is a list of TradeSignal dicts that the Executive Agent can act on.
=============================================================================
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TradeSignal:
    strategy: str
    direction: str        # "BUY" or "SELL"
    pair: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: int       # 0-100
    reasoning: str
    timestamp: str


class SMCStrategy:
    """
    Smart Money Concepts — Full Execution Strategy.

    Workflow:
    ┌──────────────┐     ┌──────────────────┐     ┌───────────────┐
    │ 1. Detect    │ ──▶ │ 2. Wait for      │ ──▶ │ 3. Find OB or │
    │ Market       │     │ Liquidity Sweep   │     │ FVG in the    │
    │ Structure    │     │ (Stop Hunt)       │     │ impulse zone  │
    └──────────────┘     └──────────────────┘     └───────┬───────┘
                                                          │
    ┌──────────────┐     ┌──────────────────┐             │
    │ 5. Set SL    │ ◀── │ 4. ENTER when    │ ◀───────────┘
    │ beyond sweep │     │ price retests    │
    │ TP at next   │     │ the OB/FVG       │
    │ liquidity    │     │                  │
    └──────────────┘     └──────────────────┘
    """

    def __init__(self, pair: str = "EURUSD", atr_period: int = 14, swing_lookback: int = 10):
        self.pair = pair
        self.atr_period = atr_period
        self.swing_lookback = swing_lookback

    # -------------------------------------------------------------------
    # STEP 1: Determine the trend via market structure
    # -------------------------------------------------------------------
    def _get_swing_points(self, df: pd.DataFrame) -> tuple[list, list]:
        swing_highs = []
        swing_lows = []
        lb = self.swing_lookback

        for i in range(lb, len(df) - lb):
            if df["high"].iloc[i] == df["high"].iloc[i - lb:i + lb + 1].max():
                swing_highs.append({"index": i, "price": df["high"].iloc[i]})
            if df["low"].iloc[i] == df["low"].iloc[i - lb:i + lb + 1].min():
                swing_lows.append({"index": i, "price": df["low"].iloc[i]})

        return swing_highs, swing_lows

    def _determine_trend(self, swing_highs: list, swing_lows: list) -> str:
        """Higher Highs + Higher Lows = BULLISH, Lower Highs + Lower Lows = BEARISH."""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "neutral"

        hh = swing_highs[-1]["price"] > swing_highs[-2]["price"]
        hl = swing_lows[-1]["price"] > swing_lows[-2]["price"]
        lh = swing_highs[-1]["price"] < swing_highs[-2]["price"]
        ll = swing_lows[-1]["price"] < swing_lows[-2]["price"]

        if hh and hl:
            return "bullish"
        elif lh and ll:
            return "bearish"
        return "neutral"

    # -------------------------------------------------------------------
    # STEP 2: Detect Liquidity Sweeps (institutional stop hunts)
    # -------------------------------------------------------------------
    def _detect_sweeps(self, df: pd.DataFrame, swing_highs: list, swing_lows: list) -> list[dict]:
        sweeps = []
        latest_idx = len(df) - 1

        # Check if the latest candle swept a recent swing high and closed below it
        for sh in swing_highs[-3:]:
            if df["high"].iloc[latest_idx] > sh["price"] and df["close"].iloc[latest_idx] < sh["price"]:
                sweeps.append({"type": "buyside_sweep", "level": sh["price"],
                               "extreme": df["high"].iloc[latest_idx]})

        # Check if the latest candle swept a recent swing low and closed above it
        for sl in swing_lows[-3:]:
            if df["low"].iloc[latest_idx] < sl["price"] and df["close"].iloc[latest_idx] > sl["price"]:
                sweeps.append({"type": "sellside_sweep", "level": sl["price"],
                               "extreme": df["low"].iloc[latest_idx]})

        return sweeps

    # -------------------------------------------------------------------
    # STEP 3: Find Order Blocks and Fair Value Gaps near the sweep
    # -------------------------------------------------------------------
    def _find_order_block(self, df: pd.DataFrame, direction: str, search_window: int = 10) -> Optional[dict]:
        end = len(df) - 1
        start = max(0, end - search_window)

        for i in range(end, start, -1):
            if direction == "BUY":
                # Bullish OB = last bearish candle before a bullish move
                if df["close"].iloc[i] < df["open"].iloc[i]:
                    if i + 1 < len(df) and df["close"].iloc[i + 1] > df["open"].iloc[i + 1]:
                        return {"ob_high": df["high"].iloc[i], "ob_low": df["low"].iloc[i],
                                "midpoint": (df["high"].iloc[i] + df["low"].iloc[i]) / 2}
            elif direction == "SELL":
                if df["close"].iloc[i] > df["open"].iloc[i]:
                    if i + 1 < len(df) and df["close"].iloc[i + 1] < df["open"].iloc[i + 1]:
                        return {"ob_high": df["high"].iloc[i], "ob_low": df["low"].iloc[i],
                                "midpoint": (df["high"].iloc[i] + df["low"].iloc[i]) / 2}
        return None

    def _find_fvg(self, df: pd.DataFrame, direction: str, search_window: int = 10) -> Optional[dict]:
        end = len(df) - 1
        start = max(2, end - search_window)

        for i in range(end, start, -1):
            c1_high = df["high"].iloc[i - 2]
            c3_low = df["low"].iloc[i]

            if direction == "BUY" and c3_low > c1_high:
                return {"gap_top": c3_low, "gap_bottom": c1_high,
                        "midpoint": (c3_low + c1_high) / 2}

            c1_low = df["low"].iloc[i - 2]
            c3_high = df["high"].iloc[i]

            if direction == "SELL" and c1_low > c3_high:
                return {"gap_top": c1_low, "gap_bottom": c3_high,
                        "midpoint": (c1_low + c3_high) / 2}
        return None

    # -------------------------------------------------------------------
    # STEP 4 & 5: GENERATE THE FULL TRADE SIGNAL
    # -------------------------------------------------------------------
    def _calc_atr(self, df: pd.DataFrame) -> float:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        """
        Main entry point. Pass in an OHLCV DataFrame.
        Returns a list of TradeSignal objects (usually 0 or 1).
        """
        signals = []
        if len(df) < self.swing_lookback * 2 + 5:
            return signals

        swing_highs, swing_lows = self._get_swing_points(df)
        trend = self._determine_trend(swing_highs, swing_lows)
        sweeps = self._detect_sweeps(df, swing_highs, swing_lows)
        atr = self._calc_atr(df)
        current_price = df["close"].iloc[-1]

        for sweep in sweeps:
            if sweep["type"] == "sellside_sweep" and trend == "bullish":
                # Bullish setup: Sell-side liquidity was swept in a bullish trend
                ob = self._find_order_block(df, "BUY")
                fvg = self._find_fvg(df, "BUY")
                zone = ob or fvg
                if zone:
                    entry = zone["midpoint"]
                    sl = sweep["extreme"] - (0.5 * atr)  # Below the sweep extreme
                    tp_target = swing_highs[-1]["price"] if swing_highs else entry + 3 * atr
                    rr = abs(tp_target - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                    signals.append(TradeSignal(
                        strategy="SMC_Liquidity_Sweep_Long",
                        direction="BUY",
                        pair=self.pair,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5),
                        take_profit=round(tp_target, 5),
                        risk_reward=round(rr, 2),
                        confidence=75 if ob and fvg else 60,
                        reasoning=(f"Bullish trend confirmed (HH+HL). Sell-side liquidity swept at {sweep['level']:.5f}. "
                                   f"{'Order Block' if ob else 'FVG'} found at {zone['midpoint']:.5f}. "
                                   f"Entry on retest. SL below sweep extreme. TP at next swing high."),
                        timestamp=str(df.index[-1])
                    ))

            elif sweep["type"] == "buyside_sweep" and trend == "bearish":
                ob = self._find_order_block(df, "SELL")
                fvg = self._find_fvg(df, "SELL")
                zone = ob or fvg
                if zone:
                    entry = zone["midpoint"]
                    sl = sweep["extreme"] + (0.5 * atr)
                    tp_target = swing_lows[-1]["price"] if swing_lows else entry - 3 * atr
                    rr = abs(entry - tp_target) / abs(sl - entry) if abs(sl - entry) > 0 else 0

                    signals.append(TradeSignal(
                        strategy="SMC_Liquidity_Sweep_Short",
                        direction="SELL",
                        pair=self.pair,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5),
                        take_profit=round(tp_target, 5),
                        risk_reward=round(rr, 2),
                        confidence=75 if ob and fvg else 60,
                        reasoning=(f"Bearish trend confirmed (LH+LL). Buy-side liquidity swept at {sweep['level']:.5f}. "
                                   f"{'Order Block' if ob else 'FVG'} found at {zone['midpoint']:.5f}. "
                                   f"Entry on retest. SL above sweep extreme. TP at next swing low."),
                        timestamp=str(df.index[-1])
                    ))

        return signals
