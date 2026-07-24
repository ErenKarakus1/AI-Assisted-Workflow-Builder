import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "reactflow";
import "reactflow/dist/style.css";

import type {
  InstanceEvent,
  OrganizationMember,
  Workflow,
  WorkflowEdge,
  WorkflowInstance,
  WorkflowNode,
} from "../../types/api";

type Props = {
  workflow: Workflow;
  isSaving: boolean;
  onSave: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
  isValidatingDraft: boolean;
  onValidateDraft: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
  onDirtyChange: (isDirty: boolean) => void;
  onGraphChange?: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
  selectedInstance: WorkflowInstance | null;
  instanceEvents: InstanceEvent[];
  organizationMembers: OrganizationMember[];
  canManageWorkflow: boolean;
};

type NodeKind = "start" | "approval" | "condition" | "delay" | "end";

const nodeKinds: NodeKind[] = ["start", "approval", "condition", "delay", "end"];
const conditionOperators = [
  { value: "equals", label: "Equals" },
  { value: "not_equals", label: "Does not equal" },
  { value: "greater_than", label: "Greater than" },
  { value: "greater_than_or_equal", label: "Greater than or equal to" },
  { value: "less_than", label: "Less than" },
  { value: "less_than_or_equal", label: "Less than or equal to" },
  { value: "contains", label: "Contains" },
];
const approvalRoles = [
  { value: "owner", label: "Owner" },
  { value: "admin", label: "Admin" },
  { value: "member", label: "Member" },
  { value: "owner_or_admin", label: "Owner or Admin" },
  { value: "all", label: "Anyone in the org" },
];

