from pydantic import BaseModel, Field

from app.models.instance import InstanceEventType, WorkflowInstanceStatus


class WorkflowInstanceCreate(BaseModel):
    input: dict = Field(default_factory=dict)


class WorkflowInstanceRead(BaseModel):
    id: str
    organization_id: str
    workflow_id: str
    workflow_revision: int
    status: WorkflowInstanceStatus
    active_node_id: str | None
    context: dict
    input: dict
    revision: int


class InstanceEventRead(BaseModel):
    id: str
    organization_id: str
    instance_id: str
    workflow_id: str
    type: InstanceEventType
    node_id: str | None
    data: dict

