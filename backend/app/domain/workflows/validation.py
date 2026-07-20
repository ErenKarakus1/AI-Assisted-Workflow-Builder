from collections import defaultdict, deque

from app.models.workflow import Workflow, WorkflowEdge, WorkflowNode
from app.schemas.workflow import WorkflowValidationIssue, WorkflowValidationResult

SUPPORTED_NODE_TYPES = {"start", "approval", "condition", "delay", "end"}
CONDITION_BRANCHES = {"true", "false"}
APPROVAL_OUTCOMES = {"approve", "reject"}
SUPPORTED_CONDITION_OPERATORS = {
    "equals",
    "not_equals",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "contains",
}


class WorkflowValidator:
    def validate(self, workflow: Workflow) -> WorkflowValidationResult:
        errors: list[WorkflowValidationIssue] = []
        warnings: list[WorkflowValidationIssue] = []

        node_ids = [node.id for node in workflow.nodes]
        node_id_set = set(node_ids)
        nodes_by_id = {node.id: node for node in workflow.nodes}
        outgoing = self._outgoing_edges(workflow.edges)
        incoming = self._incoming_edges(workflow.edges)

        self._validate_node_ids(workflow.nodes, node_ids, errors)
        self._validate_edge_ids(workflow.edges, errors)
        self._validate_supported_node_types(workflow.nodes, errors)
        self._validate_edge_references(workflow.edges, node_id_set, errors)

        if errors:
            return WorkflowValidationResult(is_valid=False, errors=errors, warnings=warnings)

        start_nodes = [node for node in workflow.nodes if node.type == "start"]
        end_nodes = [node for node in workflow.nodes if node.type == "end"]

        self._validate_start_nodes(start_nodes, incoming, outgoing, errors)
        self._validate_end_nodes(end_nodes, outgoing, errors)
        self._validate_reachability(start_nodes, workflow.nodes, outgoing, errors)
        self._validate_condition_branches(workflow.nodes, outgoing, errors)
        self._validate_condition_configs(workflow.nodes, errors)
        self._validate_approval_paths(workflow.nodes, outgoing, errors)
        self._validate_approval_configs(workflow.nodes, errors)
        self._validate_delay_configs(workflow.nodes, errors)
        self._validate_cycles(start_nodes, nodes_by_id, outgoing, errors)

        return WorkflowValidationResult(is_valid=not errors, errors=errors, warnings=warnings)

    def _validate_node_ids(
        self,
        nodes: list[WorkflowNode],
        node_ids: list[str],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        if len(node_ids) != len(set(node_ids)):
            errors.append(
                WorkflowValidationIssue(
                    code="duplicate_node_id",
                    message="Workflow contains duplicate node IDs",
                )
            )

        for node in nodes:
            if not node.id.strip():
                errors.append(
                    WorkflowValidationIssue(
                        code="invalid_node_id",
                        message="Node ID cannot be empty",
                        node_id=node.id,
                    )
                )

    def _validate_edge_ids(
        self,
        edges: list[WorkflowEdge],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        edge_ids = [edge.id for edge in edges]
        if len(edge_ids) != len(set(edge_ids)):
            errors.append(
                WorkflowValidationIssue(
                    code="duplicate_edge_id",
                    message="Workflow contains duplicate edge IDs",
                )
            )

        for edge in edges:
            if not edge.id.strip():
                errors.append(
                    WorkflowValidationIssue(
                        code="invalid_edge_id",
                        message="Edge ID cannot be empty",
                        edge_id=edge.id,
                    )
                )

    def _validate_supported_node_types(
        self,
        nodes: list[WorkflowNode],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        for node in nodes:
            if node.type not in SUPPORTED_NODE_TYPES:
                errors.append(
                    WorkflowValidationIssue(
                        code="unsupported_node_type",
                        message=f"Unsupported node type: {node.type}",
                        node_id=node.id,
                    )
                )

    def _validate_edge_references(
        self,
        edges: list[WorkflowEdge],
        node_ids: set[str],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        for edge in edges:
            if edge.source not in node_ids:
                errors.append(
                    WorkflowValidationIssue(
                        code="invalid_edge_source",
                        message="Edge source does not reference an existing node",
                        edge_id=edge.id,
                    )
                )
            if edge.target not in node_ids:
                errors.append(
                    WorkflowValidationIssue(
                        code="invalid_edge_target",
                        message="Edge target does not reference an existing node",
                        edge_id=edge.id,
                    )
                )

    def _validate_start_nodes(
        self,
        start_nodes: list[WorkflowNode],
        incoming: dict[str, list[WorkflowEdge]],
        outgoing: dict[str, list[WorkflowEdge]],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        if len(start_nodes) != 1:
            errors.append(
                WorkflowValidationIssue(
                    code="invalid_start_count",
                    message="Workflow must contain exactly one start node",
                )
            )
            return

        start_node = start_nodes[0]
        if incoming[start_node.id]:
            errors.append(
                WorkflowValidationIssue(
                    code="start_has_incoming_edges",
                    message="Start node cannot have incoming edges",
                    node_id=start_node.id,
                )
            )
        if len(outgoing[start_node.id]) != 1:
            errors.append(
                WorkflowValidationIssue(
                    code="start_outgoing_count",
                    message="Start node must have exactly one outgoing edge",
                    node_id=start_node.id,
                )
            )

    def _validate_end_nodes(
        self,
        end_nodes: list[WorkflowNode],
        outgoing: dict[str, list[WorkflowEdge]],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        if not end_nodes:
            errors.append(
                WorkflowValidationIssue(
                    code="missing_end_node",
                    message="Workflow must contain at least one end node",
                )
            )

        for end_node in end_nodes:
            if outgoing[end_node.id]:
                errors.append(
                    WorkflowValidationIssue(
                        code="end_has_outgoing_edges",
                        message="End nodes cannot have outgoing edges",
                        node_id=end_node.id,
                    )
                )

    def _validate_reachability(
        self,
        start_nodes: list[WorkflowNode],
        nodes: list[WorkflowNode],
        outgoing: dict[str, list[WorkflowEdge]],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        if len(start_nodes) != 1:
            return

        reachable = self._reachable_node_ids(start_nodes[0].id, outgoing)
        for node in nodes:
            if node.id not in reachable:
                errors.append(
                    WorkflowValidationIssue(
                        code="unreachable_node",
                        message="Node is not reachable from the start node",
                        node_id=node.id,
                    )
                )

    def _validate_condition_branches(
        self,
        nodes: list[WorkflowNode],
        outgoing: dict[str, list[WorkflowEdge]],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        for node in nodes:
            if node.type != "condition":
                continue

            labels = {edge.label for edge in outgoing[node.id]}
            if not CONDITION_BRANCHES.issubset(labels):
                errors.append(
                    WorkflowValidationIssue(
                        code="condition_missing_branch",
                        message="Condition nodes must have true and false outgoing branches",
                        node_id=node.id,
                    )
                )

    def _validate_approval_paths(
        self,
        nodes: list[WorkflowNode],
        outgoing: dict[str, list[WorkflowEdge]],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        for node in nodes:
            if node.type != "approval":
                continue

            labels = {edge.label for edge in outgoing[node.id]}
            if not APPROVAL_OUTCOMES.issubset(labels):
                errors.append(
                    WorkflowValidationIssue(
                        code="approval_missing_outcome_path",
                        message="Approval nodes must have approve and reject outgoing paths",
                        node_id=node.id,
                    )
                )

    def _validate_condition_configs(
        self,
        nodes: list[WorkflowNode],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        for node in nodes:
            if node.type != "condition":
                continue

            condition = node.data.get("condition")
            if not isinstance(condition, dict):
                errors.append(
                    WorkflowValidationIssue(
                        code="condition_config_missing",
                        message="Condition nodes must define a condition object",
                        node_id=node.id,
                    )
                )
                continue

            if not isinstance(condition.get("field"), str) or not condition["field"].strip():
                errors.append(
                    WorkflowValidationIssue(
                        code="condition_field_missing",
                        message="Condition nodes must define a field",
                        node_id=node.id,
                    )
                )
            if condition.get("operator") not in SUPPORTED_CONDITION_OPERATORS:
                errors.append(
                    WorkflowValidationIssue(
                        code="condition_operator_unsupported",
                        message="Condition node uses an unsupported operator",
                        node_id=node.id,
                    )
                )

    def _validate_approval_configs(
        self,
        nodes: list[WorkflowNode],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        for node in nodes:
            if node.type != "approval":
                continue

            assigned_user_id = node.data.get("assigned_user_id")
            assigned_role = node.data.get("assigned_role")
            has_user = isinstance(assigned_user_id, str) and bool(assigned_user_id.strip())
            has_role = isinstance(assigned_role, str) and bool(assigned_role.strip())
            if has_user == has_role:
                errors.append(
                    WorkflowValidationIssue(
                        code="approval_assignment_invalid",
                        message="Approval nodes must assign exactly one user or role",
                        node_id=node.id,
                    )
                )

    def _validate_delay_configs(
        self,
        nodes: list[WorkflowNode],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        for node in nodes:
            if node.type != "delay":
                continue

            seconds = node.data.get("seconds")
            if not isinstance(seconds, int) or seconds < 0:
                errors.append(
                    WorkflowValidationIssue(
                        code="delay_seconds_invalid",
                        message="Delay nodes must define non-negative integer seconds",
                        node_id=node.id,
                    )
                )

    def _validate_cycles(
        self,
        start_nodes: list[WorkflowNode],
        nodes_by_id: dict[str, WorkflowNode],
        outgoing: dict[str, list[WorkflowEdge]],
        errors: list[WorkflowValidationIssue],
    ) -> None:
        if len(start_nodes) != 1:
            return

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False

            visiting.add(node_id)
            for edge in outgoing[node_id]:
                if edge.target in nodes_by_id and visit(edge.target):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        if visit(start_nodes[0].id):
            errors.append(
                WorkflowValidationIssue(
                    code="unsupported_cycle",
                    message="Workflow contains an unsupported cycle",
                )
            )

    def _reachable_node_ids(
        self,
        start_node_id: str,
        outgoing: dict[str, list[WorkflowEdge]],
    ) -> set[str]:
        reachable = {start_node_id}
        queue: deque[str] = deque([start_node_id])

        while queue:
            node_id = queue.popleft()
            for edge in outgoing[node_id]:
                if edge.target not in reachable:
                    reachable.add(edge.target)
                    queue.append(edge.target)

        return reachable

    def _outgoing_edges(self, edges: list[WorkflowEdge]) -> dict[str, list[WorkflowEdge]]:
        outgoing: dict[str, list[WorkflowEdge]] = defaultdict(list)
        for edge in edges:
            outgoing[edge.source].append(edge)
        return outgoing

    def _incoming_edges(self, edges: list[WorkflowEdge]) -> dict[str, list[WorkflowEdge]]:
        incoming: dict[str, list[WorkflowEdge]] = defaultdict(list)
        for edge in edges:
            incoming[edge.target].append(edge)
        return incoming
