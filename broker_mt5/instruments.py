"""Broker-observed metadata, never a static fallback or order authorization."""

from datetime import datetime
from decimal import Decimal
import hashlib
import json
import math
import threading
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from config.execution_mode import ModeError
from core.models import VersionedRecord
from core.time_service import SystemClock, as_utc


class InstrumentError(ModeError):
    pass


class InstrumentSnapshot(VersionedRecord):
    source: Literal["mt5"] = "mt5"
    instrument_id: str
    broker_symbol: str
    server: str
    login: int = Field(gt=0)
    account_currency: str
    leverage: int = Field(gt=0)
    margin_mode: int = Field(ge=0, le=2)
    observed_at: datetime
    currency_base: str
    currency_profit: str
    currency_margin: str
    digits: int = Field(ge=0, le=12)
    point: Decimal = Field(gt=0)
    trade_tick_size: Decimal = Field(gt=0)
    trade_tick_value_profit: Decimal = Field(gt=0)
    trade_tick_value_loss: Decimal = Field(gt=0)
    trade_contract_size: Decimal = Field(gt=0)
    volume_min: Decimal = Field(gt=0)
    volume_max: Decimal = Field(gt=0)
    volume_step: Decimal = Field(gt=0)
    volume_limit: Decimal = Field(ge=0)
    trade_stops_level: int = Field(ge=0)
    trade_freeze_level: int = Field(ge=0)
    trade_mode: int = Field(ge=0, le=4)
    trade_exemode: int = Field(ge=0, le=3)
    filling_mode: int = Field(ge=0, le=7)
    order_mode: int = Field(ge=0, le=127)
    trade_calc_mode: int
    margin_initial: Decimal = Field(ge=0)
    margin_maintenance: Decimal = Field(ge=0)
    margin_hedged: Decimal = Field(ge=0)
    margin_hedged_use_leg: bool

    @field_validator("observed_at")
    @classmethod
    def utc(cls, value):
        return as_utc(value)

    @field_validator("instrument_id", "broker_symbol", "server", "account_currency",
                     "currency_base", "currency_profit", "currency_margin")
    @classmethod
    def name(cls, value):
        if not value or value != value.strip():
            raise ValueError("Missing or ambiguous metadata identity/currency")
        return value

    @model_validator(mode="after")
    def geometry(self):
        if self.point != Decimal(10) ** -self.digits:
            raise ValueError("Point does not match digits")
        if self.trade_tick_size % self.point != 0:
            raise ValueError("Tick size is not a whole number of points")
        if self.volume_min > self.volume_max or self.volume_step > self.volume_max:
            raise ValueError("Invalid volume bounds")
        if self.volume_min % self.volume_step or self.volume_max % self.volume_step:
            raise ValueError("Volume bounds are not aligned to the step")
        if self.volume_limit and self.volume_limit < self.volume_min:
            raise ValueError("Volume limit is below minimum")
        if self.trade_calc_mode not in {0, 1, 2, 3, 4, 5, 32, 33, 34, 35, 36, 37, 64}:
            raise ValueError("Unknown calculation mode")
        return self

    @property
    def revision(self):
        document = json.dumps(self.model_dump(mode="json", exclude={"observed_at"}),
                              sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return hashlib.sha256(document.encode("utf-8")).hexdigest()


_DECIMALS = (
    "point", "trade_tick_size", "trade_tick_value_profit", "trade_tick_value_loss",
    "trade_contract_size", "volume_min", "volume_max", "volume_step", "volume_limit",
    "margin_initial", "margin_maintenance", "margin_hedged",
)
_NATIVE = (
    "currency_base", "currency_profit", "currency_margin", "digits", "trade_stops_level",
    "trade_freeze_level", "trade_mode", "trade_exemode", "filling_mode", "order_mode",
    "trade_calc_mode", "margin_hedged_use_leg",
)


def _account_context(account):
    values = tuple(getattr(account, field, None) for field in ("server", "login", "currency", "leverage", "margin_mode"))
    server, login, currency, leverage, margin_mode = values
    if (type(login) is not int or login <= 0 or type(leverage) is not int or leverage <= 0
            or type(margin_mode) is not int or margin_mode not in (0, 1, 2)
            or not isinstance(server, str) or not server or server != server.strip()
            or not isinstance(currency, str) or not currency or currency != currency.strip()):
        raise InstrumentError("Invalid account metadata context")
    return values


class InstrumentProvider:
    def __init__(self, *, symbol_registry, account_reader, symbol_reader, clock=None, max_age_seconds=60):
        if type(max_age_seconds) not in (int, float) or not math.isfinite(max_age_seconds) or max_age_seconds <= 0:
            raise InstrumentError("Metadata cache lifetime must be finite and positive")
        self.registry = symbol_registry
        self.account_reader = account_reader
        self.symbol_reader = symbol_reader
        self.clock = clock or SystemClock()
        self.max_age_seconds = max_age_seconds
        self._cache = {}
        self._context = None
        self._lock = threading.RLock()

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._context = None

    def get(self, symbol, *, refresh=False):
        with self._lock:
            try:
                native = self.registry.broker_symbol(symbol)
                canonical = self.registry.from_broker(native)
                context = _account_context(self.account_reader())
                if context != self._context:
                    self._cache.clear()
                    self._context = context
                key = (context[0], context[1], native)
                now, elapsed = as_utc(self.clock.now_utc()), self.clock.monotonic()
                if not math.isfinite(elapsed):
                    raise InstrumentError("Invalid monotonic clock")
                cached = self._cache.get(key)
                if cached and not refresh:
                    snapshot, recorded = cached
                    if (0 <= elapsed - recorded < self.max_age_seconds
                            and 0 <= (now - snapshot.observed_at).total_seconds() < self.max_age_seconds):
                        return snapshot
                self._cache.pop(key, None)
                raw = self.symbol_reader(native)
                if raw is None or getattr(raw, "name", None) != native:
                    raise InstrumentError("Missing or mismatched broker symbol metadata")
                data = {name: getattr(raw, name, None) for name in _NATIVE}
                for name in _DECIMALS:
                    value = getattr(raw, name, None)
                    if type(value) not in (int, float) or not math.isfinite(value):
                        raise InstrumentError(f"Missing/nonfinite numeric metadata: {name}")
                    data[name] = Decimal(str(value)).normalize()
                after = _account_context(self.account_reader())
                if after != context:
                    raise InstrumentError("Account context changed during metadata read")
                snapshot = InstrumentSnapshot(
                    instrument_id=canonical, broker_symbol=native, server=context[0], login=context[1],
                    account_currency=context[2], leverage=context[3], margin_mode=context[4],
                    observed_at=now, **data)
                age = self.clock.monotonic() - elapsed
                if not math.isfinite(age) or not 0 <= age < self.max_age_seconds:
                    raise InstrumentError("Metadata read exceeded freshness lifetime")
                self._cache[key] = (snapshot, elapsed)
                return snapshot
            except Exception as error:
                self.clear()
                if isinstance(error, ModeError):
                    raise
                if isinstance(error, (ValidationError, ValueError, ArithmeticError, TypeError, AttributeError)):
                    raise InstrumentError("Broker metadata validation failed") from error
                raise InstrumentError("Broker metadata unavailable") from error
