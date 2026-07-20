import { useQuery } from "@tanstack/react-query";

import { listOrganizations } from "../../api/organizations";
import { useAuth } from "../auth/AuthProvider";

export function DashboardPage() {
  const { user } = useAuth();
  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: listOrganizations,
  });

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h2>Good to see you, {user?.full_name}</h2>
        </div>
      </div>
      <div className="metric-grid">
        <article className="metric-card">
          <span>Organizations</span>
          <strong>{organizationsQuery.data?.length ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Workflow editor</span>
          <strong>Next</strong>
        </article>
        <article className="metric-card">
          <span>AI review</span>
          <strong>Later</strong>
        </article>
      </div>
    </section>
  );
}

