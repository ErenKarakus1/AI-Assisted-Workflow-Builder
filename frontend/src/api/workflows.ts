import { apiRequest } from "./client";
import type {
  Workflow,
  WorkflowAIAnalyzeResult,
  WorkflowAIGenerateResult,
  WorkflowAIStatus,
  WorkflowEdge,
  WorkflowNode,
  WorkflowValidationResult,
} from "../types/api";

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

export function generateWorkflowGraph(
  organizationId: string,
  workflowId: string,
  prompt: string,
  useCurrentGraph: boolean,
): Promise<WorkflowAIGenerateResult> {
  return apiRequest<WorkflowAIGenerateResult>(
    `/api/orgs/${organizationId}/workflows/${workflowId}/ai/generate-graph`,
    {
      method: "POST",
      body: JSON.stringify({ prompt, use_current_graph: useCurrentGraph }),
    },
  );
}

export function getWorkflowAIStatus(
  organizationId: string,
  workflowId: string,
): Promise<WorkflowAIStatus> {
  return apiRequest<WorkflowAIStatus>(`/api/orgs/${organizationId}/workflows/${workflowId}/ai/status`);
}

export function analyzeWorkflowGraph(
  organizationId: string,
  workflowId: string,
  workflow: Workflow,
): Promise<WorkflowAIAnalyzeResult> {
  return apiRequest<WorkflowAIAnalyzeResult>(
    `/api/orgs/${organizationId}/workflows/${workflowId}/ai/analyze-graph`,
    {
      method: "POST",
      body: JSON.stringify({
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

export function deleteWorkflow(organizationId: string, workflowId: string): Promise<void> {
  return apiRequest<void>(`/api/orgs/${organizationId}/workflows/${workflowId}`, {
    method: "DELETE",
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
