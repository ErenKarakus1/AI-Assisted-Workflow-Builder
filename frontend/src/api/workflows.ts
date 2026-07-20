import { apiRequest } from "./client";
import type { Workflow, WorkflowValidationResult } from "../types/api";

const starterNodes = [
  { id: "start-1", type: "start", position: { x: 0, y: 0 }, data: {} },
  { id: "end-1", type: "end", position: { x: 300, y: 0 }, data: { result: "completed" } },
];

const starterEdges = [
  { id: "edge-1", source: "start-1", target: "end-1", label: null, data: {} },
];

export function listWorkflows(organizationId: string): Promise<Workflow[]> {
  return apiRequest<Workflow[]>(`/api/orgs/${organizationId}/workflows`);
}

export function getWorkflow(organizationId: string, workflowId: string): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/orgs/${organizationId}/workflows/${workflowId}`);
}

export function createWorkflow(organizationId: string, name: string): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/orgs/${organizationId}/workflows`, {
    method: "POST",
    body: JSON.stringify({
      name,
      nodes: starterNodes,
      edges: starterEdges,
    }),
  });
}

export function validateWorkflow(
  organizationId: string,
  workflowId: string,
): Promise<WorkflowValidationResult> {
  return apiRequest<WorkflowValidationResult>(
    `/api/orgs/${organizationId}/workflows/${workflowId}/validate`,
    { method: "POST" },
  );
}

export function activateWorkflow(organizationId: string, workflowId: string): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/orgs/${organizationId}/workflows/${workflowId}/activate`, {
    method: "POST",
  });
}
