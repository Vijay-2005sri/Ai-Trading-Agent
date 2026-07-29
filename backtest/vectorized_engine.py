"""
=============================================================================
BACKTESTER — Vectorized Strategy Evaluation Engine
=============================================================================
This module allows us to test ANY strategy from our strategy_library against
historical data BEFORE letting the LLM trade it live.

It uses pandas vectorization so it can test years of data in seconds.
=============================================================================
"""

import pandas as pd
import numpy as np
from typing import Type

# We import the base class/type to know what to expect
from strategy_library.smc_concepts import TradeSignal


class VectorizedBacktester:
    """
    Lightning fast backtester for our AI strategies.
    
    How it works:
    1. Pass in a Strategy class (e.g., ICTSilverBulletStrategy)
    2. Pass in historical OHLCV data (pandas DataFrame)
    3. It runs the strategy bar-by-bar (simulating live trading)
    4. Calculates win rate, max drawdown, and PnL.
    """

    def __init__(self, initial_capital: float = 10000.0, risk_per_trade: float = 0.02):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade

    def run(self, strategy_class: Type, df: pd.DataFrame, pair: str = "EURUSD", pip_value: float = 10.0) -> dict:
        """
        Run the backtest.
        Note: True vectorization is hard with complex AI signals, so we use
        a sliding window approach that exactly mimics how the live bot runs.
        """
        print(f"  [BACKTEST] Running {strategy_class.__name__} on {len(df)} bars...")
        
        strategy = strategy_class(pair=pair)
        
        capital = self.initial_capital
        peak_capital = capital
        max_drawdown = 0.0
        
        trades = []
        
        # We need a minimum amount of data for indicators to warm up
        warmup = 100
        if len(df) < warmup + 10:
            return {"error": "Not enough data"}

        # Simulate walking forward in time
        # (This is slower than pure vectorization, but necessary for complex stateful strategies)
        for i in range(warmup, len(df) - 1):
            # Window of data available UP TO this point in time
            window = df.iloc[:i+1]
            
            # Generate signals just like in live trading
            signals: list[TradeSignal] = strategy.generate_signals(window)
            
            if signals:
                # Take the highest confidence signal
                sig = sorted(signals, key=lambda x: x.confidence, reverse=True)[0]
                
                # We enter on the OPEN of the NEXT bar
                entry_price = df['open'].iloc[i+1]
                sl = sig.stop_loss
                tp = sig.take_profit
                
                # Check if this trade is a win or loss by looking ahead
                # (Simplified: assumes if low < SL it's a loss, if high > TP it's a win)
                lookahead = df.iloc[i+1 : i+50]  # Look forward max 50 bars
                
                outcome = None
                pnl = 0.0
                bars_held = 0
                
                for _, future_bar in lookahead.iterrows():
                    bars_held += 1
                    
                    if sig.direction == "BUY":
                        if future_bar['low'] <= sl:
                            outcome = "LOSS"
                            # Calculate loss amount based on 2% risk
                            risk_amount = capital * self.risk_per_trade
                            pnl = -risk_amount
                            break
                        elif future_bar['high'] >= tp:
                            outcome = "WIN"
                            risk_amount = capital * self.risk_per_trade
                            # PnL = Risk Amount * Risk/Reward Ratio
                            pnl = risk_amount * sig.risk_reward
                            break
                            
                    elif sig.direction == "SELL":
                        if future_bar['high'] >= sl:
                            outcome = "LOSS"
                            pnl = -(capital * self.risk_per_trade)
                            break
                        elif future_bar['low'] <= tp:
                            outcome = "WIN"
                            pnl = (capital * self.risk_per_trade) * sig.risk_reward
                            break
                
                if outcome:
                    capital += pnl
                    if capital > peak_capital:
                        peak_capital = capital
                    
                    dd = (peak_capital - capital) / peak_capital
                    if dd > max_drawdown:
                        max_drawdown = dd
                        
                    trades.append({
                        "time": df.index[i+1],
                        "direction": sig.direction,
                        "pnl": pnl,
                        "capital_after": capital,
                        "bars_held": bars_held
                    })
                    
        # Calculate statistics
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = (len(wins) / len(trades) * 100) if trades else 0.0
        profit_factor = (sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses))) if losses else float('inf')
        
        return {
            "strategy": strategy_class.__name__,
            "total_trades": len(trades),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "initial_capital": self.initial_capital,
            "final_capital": round(capital, 2),
            "total_return_pct": round(((capital - self.initial_capital) / self.initial_capital) * 100, 2),
            "max_drawdown_pct": round(max_drawdown * 100, 2)
        }
