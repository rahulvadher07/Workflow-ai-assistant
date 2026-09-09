import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, ListTodo, AlertCircle, Wallet, Bell, Sparkles, Users2 } from "lucide-react";
import Card from "../../components/Card";
import Button from "../../components/Button";
import LoadingScreen from "../../components/LoadingScreen";
import { attendanceService } from "../../services/attendanceService";
import { payrollService } from "../../services/payrollService";
import { useNotifications } from "../../context/NotificationContext";
import { formatMinutesAsHours, formatCurrency } from "../../utils/format";
import { useDataChange } from "../../hooks/useDataChange";

export default function EmployeeDashboard() {
  const navigate = useNavigate();
  const { notifications } = useNotifications();
  const [today, setToday] = useState(null);
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      attendanceService.today().catch(() => null),
      payrollService.payslips().catch(() => ({ data: [] })),
    ]).then(([todayRes, payslipRes]) => {
      setToday(todayRes?.data || null);
      setPayslips(payslipRes.data || []);
      setLoading(false);
    });
  }, []);
  useDataChange(async () => {
    const [todayRes, payslipRes] = await Promise.all([
      attendanceService.today().catch(() => null),
      payrollService.payslips().catch(() => ({ data: [] })),
    ]);
    setToday(todayRes?.data || null);
    setPayslips(payslipRes.data || []);
  }, ["attendance", "payroll"]);

  if (loading) return <LoadingScreen />;

  const latestPayslip = payslips[0];
  const latestNotification = notifications[0];

  async function handlePunch() {
    await attendanceService.punch();
    const res = await attendanceService.today();
    setToday(res.data);
  }

  return (
    <div className="page-shell space-y-6">
      <div className="dashboard-hero">
        <div className="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div><p className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#74e6d1]">Personal command center</p><h2 className="mt-2 text-2xl font-extrabold tracking-[-.04em] text-white sm:text-3xl">Welcome back, {user?.first_name || user?.username}</h2><p className="mt-2 max-w-xl text-sm leading-6 text-white/58">Keep your attendance, work, notifications and payroll in one calm view.</p></div>
          <div className="rounded-2xl border border-white/10 bg-white/[.06] px-4 py-3 text-xs font-semibold text-white/72">Today · {new Date().toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" })}</div>
        </div>
      </div>
      <div className="stat-grid">
        <Card className="stat-card card-hover">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-ink-500">Today's Attendance</span>
            <Clock className="h-4 w-4 text-ink-400" />
          </div>
          <p className="mt-3 text-2xl font-semibold text-ink-900">
            {today?.status === "ABSENT" ? "Not punched" : formatMinutesAsHours(today?.total_minutes)}
          </p>
          <p className="mt-1 text-xs text-ink-500">
            {today?.first_in ? `First in: ${new Date(today.first_in).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "No punches yet"}
          </p>
          <Button onClick={handlePunch} className="mt-4 w-full" variant="secondary">
            Punch {today?.punch_count % 2 === 1 ? "Out" : "In"}
          </Button>
        </Card>

        <Card className="stat-card card-hover">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-ink-500">Overtime Today</span>
            <AlertCircle className="h-4 w-4 text-ink-400" />
          </div>
          <p className="mt-3 text-2xl font-semibold text-ink-900">{formatMinutesAsHours(today?.overtime_minutes || 0)}</p>
          <p className="mt-1 text-xs text-ink-500">{today?.is_late ? "Marked late today" : "On time"}</p>
        </Card>

        <Card className="stat-card card-hover">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-ink-500">Latest Notification</span>
            <Bell className="h-4 w-4 text-ink-400" />
          </div>
          <p className="mt-3 truncate text-sm font-medium text-ink-900">{latestNotification?.title || "No notifications yet"}</p>
          <p className="mt-1 truncate text-xs text-ink-500">{latestNotification?.message || "You're all caught up"}</p>
        </Card>

        <Card className="stat-card card-hover">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-ink-500">Latest Payslip</span>
            <Wallet className="h-4 w-4 text-ink-400" />
          </div>
          {latestPayslip ? (
            <>
              <p className="mt-3 text-2xl font-semibold text-ink-900">{formatCurrency(latestPayslip.net_salary)}</p>
              <p className="mt-1 text-xs text-ink-500">{latestPayslip.period_label}</p>
            </>
          ) : (
            <p className="mt-3 text-sm text-ink-500">No approved payslips yet</p>
          )}
        </Card>
      </div>

      <div className="surface-card section-card">
        <div className="section-head"><div><h2>Quick actions</h2><p>Jump into the tools you use most.</p></div></div>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => navigate("/ai")} className="gap-2">
            <Sparkles className="h-4 w-4" /> Open AI Agent
          </Button>
          <Button onClick={() => navigate("/workspace")} variant="secondary" className="gap-2">
            <Users2 className="h-4 w-4" /> Team Workspace
          </Button>
          <Button onClick={() => navigate("/attendance")} variant="secondary" className="gap-2">
            <ListTodo className="h-4 w-4" /> View Attendance
          </Button>
        </div>
      </div>
    </div>
  );
}
