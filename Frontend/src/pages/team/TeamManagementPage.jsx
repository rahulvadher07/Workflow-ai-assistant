import { useEffect, useState } from "react";
import { Plus, UserMinus, Users2, X } from "lucide-react";
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

  async function load() {
    const [teamsRes, employeesRes] = await Promise.all([teamService.list(), employeeService.list()]);
    setTeams(teamsRes.data);
    setEmployees(employeesRes.data);
  }

  useEffect(() => {
    load().catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false));
  }, []);
  useDataChange(load, ["teams", "auth", "company"]);

  async function handleCreateTeam(e) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await teamService.create({ name: newTeamName });
      setNewTeamName("");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function handleAddMember(teamId) {
    const employeeId = addMemberForm[teamId];
    if (!employeeId) return;
    setError(null);
    try {
      await teamService.addMember(teamId, { employee_id: employeeId });
      setAddMemberForm((f) => ({ ...f, [teamId]: "" }));
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleRemoveMember(teamId, employeeId) {
    setError(null);
    try {
      await teamService.removeMember(teamId, employeeId);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  if (loading) return <div />;

  return (
    <div className="page-shell space-y-5">
      <PageHeader eyebrow="People & teams" title="Team Management" description="Build teams, manage membership and keep team structure up to date." />
      {error && <ErrorBanner message={error} />}

      <div className="flex justify-end"><Button onClick={()=>setShowCreate(true)} className="gap-1.5"><Plus className="h-4 w-4"/> Add team</Button></div>
      {showCreate && <div className="modal-backdrop fixed inset-0 z-30 flex items-center justify-center p-4"><Card className="modal-panel w-full max-w-md"><div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold">New team</h2><button onClick={()=>setShowCreate(false)}><X className="h-4 w-4"/></button></div><form onSubmit={async e=>{await handleCreateTeam(e);setShowCreate(false)}} className="space-y-3"><input required value={newTeamName} onChange={e=>setNewTeamName(e.target.value)} placeholder="Team name" className="focus-ring w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"/><Button type="submit" loading={creating}>Create</Button></form></Card></div>}

      {teams.length === 0 ? (
        <EmptyState icon={Users2} title="No teams yet" description="Create your first team above." />
      ) : (
        teams.map((team) => {
          const memberIds = new Set(team.members.map((m) => m.employee));
          const availableEmployees = employees.filter((e) => !memberIds.has(e.id));
          return (
            <Card key={team.id}>
              <h3 className="text-sm font-semibold text-ink-900">{team.name}</h3>
              <p className="mt-0.5 text-xs text-ink-500">{team.member_count} member{team.member_count === 1 ? "" : "s"}</p>

              <ul className="mt-3 divide-y divide-border-subtle">
                {team.members.map((m) => (
                  <li key={m.id} className="flex items-center justify-between py-2 text-sm">
                    <span className="text-ink-700">{m.employee_name} {m.is_lead && <span className="ml-1 text-xs text-sky-600">(lead)</span>}</span>
                    <button
                      onClick={() => handleRemoveMember(team.id, m.employee)}
                      className="focus-ring rounded p-1 text-ink-400 hover:bg-red-50 hover:text-brand-red"
                      aria-label="Remove member"
                    >
                      <UserMinus className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
              </ul>

              <div className="mt-3"><Button variant="secondary" onClick={()=>setAddingTeamId(team.id)} className="gap-1.5 !px-3 !py-1.5 text-xs"><Plus className="h-3.5 w-3.5"/> Add member</Button></div>
              {addingTeamId===team.id && <div className="modal-backdrop fixed inset-0 z-30 flex items-center justify-center p-4"><Card className="modal-panel w-full max-w-md"><div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold">Add team member</h2><button onClick={()=>setAddingTeamId(null)}><X className="h-4 w-4"/></button></div><div className="space-y-3"><select value={addMemberForm[team.id]||""} onChange={e=>setAddMemberForm(f=>({...f,[team.id]:e.target.value}))} className="focus-ring w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"><option value="">Select employee</option>{availableEmployees.map(e=><option key={e.id} value={e.id}>{`${e.first_name} ${e.last_name}`.trim()||e.username}</option>)}</select><Button onClick={async()=>{await handleAddMember(team.id);setAddingTeamId(null)}}>Add member</Button></div></Card></div>}
            </Card>
          );
        })
      )}
    </div>
  );
}
