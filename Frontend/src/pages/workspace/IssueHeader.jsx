import { useState } from "react";
import { workspaceService } from "../../services/workspaceService";
import { extractErrorMessage } from "../../services/apiClient";
import { useAuth } from "../../context/AuthContext";
import StatusBadge from "../../components/StatusBadge";
import Button from "../../components/Button";
import ErrorBanner from "../../components/ErrorBanner";
import { formatDateTime } from "../../utils/format";

const NEXT_STATUS = { OPEN: "IN_PROGRESS", IN_PROGRESS: "RESOLVED" };
const NEXT_LABEL = { OPEN: "Start work", IN_PROGRESS: "Mark resolved" };

export default function IssueHeader({ issue, onUpdated }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const nextStatus = NEXT_STATUS[issue.status];
  // Frontend hides the action a user can't perform, but the backend is
  // the actual authority - this is just to avoid a confusing 403 click.
  // Resolution is restricted to the issue lead or HOD; forward progress
  // (OPEN->IN_PROGRESS) is open to any team member viewing the chat.
  const canAct =
    nextStatus === "IN_PROGRESS" || (nextStatus === "RESOLVED" && (user?.id === issue.lead || user?.role === "HOD"));

  async function handleAdvance() {
    setLoading(true);
    setError(null);
    try {
      await workspaceService.updateIssueStatus(issue.id, nextStatus);
      onUpdated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border-b border-border-subtle px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-ink-500">{issue.display_number}</span>
            <StatusBadge status={issue.status} />
          </div>
          <h2 className="mt-1 text-sm font-semibold text-ink-900">{issue.title}</h2>
          {issue.description && <p className="mt-1 text-sm text-ink-500">{issue.description}</p>}
          <p className="mt-2 text-xs text-ink-400">
            Lead: {issue.lead_name || "Unassigned"} · Created {formatDateTime(issue.created_at)}
          </p>
        </div>

        {nextStatus && canAct && (
          <Button onClick={handleAdvance} loading={loading} variant="secondary" className="shrink-0">
            {NEXT_LABEL[issue.status]}
          </Button>
        )}
      </div>
      {error && <div className="mt-2"><ErrorBanner message={error} /></div>}
    </div>
  );
}
