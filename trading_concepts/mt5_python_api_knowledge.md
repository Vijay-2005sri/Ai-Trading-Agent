# MetaTrader 5 Python API — Complete Knowledge Base
## For AI Trading Agent Brain Context

---

## 1. WHAT IS THE MT5 PYTHON API?

The MetaTrader 5 Python package (`MetaTrader5`) is an **IPC bridge** between Python and the MetaTrader 5 desktop terminal. It does NOT connect directly to broker servers. Instead:

```
Python Script → IPC (Inter-Process Communication) → MT5 Desktop Terminal → Broker Server
```

**CRITICAL RULES:**
- The MT5 desktop terminal MUST be installed and RUNNING on the same Windows machine
- The terminal MUST be logged into a trading account
- Only ONE Python connection per terminal instance is supported
- The "Algo Trading" button in MT5 toolbar MUST be toggled ON (green)
- Python 64-bit is required to match the 64-bit terminal

---

## 2. PREREQUISITES CHECKLIST

Before the trading bot can operate, ALL of these must be true:

| Requirement | How to Verify |
|:---|:---|
| MT5 terminal installed | `terminal64.exe` exists at the configured path |
| MT5 terminal is RUNNING | Process `terminal64.exe` is in Windows Task Manager |
| Logged into account | MT5 shows account number in bottom-left |
| Algo Trading ON | Green "Algo Trading" button in MT5 toolbar |
| Symbols visible | Required symbols (EURUSD, XAUUSD, etc.) in Market Watch |
| Internet connected | MT5 shows "Connected" in bottom-right status bar |
| Python package installed | `pip install MetaTrader5` |
| 64-bit Python | Must match 64-bit terminal |

---

## 3. INITIALIZATION & CONNECTION

### 3.1 Basic Initialization (Terminal Already Running)
```python
import MetaTrader5 as mt5

if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()
```

### 3.2 Initialization with Credentials (Launch Terminal)
```python
# This can auto-launch the terminal if it's not running
if not mt5.initialize(
    path="C:/Program Files/MetaTrader 5/terminal64.exe",
    login=12345678,
    password="your_password",
    server="XMGlobal-MT5 9"
):
    print("initialize() failed, error code =", mt5.last_error())
    quit()
```

### 3.3 Login to Different Account (After Initialize)
```python
authorized = mt5.login(
    login=12345678,
    password="your_password",
    server="XMGlobal-MT5 9"
)
if not authorized:
    print("login failed, error code =", mt5.last_error())
```

### 3.4 Path Formatting Rules (Windows)
- Use FORWARD SLASHES: `"C:/Program Files/MetaTrader 5/terminal64.exe"` ✅
- Backslashes can cause issues: `"C:\\Program Files\\MetaTrader 5\\terminal64.exe"` ⚠️
- Must point to `terminal64.exe`, NOT just the directory

### 3.5 Shutdown (Always Call When Done)
```python
mt5.shutdown()
```

---

## 4. TERMINAL & ACCOUNT INFO

### 4.1 Terminal Status
```python
info = mt5.terminal_info()
# Returns namedtuple with fields:
#   community_account, community_connection, connected, dlls_allowed,
#   trade_allowed, tradeapi_disabled, email_enabled, ftp_enabled,
#   notifications_enabled, mqid, build, maxbars, codepage,
#   ping_last, community_balance, retransmission, name, company,
#   path, data_path, commondata_path
```

### 4.2 Account Info
```python
info = mt5.account_info()
# Key fields:
#   login      — Account number
#   balance    — Current balance
#   equity     — Current equity (balance + floating P/L)
#   margin     — Used margin
#   margin_free — Available margin
#   leverage   — Account leverage (e.g., 500)
#   currency   — Account currency (e.g., "USD")
#   trade_mode — 0 = DEMO, 2 = REAL

# Convert to dict:
info_dict = info._asdict()
```

