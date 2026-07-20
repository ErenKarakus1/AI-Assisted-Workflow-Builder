from app.engine.handlers.base import HandlerResult, NodeHandler
from app.models.workflow import WorkflowEdge, WorkflowNode


class EndNodeHandler(NodeHandler):
    async def execute(
        self,
        node: WorkflowNode,
        outgoing_edges: list[WorkflowEdge],
        context: dict,
        instance_input: dict,
    ) -> HandlerResult:
        result = node.data.get("result", "completed")
        return HandlerResult(context_updates={"result": result}, event_data={"result": result})

