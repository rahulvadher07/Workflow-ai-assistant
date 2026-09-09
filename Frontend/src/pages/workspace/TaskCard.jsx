import { useState } from "react";
import { workspaceService } from "../../services/workspaceService";
import { extractErrorMessage } from "../../services/apiClient";
import { useAuth } from "../../context/AuthContext";
import StatusBadge from "../../components/StatusBadge";
import Button from "../../components/Button";
import ErrorBanner from "../../components/ErrorBanner";
import { formatDate } from "../../utils/format";

export default function TaskCard({ task, onUpdated }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Backend enforces the real rule (creator/assignee can start; creator
  // or HOD can end) - this only avoids showing a button that would 403.
  const canStart = task.status === "PENDING" && (user?.id === task.creator || user?.id === task.assignee || user?.role === "HOD");
  const canEnd = task.status === "IN_PROGRESS" && (user?.id === task.creator || user?.role === "HOD");

  async function handleAction(action) {
    setLoading(true);
    setError(null);
    try {
      if (action === "start") await workspaceService.startTask(task.id);
      else await workspaceService.endTask(task.id);
      onUpdated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-border-subtle bg-slate-50 p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-ink-500">{task.display_number}</span>
            <StatusBadge status={task.status} />
          </div>
          <p className="mt-1 text-sm font-medium text-ink-900">{task.description}</p>
          <p className="mt-1 text-xs text-ink-500">
            Created by {task.creator_name}{task.assignee_name ? ` · Assigned to ${task.assignee_name}` : ""}
            {task.deadline ? ` · Due ${formatDate(task.deadline)}` : ""}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          {canStart && (
            <Button onClick={() => handleAction("start")} loading={loading} variant="secondary" className="!px-3 !py-1.5 text-xs">
              Start Task
            </Button>
          )}
          {canEnd && (
            <Button onClick={() => handleAction("end")} loading={loading} className="!px-3 !py-1.5 text-xs">
              End Task
            </Button>
          )}
        </div>
      </div>
      {error && <div className="mt-2"><ErrorBanner message={error} /></div>}
    </div>
  );
}
