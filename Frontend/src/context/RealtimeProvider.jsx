import { createContext, useContext, useEffect, useRef } from "react";
import { useAuth } from "./AuthContext";
import { createSocket } from "../services/websocketService";
import { emitDataChange } from "../services/dataChangeBus";

const RealtimeContext = createContext(null);

export function RealtimeProvider({ children }) {
  const { user } = useAuth();
  const socketRef = useRef(null);

  useEffect(() => {
    socketRef.current?.close();
    socketRef.current = null;
    if (!user) return undefined;

    const socket = createSocket("/ws/data-changes/", {
      onMessage: (change) => {
        if (!change?.resource) return;
        emitDataChange({ ...change, source: change.source || "backend_websocket" });
      },
    });
    socketRef.current = socket;

    return () => {
      socket.close();
      if (socketRef.current === socket) socketRef.current = null;
    };
  }, [user]);

  return <RealtimeContext.Provider value={{ connected: Boolean(socketRef.current) }}>{children}</RealtimeContext.Provider>;
}

export function useRealtime() {
  return useContext(RealtimeContext);
}
