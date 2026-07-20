import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useMemo, useState } from "react";

import {
  addOrganizationMember,
  createOrganization,
  listOrganizationMembers,
  listOrganizations,
} from "../../api/organizations";
import { errorMessage } from "../../lib/errors";

type FormValues = {
  name: string;
};

type MemberFormValues = {
  email: string;
  role: "admin" | "member";
};

export function OrganizationsPage() {
  const queryClient = useQueryClient();
  const form = useForm<FormValues>();
  const memberForm = useForm<MemberFormValues>({ defaultValues: { role: "member" } });
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: listOrganizations,
  });
  const organizationId = selectedOrgId;
  const selectedOrg = useMemo(
    () => organizationsQuery.data?.find((org) => org.id === organizationId),
    [organizationId, organizationsQuery.data],
  );
  const membersQuery = useQuery({
    queryKey: ["organization-members", organizationId],
    queryFn: () => listOrganizationMembers(organizationId),
    enabled: Boolean(organizationId),
  });
  const createMutation = useMutation({
    mutationFn: (values: FormValues) => createOrganization(values.name),
    onSuccess: async (organization) => {
      form.reset();
      setSelectedOrgId(organization.id);
      await queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
  const addMemberMutation = useMutation({
    mutationFn: (values: MemberFormValues) => addOrganizationMember(organizationId, values),
    onSuccess: async () => {
      memberForm.reset({ role: "member", email: "" });
      await queryClient.invalidateQueries({ queryKey: ["organization-members", organizationId] });
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

      {createMutation.isError ? (
        <p className="form-error">{errorMessage(createMutation.error, "Organization could not be created.")}</p>
      ) : null}

      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          <article className="workspace-card">
            <div className="workspace-card__header">
              <div>
                <p className="eyebrow">Create</p>
                <h3>New workspace</h3>
              </div>
            </div>
            <form
              className="workspace-create-form"
              onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
            >
              <input placeholder="Organization name" {...form.register("name", { required: true })} />
              <button className="button" type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create"}
              </button>
            </form>
          </article>

          <article className="workspace-card">
            <div className="workspace-card__header">
              <div>
                <p className="eyebrow">Browse</p>
                <h3>Your organizations</h3>
              </div>
            </div>
            <div className="workspace-list">
              {organizationsQuery.data?.length ? (
                organizationsQuery.data.map((org) => (
                  <button
                    className={org.id === organizationId ? "workspace-item active" : "workspace-item"}
                    key={org.id}
                    type="button"
                    onClick={() => setSelectedOrgId(org.id)}
                  >
                    <span className="workspace-avatar">{org.name.slice(0, 1).toUpperCase()}</span>
                    <span>
                      <strong>{org.name}</strong>
                      <small>{humanize(org.role)}</small>
                    </span>
                  </button>
                ))
              ) : (
                <p className="muted">
                  {organizationsQuery.isLoading ? "Loading organizations..." : "No organizations yet."}
                </p>
              )}
            </div>
          </article>
        </aside>

        <main className="workspace-main">
          {selectedOrg ? (
            <>
              <article className="workspace-hero">
                <div className="workspace-avatar workspace-avatar--large">
                  {selectedOrg.name.slice(0, 1).toUpperCase()}
                </div>
                <div>
                  <p className="eyebrow">Selected workspace</p>
                  <h3>{selectedOrg.name}</h3>
                  <span>Your role: {humanize(selectedOrg.role)}</span>
                </div>
                <code>{selectedOrg.id}</code>
              </article>

              <div className="workspace-detail-grid">
                <article className="workspace-card">
                  <div className="workspace-card__header">
                    <div>
                      <p className="eyebrow">Team</p>
                      <h3>Members</h3>
                    </div>
                    <span className="count-pill">{membersQuery.data?.length ?? 0}</span>
                  </div>
                  <div className="member-list">
                    {membersQuery.data?.length ? (
                      membersQuery.data.map((member) => (
                        <div className="member-row" key={member.id}>
                          <span className="workspace-avatar">
                            {(member.full_name || member.email).slice(0, 1).toUpperCase()}
                          </span>
                          <div>
                            <strong>{member.full_name || member.email}</strong>
                            <span>{member.email}</span>
                          </div>
                          <span className="role-pill">{humanize(member.role)}</span>
                        </div>
                      ))
                    ) : (
                      <p className="muted">{membersQuery.isLoading ? "Loading members..." : "No members yet."}</p>
                    )}
                  </div>
                </article>

                <article className="workspace-card">
                  <div className="workspace-card__header">
                    <div>
                      <p className="eyebrow">Invite</p>
                      <h3>Add member</h3>
                    </div>
                  </div>
                  <form
                    className="member-form"
                    onSubmit={memberForm.handleSubmit((values) => addMemberMutation.mutate(values))}
                  >
                    <label>
                      Registered user email
                      <input
                        placeholder="teammate@example.com"
                        type="email"
                        {...memberForm.register("email", { required: true })}
                      />
                    </label>
                    <label>
                      Role
                      <select {...memberForm.register("role", { required: true })}>
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                      </select>
                    </label>
                    <button
                      className="button"
                      type="submit"
                      disabled={addMemberMutation.isPending || selectedOrg.role === "member"}
                    >
                      {addMemberMutation.isPending ? "Adding..." : "Add member"}
                    </button>
                    {selectedOrg.role === "member" ? (
                      <p className="field-hint">Only organization owners and admins can add members.</p>
                    ) : null}
                    <p className="field-hint">The user must register before you can add them.</p>
                  </form>
                  {addMemberMutation.isError ? (
                    <p className="form-error">
                      {errorMessage(addMemberMutation.error, "Member could not be added.")}
                    </p>
                  ) : null}
                </article>
              </div>
            </>
          ) : organizationsQuery.data?.length ? (
            <article className="workspace-empty-state">
              <h3>Choose a workspace</h3>
              <p>Select an organization from the left to manage its members.</p>
            </article>
          ) : (
            <article className="workspace-empty-state">
              <h3>Create your first workspace</h3>
              <p>Workspaces keep workflows, members, approvals, and runs grouped together.</p>
            </article>
          )}
        </main>
      </div>
    </section>
  );
}

function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
