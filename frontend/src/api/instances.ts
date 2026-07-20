import { apiRequest } from "./client";
import type { InstanceEvent, WorkflowInstance } from "../types/api";

export function listWorkflowInstances(
  organizationId: string,
  workflowId: string,
): Promise<WorkflowInstance[]> {
  return apiRequest<WorkflowInstance[]>(
    `/api/orgs/${organizationId}/workflows/${workflowId}/instances`,
  );
}

export function startWorkflowInstance(
  organizationId: string,
  workflowId: string,
  input: Record<string, unknown>,
): Promise<WorkflowInstance> {
  return apiRequest<WorkflowInstance>(
    `/api/orgs/${organizationId}/workflows/${workflowId}/instances`,
    {
      method: "POST",
      body: JSON.stringify({ input }),
    },
  );
}

export function listInstanceEvents(
  organizationId: string,
  instanceId: string,
): Promise<InstanceEvent[]> {
  return apiRequest<InstanceEvent[]>(`/api/orgs/${organizationId}/instances/${instanceId}/events`);
}
