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


class WorkflowValidationIssue(BaseModel):
    code: str
    message: str
    node_id: str | None = None
    edge_id: str | None = None


class WorkflowValidationResult(BaseModel):
    is_valid: bool
    errors: list[WorkflowValidationIssue] = Field(default_factory=list)
    warnings: list[WorkflowValidationIssue] = Field(default_factory=list)