### 4.3 MT5 Version
```python
version = mt5.version()
# Returns tuple: (terminal_version, build, build_date)
# Example: (500, 3950, '25 Jun 2026')
```

---

## 5. SYMBOL MANAGEMENT

### 5.1 Select a Symbol (Add to Market Watch)
```python
# MUST select a symbol before requesting data or placing orders
selected = mt5.symbol_select("EURUSD", True)  # True = add, False = remove
if not selected:
    print(f"Failed to select EURUSD: {mt5.last_error()}")
```

### 5.2 Get Symbol Details
```python
info = mt5.symbol_info("EURUSD")
# Key fields:
#   visible        — Is symbol in Market Watch?
#   trade_mode     — 0=disabled, 4=full trading
#   point          — Smallest price change (e.g., 0.00001 for EURUSD)
#   digits         — Decimal places (e.g., 5 for EURUSD)
#   spread         — Current spread in points
#   volume_min     — Minimum trade volume (e.g., 0.01)
#   volume_max     — Maximum trade volume
#   volume_step    — Volume increment (e.g., 0.01)
#   trade_stops_level — Minimum SL/TP distance in points
#   filling_mode   — Supported fill types (bitmask)
```

### 5.3 Get Current Tick (Bid/Ask)
```python
tick = mt5.symbol_info_tick("EURUSD")
# Fields: time, bid, ask, last, volume, time_msc, flags, volume_real
```

### 5.4 List All Available Symbols
```python
symbols = mt5.symbols_get()
# Returns tuple of SymbolInfo named tuples

# Filter by pattern:
usd_symbols = mt5.symbols_get(group="*USD*")
```

---

## 6. HISTORICAL DATA RETRIEVAL

### 6.1 Timeframe Constants
| Constant | Description |
|:---|:---|
| `mt5.TIMEFRAME_M1` | 1 minute |
| `mt5.TIMEFRAME_M2` | 2 minutes |
| `mt5.TIMEFRAME_M3` | 3 minutes |
| `mt5.TIMEFRAME_M4` | 4 minutes |
| `mt5.TIMEFRAME_M5` | 5 minutes |
| `mt5.TIMEFRAME_M6` | 6 minutes |
| `mt5.TIMEFRAME_M10` | 10 minutes |
| `mt5.TIMEFRAME_M12` | 12 minutes |
| `mt5.TIMEFRAME_M15` | 15 minutes |
| `mt5.TIMEFRAME_M20` | 20 minutes |
| `mt5.TIMEFRAME_M30` | 30 minutes |
| `mt5.TIMEFRAME_H1` | 1 hour |
| `mt5.TIMEFRAME_H2` | 2 hours |
| `mt5.TIMEFRAME_H3` | 3 hours |
| `mt5.TIMEFRAME_H4` | 4 hours |
| `mt5.TIMEFRAME_H6` | 6 hours |
| `mt5.TIMEFRAME_H8` | 8 hours |
| `mt5.TIMEFRAME_H12` | 12 hours |
| `mt5.TIMEFRAME_D1` | 1 day |
| `mt5.TIMEFRAME_W1` | 1 week |
| `mt5.TIMEFRAME_MN1` | 1 month |

### 6.2 Get Bars by Position (Most Common)
```python
# Get last 200 H1 bars (index 0 = current bar)
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 200)
# Returns numpy array with columns: time, open, high, low, close, tick_volume, spread, real_volume

# Convert to DataFrame:
import pandas as pd
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
```

### 6.3 Get Bars by Date
```python
from datetime import datetime

rates = mt5.copy_rates_from("EURUSD", mt5.TIMEFRAME_H4, datetime(2026, 8, 1), 500)
```

### 6.4 Get Bars by Date Range
```python
rates = mt5.copy_rates_range(
    "EURUSD", mt5.TIMEFRAME_H1,
    datetime(2026, 8, 1), datetime(2026, 8, 20)
)
```

