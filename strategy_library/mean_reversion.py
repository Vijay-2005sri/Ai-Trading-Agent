"""
=============================================================================
MEAN REVERSION — FULL TRADING STRATEGY
=============================================================================
How this strategy works end-to-end:

RSI OVERSOLD/OVERBOUGHT REVERSAL:
1. CALCULATE RSI(14).
2. WAIT for RSI to drop below 30 (oversold) or above 70 (overbought).
3. WAIT for RSI to CROSS BACK above 30 (bullish reversal signal) or below 70.
4. ENTER on the RSI cross-back candle.
5. STOP LOSS at the recent swing extreme (lowest low for buys).
6. TAKE PROFIT when RSI reaches 50 (the mean).

SUPPLY & DEMAND ZONE BOUNCE:
1. IDENTIFY zones where price previously made a sharp move (imbalance).
2. WAIT for price to return to that zone.
3. ENTER with a reversal candlestick confirmation at the zone.
4. STOP LOSS beyond the zone.
5. TAKE PROFIT at the opposing zone.
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


class RSIMeanReversionStrategy:
    """
    RSI(14) Oversold/Overbought Reversal — classic mean reversion.

    Workflow:
    ┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
    │ 1. Calculate  │ ──▶ │ 2. Was RSI < 30  │ ──▶ │ 3. Has RSI now    │
    │ RSI(14)       │     │ (oversold) on    │     │ crossed BACK      │
    │               │     │ previous bar?    │     │ above 30?         │
    └──────────────┘     └──────────────────┘     └────────┬──────────┘
                                                           │ YES
    ┌──────────────┐     ┌──────────────────┐              │
    │ 5. SL at     │ ◀── │ 4. BUY signal.   │ ◀────────────┘
    │ recent low.  │     │ Price is         │
    │ TP when RSI  │     │ reverting to     │
    │ hits 50.     │     │ the mean.        │
    └──────────────┘     └──────────────────┘
    """

    def __init__(self, pair: str = "EURUSD", rsi_period: int = 14,
                 oversold: float = 30, overbought: float = 70, atr_period: int = 14):
        self.pair = pair
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.atr_period = atr_period

    def _calc_rsi(self, series: pd.Series) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _calc_atr(self, df: pd.DataFrame) -> float:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < self.rsi_period + 5:
            return signals

        rsi = self._calc_rsi(df["close"])
        atr = self._calc_atr(df)
        current_price = df["close"].iloc[-1]

        # Bullish RSI reversal: was oversold, now crossing back up
        if rsi.iloc[-2] < self.oversold and rsi.iloc[-1] >= self.oversold:
            recent_low = df["low"].iloc[-20:].min()
            entry = current_price
            sl = recent_low - 0.5 * atr
            # TP estimate: price level where RSI would reach ~50 (use 1.5x ATR as proxy)
            tp = entry + 2.5 * atr
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append(TradeSignal(
                strategy="RSI_Mean_Reversion",
                direction="BUY",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=60,
                reasoning=(f"RSI crossed back ABOVE {self.oversold} (was {rsi.iloc[-2]:.1f}, now {rsi.iloc[-1]:.1f}). "
                           f"Oversold reversal detected. Entry at {entry:.5f}. "
                           f"SL below recent low {recent_low:.5f}. TP at mean reversion target."),
                timestamp=str(df.index[-1])
            ))

        # Bearish RSI reversal: was overbought, now crossing back down
        if rsi.iloc[-2] > self.overbought and rsi.iloc[-1] <= self.overbought:
            recent_high = df["high"].iloc[-20:].max()
            entry = current_price
            sl = recent_high + 0.5 * atr
            tp = entry - 2.5 * atr
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append(TradeSignal(
                strategy="RSI_Mean_Reversion",
                direction="SELL",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=60,
                reasoning=(f"RSI crossed back BELOW {self.overbought} (was {rsi.iloc[-2]:.1f}, now {rsi.iloc[-1]:.1f}). "
                           f"Overbought reversal detected. Entry at {entry:.5f}. "
                           f"SL above recent high {recent_high:.5f}. TP at mean reversion target."),
                timestamp=str(df.index[-1])
            ))

        return signals


class SupplyDemandZoneStrategy:
    """
    Supply & Demand Zone Bounce — institutional imbalance zones.

    Workflow:
    1. Scan history for zones where price left with a sharp impulse (>2x ATR body).
    2. When price RETURNS to that zone, look for a reversal candle.
    3. Enter in the direction opposite to how price originally left the zone.
    4. SL beyond the zone boundary. TP at the next opposing zone.
    """

    def __init__(self, pair: str = "EURUSD", atr_period: int = 14, zone_lookback: int = 100):
        self.pair = pair
        self.atr_period = atr_period
        self.zone_lookback = zone_lookback

    def _calc_atr(self, df: pd.DataFrame) -> float:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def _find_zones(self, df: pd.DataFrame, atr: float) -> list[dict]:
        zones = []
        for i in range(1, min(self.zone_lookback, len(df) - 1)):
            idx = len(df) - 1 - i
            body = abs(df["close"].iloc[idx] - df["open"].iloc[idx])

            if body > 2 * atr:  # Strong impulse candle
                if df["close"].iloc[idx] > df["open"].iloc[idx]:
                    # Bullish impulse — the base before it is a DEMAND zone
                    if idx > 0:
                        zones.append({
                            "type": "demand",
                            "zone_top": df["high"].iloc[idx - 1],
                            "zone_bottom": df["low"].iloc[idx - 1],
                            "origin_idx": idx - 1
                        })
                else:
                    # Bearish impulse — the base before it is a SUPPLY zone
                    if idx > 0:
                        zones.append({
                            "type": "supply",
                            "zone_top": df["high"].iloc[idx - 1],
                            "zone_bottom": df["low"].iloc[idx - 1],
                            "origin_idx": idx - 1
                        })
        return zones

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < self.zone_lookback:
            return signals

        atr = self._calc_atr(df)
        zones = self._find_zones(df, atr)
        current_price = df["close"].iloc[-1]
        is_bullish_candle = df["close"].iloc[-1] > df["open"].iloc[-1]
        is_bearish_candle = df["close"].iloc[-1] < df["open"].iloc[-1]

        for zone in zones:
            # Price returned to a DEMAND zone + bullish confirmation = BUY
            if zone["type"] == "demand" and zone["zone_bottom"] <= current_price <= zone["zone_top"]:
                if is_bullish_candle:
                    entry = current_price
                    sl = zone["zone_bottom"] - 0.5 * atr
                    tp = entry + 3 * atr
                    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                    signals.append(TradeSignal(
                        strategy="Supply_Demand_Zone",
                        direction="BUY",
                        pair=self.pair,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5),
                        take_profit=round(tp, 5),
                        risk_reward=round(rr, 2),
                        confidence=62,
                        reasoning=(f"Price returned to a Demand Zone ({zone['zone_bottom']:.5f}-{zone['zone_top']:.5f}). "
                                   f"Bullish reversal candle confirmed. "
                                   f"SL below zone. TP at 3x ATR."),
                        timestamp=str(df.index[-1])
                    ))
                    break  # Only one signal per zone type

            # Price returned to a SUPPLY zone + bearish confirmation = SELL
            if zone["type"] == "supply" and zone["zone_bottom"] <= current_price <= zone["zone_top"]:
                if is_bearish_candle:
                    entry = current_price
                    sl = zone["zone_top"] + 0.5 * atr
                    tp = entry - 3 * atr
                    rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

                    signals.append(TradeSignal(
                        strategy="Supply_Demand_Zone",
                        direction="SELL",
                        pair=self.pair,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5),
                        take_profit=round(tp, 5),
                        risk_reward=round(rr, 2),
                        confidence=62,
                        reasoning=(f"Price returned to a Supply Zone ({zone['zone_bottom']:.5f}-{zone['zone_top']:.5f}). "
                                   f"Bearish reversal candle confirmed. "
                                   f"SL above zone. TP at 3x ATR."),
                        timestamp=str(df.index[-1])
                    ))
                    break
        return signals
