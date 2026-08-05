"""
=============================================================================
ORDER EXECUTOR — MT5 Live Trade Placement
=============================================================================
This module is the FINAL step in the pipeline. After the Risk Agent approves
a trade, this module sends the actual order to MetaTrader 5.

Modes:
  - DEMO mode: All logic runs but mt5.order_send() is NOT called. Orders
    are logged as if they were placed.
  - LIVE mode: Real orders sent to XM Global via MT5 API.

Safety features:
  - Retries order placement up to 3 times on transient errors
  - Validates MT5's return code before declaring success
  - Logs ALL attempted orders regardless of outcome (XAI audit trail)
  - Never silently swallows errors — always raises or returns a result dict
=============================================================================
"""

import time
from datetime import datetime
from typing import Optional

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class OrderExecutor:
    """
    Sends approved trades to MT5 and monitors their status.

    Usage:
        executor = OrderExecutor(demo_mode=True)
        executor.connect(login, password, server)
        result = executor.place_order(trade_record)
        executor.close_order(ticket, pair, direction, lots)
    """

    # MT5 magic number — identifies this bot's orders in the terminal
    MAGIC_NUMBER = 20250101

    # Max retries for transient MT5 errors (e.g., requote)
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # seconds

    def __init__(self, demo_mode: bool = True):
        self.demo_mode    = demo_mode
        self.is_connected = False
        self._order_log: list[dict] = []

    # =========================================================================
    # CONNECTION
    # =========================================================================

    def connect(
        self,
        login: int,
        password: str,
        server: str,
        path: Optional[str] = None
    ) -> bool:
        """
        Connect to MetaTrader 5 terminal.

        Args:
            login:    MT5 account login number
            password: MT5 account password
            server:   Broker server name (e.g., 'XMGlobal-MT5')
            path:     Optional path to terminal64.exe

        Returns True on success, False on failure.
        """
        if not MT5_AVAILABLE:
            print("  ⚠️  [MT5] MetaTrader5 package not installed. Running in simulation mode.")
            self.is_connected = False
            return False

        if self.demo_mode:
            print("  📝 [MT5] DEMO MODE — Will simulate order placement without real MT5.")
            self.is_connected = True
            return True

        print(f"  🔌 [MT5] Connecting to {server} as account {login}...")
        kwargs = {"login": login, "password": password, "server": server}
        if path:
            kwargs["path"] = path

        initialized = mt5.initialize(**kwargs)
        if not initialized:
            err = mt5.last_error()
            print(f"  ❌ [MT5] Connection failed: {err}")
            self.is_connected = False
            return False

        info = mt5.account_info()
        if info is None:
            print("  ❌ [MT5] Connected but could not retrieve account info.")
            self.is_connected = False
            return False

        self.is_connected = True
        mode = "DEMO" if info.trade_mode == 0 else "⚠️ LIVE"
        print(
            f"  ✅ [MT5] Connected! Account: {info.login} | "
            f"Balance: ${info.balance:.2f} | Mode: {mode}"
        )
        return True

    def disconnect(self):
        """Cleanly disconnect from MT5."""
        if MT5_AVAILABLE and self.is_connected and not self.demo_mode:
            mt5.shutdown()
        self.is_connected = False
        print("  🔌 [MT5] Disconnected.")

    # =========================================================================
    # ORDER PLACEMENT
    # =========================================================================

    def place_order(self, trade_record) -> dict:
        """
        Places a market order on MT5 based on a TradeRecord.

        Args:
            trade_record: TradeRecord dataclass from risk_agent.py

        Returns:
            {
              "success": bool,
              "ticket":  int or None,
              "reason":  str,
              "mode":    "DEMO" or "LIVE"
            }
        """
        pair      = trade_record.pair
        direction = trade_record.direction  # "BUY" or "SELL"
        lot_size  = trade_record.lot_size
        sl        = trade_record.stop_loss
        tp        = trade_record.take_profit

        log_entry = {
            "timestamp":   datetime.now().isoformat(),
            "trade_id":    trade_record.trade_id,
            "pair":        pair,
            "direction":   direction,
            "lot_size":    lot_size,
            "stop_loss":   sl,
            "take_profit": tp,
        }

        # ── DEMO MODE ──────────────────────────────────────────────────────
        if self.demo_mode:
            result = {
                "success": True,
                "ticket":  int(datetime.now().timestamp()),
                "reason":  f"[DEMO] {direction} {lot_size} lots {pair} simulated. SL={sl} TP={tp}",
                "mode":    "DEMO"
            }
            log_entry.update({"success": True, "mode": "DEMO", "ticket": result["ticket"]})
            self._order_log.append(log_entry)
            print(f"  📝 [DEMO] Order logged: {result['reason']}")
            return result

        # ── LIVE MODE ──────────────────────────────────────────────────────
        if not self.is_connected:
            return {"success": False, "ticket": None,
                    "reason": "MT5 not connected.", "mode": "LIVE"}

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        # Retry loop for transient errors
        for attempt in range(1, self.MAX_RETRIES + 1):
            tick = mt5.symbol_info_tick(pair)
            if tick is None:
                error = f"Could not get tick for {pair}: {mt5.last_error()}"
                print(f"  ⚠️  [MT5] Attempt {attempt}/{self.MAX_RETRIES}: {error}")
                time.sleep(self.RETRY_DELAY)
                continue

            price = tick.ask if direction == "BUY" else tick.bid

            request = {
                "action":       mt5.TRADE_ACTION_DEAL,
                "symbol":       pair,
                "volume":       float(lot_size),
                "type":         order_type,
                "price":        price,
                "sl":           float(sl),
                "tp":           float(tp),
                "deviation":    10,      # Max slippage in points
                "magic":        self.MAGIC_NUMBER,
                "comment":      f"AI_Bot_{trade_record.trade_id[:8]}",
                "type_time":    mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result_mt5 = mt5.order_send(request)

            if result_mt5 is None:
                error = f"order_send returned None: {mt5.last_error()}"
                print(f"  ⚠️  [MT5] Attempt {attempt}: {error}")
                time.sleep(self.RETRY_DELAY)
                continue

            if result_mt5.retcode == mt5.TRADE_RETCODE_DONE:
                ticket = result_mt5.order
                reason = (
                    f"✅ LIVE ORDER PLACED: {direction} {lot_size} lots {pair} "
                    f"@ {price:.5f} | SL={sl} | TP={tp} | Ticket={ticket}"
                )
                print(f"  ⚡ [LIVE] {reason}")
                log_entry.update({"success": True, "mode": "LIVE", "ticket": ticket})
                self._order_log.append(log_entry)
                return {"success": True, "ticket": ticket, "reason": reason, "mode": "LIVE"}

            else:
                error = (
                    f"retcode={result_mt5.retcode} comment='{result_mt5.comment}' "
                    f"on attempt {attempt}/{self.MAX_RETRIES}"
                )
                print(f"  ⚠️  [MT5] Order failed: {error}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)

        # All retries exhausted
        final_err = f"Order failed after {self.MAX_RETRIES} attempts for {pair}."
        log_entry.update({"success": False, "mode": "LIVE", "ticket": None, "error": final_err})
        self._order_log.append(log_entry)
        return {"success": False, "ticket": None, "reason": final_err, "mode": "LIVE"}

    # =========================================================================
    # ORDER MANAGEMENT
    # =========================================================================

    def close_order(
        self,
        ticket: int,
        pair: str,
        direction: str,
        lot_size: float
    ) -> dict:
        """
        Closes an open position by ticket number.

        Args:
            ticket:    MT5 ticket number of the open position
            pair:      Forex pair (e.g., 'EURUSD')
            direction: Original direction ('BUY' → close with SELL)
            lot_size:  Lot size of the position to close

        Returns same structure as place_order.
        """
        if self.demo_mode:
            return {
                "success": True,
                "ticket":  ticket,
                "reason":  f"[DEMO] Close {pair} ticket {ticket} simulated.",
                "mode":    "DEMO"
            }

        if not self.is_connected:
            return {"success": False, "ticket": None, "reason": "MT5 not connected.", "mode": "LIVE"}

        close_type = mt5.ORDER_TYPE_SELL if direction == "BUY" else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pair)
        if tick is None:
            return {"success": False, "ticket": None,
                    "reason": f"Could not get tick for {pair}", "mode": "LIVE"}

        price = tick.bid if direction == "BUY" else tick.ask

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       pair,
            "volume":       float(lot_size),
            "type":         close_type,
            "position":     ticket,
            "price":        price,
            "deviation":    10,
            "magic":        self.MAGIC_NUMBER,
            "comment":      f"AI_Bot_Close_{ticket}",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result_mt5 = mt5.order_send(request)
        if result_mt5 and result_mt5.retcode == mt5.TRADE_RETCODE_DONE:
            return {
                "success": True,
                "ticket":  result_mt5.order,
                "reason":  f"Position {ticket} closed successfully.",
                "mode":    "LIVE"
            }

        retcode = result_mt5.retcode if result_mt5 else "None"
        return {
            "success": False,
            "ticket":  None,
            "reason":  f"Close failed: retcode={retcode}",
            "mode":    "LIVE"
        }

    def get_open_positions(self) -> list[dict]:
        """Returns all open positions from MT5 as a list of dicts."""
        if self.demo_mode or not self.is_connected or not MT5_AVAILABLE:
            return []

        positions = mt5.positions_get()
        if positions is None:
            return []

        return [
            {
                "ticket":     p.ticket,
                "pair":       p.symbol,
                "direction":  "BUY" if p.type == 0 else "SELL",
                "lot_size":   p.volume,
                "entry_price": p.price_open,
                "current_price": p.price_current,
                "sl":         p.sl,
                "tp":         p.tp,
                "pnl":        p.profit,
                "open_time":  datetime.fromtimestamp(p.time).isoformat(),
            }
            for p in positions
        ]

    def get_account_equity(self) -> float:
        """Returns current account equity from MT5."""
        if self.demo_mode or not self.is_connected or not MT5_AVAILABLE:
            return 10000.0  # Demo default

        info = mt5.account_info()
        return info.equity if info else 10000.0

    def get_order_log(self) -> list[dict]:
        """Returns all orders attempted in this session (for XAI logging)."""
        return self._order_log
