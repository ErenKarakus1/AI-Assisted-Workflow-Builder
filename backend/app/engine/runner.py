from collections import defaultdict
from datetime import UTC, datetime

from app.engine.handlers.base import HandlerResult, NodeHandler
from app.engine.handlers.condition import ConditionNodeHandler
from app.engine.handlers.end import EndNodeHandler
from app.engine.handlers.start import StartNodeHandler
from app.models.instance import InstanceEvent, InstanceEventType, WorkflowInstance, WorkflowInstanceStatus
from app.models.task import Task
from app.models.workflow import Workflow, WorkflowEdge, WorkflowNode


class WorkflowExecutionError(Exception):
    pass


class WorkflowEngine:
    def __init__(self, created_tasks: list[Task] | None = None) -> None:
        self.created_tasks = created_tasks if created_tasks is not None else []
        self.handlers: dict[str, NodeHandler] = {
            "start": StartNodeHandler(),
            "condition": ConditionNodeHandler(),
            "end": EndNodeHandler(),
        }

    async def run(
        self,
        workflow: Workflow,
        instance: WorkflowInstance,
        starting_node_id: str | None = None,
    ) -> list[InstanceEvent]:
        events: list[InstanceEvent] = []
        nodes_by_id = {node.id: node for node in workflow.nodes}
        outgoing = self._outgoing_edges(workflow.edges)

        if starting_node_id is None:
            start_node = next(node for node in workflow.nodes if node.type == "start")
            instance.active_node_id = start_node.id
            events.append(self._event(workflow, instance, InstanceEventType.INSTANCE_STARTED))
        else:
            instance.active_node_id = starting_node_id

        try:
            while instance.status == WorkflowInstanceStatus.RUNNING and instance.active_node_id:
                node = nodes_by_id[instance.active_node_id]
                events.append(self._event(workflow, instance, InstanceEventType.NODE_ENTERED, node_id=node.id))
                if node.type == "approval":
                    task = Task(
                        organization_id=workflow.organization_id,
                        workflow_id=workflow.id,
                        instance_id=instance.id,
                        node_id=node.id,
                        assigned_user_id=node.data.get("assigned_user_id"),
                        assigned_role=node.data.get("assigned_role"),
                    )
                    self.created_tasks.append(task)
                    instance.status = WorkflowInstanceStatus.WAITING
                    events.append(
                        self._event(
                            workflow,
                            instance,
                            InstanceEventType.TASK_CREATED,
                            node_id=node.id,
                            data={"task_id": task.id},
                        )
                    )
                    instance.revision += 1
                    break

                result = await self._execute_node(node, outgoing[node.id], instance)
                self._apply_result(instance, result)

                if node.type == "condition":
                    events.append(
                        self._event(
                            workflow,
                            instance,
                            InstanceEventType.CONDITION_EVALUATED,
                            node_id=node.id,
                            data=result.event_data or {},
                        )
                    )

                if node.type == "end":
                    instance.status = WorkflowInstanceStatus.COMPLETED
                    instance.active_node_id = None
                    instance.completed_at = datetime.now(UTC)
                    events.append(
                        self._event(
                            workflow,
                            instance,
                            InstanceEventType.INSTANCE_COMPLETED,
                            node_id=node.id,
                            data=result.event_data or {},
                        )
                    )
                else:
                    instance.active_node_id = result.next_node_id

                instance.revision += 1
        except Exception as exc:
            instance.status = WorkflowInstanceStatus.FAILED
            instance.active_node_id = None
            instance.revision += 1
            events.append(
                self._event(
                    workflow,
                    instance,
                    InstanceEventType.INSTANCE_FAILED,
                    data={"error": str(exc)},
                )
            )

        return events

    async def resume_from_decision(
        self,
        workflow: Workflow,
        instance: WorkflowInstance,
        approval_node_id: str,
        decision: str,
    ) -> list[InstanceEvent]:
        outgoing = self._outgoing_edges(workflow.edges)
        edge = next(edge for edge in outgoing[approval_node_id] if edge.label == decision)
        instance.status = WorkflowInstanceStatus.RUNNING
        instance.context[f"approval_{approval_node_id}"] = decision
        return await self.run(workflow, instance, starting_node_id=edge.target)

    async def _execute_node(
        self,
        node: WorkflowNode,
        outgoing_edges: list[WorkflowEdge],
        instance: WorkflowInstance,
    ) -> HandlerResult:
        handler = self.handlers.get(node.type)
        if handler is None:
            raise WorkflowExecutionError(f"Node type is not executable yet: {node.type}")
        return await handler.execute(node, outgoing_edges, instance.context, instance.input)

    def _apply_result(self, instance: WorkflowInstance, result: HandlerResult) -> None:
        if result.context_updates:
            instance.context.update(result.context_updates)

    def _event(
        self,
        workflow: Workflow,
        instance: WorkflowInstance,
        event_type: InstanceEventType,
        node_id: str | None = None,
        data: dict | None = None,
    ) -> InstanceEvent:
        return InstanceEvent(
            organization_id=workflow.organization_id,
            instance_id=instance.id,
            workflow_id=workflow.id,
            type=event_type,
            node_id=node_id,
            data=data or {},
        )

    def _outgoing_edges(self, edges: list[WorkflowEdge]) -> dict[str, list[WorkflowEdge]]:
        outgoing: dict[str, list[WorkflowEdge]] = defaultdict(list)
        for edge in edges:
            outgoing[edge.source].append(edge)
        return outgoing
