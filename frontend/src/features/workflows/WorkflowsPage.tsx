import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { listOrganizations } from "../../api/organizations";
import { createWorkflow, listWorkflows } from "../../api/workflows";

type FormValues = {
  name: string;
};

export function WorkflowsPage() {
  const queryClient = useQueryClient();
  const form = useForm<FormValues>();
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
    mutationFn: (values: FormValues) => createWorkflow(organizationId, values.name),
    onSuccess: async () => {
      form.reset();
      await queryClient.invalidateQueries({ queryKey: ["workflows", organizationId] });
    },
  });

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
          <form className="inline-form" onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}>
            <input placeholder="Workflow name" {...form.register("name", { required: true })} />
            <button className="button" type="submit" disabled={createMutation.isPending}>
              Create
            </button>
          </form>
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
