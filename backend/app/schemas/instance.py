from pydantic import BaseModel, Field

from app.models.instance import InstanceEventType, WorkflowInstanceStatus
from app.models.workflow import WorkflowEdge, WorkflowNode


class WorkflowInstanceCreate(BaseModel):
    input: dict = Field(default_factory=dict)


class WorkflowInstanceRead(BaseModel):
    id: str
    organization_id: str
    workflow_id: str
    workflow_revision: int
    workflow_nodes: list[WorkflowNode]
    workflow_edges: list[WorkflowEdge]
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
