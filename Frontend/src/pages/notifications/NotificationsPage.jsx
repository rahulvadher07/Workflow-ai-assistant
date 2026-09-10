import React from "react";
import { Bell, CheckCheck, Plus, X, CircleCheck, Megaphone } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { notificationService } from "../../services/notificationService";
import { extractErrorMessage } from "../../services/apiClient";
import { useNotifications } from "../../context/NotificationContext";
import Card from "../../components/Card";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import { formatDateTime } from "../../utils/format";

export default function NotificationsPage() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const { user } = useAuth();
  const [open, setOpen] = React.useState(false);
  const [form, setForm] = React.useState({ title: "", message: "" });
  const [error, setError] = React.useState(null);

  return (
    <div className="page-shell notifications-page space-y-6">
      <div className="notifications-hero">
        <div>
          <p className="page-eyebrow !text-[#9ed6c8]">Inbox</p>
          <h2 className="mt-1 font-extrabold tracking-[-.04em] text-white">Notifications</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-white/70">Stay on top of approvals, updates and team activity without losing the important details.</p>
        </div>
        <div className="notifications-hero-icon"><Bell className="h-6 w-6" /></div>
      </div>

      <div className="notifications-summary-grid">
        <Card className="notif-summary-card"><span className="notif-summary-icon bg-[#e7faf4] text-[#078f79]"><Bell className="h-5 w-5" /></span><div><p className="text-2xl font-extrabold tracking-[-.03em] text-ink-900">{notifications.length}</p><p className="text-xs font-medium text-ink-500">Total notifications</p></div></Card>
        <Card className="notif-summary-card"><span className="notif-summary-icon bg-[#fff5df] text-[#c77a00]"><Megaphone className="h-5 w-5" /></span><div><p className="text-2xl font-extrabold tracking-[-.03em] text-ink-900">{unreadCount}</p><p className="text-xs font-medium text-ink-500">Unread</p></div></Card>
        <Card className="notif-summary-card"><span className="notif-summary-icon bg-[#eaf6ff] text-[#1975a7]"><CircleCheck className="h-5 w-5" /></span><div><p className="text-2xl font-extrabold tracking-[-.03em] text-ink-900">{Math.max(notifications.length - unreadCount, 0)}</p><p className="text-xs font-medium text-ink-500">Already read</p></div></Card>
      </div>

      <Card className="section-card notifications-panel">
        <div className="notifications-toolbar">
          <div><h2 className="text-base font-extrabold text-ink-900">Activity & updates</h2><p className="mt-1 text-xs text-ink-500">Approvals, team changes and system activity appear here.</p></div>
          <div className="flex flex-wrap gap-2">
            {(user?.role === "SUPER_ADMIN" || user?.role === "HOD") && <Button onClick={() => { setOpen(true); setError(null); }} className="gap-1.5 !rounded-xl !px-3 !py-2 text-xs"><Plus className="h-3.5 w-3.5" /> New notification</Button>}
            {unreadCount > 0 && <Button variant="secondary" onClick={markAllRead} className="gap-1.5 !rounded-xl !px-3 !py-2 text-xs"><CheckCheck className="h-3.5 w-3.5" /> Mark all read</Button>}
          </div>
        </div>

        {open && <div className="notification-compose"><div className="mb-4 flex items-center justify-between"><div><h3 className="text-sm font-extrabold text-ink-900">New notification</h3><p className="mt-1 text-xs text-ink-500">Send a quick update to your workspace.</p></div><button className="rounded-lg p-2 text-ink-400 hover:bg-emerald-50 hover:text-ink-900" onClick={() => setOpen(false)}><X className="h-4 w-4" /></button></div>{error && <p className="mb-3 rounded-xl bg-red-50 px-3 py-2 text-xs font-medium text-red-600">{error}</p>}<form onSubmit={e => { e.preventDefault(); const payload = { ...form }; setError(null); setForm({ title: "", message: "" }); setOpen(false); notificationService.create(payload).then(() => { window.dispatchEvent(new Event("workflow_ai_notification_created")); }).catch(err => { setForm(payload); setError(extractErrorMessage(err)); setOpen(true); }); }} className="grid gap-3"><input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Notification title" className="page-control w-full" /><textarea required value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} placeholder="Write the message..." rows="4" className="page-control w-full" /><div><Button type="submit">Send notification</Button></div></form></div>}

        {notifications.length === 0 ? <div className="py-10"><EmptyState icon={Bell} title="No notifications" description="You're all caught up." /></div> : (
          <ul className="notification-list">
            {notifications.map((n) => (
              <li key={n.id} onClick={() => !n.is_read && markRead(n.id)} className={`notification-item ${!n.is_read ? "is-unread" : ""}`}>
                <div className="notification-leading-icon"><Bell className="h-4 w-4" /></div>
                <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="text-sm font-bold text-ink-900">{n.title}</p>{!n.is_read && <span className="notification-unread-pill">Unread</span>}</div>{n.message && <p className="mt-1 text-sm leading-6 text-ink-600">{n.message}</p>}<p className="mt-2 text-[11px] font-medium text-ink-400">{formatDateTime(n.created_at)}</p></div>
                {!n.is_read && <span className="notification-dot" />}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
