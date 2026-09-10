import { useEffect, useState } from "react";
import { Users2, MessageSquare } from "lucide-react";
import { teamService } from "../../services/teamService";
import LoadingScreen from "../../components/LoadingScreen";
import EmptyState from "../../components/EmptyState";
import ErrorBanner from "../../components/ErrorBanner";
import { extractErrorMessage } from "../../services/apiClient";
import { useDataChange } from "../../hooks/useDataChange";
import TeamConversationPanel from "./TeamConversationPanel";

export default function WorkspacePage() {
  const [teams, setTeams] = useState([]);
  const [selectedTeamId, setSelectedTeamId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadTeams() {
    try {
      const res = await teamService.list();
      setTeams(res.data || []);
      setSelectedTeamId((current) => {
        if (!res.data?.length) return null;
        if (current && res.data.some((team) => team.id === current)) return current;
        return res.data[0].id;
      });
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  useEffect(() => {
    setLoading(true);
    loadTeams().finally(() => setLoading(false));
  }, []);

  useDataChange(loadTeams, ["teams", "workspace", "auth"]);

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorBanner message={error} />;
  if (!teams.length) {
    return <EmptyState icon={Users2} title="No teams yet" description="You'll see your team workspace here once you're added to a team." />;
  }

  return (
    <div className="page-shell space-y-5">
      <div className="workspace-page-head">
        <div>
          <p className="page-eyebrow">Collaboration</p>
          <h2 className="mt-1 font-extrabold tracking-[-.035em] text-ink-900">Team Workspace</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
            Collaborate with your team, share updates, follow issues, and keep work moving in one place.
          </p>
        </div>
        <div className="workspace-live-pill">
          <MessageSquare className="h-4 w-4" />
          Live workspace
        </div>
      </div>

      <TeamConversationPanel
        teams={teams}
        teamId={selectedTeamId}
        onTeamChange={setSelectedTeamId}
      />
    </div>
  );
}
