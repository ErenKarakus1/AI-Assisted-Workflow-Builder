import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listOrganizations } from "../../api/organizations";
import { approveTask, listTasks, rejectTask } from "../../api/tasks";
import { listWorkflows } from "../../api/workflows";
import { errorMessage } from "../../lib/errors";
import type { Task, Workflow } from "../../types/api";

export function TasksPage() {
  const queryClient = useQueryClient();
  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: listOrganizations,
  });
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const organizationId = selectedOrgId || organizationsQuery.data?.[0]?.id || "";
  const selectedOrg = useMemo(
    () => organizationsQuery.data?.find((org) => org.id === organizationId),
    [organizationId, organizationsQuery.data],
  );

  const tasksQuery = useQuery({
    queryKey: ["tasks", organizationId],
    queryFn: () => listTasks(organizationId),
    enabled: Boolean(organizationId),
  });
  const workflowsQuery = useQuery({
    queryKey: ["workflows", organizationId],
    queryFn: () => listWorkflows(organizationId),
    enabled: Boolean(organizationId),
  });

  const approveMutation = useMutation({
    mutationFn: (task: Task) => approveTask(organizationId, task),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tasks", organizationId] });
    },
  });
  const rejectMutation = useMutation({
    mutationFn: (task: Task) => rejectTask(organizationId, task),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tasks", organizationId] });
    },
  });

  const pendingTasks = useMemo(
    () => tasksQuery.data?.filter((task) => task.status === "pending") ?? [],
    [tasksQuery.data],
  );
  const completedTasks = useMemo(
    () => tasksQuery.data?.filter((task) => task.status === "completed") ?? [],
    [tasksQuery.data],
  );
  const activeTaskId =
    approveMutation.variables?.id ?? rejectMutation.variables?.id ?? null;
  const workflowsById = useMemo(
    () => new Map((workflowsQuery.data ?? []).map((workflow) => [workflow.id, workflow])),
    [workflowsQuery.data],
  );

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Tasks</p>
          <h2>{selectedOrg ? `${selectedOrg.name} inbox` : "Select an organization"}</h2>
        </div>
        <select value={organizationId} onChange={(event) => setSelectedOrgId(event.target.value)}>
          {organizationsQuery.data?.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
      </div>

      {approveMutation.isError ? (
        <p className="form-error">{errorMessage(approveMutation.error, "Task could not be approved.")}</p>
      ) : null}
      {rejectMutation.isError ? (
        <p className="form-error">{errorMessage(rejectMutation.error, "Task could not be rejected.")}</p>
      ) : null}

      {organizationId ? (
        <>
          <TaskList
            title="Pending approvals"
            emptyText={tasksQuery.isLoading ? "Loading tasks..." : "No pending approval tasks."}
            tasks={pendingTasks}
            workflowsById={workflowsById}
            activeTaskId={activeTaskId}
            isDeciding={approveMutation.isPending || rejectMutation.isPending}
            showActions
            onApprove={(task) => approveMutation.mutate(task)}
            onReject={(task) => rejectMutation.mutate(task)}
          />
          <TaskList
            title="Completed approvals"
            emptyText="No completed approval tasks yet."
            tasks={completedTasks}
            workflowsById={workflowsById}
            activeTaskId={activeTaskId}
            isDeciding={false}
            showActions={false}
            onApprove={() => undefined}
            onReject={() => undefined}
          />
        </>
      ) : (
        <p className="muted">Create an organization before reviewing tasks.</p>
      )}
    </section>
  );
}

function TaskList({
  title,
  emptyText,
  tasks,
  workflowsById,
  activeTaskId,
  isDeciding,
  showActions,
  onApprove,
  onReject,
}: {
  title: string;
  emptyText: string;
  tasks: Task[];
  workflowsById: Map<string, Workflow>;
  activeTaskId: string | null;
  isDeciding: boolean;
  showActions: boolean;
  onApprove: (task: Task) => void;
  onReject: (task: Task) => void;
}) {
  return (
    <article className="list-panel">
      <div className="panel-heading">{title}</div>
      {tasks.length ? (
        tasks.map((task) => (
          <div className="list-row approval-card" key={task.id}>
            <div>
              <p className="eyebrow">{workflowName(task, workflowsById)}</p>
              <strong>{taskLabel(task, workflowsById)}</strong>
              <span>
                Instance {shortId(task.instance_id)} - task revision {task.revision}
              </span>
              <span>{assignmentLabel(task)}</span>
              {task.decision ? <span>Decision: {task.decision}</span> : null}
            </div>
            <div className="row-actions">
              <Link className="text-link" to={`/workflows/${task.organization_id}/${task.workflow_id}`}>
                Open workflow
              </Link>
              {showActions ? (
                <>
                  <button
                    className="button"
                    type="button"
                    disabled={isDeciding && activeTaskId === task.id}
                    onClick={() => onApprove(task)}
                  >
                    {isDeciding && activeTaskId === task.id ? "Working..." : "Approve"}
                  </button>
                  <button
                    className="button button--ghost"
                    type="button"
                    disabled={isDeciding && activeTaskId === task.id}
                    onClick={() => onReject(task)}
                  >
                    Reject
                  </button>
                </>
              ) : null}
            </div>
          </div>
        ))
      ) : (
        <p className="muted">{emptyText}</p>
      )}
    </article>
  );
}

function taskLabel(task: Task, workflowsById: Map<string, Workflow>): string {
  const workflow = workflowsById.get(task.workflow_id);
  const node = workflow?.nodes.find((workflowNode) => workflowNode.id === task.node_id);
  const nodeName = node ? stringValue(node.data.label).trim() : "";
  return nodeName ? nodeName : `Approval at ${task.node_id}`;
}

function workflowName(task: Task, workflowsById: Map<string, Workflow>): string {
  return workflowsById.get(task.workflow_id)?.name ?? "Workflow approval";
}

function assignmentLabel(task: Task): string {
  if (task.assigned_user_id) {
    return `Assigned to user ${shortId(task.assigned_user_id)}`;
  }
  if (task.assigned_role) {
    return `Assigned to ${task.assigned_role}`;
  }
  return "Unassigned";
}

function shortId(value: string): string {
  return value.length > 8 ? value.slice(0, 8) : value;
}

function stringValue(value: unknown): string {
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : "";
}
