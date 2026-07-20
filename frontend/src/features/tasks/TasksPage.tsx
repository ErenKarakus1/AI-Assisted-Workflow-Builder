import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listOrganizationMembers, listOrganizations } from "../../api/organizations";
import { approveTask, listTasks, rejectTask } from "../../api/tasks";
import { listWorkflows } from "../../api/workflows";
import { errorMessage } from "../../lib/errors";
import type { OrganizationMember, Task, Workflow } from "../../types/api";
import { useAuth } from "../auth/AuthProvider";

type TaskStatusFilter = "all" | "pending" | "completed";
type TaskAssignmentFilter = "all" | "actionable" | "user" | "role" | "oversight";

export function TasksPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<TaskStatusFilter>("all");
  const [assignmentFilter, setAssignmentFilter] = useState<TaskAssignmentFilter>("all");
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
  const membersQuery = useQuery({
    queryKey: ["organization-members", organizationId],
    queryFn: () => listOrganizationMembers(organizationId),
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

  const activeTaskId =
    approveMutation.variables?.id ?? rejectMutation.variables?.id ?? null;
  const workflowsById = useMemo(
    () => new Map((workflowsQuery.data ?? []).map((workflow) => [workflow.id, workflow])),
    [workflowsQuery.data],
  );
  const canSeeAllTasks = selectedOrg?.role === "owner" || selectedOrg?.role === "admin";
  const filteredTasks = useMemo(
    () =>
      (tasksQuery.data ?? []).filter((task) =>
        taskMatchesFilters({
          task,
          workflowsById,
          searchTerm,
          statusFilter,
          assignmentFilter,
          isActionable: isTaskActionable(task, user?.id, selectedOrg?.role),
        }),
      ),
    [assignmentFilter, searchTerm, selectedOrg?.role, statusFilter, tasksQuery.data, user?.id, workflowsById],
  );
  const pendingTasks = useMemo(
    () => filteredTasks.filter((task) => task.status === "pending"),
    [filteredTasks],
  );
  const completedTasks = useMemo(
    () => filteredTasks.filter((task) => task.status === "completed"),
    [filteredTasks],
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
          <div className="filter-bar filter-bar--three">
            <input
              placeholder="Search tasks by workflow or approval"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as TaskStatusFilter)}>
              <option value="all">All statuses</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
            </select>
            <select
              value={assignmentFilter}
              onChange={(event) => setAssignmentFilter(event.target.value as TaskAssignmentFilter)}
            >
              <option value="all">All assignments</option>
              <option value="actionable">Actionable by me</option>
              <option value="user">Assigned to users</option>
              <option value="role">Assigned to roles</option>
              {canSeeAllTasks ? <option value="oversight">Oversight only</option> : null}
            </select>
          </div>

          {statusFilter !== "completed" ? (
            <TaskList
              title={canSeeAllTasks ? "Pending approvals" : "My pending approvals"}
              emptyText={tasksQuery.isLoading ? "Loading tasks..." : "No pending approvals match your filters."}
              tasks={pendingTasks}
              workflowsById={workflowsById}
              members={membersQuery.data ?? []}
              currentUserId={user?.id}
              currentRole={selectedOrg?.role}
              activeTaskId={activeTaskId}
              isDeciding={approveMutation.isPending || rejectMutation.isPending}
              showActions
              isTaskActionable={(task) => isTaskActionable(task, user?.id, selectedOrg?.role)}
              onApprove={(task) => approveMutation.mutate(task)}
              onReject={(task) => rejectMutation.mutate(task)}
            />
          ) : null}
          {statusFilter !== "pending" ? (
            <TaskList
              title={canSeeAllTasks ? "Completed approvals" : "My completed approvals"}
              emptyText="No completed approvals match your filters."
              tasks={completedTasks}
              workflowsById={workflowsById}
              members={membersQuery.data ?? []}
              currentUserId={user?.id}
              currentRole={selectedOrg?.role}
              activeTaskId={activeTaskId}
              isDeciding={false}
              showActions={false}
              isTaskActionable={() => false}
              onApprove={() => undefined}
              onReject={() => undefined}
            />
          ) : null}
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
  members,
  currentUserId,
  currentRole,
  activeTaskId,
  isDeciding,
  showActions,
  isTaskActionable,
  onApprove,
  onReject,
}: {
  title: string;
  emptyText: string;
  tasks: Task[];
  workflowsById: Map<string, Workflow>;
  members: OrganizationMember[];
  currentUserId: string | undefined;
  currentRole: string | undefined;
  activeTaskId: string | null;
  isDeciding: boolean;
  showActions: boolean;
  isTaskActionable: (task: Task) => boolean;
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
              <span>{assignmentLabel(task, members, currentUserId, currentRole)}</span>
              {task.decision ? <span>Decision: {humanize(task.decision)}</span> : null}
            </div>
            <div className="row-actions">
              <Link className="text-link" to={`/workflows/${task.organization_id}/${task.workflow_id}`}>
                Open workflow
              </Link>
              {showActions && isTaskActionable(task) ? (
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
              ) : showActions ? (
                <span className="muted">Visible for oversight</span>
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

function taskMatchesFilters({
  task,
  workflowsById,
  searchTerm,
  statusFilter,
  assignmentFilter,
  isActionable,
}: {
  task: Task;
  workflowsById: Map<string, Workflow>;
  searchTerm: string;
  statusFilter: TaskStatusFilter;
  assignmentFilter: TaskAssignmentFilter;
  isActionable: boolean;
}): boolean {
  const normalizedSearch = searchTerm.trim().toLowerCase();
  const searchableText = [
    workflowName(task, workflowsById),
    taskLabel(task, workflowsById),
    task.instance_id,
    task.assigned_role ?? "",
    task.assigned_user_id ?? "",
  ].join(" ").toLowerCase();
  const matchesSearch = !normalizedSearch || searchableText.includes(normalizedSearch);
  const matchesStatus = statusFilter === "all" || task.status === statusFilter;
  const matchesAssignment =
    assignmentFilter === "all" ||
    (assignmentFilter === "actionable" && isActionable) ||
    (assignmentFilter === "user" && Boolean(task.assigned_user_id)) ||
    (assignmentFilter === "role" && Boolean(task.assigned_role)) ||
    (assignmentFilter === "oversight" && !isActionable);

  return matchesSearch && matchesStatus && matchesAssignment;
}

function assignmentLabel(
  task: Task,
  members: OrganizationMember[],
  currentUserId: string | undefined,
  currentRole: string | undefined,
): string {
  if (task.assigned_user_id) {
    const assignedMember = members.find((member) => member.user_id === task.assigned_user_id);
    if (task.assigned_user_id === currentUserId) {
      return "Assigned to you";
    }
    return `Assigned to ${assignedMember ? memberLabel(assignedMember) : `user ${shortId(task.assigned_user_id)}`}`;
  }
  if (task.assigned_role) {
    if (task.assigned_role === currentRole) {
      return `Assigned to your ${humanize(task.assigned_role)} role`;
    }
    return `Assigned to ${humanize(task.assigned_role)} role`;
  }
  return "Unassigned";
}

function isTaskActionable(task: Task, userId: string | undefined, role: string | undefined): boolean {
  if (!userId || task.status !== "pending") {
    return false;
  }
  if (task.assigned_user_id) {
    return task.assigned_user_id === userId;
  }
  if (task.assigned_role) {
    return task.assigned_role === role;
  }
  return false;
}

function memberLabel(member: OrganizationMember): string {
  return member.full_name ? `${member.full_name} (${member.email})` : member.email;
}

function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function shortId(value: string): string {
  return value.length > 8 ? value.slice(0, 8) : value;
}

function stringValue(value: unknown): string {
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : "";
}
