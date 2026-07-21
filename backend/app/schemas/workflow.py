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


class WorkflowAIGenerateRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=2000)
    use_current_graph: bool = False


class WorkflowAIGenerateResponse(BaseModel):
    accepted: bool = True
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    explanation: str
    validation: WorkflowValidationResult


class WorkflowAIAnalyzeRequest(BaseModel):
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    revision: int = Field(ge=1)


class WorkflowAIAnalyzeResponse(BaseModel):
    summary: str
    paths: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    validation: WorkflowValidationResult


class WorkflowAIStatusResponse(BaseModel):
    configured: bool
