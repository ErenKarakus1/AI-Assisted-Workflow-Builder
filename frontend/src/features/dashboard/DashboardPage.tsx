import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listWorkflowInstances } from "../../api/instances";
import { listOrganizations } from "../../api/organizations";
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
  const activity = dashboardQuery.data;

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
          <strong>{activity?.organizations.length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Workflows</span>
          <strong>{activity?.workflows.length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Active workflows</span>
          <strong>{activity?.workflows.filter((workflow) => workflow.status === "active").length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Pending approvals</span>
          <strong>{activity?.tasks.filter((task) => task.status === "pending").length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Runs</span>
          <strong>{activity?.instances.length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Waiting runs</span>
          <strong>{activity?.instances.filter((instance) => instance.status === "waiting").length ?? 0}</strong>
        </article>
      </div>

      <div className="split-panel">
        <article className="list-panel">
          <div className="panel-heading">Recent workflow runs</div>
          {activity?.instances.length ? (
            activity.instances.slice(0, 6).map((instance) => (
              <div className="compact-row dashboard-row" key={instance.id}>
                <strong>{workflowName(instance.workflow_id, activity.workflows)}</strong>
                <span>
                  {humanize(instance.status)} - instance {shortId(instance.id)}
                </span>
                <Link className="text-link" to={`/workflows/${instance.organization_id}/${instance.workflow_id}`}>
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
                  <span>{task.assigned_role ? `Assigned to ${humanize(task.assigned_role)} role` : "Assigned to a user"}</span>
                  <Link className="text-link" to="/tasks">
                    Review task
                  </Link>
                </div>
              ))
          ) : (
            <p className="muted">{dashboardQuery.isLoading ? "Loading tasks..." : "No pending approvals."}</p>
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
  const taskGroups = await Promise.all(organizations.map((org) => listTasks(org.id)));
  const workflows = workflowGroups.flat();
  const tasks = taskGroups.flat();
  const instanceGroups = await Promise.all(
    workflows.map((workflow) => listWorkflowInstances(workflow.organization_id, workflow.id)),
  );

  return {
    organizations,
    workflows,
    tasks,
    instances: instanceGroups.flat(),
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
