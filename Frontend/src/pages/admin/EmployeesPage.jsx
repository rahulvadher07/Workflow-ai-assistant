import { useEffect, useState } from "react";
import { Users2 } from "lucide-react";
import { employeeService } from "../../services/employeeService";
import { companyService } from "../../services/companyService";
import { extractErrorMessage } from "../../services/apiClient";
import Card from "../../components/Card";
import EmptyState from "../../components/EmptyState";
import StatusBadge from "../../components/StatusBadge";
import Button from "../../components/Button";
import PageHeader from "../../components/PageHeader";
import ErrorBanner from "../../components/ErrorBanner";
import { useDataChange } from "../../hooks/useDataChange";

export default function EmployeesPage() {
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ email:"", first_name:"", last_name:"", phone:"", employee_code:"", department_id:"", password:"" });
  const [error, setError] = useState(null);

  async function load() {
    const [e, d] = await Promise.all([employeeService.list(), companyService.departments()]);
    setEmployees(e.data);
    setDepartments(d.data);
  }

  useEffect(() => { load().catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false)); }, []);
  useDataChange(load, ["auth", "company"]);

  function startEdit(employee) {
    setEditing(employee);
    setForm({
      email: employee.email || "", first_name: employee.first_name || "", last_name: employee.last_name || "",
      phone: employee.phone || "", employee_code: employee.employee_code || "", department_id: employee.department_id || "", password: "",
    });
  }

  async function saveEdit(e) {
    e.preventDefault();
    setError(null);
    try {
      const payload = { ...form };
      if (!payload.password) delete payload.password;
      await employeeService.updateUser(editing.id, payload);
      setEditing(null);
    } catch (err) { setError(extractErrorMessage(err)); }
  }

  if (loading) return <div />;

  return (
    <div className="page-shell admin-page space-y-5">
      <PageHeader eyebrow="Administration" title="Employees" description="Manage your organization’s employees, roles and access." />
      {error && <ErrorBanner message={error} />}
      <div className="admin-stat-grid">
        <div className="admin-stat-card"><div className="admin-stat-icon admin-icon-green"><Users2 className="h-4 w-4" /></div><div><p className="admin-stat-label">Total Employees</p><p className="admin-stat-value">{employees.length}</p></div></div>
        <div className="admin-stat-card"><div className="admin-stat-icon admin-icon-blue"><Users2 className="h-4 w-4" /></div><div><p className="admin-stat-label">Active Accounts</p><p className="admin-stat-value">{employees.filter(e => String(e.status || '').toUpperCase() === 'ACTIVE' || e.is_active === true).length || employees.length}</p></div></div>
        <div className="admin-stat-card"><div className="admin-stat-icon admin-icon-amber"><Users2 className="h-4 w-4" /></div><div><p className="admin-stat-label">HOD Accounts</p><p className="admin-stat-value">{employees.filter(e => String(e.role || '').toUpperCase() === 'HOD').length}</p></div></div>
        <div className="admin-stat-card"><div className="admin-stat-icon admin-icon-purple"><Users2 className="h-4 w-4" /></div><div><p className="admin-stat-label">Departments</p><p className="admin-stat-value">{departments.length}</p></div></div>
      </div>
      <Card className="section-card admin-table-card">
        {employees.length === 0 ? (
          <EmptyState icon={Users2} title="No employees found" />
        ) : (
          <>
            <div className="admin-table-head"><div><h3>Employee Directory</h3><p>Search and review employee access details.</p></div><div className="admin-table-caption">{employees.length} records</div></div>
            <table className="w-full text-sm">
            <thead><tr className="border-b border-border-subtle text-left text-xs text-ink-500">
              <th className="pb-2 font-medium">Name</th><th className="pb-2 font-medium">Employee Code</th><th className="pb-2 font-medium">Department</th><th className="pb-2 font-medium">Role</th><th className="pb-2" />
            </tr></thead>
            <tbody className="divide-y divide-border-subtle">
              {employees.map((e) => (
                <tr key={e.id}>
                  <td className="py-2.5 text-ink-700">{`${e.first_name} ${e.last_name}`.trim() || e.username}</td>
                  <td className="py-2.5 text-ink-500">{e.employee_code || "-"}</td>
                  <td className="py-2.5 text-ink-500">{e.department || "-"}</td>
                  <td className="py-2.5"><StatusBadge status={e.role} /></td>
                  <td className="py-2.5 text-right"><Button variant="secondary" onClick={() => startEdit(e)} className="!px-3 !py-1.5 text-xs">Edit</Button></td>
                </tr>
              ))}
            </tbody>
            </table>
          </>
        )}
      </Card>

      {editing && <Card>
        <h3 className="mb-3 text-sm font-semibold text-ink-900">Edit employee</h3>
        <form onSubmit={saveEdit} className="grid grid-cols-2 gap-2">
          {[["first_name","First name"],["last_name","Last name"],["email","Email"],["phone","Phone"],["employee_code","Employee code"]].map(([key,label]) => (
            <input key={key} required={key !== "last_name" && key !== "phone"} value={editing ? (form[key] ?? editing[key] ?? "") : form[key]} onChange={ev => setForm({...form, [key]: ev.target.value})} placeholder={label} className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm" />
          ))}
          <select value={form.department_id || editing.department_id || ""} onChange={ev => setForm({...form, department_id: ev.target.value})} className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm">
            <option value="">Keep current department</option>
            {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <input type="password" value={form.password} onChange={ev => setForm({...form, password: ev.target.value})} placeholder="New password (optional)" className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm" />
          <div className="col-span-2"><Button type="submit">Save changes</Button></div>
        </form>
      </Card>}
    </div>
  );
}
