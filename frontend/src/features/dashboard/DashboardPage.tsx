import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listOrganizationRuns } from "../../api/instances";
import { getDashboardStats, listOrganizations } from "../../api/organizations";
import { listTasks } from "../../api/tasks";
import { listWorkflows } from "../../api/workflows";
import type { Organization, Task, Workflow, WorkflowInstance } from "../../types/api";
import { useAuth } from "../auth/AuthProvider";

export function DashboardPage() {
  const { user } = useAuth();
  const dashboardQuery = useQuery({
    queryKey: ["dashboard-activity"],
    queryFn: loadDashboardActivity,
  });
  const statsQuery = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
  });
  const activity = dashboardQuery.data;
  const stats = statsQuery.data;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h2>Good to see you, {user?.full_name}</h2>
        </div>
        <div className="action-row">
          <Link className="button" to="/workflows">
            Open workflows
          </Link>
          <Link className="button button--ghost" to="/tasks">
            Review tasks
          </Link>
        </div>
      </div>
      <div className="metric-grid">
        <article className="metric-card">
          <span>Organizations</span>
          <strong>{stats?.organizations ?? activity?.organizations.length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Workflows</span>
          <strong>{stats?.workflows ?? activity?.workflows.length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Active workflows</span>
          <strong>{stats?.active_workflows ?? activity?.workflows.filter((workflow) => workflow.status === "active").length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Pending approvals</span>
          <strong>{stats?.pending_approvals ?? activity?.tasks.filter((task) => task.status === "pending").length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Runs</span>
          <strong>{stats?.runs ?? activity?.instances.length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Waiting runs</span>
          <strong>{stats?.waiting_runs ?? activity?.instances.filter((instance) => instance.status === "waiting").length ?? 0}</strong>
        </article>
      </div>

      <div className="split-panel dashboard-panel-grid">
        <article className="list-panel">
          <div className="panel-heading">
            <span>Recent workflow runs</span>
            <Link className="text-link" to="/runs">
              View runs
            </Link>
          </div>
          {activity?.instances.length ? (
            activity.instances.slice(0, 6).map((instance) => (
              <div className="compact-row dashboard-row" key={instance.id}>
                <strong>{workflowName(instance.workflow_id, activity.workflows)}</strong>
                <span>
                  {humanize(instance.status)} - instance {shortId(instance.id)}
                </span>
                <Link
                  className="text-link"
                  to={`/workflows/${instance.organization_id}/${instance.workflow_id}?instance=${instance.id}`}
                >
                  Open run
                </Link>
              </div>
            ))
          ) : (
            <p className="muted">{dashboardQuery.isLoading ? "Loading activity..." : "No workflow runs yet."}</p>
          )}
        </article>

        <article className="list-panel">
          <div className="panel-heading">Pending approvals</div>
          {activity?.tasks.filter((task) => task.status === "pending").length ? (
            activity.tasks
              .filter((task) => task.status === "pending")
              .slice(0, 6)
              .map((task) => (
                <div className="compact-row dashboard-row" key={task.id}>
                  <strong>{workflowName(task.workflow_id, activity.workflows)}</strong>
                  <span>{task.assigned_role ? `Assigned to ${approvalRoleLabel(task.assigned_role)}` : "Assigned to a user"}</span>
                  <Link className="text-link" to="/tasks">
                    Review task
                  </Link>
                </div>
              ))
          ) : (
            <div className="dashboard-empty-state">
              <strong>{dashboardQuery.isLoading ? "Loading approvals..." : "No approvals waiting"}</strong>
              <span>
                {dashboardQuery.isLoading
                  ? "Checking your organizations for pending tasks."
                  : "New approval tasks will show up here when a workflow reaches an approval node."}
              </span>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}

type DashboardActivity = {
  organizations: Organization[];
  workflows: Workflow[];
  tasks: Task[];
  instances: WorkflowInstance[];
};

async function loadDashboardActivity(): Promise<DashboardActivity> {
  const organizations = await listOrganizations();
  const workflowGroups = await Promise.all(organizations.map((org) => listWorkflows(org.id)));
  const taskGroups = await Promise.all(organizations.map((org) => listTasks(org.id, { status: "pending", limit: 6 })));
  const instanceGroups = await Promise.all(organizations.map((org) => listOrganizationRuns(org.id, { limit: 6 })));
  const workflows = workflowGroups.flat();

  return {
    organizations,
    workflows,
    tasks: taskGroups.flatMap((group) => group.items),
    instances: instanceGroups.flatMap((group) => group.items),
  };
}

function workflowName(workflowId: string, workflows: Workflow[]): string {
  return workflows.find((workflow) => workflow.id === workflowId)?.name ?? "Workflow";
}

function shortId(value: string): string {
  return value.length > 8 ? value.slice(0, 8) : value;
}

function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
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