### 6.5 Get Ticks
```python
# From a specific date, get 1000 ticks
ticks = mt5.copy_ticks_from("EURUSD", datetime(2026, 8, 20, 13), 1000, mt5.COPY_TICKS_ALL)

# By date range
ticks = mt5.copy_ticks_range("EURUSD", datetime(2026, 8, 19), datetime(2026, 8, 20), mt5.COPY_TICKS_ALL)
```

### 6.6 Data Availability Rules
- Data only exists if loaded in the MT5 terminal's history
- Increase "Max bars in chart" in Tools → Options → Charts for more history
- Opening the symbol's chart in MT5 forces data synchronization
- Weekend/holiday data gaps are normal (markets closed)

---

## 7. ORDER PLACEMENT

### 7.1 Market Order (BUY)
```python
tick = mt5.symbol_info_tick("EURUSD")
request = {
    "action":       mt5.TRADE_ACTION_DEAL,
    "symbol":       "EURUSD",
    "volume":       0.1,
    "type":         mt5.ORDER_TYPE_BUY,
    "price":        tick.ask,
    "sl":           1.05000,    # Absolute price, NOT points
    "tp":           1.10000,    # Absolute price, NOT points
    "deviation":    10,          # Max slippage in points
    "magic":        123456,      # Unique identifier for this bot
    "comment":      "AI Trade",
    "type_time":    mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}

result = mt5.order_send(request)
if result.retcode == mt5.TRADE_RETCODE_DONE:
    print(f"Order placed! Ticket: {result.order}")
else:
    print(f"Order failed: retcode={result.retcode}, comment={result.comment}")
```

### 7.2 Market Order (SELL)
```python
tick = mt5.symbol_info_tick("EURUSD")
request = {
    "action":       mt5.TRADE_ACTION_DEAL,
    "symbol":       "EURUSD",
    "volume":       0.1,
    "type":         mt5.ORDER_TYPE_SELL,
    "price":        tick.bid,
    "sl":           1.10000,
    "tp":           1.05000,
    "deviation":    10,
    "magic":        123456,
    "comment":      "AI Trade",
    "type_time":    mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}
result = mt5.order_send(request)
```

### 7.3 Pre-validate Order (Dry Run)
```python
check = mt5.order_check(request)
if check.retcode == 0:
    print("Order check passed")
else:
    print(f"Order check failed: {check.comment}")
```

### 7.4 Order Types
| Constant | Description |
|:---|:---|
| `mt5.ORDER_TYPE_BUY` | Market buy |
| `mt5.ORDER_TYPE_SELL` | Market sell |
| `mt5.ORDER_TYPE_BUY_LIMIT` | Pending buy at lower price |
| `mt5.ORDER_TYPE_SELL_LIMIT` | Pending sell at higher price |
| `mt5.ORDER_TYPE_BUY_STOP` | Pending buy at higher price |
| `mt5.ORDER_TYPE_SELL_STOP` | Pending sell at lower price |
| `mt5.ORDER_TYPE_BUY_STOP_LIMIT` | Buy stop limit |
| `mt5.ORDER_TYPE_SELL_STOP_LIMIT` | Sell stop limit |

### 7.5 Trade Actions
| Constant | Description |
|:---|:---|
| `mt5.TRADE_ACTION_DEAL` | Place market order or close position |
| `mt5.TRADE_ACTION_PENDING` | Place pending order |
| `mt5.TRADE_ACTION_SLTP` | Modify SL/TP of open position |
| `mt5.TRADE_ACTION_MODIFY` | Modify pending order |
| `mt5.TRADE_ACTION_REMOVE` | Delete pending order |

### 7.6 Filling Modes
| Constant | Description |
|:---|:---|
| `mt5.ORDER_FILLING_FOK` | Fill or Kill — must fill 100% or cancel |
| `mt5.ORDER_FILLING_IOC` | Immediate or Cancel — partial fill OK, rest cancelled |
| `mt5.ORDER_FILLING_RETURN` | Partial fill, remainder stays active |
| `mt5.ORDER_FILLING_BOC` | Book or Cancel — passive only |

