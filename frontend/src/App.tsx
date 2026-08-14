import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { queryClient } from "./app/queryClient";
import AppShell from "./app/AppShell";
import ErrorBoundary from "./app/ErrorBoundary";
import ProtectedRoute from "./app/ProtectedRoute";
import { RequireRole } from "./app/RequireRole";
import { AuthProvider } from "./auth/AuthContext";
import LoginPage from "./features/auth/LoginPage";
import ApprovalsPage from "./features/approvals/ApprovalsPage";
import ArchivePage from "./features/archive/ArchivePage";
import BudgetPage from "./features/budget/BudgetPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import GanttPage from "./features/gantt/GanttPage";
import MetricsPage from "./features/metrics/MetricsPage";
import PaymentsPage from "./features/payments/PaymentsPage";
import BrandsPage from "./features/brands/BrandsPage";
import EquipmentPage from "./features/equipment/EquipmentPage";
import PipelinePage from "./features/tasks/PipelinePage";
import TTPage from "./features/tt/TTPage";
import UsersPage from "./features/users/UsersPage";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <ErrorBoundary>
            <Routes>
              <Route path="/login" element={<LoginPage />} />

              <Route element={<ProtectedRoute />}>
                <Route element={<AppShell />}>
                  <Route index element={<DashboardPage />} />
                  <Route path="pipeline" element={<PipelinePage />} />
                  <Route path="metrics" element={<MetricsPage />} />
                  <Route path="gantt" element={<GanttPage />} />
                  <Route path="archive" element={<ArchivePage />} />
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
                        <UsersPage />
                      </RequireRole>
                    }
                  />
                </Route>
              </Route>
            </Routes>
          </ErrorBoundary>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
