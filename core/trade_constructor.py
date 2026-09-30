"""Selected candidate binding and geometry; no sizing or broker authority."""

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
import math
from numbers import Real, Integral
from uuid import UUID

from pydantic import ValidationError

from broker_mt5.instruments import InstrumentSnapshot
from broker_mt5.symbols import SymbolRegistry
from core.models import CandidateContext, TradeCandidate, ConstructedTrade, checked_payload


class ConstructionError(ValueError):
    pass


def decimal_price(value):
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)) or not math.isfinite(value):
        raise ConstructionError("Price must be a finite number")
    return Decimal(str(value))


def candidate_from_signal(signal, allowed_strategies):
    try:
        if SymbolRegistry().canonical(signal["pair"]) != signal["pair"]:
            raise ConstructionError("Candidate pair must be canonical")
        if signal["strategy"] not in allowed_strategies:
            raise ConstructionError("Unregistered candidate strategy")
        confidence = signal["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, Integral):
            raise ConstructionError("Signal confidence must be an integer")
        return TradeCandidate(
            candidate_id=UUID(str(signal["candidate_id"])), pair=signal["pair"],
            variant_label=signal.get("signal_label", signal["strategy"]),
            strategy=signal["strategy"], direction=signal["direction"],
            entry_price=decimal_price(signal["entry_price"]), stop_loss=decimal_price(signal["stop_loss"]),
            take_profit=decimal_price(signal["take_profit"]), confidence=int(confidence),
            reasoning=signal["reasoning"], timestamp=signal["timestamp"])
    except (KeyError, TypeError, ValueError, ArithmeticError) as error:
        raise ConstructionError("Invalid selected strategy candidate") from error


def evidence_json(trade_recall, news_recall, actual_win_rate):
    data = checked_payload(dict(trade_recall=trade_recall, news_recall=news_recall,
                                actual_win_rate=actual_win_rate))
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def bind_context(signal, trade_recall, news_recall, actual_win_rate, allowed_strategies):
    candidate = (TradeCandidate.model_validate(signal.model_dump()) if isinstance(signal, TradeCandidate)
                 else candidate_from_signal(signal, allowed_strategies))
    if candidate.strategy not in allowed_strategies:
        raise ConstructionError("Unregistered selected strategy")
    return CandidateContext(candidate=candidate,
                            evidence_json=evidence_json(trade_recall, news_recall, actual_win_rate))


def validate_binding(context, decision, selected, signals, evidence, allowed_strategies):
    try:
        decision = type(decision).model_validate(decision.model_dump())
        if not isinstance(context, CandidateContext):
            raise ConstructionError("No frozen candidate context")
        candidate = TradeCandidate.model_validate(context.candidate.model_dump())
        if candidate != candidate_from_signal(selected, allowed_strategies):
            raise ConstructionError("Selected candidate changed after analysis binding")
        matches = [s for s in signals if str(s.get("candidate_id")) == str(candidate.candidate_id)]
        if len(matches) != 1 or candidate != candidate_from_signal(matches[0], allowed_strategies):
            raise ConstructionError("Candidate missing, duplicated or changed in signal set")
        if evidence != context.evidence_json:
            raise ConstructionError("Evidence changed after candidate binding")
        if (decision.action != candidate.direction or decision.pair != candidate.pair
                or decision.strategy_used != candidate.strategy
                or str(decision.candidate_id) != str(candidate.candidate_id)):
            raise ConstructionError("Decision does not match selected candidate ID/strategy/side/pair")
        return candidate
    except (AttributeError, ValidationError, TypeError, KeyError) as error:
        raise ConstructionError("Malformed candidate binding") from error


def construct_trade(context, spec, *, minimum_rr):
    try:
        candidate = TradeCandidate.model_validate(context.candidate.model_dump())
        spec = InstrumentSnapshot.model_validate(spec.model_dump())
        if candidate.pair != spec.instrument_id:
            raise ConstructionError("Contract metadata belongs to another instrument")
        tick = spec.trade_tick_size
        buy = candidate.direction == "BUY"
        def rounded(value, up):
            return (value / tick).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR) * tick
        entry = rounded(candidate.entry_price, buy)
        stop = rounded(candidate.stop_loss, not buy)
        target = rounded(candidate.take_profit, not buy)
        if not (stop < entry < target if buy else target < entry < stop) or min(entry, stop, target) <= 0:
            raise ConstructionError("Tick rounding collapsed trade geometry")
        ratio = abs(target - entry) / abs(entry - stop)
        minimum = decimal_price(minimum_rr)
        if minimum <= 0 or ratio < minimum:
            raise ConstructionError("Constructed trade fails minimum risk/reward")
        return ConstructedTrade(candidate_id=candidate.candidate_id, pair=candidate.pair,
                                strategy=candidate.strategy, direction=candidate.direction,
                                entry_price=entry, stop_loss=stop, take_profit=target, risk_reward=ratio,
                                contract_revision=spec.revision,
                                evidence_digest=hashlib.sha256(context.evidence_json.encode()).hexdigest())
    except (AttributeError, ValidationError, ArithmeticError) as error:
        raise ConstructionError("Trade construction failed") from error
