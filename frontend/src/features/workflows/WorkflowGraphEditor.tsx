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

export function WorkflowGraphEditor({ workflow, isSaving, onSave }: Props) {
  const isEditable = workflow.status === "draft";
  const initialNodes = useMemo(() => workflow.nodes.map(toFlowNode), [workflow.nodes]);
  const initialEdges = useMemo(() => workflow.edges.map(toFlowEdge), [workflow.edges]);
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialEdges, initialNodes]);

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
            label: connection.sourceHandle ?? null,
          },
          current,
        ),
      );
    },
    [isEditable],
  );

  return (
    <section className="editor-panel">
      <div className="editor-toolbar">
        <div>
          <strong>Graph editor</strong>
          <span>{isEditable ? "Draft editing enabled" : "Active workflows are read-only"}</span>
        </div>
        <button
          className="button"
          type="button"
          disabled={!isEditable || isSaving}
          onClick={() => onSave(nodes.map(toWorkflowNode), edges.map(toWorkflowEdge))}
        >
          {isSaving ? "Saving..." : "Save graph"}
        </button>
      </div>
      <div className="flow-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
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
    </section>
  );
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
    type: typeof node.data?.workflowType === "string" ? node.data.workflowType : "condition",
    position: { x: node.position.x, y: node.position.y },
    data: (node.data?.workflowData as Record<string, unknown> | undefined) ?? {},
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
