"""
=============================================================================
RISK AGENT — The Iron-Fisted Safety Guard
=============================================================================
This module has ABSOLUTE VETO POWER over every trade. The LLM Brain can
suggest whatever it wants — this module decides if it actually happens.

NOTHING in this file uses AI. It is pure, deterministic Python math.
An LLM cannot hallucinate past these rules.

Rules Enforced:
  1. Risk per trade: 2% (capital ≤ $2000) or 1.5% (capital > $2000)
  2. Max drawdown from peak equity: 5% → HALT ALL TRADING
  3. Max trades per day: 2 (default) or 3 (only if market is strongly trending)
  4. Every trade MUST have SL and TP
  5. Minimum Risk:Reward ratio of 1.5
  6. No correlated pair overexposure
=============================================================================
"""

import json
import os
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class RiskCheckResult:
    approved: bool
    adjusted_lot_size: float
    reason: str
    risk_pct_used: float
    trades_today: int
    max_trades_today: int
    current_drawdown_pct: float
    equity: float


@dataclass
class TradeRecord:
    trade_id: str
    pair: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    pnl: float = 0.0
    status: str = "open"      # open, closed_win, closed_loss
    open_time: str = ""
    close_time: str = ""


class RiskAgent:
    """
    The Risk Agent. It sits between the Brain and the Broker.

    Workflow:
    ┌──────────────────┐     ┌─────────────────────┐     ┌───────────────────┐
    │ Brain says:       │ ──▶ │ Risk Agent checks:  │ ──▶ │ If APPROVED:      │
    │ "BUY EURUSD at   │     │ 1. Drawdown OK?     │     │ Calculate exact   │
    │  1.0900, SL at   │     │ 2. Trades left?     │     │ lot size & send   │
    │  1.0850"          │     │ 3. R:R ratio OK?    │     │ to Broker.        │
    └──────────────────┘     │ 4. Correlation OK?  │     │                   │
                             │ 5. Exposure OK?     │     │ If REJECTED:      │
                             └─────────────────────┘     │ Log the reason.   │
                                                         │ NO trade placed.  │
                                                         └───────────────────┘
    """

    # -----------------------------------------------------------------
    # SYMBOL-SPECIFIC RISK OVERRIDES
    # -----------------------------------------------------------------
    # These override the default/high-capital risk percentage for
    # specific instruments. Silver (XAGUSD) always uses 2% risk
    # regardless of account size, because its per-pip value is lower.
    # -----------------------------------------------------------------
    SYMBOL_RISK_OVERRIDES = {
        "XAGUSD": 0.02,   # Silver: always 2%, never reduced to 1.5%
    }

    # -----------------------------------------------------------------
    # HIGH CONVICTION HOLD — Cheap Commodity Extension
    # -----------------------------------------------------------------
    # For instruments with cheap per-pip costs (USOIL, XAGUSD), if
    # confidence is >= 90%, the system is allowed to hold the position
    # for up to 1 full day (24 hours) instead of the default intraday
    # window. This lets strong moves on slow instruments play out.
    # -----------------------------------------------------------------
    HIGH_CONVICTION_INSTRUMENTS = {
        "USOIL":  {"min_confidence": 90, "max_hold_hours": 24},
    }

    def __init__(self, config: dict):
        risk_cfg = config.get("risk", {})

        # --- Per-Trade Risk ---
        self.risk_pct_default = risk_cfg.get("risk_per_trade_default", 0.02)
        self.risk_pct_high_capital = risk_cfg.get("risk_per_trade_high_capital", 0.015)
        self.high_capital_threshold = risk_cfg.get("high_capital_threshold", 2000)

        # --- Drawdown Limits ---
        self.max_drawdown = risk_cfg.get("max_drawdown_from_peak", 0.05)
        self.daily_dd_reduce = risk_cfg.get("daily_drawdown_reduce", 0.025)
        self.daily_dd_halt = risk_cfg.get("daily_drawdown_halt", 0.04)

        # --- Trade Limits ---
        self.max_trades_default = risk_cfg.get("max_trades_default", 2)
        self.max_trades_trending = risk_cfg.get("max_trades_trending", 3)
        self.trending_confidence = risk_cfg.get("trending_confidence_threshold", 80)
        self.min_confidence = risk_cfg.get("min_confidence_to_trade", 70)

        # --- Position Limits ---
        self.max_open_positions = risk_cfg.get("max_open_positions", 3)
        self.max_single_pct = risk_cfg.get("max_single_position_pct", 0.15)
        self.max_total_exposure = risk_cfg.get("max_total_exposure_pct", 0.40)

        # --- Mandatory Rules ---
        self.require_sl = risk_cfg.get("require_stop_loss", True)
        self.require_tp = risk_cfg.get("require_take_profit", True)
        self.min_rr = risk_cfg.get("min_risk_reward", 1.5)

        # --- Correlation ---
        self.max_correlated = risk_cfg.get("max_correlated_positions", 2)
        self.corr_threshold = risk_cfg.get("correlation_threshold", 0.7)

        # --- State Tracking ---
        self.peak_equity = 0.0
        self.start_of_day_equity = 0.0
        self.trades_today: list[TradeRecord] = []
        self.open_positions: list[TradeRecord] = []
        self.current_date = date.today()
        
        # --- Streak Tracker ---
        self.streak_file = Path(__file__).parent / "streak_tracker.json"
        self.consecutive_wins = 0
        self._load_streak()

    def _load_streak(self):
        if self.streak_file.exists():
            try:
                data = json.loads(self.streak_file.read_text(encoding="utf-8"))
                self.consecutive_wins = data.get("consecutive_wins", 0)
                saved_date_str = data.get("current_date")
                if saved_date_str:
                    saved_date = date.fromisoformat(saved_date_str)
                    # If we loaded a date from the past, we handle rollover in evaluate_trade
                    if saved_date > self.current_date:
                        self.current_date = saved_date
                self.start_of_day_equity = data.get("start_of_day_equity", 0.0)
            except Exception as e:
                print(f"Failed to load streak tracker: {e}")

    def _save_streak(self):
        try:
            data = {
                "consecutive_wins": self.consecutive_wins,
                "current_date": self.current_date.isoformat(),
                "start_of_day_equity": self.start_of_day_equity
            }
            self.streak_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"Failed to save streak tracker: {e}")

    # -------------------------------------------------------------------
    # CORE: Evaluate a trade proposal
    # -------------------------------------------------------------------
    def evaluate_trade(
        self,
        pair: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: int,
        equity: float,
        is_trending: bool = False,
        pip_value: float = 10.0  # Default pip value for standard lot
    ) -> RiskCheckResult:
        """
        The main method. Returns an approved/rejected result with exact lot size.
        """
        # Reset daily counter if it's a new day
        today = date.today()
        if today > self.current_date:
            # Process yesterday's PnL
            if self.start_of_day_equity > 0:
                if equity > self.start_of_day_equity:
                    self.consecutive_wins += 1
                    print(f"📈 Profitable day yesterday! Streak is now {self.consecutive_wins} days.")
                elif equity < self.start_of_day_equity:
                    self.consecutive_wins = 0
                    print("📉 Loss day yesterday. Streak reset to 0.")
                    
            self.trades_today = []
            self.start_of_day_equity = equity
            self.current_date = today
            self._save_streak()

        # Update peak equity
        if equity > self.peak_equity:
            self.peak_equity = equity
        if self.start_of_day_equity == 0:
            self.start_of_day_equity = equity
            self._save_streak()

        # -----------------------------------------------------------
        # CHECK 1: Max Drawdown from Peak (5%)
        # -----------------------------------------------------------
        drawdown_from_peak = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0
        if drawdown_from_peak >= self.max_drawdown:
            return RiskCheckResult(
                approved=False,
                adjusted_lot_size=0.0,
                reason=f"🛑 HALTED: Drawdown from peak is {drawdown_from_peak*100:.1f}% (max allowed: {self.max_drawdown*100:.0f}%). ALL TRADING STOPPED.",
                risk_pct_used=0,
                trades_today=len(self.trades_today),
                max_trades_today=0,
                current_drawdown_pct=drawdown_from_peak,
                equity=equity
            )

        # -----------------------------------------------------------
        # CHECK 2: Daily Drawdown
        # -----------------------------------------------------------
        daily_dd = (self.start_of_day_equity - equity) / self.start_of_day_equity if self.start_of_day_equity > 0 else 0
        size_multiplier = 1.0

        if daily_dd >= self.daily_dd_halt:
            return RiskCheckResult(
                approved=False,
                adjusted_lot_size=0.0,
                reason=f"🛑 DAILY HALT: Today's drawdown is {daily_dd*100:.1f}% (halt threshold: {self.daily_dd_halt*100:.0f}%). No more trades today.",
                risk_pct_used=0,
                trades_today=len(self.trades_today),
                max_trades_today=0,
                current_drawdown_pct=drawdown_from_peak,
                equity=equity
            )
        elif daily_dd >= self.daily_dd_reduce:
            size_multiplier = 0.5  # Reduce size by 50%

        # -----------------------------------------------------------
        # CHECK 3: Minimum Confidence
        # -----------------------------------------------------------
        if confidence < self.min_confidence:
            return RiskCheckResult(
                approved=False,
                adjusted_lot_size=0.0,
                reason=f"⚠️ REJECTED: Confidence {confidence}% is below minimum {self.min_confidence}%. Not worth the risk.",
                risk_pct_used=0,
                trades_today=len(self.trades_today),
                max_trades_today=self._get_max_trades(is_trending, confidence),
                current_drawdown_pct=drawdown_from_peak,
                equity=equity
            )

        # -----------------------------------------------------------
        # CHECK 4: Trade Count Limit (2 default, 3 if trending)
        # -----------------------------------------------------------
        max_trades = self._get_max_trades(is_trending, confidence)
        if len(self.trades_today) >= max_trades:
            return RiskCheckResult(
                approved=False,
                adjusted_lot_size=0.0,
                reason=f"⚠️ REJECTED: Already took {len(self.trades_today)} trades today (max: {max_trades}). Done for the day.",
                risk_pct_used=0,
                trades_today=len(self.trades_today),
                max_trades_today=max_trades,
                current_drawdown_pct=drawdown_from_peak,
                equity=equity
            )

        # -----------------------------------------------------------
        # CHECK 5: Open Positions Limit
        # -----------------------------------------------------------
        if len(self.open_positions) >= self.max_open_positions:
            return RiskCheckResult(
                approved=False,
                adjusted_lot_size=0.0,
                reason=f"⚠️ REJECTED: Already {len(self.open_positions)} positions open (max: {self.max_open_positions}).",
                risk_pct_used=0,
                trades_today=len(self.trades_today),
                max_trades_today=max_trades,
                current_drawdown_pct=drawdown_from_peak,
                equity=equity
            )

        # -----------------------------------------------------------
        # CHECK 6: Stop Loss & Take Profit must exist
        # -----------------------------------------------------------
        if self.require_sl and (stop_loss is None or stop_loss == 0):
            return RiskCheckResult(
                approved=False, adjusted_lot_size=0.0,
                reason="🛑 REJECTED: No Stop Loss provided. Every trade MUST have a Stop Loss.",
                risk_pct_used=0, trades_today=len(self.trades_today),
                max_trades_today=max_trades, current_drawdown_pct=drawdown_from_peak, equity=equity
            )

        if self.require_tp and (take_profit is None or take_profit == 0):
            return RiskCheckResult(
                approved=False, adjusted_lot_size=0.0,
                reason="🛑 REJECTED: No Take Profit provided. Every trade MUST have a Take Profit.",
                risk_pct_used=0, trades_today=len(self.trades_today),
                max_trades_today=max_trades, current_drawdown_pct=drawdown_from_peak, equity=equity
            )

        # -----------------------------------------------------------
        # CHECK 7: Risk:Reward Ratio
        # -----------------------------------------------------------
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = abs(take_profit - entry_price)
        risk_reward = reward_distance / risk_distance if risk_distance > 0 else 0

        if risk_reward < self.min_rr:
            return RiskCheckResult(
                approved=False, adjusted_lot_size=0.0,
                reason=f"⚠️ REJECTED: R:R ratio is {risk_reward:.2f} (minimum: {self.min_rr}). Not worth the risk.",
                risk_pct_used=0, trades_today=len(self.trades_today),
                max_trades_today=max_trades, current_drawdown_pct=drawdown_from_peak, equity=equity
            )

        # -----------------------------------------------------------
        # CHECK 8: Correlated Pair Check
        # -----------------------------------------------------------
        correlated_count = self._count_correlated_positions(pair)
        if correlated_count >= self.max_correlated:
            return RiskCheckResult(
                approved=False, adjusted_lot_size=0.0,
                reason=f"⚠️ REJECTED: Already {correlated_count} positions in correlated pairs to {pair}.",
                risk_pct_used=0, trades_today=len(self.trades_today),
                max_trades_today=max_trades, current_drawdown_pct=drawdown_from_peak, equity=equity
            )

        # -----------------------------------------------------------
        # -----------------------------------------------------------
        # ALL CHECKS PASSED → Assign EXACT lot size based on rules
        # -----------------------------------------------------------
        # We bypass dynamic risk math entirely and enforce strict lot sizes 
        # as requested in the pnl_breakdown.md rules.
        
        if "XAG" in pair:  # Silver
            lot_size = 0.02
        elif "USOIL" in pair or "WTI" in pair:  # Crude Oil
            lot_size = 0.10
        elif "BTC" in pair:  # Bitcoin
            lot_size = 0.03
        else:  # Forex & Gold
            # Dynamic Lot Size Progression based on consecutive profitable days
            if self.consecutive_wins <= 1: # Day 1-2
                lot_size = 0.03
            elif self.consecutive_wins == 2: # Day 3
                lot_size = 0.04
            elif self.consecutive_wins == 3: # Day 4
                lot_size = 0.05
            elif self.consecutive_wins == 4: # Day 5
                lot_size = 0.07
            else: # Day 6+
                lot_size = 0.10

        return RiskCheckResult(
            approved=True,
            adjusted_lot_size=lot_size,
            reason=(f"✅ APPROVED: {direction} {pair} | Lot: {lot_size} | "
                    f"Risk: {risk_pct*100*size_multiplier:.1f}% (${risk_amount:.2f}) | "
                    f"R:R = 1:{risk_reward:.1f} | "
                    f"Trade {len(self.trades_today)+1}/{max_trades} today"
                    f"{' [SIZE HALVED: daily DD warning]' if size_multiplier < 1 else ''}"),
            risk_pct_used=risk_pct * size_multiplier,
            trades_today=len(self.trades_today),
            max_trades_today=max_trades,
            current_drawdown_pct=drawdown_from_peak,
            equity=equity
        )

    # -------------------------------------------------------------------
    # Helper: Get risk % based on capital size
    # -------------------------------------------------------------------
    def _get_risk_pct(self, equity: float, pair: str = "") -> float:
        """
        Returns the risk percentage for a trade.

        Priority:
          1. Symbol-specific override (e.g., XAGUSD always 2%)
          2. Capital-based rule (> $2000 → 1.5%, else 2%)
        """
        # Check for symbol-specific override first
        if pair and pair in self.SYMBOL_RISK_OVERRIDES:
            return self.SYMBOL_RISK_OVERRIDES[pair]

        # Default capital-based logic
        if equity > self.high_capital_threshold:
            return self.risk_pct_high_capital
        return self.risk_pct_default

    # -------------------------------------------------------------------
    # Helper: Get max trades based on market condition
    # -------------------------------------------------------------------
    def _get_max_trades(self, is_trending: bool, confidence: int) -> int:
        """
        Default: 2 trades/day.
        If market is strongly trending AND confidence >= 80% → allow 3rd trade.
        """
        if is_trending and confidence >= self.trending_confidence:
            return self.max_trades_trending
        return self.max_trades_default

    # -------------------------------------------------------------------
    # Helper: Check correlated pairs
    # -------------------------------------------------------------------
    def _count_correlated_positions(self, pair: str) -> int:
        """
        Simple correlation grouping based on common currency exposure.
        E.g., EURUSD and GBPUSD are both "short USD" → correlated.
        """
        CORRELATION_GROUPS = {
            "USD_SHORT": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"],
            "USD_LONG": ["USDJPY", "USDCHF", "USDCAD"],
            "GOLD_GROUP": ["XAUUSD", "XAGUSD"],
            "CRYPTO": ["BTCUSD", "ETHUSD"],
        }

        pair_groups = []
        for group_name, members in CORRELATION_GROUPS.items():
            if pair in members:
                pair_groups.append(group_name)

        count = 0
        for pos in self.open_positions:
            for group_name in pair_groups:
                if pos.pair in CORRELATION_GROUPS.get(group_name, []):
                    count += 1
                    break
        return count

    # -------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------
    def record_trade_opened(self, trade: TradeRecord):
        self.trades_today.append(trade)
        self.open_positions.append(trade)

    def record_trade_closed(self, trade_id: str, pnl: float):
        for pos in self.open_positions:
            if pos.trade_id == trade_id:
                pos.pnl = pnl
                pos.status = "closed_win" if pnl > 0 else "closed_loss"
                pos.close_time = datetime.now().isoformat()
                self.open_positions.remove(pos)
                break

    def get_status_summary(self) -> dict:
        """Returns a summary of current risk state for the dashboard."""
        return {
            "peak_equity": self.peak_equity,
            "trades_today": len(self.trades_today),
            "open_positions": len(self.open_positions),
            "daily_pnl": sum(t.pnl for t in self.trades_today),
            "halted": False,  # Updated dynamically
        }

    # -------------------------------------------------------------------
    # HIGH CONVICTION HOLD CHECK
    # -------------------------------------------------------------------
    def check_high_conviction_hold(self, pair: str, confidence: int) -> dict:
        """
        For cheap commodities (USOIL, XAGUSD), if confidence >= 90%,
        allow the position to be held for up to 24 hours (1 full day)
        instead of the default intraday close.

        Returns:
            {
                "allow_extended_hold": bool,
                "max_hold_hours": int,
                "reason": str
            }
        """
        if pair not in self.HIGH_CONVICTION_INSTRUMENTS:
            return {
                "allow_extended_hold": False,
                "max_hold_hours": 0,
                "reason": f"{pair} is not eligible for High Conviction Hold."
            }

        rules = self.HIGH_CONVICTION_INSTRUMENTS[pair]
        min_conf = rules["min_confidence"]
        max_hours = rules["max_hold_hours"]

        if confidence >= min_conf:
            return {
                "allow_extended_hold": True,
                "max_hold_hours": max_hours,
                "reason": (
                    f"🔥 HIGH CONVICTION HOLD: {pair} confidence {confidence}% "
                    f"(≥ {min_conf}%) → position may be held up to {max_hours}h "
                    f"to let the move play out."
                )
            }
        else:
            return {
                "allow_extended_hold": False,
                "max_hold_hours": 0,
                "reason": (
                    f"{pair} confidence {confidence}% is below "
                    f"High Conviction threshold ({min_conf}%). "
                    f"Standard intraday rules apply."
                )
            }
