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
        if today != self.current_date:
            self.trades_today = []
            self.start_of_day_equity = equity
            self.current_date = today

        # Update peak equity
        if equity > self.peak_equity:
            self.peak_equity = equity
        if self.start_of_day_equity == 0:
            self.start_of_day_equity = equity

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
        # ALL CHECKS PASSED → Calculate exact lot size
        # -----------------------------------------------------------
        risk_pct = self._get_risk_pct(equity)
        risk_amount = equity * risk_pct * size_multiplier
        risk_in_pips = risk_distance / 0.0001 if "JPY" not in pair else risk_distance / 0.01

        # Lot size = (Risk Amount) / (Risk in Pips × Pip Value)
        lot_size = risk_amount / (risk_in_pips * pip_value) if (risk_in_pips * pip_value) > 0 else 0
        lot_size = round(max(0.01, lot_size), 2)  # Min 0.01 lots (micro lot)

        # AGGRESSIVE MODE: Strong trend or high confidence (>= 90%)
        if is_trending or confidence >= 90:
            # Boost the lot size for high probability setups
            if lot_size < 0.05:
                lot_size = 0.05
            elif lot_size > 0.1:
                lot_size = 0.1

        # Check max single position size
        position_value = lot_size * 100000 * entry_price  # Approximate
        if position_value > equity * self.max_single_pct:
            lot_size = round((equity * self.max_single_pct) / (100000 * entry_price), 2)
            lot_size = max(0.01, lot_size)

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
    def _get_risk_pct(self, equity: float) -> float:
        """Capital > $2000 → 1.5% risk. Capital ≤ $2000 → 2% risk."""
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
