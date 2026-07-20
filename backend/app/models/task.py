from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class TaskDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    organization_id: str
    workflow_id: str
    instance_id: str
    node_id: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_user_id: str | None = None
    assigned_role: str | None = None
    decision: TaskDecision | None = None
    completed_by_user_id: str | None = None
    revision: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
