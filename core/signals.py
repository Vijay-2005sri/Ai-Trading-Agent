"""Shared strategy output adapter; executable validation occurs at candidate binding."""

from dataclasses import dataclass


@dataclass(frozen=True)
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
