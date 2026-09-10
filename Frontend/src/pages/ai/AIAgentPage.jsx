import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  FileText,
  Lightbulb,
  MessageCircle,
  Paperclip,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";
import { aiService } from "../../services/aiService";
import { extractErrorMessage } from "../../services/apiClient";
import Spinner from "../../components/Spinner";
import { useAuth } from "../../context/AuthContext";

const QUICK_PROMPTS = [
  "What is the leave policy?",
  "How to apply for leave?",
  "Show my attendance",
  "When is salary credited?",
  "Company working hours",
  "How to raise an IT request?",
  "Who is my HOD?",
  "Show team members",
];

const ACTIONS = [
  { label: "Show leave history", icon: FileText, prompt: "Show my leave history" },
  { label: "Leave policy", icon: ShieldCheck, prompt: "What is the leave policy?" },
  { label: "Apply for leave", icon: CheckCircle2, prompt: "How do I apply for leave?" },
];

export default function AIAgentPage() {
  const { user } = useAuth();
  const storageKey = user?.id ? `workflow_ai_conversation_id_${user.id}` : "workflow_ai_conversation_id";
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([
    {
      role: "ASSISTANT",
      content:
        "Hi! I’m your WorkFlow AI assistant. I can help with company policies, HR questions, leave and attendance, payroll information, and general workplace guidance. What would you like to know today?",
    },
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
    aiService
      .conversation(savedId)
      .then((res) => {
        if (cancelled) return;
        const loadedMessages = (res.data.messages || []).filter(
          (m) => m.role === "USER" || m.role === "ASSISTANT",
        );
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

  function choosePrompt(prompt) {
    setInput(prompt);
    requestAnimationFrame(() => document.getElementById("ai-message-input")?.focus());
  }

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
      setMessages((prev) => [...prev, { role: "ASSISTANT", content: chatMessage }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1480px]">
      <div className="mb-5 flex flex-col gap-1 sm:mb-6">
        <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[0.14em] text-ink-400">
          <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
          WorkFlow AI
        </div>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-[27px] font-extrabold tracking-[-0.045em] text-ink-900">AI Agent</h2>
            <p className="mt-1 text-sm text-ink-500">Get help with your work, find information, and automate tasks.</p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-[#d9ebe5] bg-[#f1fbf7] px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.09em] text-emerald-700">
            <ShieldCheck className="h-3.5 w-3.5" /> Live &amp; Protected
          </div>
        </div>
      </div>

      <div className="grid items-stretch gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="overflow-hidden rounded-[22px] border border-[#dbe9e5] bg-white/95 shadow-[0_18px_45px_rgba(12,58,49,.07)]">
          <div className="border-b border-[#e7efed] bg-[linear-gradient(180deg,#fbfefd,#f5faf8)] px-5 py-4 sm:px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-[13px] bg-[#dff8ef] text-emerald-700 shadow-inner">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[14px] font-extrabold text-ink-900">Your workplace assistant</p>
                <p className="mt-0.5 text-xs text-ink-500">Ask naturally and get answers from your available company data and tools.</p>
              </div>
            </div>
          </div>

          <div ref={scrollRef} className="min-h-[430px] max-h-[calc(100vh-360px)] space-y-4 overflow-y-auto bg-[radial-gradient(circle_at_75%_10%,rgba(24,184,159,.07),transparent_26%)] px-5 py-5 sm:px-6">
            {messages.map((m, idx) => (
              <MessageBubble key={idx} role={m.role} content={m.content} />
            ))}

            {messages.length === 1 && !sending && (
              <div className="mt-2 flex flex-wrap gap-2 pl-[42px]">
                {ACTIONS.map(({ label, icon: Icon, prompt }) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => choosePrompt(prompt)}
                    className="inline-flex items-center gap-2 rounded-full border border-[#d5ebe4] bg-[#f7fcfa] px-3.5 py-2 text-[11px] font-bold text-[#2e6055] transition hover:-translate-y-0.5 hover:border-[#9fd4c5] hover:bg-white hover:shadow-sm"
                  >
                    <Icon className="h-3.5 w-3.5 text-emerald-600" />
                    {label}
                  </button>
                ))}
              </div>
            )}

            {sending && (
              <div className="flex items-center gap-2 pl-[42px] text-xs font-semibold text-ink-400">
                <Spinner className="h-4 w-4" /> Thinking…
              </div>
            )}
          </div>

          <form onSubmit={handleSend} className="border-t border-[#e3ece9] bg-white px-4 py-3 sm:px-5">
            <div className="flex items-center gap-2 rounded-[15px] border border-[#d9e9e4] bg-[#f8fbfa] p-1.5 shadow-inner">
              <button type="button" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[11px] text-ink-400 transition hover:bg-white hover:text-ink-700" aria-label="Attach">
                <Paperclip className="h-[17px] w-[17px]" />
              </button>
              <input
                id="ai-message-input"
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message…"
                className="min-w-0 flex-1 border-0 bg-transparent px-1 text-sm font-medium text-ink-800 outline-none placeholder:text-ink-400"
              />
              <button
                type="submit"
                disabled={!input.trim() || sending}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[11px] bg-[#12b891] text-white shadow-[0_8px_16px_rgba(18,184,145,.20)] transition hover:-translate-y-0.5 hover:bg-[#0ba37f] disabled:cursor-not-allowed disabled:bg-[#b6ded4]"
                aria-label="Send"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-2 flex items-center justify-between px-1 text-[10px] text-ink-400">
              <span>WorkFlow AI can make mistakes. Please verify important information.</span>
              {error && <RotateCcw className="h-3.5 w-3.5 text-amber-600" />}
            </div>
          </form>
        </section>

        <aside className="rounded-[22px] border border-[#dbe9e5] bg-white/95 p-4 shadow-[0_18px_45px_rgba(12,58,49,.06)]">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-[14px] font-extrabold text-ink-900">Suggested Questions</p>
              <p className="mt-0.5 text-[11px] text-ink-400">Quick prompts for common tasks.</p>
            </div>
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#e9faf5] text-emerald-600">
              <Lightbulb className="h-4 w-4" />
            </div>
          </div>

          <div className="space-y-2">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => choosePrompt(prompt)}
                className="group flex w-full items-center justify-between gap-3 rounded-[13px] border border-[#e5eeeb] bg-[#fbfdfc] px-3 py-3 text-left transition hover:-translate-y-0.5 hover:border-[#b9ddd3] hover:bg-white hover:shadow-sm"
              >
                <span className="text-[11px] font-bold leading-4 text-ink-700">{prompt}</span>
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-ink-300 transition group-hover:translate-x-0.5 group-hover:text-emerald-600" />
              </button>
            ))}
          </div>

          <div className="mt-4 rounded-[15px] border border-[#d6eee6] bg-[linear-gradient(135deg,#effbf7,#f8fdfb)] p-3.5">
            <div className="flex items-start gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-white text-emerald-600 shadow-sm">
                <MessageCircle className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[11px] font-extrabold text-ink-800">Work smarter with AI</p>
                <p className="mt-1 text-[10px] leading-4 text-ink-500">Ask about leave, attendance, payroll, policies, tasks, and more.</p>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function MessageBubble({ role, content }) {
  const isUser = role === "USER";
  return (
    <div className={`flex items-end gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full shadow-sm ${isUser ? "bg-[#0a3b34]" : "bg-[#11ae8e]"}`}>
        {isUser ? <User className="h-3.5 w-3.5 text-white" /> : <Bot className="h-4 w-4 text-white" />}
      </div>
      <div className={`max-w-[78%] ${isUser ? "text-right" : "text-left"}`}>
        <div
          className={`inline-block whitespace-pre-wrap rounded-[17px] px-4 py-3 text-[12px] leading-5 shadow-[0_5px_14px_rgba(20,58,51,.045)] ${
            isUser
              ? "rounded-br-[6px] bg-[#d9f6ed] text-[#1f5549]"
              : "rounded-bl-[6px] border border-[#e7efed] bg-[#f8fbfa] text-ink-800"
          }`}
        >
          {content}
        </div>
      </div>
    </div>
  );
}
