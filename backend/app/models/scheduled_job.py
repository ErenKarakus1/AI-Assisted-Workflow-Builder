from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ScheduledJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduledJobType(StrEnum):
    DELAY = "delay"


class ScheduledJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    organization_id: str
    workflow_id: str
    instance_id: str
    node_id: str
    type: ScheduledJobType
    status: ScheduledJobStatus = ScheduledJobStatus.PENDING
    run_at: datetime
    locked_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 0
    revision: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
