export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type Organization = {
  id: string;
  name: string;
  role: "owner" | "admin" | "member";
};

export type WorkflowStatus = "draft" | "active";

export type WorkflowNode = {
  id: string;
  type: string;
  position: Record<string, number>;
  data: Record<string, unknown>;
};

export type WorkflowEdge = {
  id: string;
  source: string;
  target: string;
  label: string | null;
  data: Record<string, unknown>;
};

export type Workflow = {
  id: string;
  organization_id: string;
  name: string;
  status: WorkflowStatus;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  revision: number;
};

export type WorkflowValidationIssue = {
  code: string;
  message: string;
  node_id: string | null;
  edge_id: string | null;
};

export type WorkflowValidationResult = {
  is_valid: boolean;
  errors: WorkflowValidationIssue[];
  warnings: WorkflowValidationIssue[];
};

export type TaskStatus = "pending" | "completed";

export type TaskDecision = "approve" | "reject";

export type Task = {
  id: string;
  organization_id: string;
  workflow_id: string;
  instance_id: string;
  node_id: string;
  status: TaskStatus;
  assigned_user_id: string | null;
  assigned_role: string | null;
  decision: TaskDecision | null;
  completed_by_user_id: string | null;
  revision: number;
};

export type WorkflowInstanceStatus = "running" | "completed" | "failed" | "waiting";

export type WorkflowInstance = {
  id: string;
  organization_id: string;
  workflow_id: string;
  workflow_revision: number;
  status: WorkflowInstanceStatus;
  active_node_id: string | null;
  context: Record<string, unknown>;
  input: Record<string, unknown>;
  revision: number;
};

export type InstanceEvent = {
  id: string;
  organization_id: string;
  instance_id: string;
  workflow_id: string;
  type: string;
  node_id: string | null;
  data: Record<string, unknown>;
};
