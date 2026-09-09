import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, LogOut, ChevronDown, Sparkles } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useNotifications } from "../context/NotificationContext";

export default function TopBar({ title }) {
  const { user, logout } = useAuth();
  const { unreadCount } = useNotifications();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  async function handleLogout() { await logout(); navigate("/login"); }

  return (
    <header className="relative z-50 flex h-[82px] shrink-0 items-center justify-between border-b border-[#dbe9e5] bg-white/90 px-7 backdrop-blur-xl">
      <div className="min-w-0">
        <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.15em] text-[#78908b]"><Sparkles className="h-3 w-3 text-emerald-600" /> WorkFlow AI</div>
        <h1 className="mt-1 truncate text-[20px] font-extrabold tracking-[-.035em] text-ink-900">{title}</h1>
      </div>
      <div className="flex items-center gap-2.5">
        <button type="button" onClick={() => navigate("/notifications")} className="focus-ring relative flex h-10 w-10 items-center justify-center rounded-xl border border-[#dce8e5] bg-white text-ink-500 shadow-sm hover:bg-[#f8fbfa]" aria-label="Notifications">
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.8} />
          {unreadCount > 0 && <span className="absolute right-1 top-1 flex h-[17px] min-w-[17px] items-center justify-center rounded-full bg-rose-500 px-1 text-[9px] font-extrabold text-white">{unreadCount > 9 ? "9+" : unreadCount}</span>}
        </button>
        <div className="relative">
          <button type="button" onClick={() => setMenuOpen((v) => !v)} className="focus-ring flex items-center gap-2 rounded-xl border border-[#dce8e5] bg-white px-2.5 py-2 shadow-sm">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0a3b34] text-xs font-extrabold text-white">{(user?.first_name || user?.username || "?").charAt(0).toUpperCase()}</span>
            <span className="hidden max-w-[120px] truncate text-sm font-bold text-ink-700 sm:block">{user?.first_name || user?.username}</span>
            <ChevronDown className="h-4 w-4 text-ink-400" />
          </button>
          {menuOpen && (
            <div className="fixed right-7 top-[76px] z-[100] w-60 overflow-hidden rounded-2xl border border-[#146454] bg-[#0a4037] p-2 text-white shadow-[0_24px_55px_rgba(5,47,41,.26)]" onMouseLeave={() => setMenuOpen(false)}>
              <div className="rounded-xl bg-white/10 px-3 py-3">
                <p className="truncate text-sm font-extrabold">{user?.first_name || user?.username || "User"}</p>
                <p className="mt-0.5 truncate text-[10px] font-bold uppercase tracking-[.12em] text-emerald-200">{user?.role || "Account"}</p>
              </div>
              <button type="button" onClick={handleLogout} className="mt-2 flex min-h-11 w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-semibold text-white hover:bg-white/10"><LogOut className="h-4 w-4 text-emerald-200" /> Log out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
