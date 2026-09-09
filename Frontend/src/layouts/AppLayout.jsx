import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

const TITLES = {
  "/": "Dashboard",
  "/ai": "AI Agent",
  "/workspace": "Team Workspace",
  "/attendance": "Attendance",
  "/notifications": "Notifications",
  "/payroll": "Payroll",
  "/profile": "Profile",
  "/team-management": "Team Management",
  "/registrations": "Registration Requests",
  "/admin/employees": "Employees",
  "/admin/hods": "HOD Management",
  "/admin/departments": "Departments",
  "/admin/company-rules": "Company Rules",
  "/admin/knowledge": "Knowledge & Policy",
  "/admin/hod-leave": "HOD Leave Approval",
};

function titleFor(pathname) {
  if (TITLES[pathname]) return TITLES[pathname];
  const base = "/" + pathname.split("/")[1];
  return TITLES[base] || "WorkFlow AI";
}

export default function AppLayout() {
  const location = useLocation();
  const title = titleFor(location.pathname);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-surface">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={title} />
        <main className="app-shell-main flex-1 overflow-y-auto px-7 py-7">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