export function WorkflowGraphEditor({
  workflow,
  isSaving,
  onSave,
  isValidatingDraft,
  onValidateDraft,
  onDirtyChange,
  onGraphChange,
  selectedInstance,
  instanceEvents,
  organizationMembers,
  canManageWorkflow,
}: Props) {
  const isEditable = canManageWorkflow && !selectedInstance && workflow.status === "draft";
  const initialNodes = useMemo(() => workflow.nodes.map(toFlowNode), [workflow.nodes]);
  const initialEdges = useMemo(() => workflow.edges.map(toFlowEdge), [workflow.edges]);
  const progress = useMemo(
    () => buildInstanceProgress(selectedInstance, instanceEvents),
    [instanceEvents, selectedInstance],
  );
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const onDirtyChangeRef = useRef(onDirtyChange);
  const onGraphChangeRef = useRef(onGraphChange);

  useEffect(() => {
    onDirtyChangeRef.current = onDirtyChange;
  }, [onDirtyChange]);

  useEffect(() => {
    onGraphChangeRef.current = onGraphChange;
  }, [onGraphChange]);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    onDirtyChangeRef.current(false);
  }, [initialEdges, initialNodes]);

  useEffect(() => {
    const workflowNodes = nodes.map(toWorkflowNode);
    const workflowEdges = edges.map(toWorkflowEdge);
    onGraphChangeRef.current?.(workflowNodes, workflowEdges);
    onDirtyChangeRef.current(
      graphFingerprint(workflowNodes, workflowEdges) !== graphFingerprint(workflow.nodes, workflow.edges),
    );
  }, [edges, nodes, workflow.edges, workflow.nodes]);

  const flowNodes = useMemo(
    () => nodes.map((node) => decorateProgressNode(node, progress)),
    [nodes, progress],
  );

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId) ?? null;

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (isEditable) {
        setNodes((current) => applyNodeChanges(changes, current));
      }
    },
    [isEditable],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (isEditable) {
        setEdges((current) => applyEdgeChanges(changes, current));
      }
    },
    [isEditable],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!isEditable || !connection.source || !connection.target) {
        return;
      }

      setEdges((current) =>
        addEdge(
          {
            ...connection,
            id: `edge-${connection.source}-${connection.target}-${Date.now()}`,
            label: defaultEdgeLabel(sourceNodeType(nodes, connection.source)),
            data: {},
          },
          current,
        ),
      );
    },
    [isEditable, nodes],
  );

  function addNode(kind: NodeKind) {
    const id = `${kind}-${Date.now()}`;
    setNodes((current) => [
      ...current,
      {
        id,
        type: "default",
        position: { x: 120 + current.length * 40, y: 120 + current.length * 24 },
        data: {
          label: displayLabel(kind, id, defaultNodeData(kind)),
          workflowType: kind,
          workflowData: defaultNodeData(kind),
        },
      },
    ]);
    setSelectedNodeId(id);
    setSelectedEdgeId(null);
  }

  function deleteSelection() {
    if (selectedNodeId) {
      setNodes((current) => current.filter((node) => node.id !== selectedNodeId));
      setEdges((current) =>
        current.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId),
      );
      setSelectedNodeId(null);
      return;
    }

    if (selectedEdgeId) {
      setEdges((current) => current.filter((edge) => edge.id !== selectedEdgeId));
      setSelectedEdgeId(null);
    }
  }

  function updateSelectedNodeData(nextData: Record<string, unknown>) {
    if (!selectedNodeId) {
      return;
    }

    setNodes((current) =>
      current.map((node) =>
        node.id === selectedNodeId
          ? {
              ...node,
              data: {
                ...node.data,
                label: displayLabel(workflowType(node), node.id, nextData),
                workflowData: nextData,
              },
            }
          : node,
      ),
    );
  }

  function updateSelectedEdgeLabel(label: string) {
    if (!selectedEdgeId) {
      return;
    }

    setEdges((current) =>
      current.map((edge) =>
        edge.id === selectedEdgeId
          ? {
              ...edge,
              label: label || null,
            }
          : edge,
      ),
    );
  }

  return (
    <section className="editor-panel">
      <div className="editor-toolbar">
        <div>
          <strong>Graph editor</strong>
          <span>
            {selectedInstance
              ? `Viewing instance ${selectedInstance.id} graph snapshot`
              : isEditable
                ? "Draft editing enabled"
                : canManageWorkflow
                  ? "Active workflows are read-only"
                  : "Members can view workflows but cannot edit them"}
          </span>
        </div>
        <div className="editor-actions">
          <button className="button button--ghost" type="button" disabled={!isEditable} onClick={deleteSelection}>
            Delete selected
          </button>
          <button
            className="button"
            type="button"
            disabled={!isEditable || isValidatingDraft}
            onClick={() => onValidateDraft(nodes.map(toWorkflowNode), edges.map(toWorkflowEdge))}
          >
            {isValidatingDraft ? "Validating..." : "Validate draft"}
          </button>
          <button
            className="button button--secondary"
            type="button"
            disabled={!isEditable || isSaving}
            onClick={() => onSave(nodes.map(toWorkflowNode), edges.map(toWorkflowEdge))}
          >
            {isSaving ? "Saving..." : "Save graph"}
          </button>
        </div>
      </div>

      <div className="node-toolbar">
        {nodeKinds.map((kind) => (
          <button
            className="button button--ghost"
            type="button"
            key={kind}
            disabled={!isEditable}
            onClick={() => addNode(kind)}
          >
            Add {kind}
          </button>
        ))}
      </div>

      <div className="editor-grid">
        <div className="flow-canvas">
          <ReactFlow
            nodes={flowNodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, node) => {
              setSelectedNodeId(node.id);
              setSelectedEdgeId(null);
            }}
            onEdgeClick={(_, edge) => {
              setSelectedEdgeId(edge.id);
              setSelectedNodeId(null);
            }}
            onPaneClick={() => {
              setSelectedNodeId(null);
              setSelectedEdgeId(null);
            }}
            nodesDraggable={isEditable}
            nodesConnectable={isEditable}
            edgesFocusable={isEditable}
            fitView
          >
            <MiniMap pannable zoomable />
            <Controls />
            <Background gap={18} />
          </ReactFlow>
        </div>

        <aside className="config-panel">
          {selectedNode ? (
            <NodeConfigPanel
              node={selectedNode}
              isEditable={isEditable}
              onChange={updateSelectedNodeData}
              organizationMembers={organizationMembers}
            />
          ) : selectedEdge ? (
            <EdgeConfigPanel
              edge={selectedEdge}
              sourceType={sourceNodeType(nodes, selectedEdge.source)}
              isEditable={isEditable}
              onChange={updateSelectedEdgeLabel}
            />
          ) : (
            <p className="muted">Select a node or edge to edit its configuration.</p>
          )}
        </aside>
      </div>
    </section>
  );
}

