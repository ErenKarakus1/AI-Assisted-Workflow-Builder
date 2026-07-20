import type { WorkflowEdge, WorkflowNode } from "../../types/api";

export type WorkflowTemplate = {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

export const workflowTemplates: WorkflowTemplate[] = [
  {
    id: "blank",
    name: "Blank workflow",
    description: "A simple start and end flow.",
    nodes: [
      node("start-1", "start", 0, 0, { label: "Start" }),
      node("end-1", "end", 320, 0, { label: "End", result: "completed" }),
    ],
    edges: [edge("edge-start-end", "start-1", "end-1")],
  },
  {
    id: "approval",
    name: "Approval",
    description: "Ask a role to approve, then complete or reject.",
    nodes: [
      node("start-1", "start", 0, 0, { label: "Start" }),
      node("approval-1", "approval", 280, 0, { label: "Approval", assigned_role: "manager" }),
      node("approved-end", "end", 600, -90, { label: "Approved", result: "approved" }),
      node("rejected-end", "end", 600, 90, { label: "Rejected", result: "rejected" }),
    ],
    edges: [
      edge("edge-start-approval", "start-1", "approval-1"),
      edge("edge-approval-approved", "approval-1", "approved-end", "approve"),
      edge("edge-approval-rejected", "approval-1", "rejected-end", "reject"),
    ],
  },
  {
    id: "conditional-approval",
    name: "Conditional approval",
    description: "Approve only when an amount reaches a threshold.",
    nodes: [
      node("start-1", "start", 0, 0, { label: "Start" }),
      node("condition-1", "condition", 280, 0, {
        label: "Amount check",
        condition: { field: "input.amount", operator: "greater_than_or_equal", value: 1000 },
      }),
      node("approval-1", "approval", 600, -90, { label: "Manager approval", assigned_role: "manager" }),
      node("auto-end", "end", 600, 120, { label: "Auto complete", result: "auto_completed" }),
      node("approved-end", "end", 920, -160, { label: "Approved", result: "approved" }),
      node("rejected-end", "end", 920, 0, { label: "Rejected", result: "rejected" }),
    ],
    edges: [
      edge("edge-start-condition", "start-1", "condition-1"),
      edge("edge-condition-approval", "condition-1", "approval-1", "true"),
      edge("edge-condition-auto", "condition-1", "auto-end", "false"),
      edge("edge-approval-approved", "approval-1", "approved-end", "approve"),
      edge("edge-approval-rejected", "approval-1", "rejected-end", "reject"),
    ],
  },
  {
    id: "approval-delay",
    name: "Approval with delay",
    description: "Approve, wait for a delay, then complete.",
    nodes: [
      node("start-1", "start", 0, 0, { label: "Start" }),
      node("approval-1", "approval", 280, 0, { label: "Approval", assigned_role: "manager" }),
      node("delay-1", "delay", 600, -80, { label: "Wait", seconds: 3600 }),
      node("done-end", "end", 900, -80, { label: "Completed", result: "completed" }),
      node("rejected-end", "end", 600, 110, { label: "Rejected", result: "rejected" }),
    ],
    edges: [
      edge("edge-start-approval", "start-1", "approval-1"),
      edge("edge-approval-delay", "approval-1", "delay-1", "approve"),
      edge("edge-approval-rejected", "approval-1", "rejected-end", "reject"),
      edge("edge-delay-done", "delay-1", "done-end"),
    ],
  },
];

function node(
  id: string,
  type: string,
  x: number,
  y: number,
  data: Record<string, unknown>,
): WorkflowNode {
  return {
    id,
    type,
    position: { x, y },
    data,
  };
}

function edge(id: string, source: string, target: string, label: string | null = null): WorkflowEdge {
  return {
    id,
    source,
    target,
    label,
    data: {},
  };
}
