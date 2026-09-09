import { useEffect, useState } from "react";
import { AlertTriangle, Clock3, Palmtree, Timer, UserPlus } from "lucide-react";
import Card from "../../components/Card";
import LoadingScreen from "../../components/LoadingScreen";
import { notificationService } from "../../services/notificationService";
import { authService } from "../../services/authService";
import { Link } from "react-router-dom";
import { useDataChange } from "../../hooks/useDataChange";

export default function HodDashboard() {
  const [brief, setBrief] = useState(null);
  const [pendingRegs, setPendingRegs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      notificationService.dailyBrief().catch(() => ({ data: null })),
      authService.pendingRegistrations().catch(() => ({ data: [] })),
    ]).then(([briefRes, regsRes]) => {
      setBrief(briefRes.data);
      setPendingRegs(regsRes.data);
      setLoading(false);
    });
  }, []);
  useDataChange(async () => {
    const [briefRes, regsRes] = await Promise.all([
      notificationService.dailyBrief().catch(() => ({ data: null })),
      authService.pendingRegistrations().catch(() => ({ data: [] })),
    ]);
    setBrief(briefRes.data);
    setPendingRegs(regsRes.data);
  }, ["notifications", "auth", "attendance", "leave", "workspace", "teams"]);

  if (loading) return <LoadingScreen />;

  return (
    <div className="page-shell space-y-6">
      <div className="dashboard-hero">
        <div className="relative z-10 flex items-end justify-between gap-4"><div><p className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#74e6d1]">Team command center</p><h2 className="mt-2 text-2xl font-extrabold tracking-[-.04em] text-white">Daily operations overview</h2><p className="mt-2 text-sm leading-6 text-white/58">A focused view of issues, attendance, leave and work that needs your attention.</p></div>{brief?.department && <span className="rounded-full border border-white/10 bg-white/[.06] px-3 py-2 text-xs font-bold text-white/75">{brief.department}</span>}</div>
      </div>
      <Card className="section-card">
        <h2 className="text-base font-extrabold text-ink-900">Daily Brief — {brief?.department}</h2>
        <p className="text-xs text-ink-500">{brief?.date}</p>

        <div className="stat-grid mt-4">
          <BriefStat icon={AlertTriangle} color="text-brand-red" label="Pending Issues" value={brief?.pending_issues?.length ?? 0} />
          <BriefStat icon={Clock3} color="text-brand-amber" label="Attendance Problems" value={brief?.attendance_problems?.length ?? 0} />
          <BriefStat icon={Palmtree} color="text-sky-600" label="Today's Leaves" value={brief?.todays_leaves?.length ?? 0} />
          <BriefStat icon={Timer} color="text-brand-amber" label="Overdue Tasks" value={brief?.overdue_tasks?.length ?? 0} />
        </div>

        <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2">
          <BriefList title="📌 Pending Issues" items={brief?.pending_issues} render={(i) => `${i.issue_number} — ${i.title}`} />
          <BriefList title="🕒 Attendance Problems" items={brief?.attendance_problems} render={(a) => `${a.employee} — ${a.issue}`} />
          <BriefList title="🏖️ Today's Leaves" items={brief?.todays_leaves} render={(l) => `${l.employee} — ${l.leave_type}`} />
          <BriefList title="⏰ Overdue Tasks" items={brief?.overdue_tasks} render={(t) => `${t.task_number} — ${t.description}`} />
        </div>
      </Card>

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink-900">
            <UserPlus className="h-4 w-4" /> Registration Requests
          </h2>
          <Link to="/registrations" className="text-xs font-medium text-sky-600 hover:underline">View all</Link>
        </div>
        {pendingRegs.length === 0 ? (
          <p className="text-sm text-ink-500">No pending registrations.</p>
        ) : (
          <ul className="divide-y divide-border-subtle">
            {pendingRegs.slice(0, 4).map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-ink-700">{r.first_name} {r.last_name}</span>
                <span className="text-xs text-ink-500">{r.department}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function BriefStat({ icon: Icon, color, label, value }) {
  return (
    <div className="rounded-2xl border border-[#dfebe8] bg-[#f9fcfb] p-4 shadow-sm">
      <Icon className={`h-4 w-4 ${color}`} />
      <p className="mt-2 text-xl font-semibold text-ink-900">{value}</p>
      <p className="text-xs text-ink-500">{label}</p>
    </div>
  );
}

function BriefList({ title, items, render }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">{title}</h3>
      {!items || items.length === 0 ? (
        <p className="text-sm text-ink-400">Nothing to show</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((item, idx) => (
            <li key={idx} className="text-sm text-ink-700">{render(item)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
