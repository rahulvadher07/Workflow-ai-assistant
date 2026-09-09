import { useAuth } from "../../context/AuthContext";
import EmployeeDashboard from "./EmployeeDashboard";
import HodDashboard from "./HodDashboard";
import AdminDashboard from "./AdminDashboard";

export default function DashboardPage() {
  const { user } = useAuth();
  if (user?.role === "SUPER_ADMIN") return <AdminDashboard />;
  if (user?.role === "HOD") return <HodDashboard />;
  return <EmployeeDashboard />;
}
