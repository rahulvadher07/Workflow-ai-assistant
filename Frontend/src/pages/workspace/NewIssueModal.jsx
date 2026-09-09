import { useState } from "react";
import { X } from "lucide-react";
import { workspaceService } from "../../services/workspaceService";
import { extractErrorMessage } from "../../services/apiClient";
import Button from "../../components/Button";
import ErrorBanner from "../../components/ErrorBanner";

export default function NewIssueModal({ teamId, onClose, onCreated }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await workspaceService.createIssue(teamId, { title, description });
      onCreated({ id: res.data.conversation });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/40 px-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink-900">New Issue</h2>
          <button onClick={onClose} className="focus-ring rounded p-1 text-ink-400 hover:bg-slate-100">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <ErrorBanner message={error} />}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">Title</label>
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="focus-ring w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"
              placeholder="Home Page Error"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-700">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="focus-ring w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"
              placeholder="Home page is not loading."
            />
          </div>
          <Button type="submit" loading={loading} className="w-full">Create issue</Button>
        </form>
      </div>
    </div>
  );
}
