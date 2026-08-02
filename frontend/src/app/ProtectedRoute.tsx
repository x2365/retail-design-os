import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function ProtectedRoute() {
  const { user, isLoading } = useAuth();

  if (isLoading) return <p style={{ padding: 24 }}>Загрузка…</p>;
  if (!user) return <Navigate to="/login" replace />;

  return <Outlet />;
}
