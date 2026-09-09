import React from "react";
import { Bell, CheckCheck, Plus, X } from "lucide-react";
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
  const [form, setForm] = React.useState({ title:"", message:"" });
  const [error, setError] = React.useState(null);

  return (
    <div className="page-shell space-y-5"><div className="page-header"><div><p className="page-eyebrow">Inbox</p><h2 className="mt-1 font-extrabold tracking-[-.035em] text-ink-900">Notifications</h2><p className="mt-2 text-sm leading-6 text-ink-500">Stay on top of approvals, updates and team activity.</p></div></div><Card className="section-card">
      <div className="section-head mb-4">
        <h2 className="text-sm font-semibold text-ink-900">
          Notifications {unreadCount > 0 && <span className="text-ink-500">({unreadCount} unread)</span>}
        </h2>
        {(user?.role === "SUPER_ADMIN" || user?.role === "HOD") && <Button onClick={()=>{setOpen(true);setError(null)}} className="gap-1.5 !px-3 !py-1.5 text-xs"><Plus className="h-3.5 w-3.5" /> New notification</Button>}
        {unreadCount > 0 && (
          <Button variant="secondary" onClick={markAllRead} className="gap-1.5 !px-3 !py-1.5 text-xs">
            <CheckCheck className="h-3.5 w-3.5" /> Mark all read
          </Button>
        )}
      </div>

      {open && <div className="mb-4 rounded-lg border border-border-subtle bg-white p-4"><div className="mb-3 flex items-center justify-between"><h3 className="text-sm font-semibold">New notification</h3><button onClick={()=>setOpen(false)}><X className="h-4 w-4" /></button></div>{error && <p className="mb-2 text-xs text-red-600">{error}</p>}<form onSubmit={e=>{e.preventDefault();const payload={...form};setError(null);setForm({title:"",message:""});setOpen(false);notificationService.create(payload).then(()=>{window.dispatchEvent(new Event("workflow_ai_notification_created"))}).catch(err=>{setForm(payload);setError(extractErrorMessage(err));setOpen(true)})}} className="space-y-2"><input required value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="Title" className="w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"/><textarea required value={form.message} onChange={e=>setForm({...form,message:e.target.value})} placeholder="Message" rows="3" className="w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"/><Button type="submit">Send notification</Button></form></div>}

      {notifications.length === 0 ? (
        <EmptyState icon={Bell} title="No notifications" description="You're all caught up." />
      ) : (
        <ul className="divide-y divide-border-subtle">
          {notifications.map((n) => (
            <li
              key={n.id}
              onClick={() => !n.is_read && markRead(n.id)}
              className={`notification-row group cursor-pointer rounded-2xl transition hover:bg-emerald-50/60 ${!n.is_read ? "bg-emerald-50/70" : ""}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-ink-900">{n.title}</p>
                  {n.message && <p className="mt-0.5 whitespace-pre-wrap text-sm text-ink-500">{n.message}</p>}
                  <p className="mt-1 text-xs text-ink-400">{formatDateTime(n.created_at)}</p>
                </div>
                {!n.is_read && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-sky-600" />}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card></div>
  );
}
