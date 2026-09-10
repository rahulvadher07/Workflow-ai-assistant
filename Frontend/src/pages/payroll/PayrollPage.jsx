import { useEffect, useMemo, useState } from "react";
import { Wallet, Download, CheckCircle2, CalendarDays, BadgeIndianRupee } from "lucide-react";
import { payrollService } from "../../services/payrollService";
import { extractErrorMessage } from "../../services/apiClient";
import { useAuth } from "../../context/AuthContext";
import Card from "../../components/Card";
import Button from "../../components/Button";
import StatusBadge from "../../components/StatusBadge";
import LoadingScreen from "../../components/LoadingScreen";
import EmptyState from "../../components/EmptyState";
import ErrorBanner from "../../components/ErrorBanner";
import { formatCurrency, formatMinutesAsHours } from "../../utils/format";
import { getTokens } from "../../services/apiClient";
import { useDataChange } from "../../hooks/useDataChange";

export default function PayrollPage() {
  const { user } = useAuth();
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [error, setError] = useState(null);
  const [approving, setApproving] = useState(null);

  async function load() {
    const res = await payrollService.payslips();
    setPayslips(res.data);
  }

  useEffect(() => {
    load().catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false));
  }, []);
  useDataChange(load, "payroll");

  async function handleApprove(id) {
    setApproving(id);
    setError(null);
    try {
      await payrollService.approve(id);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setApproving(null);
    }
  }

  async function handleDownload(id) {
    const tokens = getTokens();
    const url = payrollService.downloadUrl(id);
    const res = await fetch(url, { headers: { Authorization: `Bearer ${tokens?.access}` } });
    const blob = await res.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `payslip_${id}.pdf`;
    link.click();
  }

  const isHodOrAdmin = user?.role === "HOD" || user?.role === "SUPER_ADMIN";
  const totalNet = useMemo(() => payslips.reduce((sum, item) => sum + Number(item.net_salary || 0), 0), [payslips]);
  const pendingCount = payslips.filter((p) => p.status === "DRAFT").length;
  const approvedCount = payslips.filter((p) => p.status === "HOD_APPROVED").length;

  if (loading) return <LoadingScreen />;

  return (
    <div className="page-shell payroll-page space-y-6">
      <div className="payroll-hero">
        <div>
          <p className="page-eyebrow !text-[#9ed6c8]">Compensation</p>
          <h2 className="mt-1 font-extrabold tracking-[-.04em] text-white">Payroll</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-white/70">Review payslips, approvals and detailed payroll components in one clean workspace.</p>
        </div>
        <div className="payroll-hero-badge"><BadgeIndianRupee className="h-5 w-5" /><span>Secure payroll workspace</span></div>
      </div>

      {error && <ErrorBanner message={error} />}

      {payslips.length === 0 ? (
        <Card className="section-card payroll-empty"><EmptyState icon={Wallet} title="No payroll records yet" description="Approved payslips will appear here." /></Card>
      ) : (
        <>
          <div className="stat-grid payroll-stat-grid">
            <Card className="stat-card card-hover"><div className="stat-icon"><Wallet className="h-5 w-5" /></div><p className="stat-value">{payslips.length}</p><p className="stat-label">Payslips</p><p className="stat-meta">Available in your workspace</p></Card>
            <Card className="stat-card card-hover"><div className="stat-icon"><BadgeIndianRupee className="h-5 w-5" /></div><p className="stat-value">{formatCurrency(totalNet)}</p><p className="stat-label">Total net value</p><p className="stat-meta">Across loaded payslips</p></Card>
            <Card className="stat-card card-hover"><div className="stat-icon"><CalendarDays className="h-5 w-5" /></div><p className="stat-value">{approvedCount}</p><p className="stat-label">Approved</p><p className="stat-meta">Ready to download</p></Card>
            <Card className="stat-card card-hover"><div className="stat-icon"><CheckCircle2 className="h-5 w-5" /></div><p className="stat-value">{pendingCount}</p><p className="stat-label">Awaiting approval</p><p className="stat-meta">Needs review</p></Card>
          </div>

          <div className="payroll-list">
            {payslips.map((p) => (
              <Card key={p.id} className={`payroll-card card-hover ${expandedId === p.id ? "is-open" : ""}`}>
                <div className="payroll-card-top">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="payroll-period-icon"><CalendarDays className="h-4 w-4" /></span>
                      <h3 className="text-[15px] font-bold text-ink-900">{p.period_label}</h3>
                      <StatusBadge status={p.status} />
                      {isHodOrAdmin && <span className="payroll-employee-tag">{p.employee_name}</span>}
                    </div>
                    <p className="mt-3 text-2xl font-extrabold tracking-[-.03em] text-ink-900">{formatCurrency(p.net_salary)}</p>
                    <p className="mt-1 text-xs text-ink-500">Net salary for this pay period</p>
                  </div>
                  <div className="payroll-actions">
                    <Button variant="secondary" onClick={() => setExpandedId(expandedId === p.id ? null : p.id)} className="!rounded-xl !px-3 !py-2 text-xs">
                      {expandedId === p.id ? "Hide details" : "View payslip"}
                    </Button>
                    {p.status === "HOD_APPROVED" && (
                      <Button variant="secondary" onClick={() => handleDownload(p.id)} className="gap-1.5 !rounded-xl !px-3 !py-2 text-xs">
                        <Download className="h-3.5 w-3.5" /> Download
                      </Button>
                    )}
                    {isHodOrAdmin && p.status === "DRAFT" && (
                      <Button onClick={() => handleApprove(p.id)} loading={approving === p.id} className="gap-1.5 !rounded-xl !px-3 !py-2 text-xs">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                      </Button>
                    )}
                  </div>
                </div>

                {expandedId === p.id && (
                  <div className="payroll-details-grid">
                    <Detail label="Working Days" value={p.working_days} />
                    <Detail label="Present Days" value={p.present_days} />
                    <Detail label="Leave Days" value={p.leave_days} />
                    <Detail label="Late Days" value={p.late_days} />
                    <Detail label="Overtime" value={formatMinutesAsHours(p.overtime_minutes)} />
                    <Detail label="Basic Salary" value={formatCurrency(p.basic_salary)} />
                    <Detail label="Allowances" value={formatCurrency(p.allowances)} />
                    <Detail label="Overtime Amount" value={formatCurrency(p.overtime_amount)} />
                    <Detail label="Gross Salary" value={formatCurrency(p.gross_salary)} />
                    <Detail label="PF Deduction" value={formatCurrency(p.pf_deduction)} />
                    <Detail label="Net Salary" value={formatCurrency(p.net_salary)} bold />
                  </div>
                )}
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Detail({ label, value, bold }) {
  return <div className="payroll-detail-item"><p className="text-[11px] font-semibold uppercase tracking-[.08em] text-ink-500">{label}</p><p className={`mt-1 text-sm text-ink-900 ${bold ? "font-extrabold" : "font-semibold"}`}>{value}</p></div>;
}
