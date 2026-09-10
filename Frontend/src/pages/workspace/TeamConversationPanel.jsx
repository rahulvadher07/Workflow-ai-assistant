import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Hash, MessageSquare, Plus, Search, Users2, ListTodo } from "lucide-react";
import { workspaceService } from "../../services/workspaceService";
import LoadingScreen from "../../components/LoadingScreen";
import StatusBadge from "../../components/StatusBadge";
import ChatPanel from "./ChatPanel";
import NewIssueModal from "./NewIssueModal";
import Card from "../../components/Card";
import Button from "../../components/Button";
import ErrorBanner from "../../components/ErrorBanner";
import { extractErrorMessage } from "../../services/apiClient";
import { useDataChange } from "../../hooks/useDataChange";

export default function TeamConversationPanel({ teams, teamId, onTeamChange }) {
  const [conversations, setConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showNewIssue, setShowNewIssue] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("");

  async function loadConversations() {
    if (!teamId) return [];
    try {
      const res = await workspaceService.conversations(teamId);
      const data = res.data || [];
      setConversations(data);
      setSelectedConversationId((current) => {
        if (current && data.some((c) => c.id === current)) return current;
        const general = data.find((c) => c.kind === "TEAM_GENERAL");
        return general?.id ?? data[0]?.id ?? null;
      });
      setError(null);
      return data;
    } catch (err) {
      setError(extractErrorMessage(err));
      return [];
    }
  }

  useEffect(() => {
    setLoading(true);
    setSelectedConversationId(null);
    loadConversations().finally(() => setLoading(false));
  }, [teamId]);

  useDataChange(loadConversations, ["workspace", "teams"]);

  const selected = conversations.find((c) => c.id === selectedConversationId);
  const currentTeam = teams.find((team) => team.id === teamId);
  const issues = conversations.filter((c) => c.kind === "ISSUE" && c.issue);
  const tasks = conversations.filter((c) => c.task).map((c) => c.task);

  const visibleConversations = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) return conversations;
    return conversations.filter((conversation) => {
      const text = [
        conversation.kind,
        conversation.issue?.title,
        conversation.issue?.description,
        conversation.task?.description,
      ].filter(Boolean).join(" ").toLowerCase();
      return text.includes(query);
    });
  }, [conversations, filter]);

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="workspace-shell">
      <aside className="workspace-team-rail">
        <div className="workspace-panel-title-row">
          <div>
            <p className="workspace-kicker">Teams</p>
            <h3>Workspace</h3>
          </div>
          <span className="workspace-count-badge">{teams.length}</span>
        </div>
        <div className="workspace-team-list">
          {teams.map((team) => {
            const active = team.id === teamId;
            return (
              <button
                key={team.id}
                type="button"
                onClick={() => onTeamChange(team.id)}
                className={`workspace-team-item ${active ? "is-active" : ""}`}
              >
                <span className="workspace-team-icon"><Hash className="h-4 w-4" /></span>
                <span className="min-w-0 flex-1 text-left">
                  <span className="block truncate text-sm font-bold text-ink-900">{team.name}</span>
                  <span className="mt-0.5 block text-[11px] text-ink-500">{team.member_count} members</span>
                </span>
              </button>
            );
          })}
        </div>
        <div className="workspace-team-summary">
          <Users2 className="h-4 w-4 text-emerald-600" />
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[.08em] text-ink-400">Current team</p>
            <p className="mt-0.5 text-sm font-bold text-ink-900">{currentTeam?.name || "—"}</p>
          </div>
        </div>
      </aside>

      <section className="workspace-main-card">
        <div className="workspace-card-head">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="workspace-channel-dot"><MessageSquare className="h-3.5 w-3.5" /></span>
              <h3 className="truncate text-base font-extrabold text-ink-900">{currentTeam?.name || "Team"}</h3>
            </div>
            <p className="mt-1 text-xs text-ink-500">Conversations, issues and tasks for your team.</p>
          </div>
          <Button onClick={() => setShowNewIssue(true)} className="!min-h-9 !rounded-xl !px-3 !py-2 text-xs">
            <Plus className="h-3.5 w-3.5" />
            New Issue
          </Button>
        </div>

        <div className="workspace-content-grid">
          <div className="workspace-conversation-list">
            <div className="workspace-list-head">
              <div>
                <p className="text-sm font-extrabold text-ink-900">Conversations</p>
                <p className="text-[11px] text-ink-500">Pick a channel or issue.</p>
              </div>
              <div className="workspace-search-wrap">
                <Search className="h-3.5 w-3.5" />
                <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search" aria-label="Search conversations" />
              </div>
            </div>
            <div className="workspace-conversation-items">
              {visibleConversations.map((conversation) => {
                const active = selectedConversationId === conversation.id;
                const isIssue = conversation.kind === "ISSUE";
                return (
                  <button
                    key={conversation.id}
                    type="button"
                    className={`workspace-conversation-item ${active ? "is-active" : ""}`}
                    onClick={() => setSelectedConversationId(conversation.id)}
                  >
                    <span className={`workspace-conversation-icon ${isIssue ? "issue" : "general"}`}>
                      {isIssue ? <AlertCircle className="h-4 w-4" /> : <Hash className="h-4 w-4" />}
                    </span>
                    <span className="min-w-0 flex-1 text-left">
                      <span className="block truncate text-sm font-bold text-ink-900">
                        {isIssue ? conversation.issue?.title : "General"}
                      </span>
                      <span className="mt-0.5 block truncate text-[11px] text-ink-500">
                        {isIssue ? conversation.issue?.display_number : "Team conversation"}
                      </span>
                    </span>
                    {isIssue && conversation.issue?.status && <StatusBadge status={conversation.issue.status} />}
                  </button>
                );
              })}
              {!visibleConversations.length && (
                <div className="workspace-empty-row">No conversations match your search.</div>
              )}
            </div>
          </div>

          <div className="workspace-chat-wrap">
            {selected ? (
              <ChatPanel
                conversation={selected}
                teamId={teamId}
                onIssueUpdated={loadConversations}
                onTaskCreated={loadConversations}
              />
            ) : (
              <Card className="h-full flex items-center justify-center text-sm text-ink-500">Choose a conversation to get started.</Card>
            )}
          </div>
        </div>
      </section>

      <aside className="workspace-side-rail">
        <div className="workspace-side-card">
          <div className="workspace-side-head">
            <div>
              <p className="workspace-kicker">Work tracking</p>
              <h3>Issues</h3>
            </div>
            <span className="workspace-count-badge">{issues.length}</span>
          </div>
          <div className="workspace-side-list">
            {issues.slice(0, 5).map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                className="workspace-side-row"
                onClick={() => setSelectedConversationId(conversation.id)}
              >
                <span className="workspace-side-icon issue"><AlertCircle className="h-4 w-4" /></span>
                <span className="min-w-0 flex-1 text-left">
                  <span className="block truncate text-xs font-bold text-ink-900">{conversation.issue.title}</span>
                  <span className="mt-0.5 block text-[10px] text-ink-500">{conversation.issue.display_number}</span>
                </span>
                {conversation.issue.status && <StatusBadge status={conversation.issue.status} />}
              </button>
            ))}
            {!issues.length && <p className="workspace-empty-row">No issues yet.</p>}
          </div>
        </div>

        <div className="workspace-side-card">
          <div className="workspace-side-head">
            <div>
              <p className="workspace-kicker">Work items</p>
              <h3>Tasks</h3>
            </div>
            <span className="workspace-count-badge">{tasks.length}</span>
          </div>
          <div className="workspace-side-list">
            {tasks.slice(0, 5).map((task) => (
              <button
                key={task.id}
                type="button"
                className="workspace-side-row"
                onClick={() => {
                  const taskConversation = conversations.find((c) => c.task?.id === task.id);
                  if (taskConversation) setSelectedConversationId(taskConversation.id);
                }}
              >
                <span className="workspace-side-icon task"><ListTodo className="h-4 w-4" /></span>
                <span className="min-w-0 flex-1 text-left">
                  <span className="block line-clamp-2 text-xs font-bold text-ink-900">{task.description}</span>
                  <span className="mt-0.5 block text-[10px] text-ink-500">{task.display_number}</span>
                </span>
                <StatusBadge status={task.status} />
              </button>
            ))}
            {!tasks.length && <p className="workspace-empty-row">No tasks yet.</p>}
          </div>
        </div>

        <div className="workspace-side-footer">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700"><Users2 className="h-4 w-4" /></div>
          <div>
            <p className="text-xs font-extrabold text-ink-900">{currentTeam?.member_count ?? 0} team members</p>
            <p className="mt-0.5 text-[11px] text-ink-500">Keep everyone aligned in real time.</p>
          </div>
        </div>
      </aside>

      {showNewIssue && (
        <NewIssueModal
          teamId={teamId}
          onClose={() => setShowNewIssue(false)}
          onCreated={async ({ id }) => {
            setShowNewIssue(false);
            setSelectedConversationId(id);
            await loadConversations();
          }}
        />
      )}
    </div>
  );
}
