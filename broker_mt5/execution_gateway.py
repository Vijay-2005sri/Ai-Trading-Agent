"""Fresh-quote validation and one-shot authorization for MT5 market orders."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
import hashlib
import json
import math
import secrets
import threading
from uuid import UUID
from functools import wraps
from numbers import Real

from broker_mt5.instruments import InstrumentSnapshot

from config.execution_mode import ModeError
from core.position_sizer import SizingError, decimal_value
from core.time_service import SystemClock, as_utc


class GatewayError(ModeError):
    pass


def guarded(operation):
    """Serialize gateway transitions and fail closed on native callback failures."""
    @wraps(operation)
    def run(self, *args, **kwargs):
        with self._lock:
            try:
                return operation(self, *args, **kwargs)
            except GatewayError:
                raise
            except Exception as error:
                raise GatewayError(f"{operation.__name__} failed; no automatic retry") from error
    return run


@dataclass(frozen=True)
class QuotePreparation:
    pair: str
    direction: str
    reference_entry: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    risk_reward: Decimal
    bid: Decimal
    ask: Decimal
    quote_time: datetime
    acquired_monotonic: float
    account_identity: tuple
    instrument: object
    candidate_id: str
    strategy_id: str
    evidence_digest: str
    preparation_id: str


@dataclass(frozen=True)
class GatewayAuthorization:
    approved: bool
    trade_record: object | None
    risk_result: object | None
    token: str | None
    audit: dict
    reason: str


class ExecutionGateway:
    """Issue expiring, in-memory, single-use authority for one exact request."""

    def __init__(self, executor, *, config=None, clock=None):
        self.executor = executor
        self.mt5 = executor._mt5
        self.clock = clock or SystemClock()
        values = {} if config is None else config
        if not isinstance(values, dict):
            raise GatewayError("Gateway configuration must be a mapping")
        if set(values) - {"quote_max_age_seconds", "approval_ttl_seconds", "max_spread_points",
                          "max_entry_deviation_points", "request_deviation_points"}:
            raise GatewayError("Unknown gateway configuration key")
        self.quote_max_age = self._positive(values.get("quote_max_age_seconds", 2), "quote age")
        self.approval_ttl = self._positive(values.get("approval_ttl_seconds", 3), "approval TTL")
        self.max_spread_points = self._positive(values.get("max_spread_points", 50), "spread limit")
        self.max_deviation_points = self._positive(values.get("max_entry_deviation_points", 100), "deviation limit")
        self.deviation_request_points = values.get("request_deviation_points", 10)
        if type(self.deviation_request_points) is not int or self.deviation_request_points <= 0:
            raise GatewayError("Request deviation must be a positive integer")
        self._risk_agent = None
        self._approvals = {}
        self._preparations = {}
        self._native_permits = {}
        self._lock = threading.RLock()

    @staticmethod
    def _positive(value, label):
        try:
            if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
                raise ValueError
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            raise GatewayError(f"Invalid {label} configuration") from None
        if not math.isfinite(number) or number <= 0:
            raise GatewayError(f"Invalid {label} configuration")
        return number

    def bind_risk_agent(self, risk_agent):
        if risk_agent is None or not callable(getattr(risk_agent, "evaluate_trade", None)):
            raise GatewayError("A deterministic RiskAgent is required")
        self._risk_agent = risk_agent

    def clear(self):
        with self._lock:
            self._approvals.clear()
            self._preparations.clear()
            self._native_permits.clear()

    @staticmethod
    def _fingerprint(value):
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _preparation_fingerprint(self, preparation):
        return self._fingerprint({
            "pair": preparation.pair, "direction": preparation.direction,
            "reference_entry": str(preparation.reference_entry),
            "entry_price": str(preparation.entry_price), "stop_loss": str(preparation.stop_loss),
            "take_profit": str(preparation.take_profit), "risk_reward": str(preparation.risk_reward),
            "bid": str(preparation.bid), "ask": str(preparation.ask),
            "quote_time": preparation.quote_time.isoformat(),
            "acquired_monotonic": preparation.acquired_monotonic,
            "account_identity": preparation.account_identity,
            "instrument_revision": preparation.instrument.revision,
            "candidate_id": preparation.candidate_id, "strategy_id": preparation.strategy_id,
            "evidence_digest": preparation.evidence_digest,
            "preparation_id": preparation.preparation_id,
        })

    @staticmethod
    def _risk_decimal(value, label):
        if isinstance(value, str):
            try:
                parsed = Decimal(value)
            except Exception as error:
                raise GatewayError(f"Invalid RiskAgent {label}") from error
            if not parsed.is_finite():
                raise GatewayError(f"Invalid RiskAgent {label}")
            return parsed
        return decimal_value(value, label)

    def _account_identity(self, account):
        identity = tuple(getattr(account, key, None) for key in (
            "login", "server", "currency", "leverage", "margin_mode"))
        if (type(identity[0]) is not int or identity[0] <= 0
                or not all(isinstance(v, str) and v and v == v.strip() for v in (identity[1], identity[2]))
                or type(identity[3]) is not int or identity[3] <= 0
                or type(identity[4]) is not int or identity[4] not in (0, 1, 2)):
            raise GatewayError("Invalid account identity for pre-trade approval")
        if getattr(account, "trade_allowed", None) is not True or getattr(account, "trade_expert", None) is not True:
            raise GatewayError("Account trading permissions are disabled")
        return identity

    def _check_elapsed(self, started):
        now = self.clock.monotonic()
        elapsed = now - started
        if not math.isfinite(now) or not math.isfinite(elapsed) or not 0 <= elapsed <= self.approval_ttl:
            raise GatewayError("Gateway approval expired or monotonic clock is invalid")

    @staticmethod
    def _native_number(value):
        number = float(value)
        if not math.isfinite(number) or decimal_value(number, "native number") != value:
            raise GatewayError("Validated number cannot be represented by native request")
        return number

    def _read_quote(self, pair):
        account = self.executor.assert_demo_session()
        identity = self._account_identity(account)
        terminal = self.mt5.terminal_info()
        if (terminal is None or getattr(terminal, "trade_allowed", None) is not True
                or getattr(terminal, "tradeapi_disabled", None) is not False):
            raise GatewayError("Terminal trading API permissions are disabled or unavailable")
        spec = self.executor.get_instrument_spec(pair)
        if not isinstance(spec, InstrumentSnapshot):
            raise GatewayError("Verified contract snapshot is required")
        spec = InstrumentSnapshot.model_validate(spec.model_dump())
        if (spec.login, spec.server, spec.account_currency, spec.leverage, spec.margin_mode) != identity:
            raise GatewayError("Account and contract identities differ")
        symbol = spec.broker_symbol
        started = self.clock.monotonic()
        try:
            tick = self.mt5.symbol_info_tick(symbol)
        except Exception as error:
            raise GatewayError("Current executable quote unavailable") from error
        acquired = self.clock.monotonic()
        now = as_utc(self.clock.now_utc())
        if not math.isfinite(started) or not math.isfinite(acquired) or acquired < started:
            raise GatewayError("Invalid monotonic quote clock")
        if tick is None or type(getattr(tick, "time_msc", None)) is not int or tick.time_msc <= 0:
            raise GatewayError("Quote has no valid millisecond timestamp")
        try:
            bid = decimal_value(getattr(tick, "bid", None), "bid")
            ask = decimal_value(getattr(tick, "ask", None), "ask")
            quote_time = datetime.fromtimestamp(tick.time_msc / 1000, tz=timezone.utc)
            age = (now - quote_time).total_seconds()
        except (ValueError, OverflowError, OSError) as error:
            raise GatewayError("Quote timestamp or price is invalid") from error
        if bid <= 0 or ask <= 0 or ask < bid:
            raise GatewayError("Quote is missing, nonpositive or crossed")
        if not math.isfinite(age) or age < 0 or age > self.quote_max_age:
            raise GatewayError("Quote is future-dated or stale")
        if acquired - started > self.quote_max_age:
            raise GatewayError("Quote retrieval exceeded freshness window")
        account = self.executor.assert_demo_session()
        if self._account_identity(account) != identity:
            raise GatewayError("Account changed during quote retrieval")
        terminal = self.mt5.terminal_info()
        if (terminal is None or getattr(terminal, "trade_allowed", None) is not True
                or getattr(terminal, "tradeapi_disabled", None) is not False):
            raise GatewayError("Terminal trading API permissions changed during quote retrieval")
        return account, identity, spec, bid, ask, quote_time, started

    def _validate_permissions(self, account, spec, direction, *, closing=False):
        if getattr(account, "trade_allowed", None) is not True or getattr(account, "trade_expert", None) is not True:
            raise GatewayError("Account trading permissions are disabled")
        mode = spec.trade_mode
        if mode == 0 or (not closing and mode == 3):
            raise GatewayError("Instrument trade mode blocks this order")
        if not closing and ((mode == 1 and direction != "BUY") or (mode == 2 and direction != "SELL")):
            raise GatewayError("Instrument trade mode blocks this direction")
        if not spec.order_mode & 1:
            raise GatewayError("Instrument does not permit market orders")
        if not closing and (not spec.order_mode & 16 or not spec.order_mode & 32):
            raise GatewayError("Instrument does not permit protective stop and target")
        # Preserve the executor's supported IOC path; do not silently select a
        # different fill policy based on unfamiliar broker flags.
        if spec.trade_exemode in (2, 3) and not spec.filling_mode & 2:
            raise GatewayError("Instrument does not support IOC execution")

    @guarded
    def prepare_trade(self, *, pair, direction, reference_entry, stop_loss, take_profit,
                      minimum_rr, contract_revision, candidate_id, strategy_id, evidence_digest):
        started = self.clock.monotonic()
        if self._risk_agent is None:
            raise GatewayError("RiskAgent has not been bound to the execution gateway")
        canonical = self.executor.symbol_registry.canonical(pair)
        if direction not in ("BUY", "SELL"):
            raise GatewayError("Direction must be BUY or SELL")
        try:
            candidate = UUID(str(candidate_id))
            if candidate.version != 4:
                raise ValueError("candidate ID must be UUID4")
            if not isinstance(strategy_id, str) or not 1 <= len(strategy_id.strip()) <= 100:
                raise ValueError("strategy ID is missing")
            if not isinstance(evidence_digest, str) or len(evidence_digest) != 64 or any(c not in "0123456789abcdef" for c in evidence_digest):
                raise ValueError("evidence digest is invalid")
            reference = decimal_value(reference_entry, "reference entry")
            stop = decimal_value(stop_loss, "stop loss")
            target = decimal_value(take_profit, "take profit")
            minimum = decimal_value(minimum_rr, "minimum reward/risk")
            expected_revision = str(contract_revision)
        except (ValueError, TypeError, SizingError) as error:
            raise GatewayError(f"Invalid constructed trade identity or prices: {error}") from error
        if reference <= 0 or stop <= 0 or target <= 0 or minimum <= 0:
            raise GatewayError("Constructed prices and minimum reward/risk must be positive")

        account, identity, spec, bid, ask, quote_time, acquired = self._read_quote(canonical)
        if spec.revision != expected_revision:
            raise GatewayError("Contract changed since construction; reanalysis required")
        self._validate_permissions(account, spec, direction)
        point, tick_size = spec.point, spec.trade_tick_size
        entry = ask if direction == "BUY" else bid
        if entry % tick_size:
            raise GatewayError("Executable quote is off the contract tick grid")
        spread_points = (ask - bid) / point
        drift_points = abs(entry - reference) / point
        if spread_points > Decimal(str(self.max_spread_points)):
            raise GatewayError("Spread exceeds configured maximum")
        if drift_points > Decimal(str(self.max_deviation_points)):
            raise GatewayError("Executable price drift exceeds configured maximum")
        if direction == "BUY":
            if not stop < entry < target:
                raise GatewayError("BUY executable geometry crosses stop or target")
            close_side = bid
        else:
            if not target < entry < stop:
                raise GatewayError("SELL executable geometry crosses stop or target")
            close_side = ask
        risk_distance = abs(entry - stop)
        reward_distance = abs(target - entry)
        reward_risk = reward_distance / risk_distance
        if reward_risk < minimum:
            raise GatewayError("Executable quote erodes reward/risk below minimum")
        minimum_distance = Decimal(max(spec.trade_stops_level, spec.trade_freeze_level)) * point
        stop_distance = close_side - stop if direction == "BUY" else stop - close_side
        target_distance = target - close_side if direction == "BUY" else close_side - target
        if min(stop_distance, target_distance) <= 0 or min(stop_distance, target_distance) < minimum_distance:
            raise GatewayError("Stop or freeze distance is too close to current closing-side quote")
        if stop % tick_size or target % tick_size:
            raise GatewayError("Protective prices are off the contract tick grid")
        preparation = QuotePreparation(
            pair=canonical, direction=direction, reference_entry=reference, entry_price=entry,
            stop_loss=stop, take_profit=target, risk_reward=reward_risk, bid=bid, ask=ask,
            quote_time=quote_time, acquired_monotonic=started, account_identity=identity,
            instrument=spec, candidate_id=str(candidate), strategy_id=strategy_id.strip(),
            evidence_digest=evidence_digest, preparation_id=secrets.token_urlsafe(32),
        )
        with self._lock:
            self._check_elapsed(started)
            self._preparations[preparation.preparation_id] = (
                preparation, self._preparation_fingerprint(preparation))
        return preparation

    def _request(self, preparation, record, volume):
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": preparation.instrument.broker_symbol,
            "volume": self._native_number(volume),
            "type": self.mt5.ORDER_TYPE_BUY if preparation.direction == "BUY" else self.mt5.ORDER_TYPE_SELL,
            "price": self._native_number(preparation.entry_price),
            "sl": self._native_number(preparation.stop_loss),
            "tp": self._native_number(preparation.take_profit),
            "deviation": self.deviation_request_points,
            "magic": self.executor.MAGIC_NUMBER,
            "comment": f"AI_Bot_{record.trade_id[:8]}",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        return request

    @guarded
    def authorize_trade(self, preparation, record, *, confidence, is_trending=False):
        """Run fresh risk, broker P/L, margin and order_check; issue only then."""
        if self._risk_agent is None or not isinstance(preparation, QuotePreparation):
            raise GatewayError("A prepared quote and bound RiskAgent are required")
        with self._lock:
            stored = self._preparations.pop(preparation.preparation_id, None)
        if (stored is None or stored[0] is not preparation
                or stored[1] != self._preparation_fingerprint(preparation)):
            raise GatewayError("Quote preparation is foreign, mutated or already consumed")
        approval_started = preparation.acquired_monotonic
        self._check_elapsed(approval_started)
        age = self.clock.monotonic() - approval_started
        if not math.isfinite(age) or age < 0 or age > self.approval_ttl:
            raise GatewayError("Quote preparation expired before final risk check")
        if (record.candidate_id != preparation.candidate_id or record.strategy_id != preparation.strategy_id
                or record.evidence_digest != preparation.evidence_digest
                or record.contract_revision != preparation.instrument.revision
                or self.executor.symbol_registry.canonical(record.pair) != preparation.pair
                or record.direction != preparation.direction):
            raise GatewayError("Trade record does not match the prepared candidate")
        risk_result = self._risk_agent.evaluate_trade(
            pair=preparation.pair, direction=preparation.direction,
            entry_price=preparation.entry_price, stop_loss=preparation.stop_loss,
            take_profit=preparation.take_profit, confidence=confidence,
            equity=self.executor.get_account_equity(), is_trending=is_trending,
            instrument_snapshot=preparation.instrument,
        )
        if not risk_result.approved or not risk_result.sizing:
            return GatewayAuthorization(False, None, risk_result, None, {}, risk_result.reason)

        try:
            if self.clock.monotonic() - approval_started > self.approval_ttl:
                raise GatewayError("Quote preparation expired during final risk check")
            self._validate_quote_again(preparation)
            spec = preparation.instrument
            action = self.mt5.ORDER_TYPE_BUY if preparation.direction == "BUY" else self.mt5.ORDER_TYPE_SELL
            self.executor.assert_demo_session()
            profit_one = self.mt5.order_calc_profit(
                action, spec.broker_symbol, 1.0, float(preparation.entry_price), float(preparation.stop_loss))
            profit_one = decimal_value(profit_one, "one-lot stop P/L")
            if profit_one >= 0:
                raise GatewayError("Broker P/L calculator did not report an adverse stop loss")
            budget = self._risk_decimal(risk_result.sizing["risk_budget"], "risk budget")
            allowance = self._risk_decimal(risk_result.sizing["cost_allowance_per_lot"], "cost allowance")
            if budget <= 0 or allowance < 0:
                raise GatewayError("Invalid monetary risk budget or cost allowance")
            if risk_result.sizing.get("account_currency") != spec.account_currency:
                raise GatewayError("Risk budget currency differs from broker account currency")
            per_lot_loss = abs(profit_one) + allowance
            step, minimum = spec.volume_step, spec.volume_min
            broker_raw = budget / per_lot_loss
            broker_floored = (broker_raw / step).to_integral_value(rounding=ROUND_FLOOR) * step
            risk_volume = decimal_value(risk_result.adjusted_lot_size, "RiskAgent volume")
            volume = min(broker_floored, risk_volume, spec.volume_max)
            if spec.volume_limit > 0:
                volume = min(volume, spec.volume_limit)
            volume = (volume / step).to_integral_value(rounding=ROUND_FLOOR) * step
            if volume < minimum:
                raise GatewayError("Broker P/L sizing is below broker minimum volume")
            self.executor.assert_demo_session()
            profit_final = self.mt5.order_calc_profit(
                action, spec.broker_symbol, float(volume), float(preparation.entry_price), float(preparation.stop_loss))
            profit_final = decimal_value(profit_final, "final-volume stop P/L")
            final_loss = abs(profit_final) + allowance * volume
            if profit_final >= 0 or final_loss > budget:
                raise GatewayError("Final broker-calculated stop loss exceeds risk budget")

            adjusted = replace(
                record, pair=preparation.pair, direction=preparation.direction,
                entry_price=float(preparation.entry_price), stop_loss=float(preparation.stop_loss),
                take_profit=float(preparation.take_profit), lot_size=float(volume),
            )
            request = self._request(preparation, adjusted, volume)
            self.executor.assert_demo_session()
            margin = decimal_value(self.mt5.order_calc_margin(
                action, spec.broker_symbol, float(volume), float(preparation.entry_price)), "required margin")
            account = self.executor.assert_demo_session()
            free_margin = decimal_value(getattr(account, "margin_free", None), "free margin")
            if margin < 0 or free_margin < 0 or margin > free_margin:
                raise GatewayError("Insufficient or invalid free margin")
            request_before = self._fingerprint(request)
            checked_request = dict(request)
            checked = self.mt5.order_check(checked_request)
            if (checked is None or type(getattr(checked, "retcode", None)) is not int
                    or checked.retcode != 0 or self._fingerprint(checked_request) != request_before):
                raise GatewayError("Broker rejected the exact pre-trade request check")

            # Re-read account, contract and quote after potentially slow native checks.
            current_account, identity, current_spec, bid, ask, quote_time, acquired = self._read_quote(preparation.pair)
            if identity != preparation.account_identity or current_spec.revision != spec.revision:
                raise GatewayError("Account or contract changed during approval")
            if bid != preparation.bid or ask != preparation.ask:
                raise GatewayError("Quote changed during approval; fresh analysis required")
            sized_equity = self._risk_decimal(risk_result.sizing["equity"], "sized equity")
            if decimal_value(getattr(current_account, "equity", None), "current equity") != sized_equity:
                raise GatewayError("Equity changed during approval; fresh risk calculation required")
            if decimal_value(getattr(current_account, "margin_free", None), "current free margin") != free_margin:
                raise GatewayError("Free margin changed during approval")
            self._validate_permissions(current_account, current_spec, preparation.direction)
            self._check_elapsed(approval_started)
            if (self.clock.monotonic() - approval_started) > self.approval_ttl:
                raise GatewayError("Pre-trade calculations exceeded approval TTL")

            sizing = dict(risk_result.sizing)
            sizing.update({
                "riskagent_volume": str(risk_volume), "broker_raw_volume": str(broker_raw),
                "volume": str(volume), "broker_stop_loss_per_lot": str(abs(profit_one)),
                "estimated_total_loss": str(final_loss), "margin_required": str(margin),
                "free_margin": str(free_margin), "quote_time": quote_time.isoformat(),
            })
            adjusted = replace(adjusted, sizing_provenance=sizing)
            risk_result = replace(risk_result, adjusted_lot_size=float(volume), sizing=sizing)
            token = secrets.token_urlsafe(32)
            record_digest = self._fingerprint(self._record_data(adjusted))
            request_digest = self._fingerprint(request)
            with self._lock:
                self._approvals[token] = {
                    "request": dict(request), "request_digest": request_digest,
                    "record_digest": record_digest, "record": adjusted,
                    "preparation": preparation, "issued": approval_started,
                    "account_identity": identity, "revision": spec.revision,
                    "risk_budget": str(budget), "sized_equity": str(sized_equity),
                    "margin_required": str(margin),
                    "free_margin": str(free_margin),
                }
            audit = {key: sizing[key] for key in (
                "account_currency", "contract_revision", "risk_budget", "estimated_total_loss",
                "volume", "margin_required", "free_margin", "quote_time")}
            return GatewayAuthorization(True, adjusted, risk_result, token, audit, "Approved")
        except GatewayError:
            raise
        except (ModeError, SizingError, TypeError, ValueError, AttributeError, ArithmeticError) as error:
            raise GatewayError(f"Pre-trade broker validation failed: {error}") from error
        except Exception as error:
            raise GatewayError("Pre-trade broker check failed; no order submitted") from error

    @staticmethod
    def _record_data(record):
        return {name: getattr(record, name) for name in (
            "trade_id", "pair", "direction", "entry_price", "stop_loss", "take_profit",
            "lot_size", "candidate_id", "strategy_id", "contract_revision", "evidence_digest",
            "sizing_provenance")}

    def _validate_quote_again(self, preparation):
        account, identity, spec, bid, ask, quote_time, acquired = self._read_quote(preparation.pair)
        if identity != preparation.account_identity or spec.revision != preparation.instrument.revision:
            raise GatewayError("Account or contract changed after approval")
        if bid != preparation.bid or ask != preparation.ask:
            raise GatewayError("Quote changed after approval")
        self._validate_permissions(account, spec, preparation.direction)
        return spec

    @guarded
    def submit_entry(self, record, token):
        """Consume authority before any final check; at most one send attempt."""
        with self._lock:
            approval = self._approvals.pop(token, None) if isinstance(token, str) else None
        if approval is None:
            raise GatewayError("Missing, foreign, expired or already consumed gateway approval")
        self._check_elapsed(approval["issued"])
        if self.clock.monotonic() - approval["issued"] > self.approval_ttl:
            raise GatewayError("Gateway approval expired")
        if self._fingerprint(self._record_data(record)) != approval["record_digest"]:
            raise GatewayError("Trade record changed after gateway approval")
        rebuilt = self._request(approval["preparation"], record, decimal_value(record.lot_size, "volume"))
        if self._fingerprint(rebuilt) != approval["request_digest"]:
            raise GatewayError("Exact approved order request changed")
        request = approval["request"]
        spec = self._validate_quote_again(approval["preparation"])
        account = self.executor.assert_demo_session()
        if self._account_identity(account) != approval["account_identity"]:
            raise GatewayError("Account identity changed immediately before send")
        if spec.revision != approval["revision"]:
            raise GatewayError("Contract revision changed immediately before send")
        if self.clock.monotonic() - approval["issued"] > self.approval_ttl:
            raise GatewayError("Gateway approval expired before send")
        permit = object()
        self._native_permits[permit] = ("entry", approval["request_digest"], approval)
        try:
            result = self.executor._send_demo_request(
                request, contract_revision=spec.revision, gateway_permit=permit)
        finally:
            self._native_permits.pop(permit, None)
        if result is None:
            return {"success": False, "ticket": None,
                    "reason": "Ambiguous order_send result; approval consumed and no retry allowed",
                    "mode": "DEMO_MT5"}
        if getattr(result, "retcode", None) != self.mt5.TRADE_RETCODE_DONE:
            return {"success": False, "ticket": None,
                    "reason": f"Order rejected (retcode={getattr(result, 'retcode', None)}); approval consumed",
                    "mode": "DEMO_MT5"}
        return {"success": True, "ticket": result.order,
                "reason": "Gateway-approved demo order placed", "mode": "DEMO_MT5"}

    def validates_permit(self, permit, request):
        return self._valid_permit(permit, request, "entry")

    def validates_close_permit(self, permit, request):
        return self._valid_permit(permit, request, "close")

    def _valid_permit(self, permit, request, kind):
        with self._lock:
            if type(permit) is not object:
                return False
            stored = self._native_permits.get(permit)
            return bool(stored and stored[0] == kind and stored[1] == self._fingerprint(request))

    @guarded
    def final_send_check(self, permit, request, current_spec):
        stored = self._native_permits.pop(permit, None) if type(permit) is object else None
        if stored is None or stored[1] != self._fingerprint(request):
            raise GatewayError("Native send has no valid unconsumed gateway permit")
        kind, _, detail = stored
        self._check_elapsed(detail["issued"])
        if kind == "close":
            self._check_position(detail)
            self._check_close_context(detail)
            if current_spec.revision != detail["revision"]:
                raise GatewayError("Contract changed before close")
            return
        approval = detail
        if self.clock.monotonic() - approval["issued"] > self.approval_ttl:
            raise GatewayError("Gateway approval expired before native send")
        if current_spec.revision != approval["revision"]:
            raise GatewayError("Contract revision changed before native send")
        account, identity, spec, bid, ask, quote_time, acquired = self._read_quote(
            approval["preparation"].pair)
        if identity != approval["account_identity"] or spec.revision != approval["revision"]:
            raise GatewayError("Account or contract changed at native send boundary")
        if bid != approval["preparation"].bid or ask != approval["preparation"].ask:
            raise GatewayError("Quote changed at native send boundary")
        self._validate_permissions(account, spec, approval["preparation"].direction)
        if decimal_value(getattr(account, "equity", None), "current equity") != self._risk_decimal(approval["sized_equity"], "sized equity"):
            raise GatewayError("Equity changed before native send")
        free_margin = decimal_value(getattr(account, "margin_free", None), "free margin")
        if (free_margin != self._risk_decimal(approval["free_margin"], "approved free margin")
                or free_margin < self._risk_decimal(approval["margin_required"], "required margin")):
            raise GatewayError("Free margin changed before native send")
        self._check_elapsed(approval["issued"])

    def _check_position(self, detail):
        positions = self.mt5.positions_get(ticket=detail["ticket"])
        if positions is None or len(positions) != 1:
            raise GatewayError("Position changed before close send")
        position = positions[0]
        if (type(getattr(position, "ticket", None)) is not int or position.ticket != detail["ticket"]
                or getattr(position, "symbol", None) != detail["symbol"]
                or type(getattr(position, "type", None)) is not int or position.type != detail["type"]
                or decimal_value(getattr(position, "volume", None), "position volume") < detail["volume"]):
            raise GatewayError("Close no longer reduces the same native position")

    def _check_close_context(self, detail):
        account, identity, spec, bid, ask, _, _ = self._read_quote(detail["pair"])
        if (identity != detail["identity"] or spec.revision != detail["revision"]
                or bid != detail["bid"] or ask != detail["ask"]):
            raise GatewayError("Close account, contract or quote changed before send")
        self._validate_permissions(account, spec, detail["direction"], closing=True)
        self._check_elapsed(detail["issued"])

    @guarded
    def close_position(self, ticket, pair, direction, volume):
        """Validate a ticket-backed reduction; no caller-created `position` bypass."""
        started = self.clock.monotonic()
        if type(ticket) is not int or ticket <= 0 or direction not in ("BUY", "SELL"):
            raise GatewayError("Invalid close position identity")
        canonical = self.executor.symbol_registry.canonical(pair)
        requested_volume = decimal_value(volume, "close volume")
        account = self.executor.assert_demo_session()
        initial_identity = self._account_identity(account)
        if getattr(account, "trade_allowed", None) is not True:
            raise GatewayError("Account trading permission is disabled")
        positions = self.mt5.positions_get(ticket=ticket)
        if positions is None or len(positions) != 1:
            raise GatewayError("Native position ticket is unavailable or ambiguous")
        position = positions[0]
        if self._account_identity(self.executor.assert_demo_session()) != initial_identity:
            raise GatewayError("Account changed while reading close position")
        spec = self.executor.get_instrument_spec(canonical)
        raw_symbol = spec.broker_symbol
        native_type = getattr(position, "type", None)
        if type(native_type) is not int or native_type not in (self.mt5.POSITION_TYPE_BUY, self.mt5.POSITION_TYPE_SELL):
            raise GatewayError("Unknown native position side")
        native_direction = "BUY" if native_type == self.mt5.POSITION_TYPE_BUY else "SELL"
        current_volume = decimal_value(getattr(position, "volume", None), "position volume")
        if (type(getattr(position, "ticket", None)) is not int or position.ticket != ticket or getattr(position, "symbol", None) != raw_symbol
                or self.executor.symbol_registry.from_broker(raw_symbol) != canonical
                or native_direction != direction or current_volume <= 0):
            raise GatewayError("Close request does not match native position")
        if (requested_volume <= 0 or requested_volume > current_volume
                or requested_volume % spec.volume_step):
            raise GatewayError("Close volume must be positive, stepped and no larger than the position")
        close_direction = "SELL" if direction == "BUY" else "BUY"
        try:
            account, identity, spec, bid, ask, quote_time, acquired = self._read_quote(canonical)
            if identity != initial_identity:
                raise GatewayError("Account changed before close preparation")
            self._validate_permissions(account, spec, close_direction, closing=True)
            price = bid if close_direction == "SELL" else ask
            if price % spec.trade_tick_size or requested_volume > spec.volume_max or requested_volume < spec.volume_min:
                raise GatewayError("Close price or volume violates contract grid/bounds")
            action = self.mt5.ORDER_TYPE_SELL if close_direction == "SELL" else self.mt5.ORDER_TYPE_BUY
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL, "symbol": raw_symbol,
                "volume": self._native_number(requested_volume), "type": action, "position": ticket,
                "price": self._native_number(price), "deviation": self.deviation_request_points,
                "magic": self.executor.MAGIC_NUMBER, "comment": f"AI_Bot_Close_{ticket}",
                "type_time": self.mt5.ORDER_TIME_GTC, "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            checked_request = dict(request)
            checked = self.mt5.order_check(checked_request)
            if (checked is None or type(getattr(checked, "retcode", None)) is not int or checked.retcode != 0
                    or self._fingerprint(checked_request) != self._fingerprint(request)):
                raise GatewayError("Broker rejected protective close request check")
            # Re-fetch the position after slow order_check so close-only permission
            # cannot be used to reverse a changed/removed position.
            detail = {
                "ticket": ticket, "pair": canonical, "identity": identity,
                "revision": spec.revision, "symbol": raw_symbol, "type": native_type,
                "volume": requested_volume, "bid": bid, "ask": ask,
                "direction": close_direction, "issued": started,
            }
            self._check_position(detail)
            self._check_close_context(detail)
            permit = object()
            self._native_permits[permit] = ("close", self._fingerprint(request), detail)
            try:
                result = self.executor._send_demo_request(
                    request, contract_revision=spec.revision, gateway_permit=permit)
            finally:
                self._native_permits.pop(permit, None)
            if result is None or getattr(result, "retcode", None) != self.mt5.TRADE_RETCODE_DONE:
                return {"success": False, "ticket": None,
                        "reason": "Close was not confirmed; no retry allowed", "mode": "DEMO_MT5"}
            return {"success": True, "ticket": result.order,
                    "reason": f"Position {ticket} reduction sent", "mode": "DEMO_MT5"}
        except GatewayError:
            raise
        except (ModeError, SizingError, TypeError, ValueError, AttributeError, ArithmeticError) as error:
            raise GatewayError(f"Protective close validation failed: {error}") from error
