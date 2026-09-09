import { useEffect, useState } from "react";
import { Plus, Users, X } from "lucide-react";
import { employeeService } from "../../services/employeeService";
import { companyService } from "../../services/companyService";
import { extractErrorMessage } from "../../services/apiClient";
import Card from "../../components/Card";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import ErrorBanner from "../../components/ErrorBanner";
import StatusBadge from "../../components/StatusBadge";
import { useDataChange } from "../../hooks/useDataChange";
import PageHeader from "../../components/PageHeader";

const emptyForm = { username:"", email:"", first_name:"", last_name:"", password:"", department_id:"", employee_code:"", phone:"" };

export default function HODsPage() {
  const [hods, setHods] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  async function load() {
    const [h, d] = await Promise.all([employeeService.listHods(), companyService.departments()]);
    setHods(h.data); setDepartments(d.data);
  }
  useEffect(() => { load().catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false)); }, []);
  useDataChange(load, ["auth", "company"]);

  function startEdit(h) {
    setEditing(h);
    setForm({ username:h.username, email:h.email, first_name:h.first_name, last_name:h.last_name || "", password:"", department_id:h.department_id || departments.find(d => d.name === h.department)?.id || "", employee_code:h.employee_code || "", phone:h.phone || "" });
  }

  function reset() { setEditing(null); setForm(emptyForm); setShowCreate(false); }

  async function save(e) {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      const payload = { ...form };
      if (!payload.password) delete payload.password;
      if (!payload.department_id) delete payload.department_id;
      if (editing) await employeeService.updateUser(editing.id, payload);
      else await employeeService.createHod(payload);
      reset();
    } catch (err) { setError(extractErrorMessage(err)); } finally { setSaving(false); }
  }

  if (loading) return <div />;
  return <div className="page-shell space-y-5">
    <PageHeader eyebrow="People leadership" title="HOD Management" description="Create, review and maintain HOD accounts and department assignments." />
    {error && <ErrorBanner message={error} />}
    {!editing && <div className="flex justify-end"><Button onClick={()=>{setShowCreate(true);setError(null)}} className="gap-1.5"><Plus className="h-4 w-4"/> Create HOD</Button></div>}
    {(editing || showCreate) && <Card>
      <div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-semibold text-ink-900">{editing ? "Edit HOD" : "Create HOD account"}</h2>{(editing || showCreate) && <Button variant="secondary" onClick={reset}><X className="h-4 w-4" /> Cancel</Button>}</div>
      <form onSubmit={save} className="grid grid-cols-2 gap-2">
        {[["first_name","First name"],["last_name","Last name"],["username","Username"],["email","Email"],["employee_code","Employee code"],["phone","Phone"]].map(([key,label]) => <input key={key} required={key!=="last_name" && key!=="phone"} disabled={editing && key==="username"} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})} placeholder={label} className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm" />)}
        {!editing && <input required type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} placeholder="Password" className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm" />}
        {editing && <input type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} placeholder="New password (optional)" className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm" />}
        <select required={!editing} value={form.department_id} onChange={e=>setForm({...form,department_id:e.target.value})} className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm"><option value="">Select department</option>{departments.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select>
        <div className="col-span-2"><Button type="submit" loading={saving} className="gap-1.5"><Plus className="h-4 w-4" /> {editing ? "Save changes" : "Create HOD"}</Button></div>
      </form>
    </Card>}
    <Card>
      {hods.length===0 ? <EmptyState icon={Users} title="No HOD accounts" /> : <table className="w-full text-sm"><thead><tr className="border-b border-border-subtle text-left text-xs text-ink-500"><th className="pb-2">Name</th><th className="pb-2">Code</th><th className="pb-2">Department</th><th className="pb-2">Role</th><th className="pb-2"></th></tr></thead><tbody className="divide-y divide-border-subtle">{hods.map(h=><tr key={h.id}><td className="py-2.5">{`${h.first_name} ${h.last_name}`.trim()||h.username}</td><td className="py-2.5 text-ink-500">{h.employee_code||"-"}</td><td className="py-2.5 text-ink-500">{h.department||"-"}</td><td className="py-2.5"><StatusBadge status={h.role}/></td><td className="py-2.5 text-right"><Button variant="secondary" onClick={()=>startEdit(h)} className="!px-3 !py-1.5 text-xs">Edit</Button></td></tr>)}</tbody></table>}
    </Card>
  </div>;
}
