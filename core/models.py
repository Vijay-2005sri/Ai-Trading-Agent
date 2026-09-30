"""Versioned metadata. These records confer no trading/execution authority."""

from datetime import datetime
from decimal import Decimal
import json
import math
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator, model_validator

from config.execution_mode import ExecutionMode
from core.time_service import as_utc


def finite_json(value, depth=0):
    if depth > 16:
        raise ValueError("JSON exceeds maximum nesting depth 16")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            finite_json(item, depth + 1)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            finite_json(item, depth + 1)
        return
    raise ValueError("Payload must be finite JSON with string object keys")


def checked_payload(value):
    if type(value) is not dict:
        raise ValueError("Payload must be a JSON object")
    finite_json(value)
    if len(json.dumps(value, allow_nan=False, ensure_ascii=False).encode("utf-8")) > 65536:
        raise ValueError("Payload exceeds 64 KiB")
    return value


class VersionedRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, allow_inf_nan=False,
                              validate_default=True)
    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Only schema version 1 is supported")
        return value

    @field_validator("created_at", "expires_at", "market_snapshot_at", "occurred_at",
                     "recorded_at", check_fields=False)
    @classmethod
    def aware_utc(cls, value):
        return as_utc(value) if value is not None else None


class RunRecord(VersionedRecord):
    run_id: UUID4 = Field(default_factory=uuid4)
    mode: ExecutionMode
    purpose: str = Field(min_length=1, max_length=100, pattern=r"\S")
    created_at: datetime
    expires_at: datetime | None = None
    market_snapshot_at: datetime | None = None

    @model_validator(mode="after")
    def timestamps(self):
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("Run expiry must follow creation")
        if self.market_snapshot_at is not None and self.market_snapshot_at > self.created_at:
            raise ValueError("Market snapshot cannot postdate run creation")
        return self


class OrderIntent(VersionedRecord):
    """Immutable draft request snapshot; not a ValidatedTrade or send capability."""
    intent_id: UUID4 = Field(default_factory=uuid4)
    run_id: UUID4
    proposal_id: UUID4
    mode: ExecutionMode
    created_at: datetime
    instrument_id: str = Field(min_length=1, max_length=100, pattern=r"\S")
    direction: Literal["BUY", "SELL"]
    request: dict[str, Any]

    @field_validator("request", mode="before")
    @classmethod
    def validate_request(cls, value):
        return checked_payload(value)


class TradeCandidate(VersionedRecord):
    candidate_id: UUID4
    pair: str = Field(min_length=1, max_length=32)
    strategy: str = Field(min_length=1, max_length=100)
    variant_label: str = Field(default="", max_length=100)
    direction: Literal["BUY", "SELL"]
    entry_price: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    take_profit: Decimal = Field(gt=0)
    confidence: int = Field(ge=0, le=100)
    reasoning: str = Field(min_length=1, max_length=4000)
    timestamp: str = Field(min_length=1, max_length=100)  # Original label; timezone migration is 3.1.

    @model_validator(mode="after")
    def geometry(self):
        if not (self.stop_loss < self.entry_price < self.take_profit if self.direction == "BUY"
                else self.take_profit < self.entry_price < self.stop_loss):
            raise ValueError("Invalid candidate SL/entry/TP geometry")
        return self


class CandidateContext(VersionedRecord):
    candidate: TradeCandidate
    evidence_json: str  # Canonical serialized snapshot, no nested mutable dicts.


class ConstructedTrade(VersionedRecord):
    candidate_id: UUID4
    pair: str
    strategy: str
    direction: Literal["BUY", "SELL"]
    entry_price: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    take_profit: Decimal = Field(gt=0)
    risk_reward: Decimal = Field(gt=0)
    contract_revision: str
    evidence_digest: str
