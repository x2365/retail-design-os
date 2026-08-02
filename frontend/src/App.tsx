import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { queryClient } from "./app/queryClient";
import { AuthProvider, useAuth } from "./auth/AuthContext";

function Shell() {
  const { user, isLoading } = useAuth();

  if (isLoading) return <p style={{ padding: 24 }}>Загрузка…</p>;

  return (
    <div style={{ padding: 24 }}>
      <h1>RetailDesign OS</h1>
      <p>
        {user
          ? `Вошли как ${user.full_name} (${user.role})`
          : "Не авторизованы — экран входа появится в следующем шаге."}
      </p>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Shell />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
