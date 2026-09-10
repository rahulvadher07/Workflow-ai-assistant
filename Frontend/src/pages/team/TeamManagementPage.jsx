import { useEffect, useState } from "react";
import { Plus, UserMinus, Users2, X, UsersRound, UserPlus, Crown } from "lucide-react";
import { teamService } from "../../services/teamService";
import { employeeService } from "../../services/employeeService";
import { extractErrorMessage } from "../../services/apiClient";
import { useDataChange } from "../../hooks/useDataChange";
import Card from "../../components/Card";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import ErrorBanner from "../../components/ErrorBanner";
import PageHeader from "../../components/PageHeader";

export default function TeamManagementPage() {
  const [teams, setTeams] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newTeamName, setNewTeamName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [addMemberForm, setAddMemberForm] = useState({});
  const [showCreate, setShowCreate] = useState(false);
  const [addingTeamId, setAddingTeamId] = useState(null);

  async function load() { const [teamsRes, employeesRes] = await Promise.all([teamService.list(), employeeService.list()]); setTeams(teamsRes.data); setEmployees(employeesRes.data); }
  useEffect(() => { load().catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false)); }, []);
  useDataChange(load, ["teams", "auth", "company"]);
  async function handleCreateTeam(e) { e.preventDefault(); setCreating(true); setError(null); try { await teamService.create({ name: newTeamName }); setNewTeamName(""); } catch (err) { setError(extractErrorMessage(err)); } finally { setCreating(false); } }
  async function handleAddMember(teamId) { const employeeId = addMemberForm[teamId]; if (!employeeId) return; setError(null); try { await teamService.addMember(teamId, { employee_id: employeeId }); setAddMemberForm((f) => ({ ...f, [teamId]: "" })); } catch (err) { setError(extractErrorMessage(err)); } }
  async function handleRemoveMember(teamId, employeeId) { setError(null); try { await teamService.removeMember(teamId, employeeId); } catch (err) { setError(extractErrorMessage(err)); } }
  if (loading) return <div />;

  return (
    <div className="page-shell team-management-page space-y-6">
      <PageHeader eyebrow="People & teams" title="Team Management" description="Build teams, manage membership and keep team structure up to date." actions={<Button onClick={() => setShowCreate(true)} className="gap-1.5"><Plus className="h-4 w-4" /> Add team</Button>} />
      {error && <ErrorBanner message={error} />}

      <div className="team-management-banner"><div className="team-banner-icon"><UsersRound className="h-6 w-6" /></div><div><p className="text-sm font-extrabold text-white">Organize teams around the work</p><p className="mt-1 text-xs text-white/70">Keep membership, leads and team structure visible at a glance.</p></div><div className="team-banner-stat"><strong>{teams.length}</strong><span>Teams</span></div><div className="team-banner-stat"><strong>{employees.length}</strong><span>Employees</span></div></div>

      {showCreate && <div className="modal-backdrop fixed inset-0 z-30 flex items-center justify-center p-4"><Card className="modal-panel w-full max-w-md p-6"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-extrabold text-ink-900">Create a new team</h2><p className="mt-1 text-xs text-ink-500">Give the team a clear working name.</p></div><button className="rounded-lg p-2 text-ink-400 hover:bg-emerald-50 hover:text-ink-900" onClick={() => setShowCreate(false)}><X className="h-4 w-4" /></button></div><form onSubmit={async e => { await handleCreateTeam(e); setShowCreate(false); }} className="space-y-4"><input required value={newTeamName} onChange={e => setNewTeamName(e.target.value)} placeholder="Team name" className="page-control w-full" /><Button type="submit" loading={creating}>Create team</Button></form></Card></div>}

      {teams.length === 0 ? <Card className="section-card"><EmptyState icon={Users2} title="No teams yet" description="Create your first team above." /></Card> : (
        <div className="team-card-grid">
          {teams.map((team) => {
            const memberIds = new Set(team.members.map((m) => m.employee));
            const availableEmployees = employees.filter((e) => !memberIds.has(e.id));
            return (
              <Card key={team.id} className="team-management-card card-hover">
                <div className="team-card-header"><div className="team-card-title-wrap"><span className="team-card-icon"><Users2 className="h-4 w-4" /></span><div><h3 className="text-sm font-extrabold text-ink-900">{team.name}</h3><p className="mt-1 text-xs text-ink-500">{team.member_count} member{team.member_count === 1 ? "" : "s"}</p></div></div><span className="team-count-pill">{team.member_count}</span></div>
                <ul className="team-member-list">
                  {team.members.length === 0 ? <li className="team-member-empty">No members yet.</li> : team.members.map((m) => <li key={m.id} className="team-member-row"><div className="flex min-w-0 items-center gap-2"><span className="member-avatar">{m.employee_name?.[0]?.toUpperCase() || "U"}</span><span className="truncate text-sm font-semibold text-ink-700">{m.employee_name}</span>{m.is_lead && <span className="team-lead-pill"><Crown className="h-3 w-3" /> Lead</span>}</div><button onClick={() => handleRemoveMember(team.id, m.employee)} className="remove-member-btn" aria-label="Remove member"><UserMinus className="h-3.5 w-3.5" /></button></li>)}
                </ul>
                <Button variant="secondary" onClick={() => setAddingTeamId(team.id)} className="mt-4 w-full gap-1.5 !rounded-xl !py-2 text-xs"><UserPlus className="h-3.5 w-3.5" /> Add member</Button>
                {addingTeamId === team.id && <div className="modal-backdrop fixed inset-0 z-30 flex items-center justify-center p-4"><Card className="modal-panel w-full max-w-md p-6"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-base font-extrabold text-ink-900">Add team member</h2><p className="mt-1 text-xs text-ink-500">Choose an employee who is not already in this team.</p></div><button className="rounded-lg p-2 text-ink-400 hover:bg-emerald-50 hover:text-ink-900" onClick={() => setAddingTeamId(null)}><X className="h-4 w-4" /></button></div><div className="space-y-4"><select value={addMemberForm[team.id] || ""} onChange={e => setAddMemberForm(f => ({ ...f, [team.id]: e.target.value }))} className="page-control w-full"><option value="">Select employee</option>{availableEmployees.map(e => <option key={e.id} value={e.id}>{`${e.first_name} ${e.last_name}`.trim() || e.username}</option>)}</select><Button onClick={async () => { await handleAddMember(team.id); setAddingTeamId(null); }}>Add member</Button></div></Card></div>}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
