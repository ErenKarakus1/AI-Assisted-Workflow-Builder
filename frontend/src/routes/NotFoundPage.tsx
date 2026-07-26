import { Link } from "react-router-dom";

type Props = {
  title?: string;
  description?: string;
  actionLabel?: string;
  actionTo?: string;
};

export function NotFoundPage({
  title = "Page not found",
  description = "The page you tried to open does not exist, or the link may be outdated.",
  actionLabel = "Go to dashboard",
  actionTo = "/",
}: Props) {
  return (
    <section className="not-found-page">
      <div className="not-found-card">
        <span>404</span>
        <h2>{title}</h2>
        <p>{description}</p>
        <Link className="button" to={actionTo}>
          {actionLabel}
        </Link>
      </div>
    </section>
  );
}
