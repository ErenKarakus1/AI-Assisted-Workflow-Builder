import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../../features/auth/AuthProvider";

export function AppLayout() {
  const navigate = useNavigate();
  const { signOut, user } = useAuth();

  return (
    <div className="layout">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Workflow Builder</p>
          <h1 className="app-title">Operations</h1>
        </div>
        <nav className="nav-list">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/organizations">Organizations</NavLink>
          <NavLink to="/workflows">Workflows</NavLink>
          <NavLink to="/tasks">Tasks</NavLink>
          <NavLink to="/runs">Runs</NavLink>
        </nav>
        <div className="sidebar-footer">
          <span>{user?.email}</span>
          <button
            type="button"
            className="button button--ghost"
            onClick={() => {
              signOut();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
