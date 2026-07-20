import { useQuery } from "@tanstack/react-query";

import { getHealth } from "../api/health";

export function App() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    retry: false,
  });

  const apiStatus = healthQuery.data?.status ?? (healthQuery.isError ? "offline" : "checking");

  return (
    <main className="app-shell">
      <section className="intro-panel">
        <p className="eyebrow">Workflow automation</p>
        <h1>AI-Assisted Workflow Builder</h1>
        <p className="lede">
          A focused platform for visual approval workflows, deterministic execution, and optional
          AI documentation and review.
        </p>
        <div className="status-row">
          <span className={`status-dot status-dot--${apiStatus}`} />
          <span>API status: {apiStatus}</span>
        </div>
      </section>
    </main>
  );
}

