import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../features/auth/AuthProvider";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <main className="centered-page">Loading...</main>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

