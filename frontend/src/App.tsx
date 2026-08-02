import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { queryClient } from "./app/queryClient";
import AppShell from "./app/AppShell";
import ProtectedRoute from "./app/ProtectedRoute";
import { RequireRole } from "./app/RequireRole";
import { AuthProvider } from "./auth/AuthContext";
import { ComingSoon } from "./components/ComingSoon";
import LoginPage from "./features/auth/LoginPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import PipelinePage from "./features/tasks/PipelinePage";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route index element={<DashboardPage />} />
                <Route path="pipeline" element={<PipelinePage />} />
                <Route path="gantt" element={<ComingSoon title="Таймлайн" />} />
                <Route path="archive" element={<ComingSoon title="Архив задач" />} />
                <Route path="budget" element={<ComingSoon title="Бюджеты" />} />
                <Route path="payments" element={<ComingSoon title="Оплаты / КП" />} />
                <Route path="tt" element={<ComingSoon title="Торговые точки" />} />
                <Route path="approvals" element={<ComingSoon title="Согласования" />} />
                <Route path="brands" element={<ComingSoon title="Бренды" />} />
                <Route path="library" element={<ComingSoon title="Библиотека" />} />
                <Route
                  path="users"
                  element={
                    <RequireRole roles={["admin"]}>
                      <ComingSoon title="Пользователи" />
                    </RequireRole>
                  }
                />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
