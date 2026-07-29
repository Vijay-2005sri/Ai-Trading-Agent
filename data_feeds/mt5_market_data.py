import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

class MT5DataFetcher:
    def __init__(self, login, password, server, path=None):
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        
    def connect(self):
        """Initializes the MT5 connection."""
        print(f"Connecting to MT5: {self.login} on {self.server}")
        if self.path:
            initialized = mt5.initialize(path=self.path, login=self.login, password=self.password, server=self.server)
        else:
            initialized = mt5.initialize(login=self.login, password=self.password, server=self.server)
            
        if not initialized:
            print(f"MT5 initialization failed. Error: {mt5.last_error()}")
            return False
        return True
        
    def get_historical_data(self, symbol, timeframe, count=500):
        """Fetches historical OHLCV data."""
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            print(f"Failed to get data for {symbol}. Error: {mt5.last_error()}")
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df

    def get_live_tick(self, symbol):
        """Gets the most recent tick (bid/ask)."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'time': pd.to_datetime(tick.time, unit='s')
        }

    def disconnect(self):
        mt5.shutdown()

if __name__ == "__main__":
    # Test script functionality
    pass