**IMPORTANT:** Not all brokers support all fill types. Check `symbol_info(symbol).filling_mode` bitmask.

---

## 8. POSITION MANAGEMENT

### 8.1 Get All Open Positions
```python
positions = mt5.positions_get()
if positions:
    for pos in positions:
        print(f"Ticket: {pos.ticket}, Symbol: {pos.symbol}, "
              f"Type: {'BUY' if pos.type == 0 else 'SELL'}, "
              f"Volume: {pos.volume}, Profit: {pos.profit}")
```

### 8.2 Get Positions for Specific Symbol
```python
positions = mt5.positions_get(symbol="EURUSD")
```

### 8.3 Close a Position
```python
def close_position(position):
    tick = mt5.symbol_info_tick(position.symbol)
    
    if position.type == mt5.POSITION_TYPE_BUY:
        price = tick.bid
        order_type = mt5.ORDER_TYPE_SELL
    else:
        price = tick.ask
        order_type = mt5.ORDER_TYPE_BUY
    
    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       position.symbol,
        "volume":       position.volume,
        "type":         order_type,
        "position":     position.ticket,   # MUST include ticket
        "price":        price,
        "deviation":    20,
        "magic":        position.magic,
        "comment":      "Close position",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return mt5.order_send(request)
```

### 8.4 Modify SL/TP of Open Position
```python
request = {
    "action":   mt5.TRADE_ACTION_SLTP,
    "symbol":   "EURUSD",
    "position": ticket_number,
    "sl":       new_sl_price,
    "tp":       new_tp_price,
}
result = mt5.order_send(request)
```

---

## 9. ORDER & DEAL HISTORY

### 9.1 Get Historical Orders
```python
from datetime import datetime, timedelta

orders = mt5.history_orders_get(
    datetime.now() - timedelta(days=7),
    datetime.now()
)
```

### 9.2 Get Historical Deals (Executed Trades)
```python
deals = mt5.history_deals_get(
    datetime.now() - timedelta(days=30),
    datetime.now()
)
```

### 9.3 Margin & Profit Calculation
```python
margin = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, "EURUSD", 0.1, 1.08000)
profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, "EURUSD", 0.1, 1.08000, 1.09000)
```

---

## 10. ERROR CODES & TROUBLESHOOTING

### 10.1 Internal Error Codes (from `mt5.last_error()`)
| Code | Constant | Description |
|:---|:---|:---|
| 1 | `RES_S_OK` | Success |
| -1 | `RES_E_FAIL` | Generic failure |
| -2 | `RES_E_INVALID_PARAMS` | Invalid parameters |
| -3 | `RES_E_NO_MEMORY` | Out of memory |
| -4 | `RES_E_NOT_FOUND` | No data found |
| -6 | `RES_E_AUTH_FAILED` | Login/password incorrect |
| -8 | `RES_E_AUTO_TRADING_DISABLED` | Algo Trading is OFF in terminal |
| -10000 | `RES_E_INTERNAL_FAIL` | Internal IPC error |
| -10003 | — | IPC initialize failed / process create failed |
| -10004 | — | No IPC connection |
| -10005 | `RES_E_INTERNAL_FAIL_TIMEOUT` | IPC timeout |

