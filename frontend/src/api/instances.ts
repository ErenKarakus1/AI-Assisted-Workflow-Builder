import { apiRequest } from "./client";
import type { InstanceEvent, WorkflowInstance, WorkflowInstancePage, WorkflowInstanceStatus } from "../types/api";

export function listWorkflowInstances(
  organizationId: string,
  workflowId: string,
): Promise<WorkflowInstance[]> {
  return apiRequest<WorkflowInstance[]>(
    `/api/orgs/${organizationId}/workflows/${workflowId}/instances`,
  );
}

export function listOrganizationRuns(
  organizationId: string,
  options: { status?: WorkflowInstanceStatus | "all"; limit?: number; before?: string | null } = {},
): Promise<WorkflowInstancePage> {
  const params = new URLSearchParams();
  if (options.status && options.status !== "all") {
    params.set("status", options.status);
  }
  if (options.limit) {
    params.set("limit", String(options.limit));
  }
  if (options.before) {
    params.set("before", options.before);
  }
  const query = params.toString();
  return apiRequest<WorkflowInstancePage>(`/api/orgs/${organizationId}/runs${query ? `?${query}` : ""}`);
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
