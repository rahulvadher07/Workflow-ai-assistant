import { useEffect, useState } from "react";
import { UserPlus, Check, X } from "lucide-react";
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

  async function load() {
    const res = await authService.pendingRegistrations();
    setRegistrations(res.data);
  }

  useEffect(() => {
    load().catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false));
  }, []);
  useDataChange(load, "auth");

  async function handleDecision(id, approve) {
    setActingId(id);
    setError(null);
    try {
      if (approve) await authService.approveRegistration(id);
      else await authService.rejectRegistration(id);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setActingId(null);
    }
  }

  if (loading) return <div />;

  return (
    <div className="page-shell space-y-5">
      <PageHeader eyebrow="Approvals" title="Registration Requests" description="Review pending employee registrations for your teams." />
      <Card className="section-card">
      <h2 className="mb-4 text-sm font-semibold text-ink-900">Registration Requests</h2>
      {error && <div className="mb-3"><ErrorBanner message={error} /></div>}

      {registrations.length === 0 ? (
        <EmptyState icon={UserPlus} title="No pending registrations" />
      ) : (
        <ul className="divide-y divide-border-subtle">
          {registrations.map((r) => (
            <li key={r.id} className="flex items-center justify-between py-3">
              <div>
                <p className="text-sm font-medium text-ink-900">{r.first_name} {r.last_name}</p>
                <p className="text-xs text-ink-500">{r.department} · {r.email}</p>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => handleDecision(r.id, true)}
                  loading={actingId === r.id}
                  className="gap-1.5 !px-3 !py-1.5 text-xs"
                >
                  <Check className="h-3.5 w-3.5" /> Approve
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => handleDecision(r.id, false)}
                  loading={actingId === r.id}
                  className="gap-1.5 !px-3 !py-1.5 text-xs"
                >
                  <X className="h-3.5 w-3.5" /> Reject
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      </Card>
    </div>
  );
}
