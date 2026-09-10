import { useEffect, useRef, useState } from "react";
import { Send, Plus } from "lucide-react";
import { workspaceService } from "../../services/workspaceService";
import { createSocket } from "../../services/websocketService";
import { useAuth } from "../../context/AuthContext";
import { formatDateTime } from "../../utils/format";
import IssueHeader from "./IssueHeader";
import TaskCard from "./TaskCard";
import NewTaskModal from "./NewTaskModal";
import ErrorBanner from "../../components/ErrorBanner";

export default function ChatPanel({ conversation, teamId, onIssueUpdated, onTaskCreated }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [showNewTask, setShowNewTask] = useState(false);
  const [sendError, setSendError] = useState(null);
  const scrollRef = useRef(null);
  const socketRef = useRef(null);

  useEffect(() => {
    setLoading(true);
    workspaceService.messages(conversation.id).then((res) => {
      setMessages((prev) => {
        const byId = new Map(res.data.map((item) => [item.id, item]));
        prev.forEach((item) => byId.set(item.id, item));
        return [...byId.values()].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
      });
      setLoading(false);
    }).catch(() => {
      setMessages([]);
      setLoading(false);
    });

    const socket = createSocket(`/ws/workspace/conversations/${conversation.id}/`, {
      onMessage: (msg) => setMessages((prev) => (
        prev.some((item) => item.id === msg.id) ? prev : [...prev, msg]
      )),
    });
    socketRef.current = socket;

    return () => socket.close();
  }, [conversation.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    const sentRealtime = socketRef.current?.send({ text });
    if (!sentRealtime) {
      try {
        const res = await workspaceService.sendMessage(conversation.id, text);
        setMessages((prev) => (
          prev.some((item) => item.id === res.data.id) ? prev : [...prev, res.data]
        ));
      } catch {
        setSendError("Message could not be sent. Please try again.");
        return;
      }
    }
    setSendError(null);
    setInput("");
  }

  function handleTaskCreated() {
    setShowNewTask(false);
    onTaskCreated();
  }

  return (
    <div className="workspace-chat-card">
      {conversation.issue && (
        <IssueHeader issue={conversation.issue} conversationTeamId={teamId} onUpdated={onIssueUpdated} />
      )}

      {conversation.kind === "ISSUE" && !conversation.task && (
        <div className="border-b border-border-subtle px-4 py-2.5">
          <button
            onClick={() => setShowNewTask(true)}
            className="focus-ring flex items-center gap-1.5 text-xs font-medium text-sky-600 hover:underline"
          >
            <Plus className="h-3.5 w-3.5" /> Create task for this issue
          </button>
        </div>
      )}

      {conversation.task && (
        <div className="border-b border-border-subtle p-3">
          <TaskCard task={conversation.task} onUpdated={onTaskCreated} />
        </div>
      )}

      <div ref={scrollRef} className="workspace-chat-messages flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {!loading && messages.length === 0 && (
          <p className="py-8 text-center text-sm text-ink-400">No messages yet. Say hello.</p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={m.sender === user?.id ? "flex justify-end" : "flex justify-start"}>
            <div className={`workspace-message max-w-[78%] rounded-2xl px-3.5 py-2.5 text-sm ${m.sender === user?.id ? "sent" : "received"}`}>
              {m.sender !== user?.id && <p className="mb-0.5 text-xs font-medium opacity-70">{m.sender_name}</p>}
              <p className="whitespace-pre-wrap">{m.text}</p>
              <p className={`mt-1 text-[10px] ${m.sender === user?.id ? "text-white/65" : "text-ink-400"}`}>{formatDateTime(m.created_at)}</p>
            </div>
          </div>
        ))}
      </div>

      {sendError && <div className="px-4 pt-3"><ErrorBanner message={sendError} /></div>}

      <form onSubmit={handleSend} className="workspace-chat-input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message the team…"
          className="focus-ring flex-1 rounded-xl border border-border-subtle bg-white px-3.5 py-2.5 text-sm"
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="focus-ring flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-600 text-white hover:bg-sky-700 disabled:bg-sky-300"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>

      {showNewTask && (
        <NewTaskModal conversationId={conversation.id} onClose={() => setShowNewTask(false)} onCreated={handleTaskCreated} />
      )}
    </div>
  );
}
