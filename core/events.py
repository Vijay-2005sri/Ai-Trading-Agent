"""Transport-neutral event envelopes; deliberately no publish/execute callbacks."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import Field, UUID4, field_validator

from config.execution_mode import ExecutionMode
from core.models import VersionedRecord, checked_payload


class EventEnvelope(VersionedRecord):
    event_id: UUID4 = Field(default_factory=uuid4)
    event_type: str = Field(pattern=r"^[A-Z][A-Za-z0-9]{0,99}$")
    source: str = Field(min_length=1, max_length=100, pattern=r"\S")
    run_id: UUID4
    proposal_id: UUID4 | None = None
    intent_id: UUID4 | None = None
    causation_id: UUID4 | None = None
    mode: ExecutionMode
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload", mode="before")
    @classmethod
    def validate_payload(cls, value):
        return checked_payload(value)


class RecordedEvent(VersionedRecord):
    sequence: int = Field(gt=0)
    source_sequence: int = Field(gt=0)
    recorded_at: datetime
    event: EventEnvelope
