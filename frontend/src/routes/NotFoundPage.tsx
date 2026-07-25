import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="not-found-page">
      <div className="not-found-card">
        <span>404</span>
        <h2>Page not found</h2>
        <p>The page you tried to open does not exist, or the link may be outdated.</p>
        <Link className="button" to="/">
          Go to dashboard
        </Link>
      </div>
    </section>
  );
}
