from app.engine.conditions import evaluate_condition
from app.engine.handlers.base import HandlerResult, NodeHandler
from app.models.workflow import WorkflowEdge, WorkflowNode


class ConditionNodeHandler(NodeHandler):
    async def execute(
        self,
        node: WorkflowNode,
        outgoing_edges: list[WorkflowEdge],
        context: dict,
        instance_input: dict,
    ) -> HandlerResult:
        expression = node.data.get("condition", {})
        result = evaluate_condition(expression, {"input": instance_input, "context": context})
        branch = "true" if result else "false"
        next_edge = next(edge for edge in outgoing_edges if edge.label == branch)
        return HandlerResult(
            next_node_id=next_edge.target,
            context_updates={f"condition_{node.id}": result},
            event_data={"result": result, "branch": branch},
        )

