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

export function WorkflowsPage() {
  const queryClient = useQueryClient();
  const form = useForm<FormValues>({ defaultValues: { templateId: "blank" } });
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

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Workflows</p>
          <h2>{selectedOrg ? selectedOrg.name : "Select an organization"}</h2>
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
          <form className="workflow-create-form" onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}>
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
          <div className="list-panel">
            {workflowsQuery.data?.length ? (
              workflowsQuery.data.map((workflow) => (
                <article className="list-row" key={workflow.id}>
                  <div>
                    <strong>{workflow.name}</strong>
                    <span>
                      {workflow.status} - revision {workflow.revision}
                    </span>
                  </div>
                  <Link className="text-link" to={`/workflows/${workflow.organization_id}/${workflow.id}`}>
                    Open
                  </Link>
                </article>
              ))
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
