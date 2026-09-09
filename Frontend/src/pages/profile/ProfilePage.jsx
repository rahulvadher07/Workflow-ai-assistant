import { useEffect, useState } from "react";
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
  const [form, setForm] = useState({ first_name:user?.first_name||"", last_name:user?.last_name||"", email:user?.email||"", phone:user?.phone||"" });
  useEffect(() => {
    setForm({ first_name:user?.first_name||"", last_name:user?.last_name||"", email:user?.email||"", phone:user?.phone||"" });
  }, [user?.id, user?.first_name, user?.last_name, user?.email, user?.phone]);
  const [saving,setSaving]=useState(false), [error,setError]=useState(null), [success,setSuccess]=useState(false);
  const [oldPassword,setOldPassword]=useState(""), [newPassword,setNewPassword]=useState(""), [pwSaving,setPwSaving]=useState(false);
  useDataChange(async () => { await reloadUser(); }, "auth");

  async function saveProfile(e){e.preventDefault();setSaving(true);setError(null);setSuccess(false);try{await authService.updateProfile(form);await reloadUser();setSuccess(true)}catch(err){setError(extractErrorMessage(err))}finally{setSaving(false)}}
  async function changePassword(e){e.preventDefault();setPwSaving(true);setError(null);try{await authService.changePassword(oldPassword,newPassword);setOldPassword("");setNewPassword("");setSuccess(true)}catch(err){setError(extractErrorMessage(err))}finally{setPwSaving(false)}}
  return <div className="page-shell max-w-3xl space-y-6"><PageHeader eyebrow="Account" title="Profile" description="Manage your personal details and account security." />{error&&<ErrorBanner message={error}/>} {success&&<p className="text-sm text-brand-green">Saved successfully.</p>}
    <Card><h2 className="mb-4 text-sm font-semibold text-ink-900">Profile</h2><form onSubmit={saveProfile} className="grid grid-cols-2 gap-3">
      <Field label="First name" value={form.first_name} onChange={v=>setForm({...form,first_name:v})}/><Field label="Last name" value={form.last_name} onChange={v=>setForm({...form,last_name:v})}/><Field label="Email" value={form.email} onChange={v=>setForm({...form,email:v})}/><Field label="Phone" value={form.phone} onChange={v=>setForm({...form,phone:v})}/>
      <Field label="Username" value={user?.username||""} disabled/><Field label="Role" value={user?.role||""} disabled/><div className="col-span-2"><p className="text-xs text-ink-500">Department: <span className="font-medium text-ink-700">{user?.department||"—"}</span> · Employee code: <span className="font-medium text-ink-700">{user?.employee_code||"—"}</span></p></div><div className="col-span-2"><Button type="submit" loading={saving}>Save profile</Button></div>
    </form></Card>
    <Card><h2 className="mb-4 text-sm font-semibold text-ink-900">Change Password</h2><form onSubmit={changePassword} className="space-y-3"><Field label="Current password" type="password" value={oldPassword} onChange={setOldPassword}/><Field label="New password" type="password" value={newPassword} onChange={setNewPassword}/><Button type="submit" loading={pwSaving}>Update password</Button></form></Card>
  </div>;
}
function Field({label,value,onChange,type="text",disabled=false}){return <div><label className="mb-1.5 block text-sm font-medium text-ink-700">{label}</label><input type={type} disabled={disabled} required={!disabled} value={value} onChange={e=>onChange?.(e.target.value)} className={`focus-ring w-full rounded-lg border border-border-subtle px-3 py-2 text-sm ${disabled?"bg-slate-50 text-ink-500":""}`}/></div>}