function NodeConfigPanel({
  node,
  isEditable,
  onChange,
  organizationMembers,
}: {
  node: Node;
  isEditable: boolean;
  onChange: (data: Record<string, unknown>) => void;
  organizationMembers: OrganizationMember[];
}) {
  const kind = workflowType(node);
  const data = workflowData(node);

  return (
    <div className="config-stack">
      <div>
        <p className="eyebrow">Node</p>
        <h3>{displayLabel(kind, node.id, data)}</h3>
        <code>{node.id}</code>
      </div>

      <label>
        Name
        <input
          disabled={!isEditable}
          value={stringValue(data.label)}
          onChange={(event) => onChange({ ...data, label: event.target.value })}
        />
      </label>

      {kind === "approval" ? (
        <ApprovalConfig
          data={data}
          isEditable={isEditable}
          organizationMembers={organizationMembers}
          onChange={onChange}
        />
      ) : null}

      {kind === "condition" ? (
        <>
          <label>
            Check this field
            <input
              disabled={!isEditable}
              placeholder="amount"
              value={conditionFieldValue(data)}
              onChange={(event) =>
                onChange({
                  ...data,
                  condition: { ...conditionData(data), field: normalizeConditionField(event.target.value) },
                })
              }
            />
            <span className="field-hint">Use a field from the run input. Example: amount saves as input.amount.</span>
          </label>
          <label>
            Comparison
            <select
              disabled={!isEditable}
              value={stringValue(conditionData(data).operator) || "equals"}
              onChange={(event) =>
                onChange({
                  ...data,
                  condition: { ...conditionData(data), operator: event.target.value },
                })
              }
            >
              {conditionOperators.map((operator) => (
                <option key={operator.value} value={operator.value}>
                  {operator.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Compare against
            <input
              disabled={!isEditable}
              placeholder="1000"
              value={stringValue(conditionData(data).value)}
              onChange={(event) =>
                onChange({
                  ...data,
                  condition: { ...conditionData(data), value: parseConfigValue(event.target.value) },
                })
              }
            />
            <span className="field-hint">Numbers, true, and false are converted automatically.</span>
          </label>
        </>
      ) : null}

      {kind === "delay" ? (
        <DelayConfig data={data} isEditable={isEditable} onChange={onChange} />
      ) : null}

      {kind === "end" ? (
        <label>
          Result
          <input
            disabled={!isEditable}
            value={stringValue(data.result)}
            onChange={(event) => onChange({ ...data, result: event.target.value })}
          />
        </label>
      ) : null}
    </div>
  );
}

function DelayConfig({
  data,
  isEditable,
  onChange,
}: {
  data: Record<string, unknown>;
  isEditable: boolean;
  onChange: (data: Record<string, unknown>) => void;
}) {
  const duration = splitDuration(numberValue(data.seconds));

  return (
    <div className="duration-fields">
      <label>
        Hours
        <input
          disabled={!isEditable}
          type="number"
          min={0}
          value={duration.hours}
          onChange={(event) =>
            onChange({
              ...data,
              seconds: combineDuration({
                ...duration,
                hours: Math.max(0, Number(event.target.value)),
              }),
            })
          }
        />
      </label>
      <label>
        Minutes
        <input
          disabled={!isEditable}
          type="number"
          min={0}
          value={duration.minutes}
          onChange={(event) =>
            onChange({
              ...data,
              seconds: combineDuration({
                ...duration,
                minutes: Math.max(0, Number(event.target.value)),
              }),
            })
          }
        />
      </label>
      <label>
        Seconds
        <input
          disabled={!isEditable}
          type="number"
          min={0}
          value={duration.seconds}
          onChange={(event) =>
            onChange({
              ...data,
              seconds: combineDuration({
                ...duration,
                seconds: Math.max(0, Number(event.target.value)),
              }),
            })
          }
        />
      </label>
    </div>
  );
}

function ApprovalConfig({
  data,
  isEditable,
  organizationMembers,
  onChange,
}: {
  data: Record<string, unknown>;
  isEditable: boolean;
  organizationMembers: OrganizationMember[];
  onChange: (data: Record<string, unknown>) => void;
}) {
  const assignmentType = stringValue(data.assigned_user_id) ? "user" : "role";

  return (
    <>
      <label>
        Assign approval to
        <select
          disabled={!isEditable}
          value={assignmentType}
          onChange={(event) => {
            if (event.target.value === "user") {
              onChange({
                ...data,
                assigned_user_id: organizationMembers[0]?.user_id,
                assigned_role: undefined,
              });
              return;
            }

            onChange({
              ...data,
              assigned_role: stringValue(data.assigned_role) || "member",
              assigned_user_id: undefined,
            });
          }}
        >
          <option value="role">A role</option>
          <option value="user">A specific user</option>
        </select>
      </label>

      {assignmentType === "user" ? (
        <label>
          Assigned user
          <select
            disabled={!isEditable || organizationMembers.length === 0}
            value={stringValue(data.assigned_user_id)}
            onChange={(event) =>
              onChange({
                ...data,
                assigned_user_id: event.target.value || undefined,
                assigned_role: undefined,
              })
            }
          >
            <option value="">Select user</option>
            {organizationMembers.map((member) => (
              <option key={member.id} value={member.user_id}>
                {member.full_name || member.email} ({member.role})
              </option>
            ))}
          </select>
          {organizationMembers.length === 0 ? (
            <span className="field-hint">No organization members are available yet.</span>
          ) : null}
        </label>
      ) : (
        <label>
          Assigned role
          <select
            disabled={!isEditable}
            value={stringValue(data.assigned_role)}
            onChange={(event) =>
              onChange({
                ...data,
                assigned_role: event.target.value || undefined,
                assigned_user_id: undefined,
              })
            }
          >
            <option value="">Select role</option>
            {approvalRoles.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>
        </label>
      )}
    </>
  );
}

function EdgeConfigPanel({
  edge,
  sourceType,
  isEditable,
  onChange,
}: {
  edge: Edge;
  sourceType: NodeKind | null;
  isEditable: boolean;
  onChange: (label: string) => void;
}) {
  const options = edgeLabelOptions(sourceType);

  return (
    <div className="config-stack">
      <div>
        <p className="eyebrow">Edge</p>
        <h3>{edge.source} to {edge.target}</h3>
        <code>{edge.id}</code>
      </div>
      <label>
        Label
        <select
          disabled={!isEditable}
          value={typeof edge.label === "string" ? edge.label : ""}
          onChange={(event) => onChange(event.target.value)}
        >
          {options.map((option) => (
            <option key={option.value || "none"} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function defaultNodeData(kind: NodeKind): Record<string, unknown> {
  if (kind === "approval") {
    return { label: "Approval", assigned_role: "member" };
  }
  if (kind === "condition") {
    return {
      label: "Condition",
      condition: { field: "input.amount", operator: "greater_than_or_equal", value: 1000 },
    };
  }
  if (kind === "delay") {
    return { label: "Delay", seconds: 60 };
  }
  if (kind === "end") {
    return { label: "End", result: "completed" };
  }
  return { label: "Start" };
}

function toFlowNode(node: WorkflowNode): Node {
  return {
    id: node.id,
    type: "default",
    position: { x: node.position.x ?? 0, y: node.position.y ?? 0 },
    data: { label: displayLabel(node.type as NodeKind, node.id, node.data), workflowType: node.type, workflowData: node.data },
  };
}

function toFlowEdge(edge: WorkflowEdge): Edge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label ?? undefined,
    data: edge.data,
  };
}

function toWorkflowNode(node: Node): WorkflowNode {
  return {
    id: node.id,
    type: workflowType(node),
    position: { x: node.position.x, y: node.position.y },
    data: workflowData(node),
  };
}

function toWorkflowEdge(edge: Edge): WorkflowEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: typeof edge.label === "string" ? edge.label : null,
    data: (edge.data as Record<string, unknown> | undefined) ?? {},
  };
}

function graphFingerprint(nodes: WorkflowNode[], edges: WorkflowEdge[]): string {
  return JSON.stringify({
    nodes: nodes
      .map((node) => ({
        id: node.id,
        type: node.type,
        position: node.position,
        data: node.data,
      }))
      .sort((left, right) => left.id.localeCompare(right.id)),
    edges: edges
      .map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        data: edge.data,
      }))
      .sort((left, right) => left.id.localeCompare(right.id)),
  });
}

function workflowType(node: Node): NodeKind {
  const value = node.data?.workflowType;
  return nodeKinds.includes(value as NodeKind) ? (value as NodeKind) : "condition";
}

function sourceNodeType(nodes: Node[], sourceId: string | null): NodeKind | null {
  const source = nodes.find((node) => node.id === sourceId);
  return source ? workflowType(source) : null;
}

function displayLabel(kind: NodeKind, id: string, data: Record<string, unknown>): string {
  const label = stringValue(data.label).trim();
  return label ? `${label} (${kind})` : `${kind}: ${id}`;
}

function defaultEdgeLabel(kind: NodeKind | null): string | null {
  const options = edgeLabelOptions(kind);
  return options[0]?.value || null;
}

function edgeLabelOptions(kind: NodeKind | null): Array<{ value: string; label: string }> {
  if (kind === "condition") {
    return [
      { value: "true", label: "true" },
      { value: "false", label: "false" },
    ];
  }
  if (kind === "approval") {
    return [
      { value: "approve", label: "approve" },
      { value: "reject", label: "reject" },
    ];
  }
  return [{ value: "", label: "none" }];
}

function workflowData(node: Node): Record<string, unknown> {
  return (node.data?.workflowData as Record<string, unknown> | undefined) ?? {};
}

function conditionData(data: Record<string, unknown>): Record<string, unknown> {
  return (data.condition as Record<string, unknown> | undefined) ?? {};
}

function conditionFieldValue(data: Record<string, unknown>): string {
  const field = stringValue(conditionData(data).field);
  return field.startsWith("input.") ? field.slice("input.".length) : field;
}

function normalizeConditionField(field: string): string {
  const trimmed = field.trim();
  if (!trimmed || trimmed.startsWith("input.") || trimmed.startsWith("context.")) {
    return trimmed;
  }
  return `input.${trimmed}`;
}

function stringValue(value: unknown): string {
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : "";
}

function numberValue(value: unknown): number {
  return typeof value === "number" ? value : 0;
}

function splitDuration(totalSeconds: number): { hours: number; minutes: number; seconds: number } {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  return { hours, minutes, seconds };
}

function combineDuration(duration: { hours: number; minutes: number; seconds: number }): number {
  return Math.floor(duration.hours) * 3600 + Math.floor(duration.minutes) * 60 + Math.floor(duration.seconds);
}

function parseConfigValue(value: string): string | number | boolean {
  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }
  const numeric = Number(value);
  return value.trim() !== "" && Number.isFinite(numeric) ? numeric : value;
}

type InstanceProgress = {
  activeNodeId: string | null;
  failedNodeIds: Set<string>;
  visitedNodeIds: Set<string>;
};

function buildInstanceProgress(
  instance: WorkflowInstance | null,
  events: InstanceEvent[],
): InstanceProgress {
  const failedNodeIds = new Set(
    events
      .filter((event) => event.type === "instance_failed" && event.node_id)
      .map((event) => event.node_id as string),
  );
  const visitedNodeIds = new Set(
    events
      .filter((event) => event.type === "node_entered" && event.node_id)
      .map((event) => event.node_id as string),
  );

  return {
    activeNodeId: instance?.active_node_id ?? null,
    failedNodeIds,
    visitedNodeIds,
  };
}

function decorateProgressNode(node: Node, progress: InstanceProgress): Node {
  const status = nodeProgressStatus(node.id, progress);
  return {
    ...node,
    className: status ? `workflow-node workflow-node--${status}` : "workflow-node",
    data: {
      ...node.data,
      label: status ? `${node.data?.label ?? node.id} · ${status}` : node.data?.label,
    },
  };
}

function nodeProgressStatus(nodeId: string, progress: InstanceProgress): string | null {
  if (progress.failedNodeIds.has(nodeId)) {
    return "failed";
  }
  if (progress.activeNodeId === nodeId) {
    return "active";
  }
  if (progress.visitedNodeIds.has(nodeId)) {
    return "visited";
  }
  return null;
}
