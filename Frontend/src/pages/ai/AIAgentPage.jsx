import { useEffect, useRef, useState } from "react";
import { Sparkles, Send, User, ShieldCheck, Lightbulb, RotateCcw } from "lucide-react";
import { aiService } from "../../services/aiService";
import { extractErrorMessage } from "../../services/apiClient";
import Spinner from "../../components/Spinner";
import { useAuth } from "../../context/AuthContext";

export default function AIAgentPage() {
  const { user } = useAuth();
  const storageKey = user?.id ? `workflow_ai_conversation_id_${user.id}` : "workflow_ai_conversation_id";
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([
    { role: "ASSISTANT", content: "Hi! I can help with leave requests, attendance questions, tasks, issues, and company policy. What do you need?" },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    let savedId = localStorage.getItem(storageKey);
    const legacyId = localStorage.getItem("workflow_ai_conversation_id");
    if (!savedId && legacyId) {
      savedId = legacyId;
      localStorage.setItem(storageKey, legacyId);
      localStorage.removeItem("workflow_ai_conversation_id");
    }
    if (!savedId) return;

    let cancelled = false;
    aiService.conversation(savedId)
      .then((res) => {
        if (cancelled) return;
        const loadedMessages = (res.data.messages || []).filter((m) => m.role === "USER" || m.role === "ASSISTANT");
        setConversationId(res.data.id);
        if (loadedMessages.length) setMessages(loadedMessages);
      })
      .catch(() => {
        localStorage.removeItem(storageKey);
      });

    return () => {
      cancelled = true;
    };
  }, [storageKey]);

  useEffect(() => {
    if (conversationId) localStorage.setItem(storageKey, String(conversationId));
  }, [conversationId, storageKey]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setError(null);
    setMessages((prev) => [...prev, { role: "USER", content: text }]);
    setInput("");
    setSending(true);

    try {
      const res = await aiService.chat(conversationId, text);
      setConversationId(res.data.conversation_id);
      localStorage.setItem(storageKey, String(res.data.conversation_id));
      setMessages((prev) => [...prev, { role: "ASSISTANT", content: res.data.reply }]);
    } catch (err) {
      const message = extractErrorMessage(err);
      const incidentId = err?.response?.data?.error?.incident_id;
      const chatMessage = incidentId
        ? `I couldn’t complete that request. ${message} Reference: ${incidentId}.`
        : `I couldn’t complete that request. ${message}`;
      setError(chatMessage);
      setMessages((prev) => [
        ...prev,
        { role: "ASSISTANT", content: chatMessage },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page-shell flex h-[calc(100vh-9.2rem)] min-h-[560px] flex-col overflow-hidden rounded-[24px] border border-[#d8e7e3] bg-white/90 shadow-[0_20px_55px_rgba(12,58,49,.08)] backdrop-blur-xl">
      <div className="relative flex items-center justify-between border-b border-[#dfeae7] bg-[linear-gradient(135deg,#f7fcfa,#ffffff)] px-6 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#e9fbf6] text-emerald-700 shadow-inner"><Sparkles className="h-5 w-5" /></div>
          <div className="min-w-0"><div className="flex items-center gap-2"><p className="text-[15px] font-extrabold text-ink-900">AI Agent</p><span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-wide text-emerald-700">Live</span></div><p className="mt-0.5 truncate text-xs text-ink-500">Ask about people operations, leave, attendance, tasks and policy.</p></div>
        </div>
        <span className="hidden items-center gap-1.5 rounded-full border border-emerald-100 bg-emerald-50/80 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700 sm:flex"><ShieldCheck className="h-3.5 w-3.5" /> Protected</span>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-5 overflow-y-auto bg-[radial-gradient(circle_at_75%_15%,rgba(20,184,166,.055),transparent_22%)] px-5 py-6 sm:px-7">
        {messages.map((m, idx) => (
          <MessageBubble key={idx} role={m.role} content={m.content} />
        ))}
        {messages.length === 1 && !sending && (
          <div className="grid gap-3 md:grid-cols-3">
            {["Show my attendance today", "What is my leave balance?", "How many hours did I work this month?"].map((prompt) => (
              <button key={prompt} type="button" onClick={() => setInput(prompt)} className="group rounded-2xl border border-[#dceae6] bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-[#bcdad1] hover:shadow-md">
                <Lightbulb className="h-4 w-4 text-emerald-600" />
                <span className="mt-3 block text-xs font-bold leading-5 text-ink-700">{prompt}</span>
              </button>
            ))}
          </div>
        )}

        {sending && (
          <div className="flex items-center gap-2 text-sm text-ink-500">
            <Spinner className="h-4 w-4" /> Thinking…
          </div>
        )}
      </div>

      <form onSubmit={handleSend} className="border-t border-[#dfeae7] bg-white/95 p-4 backdrop-blur">
        <div className="flex items-center gap-3 rounded-2xl border border-[#d8e7e3] bg-[#f8fbfa] px-3 py-2 shadow-inner">
          <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about leave, attendance, tasks, or policy…"
          className="focus-ring flex-1 rounded-lg border border-border-subtle px-3.5 py-2.5 text-sm"
          />
          <button
          type="submit"
          disabled={!input.trim() || sending}
          className="focus-ring flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sky-600 text-white hover:bg-sky-700 disabled:bg-sky-300"
          aria-label="Send"
        >
          <Send className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-2 flex items-center justify-between px-1 text-[10px] text-ink-400"><span>AI responses are grounded in your available company data and tools.</span>{error && <RotateCcw className="h-3 w-3" />}</div>
      </form>
    </div>
  );
}

function MessageBubble({ role, content }) {
  const isUser = role === "USER";
  return (
    <div className={`flex items-start gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${isUser ? "bg-navy-800" : "bg-sky-600"}`}>
        {isUser ? <User className="h-3.5 w-3.5 text-white" /> : <Sparkles className="h-3.5 w-3.5 text-white" />}
      </div>
      <div
        className={`max-w-[75%] whitespace-pre-wrap rounded-xl px-4 py-2.5 text-sm ${
          isUser ? "bg-navy-800 text-white" : "bg-slate-100 text-ink-900"
        }`}
      >
        {content}
      </div>
    </div>
  );
}
