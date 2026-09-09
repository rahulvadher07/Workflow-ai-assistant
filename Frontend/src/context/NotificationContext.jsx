import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { useAuth } from "./AuthContext";
import { notificationService } from "../services/notificationService";
import { createSocket } from "../services/websocketService";
import { emitDataChange } from "../services/dataChangeBus";

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const socketRef = useRef(null);

  const refresh = useCallback(async () => {
    if (!user) return;
    try {
      const [listRes, countRes] = await Promise.all([
        notificationService.list(),
        notificationService.unreadCount(),
      ]);
      // The REST API is authoritative. Replace the client snapshot so newly
      // created/updated notifications appear without a manual page refresh.
      setNotifications(
        [...listRes.data].sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at)
        )
      );
      setUnreadCount(countRes.data.unread_count);
    } catch {
      // silent - notifications are non-critical, page still works without them
    }
  }, [user]);

  useEffect(() => {
    if (!user) {
      socketRef.current?.close();
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    refresh();

    // Realtime UI updates are state-driven: when the WebSocket receives a
    // notification, setState immediately updates every mounted consumer.
    // No polling or focus/visibility synchronization is needed.
    const socket = createSocket("/ws/notifications/", {
      onMessage: (notification) => {
        setNotifications((prev) => {
          if (prev.some((item) => item.id === notification.id)) return prev;
          return [notification, ...prev];
        });
        setUnreadCount((prev) => prev + 1);

        const verb = String(notification?.verb || "").toUpperCase();
        const resource =
          verb.startsWith("LEAVE_") ? "leave" :
          verb.startsWith("TASK_") ? "workspace" :
          verb.startsWith("ISSUE_") ? "workspace" :
          verb.startsWith("PAYSLIP_") ? "payroll" :
          verb.startsWith("REGISTRATION_") ? "auth" :
          verb === "ANNOUNCEMENT" || verb === "DAILY_BRIEF" ? "notifications" :
          "notifications";
        emitDataChange({ resource, source: "notification_websocket", verb });
      },
    });
    socketRef.current = socket;

    return () => socket.close();
  }, [user, refresh]);

  async function markRead(id) {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    setUnreadCount((prev) => Math.max(0, prev - 1));
    try {
      await notificationService.markRead(id);
    } catch {
      refresh();
    }
  }

  async function markAllRead() {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
    try {
      await notificationService.markAllRead();
      await refresh();
    } catch {
      refresh();
    }
  }

  return (
    <NotificationContext.Provider value={{ notifications, unreadCount, refresh, markRead, markAllRead }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotifications must be used within NotificationProvider");
  return ctx;
}
