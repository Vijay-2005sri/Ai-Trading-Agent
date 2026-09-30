"""
=============================================================================
CONTRACT SPECIFICATIONS — Pip/Point Values Per Instrument (XM MT5)
=============================================================================
UNVERIFIED REFERENCE ONLY. These legacy examples are not account-specific broker
metadata, sizing approval or execution authority. Runtime metadata comes only from
broker_mt5.instruments. Pip conventions and dollar examples below are illustrative;
actual economics vary by account currency and broker contract. Unknown names fail
instead of inheriting guessed forex/crypto/metal values.

Formula for every instrument:
  Risk Amount ($) = Lot Size × Pip Value Per Lot × SL in Pips
  → Lot Size = Risk Amount / (Pip Value Per Lot × SL in Pips)
=============================================================================
"""

# =============================================================================
# CONTRACT SPECIFICATIONS TABLE
# =============================================================================
# Each entry contains:
#   pip_size     : The decimal price movement = 1 pip  (e.g., 0.0001 for EURUSD)
#   pip_value    : Dollar value of 1 pip per 1 Standard Lot (e.g., $10 for EURUSD)
#   contract_size: Units of base asset per 1 Standard Lot
#   min_lot      : Minimum tradeable lot size
#   lot_step     : Lot size increment step
#   market_type  : "forex" | "commodity" | "crypto" | "energy"
#   volatility   : "slow_steady" | "high_volatility"
#   notes        : Important notes for the Risk Agent

CONTRACT_SPECS = {

    # =========================================================================
    # FOREX — Slow & Steady Markets
    # =========================================================================

    "EURUSD": {
        "pip_size":     0.0001,        # 1 pip = $0.0001 price move
        "pip_value":    10.0,          # $10 per pip per 1 Standard Lot
        "contract_size": 100_000,      # 100,000 EUR per lot
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "forex",
        "volatility":   "slow_steady",
        "notes": "Major pair. 1 pip = 4th decimal. $10/pip/lot. JPY pairs use 0.01 pip size."
    },

    "GBPUSD": {
        "pip_size":     0.0001,
        "pip_value":    10.0,          # $10 per pip per 1 Standard Lot
        "contract_size": 100_000,
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "forex",
        "volatility":   "slow_steady",
        "notes": "Major pair. More volatile than EURUSD but still slow/steady category."
    },

    "AUDUSD": {
        "pip_size":     0.0001,
        "pip_value":    10.0,
        "contract_size": 100_000,
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "forex",
        "volatility":   "slow_steady",
        "notes": "Major pair. Sensitive to Chinese economy and commodity prices."
    },

    "NZDUSD": {
        "pip_size":     0.0001,
        "pip_value":    10.0,
        "contract_size": 100_000,
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "forex",
        "volatility":   "slow_steady",
        "notes": "Minor major pair. Commodity-linked currency."
    },

    "USDJPY": {
        "pip_size":     0.01,          # JPY pairs: 1 pip = 0.01 (2nd decimal)
        "pip_value":    6.5,           # ~$6.50 per pip (varies with exchange rate)
        "contract_size": 100_000,
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "forex",
        "volatility":   "slow_steady",
        "notes": (
            "JPY pair: pip size is 0.01, NOT 0.0001. "
            "Pip value fluctuates: use formula (0.01/current_rate)*100000*lots. "
            "Approx $6.50/pip/lot at 154 rate."
        )
    },

    "USDCHF": {
        "pip_size":     0.0001,
        "pip_value":    10.0,          # Approximately $10 (varies slightly with CHF rate)
        "contract_size": 100_000,
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "forex",
        "volatility":   "slow_steady",
        "notes": "Safe haven currency pair. Pip value ≈ $10 at parity."
    },

    "USDCAD": {
        "pip_size":     0.0001,
        "pip_value":    7.5,           # ≈$7.50/pip (varies with CAD rate)
        "contract_size": 100_000,
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "forex",
        "volatility":   "slow_steady",
        "notes": "Oil-linked currency. Pip value ≈ $7-8 depending on USDCAD rate."
    },

    # =========================================================================
    # COMMODITIES — High Volatility
    # =========================================================================

    "XAUUSD": {
        # As per user-provided breakdown:
        # 1 pip = $0.10 price movement in Gold
        # 1 lot = 100 oz
        # $10 profit/loss per pip per 1 Standard Lot
        # Loss at SL of 15 pips = 15 × $10 = $150 (1 lot)
        "pip_size":     0.10,          # 1 pip = $0.10 price move in Gold
        "pip_value":    10.0,          # $10 per pip per 1 Standard Lot (100 oz)
        "contract_size": 100,          # 100 troy ounces per lot
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "commodity",
        "volatility":   "high_volatility",
        "notes": (
            "GOLD: 1 pip = $0.10 price move. $10/pip for 1 lot (100 oz). "
            "Example: 15-pip SL on 0.10 lot = $15 risk. "
            "70-pip TP on 0.10 lot = $70 profit. "
            "This matches the user's verified breakdown."
        )
    },

    "XAGUSD": {
        # Silver: 1 lot = 5,000 oz. 1 pip = $0.01. $50/pip/lot.
        # Much more volatile than Gold per dollar moved.
        "pip_size":     0.01,          # 1 pip = $0.01 price move in Silver
        "pip_value":    50.0,          # $50 per pip per 1 Standard Lot (5,000 oz)
        "contract_size": 5000,         # 5,000 troy ounces per lot
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "commodity",
        "volatility":   "high_volatility",
        "notes": (
            "SILVER: Very high pip value. $50/pip/lot. "
            "Use minimum lot sizes (0.01). "
            "15-pip SL on 0.01 lot = $7.50 risk. "
            "Silver is extremely volatile — treat like crypto."
        )
    },

    "USOIL": {
        # Oil: 1 lot = 100 barrels. 1 pip = $0.01. $1/pip/lot.
        "pip_size":     0.01,          # 1 pip = $0.01 price move in Oil
        "pip_value":    1.0,           # $1 per pip per 1 Standard Lot (100 barrels)
        "contract_size": 100,          # 100 barrels per lot
        "min_lot":      0.10,          # Minimum 0.10 lots
        "lot_step":     0.10,
        "market_type":  "energy",
        "volatility":   "high_volatility",
        "notes": (
            "CRUDE OIL WTI: $1/pip/lot. "
            "Min lot = 0.10. Sensitive to OPEC news and geopolitics."
        )
    },

    # =========================================================================
    # CRYPTO — High Volatility (Measured in $1 points, not traditional pips)
    # =========================================================================

    "BTCUSD": {
        # Bitcoin: 1 lot = 1 BTC. Price moves in $1 increments.
        # Convention: 1 "pip" = $1.00 price move (NOT $0.10 like gold)
        # Some brokers use 1 pip = $0.01 — we use $1 as standard readable unit
        "pip_size":     1.0,           # 1 pip = $1.00 price move in BTC
        "pip_value":    1.0,           # $1 per pip per 1 Standard Lot (1 BTC)
        "contract_size": 1,            # 1 Bitcoin per lot
        "min_lot":      0.01,
        "lot_step":     0.01,
        "market_type":  "crypto",
        "volatility":   "high_volatility",
        "notes": (
            "BITCOIN: 1 pip = $1.00 price move. "
            "1 lot = 1 BTC. 15-pip SL on 0.01 lot = $0.15 risk. "
            "For meaningful risk, trade 0.01+ lots with 500-2000 pip SL. "
            "Example: 1000-pip SL on 0.01 lot = $10 risk."
        )
    },

    "ETHUSD": {
        # Ethereum: 1 lot = 1 ETH. 1 pip = $0.01 price move.
        "pip_size":     0.01,          # 1 pip = $0.01 price move in ETH
        "pip_value":    0.01,          # $0.01 per pip per 1 Standard Lot
        "contract_size": 1,            # 1 ETH per lot
        "min_lot":      0.10,
        "lot_step":     0.10,
        "market_type":  "crypto",
        "volatility":   "high_volatility",
        "notes": (
            "ETHEREUM: Smaller than BTC. 1 lot = 1 ETH. "
            "Use larger pip targets (500-1000 pips) for meaningful moves."
        )
    },
}


