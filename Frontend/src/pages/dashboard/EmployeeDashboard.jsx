import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Bell, CalendarCheck2, Clock3, ListTodo, Sparkles, Users2, WalletCards } from "lucide-react";
import Card from "../../components/Card";
import Button from "../../components/Button";
import LoadingScreen from "../../components/LoadingScreen";
import { attendanceService } from "../../services/attendanceService";
import { payrollService } from "../../services/payrollService";
import { useNotifications } from "../../context/NotificationContext";
import { useAuth } from "../../context/AuthContext";
import { formatMinutesAsHours, formatCurrency } from "../../utils/format";
import { useDataChange } from "../../hooks/useDataChange";

function formatDate(date) {
  return new Intl.DateTimeFormat([], {
    weekday: "long",
    month: "short",
    day: "numeric",
  }).format(date);
}

export default function EmployeeDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
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

  const todayLabel = useMemo(() => formatDate(new Date()), []);

  if (loading) return <LoadingScreen />;

  const latestPayslip = payslips[0];
  const latestNotification = notifications[0];
  const unreadCount = notifications.filter((notification) => !notification.is_read).length;
  const greetingName = user?.first_name || user?.username || "there";
  async function handlePunch() {
    await attendanceService.punch();
    const res = await attendanceService.today();
    setToday(res.data);
  }

  const isClockedIn = (today?.punch_count || 0) % 2 === 1;

  return (
    <div className="page-shell space-y-5">
      <section className="rounded-[24px] border border-[#cfe6df] bg-white px-6 py-5 shadow-[0_16px_44px_rgba(18,58,51,.055)] sm:px-7">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.16em] text-[#6f8881]">
              <Sparkles className="h-3.5 w-3.5 text-[#19a98e]" />
              Your workplace overview
            </div>
            <h2 className="mt-2 text-[28px] font-extrabold tracking-[-.045em] text-[#102a27] sm:text-[32px]">
              Good morning, {greetingName}! <span aria-hidden="true">👋</span>
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#6d8580]">
              Keep attendance, work, notifications and payroll together in one calm view.
            </p>
          </div>
          <div className="rounded-2xl border border-[#dcebe7] bg-[#f7fbfa] px-4 py-3 text-right">
            <p className="text-[10px] font-extrabold uppercase tracking-[.14em] text-[#7d948e]">Today</p>
            <p className="mt-1 text-sm font-bold text-[#173a34]">{todayLabel}</p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="card-hover !p-5">
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e8f8f3] text-[#0f9a80]">
              <CalendarCheck2 className="h-5 w-5" />
            </div>
            <span className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold ${isClockedIn ? "bg-[#e7f8ee] text-[#15803d]" : "bg-[#f5f7f7] text-[#70857f]"}`}>
              {isClockedIn ? "ACTIVE" : "TODAY"}
            </span>
          </div>
          <p className="mt-5 text-[11px] font-bold uppercase tracking-[.08em] text-[#7d948e]">Today&apos;s Attendance</p>
          <p className="mt-1 text-[27px] font-extrabold tracking-[-.04em] text-[#102a27]">{formatMinutesAsHours(today?.total_minutes || 0)}</p>
          <p className="mt-1 text-xs text-[#748983]">
            {today?.first_in ? `First in: ${new Date(today.first_in).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "No punches yet"}
          </p>
          <Button onClick={handlePunch} className="mt-4 w-full" variant={isClockedIn ? "secondary" : "primary"}>
            {isClockedIn ? "Punch Out" : "Punch In"}
          </Button>
        </Card>

        <Card className="card-hover !p-5">
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#eef8f8] text-[#277d73]">
              <Clock3 className="h-5 w-5" />
            </div>
            <span className="rounded-full bg-[#fff7e7] px-2.5 py-1 text-[10px] font-extrabold text-[#b7791f]">STATUS</span>
          </div>
          <p className="mt-5 text-[11px] font-bold uppercase tracking-[.08em] text-[#7d948e]">Overtime Today</p>
          <p className="mt-1 text-[27px] font-extrabold tracking-[-.04em] text-[#102a27]">{formatMinutesAsHours(today?.overtime_minutes || 0)}</p>
          <p className="mt-1 text-xs text-[#748983]">{today?.is_late ? "Marked late today" : "You are on time"}</p>
        </Card>

        <Card className="card-hover !p-5">
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#edf5ff] text-[#3d7dc2]">
              <Bell className="h-5 w-5" />
            </div>
            {unreadCount > 0 && <span className="rounded-full bg-[#ef4444] px-2.5 py-1 text-[10px] font-extrabold text-white">{unreadCount} NEW</span>}
          </div>
          <p className="mt-5 text-[11px] font-bold uppercase tracking-[.08em] text-[#7d948e]">Latest Notification</p>
          <p className="mt-2 truncate text-sm font-extrabold text-[#173a34]">{latestNotification?.title || "No notifications yet"}</p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-[#748983]">{latestNotification?.message || "You&apos;re all caught up."}</p>
        </Card>

        <Card className="card-hover !p-5">
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#f4efff] text-[#8b63c7]">
              <WalletCards className="h-5 w-5" />
            </div>
            <span className="rounded-full bg-[#f3efff] px-2.5 py-1 text-[10px] font-extrabold text-[#8b63c7]">PAYROLL</span>
          </div>
          <p className="mt-5 text-[11px] font-bold uppercase tracking-[.08em] text-[#7d948e]">Latest Payslip</p>
          {latestPayslip ? (
            <>
              <p className="mt-1 text-[27px] font-extrabold tracking-[-.04em] text-[#102a27]">{formatCurrency(latestPayslip.net_salary)}</p>
              <p className="mt-1 truncate text-xs text-[#748983]">{latestPayslip.period_label}</p>
            </>
          ) : (
            <p className="mt-2 text-sm text-[#748983]">No approved payslips yet.</p>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.55fr_.95fr]">
        <Card className="!p-6">
          <div className="section-head">
            <div>
              <h2 className="text-base font-extrabold text-[#173a34]">Quick Actions</h2>
              <p>Jump directly into the tools you use most.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <button onClick={() => navigate("/ai")} className="group rounded-2xl border border-[#dcebe7] bg-[#f9fcfb] p-4 text-left transition hover:-translate-y-0.5 hover:border-[#9ed9ca] hover:bg-[#f2fbf7]">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#dcf7ef] text-[#12957d]"><Sparkles className="h-5 w-5" /></span>
              <p className="mt-4 text-sm font-extrabold text-[#173a34]">Open AI Agent</p>
              <p className="mt-1 text-xs leading-5 text-[#7a8f89]">Ask questions and get workplace help.</p>
            </button>
            <button onClick={() => navigate("/workspace")} className="group rounded-2xl border border-[#dcebe7] bg-[#f9fcfb] p-4 text-left transition hover:-translate-y-0.5 hover:border-[#9ed9ca] hover:bg-[#f2fbf7]">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#eaf2ff] text-[#3778bd]"><Users2 className="h-5 w-5" /></span>
              <p className="mt-4 text-sm font-extrabold text-[#173a34]">Team Workspace</p>
              <p className="mt-1 text-xs leading-5 text-[#7a8f89]">Collaborate with your team.</p>
            </button>
            <button onClick={() => navigate("/attendance")} className="group rounded-2xl border border-[#dcebe7] bg-[#f9fcfb] p-4 text-left transition hover:-translate-y-0.5 hover:border-[#9ed9ca] hover:bg-[#f2fbf7]">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#fff6df] text-[#b77b22]"><ListTodo className="h-5 w-5" /></span>
              <p className="mt-4 text-sm font-extrabold text-[#173a34]">View Attendance</p>
              <p className="mt-1 text-xs leading-5 text-[#7a8f89]">Track history and work hours.</p>
            </button>
          </div>
        </Card>

        <Card className="!p-6">
          <div className="section-head">
            <div>
              <h2 className="text-base font-extrabold text-[#173a34]">Today&apos;s Status</h2>
              <p>Your live attendance snapshot.</p>
            </div>
            <AlertCircle className="h-5 w-5 text-[#6f8881]" />
          </div>
          <div className="rounded-2xl border border-[#dfece8] bg-[#f8fcfb] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[.08em] text-[#81958f]">Current state</p>
                <p className="mt-1 text-lg font-extrabold text-[#173a34]">{isClockedIn ? "Present" : today?.status === "ABSENT" ? "Not marked" : "Ready"}</p>
              </div>
              <span className={`h-3 w-3 rounded-full ${isClockedIn ? "bg-[#22c55e]" : "bg-[#9fb2ad]"}`} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-white p-3">
                <p className="text-[10px] font-bold uppercase tracking-[.08em] text-[#8a9b96]">Hours</p>
                <p className="mt-1 text-sm font-extrabold text-[#173a34]">{formatMinutesAsHours(today?.total_minutes || 0)}</p>
              </div>
              <div className="rounded-xl bg-white p-3">
                <p className="text-[10px] font-bold uppercase tracking-[.08em] text-[#8a9b96]">Overtime</p>
                <p className="mt-1 text-sm font-extrabold text-[#173a34]">{formatMinutesAsHours(today?.overtime_minutes || 0)}</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden !p-0">
        <div className="flex flex-col gap-4 bg-gradient-to-r from-[#ecfbf6] via-[#f6fcfa] to-white px-6 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <div>
            <div className="flex items-center gap-2 text-sm font-extrabold text-[#123d35]"><Sparkles className="h-4 w-4 text-[#12a487]" /> Work smarter with AI</div>
            <p className="mt-1 text-sm text-[#718681]">Get help with tasks, find information, and automate your workflow.</p>
          </div>
          <Button onClick={() => navigate("/ai")} className="shrink-0">Open AI Agent</Button>
        </div>
      </Card>
    </div>
  );
}
