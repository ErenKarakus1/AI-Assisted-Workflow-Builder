import { apiRequest } from "./client";
import type { Task } from "../types/api";

export function listTasks(organizationId: string): Promise<Task[]> {
  return apiRequest<Task[]>(`/api/orgs/${organizationId}/tasks`);
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
