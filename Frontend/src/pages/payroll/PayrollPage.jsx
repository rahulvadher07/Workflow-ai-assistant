import { useEffect, useState } from "react";
import { Wallet, Download, CheckCircle2 } from "lucide-react";
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

  if (loading) return <LoadingScreen />;

  const isHodOrAdmin = user?.role === "HOD" || user?.role === "SUPER_ADMIN";

  return (
    <div className="page-shell space-y-6">
      <div className="page-header"><div><p className="page-eyebrow">Compensation</p><h2 className="mt-1 font-extrabold tracking-[-.035em] text-ink-900">Payroll</h2><p className="mt-2 text-sm leading-6 text-ink-500">Review payslips, approvals and detailed payroll components.</p></div></div>
      {error && <ErrorBanner message={error} />}

      {payslips.length === 0 ? (
        <EmptyState icon={Wallet} title="No payroll records yet" description="Approved payslips will appear here." />
      ) : (
        payslips.map((p) => (
          <Card key={p.id} className="card-hover">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-ink-900">{p.period_label}</h3>
                  <StatusBadge status={p.status} />
                  {isHodOrAdmin && <span className="text-xs text-ink-400">{p.employee_name}</span>}
                </div>
                <p className="mt-1 text-lg font-semibold text-ink-900">{formatCurrency(p.net_salary)}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setExpandedId(expandedId === p.id ? null : p.id)} className="!px-3 !py-1.5 text-xs">
                  {expandedId === p.id ? "Hide details" : "View Payslip"}
                </Button>
                {p.status === "HOD_APPROVED" && (
                  <Button variant="secondary" onClick={() => handleDownload(p.id)} className="gap-1.5 !px-3 !py-1.5 text-xs">
                    <Download className="h-3.5 w-3.5" /> Download
                  </Button>
                )}
                {isHodOrAdmin && p.status === "DRAFT" && (
                  <Button onClick={() => handleApprove(p.id)} loading={approving === p.id} className="gap-1.5 !px-3 !py-1.5 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                  </Button>
                )}
              </div>
            </div>

            {expandedId === p.id && (
              <div className="mt-5 grid grid-cols-2 gap-3 border-t border-[#e6efec] pt-5 text-sm sm:grid-cols-4">
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
        ))
      )}
    </div>
  );
}

function Detail({ label, value, bold }) {
  return (
    <div>
      <p className="text-xs text-ink-500">{label}</p>
      <p className={`text-ink-900 ${bold ? "font-semibold" : ""}`}>{value}</p>
    </div>
  );
}
