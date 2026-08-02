import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { queryClient } from "./app/queryClient";
import AppShell from "./app/AppShell";
import ProtectedRoute from "./app/ProtectedRoute";
import { RequireRole } from "./app/RequireRole";
import { AuthProvider } from "./auth/AuthContext";
import { ComingSoon } from "./components/ComingSoon";
import LoginPage from "./features/auth/LoginPage";
import ApprovalsPage from "./features/approvals/ApprovalsPage";
import BudgetPage from "./features/budget/BudgetPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import PaymentsPage from "./features/payments/PaymentsPage";
import BrandsPage from "./features/brands/BrandsPage";
import EquipmentPage from "./features/equipment/EquipmentPage";
import PipelinePage from "./features/tasks/PipelinePage";
import TTPage from "./features/tt/TTPage";

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
                <Route path="budget" element={<BudgetPage />} />
                <Route path="payments" element={<PaymentsPage />} />
                <Route path="tt" element={<TTPage />} />
                <Route path="approvals" element={<ApprovalsPage />} />
                <Route path="brands" element={<BrandsPage />} />
                <Route path="library" element={<EquipmentPage />} />
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
