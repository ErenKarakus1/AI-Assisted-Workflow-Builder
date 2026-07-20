import { apiRequest } from "./client";
import type { Workflow, WorkflowEdge, WorkflowNode, WorkflowValidationResult } from "../types/api";

export function listWorkflows(organizationId: string): Promise<Workflow[]> {
  return apiRequest<Workflow[]>(`/api/orgs/${organizationId}/workflows`);
}

export function getWorkflow(organizationId: string, workflowId: string): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/orgs/${organizationId}/workflows/${workflowId}`);
}

export function createWorkflow(
  organizationId: string,
  name: string,
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/orgs/${organizationId}/workflows`, {
    method: "POST",
    body: JSON.stringify({
      name,
      nodes,
      edges,
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

export function validateWorkflowDraft(
  organizationId: string,
  workflowId: string,
  workflow: Workflow,
): Promise<WorkflowValidationResult> {
  return apiRequest<WorkflowValidationResult>(
    `/api/orgs/${organizationId}/workflows/${workflowId}/validate-draft`,
    {
      method: "POST",
      body: JSON.stringify({
        name: workflow.name,
        nodes: workflow.nodes,
        edges: workflow.edges,
        revision: workflow.revision,
      }),
    },
  );
}

export function activateWorkflow(organizationId: string, workflowId: string): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/orgs/${organizationId}/workflows/${workflowId}/activate`, {
    method: "POST",
  });
}

export function deactivateWorkflow(organizationId: string, workflowId: string): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/orgs/${organizationId}/workflows/${workflowId}/deactivate`, {
    method: "POST",
  });
}

export function updateWorkflow(workflow: Workflow): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/orgs/${workflow.organization_id}/workflows/${workflow.id}`, {
    method: "PUT",
    body: JSON.stringify({
      name: workflow.name,
      nodes: workflow.nodes,
      edges: workflow.edges,
      revision: workflow.revision,
    }),
  });
}
