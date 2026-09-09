import { useEffect, useState } from "react";
import { FileText, Upload, Trash2, Plus, X } from "lucide-react";
import { knowledgeService } from "../../services/knowledgeService";
import { extractErrorMessage } from "../../services/apiClient";
import Card from "../../components/Card";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import ErrorBanner from "../../components/ErrorBanner";
import { formatDate } from "../../utils/format";
import { useDataChange } from "../../hooks/useDataChange";
import PageHeader from "../../components/PageHeader";

const CATEGORIES = ["LEAVE", "ATTENDANCE", "OVERTIME", "PAYROLL", "GENERAL"];

export default function KnowledgePage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("GENERAL");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);

  async function load() {
    const res = await knowledgeService.list();
    setDocuments(res.data);
  }

  useEffect(() => {
    load().catch((err) => setError(extractErrorMessage(err))).finally(() => setLoading(false));
  }, []);
  useDataChange(load, "company");

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("title", title);
      formData.append("category", category);
      formData.append("file", file);
      await knowledgeService.upload(formData);
      setTitle("");
      setCategory("GENERAL");
      setFile(null);
      e.target.reset();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    setError(null);
    try {
      await knowledgeService.remove(id);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  if (loading) return <div />;

  return (
    <div className="page-shell space-y-5">
      <PageHeader eyebrow="Company intelligence" title="Knowledge & Policy" description="Manage the documents used as an authoritative knowledge source for policy-aware answers." />
      <div className="flex justify-end"><Button onClick={()=>{setOpen(true);setError(null)}} className="gap-1.5"><Plus className="h-4 w-4"/> Add policy PDF</Button></div>
      {open && <div className="modal-backdrop fixed inset-0 z-30 flex items-center justify-center p-4"><Card className="modal-panel w-full max-w-xl"><div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold">Upload policy document</h2><button onClick={()=>setOpen(false)}><X className="h-4 w-4"/></button></div>
        <form onSubmit={async e=>{await handleUpload(e);setOpen(false)}} className="space-y-3">
          <input required value={title} onChange={e=>setTitle(e.target.value)} placeholder="Title" className="focus-ring w-full rounded-lg border border-border-subtle px-3 py-2 text-sm"/>
          <select value={category} onChange={e=>setCategory(e.target.value)} className="focus-ring w-full rounded-lg border border-border-subtle px-3 py-2 text-sm">{CATEGORIES.map(c=><option key={c}>{c}</option>)}</select>
          <input required type="file" accept="application/pdf" onChange={e=>setFile(e.target.files[0])} className="focus-ring w-full text-sm"/>
          <Button type="submit" loading={uploading} className="gap-1.5"><Upload className="h-4 w-4"/> Upload</Button>
        </form></Card></div>}

      <Card>
        {documents.length === 0 ? (
          <EmptyState icon={FileText} title="No documents uploaded yet" />
        ) : (
          <ul className="divide-y divide-border-subtle">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-ink-400" />
                  <div>
                    <p className="text-sm font-medium text-ink-900">{doc.title}</p>
                    <p className="text-xs text-ink-500">{doc.category} · Uploaded {formatDate(doc.created_at)} by {doc.uploaded_by_name}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="focus-ring rounded p-1.5 text-ink-400 hover:bg-red-50 hover:text-brand-red"
                  aria-label="Delete document"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
