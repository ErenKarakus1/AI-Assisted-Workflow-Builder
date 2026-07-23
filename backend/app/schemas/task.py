from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import TaskDecision, TaskStatus


class TaskRead(BaseModel):
    id: str
    organization_id: str
    workflow_id: str
    instance_id: str
    node_id: str
    status: TaskStatus
    assigned_user_id: str | None
    assigned_role: str | None
    decision: TaskDecision | None
    completed_by_user_id: str | None
    revision: int
    created_at: datetime
    completed_at: datetime | None


class TaskDecisionRequest(BaseModel):
    revision: int = Field(ge=1)


class TaskPageRead(BaseModel):
    items: list[TaskRead]
    next_cursor: datetime | None