### 10.2 Trade Return Codes (from `order_send().retcode`)
| Code | Constant | Description |
|:---|:---|:---|
| 10009 | `TRADE_RETCODE_DONE` | Order executed successfully |
| 10008 | `TRADE_RETCODE_PLACED` | Order placed (pending) |
| 10010 | `TRADE_RETCODE_DONE_PARTIAL` | Partially filled |
| 10006 | `TRADE_RETCODE_REJECT` | Request rejected |
| 10013 | `TRADE_RETCODE_INVALID` | Invalid request |
| 10014 | `TRADE_RETCODE_INVALID_VOLUME` | Invalid volume |
| 10015 | `TRADE_RETCODE_INVALID_PRICE` | Invalid price |
| 10016 | `TRADE_RETCODE_INVALID_STOPS` | Invalid SL/TP (too close) |
| 10017 | `TRADE_RETCODE_TRADE_DISABLED` | Trading disabled |
| 10018 | `TRADE_RETCODE_MARKET_CLOSED` | Market is closed |
| 10019 | `TRADE_RETCODE_NO_MONEY` | Insufficient funds |
| 10021 | `TRADE_RETCODE_PRICE_OFF` | Price changed (requote) |
| 10024 | `TRADE_RETCODE_TOO_MANY_REQUESTS` | Too many requests |

### 10.3 Common Error Scenarios & Fixes

#### Error: `-10003` "IPC initialize failed, Process create failed"
**Cause:** MT5 terminal is not running or wrong path.
**Fix:**
1. Open MetaTrader 5 manually
2. Log into your account
3. Verify the `.exe` path is correct
4. Run both Python and MT5 with same privilege level (both admin or both normal)

#### Error: `-10004` "No IPC connection"
**Cause:** Terminal crashed or was closed mid-session.
**Fix:**
1. Restart MT5 terminal
2. Call `mt5.shutdown()` then `mt5.initialize()` again

#### Error: `-10005` "IPC timeout"
**Cause:** Terminal is busy, frozen, or blocked.
**Fix:**
1. Wait and retry (terminal may be loading data)
2. Ensure MT5 is not showing a modal dialog
3. Check internet connection

#### Error: `-6` "Authorization failed"
**Cause:** Wrong login, password, or server.
**Fix:** Verify credentials match exactly what's in MT5 terminal

#### Error: `10016` "Invalid stops"
**Cause:** SL/TP price is too close to current market price.
**Fix:** Check `symbol_info(symbol).trade_stops_level` for minimum distance in points

#### Error: `10018` "Market closed"
**Cause:** Trying to trade when market is closed.
**Fix:** Check if it's weekend (forex closed Fri 5PM-Sun 5PM EST) or holiday

#### Error: `10019` "No money"
**Cause:** Insufficient margin for the trade.
**Fix:** Reduce lot size or check account balance

---

## 11. MARKET HOURS REFERENCE

### Forex Market Hours (UTC)
- **Sydney:** Sun 22:00 → Fri 22:00
- **Tokyo:** Mon 00:00 → Fri 09:00
- **London:** Mon 08:00 → Fri 17:00
- **New York:** Mon 13:00 → Fri 22:00
- **MARKET CLOSED:** Friday 22:00 UTC → Sunday 22:00 UTC

### Commodities (XAUUSD, XAGUSD, USOIL)
- Generally follow forex hours but may have daily breaks (22:00-23:00 UTC)
- Check your broker's specific schedule

### Crypto (BTCUSD, ETHUSD)
- Typically 24/7 including weekends (broker dependent)
- XM crypto pairs may have limited hours

---

## 12. BEST PRACTICES FOR AUTOMATED TRADING

### 12.1 Connection Management
```python
try:
    mt5.initialize(...)
    # ... trading logic ...
finally:
    mt5.shutdown()
```

### 12.2 Auto-Reconnect Pattern
```python
def ensure_connected(fetcher):
    tick = mt5.symbol_info_tick("EURUSD")
    if tick is None:
        print("Connection lost, reconnecting...")
        mt5.shutdown()
        time.sleep(2)
        return fetcher.connect()
    return True
```

### 12.3 Symbol Selection Before Data Request
```python
if not mt5.symbol_select(symbol, True):
    print(f"Symbol {symbol} not available")
    return None
```

### 12.4 SL/TP Rules
- SL and TP must be **absolute price levels**, NOT distances in points
- For BUY: SL < entry_price < TP
- For SELL: TP < entry_price < SL
- Respect `trade_stops_level` minimum distance
- Always set both SL and TP (never trade without a stop loss)

