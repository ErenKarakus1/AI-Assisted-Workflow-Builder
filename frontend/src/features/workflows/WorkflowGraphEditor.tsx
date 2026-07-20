import { useCallback, useEffect, useMemo, useState } from "react";
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

import type { Workflow, WorkflowEdge, WorkflowNode } from "../../types/api";

type Props = {
  workflow: Workflow;
  isSaving: boolean;
  onSave: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
};

type NodeKind = "start" | "approval" | "condition" | "delay" | "end";

const nodeKinds: NodeKind[] = ["start", "approval", "condition", "delay", "end"];
const conditionOperators = [
  "equals",
  "not_equals",
  "greater_than",
  "greater_than_or_equal",
  "less_than",
  "less_than_or_equal",
  "contains",
];

export function WorkflowGraphEditor({ workflow, isSaving, onSave }: Props) {
  const isEditable = workflow.status === "draft";
  const initialNodes = useMemo(() => workflow.nodes.map(toFlowNode), [workflow.nodes]);
  const initialEdges = useMemo(() => workflow.edges.map(toFlowEdge), [workflow.edges]);
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
  }, [initialEdges, initialNodes]);

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
            label: null,
            data: {},
          },
          current,
        ),
      );
    },
    [isEditable],
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
          label: `${kind}: ${id}`,
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
          <span>{isEditable ? "Draft editing enabled" : "Active workflows are read-only"}</span>
        </div>
        <div className="editor-actions">
          <button className="button button--ghost" type="button" disabled={!isEditable} onClick={deleteSelection}>
            Delete selected
          </button>
          <button
            className="button"
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
            nodes={nodes}
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
            />
          ) : selectedEdge ? (
            <EdgeConfigPanel edge={selectedEdge} isEditable={isEditable} onChange={updateSelectedEdgeLabel} />
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
}: {
  node: Node;
  isEditable: boolean;
  onChange: (data: Record<string, unknown>) => void;
}) {
  const kind = workflowType(node);
  const data = workflowData(node);

  return (
    <div className="config-stack">
      <div>
        <p className="eyebrow">Node</p>
        <h3>{kind}</h3>
        <code>{node.id}</code>
      </div>

      {kind === "approval" ? (
        <>
          <label>
            Assigned user ID
            <input
              disabled={!isEditable}
              value={stringValue(data.assigned_user_id)}
              onChange={(event) =>
                onChange({
                  ...data,
                  assigned_user_id: event.target.value || undefined,
                  assigned_role: event.target.value ? undefined : data.assigned_role,
                })
              }
            />
          </label>
          <label>
            Assigned role
            <input
              disabled={!isEditable}
              value={stringValue(data.assigned_role)}
              onChange={(event) =>
                onChange({
                  ...data,
                  assigned_role: event.target.value || undefined,
                  assigned_user_id: event.target.value ? undefined : data.assigned_user_id,
                })
              }
            />
          </label>
        </>
      ) : null}

      {kind === "condition" ? (
        <>
          <label>
            Field
            <input
              disabled={!isEditable}
              value={stringValue((data.condition as Record<string, unknown> | undefined)?.field)}
              onChange={(event) =>
                onChange({
                  ...data,
                  condition: { ...conditionData(data), field: event.target.value },
                })
              }
            />
          </label>
          <label>
            Operator
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
                <option key={operator} value={operator}>
                  {operator}
                </option>
              ))}
            </select>
          </label>
          <label>
            Value
            <input
              disabled={!isEditable}
              value={stringValue(conditionData(data).value)}
              onChange={(event) =>
                onChange({
                  ...data,
                  condition: { ...conditionData(data), value: parseConfigValue(event.target.value) },
                })
              }
            />
          </label>
        </>
      ) : null}

      {kind === "delay" ? (
        <label>
          Seconds
          <input
            disabled={!isEditable}
            type="number"
            min={0}
            value={numberValue(data.seconds)}
            onChange={(event) => onChange({ ...data, seconds: Number(event.target.value) })}
          />
        </label>
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

function EdgeConfigPanel({
  edge,
  isEditable,
  onChange,
}: {
  edge: Edge;
  isEditable: boolean;
  onChange: (label: string) => void;
}) {
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
          <option value="">none</option>
          <option value="true">true</option>
          <option value="false">false</option>
          <option value="approve">approve</option>
          <option value="reject">reject</option>
        </select>
      </label>
    </div>
  );
}

function defaultNodeData(kind: NodeKind): Record<string, unknown> {
  if (kind === "approval") {
    return { assigned_role: "manager" };
  }
  if (kind === "condition") {
    return { condition: { field: "input.amount", operator: "greater_than_or_equal", value: 1000 } };
  }
  if (kind === "delay") {
    return { seconds: 60 };
  }
  if (kind === "end") {
    return { result: "completed" };
  }
  return {};
}

function toFlowNode(node: WorkflowNode): Node {
  return {
    id: node.id,
    type: "default",
    position: { x: node.position.x ?? 0, y: node.position.y ?? 0 },
    data: { label: `${node.type}: ${node.id}`, workflowType: node.type, workflowData: node.data },
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

function workflowType(node: Node): NodeKind {
  const value = node.data?.workflowType;
  return nodeKinds.includes(value as NodeKind) ? (value as NodeKind) : "condition";
}

function workflowData(node: Node): Record<string, unknown> {
  return (node.data?.workflowData as Record<string, unknown> | undefined) ?? {};
}

function conditionData(data: Record<string, unknown>): Record<string, unknown> {
  return (data.condition as Record<string, unknown> | undefined) ?? {};
}

function stringValue(value: unknown): string {
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : "";
}

function numberValue(value: unknown): number {
  return typeof value === "number" ? value : 0;
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
