"""
=============================================================================
ICT (Inner Circle Trader) — FULL TRADING STRATEGY
=============================================================================
How this strategy works end-to-end:

ICT SILVER BULLET STRATEGY:
1. WAIT for a specific Kill Zone (London Open 02:00-05:00 EST or NY AM 10:00-11:00 EST).
2. IDENTIFY the initial range formed in the first 30 minutes of the Kill Zone.
3. WAIT for a Judas Swing — price fakes out one direction to grab liquidity.
4. ENTER in the OPPOSITE direction once price shows displacement (strong candle).
5. STOP LOSS behind the Judas Swing extreme.
6. TAKE PROFIT at the FVG created by the displacement OR the session high/low.

ICT OPTIMAL TRADE ENTRY (OTE):
1. IDENTIFY a strong impulsive move (displacement).
2. DRAW Fibonacci from the swing low to swing high (or vice versa).
3. WAIT for price to retrace to the 62%-79% Fibonacci zone (the OTE zone).
4. ENTER at OTE zone with confirmation (e.g., bullish engulfing).
5. STOP LOSS below the 100% Fibonacci level.
6. TAKE PROFIT at the -27% or -62% Fibonacci extension.
=============================================================================
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
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


class ICTSilverBulletStrategy:
    """
    ICT Silver Bullet — Executes during specific Kill Zones.

    Kill Zones (EST / New York Time):
      - London Kill Zone:  02:00 – 05:00 EST
      - NY AM Kill Zone:   10:00 – 11:00 EST
      - NY PM Kill Zone:   14:00 – 15:00 EST

    Workflow:
    ┌───────────────┐     ┌──────────────────┐     ┌──────────────────┐
    │ 1. Is it a    │ ──▶ │ 2. Get initial   │ ──▶ │ 3. Did price do  │
    │ Kill Zone?    │     │ range (first 30  │     │ a Judas Swing?   │
    │ (time filter) │     │ mins of session) │     │ (fake breakout)  │
    └───────────────┘     └──────────────────┘     └────────┬─────────┘
                                                            │
    ┌───────────────┐     ┌──────────────────┐              │
    │ 5. SL behind  │ ◀── │ 4. ENTER opposite│ ◀────────────┘
    │ the Judas     │     │ direction with   │
    │ TP at FVG or  │     │ displacement     │
    │ session level │     │ confirmation     │
    └───────────────┘     └──────────────────┘
    """

    # Kill Zone hours in UTC (adjusted from EST + 5)
    KILL_ZONES = {
        "london": {"start": 7, "end": 10},     # 02-05 EST = 07-10 UTC
        "ny_am":  {"start": 14, "end": 15},     # 10-11 EST = 14-15 UTC  (if EST=UTC-5, 10+4=14 UTC during summer)
        "ny_pm":  {"start": 18, "end": 19},     # 14-15 EST
    }

    def __init__(self, pair: str = "EURUSD", atr_period: int = 14):
        self.pair = pair
        self.atr_period = atr_period

    def _is_kill_zone(self, timestamp: pd.Timestamp) -> Optional[str]:
        hour = timestamp.hour
        for kz_name, kz_hours in self.KILL_ZONES.items():
            if kz_hours["start"] <= hour < kz_hours["end"]:
                return kz_name
        return None

    def _calc_atr(self, df: pd.DataFrame) -> float:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean().iloc[-1]

    def _detect_judas_swing(self, df: pd.DataFrame, window: int = 6) -> Optional[dict]:
        """
        A Judas Swing is when price breaks one side of the initial range
        and then reverses sharply (displacement) in the opposite direction.
        """
        if len(df) < window + 2:
            return None

        # Initial range = first 'window/2' candles of the kill zone
        init_range_bars = window // 2
        init_high = df["high"].iloc[-window: -window + init_range_bars].max()
        init_low = df["low"].iloc[-window: -window + init_range_bars].min()

        # Check later candles for a fake breakout + reversal
        for i in range(-init_range_bars, 0):
            # Bearish Judas Swing: price spiked above range then reversed down
            if df["high"].iloc[i] > init_high and df["close"].iloc[i] < init_high:
                # Displacement = next candle is a strong bearish candle
                if i + 1 < 0 or i + 1 == 0:
                    next_i = len(df) + i + 1 if i + 1 < 0 else len(df) - 1
                else:
                    continue
                if next_i < len(df) and df["close"].iloc[next_i] < df["open"].iloc[next_i]:
                    return {
                        "type": "bearish_judas",
                        "fake_high": df["high"].iloc[i],
                        "init_low": init_low,
                        "displacement_close": df["close"].iloc[next_i]
                    }

            # Bullish Judas Swing: price spiked below range then reversed up
            if df["low"].iloc[i] < init_low and df["close"].iloc[i] > init_low:
                if i + 1 < 0 or i + 1 == 0:
                    next_i = len(df) + i + 1 if i + 1 < 0 else len(df) - 1
                else:
                    continue
                if next_i < len(df) and df["close"].iloc[next_i] > df["open"].iloc[next_i]:
                    return {
                        "type": "bullish_judas",
                        "fake_low": df["low"].iloc[i],
                        "init_high": init_high,
                        "displacement_close": df["close"].iloc[next_i]
                    }
        return None

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < 20:
            return signals

        current_time = df.index[-1]
        kz = self._is_kill_zone(current_time)
        if kz is None:
            return signals  # Not in a Kill Zone — do nothing

        atr = self._calc_atr(df)
        judas = self._detect_judas_swing(df)
        if judas is None:
            return signals

        if judas["type"] == "bullish_judas":
            entry = judas["displacement_close"]
            sl = judas["fake_low"] - 0.3 * atr
            tp = judas["init_high"] + 1.0 * atr
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append(TradeSignal(
                strategy=f"ICT_Silver_Bullet_{kz}",
                direction="BUY",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=70,
                reasoning=(f"[{kz.upper()} Kill Zone] Bullish Judas Swing detected. "
                           f"Price swept below {judas['fake_low']:.5f} and reversed with displacement. "
                           f"Entry at {entry:.5f}. SL below fake low. TP at session high + ATR."),
                timestamp=str(current_time)
            ))

        elif judas["type"] == "bearish_judas":
            entry = judas["displacement_close"]
            sl = judas["fake_high"] + 0.3 * atr
            tp = judas["init_low"] - 1.0 * atr
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append(TradeSignal(
                strategy=f"ICT_Silver_Bullet_{kz}",
                direction="SELL",
                pair=self.pair,
                entry_price=round(entry, 5),
                stop_loss=round(sl, 5),
                take_profit=round(tp, 5),
                risk_reward=round(rr, 2),
                confidence=70,
                reasoning=(f"[{kz.upper()} Kill Zone] Bearish Judas Swing detected. "
                           f"Price swept above {judas['fake_high']:.5f} and reversed with displacement. "
                           f"Entry at {entry:.5f}. SL above fake high. TP at session low - ATR."),
                timestamp=str(current_time)
            ))

        return signals


class ICTOptimalTradeEntry:
    """
    ICT OTE (Optimal Trade Entry) — Fibonacci-Based Pullback Strategy.

    Workflow:
    1. Find a strong impulse move (displacement leg).
    2. Draw Fibonacci retracement from swing low → swing high (for longs).
    3. Wait for price to pull back into the 62% – 79% zone (OTE zone).
    4. Enter with a bullish confirmation candle inside OTE zone.
    5. SL below the 100% Fibonacci level.
    6. TP at the -27% or -62% Fibonacci extension.
    """

    def __init__(self, pair: str = "EURUSD", fib_entry_low: float = 0.62, fib_entry_high: float = 0.79):
        self.pair = pair
        self.fib_entry_low = fib_entry_low
        self.fib_entry_high = fib_entry_high

    def _find_last_impulse(self, df: pd.DataFrame, lookback: int = 30, min_atr_multiple: float = 2.0) -> Optional[dict]:
        """Find the most recent strong impulse move."""
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]

        for i in range(len(df) - 2, max(len(df) - lookback, 5), -1):
            move = abs(df["close"].iloc[i] - df["open"].iloc[i])
            if move > min_atr_multiple * atr:
                if df["close"].iloc[i] > df["open"].iloc[i]:
                    # Bullish impulse — find the swing low before it
                    swing_low = df["low"].iloc[max(0, i - 10):i + 1].min()
                    swing_high = df["high"].iloc[i]
                    return {"direction": "bullish", "swing_low": swing_low, "swing_high": swing_high, "idx": i}
                else:
                    swing_high = df["high"].iloc[max(0, i - 10):i + 1].max()
                    swing_low = df["low"].iloc[i]
                    return {"direction": "bearish", "swing_high": swing_high, "swing_low": swing_low, "idx": i}
        return None

    def generate_signals(self, df: pd.DataFrame) -> list[TradeSignal]:
        signals = []
        if len(df) < 40:
            return signals

        impulse = self._find_last_impulse(df)
        if impulse is None:
            return signals

        current_price = df["close"].iloc[-1]
        fib_range = impulse["swing_high"] - impulse["swing_low"]

        if impulse["direction"] == "bullish":
            ote_top = impulse["swing_high"] - self.fib_entry_low * fib_range
            ote_bottom = impulse["swing_high"] - self.fib_entry_high * fib_range

            if ote_bottom <= current_price <= ote_top:
                # Confirmation: is the current candle bullish?
                if df["close"].iloc[-1] > df["open"].iloc[-1]:
                    entry = current_price
                    sl = impulse["swing_low"] - 0.001  # Below the 100% fib
                    tp = impulse["swing_high"] + 0.27 * fib_range  # -27% extension
                    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                    signals.append(TradeSignal(
                        strategy="ICT_OTE_Long",
                        direction="BUY",
                        pair=self.pair,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5),
                        take_profit=round(tp, 5),
                        risk_reward=round(rr, 2),
                        confidence=65,
                        reasoning=(f"Bullish impulse detected. Price pulled back into OTE zone "
                                   f"({self.fib_entry_low*100:.0f}%-{self.fib_entry_high*100:.0f}% Fib). "
                                   f"Bullish confirmation candle at {entry:.5f}. "
                                   f"SL below swing low. TP at -27% Fib extension."),
                        timestamp=str(df.index[-1])
                    ))

        elif impulse["direction"] == "bearish":
            ote_bottom = impulse["swing_low"] + self.fib_entry_low * fib_range
            ote_top = impulse["swing_low"] + self.fib_entry_high * fib_range

            if ote_bottom <= current_price <= ote_top:
                if df["close"].iloc[-1] < df["open"].iloc[-1]:
                    entry = current_price
                    sl = impulse["swing_high"] + 0.001
                    tp = impulse["swing_low"] - 0.27 * fib_range
                    rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

                    signals.append(TradeSignal(
                        strategy="ICT_OTE_Short",
                        direction="SELL",
                        pair=self.pair,
                        entry_price=round(entry, 5),
                        stop_loss=round(sl, 5),
                        take_profit=round(tp, 5),
                        risk_reward=round(rr, 2),
                        confidence=65,
                        reasoning=(f"Bearish impulse detected. Price pulled back into OTE zone "
                                   f"({self.fib_entry_low*100:.0f}%-{self.fib_entry_high*100:.0f}% Fib). "
                                   f"Bearish confirmation candle at {entry:.5f}. "
                                   f"SL above swing high. TP at -27% Fib extension."),
                        timestamp=str(df.index[-1])
                    ))

        return signals
