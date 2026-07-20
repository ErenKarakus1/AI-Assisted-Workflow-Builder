from app.engine.handlers.base import HandlerResult, NodeHandler
from app.models.workflow import WorkflowEdge, WorkflowNode


class StartNodeHandler(NodeHandler):
    async def execute(
        self,
        node: WorkflowNode,
        outgoing_edges: list[WorkflowEdge],
        context: dict,
        instance_input: dict,
    ) -> HandlerResult:
        return HandlerResult(next_node_id=outgoing_edges[0].target)

