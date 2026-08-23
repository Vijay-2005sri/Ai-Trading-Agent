"""
=============================================================================
MT5 DATA FETCHER — Self-Healing & Auto-Launch
=============================================================================
Features:
  - Auto-detects if MetaTrader 5 terminal is running (process check)
  - Auto-launches terminal64.exe if not running
  - Waits for full terminal initialization (IPC server ready)
  - Auto-reconnects with exponential backoff on IPC drops
  - symbol_select(symbol, True) before every data fetch
  - Thread-safe reconnection with circuit breaker (no reconnection storm)
=============================================================================
"""

import os
import sys

# Force UTF-8 encoding on Windows to prevent emoji crashes (cp1252 can't handle them)
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

import MetaTrader5 as mt5
import pandas as pd
import subprocess
import time
import threading
from datetime import datetime
from pathlib import Path


class MT5DataFetcher:
    """
    Self-healing MT5 data fetcher.

    Automatically launches, connects, reconnects, and selects symbols.
    Designed to run 24/7 without manual intervention.
    """

    # ── Configuration ────────────────────────────────────────────────────────
    MAX_CONNECT_RETRIES = 3          # Max attempts per connect() call
    MAX_LAUNCH_WAIT_SECONDS = 45     # Max wait after launching terminal
    LAUNCH_POLL_INTERVAL = 3         # Seconds between init polls after launch
    IPC_READY_WAIT = 10              # Extra seconds after process detected for IPC server to start
    BACKOFF_BASE = 2.0               # Exponential backoff base (seconds)
    BACKOFF_MAX = 60.0               # Maximum backoff delay (seconds)
    MAX_RECONNECT_ATTEMPTS = 5       # Max reconnection attempts before giving up
    CIRCUIT_BREAKER_COOLDOWN = 120   # Seconds to wait before allowing another reconnect cycle

    # Common MT5 terminal paths (Windows)
    DEFAULT_TERMINAL_PATHS = [
        r"C:\Program Files\XM MT5\terminal64.exe",
        r"C:\Program Files\XM Global MT5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    ]

    def __init__(self, login, password, server, path=None):
        self.login = login
        self.password = password
        self.server = server
        self.path = path  # Path to terminal64.exe (from .env or auto-detected)
        self._reconnect_lock = threading.Lock()
        self._selected_symbols = set()  # Track which symbols have been selected
        self._consecutive_failures = 0  # Track failures for backoff
        self._last_reconnect_time = 0   # Timestamp of last reconnect attempt (circuit breaker)
        self._connection_alive = False  # Track if we have a working connection

    # =========================================================================
    # PROCESS DETECTION
    # =========================================================================

    def _is_mt5_running(self) -> bool:
        """
        Check if any MetaTrader 5 terminal process is currently running.
        Uses tasklist on Windows to check for terminal64.exe.
        """
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq terminal64.exe"],
                capture_output=True, text=True, timeout=5
            )
            return "terminal64.exe" in result.stdout.lower()
        except Exception:
            # If we can't check, assume it might be running and try to connect
            return True

    # =========================================================================
    # AUTO-LAUNCH
    # =========================================================================

    def _find_terminal_path(self) -> str | None:
        """
        Find the path to terminal64.exe.
        Priority: self.path (from .env) → common default paths.
        """
        # Check user-specified path first
        if self.path and Path(self.path).exists():
            return self.path

        # Search common installation directories
        for candidate in self.DEFAULT_TERMINAL_PATHS:
            if Path(candidate).exists():
                print(f"    🔍 Found MT5 terminal at: {candidate}")
                return candidate

        return None

    def _auto_launch_terminal(self) -> bool:
        """
        Launch MetaTrader 5 terminal if it's not running.

        Returns True if terminal was launched (or was already running).
        Returns False if terminal could not be found or launched.
        """
        if self._is_mt5_running():
            print("    ✅ MT5 terminal is already running.")
            return True

        terminal_path = self._find_terminal_path()
        if not terminal_path:
            print(
                "    ❌ MT5 terminal NOT found! Searched:\n"
                f"       • .env MT5_PATH: {self.path or '(not set)'}\n"
                "       • C:\\Program Files\\XM MT5\\terminal64.exe\n"
                "       • C:\\Program Files\\MetaTrader 5\\terminal64.exe\n"
                "\n"
                "    💡 FIX: Set MT5_PATH in your .env file to the correct path:\n"
                '       MT5_PATH="C:\\Path\\To\\Your\\terminal64.exe"'
            )
            return False

        print(f"    🚀 Launching MT5 terminal: {terminal_path}")
        try:
            # Launch in background — don't wait for it to finish
            subprocess.Popen(
                [terminal_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"    ❌ Failed to launch MT5: {e}")
            return False

        # Wait for the terminal to become ready
        print(f"    ⏳ Waiting up to {self.MAX_LAUNCH_WAIT_SECONDS}s for MT5 to start...")
        waited = 0
        while waited < self.MAX_LAUNCH_WAIT_SECONDS:
            time.sleep(self.LAUNCH_POLL_INTERVAL)
            waited += self.LAUNCH_POLL_INTERVAL

            if self._is_mt5_running():
                print(f"    ✅ MT5 process detected after {waited}s.")
                # Give the terminal plenty of time to fully initialize:
                # - Load UI
                # - Connect to broker server
                # - Authenticate
                # - Start IPC server for API connections
                print(f"    ⏳ Waiting {self.IPC_READY_WAIT}s for MT5 IPC server to become ready...")
                time.sleep(self.IPC_READY_WAIT)
                return True

        print(f"    ⚠️ MT5 process not detected after {self.MAX_LAUNCH_WAIT_SECONDS}s.")
        return False

    # =========================================================================
    # CONNECTION (with auto-launch + retry)
    # =========================================================================

    def connect(self) -> bool:
        """
        Initialize MT5 connection with auto-launch and retry logic.

        Key insight: mt5.initialize(path=...) tries to CREATE/LAUNCH a new
        terminal process at that path. If the terminal is already running,
        we should call mt5.initialize() WITHOUT the path parameter — this
        connects to the already-running terminal via IPC.

        We only pass `path` on the FIRST attempt if the terminal isn't running.
        On retries (terminal already running), we omit `path` to avoid the
        "Process create failed" error.

        Returns True on success, False on failure.
        """
        # Step 1: Ensure MT5 terminal is running
        was_already_running = self._is_mt5_running()
        if not was_already_running:
            if not self._auto_launch_terminal():
                print("    ❌ Cannot connect — MT5 terminal is not running and could not be launched.")
                return False

        # Step 2: Try to initialize with retries
        for attempt in range(1, self.MAX_CONNECT_RETRIES + 1):
            print(f"    🔌 MT5 connect attempt {attempt}/{self.MAX_CONNECT_RETRIES} "
                  f"→ {self.login}@{self.server}")

            # Strategy for the path parameter:
            # - If terminal was NOT running and this is attempt 1: pass path 
            #   (mt5.initialize will launch + connect)
            # - If terminal IS already running: do NOT pass path
            #   (just connect to the existing process via IPC)
            use_path = (not was_already_running and attempt == 1)

            kwargs = {
                "login": self.login,
                "password": self.password,
                "server": self.server
            }
            if use_path and self.path:
                kwargs["path"] = self.path

            try:
                # Shutdown any previous broken connection before retrying
                if attempt > 1:
                    try:
                        mt5.shutdown()
                    except Exception:
                        pass
                    time.sleep(1)

                initialized = mt5.initialize(**kwargs)
            except Exception as e:
                print(f"    ⚠️ mt5.initialize() threw exception: {e}")
                initialized = False

            if initialized:
                self._consecutive_failures = 0
                self._connection_alive = True
                self._selected_symbols.clear()  # Re-select symbols after reconnect
                print(f"    ✅ MT5 connected successfully on attempt {attempt}.")
                return True

            error = mt5.last_error()
            print(f"    ⚠️ Attempt {attempt} failed: {error}")

            if attempt < self.MAX_CONNECT_RETRIES:
                wait = min(self.BACKOFF_BASE ** attempt, self.BACKOFF_MAX)
                print(f"    ⏳ Retrying in {wait:.0f}s...")
                time.sleep(wait)

        # All retries exhausted
        self._consecutive_failures += 1
        self._connection_alive = False
        print(
            f"    ❌ MT5 connection FAILED after {self.MAX_CONNECT_RETRIES} attempts.\n"
            "    💡 Troubleshooting:\n"
            "       1. Is MetaTrader 5 terminal open AND logged in to your account?\n"
            "       2. Is your internet connection active?\n"
            "       3. Are MT5_LOGIN, MT5_PASSWORD, MT5_SERVER correct in .env?\n"
            "       4. Is 'Algo Trading' enabled in MT5? (Tools → Options → Expert Advisors)\n"
            "       5. Try closing ALL MetaTrader terminals and let the bot re-launch the correct one."
        )
        return False

    # =========================================================================
    # RECONNECTION WITH EXPONENTIAL BACKOFF + CIRCUIT BREAKER
    # =========================================================================

    def _reconnect_with_backoff(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.
        Thread-safe — only one thread can attempt reconnection at a time.

        CIRCUIT BREAKER: If a reconnection cycle already happened recently
        (within CIRCUIT_BREAKER_COOLDOWN seconds), skip immediately to prevent
        a reconnection storm where 9 symbol threads each trigger 5-attempt cycles.

        Backoff schedule: 2s → 4s → 8s → 16s → 32s (capped at 60s)
        """
        now = time.time()

        # ── Circuit Breaker ─────────────────────────────────────────────
        # If we recently completed a full reconnection cycle (success or fail),
        # don't try again — prevents 9 threads × 5 attempts × 3 retries = storm
        if (now - self._last_reconnect_time) < self.CIRCUIT_BREAKER_COOLDOWN:
            if self._connection_alive:
                return True  # Recent reconnect succeeded
            else:
                print(f"    ⏸️ Circuit breaker active — last reconnect was "
                      f"{int(now - self._last_reconnect_time)}s ago. "
                      f"Waiting {self.CIRCUIT_BREAKER_COOLDOWN}s cooldown.")
                return False  # Recent reconnect failed, don't spam

        # Prevent multiple threads from reconnecting simultaneously
        if not self._reconnect_lock.acquire(blocking=False):
            # Another thread is already reconnecting — wait for it
            print("    🔄 Another thread is reconnecting. Waiting...")
            with self._reconnect_lock:
                # By the time we get the lock, reconnection should be done
                return self._connection_alive

        try:
            print("    🔄 Starting reconnection with exponential backoff...")
            self._last_reconnect_time = now

            for attempt in range(1, self.MAX_RECONNECT_ATTEMPTS + 1):
                backoff_delay = min(
                    self.BACKOFF_BASE ** attempt,
                    self.BACKOFF_MAX
                )
                print(f"    🔄 Reconnect attempt {attempt}/{self.MAX_RECONNECT_ATTEMPTS} "
                      f"(backoff: {backoff_delay:.0f}s)")

                # Shutdown existing broken connection
                try:
                    mt5.shutdown()
                except Exception:
                    pass

                time.sleep(backoff_delay)

                if self.connect():
                    print(f"    ✅ Reconnected on attempt {attempt}!")
                    self._last_reconnect_time = time.time()
                    return True

            print(f"    ❌ All {self.MAX_RECONNECT_ATTEMPTS} reconnection attempts failed.")
            print(f"    ⏸️ Circuit breaker engaged — no retries for {self.CIRCUIT_BREAKER_COOLDOWN}s.")
            self._last_reconnect_time = time.time()
            return False

        finally:
            self._reconnect_lock.release()

    # =========================================================================
    # SYMBOL SELECTION
    # =========================================================================

    def ensure_symbol_selected(self, symbol: str) -> bool:
        """
        Ensure a symbol is visible in Market Watch via symbol_select().

        MT5 requires symbols to be selected (visible) before you can
        fetch data for them. This is a common cause of "no data" errors.
        """
        if symbol in self._selected_symbols:
            return True  # Already selected this session

        if not self._connection_alive:
            return False  # No point trying if we know connection is down

        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                # Symbol doesn't exist on this broker
                print(f"    ⚠️ Symbol '{symbol}' not found on broker {self.server}.")
                return False

            if not info.visible:
                # Symbol exists but is not in Market Watch — select it
                if not mt5.symbol_select(symbol, True):
                    print(f"    ⚠️ Failed to select '{symbol}' in Market Watch.")
                    return False
                print(f"    📊 Selected '{symbol}' in Market Watch.")

            self._selected_symbols.add(symbol)
            return True

        except Exception as e:
            print(f"    ⚠️ Error selecting symbol '{symbol}': {e}")
            return False

    # =========================================================================
    # DATA FETCHING (with self-healing)
    # =========================================================================

    def get_historical_data(self, symbol, timeframe, count=500):
        """
        Fetches historical OHLCV data with full self-healing.

        Flow:
          1. If connection is known dead → quick reconnect check → skip if still dead
          2. Ensure symbol is selected in Market Watch
          3. Fetch data
          4. If fails → reconnect with backoff → retry
          5. Returns DataFrame or None
        """
        # Quick bail-out if connection is known dead and circuit breaker is active
        if not self._connection_alive:
            if not self._reconnect_with_backoff():
                return None

        # Ensure symbol is in Market Watch
        if not self.ensure_symbol_selected(symbol):
            # Symbol doesn't exist — no point retrying
            return None

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)

        if rates is not None and len(rates) > 0:
            self._consecutive_failures = 0
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            return df

        # ── Data fetch failed — attempt self-healing ────────────────────
        print(f"    ⚠️ No data for {symbol}. Attempting self-healing...")
        self._connection_alive = False  # Mark as dead

        if self._reconnect_with_backoff():
            # Re-select symbol after reconnect
            self.ensure_symbol_selected(symbol)
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)

            if rates is not None and len(rates) > 0:
                print(f"    ✅ Self-healing successful for {symbol}!")
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                return df

        print(f"    ❌ Failed to get data for {symbol} after self-healing. "
              f"Error: {mt5.last_error()}")
        return None

    def get_live_tick(self, symbol):
        """
        Gets the most recent tick (bid/ask) with self-healing.

        Flow:
          1. If connection is known dead → quick reconnect check → skip if still dead
          2. Ensure symbol is selected
          3. Fetch tick
          4. If fails → reconnect with backoff → retry
          5. Returns dict or None
        """
        # Quick bail-out if connection is known dead and circuit breaker is active
        if not self._connection_alive:
            if not self._reconnect_with_backoff():
                return None

        # Ensure symbol is in Market Watch
        if not self.ensure_symbol_selected(symbol):
            return None

        tick = mt5.symbol_info_tick(symbol)

        if tick is not None:
            self._consecutive_failures = 0
            return {
                'bid': tick.bid,
                'ask': tick.ask,
                'time': pd.to_datetime(tick.time, unit='s')
            }

        # ── Tick fetch failed — attempt self-healing ────────────────────
        print(f"    ⚠️ No tick for {symbol}. Attempting self-healing...")
        self._connection_alive = False

        if self._reconnect_with_backoff():
            self.ensure_symbol_selected(symbol)
            tick = mt5.symbol_info_tick(symbol)

            if tick is not None:
                print(f"    ✅ Self-healing successful for {symbol} tick!")
                return {
                    'bid': tick.bid,
                    'ask': tick.ask,
                    'time': pd.to_datetime(tick.time, unit='s')
                }

        print(f"    ❌ Failed to get tick for {symbol} after self-healing.")
        return None

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    def health_check(self, symbols: list[str]) -> dict:
        """
        Comprehensive health check. Used at startup and periodically.

        Returns:
          {
            "connected": bool,
            "terminal_running": bool,
            "algo_trading_enabled": bool,
            "account_info": {...} or None,
            "symbols_status": {"EURUSD": True, "XAUUSD": False, ...},
            "issues": ["list of problems found"]
          }
        """
        result = {
            "connected": False,
            "terminal_running": False,
            "algo_trading_enabled": False,
            "account_info": None,
            "symbols_status": {},
            "issues": []
        }

        # Check 1: Is MT5 process running?
        result["terminal_running"] = self._is_mt5_running()
        if not result["terminal_running"]:
            result["issues"].append(
                "MT5 terminal is NOT running. "
                "FIX: Open MetaTrader 5 and log in, or set MT5_PATH in .env for auto-launch."
            )
            return result

        # Check 2: Can we connect?
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                result["issues"].append(
                    "MT5 terminal is running but IPC connection failed. "
                    "FIX: Restart MetaTrader 5 terminal."
                )
                return result
            result["connected"] = True
        except Exception as e:
            result["issues"].append(f"MT5 terminal_info() error: {e}")
            return result

        # Check 3: Algo trading enabled?
        try:
            result["algo_trading_enabled"] = terminal_info.trade_allowed
            if not terminal_info.trade_allowed:
                result["issues"].append(
                    "Algo Trading is DISABLED in MT5. "
                    "FIX: Go to Tools → Options → Expert Advisors → Enable 'Allow algorithmic trading'."
                )
        except Exception:
            result["issues"].append("Could not check algo trading status.")

        # Check 4: Account info
        try:
            account = mt5.account_info()
            if account:
                result["account_info"] = {
                    "login": account.login,
                    "balance": account.balance,
                    "equity": account.equity,
                    "trade_mode": "DEMO" if account.trade_mode == 0 else "LIVE",
                }
            else:
                result["issues"].append(
                    "Could not retrieve account info. "
                    "FIX: Ensure you are logged into your MT5 account."
                )
        except Exception as e:
            result["issues"].append(f"Account info error: {e}")

        # Check 5: Symbol availability
        for symbol in symbols:
            selected = self.ensure_symbol_selected(symbol)
            result["symbols_status"][symbol] = selected
            if not selected:
                result["issues"].append(
                    f"Symbol '{symbol}' is NOT available on {self.server}. "
                    f"FIX: Remove it from config/settings.yaml or add it in MT5 Market Watch."
                )

        return result

    # =========================================================================
    # DISCONNECT
    # =========================================================================

    def disconnect(self):
        """Cleanly shutdown the MT5 connection."""
        try:
            mt5.shutdown()
        except Exception:
            pass
        self._selected_symbols.clear()
        self._connection_alive = False


if __name__ == "__main__":
    # Test script functionality
    pass
