import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Sparkles, Users2, Clock, Bell, Wallet, UserCircle,
  Building2, ShieldCheck, FileText, UserPlus, ClipboardList,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useNotifications } from "../context/NotificationContext";

const EMPLOYEE_NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/ai", label: "AI Agent", icon: Sparkles },
  { to: "/workspace", label: "Team Workspace", icon: Users2 },
  { to: "/attendance", label: "Attendance", icon: Clock },
  { to: "/notifications", label: "Notifications", icon: Bell },
  { to: "/payroll", label: "Payroll", icon: Wallet },
  { to: "/profile", label: "Profile", icon: UserCircle },
];
const HOD_NAV = [
  ...EMPLOYEE_NAV.filter((item) => !["/notifications","/payroll","/profile"].includes(item.to)),
  { to: "/team-management", label: "Team Management", icon: ClipboardList },
  { to: "/registrations", label: "Registration Requests", icon: UserPlus },
  { to: "/payroll", label: "Payroll", icon: Wallet },
  { to: "/notifications", label: "Notifications", icon: Bell },
  { to: "/profile", label: "Profile", icon: UserCircle },
];
const ADMIN_NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/employees", label: "Employees", icon: Users2 },
  { to: "/admin/hods", label: "HOD Management", icon: Users2 },
  { to: "/admin/departments", label: "Departments", icon: Building2 },
  { to: "/admin/company-rules", label: "Company Rules", icon: ShieldCheck },
  { to: "/admin/knowledge", label: "Knowledge & Policy", icon: FileText },
  { to: "/payroll", label: "Payroll Management", icon: Wallet },
  { to: "/notifications", label: "Notifications", icon: Bell },
  { to: "/admin/hod-leave", label: "HOD Leave Approval", icon: ClipboardList },
  { to: "/profile", label: "Profile", icon: UserCircle },
];

function navForRole(role) {
  if (role === "SUPER_ADMIN") return ADMIN_NAV;
  if (role === "HOD") return HOD_NAV;
  return EMPLOYEE_NAV;
}

export default function Sidebar() {
  const { user } = useAuth();
  const { unreadCount } = useNotifications();
  const nav = navForRole(user?.role);

  return (
    <aside className="flex h-full w-[268px] shrink-0 flex-col bg-[#06372f] text-white shadow-[12px_0_38px_rgba(5,49,42,.10)]">
      <div className="border-b border-white/8 px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-[#26d7b4] to-[#0b8f78] shadow-[0_10px_24px_rgba(16,185,150,.28)]">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-[15px] font-extrabold tracking-tight">WorkFlow AI</div>
            <div className="mt-0.5 text-[10px] font-bold uppercase tracking-[0.15em] text-white/40">Operations Hub</div>
          </div>
        </div>
      </div>

      <nav className="mt-4 flex-1 space-y-1.5 px-3">
        <div className="px-2 pb-2 text-[9px] font-extrabold uppercase tracking-[.16em] text-white/30">Workspace</div>
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) =>
            `group relative flex items-center gap-3 rounded-2xl px-3.5 py-3 text-[13px] font-semibold transition-all ${isActive ? "bg-white/[.11] text-white shadow-[inset_0_1px_0_rgba(255,255,255,.06)]" : "text-white/60 hover:bg-white/[.055] hover:text-white"}`
          }>
            {({ isActive }) => (
              <>
                {isActive && <span className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-[#25d6b4]" />}
                <Icon className={`h-[17px] w-[17px] shrink-0 ${isActive ? "text-[#5ee6cc]" : "text-white/42 group-hover:text-white/75"}`} strokeWidth={1.9} />
                <span className="min-w-0 flex-1 truncate">{label}</span>
                {to === "/notifications" && unreadCount > 0 && <span className="rounded-full bg-rose-500 px-1.5 py-0.5 text-[9px] font-extrabold text-white">{unreadCount > 9 ? "9+" : unreadCount}</span>}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mx-3 mb-3 rounded-2xl border border-white/9 bg-white/[.045] px-4 py-3.5">
        <p className="text-[9px] font-extrabold uppercase tracking-[.15em] text-white/32">Signed in as</p>
        <p className="mt-1.5 truncate text-sm font-bold text-white/90">{user?.first_name || user?.username}</p>
        <div className="mt-2 flex items-center justify-between gap-2">
          <p className="truncate text-xs text-white/45">{user?.department || "Company wide"}</p>
          <span className="rounded-full bg-white/8 px-2 py-1 text-[9px] font-bold uppercase tracking-wide text-white/55">{user?.role?.replace("_", " ")}</span>
        </div>
      </div>
    </aside>
  );
}
