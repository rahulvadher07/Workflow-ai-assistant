import { useEffect, useState } from "react";
import { AlertTriangle, CalendarDays, CheckCircle2, Clock3, Coffee, House, TrendingUp } from "lucide-react";
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

const statusTone = {
  PRESENT: "attendance-tone-present",
  ABSENT: "attendance-tone-absent",
  HALF_DAY: "attendance-tone-half",
  WFH: "attendance-tone-wfh",
};

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
      await loadData();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setPunching(false);
    }
  }

  if (loading) return <LoadingScreen />;

  const nextPunchLabel = (today?.punch_count || 0) % 2 === 1 ? "OUT" : "IN";
  const currentStatus = today?.status || "ABSENT";
  const attendanceRate = getAttendanceRate(history);
  const monthLabel = getMonthLabel(today?.date);

  return (
    <div className="page-shell attendance-page">
      <div className="attendance-page-header page-header">
        <div>
          <p className="page-eyebrow">Time & presence</p>
          <h2 className="attendance-title">Attendance</h2>
          <p className="attendance-subtitle">Track your attendance and manage your work schedule.</p>
        </div>
        <div className="attendance-header-actions">
          <div className="attendance-month-pill">
            <CalendarDays className="h-4 w-4" />
            <span>{monthLabel}</span>
          </div>
          <Button onClick={handlePunch} loading={punching} className="attendance-punch-btn">
            <CheckCircle2 className="h-4 w-4" />
            Mark Attendance
          </Button>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="attendance-stat-grid">
        <AttendanceStatCard icon={CalendarDays} value={formatCount(today?.present_days, history)} label="Present Days" tone="green" />
        <AttendanceStatCard icon={CalendarDays} value={formatCount(today?.absent_days, history)} label="Absent Days" tone="red" />
        <AttendanceStatCard icon={Clock3} value={formatCount(today?.half_days, history)} label="Half Days" tone="amber" />
        <AttendanceStatCard icon={House} value={formatCount(today?.wfh_days, history)} label="Work From Home" tone="violet" />
      </div>

      <div className="attendance-content-grid">
        <Card className="attendance-record-card section-card">
          <div className="section-head attendance-section-head">
            <div>
              <h2>Attendance Records</h2>
              <p>Recent attendance activity and work hours.</p>
            </div>
            <span className="attendance-filter-pill">All Status</span>
          </div>

          <div className="table-shell attendance-table-shell">
            {history.length === 0 ? (
              <EmptyState icon={Clock3} title="No attendance history yet" description="Your punches will appear here." />
            ) : (
              <table className="w-full text-sm attendance-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Day</th>
                    <th>Check In</th>
                    <th>Check Out</th>
                    <th>Work Hours</th>
                    <th>Status</th>
                    <th>Location</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((day) => (
                    <tr key={day.id}>
                      <td className="attendance-date-cell">{formatDate(day.date)}</td>
                      <td>{formatDay(day.date)}</td>
                      <td>{formatTime(day.first_in)}</td>
                      <td>{formatTime(day.last_out)}</td>
                      <td className="attendance-hours-cell">{formatMinutesAsHours(day.total_minutes)}</td>
                      <td>
                        <div className="attendance-status-cell">
                          <StatusBadge status={day.status} />
                          {day.is_late && (
                            <span className="attendance-late-tag">
                              <AlertTriangle className="h-3.5 w-3.5" /> Late
                            </span>
                          )}
                        </div>
                      </td>
                      <td>{day.location || "Office"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        <div className="attendance-side-stack">
          <Card className="attendance-side-card">
            <div className="attendance-side-title-row">
              <div>
                <p className="attendance-card-kicker">Today’s Status</p>
                <h3>{titleCase(currentStatus)}</h3>
              </div>
              <span className={`attendance-status-dot ${statusTone[currentStatus] || "attendance-tone-present"}`} />
            </div>
            <div className="attendance-today-box">
              <div>
                <span className="attendance-mini-label">Checked in</span>
                <strong>{formatTime(today?.first_in)}</strong>
              </div>
              <div>
                <span className="attendance-mini-label">Working hours</span>
                <strong>{formatMinutesAsHours(today?.total_minutes || 0)}</strong>
              </div>
            </div>
            <div className="attendance-next-punch">
              <div>
                <span className="attendance-mini-label">Next punch</span>
                <strong>{nextPunchLabel}</strong>
              </div>
              <Button onClick={handlePunch} loading={punching} className="px-4 py-2 text-xs">
                Punch now
              </Button>
            </div>
            {today?.is_late && (
              <div className="attendance-late-box">
                <AlertTriangle className="h-4 w-4" />
                <span>You checked in late today.</span>
              </div>
            )}
          </Card>

          <Card className="attendance-side-card attendance-overview-card">
            <div className="attendance-side-title-row">
              <div>
                <p className="attendance-card-kicker">Monthly Overview</p>
                <h3>Attendance rate</h3>
              </div>
              <TrendingUp className="h-5 w-5 text-brand-green" />
            </div>
            <div className="attendance-rate-wrap">
              <div className="attendance-donut" style={{ "--attendance-progress": `${attendanceRate}%` }}>
                <div className="attendance-donut-center">
                  <strong>{attendanceRate}%</strong>
                  <span>Attendance Rate</span>
                </div>
              </div>
            </div>
            <div className="attendance-legend">
              <LegendRow label="Present" value={countStatus(history, "PRESENT")} tone="green" />
              <LegendRow label="Absent" value={countStatus(history, "ABSENT")} tone="red" />
              <LegendRow label="Half Day" value={countStatus(history, "HALF_DAY")} tone="amber" />
              <LegendRow label="WFH" value={countStatus(history, "WFH")} tone="violet" />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function AttendanceStatCard({ icon: Icon, value, label, tone }) {
  return (
    <Card className="attendance-stat-card">
      <div className={`attendance-stat-icon attendance-stat-icon-${tone}`}>
        <Icon className="h-5 w-5" />
      </div>
      <p className="attendance-stat-value">{value}</p>
      <p className="attendance-stat-label">{label}</p>
    </Card>
  );
}

function LegendRow({ label, value, tone }) {
  return (
    <div className="attendance-legend-row">
      <span className={`attendance-legend-dot attendance-legend-dot-${tone}`} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function getMonthLabel(dateValue) {
  if (!dateValue) return "Current Month";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return "Current Month";
  return date.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function formatDay(dateValue) {
  if (!dateValue) return "—";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { weekday: "short" });
}

function titleCase(value) {
  return String(value || "").replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function countStatus(history, status) {
  return history.filter((item) => item.status === status).length;
}

function getAttendanceRate(history) {
  if (!history.length) return 0;
  const present = history.filter((item) => item.status === "PRESENT").length;
  return Math.round((present / history.length) * 100);
}

function formatCount(candidate, history) {
  if (candidate !== undefined && candidate !== null) return candidate;
  return history.length ? countStatus(history, "PRESENT") : 0;
}
