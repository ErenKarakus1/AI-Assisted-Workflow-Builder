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


class TaskDecisionRequest(BaseModel):
    revision: int = Field(ge=1)
