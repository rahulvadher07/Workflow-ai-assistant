import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { NotificationProvider } from "./context/NotificationContext";
import { RealtimeProvider } from "./context/RealtimeProvider";
import ProtectedRoute from "./routes/ProtectedRoute";
import AuthLayout from "./layouts/AuthLayout";
import AppLayout from "./layouts/AppLayout";

import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import DashboardPage from "./pages/dashboard/DashboardPage";
import AIAgentPage from "./pages/ai/AIAgentPage";
import WorkspacePage from "./pages/workspace/WorkspacePage";
import AttendancePage from "./pages/attendance/AttendancePage";
import NotificationsPage from "./pages/notifications/NotificationsPage";
import PayrollPage from "./pages/payroll/PayrollPage";
import ProfilePage from "./pages/profile/ProfilePage";
import TeamManagementPage from "./pages/team/TeamManagementPage";
import RegistrationsPage from "./pages/team/RegistrationsPage";
import EmployeesPage from "./pages/admin/EmployeesPage";
import HODsPage from "./pages/admin/HODsPage";
import DepartmentsPage from "./pages/admin/DepartmentsPage";
import CompanyRulesPage from "./pages/admin/CompanyRulesPage";
import KnowledgePage from "./pages/admin/KnowledgePage";
import HODLeaveApprovalPage from "./pages/admin/HODLeaveApprovalPage";

function RootRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <DashboardPage />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          <RealtimeProvider>
          <Routes>
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>

            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<RootRedirect />} />
                <Route path="/ai" element={<AIAgentPage />} />
                <Route path="/workspace" element={<WorkspacePage />} />
                <Route path="/attendance" element={<AttendancePage />} />
                <Route path="/notifications" element={<NotificationsPage />} />
                <Route path="/payroll" element={<PayrollPage />} />
                <Route path="/profile" element={<ProfilePage />} />

                <Route element={<ProtectedRoute allowedRoles={["HOD"]} />}>
                  <Route path="/team-management" element={<TeamManagementPage />} />
                  <Route path="/registrations" element={<RegistrationsPage />} />
                </Route>

                <Route element={<ProtectedRoute allowedRoles={["SUPER_ADMIN"]} />}>
                  <Route path="/admin/employees" element={<EmployeesPage />} />
                  <Route path="/admin/hods" element={<HODsPage />} />
                  <Route path="/admin/departments" element={<DepartmentsPage />} />
                  <Route path="/admin/company-rules" element={<CompanyRulesPage />} />
                  <Route path="/admin/knowledge" element={<KnowledgePage />} />
                  <Route path="/admin/hod-leave" element={<HODLeaveApprovalPage />} />
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </RealtimeProvider>
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
