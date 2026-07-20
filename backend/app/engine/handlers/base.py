from dataclasses import dataclass

from app.models.workflow import WorkflowEdge, WorkflowNode


@dataclass(frozen=True)
class HandlerResult:
    next_node_id: str | None = None
    context_updates: dict | None = None
    event_data: dict | None = None


class NodeHandler:
    async def execute(
        self,
        node: WorkflowNode,
        outgoing_edges: list[WorkflowEdge],
        context: dict,
        instance_input: dict,
    ) -> HandlerResult:
        raise NotImplementedError

