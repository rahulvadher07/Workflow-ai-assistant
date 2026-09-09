import { useEffect, useState } from "react";
import { Users2, MessageSquare } from "lucide-react";
import { teamService } from "../../services/teamService";
import LoadingScreen from "../../components/LoadingScreen";
import EmptyState from "../../components/EmptyState";
import TeamConversationPanel from "./TeamConversationPanel";
import Card from "../../components/Card";
import ErrorBanner from "../../components/ErrorBanner";
import { extractErrorMessage } from "../../services/apiClient";
import { useDataChange } from "../../hooks/useDataChange";

export default function WorkspacePage() {
  const [teams, setTeams] = useState([]);
  const [selectedTeamId, setSelectedTeamId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    teamService.list().then((res) => {
      setTeams(res.data);
      if (res.data.length) setSelectedTeamId(res.data[0].id);
    }).catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false));
  }, []);
  useDataChange(async () => {
    try {
      const res = await teamService.list();
      setTeams(res.data);
      if (res.data.length && !res.data.some((team) => team.id === selectedTeamId)) setSelectedTeamId(res.data[0].id);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }, ["teams", "workspace", "auth"]);

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorBanner message={error} />;
  if (!teams.length) return <EmptyState icon={Users2} title="No teams yet" description="You'll see your team workspace here once you're added to a team." />;

  return (
    <div className="page-shell space-y-6">
      <div className="page-header"><div><p className="page-eyebrow">Collaboration</p><h2 className="mt-1 font-extrabold tracking-[-.035em] text-ink-900">Your teams</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">Choose a team to open its conversations, issues and tasks.</p></div>
        <div className="hidden items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700 sm:flex"><MessageSquare className="h-4 w-4" /> Live workspace</div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {teams.map((team) => {
          const active = selectedTeamId === team.id;
          return (
            <button key={team.id} type="button" onClick={() => setSelectedTeamId(team.id)} className="text-left">
              <Card className={`card-hover ${active ? "border-emerald-300 bg-emerald-50/70 shadow-[0_14px_34px_rgba(5,150,105,.12)]" : "hover:border-[#c6ddd7]"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${active ? "bg-emerald-600 text-white shadow-[0_10px_20px_rgba(5,150,105,.18)]" : "bg-[#eef6f3] text-ink-500"}`}>
                    <Users2 className="h-5 w-5" />
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${active ? "bg-sky-100 text-sky-700" : "bg-slate-100 text-ink-500"}`}>
                    {team.member_count} member{team.member_count === 1 ? "" : "s"}
                  </span>
                </div>
                <p className="mt-4 text-[15px] font-bold text-ink-900">{team.name}</p>
                <p className="mt-1 text-xs text-ink-500">Team conversations and work tracking</p>
              </Card>
            </button>
          );
        })}
      </div>

      {selectedTeamId && <TeamConversationPanel teamId={selectedTeamId} />}
    </div>
  );
}
