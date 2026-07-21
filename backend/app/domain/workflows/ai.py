import json

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.domain.workflows.validation import WorkflowValidator
from app.models.workflow import Workflow, WorkflowEdge, WorkflowNode
from app.schemas.workflow import WorkflowAIGenerateResponse


class AIConfigurationError(Exception):
    pass


class AIGenerationError(Exception):
    pass


class GeneratedWorkflowGraph(BaseModel):
    accepted: bool = True
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    explanation: str = Field(min_length=1, max_length=1000)


class WorkflowAIService:
    async def generate_graph(self, workflow: Workflow, prompt: str) -> WorkflowAIGenerateResponse:
        if not settings.openai_api_key:
            raise AIConfigurationError

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        try:
            response = await client.responses.create(
                model=settings.openai_model,
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": system_prompt()}]},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": json.dumps(
                                    {
                                        "workflow_name": workflow.name,
                                        "current_nodes": [node.model_dump() for node in workflow.nodes],
                                        "current_edges": [edge.model_dump() for edge in workflow.edges],
                                        "request": prompt,
                                    }
                                ),
                            }
                        ],
                    },
                ],
                text={"format": {"type": "json_object"}},
            )
        except OpenAIError as exc:
            raise AIGenerationError from exc

        content = response.output_text
        if not content:
            raise AIGenerationError

        try:
            generated = GeneratedWorkflowGraph.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            raise AIGenerationError from exc

        if not generated.accepted:
            return WorkflowAIGenerateResponse(
                accepted=False,
                nodes=[],
                edges=[],
                explanation=generated.explanation,
                validation=WorkflowValidator().validate(workflow),
            )
        if len(generated.nodes) < 2:
            raise AIGenerationError

        draft = workflow.model_copy(
            update={
                "nodes": generated.nodes,
                "edges": generated.edges,
            }
        )
        validation = WorkflowValidator().validate(draft)
        return WorkflowAIGenerateResponse(
            accepted=True,
            nodes=generated.nodes,
            edges=generated.edges,
            explanation=generated.explanation,
            validation=validation,
        )


def system_prompt() -> str:
    return """
You generate workflow graphs for an AI-assisted workflow builder.
Return JSON only with keys: accepted, nodes, edges, explanation.

If the user's request cannot be represented accurately with the supported node types and approval assignments, return:
{"accepted": false, "nodes": [], "edges": [], "explanation": "Clear reason and what the user can choose instead."}
Do not generate a graph that intentionally changes a user's explicit approval assignment.
Do not refuse normal multi-step workflows. Multiple approvals, conditions after approvals, approvals after rejection paths, and several end nodes are supported.
Ignore existing current_nodes/current_edges unless the user explicitly asks to modify or preserve them; otherwise create a fresh graph for the request.
If wording says "if approved" or "if rejected/if no" near an approval node, interpret that as the approval node's approve/reject edge.
If wording says "if yes" or "if no" near a condition, interpret that as the condition node's true/false edge.
Ask for clarification only when there are multiple materially different valid graphs and no reasonable interpretation.
Match approval roles exactly. If the user says "owner approval" or "ask owner", use assigned_role="owner". If the user says "admin approval", use assigned_role="admin". If the user says "member approval", use assigned_role="member". Use assigned_role="owner_or_admin" only when the user explicitly says owner or admin, owner/admin, admins or owners, or equivalent. Never broaden a single requested role into a group.

Supported node types:
- start: exactly one, no incoming edges. Data: {"label": string}.
- condition: branches based on input/context. Data: {"label": string, "condition": {"field": "input.someField", "operator": one of ["equals","not_equals","greater_than","greater_than_or_equal","less_than","less_than_or_equal","contains"], "value": string/number/bool}}. Must have outgoing edge labels "true" and "false".
- approval: human approval. Data: {"label": string, "assigned_role": one of ["owner","admin","member","owner_or_admin","all"]}. Use "owner_or_admin" only for owner/admin approval. Use "all" when any org member may approve. Do not substitute a different role group when the user explicitly excludes a role. If the user asks for an unsupported role combination, return accepted=false instead of choosing a closest role. Must have outgoing edge labels "approve" and "reject".
- delay: wait before continuing. Data: {"label": string, "seconds": non-negative integer}.
- end: terminal result. Data: {"label": string, "result": string}.

Graph rules:
- Use stable lowercase IDs like start-1, approval-1, end-approved.
- Every edge has id, source, target, label, data.
- Use null labels except condition/approval branches.
- Every node has id, type, position with x/y numbers, and data.
- Keep graphs small and understandable.
- Prefer a valid graph over a clever graph.
- For a request like "start with owner approval; if owner approves, accept; if owner rejects, check amount >= 15000; if false reject; if true ask admin approval; if approved accept; if rejected reject", generate exactly that chain.
""".strip()
