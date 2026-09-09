import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, X, ShieldCheck } from "lucide-react";
import { companyService } from "../../services/companyService";
import { apiClient, extractErrorMessage } from "../../services/apiClient";
import Card from "../../components/Card";
import Button from "../../components/Button";
import ErrorBanner from "../../components/ErrorBanner";
import LoadingScreen from "../../components/LoadingScreen";
import { useDataChange } from "../../hooks/useDataChange";
import PageHeader from "../../components/PageHeader";

const emptyRule = { title: "", category: "GENERAL", details: "" };

export default function CompanyRulesPage() {
  const [company, setCompany] = useState(null);
  const [payrollRule, setPayrollRule] = useState(null);
  const [rules, setRules] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [ruleForm, setRuleForm] = useState(emptyRule);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    const [c, p, r] = await Promise.all([companyService.companyInfo(), companyService.payrollRules(), companyService.rules()]);
    setCompany(c.data); setPayrollRule(p.data); setRules(r.data);
  }

  useEffect(() => { load().catch(setError).finally(() => setLoading(false)); }, []);
  useDataChange(load, "company");

  async function handleSaveSettings(e) {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      await Promise.all([apiClient.patch("/company/info/", company), apiClient.patch("/company/payroll-rules/", payrollRule)]);
    } catch (err) { setError(extractErrorMessage(err)); } finally { setSaving(false); }
  }

  function openCreate() { setEditingRule(null); setRuleForm(emptyRule); setShowForm(true); setError(null); }
  function openEdit(rule) { setEditingRule(rule); setRuleForm({ title: rule.title, category: rule.category, details: rule.details }); setShowForm(true); setError(null); }

  async function saveRule(e) {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (editingRule) await companyService.updateRule(editingRule.id, ruleForm);
      else await companyService.createRule(ruleForm);
      setShowForm(false); setRuleForm(emptyRule);
    } catch (err) { setError(extractErrorMessage(err)); } finally { setSaving(false); }
  }

  async function deleteRule(id) {
    if (!window.confirm("Delete this company rule?")) return;
    try { await companyService.deleteRule(id); } catch (err) { setError(extractErrorMessage(err)); }
  }

  if (loading) return <LoadingScreen />;
  return <div className="page-shell space-y-5">
    <PageHeader eyebrow="Governance" title="Company Rules" description="Keep company-wide operating rules and payroll settings in one place." />
    {error && <ErrorBanner message={error?.message ? error.message : error} />}

    <div className="flex items-center justify-between">
      <div><h2 className="text-base font-semibold text-ink-900">Company Rules</h2><p className="text-xs text-ink-500">Keep reusable company rules in one place.</p></div>
      <Button onClick={openCreate} className="gap-1.5"><Plus className="h-4 w-4" /> Add rule</Button>
    </div>

    {showForm && <Card>
      <div className="mb-3 flex items-center justify-between"><h3 className="text-sm font-semibold text-ink-900">{editingRule ? "Edit rule" : "New company rule"}</h3><button onClick={()=>setShowForm(false)}><X className="h-4 w-4 text-ink-400" /></button></div>
      <form onSubmit={saveRule} className="grid grid-cols-2 gap-3">
        <input required value={ruleForm.title} onChange={e=>setRuleForm({...ruleForm,title:e.target.value})} placeholder="Rule name e.g. Salary Rule" className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm" />
        <select value={ruleForm.category} onChange={e=>setRuleForm({...ruleForm,category:e.target.value})} className="focus-ring rounded-lg border border-border-subtle px-3 py-2 text-sm"><option value="PAYROLL">Payroll</option><option value="TIME">Time</option><option value="ATTENDANCE">Attendance</option><option value="LEAVE">Leave</option><option value="GENERAL">General</option></select>
        <textarea required value={ruleForm.details} onChange={e=>setRuleForm({...ruleForm,details:e.target.value})} rows="4" placeholder="Rule details" className="focus-ring col-span-2 rounded-lg border border-border-subtle px-3 py-2 text-sm" />
        <div className="col-span-2 flex gap-2"><Button type="submit" loading={saving}>{editingRule ? "Save changes" : "Create rule"}</Button><Button type="button" variant="secondary" onClick={()=>setShowForm(false)}>Cancel</Button></div>
      </form>
    </Card>}

    {rules.length === 0 ? <EmptyRule /> : <div className="grid grid-cols-3 gap-4">{rules.map(rule => <Card key={rule.id} className="relative"><div className="flex items-start gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-50"><ShieldCheck className="h-4 w-4 text-sky-600" /></div><div className="min-w-0"><p className="text-sm font-semibold text-ink-900">{rule.title}</p><p className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-sky-600">{rule.category}</p><p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-ink-500">{rule.details}</p></div></div><div className="mt-3 flex gap-1"><button onClick={()=>openEdit(rule)} className="rounded p-1.5 text-ink-400 hover:bg-slate-100"><Pencil className="h-3.5 w-3.5" /></button><button onClick={()=>deleteRule(rule.id)} className="rounded p-1.5 text-ink-400 hover:bg-red-50 hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button></div></Card>)}</div>}

    <form onSubmit={handleSaveSettings} className="space-y-4">
      <Card><h2 className="mb-3 text-sm font-semibold text-ink-900">Company settings</h2><Field label="Company name" value={company.name} onChange={(v)=>setCompany({...company,name:v})}/><Field label="Standard break (minutes)" type="number" value={company.standard_break_minutes} onChange={(v)=>setCompany({...company,standard_break_minutes:v})}/><Field label="Standard shift (minutes)" type="number" value={company.standard_shift_minutes} onChange={(v)=>setCompany({...company,standard_shift_minutes:v})}/><Field label="Shift start time" type="time" value={company.shift_start_time} onChange={(v)=>setCompany({...company,shift_start_time:v})}/></Card>
      <Card><h2 className="mb-3 text-sm font-semibold text-ink-900">Payroll rules</h2><Field label="PF percent" type="number" step="0.01" value={payrollRule.pf_percent} onChange={(v)=>setPayrollRule({...payrollRule,pf_percent:v})}/><Field label="Overtime multiplier" type="number" step="0.01" value={payrollRule.overtime_multiplier} onChange={(v)=>setPayrollRule({...payrollRule,overtime_multiplier:v})}/><Field label="Late threshold (minutes)" type="number" value={payrollRule.late_threshold_minutes} onChange={(v)=>setPayrollRule({...payrollRule,late_threshold_minutes:v})}/></Card>
      <Button type="submit" loading={saving}>Save settings</Button>
    </form>
  </div>;
}
function Field({label,value,onChange,type="text",step}){return <div className="mb-3"><label className="mb-1.5 block text-sm font-medium text-ink-700">{label}</label><input type={type} step={step} value={value} onChange={e=>onChange(e.target.value)} className="focus-ring w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"/></div>}
function EmptyRule(){return <Card><p className="text-sm text-ink-500">No custom company rules yet. Add your first rule above.</p></Card>}
