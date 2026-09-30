"""Decimal stop-risk sizing from a broker-verified instrument snapshot."""

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import math
from pydantic import ValidationError
from numbers import Real


class SizingError(ValueError):
    """Inputs or instrument metadata cannot safely produce an order volume."""


def decimal_value(value, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, Real)):
        raise SizingError(f"{label} must be a finite number")
    try:
        if isinstance(value, Real) and not math.isfinite(value):
            raise SizingError(f"{label} must be finite")
        result = value if isinstance(value, Decimal) else Decimal(str(value))
        if not result.is_finite():
            raise SizingError(f"{label} must be finite")
        return result
    except (InvalidOperation, ValueError, TypeError, OverflowError) as error:
        raise SizingError(f"{label} must be a finite number") from error


@dataclass(frozen=True)
class PositionSize:
    volume: Decimal
    risk_fraction: Decimal
    drawdown_multiplier: Decimal
    equity: Decimal
    risk_budget: Decimal
    stop_loss_per_lot: Decimal
    cost_allowance_per_lot: Decimal
    raw_volume: Decimal
    estimated_total_loss: Decimal
    account_currency: str
    instrument_id: str
    contract_revision: str

    def to_audit_dict(self) -> dict:
        return {key: str(value) if isinstance(value, Decimal) else value
                for key, value in asdict(self).items()}


_LINEAR_TICK_VALUE_MODES = frozenset({0, 1, 3, 4, 5})


def size_position(*, instrument, direction: str, entry_price, stop_loss,
                  equity, risk_fraction, drawdown_multiplier=1,
                  cost_allowance_per_lot=0) -> PositionSize:
    """Size in account currency, floor to valid volume, reject under-minimum.

    MT5 tick loss values are already denominated in the observed account
    currency. Unknown/nonlinear calculation modes need a broker P/L calculator
    and are left to the quote-time gateway rather than approximated here.
    """
    try:
        from broker_mt5.instruments import InstrumentSnapshot
        if not isinstance(instrument, InstrumentSnapshot):
            raise SizingError("validated InstrumentSnapshot is required")
        instrument = InstrumentSnapshot.model_validate(instrument.model_dump())
        if direction not in ("BUY", "SELL"):
            raise SizingError("direction must be BUY or SELL")
        entry = decimal_value(entry_price, "entry price")
        stop = decimal_value(stop_loss, "stop loss")
        balance = decimal_value(equity, "equity")
        fraction = decimal_value(risk_fraction, "risk fraction")
        multiplier = decimal_value(drawdown_multiplier, "drawdown multiplier")
        allowance = decimal_value(cost_allowance_per_lot, "cost allowance")

        if balance <= 0:
            raise SizingError("equity must be positive")
        if fraction <= 0 or fraction > 1:
            raise SizingError("risk fraction must be in (0, 1]")
        if multiplier <= 0 or multiplier > 1:
            raise SizingError("drawdown multiplier must be in (0, 1]")
        if allowance < 0:
            raise SizingError("cost allowance cannot be negative")
        if entry <= 0 or stop <= 0:
            raise SizingError("entry and stop must be positive")
        if (direction == "BUY" and stop >= entry) or (direction == "SELL" and stop <= entry):
            raise SizingError("stop must be on the loss side of entry")

        if instrument.trade_calc_mode not in _LINEAR_TICK_VALUE_MODES:
            raise SizingError("instrument calculation mode requires broker P/L calculation")
        tick_size = decimal_value(instrument.trade_tick_size, "tick size")
        tick_value = decimal_value(instrument.trade_tick_value_loss, "losing tick value")
        minimum = decimal_value(instrument.volume_min, "minimum volume")
        maximum = decimal_value(instrument.volume_max, "maximum volume")
        step = decimal_value(instrument.volume_step, "volume step")
        symbol_limit = decimal_value(instrument.volume_limit, "volume limit")
        if min(tick_size, tick_value, minimum, maximum, step) <= 0:
            raise SizingError("instrument tick/volume fields must be positive")
        if minimum > maximum or minimum % step or maximum % step:
            raise SizingError("instrument volume bounds are inconsistent")
        cap = min(maximum, symbol_limit) if symbol_limit > 0 else maximum
        if cap < minimum:
            raise SizingError("instrument volume limit is below minimum")

        risk_budget = balance * fraction * multiplier
        stop_loss_per_lot = abs(entry - stop) / tick_size * tick_value
        per_lot_loss = stop_loss_per_lot + allowance
        if not risk_budget.is_finite() or not stop_loss_per_lot.is_finite() or per_lot_loss <= 0:
            raise SizingError("risk budget or stop loss is invalid")
        raw_volume = risk_budget / per_lot_loss
        stepped = (raw_volume / step).to_integral_value(rounding=ROUND_FLOOR) * step
        volume = min(stepped, cap)
        volume = (volume / step).to_integral_value(rounding=ROUND_FLOOR) * step
        if volume < minimum:
            raise SizingError("risk budget cannot fund the broker minimum volume")

        estimated_loss = per_lot_loss * volume
        if not estimated_loss.is_finite() or estimated_loss > risk_budget:
            raise SizingError("rounded volume exceeds the monetary risk budget")

        return PositionSize(
            volume=volume, risk_fraction=fraction, drawdown_multiplier=multiplier,
            equity=balance, risk_budget=risk_budget,
            stop_loss_per_lot=stop_loss_per_lot,
            cost_allowance_per_lot=allowance, raw_volume=raw_volume,
            estimated_total_loss=estimated_loss,
            account_currency=instrument.account_currency,
            instrument_id=instrument.instrument_id,
            contract_revision=instrument.revision,
        )
    except SizingError:
        raise
    except (InvalidOperation, ArithmeticError, AttributeError, TypeError, ValueError, ValidationError) as error:
        raise SizingError("position sizing failed validation") from error
