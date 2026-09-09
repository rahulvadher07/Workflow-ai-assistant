import { useEffect, useState } from "react";
import { Plus, MessageSquare, AlertCircle } from "lucide-react";
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

export default function TeamConversationPanel({ teamId }) {
  const [conversations, setConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showNewIssue, setShowNewIssue] = useState(false);
  const [error, setError] = useState(null);

  async function loadConversations() { const res = await workspaceService.conversations(teamId); setConversations(res.data); return res.data; }
  useEffect(() => { setLoading(true); setError(null); loadConversations().then(data => { const general=data.find(c=>c.kind==="TEAM_GENERAL"); setSelectedConversationId(general?.id ?? data[0]?.id ?? null); }).catch(err => setError(extractErrorMessage(err))).finally(()=>setLoading(false)); }, [teamId]);
  useDataChange(loadConversations, ["workspace", "teams"]);
  if (loading) return <LoadingScreen />;
  if (error) return <ErrorBanner message={error} />;

  const general = conversations.find(c=>c.kind==="TEAM_GENERAL");
  const issues = conversations.filter(c=>c.kind==="ISSUE" && c.issue);
  const selected = conversations.find(c=>c.id===selectedConversationId);

  return <div className="page-shell space-y-5">
    <div className="grid grid-cols-2 gap-3">
      {general && <button className="text-left" onClick={()=>setSelectedConversationId(general.id)}><Card className={selectedConversationId===general.id ? "border-sky-300 ring-1 ring-sky-200" : "hover:border-sky-200"}><div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-50"><MessageSquare className="h-4 w-4 text-sky-600"/></div><div><p className="text-sm font-semibold text-ink-900">Team Chat</p><p className="text-xs text-ink-500">General team conversation</p></div></div></Card></button>}
      <Card><div className="flex items-center justify-between gap-3"><div><p className="text-sm font-semibold text-ink-900">Issues</p><p className="text-xs text-ink-500">Click an issue card to open its dedicated chat.</p></div><Button onClick={()=>setShowNewIssue(true)} className="gap-1.5 !px-3 !py-1.5 text-xs"><Plus className="h-3.5 w-3.5"/> New Issue</Button></div></Card>
    </div>

    <div className="grid grid-cols-3 gap-3">
      {issues.map(c => <button key={c.id} className="text-left" onClick={()=>setSelectedConversationId(c.id)}><Card className={selectedConversationId===c.id ? "border-sky-300 ring-1 ring-sky-200" : "hover:border-sky-200"}><div className="flex items-start justify-between gap-2"><div className="flex gap-2"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500"/><div><p className="text-xs font-medium text-sky-600">{c.issue.display_number}</p><p className="text-sm font-semibold text-ink-900">{c.issue.title}</p><p className="mt-1 text-xs text-ink-500 line-clamp-2">{c.issue.description}</p><p className="mt-2 text-[11px] text-ink-400">Created by {c.issue.created_by_name || "—"}</p></div></div>{c.issue.status && <StatusBadge status={c.issue.status}/>}</div></Card></button>)}
      {issues.length===0 && <div className="col-span-3"><Card><p className="text-sm text-ink-500">No issues yet.</p></Card></div>}
    </div>

    {selected && <div className="h-[calc(100vh-24rem)] min-h-[480px]"><ChatPanel conversation={selected} teamId={teamId} onIssueUpdated={loadConversations} onTaskCreated={loadConversations}/></div>}
    {showNewIssue && <NewIssueModal teamId={teamId} onClose={()=>setShowNewIssue(false)} onCreated={async ({id})=>{setShowNewIssue(false); setSelectedConversationId(id);}}/>}
  </div>;
}
