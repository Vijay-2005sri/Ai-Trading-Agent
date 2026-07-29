"""
=============================================================================
SCALPING & PRICE ACTION — FULL TRADING STRATEGIES
=============================================================================
Strategies used by intraday traders on lower timeframes (M1, M5, M15).

VWAP SCALPING:
1. CALCULATE the VWAP (Volume Weighted Average Price) for the session.
2. WAIT for price to pull back to VWAP.
3. BUY if price is above VWAP and pulls back to it (VWAP acts as support).
4. SELL if price is below VWAP and rallies to it (VWAP acts as resistance).
5. STOP LOSS at 1x ATR. TAKE PROFIT at 1.5x ATR.

ENGULFING CANDLE STRATEGY:
1. DETECT a Bullish Engulfing or Bearish Engulfing candlestick pattern.
2. CONFIRM it happens at a key level (support/resistance or S&D zone).
3. ENTER in the direction of the engulfing pattern.
4. STOP LOSS at the opposite end of the engulfing candle.
5. TAKE PROFIT at 2x the engulfing candle size.

NEWS SPIKE FADE:
1. DETECT a sudden, abnormally large candle (>3x ATR body) after news.
2. WAIT for the immediate reaction to overextend.
3. FADE the move — trade the opposite direction expecting a 50% retracement.
4. STOP LOSS beyond the spike extreme. TAKE PROFIT at 50% retracement.
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


class VWAPScalpingStrategy:
    """
    VWAP Scalping — institutional "fair value" bounce strategy.

    Workflow:
    ┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
    │ 1. Calculate  │ ──▶ │ 2. Is price      │ ──▶ │ 3. Has price      │
    │ session VWAP  │     │ trending above   │     │ pulled back to    │
    │               │     │ or below VWAP?   │     │ touch VWAP?       │
    └──────────────┘     └──────────────────┘     └────────┬──────────┘
                                                           │ YES
    ┌──────────────┐     ┌──────────────────┐              │
    │ 5. SL 1xATR  │ ◀── │ 4. ENTER at VWAP │ ◀────────────┘
    │ TP 1.5xATR   │     │ in the direction │
    │               │     │ of the trend     │
    └──────────────┘     └──────────────────┘
    """

    def __init__(self, pair: str = "EURUSD", atr_period: int = 14):
        self.pair = pair
        self.atr_period = atr_period

    def _calc_vwap(self, df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        if "volume" in df.columns and df["volume"].sum() > 0:
            cum_tp_vol = (typical_price * df["volume"]).cumsum()
            cum_vol = df["volume"].cumsum()
            return cum_tp_vol / cum_vol.replace(0, np.nan)
        else:
            # Fallback: use a rolling mean as proxy VWAP for Forex (no volume)
            return typical_price.rolling(20).mean()

    def _calc_atr(self, df: pd.DataFrame) -> float:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < 25:
            return signals

        vwap = self._calc_vwap(df)
        atr = self._calc_atr(df)
        current_price = df["close"].iloc[-1]
        vwap_now = vwap.iloc[-1]

        if pd.isna(vwap_now):
            return signals

        # Price was above VWAP (uptrend) and pulled back to touch it
        was_above = df["close"].iloc[-3:-1].min() > vwap.iloc[-3:-1].min()
        touches_vwap_from_above = abs(current_price - vwap_now) < 0.3 * atr and current_price >= vwap_now

        if was_above and touches_vwap_from_above:
            entry = current_price
            sl = entry - 1.0 * atr
            tp = entry + 1.5 * atr
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append(TradeSignal(
                strategy="VWAP_Scalp",
                direction="BUY",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=58,
                reasoning=(f"Price was trending above VWAP ({vwap_now:.5f}) and pulled back to it. "
                           f"VWAP acting as institutional support. SL at 1x ATR. TP at 1.5x ATR."),
                timestamp=str(df.index[-1])
            ))

        # Price was below VWAP (downtrend) and rallied to touch it
        was_below = df["close"].iloc[-3:-1].max() < vwap.iloc[-3:-1].max()
        touches_vwap_from_below = abs(current_price - vwap_now) < 0.3 * atr and current_price <= vwap_now

        if was_below and touches_vwap_from_below:
            entry = current_price
            sl = entry + 1.0 * atr
            tp = entry - 1.5 * atr
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append(TradeSignal(
                strategy="VWAP_Scalp",
                direction="SELL",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=58,
                reasoning=(f"Price was trending below VWAP ({vwap_now:.5f}) and rallied to it. "
                           f"VWAP acting as institutional resistance. SL at 1x ATR. TP at 1.5x ATR."),
                timestamp=str(df.index[-1])
            ))

        return signals


class EngulfingCandleStrategy:
    """
    Engulfing Candlestick Pattern at Key Levels.

    - Bullish Engulfing: Current candle body fully engulfs previous bearish body.
    - Bearish Engulfing: Current candle body fully engulfs previous bullish body.
    - Only triggers near support/resistance (20-period high/low).
    """

    def __init__(self, pair: str = "EURUSD", atr_period: int = 14):
        self.pair = pair
        self.atr_period = atr_period

    def _calc_atr(self, df: pd.DataFrame) -> float:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < 25:
            return signals

        atr = self._calc_atr(df)
        curr_open, curr_close = df["open"].iloc[-1], df["close"].iloc[-1]
        prev_open, prev_close = df["open"].iloc[-2], df["close"].iloc[-2]
        current_price = curr_close

        recent_low = df["low"].iloc[-20:].min()
        recent_high = df["high"].iloc[-20:].max()
        near_support = abs(current_price - recent_low) < 1.0 * atr
        near_resistance = abs(current_price - recent_high) < 1.0 * atr

        # Bullish Engulfing at support
        bullish_engulfing = (prev_close < prev_open and  # previous was bearish
                             curr_close > curr_open and  # current is bullish
                             curr_close > prev_open and  # current body engulfs previous
                             curr_open < prev_close)

        if bullish_engulfing and near_support:
            entry = current_price
            sl = df["low"].iloc[-1] - 0.3 * atr
            tp = entry + 2 * abs(curr_close - curr_open)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append(TradeSignal(
                strategy="Engulfing_Candle",
                direction="BUY",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=63,
                reasoning=(f"Bullish Engulfing candle detected at support ({recent_low:.5f}). "
                           f"Current body fully engulfed previous bearish candle. "
                           f"SL below engulfing low. TP at 2x candle body."),
                timestamp=str(df.index[-1])
            ))

        # Bearish Engulfing at resistance
        bearish_engulfing = (prev_close > prev_open and
                             curr_close < curr_open and
                             curr_close < prev_open and
                             curr_open > prev_close)

        if bearish_engulfing and near_resistance:
            entry = current_price
            sl = df["high"].iloc[-1] + 0.3 * atr
            tp = entry - 2 * abs(curr_open - curr_close)
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append(TradeSignal(
                strategy="Engulfing_Candle",
                direction="SELL",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=63,
                reasoning=(f"Bearish Engulfing candle detected at resistance ({recent_high:.5f}). "
                           f"Current body fully engulfed previous bullish candle. "
                           f"SL above engulfing high. TP at 2x candle body."),
                timestamp=str(df.index[-1])
            ))

        return signals


class NewsSpikeFadeStrategy:
    """
    News Spike Fade — trades the overreaction after a news release.

    Logic: When a candle body is >3x ATR (abnormal spike), the move is
    often exaggerated. We fade it expecting a 50% retracement.
    """

    def __init__(self, pair: str = "EURUSD", atr_period: int = 14, spike_multiple: float = 3.0):
        self.pair = pair
        self.atr_period = atr_period
        self.spike_multiple = spike_multiple

    def _calc_atr(self, df: pd.DataFrame) -> float:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < self.atr_period + 5:
            return signals

        atr = self._calc_atr(df)
        last_body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])

        if last_body < self.spike_multiple * atr:
            return signals  # No spike

        current_price = df["close"].iloc[-1]
        spike_open = df["open"].iloc[-1]
        spike_range = current_price - spike_open
        retracement_50 = spike_open + 0.5 * spike_range

        if spike_range > 0:
            # Bullish spike → FADE short
            entry = current_price
            sl = df["high"].iloc[-1] + 0.5 * atr
            tp = retracement_50
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append(TradeSignal(
                strategy="News_Spike_Fade",
                direction="SELL",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=55,
                reasoning=(f"Abnormal bullish spike detected (body={last_body:.5f}, ATR={atr:.5f}, "
                           f"ratio={last_body/atr:.1f}x). Market likely overreacted. "
                           f"Fading the spike. TP at 50% retracement ({retracement_50:.5f})."),
                timestamp=str(df.index[-1])
            ))

        elif spike_range < 0:
            # Bearish spike → FADE long
            entry = current_price
            sl = df["low"].iloc[-1] - 0.5 * atr
            tp = retracement_50
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append(TradeSignal(
                strategy="News_Spike_Fade",
                direction="BUY",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=55,
                reasoning=(f"Abnormal bearish spike detected (body={last_body:.5f}, ATR={atr:.5f}, "
                           f"ratio={last_body/atr:.1f}x). Market likely overreacted. "
                           f"Fading the spike. TP at 50% retracement ({retracement_50:.5f})."),
                timestamp=str(df.index[-1])
            ))

        return signals
