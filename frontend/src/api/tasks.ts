import { apiRequest } from "./client";
import type { Task, TaskPage, TaskStatus } from "../types/api";

export function listTasks(
  organizationId: string,
  options: { status?: TaskStatus | "all"; limit?: number; before?: string | null; search?: string } = {},
): Promise<TaskPage> {
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
  if (options.search?.trim()) {
    params.set("search", options.search.trim());
  }
  const query = params.toString();
  return apiRequest<TaskPage>(`/api/orgs/${organizationId}/tasks${query ? `?${query}` : ""}`);
}

export function approveTask(organizationId: string, task: Task): Promise<Task> {
  return decideTask(organizationId, task, "approve");
}

export function rejectTask(organizationId: string, task: Task): Promise<Task> {
  return decideTask(organizationId, task, "reject");
}

function decideTask(
  organizationId: string,
  task: Task,
  decision: "approve" | "reject",
): Promise<Task> {
  return apiRequest<Task>(`/api/orgs/${organizationId}/tasks/${task.id}/${decision}`, {
    method: "POST",
    body: JSON.stringify({ revision: task.revision }),
  });
}
