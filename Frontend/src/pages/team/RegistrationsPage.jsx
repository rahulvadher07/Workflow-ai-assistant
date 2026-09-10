import { useEffect, useState } from "react";
import { UserPlus, Check, X, Clock3, UserRoundCheck } from "lucide-react";
import { authService } from "../../services/authService";
import { extractErrorMessage } from "../../services/apiClient";
import Card from "../../components/Card";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import ErrorBanner from "../../components/ErrorBanner";
import { useDataChange } from "../../hooks/useDataChange";
import PageHeader from "../../components/PageHeader";

export default function RegistrationsPage() {
  const [registrations, setRegistrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState(null);
  const [error, setError] = useState(null);
  async function load() { const res = await authService.pendingRegistrations(); setRegistrations(res.data); }
  useEffect(() => { load().catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false)); }, []);
  useDataChange(load, "auth");
  async function handleDecision(id, approve) { setActingId(id); setError(null); try { if (approve) await authService.approveRegistration(id); else await authService.rejectRegistration(id); } catch (err) { setError(extractErrorMessage(err)); } finally { setActingId(null); } }
  if (loading) return <div />;
  return (
    <div className="page-shell registrations-page space-y-6">
      <PageHeader eyebrow="Approvals" title="Registration Requests" description="Review pending employee registrations for your teams." />
      {error && <ErrorBanner message={error} />}
      <div className="registrations-banner"><span className="registrations-banner-icon"><Clock3 className="h-5 w-5" /></span><div><p className="text-sm font-extrabold text-white">Pending onboarding</p><p className="mt-1 text-xs text-white/70">Review each request and decide who can join your teams.</p></div><div className="registrations-count"><strong>{registrations.length}</strong><span>Waiting</span></div></div>

      <Card className="section-card registrations-panel">
        <div className="registrations-panel-head"><div><h2 className="text-base font-extrabold text-ink-900">Pending requests</h2><p className="mt-1 text-xs text-ink-500">Approve or reject applicants without leaving this page.</p></div><span className="registration-total-pill">{registrations.length} pending</span></div>
        {registrations.length === 0 ? <div className="py-10"><EmptyState icon={UserPlus} title="No pending registrations" description="New requests will appear here." /></div> : <ul className="registration-list">{registrations.map(r => <li key={r.id} className="registration-item"><div className="registration-avatar"><UserRoundCheck className="h-5 w-5" /></div><div className="min-w-0 flex-1"><p className="text-sm font-extrabold text-ink-900">{r.first_name} {r.last_name}</p><p className="mt-1 text-xs text-ink-500">{r.department} · {r.email}</p></div><div className="registration-actions"><Button onClick={() => handleDecision(r.id, true)} loading={actingId === r.id} className="gap-1.5 !rounded-xl !px-3 !py-2 text-xs"><Check className="h-3.5 w-3.5" /> Approve</Button><Button variant="secondary" onClick={() => handleDecision(r.id, false)} loading={actingId === r.id} className="gap-1.5 !rounded-xl !px-3 !py-2 text-xs"><X className="h-3.5 w-3.5" /> Reject</Button></div></li>)}</ul>}
      </Card>
    </div>
  );
}
