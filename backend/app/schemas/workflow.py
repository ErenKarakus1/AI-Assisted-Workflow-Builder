from pydantic import BaseModel, Field

from app.models.workflow import WorkflowEdge, WorkflowNode, WorkflowStatus


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    revision: int = Field(ge=1)


class WorkflowRead(BaseModel):
    id: str
    organization_id: str
    name: str
    status: WorkflowStatus
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    revision: int

