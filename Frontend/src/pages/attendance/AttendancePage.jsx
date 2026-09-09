import { useEffect, useState } from "react";
import { Clock, Coffee, AlertTriangle, TrendingUp } from "lucide-react";
import Card from "../../components/Card";
import Button from "../../components/Button";
import LoadingScreen from "../../components/LoadingScreen";
import EmptyState from "../../components/EmptyState";
import StatusBadge from "../../components/StatusBadge";
import { attendanceService } from "../../services/attendanceService";
import { extractErrorMessage } from "../../services/apiClient";
import { formatMinutesAsHours, formatTime, formatDate } from "../../utils/format";
import ErrorBanner from "../../components/ErrorBanner";
import { useDataChange } from "../../hooks/useDataChange";

export default function AttendancePage() {
  const [today, setToday] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [punching, setPunching] = useState(false);
  const [error, setError] = useState(null);

  async function loadData() {
    const [todayRes, historyRes] = await Promise.all([
      attendanceService.today(),
      attendanceService.history(),
    ]);
    setToday(todayRes.data);
    setHistory(historyRes.data);
  }

  useEffect(() => {
    loadData().finally(() => setLoading(false));
  }, []);
  useDataChange(loadData, "attendance");

  async function handlePunch() {
    setPunching(true);
    setError(null);
    try {
      await attendanceService.punch();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setPunching(false);
    }
  }

  if (loading) return <LoadingScreen />;

  const nextPunchLabel = (today?.punch_count || 0) % 2 === 1 ? "OUT" : "IN";

  return (
    <div className="page-shell space-y-6">
      <div className="page-header"><div><p className="page-eyebrow">Time & presence</p><h2 className="mt-1 font-extrabold tracking-[-.035em] text-ink-900">Attendance</h2><p className="mt-2 text-sm leading-6 text-ink-500">Track today's presence, working time and attendance history.</p></div></div>
      <Card className="relative flex flex-col items-center gap-4 overflow-hidden bg-[linear-gradient(145deg,#ffffff,#f0fbf7)] py-9 text-center">
        {error && <ErrorBanner message={error} />}
        <div>
          <p className="text-sm text-ink-500">Next punch</p>
          <p className="text-2xl font-semibold text-ink-900">{nextPunchLabel}</p>
        </div>
        <Button onClick={handlePunch} loading={punching} className="px-8 py-3 text-base">
          Punch
        </Button>
      </Card>

      <div className="stat-grid">
        <StatCard icon={Clock} label="First IN" value={formatTime(today?.first_in)} />
        <StatCard icon={Clock} label="Last OUT" value={formatTime(today?.last_out)} />
        <StatCard icon={Coffee} label="Break" value={formatMinutesAsHours(today?.break_minutes || 0)} />
        <StatCard icon={TrendingUp} label="Overtime" value={formatMinutesAsHours(today?.overtime_minutes || 0)} />
      </div>

      <Card className="section-card">
        <div className="section-head"><div><h2>Today's status</h2><p>Current attendance snapshot.</p></div><StatusBadge status={today?.status || "ABSENT"} /></div>
        <div className="mt-3 flex items-center gap-4 text-sm text-ink-500">
          <span>Working hours: {formatMinutesAsHours(today?.total_minutes || 0)}</span>
          {today?.is_late && (
            <span className="flex items-center gap-1 text-brand-amber">
              <AlertTriangle className="h-3.5 w-3.5" /> Late
            </span>
          )}
        </div>
      </Card>

      <Card className="section-card">
        <div className="section-head"><div><h2>History</h2><p>Your recent attendance records.</p></div></div>
        <div className="table-shell">
        {history.length === 0 ? (
          <EmptyState icon={Clock} title="No attendance history yet" description="Your punches will appear here." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-left text-xs text-ink-500">
                <th className="pb-2 font-medium">Date</th>
                <th className="pb-2 font-medium">First IN</th>
                <th className="pb-2 font-medium">Last OUT</th>
                <th className="pb-2 font-medium">Hours</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {history.map((day) => (
                <tr key={day.id}>
                  <td className="py-2.5 text-ink-700">{formatDate(day.date)}</td>
                  <td className="py-2.5 text-ink-500">{formatTime(day.first_in)}</td>
                  <td className="py-2.5 text-ink-500">{formatTime(day.last_out)}</td>
                  <td className="py-2.5 text-ink-500">{formatMinutesAsHours(day.total_minutes)}</td>
                  <td className="py-2.5">
                    <StatusBadge status={day.status} />
                    {day.is_late && <span className="ml-2 text-xs text-brand-amber">Late</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        </div>
      </Card>
    </div>
  );
}

function StatCard({ icon: Icon, label, value }) {
  return (
    <Card className="stat-card card-hover">
      <div className="stat-icon"><Icon className="h-4 w-4" /></div>
      <p className="mt-3 text-xl font-semibold text-ink-900">{value}</p>
      <p className="mt-1 text-xs text-ink-500">{label}</p>
    </Card>
  );
}
