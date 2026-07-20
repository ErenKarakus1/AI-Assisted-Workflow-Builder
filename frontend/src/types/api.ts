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

