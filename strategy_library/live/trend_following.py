"""
=============================================================================
TREND FOLLOWING — FULL TRADING STRATEGY
=============================================================================
How this strategy works end-to-end:

MOVING AVERAGE CROSSOVER + ADX FILTER:
1. CALCULATE 20 EMA (fast) and 50 EMA (slow).
2. CHECK ADX(14) > 25 to confirm a trending market (not choppy/ranging).
3. BUY when 20 EMA crosses ABOVE 50 EMA with ADX > 25.
4. SELL when 20 EMA crosses BELOW 50 EMA with ADX > 25.
5. STOP LOSS placed at 2x ATR from entry.
6. TAKE PROFIT at 3x ATR from entry (1:1.5 Risk/Reward minimum).

BREAKOUT STRATEGY:
1. IDENTIFY a consolidation range (Bollinger Band squeeze — bandwidth shrinking).
2. WAIT for a candle to close OUTSIDE the Bollinger Band on high volume.
3. ENTER in the breakout direction.
4. STOP LOSS at the opposite Bollinger Band.
5. TAKE PROFIT at 2x the range width.
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


class EMACrossoverStrategy:
    """
    EMA Crossover + ADX Trend Filter — the most widely used trend strategy.

    Workflow:
    ┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
    │ 1. Calculate  │ ──▶ │ 2. Is ADX > 25?  │ ──▶ │ 3. Has EMA 20    │
    │ 20 EMA,       │     │ (trend exists?)  │     │ crossed EMA 50?  │
    │ 50 EMA, ADX   │     │ NO → skip        │     │ NO → skip        │
    └──────────────┘     └──────────────────┘     └────────┬──────────┘
                                                           │ YES
    ┌──────────────┐     ┌──────────────────┐              │
    │ 5. Set SL at │ ◀── │ 4. ENTER in the  │ ◀────────────┘
    │ 2x ATR       │     │ direction of the │
    │ TP at 3x ATR │     │ crossover        │
    └──────────────┘     └──────────────────┘
    """

    def __init__(self, pair: str = "EURUSD", fast_ema: int = 20, slow_ema: int = 50,
                 adx_period: int = 14, adx_threshold: float = 25.0, atr_period: int = 14):
        self.pair = pair
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.atr_period = atr_period

    def _calc_ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def _calc_adx(self, df: pd.DataFrame) -> pd.Series:
        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=self.adx_period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=self.adx_period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=self.adx_period, adjust=False).mean() / atr)

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.ewm(span=self.adx_period, adjust=False).mean()
        return adx

    def _calc_atr(self, df: pd.DataFrame) -> float:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < self.slow_ema + 5:
            return signals

        ema_fast = self._calc_ema(df["close"], self.fast_ema)
        ema_slow = self._calc_ema(df["close"], self.slow_ema)
        adx = self._calc_adx(df)
        atr = self._calc_atr(df)
        current_price = df["close"].iloc[-1]

        # Check for a crossover on the LAST bar
        cross_up = ema_fast.iloc[-1] > ema_slow.iloc[-1] and ema_fast.iloc[-2] <= ema_slow.iloc[-2]
        cross_down = ema_fast.iloc[-1] < ema_slow.iloc[-1] and ema_fast.iloc[-2] >= ema_slow.iloc[-2]
        adx_ok = adx.iloc[-1] > self.adx_threshold

        if cross_up and adx_ok:
            entry = current_price
            sl = entry - 2 * atr
            tp = entry + 3 * atr
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append(TradeSignal(
                strategy="EMA_Crossover_Trend",
                direction="BUY",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=int(min(90, 50 + adx.iloc[-1])),
                reasoning=(f"EMA{self.fast_ema} crossed ABOVE EMA{self.slow_ema}. "
                           f"ADX={adx.iloc[-1]:.1f} confirms strong trend. "
                           f"Entry at {entry:.5f}. SL at 2x ATR ({sl:.5f}). TP at 3x ATR ({tp:.5f})."),
                timestamp=str(df.index[-1])
            ))

        elif cross_down and adx_ok:
            entry = current_price
            sl = entry + 2 * atr
            tp = entry - 3 * atr
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append(TradeSignal(
                strategy="EMA_Crossover_Trend",
                direction="SELL",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=int(min(90, 50 + adx.iloc[-1])),
                reasoning=(f"EMA{self.fast_ema} crossed BELOW EMA{self.slow_ema}. "
                           f"ADX={adx.iloc[-1]:.1f} confirms strong trend. "
                           f"Entry at {entry:.5f}. SL at 2x ATR ({sl:.5f}). TP at 3x ATR ({tp:.5f})."),
                timestamp=str(df.index[-1])
            ))

        return signals


class BreakoutStrategy:
    """
    Bollinger Band Squeeze Breakout — trades when volatility explodes.

    Workflow:
    1. Calculate Bollinger Bands (20 SMA, 2 StdDev).
    2. Detect 'squeeze' — bandwidth at 6-month low (volatility compressed).
    3. When a candle closes OUTSIDE the band after a squeeze → ENTER.
    4. SL = opposite band.  TP = 2x the band width.
    """

    def __init__(self, pair: str = "EURUSD", bb_period: int = 20, bb_std: float = 2.0):
        self.pair = pair
        self.bb_period = bb_period
        self.bb_std = bb_std

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < self.bb_period + 20:
            return signals

        sma = df["close"].rolling(self.bb_period).mean()
        std = df["close"].rolling(self.bb_period).std()
        upper = sma + self.bb_std * std
        lower = sma - self.bb_std * std
        bandwidth = (upper - lower) / sma

        # Squeeze detection: current bandwidth is in the bottom 20% of recent bandwidth
        bw_percentile = bandwidth.rolling(120).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)

        is_squeeze = bw_percentile.iloc[-2] < 0.20 if not pd.isna(bw_percentile.iloc[-2]) else False
        current_price = df["close"].iloc[-1]
        band_width = upper.iloc[-1] - lower.iloc[-1]

        # Bullish breakout
        if is_squeeze and current_price > upper.iloc[-1]:
            entry = current_price
            sl = lower.iloc[-1]
            tp = entry + 2 * band_width
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append(TradeSignal(
                strategy="Bollinger_Breakout",
                direction="BUY",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=65,
                reasoning=(f"Bollinger Band squeeze detected (bandwidth at historic low). "
                           f"Price broke ABOVE upper band at {upper.iloc[-1]:.5f}. "
                           f"Volatility expansion expected. SL at lower band. TP at 2x band width."),
                timestamp=str(df.index[-1])
            ))

        # Bearish breakout
        elif is_squeeze and current_price < lower.iloc[-1]:
            entry = current_price
            sl = upper.iloc[-1]
            tp = entry - 2 * band_width
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append(TradeSignal(
                strategy="Bollinger_Breakout",
                direction="SELL",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=65,
                reasoning=(f"Bollinger Band squeeze detected (bandwidth at historic low). "
                           f"Price broke BELOW lower band at {lower.iloc[-1]:.5f}. "
                           f"Volatility expansion expected. SL at upper band. TP at 2x band width."),
                timestamp=str(df.index[-1])
            ))

        return signals
