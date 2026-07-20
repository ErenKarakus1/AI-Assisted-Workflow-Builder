import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { listOrganizations } from "../../api/organizations";
import { createWorkflow, listWorkflows } from "../../api/workflows";
import { workflowTemplates } from "./templates";

type FormValues = {
  name: string;
  templateId: string;
};

type WorkflowStatusFilter = "all" | "draft" | "active";

export function WorkflowsPage() {
  const queryClient = useQueryClient();
  const form = useForm<FormValues>({ defaultValues: { templateId: "blank" } });
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<WorkflowStatusFilter>("all");
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

  const workflowsQuery = useQuery({
    queryKey: ["workflows", organizationId],
    queryFn: () => listWorkflows(organizationId),
    enabled: Boolean(organizationId),
  });
  const createMutation = useMutation({
    mutationFn: (values: FormValues) => {
      const template = workflowTemplates.find((item) => item.id === values.templateId) ?? workflowTemplates[0];
      return createWorkflow(organizationId, values.name, template.nodes, template.edges);
    },
    onSuccess: async () => {
      form.reset({ templateId: "blank" });
      await queryClient.invalidateQueries({ queryKey: ["workflows", organizationId] });
    },
  });
  const selectedTemplate =
    workflowTemplates.find((template) => template.id === form.watch("templateId")) ?? workflowTemplates[0];
  const canManageWorkflows = selectedOrg ? selectedOrg.role === "owner" || selectedOrg.role === "admin" : false;
  const filteredWorkflows = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    return (workflowsQuery.data ?? []).filter((workflow) => {
      const matchesSearch = !normalizedSearch || workflow.name.toLowerCase().includes(normalizedSearch);
      const matchesStatus = statusFilter === "all" || workflow.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [searchTerm, statusFilter, workflowsQuery.data]);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Workflows</p>
          <h2>{selectedOrg ? selectedOrg.name : "Select an organization"}</h2>
          {selectedOrg ? <p className="muted">Your role: {humanize(selectedOrg.role)}</p> : null}
        </div>
        <select value={organizationId} onChange={(event) => setSelectedOrgId(event.target.value)}>
          {organizationsQuery.data?.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
      </div>
      {organizationId ? (
        <>
          {canManageWorkflows ? (
            <>
              <form
                className="workflow-create-form"
                onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
              >
                <input placeholder="Workflow name" {...form.register("name", { required: true })} />
                <select {...form.register("templateId")}>
                  {workflowTemplates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
                <button className="button" type="submit" disabled={createMutation.isPending}>
                  Create
                </button>
              </form>
              <p className="muted">{selectedTemplate.description}</p>
            </>
          ) : (
            <p className="help-panel">Members can view workflows and run active workflows, but only owners and admins can create or edit them.</p>
          )}

          <div className="filter-bar">
            <input
              placeholder="Search workflows"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as WorkflowStatusFilter)}
            >
              <option value="all">All statuses</option>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
            </select>
          </div>

          <div className="list-panel">
            {filteredWorkflows.length ? (
              filteredWorkflows.map((workflow) => (
                <article className="list-row" key={workflow.id}>
                  <div>
                    <strong>{workflow.name}</strong>
                    <span>
                      {humanize(workflow.status)} - revision {workflow.revision}
                    </span>
                  </div>
                  <Link className="text-link" to={`/workflows/${workflow.organization_id}/${workflow.id}`}>
                    Open
                  </Link>
                </article>
              ))
            ) : workflowsQuery.isLoading ? (
              <p className="muted">Loading workflows...</p>
            ) : workflowsQuery.data?.length ? (
              <p className="muted">No workflows match your filters.</p>
            ) : (
              <p className="muted">No workflows in this organization yet.</p>
            )}
          </div>
        </>
      ) : (
        <p className="muted">Create an organization before adding workflows.</p>
      )}
    </section>
  );
}

function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