### 12.5 Volume Rules
- Check `symbol_info(symbol).volume_min` (usually 0.01 lots)
- Check `symbol_info(symbol).volume_max` (usually 100 lots)
- Volume must be a multiple of `volume_step` (usually 0.01)
- Round lot sizes: `round(lot_size / volume_step) * volume_step`

### 12.6 Error Handling Flow
```python
# 1. Check initialize
if not mt5.initialize(...):
    error = mt5.last_error()
    handle_init_error(error)

# 2. Pre-check order
check = mt5.order_check(request)
if check.retcode != 0:
    handle_check_error(check)

# 3. Send order with retry
for attempt in range(3):
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        break
    time.sleep(2)
```

---

## 13. COMPLETE FUNCTION REFERENCE TABLE

| Function | Purpose |
|:---|:---|
| `mt5.initialize()` | Connect to MT5 terminal |
| `mt5.login()` | Log in to specific account |
| `mt5.shutdown()` | Close connection |
| `mt5.version()` | Get terminal version |
| `mt5.last_error()` | Get last error code + description |
| `mt5.account_info()` | Get account balance, equity, margin |
| `mt5.terminal_info()` | Get terminal status and settings |
| `mt5.symbols_total()` | Count all available symbols |
| `mt5.symbols_get()` | List all symbols (with filter) |
| `mt5.symbol_info()` | Get symbol specifications |
| `mt5.symbol_info_tick()` | Get latest bid/ask |
| `mt5.symbol_select()` | Add/remove symbol from Market Watch |
| `mt5.copy_rates_from()` | Get bars from date |
| `mt5.copy_rates_from_pos()` | Get bars from position index |
| `mt5.copy_rates_range()` | Get bars in date range |
| `mt5.copy_ticks_from()` | Get ticks from date |
| `mt5.copy_ticks_range()` | Get ticks in date range |
| `mt5.order_check()` | Validate order without sending |
| `mt5.order_send()` | Send trade request |
| `mt5.order_calc_margin()` | Calculate required margin |
| `mt5.order_calc_profit()` | Calculate potential profit |
| `mt5.orders_total()` | Count active pending orders |
| `mt5.orders_get()` | Get active pending orders |
| `mt5.positions_total()` | Count open positions |
| `mt5.positions_get()` | Get open positions |
| `mt5.history_orders_total()` | Count historical orders |
| `mt5.history_orders_get()` | Get historical orders |
| `mt5.history_deals_total()` | Count historical deals |
| `mt5.history_deals_get()` | Get historical deals |
| `mt5.market_book_add()` | Subscribe to market depth |
| `mt5.market_book_get()` | Get market depth data |
| `mt5.market_book_release()` | Unsubscribe from market depth |

---

## 14. YOUR SETUP-SPECIFIC NOTES

### Your MT5 Configuration
- **Broker:** XM Global
- **Server:** `XMGlobal-MT5 9`
- **Account:** `334700663`
- **Terminal Path:** `C:\Program Files\MetaTrader 5\terminal64.exe`
- **Mode:** DEMO (safe for testing)
- **Symbols Traded:** EURUSD, GBPUSD, USDJPY, AUDUSD, XAUUSD, XAGUSD, USOIL, BTCUSD, ETHUSD

### Startup Procedure
1. Open MetaTrader 5 terminal manually
2. Verify it says "Connected" in bottom-right
3. Verify "Algo Trading" button is ON (green)
4. Verify all 9 symbols are visible in Market Watch
5. Then run `python main.py`

### If MT5 Was Just Installed / First Time
1. Open MT5 terminal
2. File → Open an Account → Search for "XMGlobal"
3. Enter login: 334700663, password, select server "XMGlobal-MT5 9"
4. Wait for data to synchronize (may take 1-2 minutes)
5. Right-click Market Watch → "Show All" to make all symbols visible
6. Enable Algo Trading button in toolbar
