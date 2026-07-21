import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { listOrganizationRuns } from "../../api/instances";
import { listOrganizations } from "../../api/organizations";
import { listWorkflows } from "../../api/workflows";
import type { Workflow, WorkflowInstanceStatus } from "../../types/api";

type RunStatusFilter = "all" | WorkflowInstanceStatus;

export function RunsPage() {
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [statusFilter, setStatusFilter] = useState<RunStatusFilter>("all");
  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: listOrganizations,
  });
  const organizationId = selectedOrgId || organizationsQuery.data?.[0]?.id || "";
  const workflowsQuery = useQuery({
    queryKey: ["workflows", organizationId],
    queryFn: () => listWorkflows(organizationId),
    enabled: Boolean(organizationId),
  });
  const runsQuery = useInfiniteQuery({
    queryKey: ["runs", organizationId, statusFilter],
    queryFn: ({ pageParam }) =>
      listOrganizationRuns(organizationId, { status: statusFilter, limit: 50, before: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    enabled: Boolean(organizationId),
  });
  const workflowsById = useMemo(
    () => new Map((workflowsQuery.data ?? []).map((workflow) => [workflow.id, workflow])),
    [workflowsQuery.data],
  );
  const runs = runsQuery.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Runs</p>
          <h2>Workflow runs</h2>
        </div>
      </div>

      <div className="filter-bar">
        <label>
          Organization
          <select value={organizationId} onChange={(event) => setSelectedOrgId(event.target.value)}>
            {(organizationsQuery.data ?? []).map((organization) => (
              <option key={organization.id} value={organization.id}>
                {organization.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as RunStatusFilter)}>
            {runStatusFilters.map((status) => (
              <option key={status} value={status}>
                {humanize(status)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <article className="list-panel">
        <div className="panel-heading">Instances</div>
        {runs.length ? (
          runs.map((instance) => (
            <div className="compact-row run-row" key={instance.id}>
              <div className="run-row__title">
                <strong>{workflowName(instance.workflow_id, workflowsById)}</strong>
                <span>
                  {humanize(instance.status)} · instance {shortId(instance.id)} · rev {instance.workflow_revision}
                </span>
              </div>
              <div className="run-row__meta">
                <span>Started {formatDateTime(instance.started_at)}</span>
                <span>Active node: {instance.active_node_id ?? "None"}</span>
              </div>
              <Link
                className="text-link"
                to={`/workflows/${instance.organization_id}/${instance.workflow_id}?instance=${instance.id}`}
              >
                Open run
              </Link>
            </div>
          ))
        ) : (
          <p className="muted">{runsQuery.isLoading ? "Loading runs..." : "No runs match your filters."}</p>
        )}
        {runsQuery.hasNextPage ? (
          <div className="load-more-row load-more-row--runs">
            <button
              className="button button--ghost"
              type="button"
              disabled={runsQuery.isFetchingNextPage}
              onClick={() => runsQuery.fetchNextPage()}
            >
              {runsQuery.isFetchingNextPage ? "Loading..." : "Load more"}
            </button>
          </div>
        ) : null}
      </article>
    </section>
  );
}

const runStatusFilters: RunStatusFilter[] = ["all", "running", "waiting", "completed", "failed"];

function workflowName(workflowId: string, workflowsById: Map<string, Workflow>): string {
  return workflowsById.get(workflowId)?.name ?? "Workflow";
}

function shortId(value: string): string {
  return value.length > 8 ? value.slice(0, 8) : value;
}

function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
