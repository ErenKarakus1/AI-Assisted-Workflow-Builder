import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listOrganizationMembers, listOrganizations } from "../../api/organizations";
import { approveTask, listTasks, rejectTask } from "../../api/tasks";
import { listWorkflows } from "../../api/workflows";
import { errorMessage } from "../../lib/errors";
import type { OrganizationMember, Task, TaskStatus, Workflow } from "../../types/api";
import { useAuth } from "../auth/AuthContext";

type TaskStatusFilter = "all" | TaskStatus;
type TaskAssignmentFilter = "all" | "actionable" | "user" | "role" | "oversight";

export function TasksPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const [submittedSearchTerm, setSubmittedSearchTerm] = useState("");
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

  const pendingTasksQuery = useInfiniteQuery({
    queryKey: ["tasks", organizationId, "pending", submittedSearchTerm],
    queryFn: ({ pageParam }) =>
      listTasks(organizationId, { status: "pending", limit: 50, before: pageParam, search: submittedSearchTerm }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    enabled: Boolean(organizationId) && statusFilter !== "completed",
  });
  const completedTasksQuery = useInfiniteQuery({
    queryKey: ["tasks", organizationId, "completed", submittedSearchTerm],
    queryFn: ({ pageParam }) =>
      listTasks(organizationId, { status: "completed", limit: 50, before: pageParam, search: submittedSearchTerm }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    enabled: Boolean(organizationId) && statusFilter !== "pending",
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
      await queryClient.invalidateQueries({ queryKey: ["workflow-instances", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["instance-events", organizationId] });
    },
  });
  const rejectMutation = useMutation({
    mutationFn: (task: Task) => rejectTask(organizationId, task),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tasks", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["workflow-instances", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["instance-events", organizationId] });
    },
  });

  const activeTaskId =
    approveMutation.variables?.id ?? rejectMutation.variables?.id ?? null;
  const workflowsById = useMemo(
    () => new Map((workflowsQuery.data ?? []).map((workflow) => [workflow.id, workflow])),
    [workflowsQuery.data],
  );
  const canSeeAllTasks = selectedOrg?.role === "owner" || selectedOrg?.role === "admin";
  const submitSearch = () => setSubmittedSearchTerm(searchTerm.trim());
  const clearSearch = () => {
    setSearchTerm("");
    setSubmittedSearchTerm("");
  };
  const pendingTasks = useMemo(
    () =>
      filterTasks({
        tasks: pendingTasksQuery.data?.pages.flatMap((page) => page.items) ?? [],
        assignmentFilter,
        userId: user?.id,
        role: selectedOrg?.role,
      }),
    [assignmentFilter, pendingTasksQuery.data, selectedOrg?.role, user?.id],
  );
  const completedTasks = useMemo(
    () =>
      filterTasks({
        tasks: completedTasksQuery.data?.pages.flatMap((page) => page.items) ?? [],
        assignmentFilter,
        userId: user?.id,
        role: selectedOrg?.role,
      }),
    [assignmentFilter, completedTasksQuery.data, selectedOrg?.role, user?.id],
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
          <div className="filter-bar filter-bar--tasks">
            <div className="search-control">
              <input
                placeholder="Search tasks by workflow, approval, or assignee"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    submitSearch();
                  }
                }}
              />
              <button className="button" type="button" onClick={submitSearch}>
                Search
              </button>
              {submittedSearchTerm ? (
                <button className="button button--ghost" type="button" onClick={clearSearch}>
                  Clear
                </button>
              ) : null}
            </div>
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
              emptyText={pendingTasksQuery.isLoading ? "Loading tasks..." : "No pending approvals match your filters."}
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
              hasNextPage={pendingTasksQuery.hasNextPage}
              isFetchingNextPage={pendingTasksQuery.isFetchingNextPage}
              onLoadMore={() => pendingTasksQuery.fetchNextPage()}
            />
          ) : null}
          {statusFilter !== "pending" ? (
            <TaskList
              title={canSeeAllTasks ? "Completed approvals" : "My completed approvals"}
              emptyText={completedTasksQuery.isLoading ? "Loading tasks..." : "No completed approvals match your filters."}
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
              hasNextPage={completedTasksQuery.hasNextPage}
              isFetchingNextPage={completedTasksQuery.isFetchingNextPage}
              onLoadMore={() => completedTasksQuery.fetchNextPage()}
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
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
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
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
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
      {hasNextPage ? (
        <div className="load-more-row load-more-row--tasks">
          <button
            className="button button--load-more"
            type="button"
            disabled={isFetchingNextPage}
            onClick={onLoadMore}
          >
            {isFetchingNextPage ? "Loading..." : "Load more"}
          </button>
        </div>
      ) : null}
    </article>
  );
}

function filterTasks({
  tasks,
  assignmentFilter,
  userId,
  role,
}: {
  tasks: Task[];
  assignmentFilter: TaskAssignmentFilter;
  userId: string | undefined;
  role: string | undefined;
}): Task[] {
  return tasks.filter((task) =>
    taskMatchesFilters({
      task,
      assignmentFilter,
      isActionable: isTaskActionable(task, userId, role),
    }),
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
  assignmentFilter,
  isActionable,
}: {
  task: Task;
  assignmentFilter: TaskAssignmentFilter;
  isActionable: boolean;
}): boolean {
  const matchesAssignment =
    assignmentFilter === "all" ||
    (assignmentFilter === "actionable" && isActionable) ||
    (assignmentFilter === "user" && Boolean(task.assigned_user_id)) ||
    (assignmentFilter === "role" && Boolean(task.assigned_role)) ||
    (assignmentFilter === "oversight" && !isActionable);

  return matchesAssignment;
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
    if (roleAssignmentMatches(task.assigned_role, currentRole)) {
      return `Assigned to your ${approvalRoleLabel(task.assigned_role)} group`;
    }
    return `Assigned to ${approvalRoleLabel(task.assigned_role)}`;
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
    return roleAssignmentMatches(task.assigned_role, role);
  }
  return false;
}

function roleAssignmentMatches(assignedRole: string, role: string | undefined): boolean {
  if (!role) {
    return false;
  }
  if (assignedRole === "all") {
    return true;
  }
  if (assignedRole === "owner_or_admin") {
    return role === "owner" || role === "admin";
  }
  return assignedRole === role;
}

function approvalRoleLabel(role: string): string {
  if (role === "owner_or_admin") {
    return "Owner or Admin";
  }
  if (role === "all") {
    return "Anyone in the org";
  }
  return `${humanize(role)} role`;
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
