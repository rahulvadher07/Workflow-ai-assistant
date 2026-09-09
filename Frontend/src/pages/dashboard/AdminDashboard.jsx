import { useEffect, useState } from "react";
import { Building2, Users2, Wallet } from "lucide-react";
import Card from "../../components/Card";
import LoadingScreen from "../../components/LoadingScreen";
import { companyService } from "../../services/companyService";
import { payrollService } from "../../services/payrollService";
import { useDataChange } from "../../hooks/useDataChange";

export default function AdminDashboard() {
  const [departments, setDepartments] = useState([]);
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      companyService.departments().catch(() => ({ data: [] })),
      payrollService.payslips().catch(() => ({ data: [] })),
    ]).then(([deptRes, paysRes]) => {
      setDepartments(deptRes.data);
      setPayslips(paysRes.data);
      setLoading(false);
    });
  }, []);
  useDataChange(async () => {
    const [deptRes, paysRes] = await Promise.all([
      companyService.departments().catch(() => ({ data: [] })),
      payrollService.payslips().catch(() => ({ data: [] })),
    ]);
    setDepartments(deptRes.data);
    setPayslips(paysRes.data);
  }, ["company", "payroll"]);

  if (loading) return <LoadingScreen />;

  const approvedCount = payslips.filter((p) => p.status === "HOD_APPROVED").length;

  return (
    <div className="page-shell space-y-6">
      <div className="dashboard-hero">
        <div className="relative z-10"><p className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#74e6d1]">Administration</p><h2 className="mt-2 text-2xl font-extrabold tracking-[-.04em] text-white sm:text-3xl">Company operations at a glance</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-white/58">Manage structure, people, policies and payroll from one central control surface.</p></div>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="stat-card card-hover">
          <Building2 className="h-4 w-4 text-ink-400" />
          <p className="mt-3 text-2xl font-semibold text-ink-900">{departments.length}</p>
          <p className="mt-1 text-xs text-ink-500">Departments</p>
        </Card>
        <Card className="stat-card card-hover">
          <Users2 className="h-4 w-4 text-ink-400" />
          <p className="mt-3 text-2xl font-semibold text-ink-900">{departments.filter((d) => d.hod).length}</p>
          <p className="mt-1 text-xs text-ink-500">Departments with an assigned HOD</p>
        </Card>
        <Card className="stat-card card-hover">
          <Wallet className="h-4 w-4 text-ink-400" />
          <p className="mt-3 text-2xl font-semibold text-ink-900">{approvedCount}</p>
          <p className="mt-1 text-xs text-ink-500">Approved payslips</p>
        </Card>
      </div>

      <Card className="section-card">
        <div className="section-head"><div><h2>Departments</h2><p>Company structure and assigned HOD coverage.</p></div></div>
        <div className="table-shell">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-left text-xs text-ink-500">
              <th className="pb-2 font-medium">Name</th>
              <th className="pb-2 font-medium">HOD</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {departments.map((d) => (
              <tr key={d.id}>
                <td className="py-2 text-ink-700">{d.name}</td>
                <td className="py-2 text-ink-500">{d.hod_name || "Unassigned"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </Card>
    </div>
  );
}
