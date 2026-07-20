import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { createOrganization, listOrganizations } from "../../api/organizations";

type FormValues = {
  name: string;
};

export function OrganizationsPage() {
  const queryClient = useQueryClient();
  const form = useForm<FormValues>();
  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: listOrganizations,
  });
  const createMutation = useMutation({
    mutationFn: (values: FormValues) => createOrganization(values.name),
    onSuccess: async () => {
      form.reset();
      await queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Organizations</p>
          <h2>Workspaces</h2>
        </div>
      </div>
      <form className="inline-form" onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}>
        <input placeholder="Organization name" {...form.register("name", { required: true })} />
        <button className="button" type="submit" disabled={createMutation.isPending}>
          Create
        </button>
      </form>
      <div className="list-panel">
        {organizationsQuery.data?.length ? (
          organizationsQuery.data.map((org) => (
            <article className="list-row" key={org.id}>
              <div>
                <strong>{org.name}</strong>
                <span>{org.role}</span>
              </div>
              <code>{org.id}</code>
            </article>
          ))
        ) : (
          <p className="muted">No organizations yet.</p>
        )}
      </div>
    </section>
  );
}

