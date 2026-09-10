import { useEffect, useMemo, useState } from "react";
import { ShieldCheck, UserRound, Mail, Phone, Building2, KeyRound } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { authService } from "../../services/authService";
import { extractErrorMessage } from "../../services/apiClient";
import Card from "../../components/Card";
import Button from "../../components/Button";
import ErrorBanner from "../../components/ErrorBanner";
import { useDataChange } from "../../hooks/useDataChange";
import PageHeader from "../../components/PageHeader";

export default function ProfilePage() {
  const { user, reloadUser } = useAuth();
  const [form, setForm] = useState({ first_name: user?.first_name || "", last_name: user?.last_name || "", email: user?.email || "", phone: user?.phone || "" });
  useEffect(() => { setForm({ first_name: user?.first_name || "", last_name: user?.last_name || "", email: user?.email || "", phone: user?.phone || "" }); }, [user?.id, user?.first_name, user?.last_name, user?.email, user?.phone]);
  const [saving, setSaving] = useState(false), [error, setError] = useState(null), [success, setSuccess] = useState(false);
  const [oldPassword, setOldPassword] = useState(""), [newPassword, setNewPassword] = useState(""), [pwSaving, setPwSaving] = useState(false);
  useDataChange(async () => { await reloadUser(); }, "auth");

  async function saveProfile(e) { e.preventDefault(); setSaving(true); setError(null); setSuccess(false); try { await authService.updateProfile(form); await reloadUser(); setSuccess(true); } catch (err) { setError(extractErrorMessage(err)); } finally { setSaving(false); } }
  async function changePassword(e) { e.preventDefault(); setPwSaving(true); setError(null); try { await authService.changePassword(oldPassword, newPassword); setOldPassword(""); setNewPassword(""); setSuccess(true); } catch (err) { setError(extractErrorMessage(err)); } finally { setPwSaving(false); } }

  const initials = useMemo(() => `${user?.first_name?.[0] || ""}${user?.last_name?.[0] || user?.username?.[0] || ""}`.toUpperCase(), [user]);

  return (
    <div className="page-shell profile-page max-w-5xl space-y-6">
      <PageHeader eyebrow="Account" title="Profile" description="Manage your personal details and account security." />
      {error && <ErrorBanner message={error} />}
      {success && <div className="profile-success"><ShieldCheck className="h-4 w-4" /> Saved successfully.</div>}

      <div className="profile-hero">
        <div className="profile-avatar">{initials || <UserRound className="h-8 w-8" />}</div>
        <div className="min-w-0 flex-1"><p className="text-xs font-bold uppercase tracking-[.12em] text-white/60">Workspace account</p><h2 className="mt-1 truncate text-2xl font-extrabold tracking-[-.03em] text-white">{[user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username || "Your profile"}</h2><p className="mt-1 text-sm text-white/70">@{user?.username || "user"} · {user?.role || "Member"}</p></div>
        <div className="profile-hero-badge"><ShieldCheck className="h-4 w-4" /> Account protected</div>
      </div>

      <div className="profile-layout">
        <Card className="section-card profile-card">
          <div className="profile-section-heading"><span className="profile-section-icon"><UserRound className="h-4 w-4" /></span><div><h2 className="text-sm font-extrabold text-ink-900">Personal details</h2><p className="mt-1 text-xs text-ink-500">Keep your contact details up to date.</p></div></div>
          <form onSubmit={saveProfile} className="profile-form-grid">
            <Field label="First name" value={form.first_name} onChange={v => setForm({ ...form, first_name: v })} />
            <Field label="Last name" value={form.last_name} onChange={v => setForm({ ...form, last_name: v })} />
            <Field label="Email" icon={Mail} value={form.email} onChange={v => setForm({ ...form, email: v })} />
            <Field label="Phone" icon={Phone} value={form.phone} onChange={v => setForm({ ...form, phone: v })} />
            <Field label="Username" value={user?.username || ""} disabled />
            <Field label="Role" value={user?.role || ""} disabled />
            <div className="profile-meta-row"><span><Building2 className="h-4 w-4" />Department</span><strong>{user?.department || "—"}</strong></div><div className="profile-meta-row"><span><UserRound className="h-4 w-4" />Employee code</span><strong>{user?.employee_code || "—"}</strong></div>
            <div className="col-span-full"><Button type="submit" loading={saving}>Save profile</Button></div>
          </form>
        </Card>

        <Card className="section-card profile-card profile-security-card">
          <div className="profile-section-heading"><span className="profile-section-icon security"><KeyRound className="h-4 w-4" /></span><div><h2 className="text-sm font-extrabold text-ink-900">Account security</h2><p className="mt-1 text-xs text-ink-500">Change your password without leaving your profile.</p></div></div>
          <div className="security-note"><ShieldCheck className="h-5 w-5" /><div><p className="text-xs font-extrabold text-ink-900">Keep your account protected</p><p className="mt-1 text-xs leading-5 text-ink-500">Use a strong password you do not reuse elsewhere.</p></div></div>
          <form onSubmit={changePassword} className="space-y-4"><Field label="Current password" type="password" value={oldPassword} onChange={setOldPassword} /><Field label="New password" type="password" value={newPassword} onChange={setNewPassword} /><Button type="submit" loading={pwSaving}>Update password</Button></form>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", disabled = false, icon: Icon }) {
  return <div><label className="mb-1.5 block text-xs font-bold text-ink-700">{label}</label><div className="relative">{Icon && <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />}<input type={type} disabled={disabled} required={!disabled} value={value} onChange={e => onChange?.(e.target.value)} className={`page-control w-full ${Icon ? "pl-10" : ""} ${disabled ? "profile-disabled" : ""}`} /></div></div>;
}
