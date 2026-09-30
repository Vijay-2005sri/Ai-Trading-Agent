"""
=============================================================================
ORDER EXECUTOR — Verified MT5 Demo Trade Placement
=============================================================================
This module is the FINAL step in the pipeline. After the Risk Agent approves
a trade, this module sends the actual order to MetaTrader 5.

Only an explicitly enabled, broker-verified DEMO_MT5 session may send orders.
Live is disabled; paper requires a real adapter and never fakes success.

Safety features:
  - Legacy entry retries (error classification is deferred to task 1.6)
  - Validates MT5's return code before declaring success
  - Records entry outcomes and mode denials (full lifecycle audit is deferred)
  - Never silently swallows errors — always raises or returns a result dict
=============================================================================
"""

import time  # Retained as a patch point for offline legacy retry fixtures.
import math
import re
from datetime import datetime
from typing import Optional

from config.execution_mode import DevelopmentPolicy, ModeError, validate_demo_credentials
from broker_mt5.symbols import SymbolRegistry
from broker_mt5.instruments import InstrumentProvider, InstrumentError
from broker_mt5.execution_gateway import ExecutionGateway
from core.time_service import SystemClock

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class OrderExecutor:
    """
    Sends approved trades to MT5 and monitors their status.

    Usage:
        executor = OrderExecutor(mode="demo_mt5", enable_demo_orders=True)
        executor.connect(login, password, server)
        result = executor.place_order(trade_record)
        executor.close_order(ticket, pair, direction, lots)
    """

    # MT5 magic number — identifies this bot's orders in the terminal
    MAGIC_NUMBER = 20250101

    # Max retries for transient MT5 errors (e.g., requote)
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # seconds

    def __init__(self, demo_mode: Optional[bool] = None, *, mode: Optional[str] = None,
                 enable_demo_orders: bool = False, symbol_registry=None, clock=None,
                 gateway_config=None):
        self._mt5 = mt5
        self.clock = clock or SystemClock()
        self.symbol_registry = symbol_registry or SymbolRegistry()
        broker = {"mode": mode, "enable_demo_orders": enable_demo_orders}
        if demo_mode is not None:
            broker["demo_mode"] = demo_mode
        self._policy = DevelopmentPolicy.from_config({"broker": broker})
        self._policy.require_demo_session()
        self.demo_mode = True  # Compatibility only; never used as send authority.
        self.is_connected = False
        self._expected_identity = None
        self._order_log: list[dict] = []
        self.instruments = InstrumentProvider(
            symbol_registry=self.symbol_registry, account_reader=self.assert_demo_session,
            symbol_reader=lambda symbol: mt5.symbol_info(symbol), clock=self.clock)
        self.execution_gateway = ExecutionGateway(self, config=gateway_config, clock=self.clock)

    def _invalidate_session(self):
        self.instruments.clear()
        if hasattr(self, "execution_gateway"):
            self.execution_gateway.clear()
        self.is_connected = False
        self._expected_identity = None
        if MT5_AVAILABLE:
            try:
                mt5.shutdown()
            except Exception:
                pass  # State is already latched closed even if shutdown fails.

    def assert_demo_session(self):
        """Revalidate native account identity; failure requires explicit reconnect."""
        self._policy.require_demo_session()
        if not MT5_AVAILABLE or not self.is_connected or self._expected_identity is None:
            raise ModeError("No verified demo MT5 session; connect explicitly before use")
        try:
            terminal = mt5.terminal_info()
            info = mt5.account_info()
        except Exception:
            self._invalidate_session()
            raise ModeError("Demo account state unavailable") from None
        if (terminal is None or getattr(terminal, "connected", None) is not True
                or info is None or type(getattr(info, "trade_mode", None)) is not int
                or info.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO
                or type(getattr(info, "login", None)) is not int
                or (info.login, getattr(info, "server", None)) != self._expected_identity):
            self._invalidate_session()
            raise ModeError("Demo account identity unavailable or changed; reconnect required")
        return info

    def _blocked(self, reason):
        result = {"success": False, "ticket": None, "reason": str(reason), "mode": "DEMO_MT5"}
        self._order_log.append({"timestamp": datetime.now().isoformat(), **result})
        return result

    def _send_demo_request(self, request, *, contract_revision=None, gateway_permit=None):
        # The only native submission site, including closes and entry retries.
        # MT5 cannot make this identity check and send an atomic operation.
        self.assert_demo_session()
        if (not hasattr(self, "execution_gateway")
                or not self.execution_gateway.validates_permit(gateway_permit, request)
                and not self.execution_gateway.validates_close_permit(gateway_permit, request)):
            raise InstrumentError("Native order submission requires a gateway-issued permit")
        if "position" not in request and (not isinstance(contract_revision, str)
                or re.fullmatch(r"[0-9a-f]{64}", contract_revision) is None):
            raise InstrumentError("Entry submission requires a construction revision")
        spec = self.instruments.get(request["symbol"], refresh=True)
        if contract_revision is not None and contract_revision != spec.revision:
            raise InstrumentError("Contract metadata changed since trade construction; reanalysis required")
        closing = "position" in request
        if spec.trade_mode == 0 or (not closing and spec.trade_mode == 3):
            raise InstrumentError("Broker trade mode blocks this operation")
        if not closing and ((spec.trade_mode == 1 and request["type"] != mt5.ORDER_TYPE_BUY)
                            or (spec.trade_mode == 2 and request["type"] != mt5.ORDER_TYPE_SELL)):
            raise InstrumentError("Broker trade mode blocks this direction")
        if not spec.order_mode & 1:
            raise InstrumentError("Broker does not permit market orders")
        if request.get("sl") and not spec.order_mode & 16:
            raise InstrumentError("Broker does not permit Stop Loss")
        if request.get("tp") and not spec.order_mode & 32:
            raise InstrumentError("Broker does not permit Take Profit")
        if request.get("type_filling") != mt5.ORDER_FILLING_IOC or (spec.trade_exemode in (2, 3) and not spec.filling_mode & 2):
            raise InstrumentError("Current IOC request is unsupported by broker metadata")
        account = self.assert_demo_session()
        if (getattr(account, "currency", None), getattr(account, "leverage", None), getattr(account, "margin_mode", None)) != (
                spec.account_currency, spec.leverage, spec.margin_mode):
            self.instruments.clear()
            raise InstrumentError("Account metadata context changed before submission")
        self.execution_gateway.final_send_check(gateway_permit, request, spec)
        self._order_log.append({"event": "ContractSpecObserved", "revision": spec.revision,
                                "snapshot": spec.model_dump(mode="json")})
        return mt5.order_send(request)

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
        self.is_connected = False
        self._expected_identity = None
        self.instruments.clear()
        self._policy.require_demo_session()
        validate_demo_credentials(login, password, server, path)
        if not MT5_AVAILABLE:
            return False

        kwargs = {"login": login, "password": password, "server": server}
        if path:
            kwargs["path"] = path

        try:
            initialized = mt5.initialize(**kwargs)
        except Exception:
            self._invalidate_session()
            return False
        if not initialized:
            self._invalidate_session()
            return False
        self._expected_identity = (login, server)
        self.is_connected = True
        try:
            self.assert_demo_session()
        except ModeError:
            return False
        print("  [MT5] Verified demo account connected (DEMO_MT5)")
        return True

    def disconnect(self):
        """Cleanly disconnect from MT5."""
        self._invalidate_session()
        print("  🔌 [MT5] Disconnected.")

    # =========================================================================
    # ORDER PLACEMENT
    # =========================================================================

    def place_order(self, trade_record, *, approval_token=None) -> dict:
        """
        Places a market order on MT5 based on a TradeRecord.

        Args:
            trade_record: TradeRecord dataclass from risk_agent.py

        Returns:
            {
              "success": bool,
              "ticket":  int or None,
              "reason":  str,
              "mode":    "DEMO_MT5"
            }
        """
        try:
            if not approval_token:
                return self._blocked("Entry requires a fresh one-shot gateway approval")
            result = self.execution_gateway.submit_entry(trade_record, approval_token)
            self._order_log.append({"timestamp": self.clock.now_utc().isoformat(),
                                    "trade_id": trade_record.trade_id, **result})
            return result
        except (ModeError, AttributeError, TypeError, ValueError) as error:
            return self._blocked(error)

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
        try:
            result = self.execution_gateway.close_position(ticket, pair, direction, lot_size)
            self._order_log.append({"timestamp": self.clock.now_utc().isoformat(), **result})
            return result
        except (ModeError, AttributeError, TypeError, ValueError) as error:
            return self._blocked(error)

    def bind_risk_agent(self, risk_agent):
        self.execution_gateway.bind_risk_agent(risk_agent)

    def prepare_trade(self, **kwargs):
        return self.execution_gateway.prepare_trade(**kwargs)

    def authorize_trade(self, preparation, record, *, confidence, is_trending=False):
        return self.execution_gateway.authorize_trade(
            preparation, record, confidence=confidence, is_trending=is_trending)

    def get_open_positions(self) -> list[dict]:
        """Returns all open positions from MT5 as a list of dicts."""
        self.assert_demo_session()
        try:
            positions = mt5.positions_get()
        except Exception:
            self._invalidate_session()
            raise ModeError("Demo positions unavailable; reconnect required") from None
        if positions is None:
            self._invalidate_session()
            raise ModeError("Demo positions unavailable; cannot assume an empty portfolio")
        self.assert_demo_session()

        return [
            {
                "ticket":     p.ticket,
                "pair":       self.symbol_registry.from_broker(p.symbol),
                "broker_symbol": p.symbol,
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
        info = self.assert_demo_session()
        equity = getattr(info, "equity", None)
        if type(equity) not in (int, float) or not math.isfinite(equity) or equity < 0:
            self._invalidate_session()
            raise ModeError("Demo equity unavailable or invalid; no synthetic balance fallback")
        return float(equity)

    def get_instrument_spec(self, symbol):
        return self.instruments.get(symbol, refresh=True)

    def get_order_log(self) -> list[dict]:
        """Returns all orders attempted in this session (for XAI logging)."""
        return self._order_log
