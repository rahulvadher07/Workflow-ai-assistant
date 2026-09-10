import { useEffect, useState } from "react";
import { Check, X, ClipboardList } from "lucide-react";
import { leaveService } from "../../services/leaveService";
import { extractErrorMessage } from "../../services/apiClient";
import { useDataChange } from "../../hooks/useDataChange";
import PageHeader from "../../components/PageHeader";
import Card from "../../components/Card";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import ErrorBanner from "../../components/ErrorBanner";

export default function HODLeaveApprovalPage(){
 const [requests,setRequests]=useState([]); const [loading,setLoading]=useState(true); const [error,setError]=useState(null);
 async function load(){try{setRequests((await leaveService.hodRequests()).data)}catch(e){setError(extractErrorMessage(e))}}
 useEffect(()=>{load().finally(()=>setLoading(false))},[]); useDataChange(load,"leave");
 async function decide(id,action){setError(null);try{if(action==="approve")await leaveService.approveHod(id);else await leaveService.rejectHod(id)}catch(e){setError(extractErrorMessage(e))}}
 if(loading)return <div/>;
 return <div className="page-shell admin-page space-y-5"><PageHeader eyebrow="Approvals" title="HOD Leave Approval" description="Review leave requests that require company-level approval." />{error&&<ErrorBanner message={error}/>}<Card><h2 className="text-sm font-semibold text-ink-900">HOD Leave Approval</h2><p className="mt-1 text-xs text-ink-500">Review pending leave requests submitted by HODs.</p></Card>{requests.length===0?<EmptyState icon={ClipboardList} title="No HOD leave requests"/>:<div className="space-y-3">{requests.map(r=><Card key={r.id}><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-medium text-sky-600">{r.department} · {r.leave_type}</p><p className="mt-1 text-sm font-semibold text-ink-900">{r.employee_name}</p><p className="mt-1 text-xs text-ink-500">{r.from_date} → {r.to_date} · {r.days} day(s)</p><p className="mt-2 text-sm text-ink-700">{r.reason}</p><p className="mt-2 text-xs text-ink-400">Status: {r.status}</p></div>{r.status==="PENDING"&&<div className="flex shrink-0 gap-2"><Button onClick={()=>decide(r.id,"approve")} className="gap-1.5 !px-3 !py-1.5 text-xs"><Check className="h-3.5 w-3.5"/> Approve</Button><Button variant="secondary" onClick={()=>decide(r.id,"reject")} className="gap-1.5 !px-3 !py-1.5 text-xs"><X className="h-3.5 w-3.5"/> Reject</Button></div>}</div></Card>)}</div>}</div>;
}
