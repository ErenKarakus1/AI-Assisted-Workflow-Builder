from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowInstanceStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


class InstanceEventType(StrEnum):
    INSTANCE_STARTED = "instance_started"
    NODE_ENTERED = "node_entered"
    CONDITION_EVALUATED = "condition_evaluated"
    INSTANCE_COMPLETED = "instance_completed"
    INSTANCE_FAILED = "instance_failed"


class WorkflowInstance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    organization_id: str
    workflow_id: str
    workflow_revision: int
    status: WorkflowInstanceStatus = WorkflowInstanceStatus.RUNNING
    active_node_id: str | None = None
    context: dict = Field(default_factory=dict)
    input: dict = Field(default_factory=dict)
    revision: int = 1
    started_by_user_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class InstanceEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    organization_id: str
    instance_id: str
    workflow_id: str
    type: InstanceEventType
    node_id: str | None = None
    data: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