# =============================================================================
# MARKET CLASSIFICATION
# =============================================================================

# These symbols are classified as "slow & steady" — use conservative risk rules
SLOW_STEADY_MARKETS = {
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
    "USDJPY", "USDCHF", "USDCAD"
}

# These symbols are classified as "high volatility" — use aggressive protection rules
HIGH_VOLATILITY_MARKETS = {
    "XAUUSD", "XAGUSD", "USOIL",
    "BTCUSD", "ETHUSD"
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_contract_spec(symbol: str) -> dict:
    """
    Return a copy of an exact, unverified reference entry, never live metadata.
    """
    spec = CONTRACT_SPECS.get(symbol)
    if spec:
        return {**spec, "source": "unverified_reference", "execution_eligible": False}
    raise ValueError(f"No reference specification for exact symbol {symbol!r}")


def calculate_lot_size(
    symbol: str,
    risk_amount_dollars: float,
    sl_in_pips: float
) -> float:
    """Reject the unsafe historical estimator; use verified account metadata."""
    raise ValueError(
        "Static contract specs cannot size orders; use core.position_sizer.size_position "
        "with a broker-verified InstrumentSnapshot"
    )


def dollars_to_pips(symbol: str, dollar_move: float, lot_size: float) -> float:
    """Converts a dollar P&L into pips for display purposes."""
    spec = get_contract_spec(symbol)
    if spec["pip_value"] * lot_size <= 0:
        return 0.0
    return dollar_move / (spec["pip_value"] * lot_size)


def pips_to_dollars(symbol: str, pips: float, lot_size: float) -> float:
    """Converts pips into dollar P&L."""
    spec = get_contract_spec(symbol)
    return pips * spec["pip_value"] * lot_size


def pips_to_price(symbol: str, pips: float) -> float:
    """Converts pips into a price movement (for calculating SL/TP prices)."""
    spec = get_contract_spec(symbol)
    return pips * spec["pip_size"]


def is_high_volatility(symbol: str) -> bool:
    """Returns True if the symbol is classified as high-volatility."""
    return symbol in HIGH_VOLATILITY_MARKETS


def get_pip_summary(symbol: str) -> str:
    """Returns a human-readable pip spec for logging/LLM context."""
    spec = get_contract_spec(symbol)
    return (
        f"{symbol}: 1 pip = ${spec['pip_size']} price move | "
        f"${spec['pip_value']}/pip/lot | "
        f"Contract: {spec['contract_size']} units | "
        f"Market: {spec['volatility'].replace('_', ' ').title()}"
    )


if __name__ == "__main__":
    # Quick verification test
    print("=== CONTRACT SPEC VERIFICATION ===\n")

    for sym in CONTRACT_SPECS:
        print(get_pip_summary(sym))

    print("\nOrder sizing requires a broker-verified InstrumentSnapshot.")
