import { API_BASE_URL, getTokens, setTokens } from "./apiClient";

function resolveWebSocketBaseUrl() {
  const configured = import.meta.env.VITE_WS_BASE_URL?.trim();
  if (configured) {
    return configured
      .replace(/^http:\/\//i, "ws://")
      .replace(/^https:\/\//i, "wss://")
      .replace(/\/$/, "");
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  // Vite dev runs the Django API/WebSocket server on 8000. In production the
  // same origin is reverse-proxied by nginx, so do not hard-code port 8000.
  if (window.location.port === "5173") return `${protocol}://${window.location.hostname}:8000`;
  return `${protocol}://${window.location.host}`;
}

const WS_BASE_URL = resolveWebSocketBaseUrl();

async function refreshAccessToken() {
  const tokens = getTokens();
  if (!tokens?.refresh) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: tokens.refresh }),
    });

    if (!response.ok) return false;
    const data = await response.json();
    if (!data?.access) return false;

    setTokens({
      access: data.access,
      refresh: data.refresh || tokens.refresh,
    });
    return true;
  } catch {
    return false;
  }
}

/**
 * Reconnecting WebSocket wrapper for authenticated notifications/workspace
 * sockets. The access token is attached as ?token=..., matching the backend
 * JWTAuthMiddleware.
 */
export function createSocket(path, { onMessage, onOpen, onClose, onError } = {}) {
  let socket = null;
  let reconnectAttempts = 0;
  let closedByClient = false;
  let reconnectTimer = null;
  let refreshing = false;
  let authRecoveryAttempts = 0;

  function scheduleReconnect() {
    if (closedByClient || reconnectTimer) return;
    const delay = Math.min(1000 * 2 ** reconnectAttempts, 10000);
    reconnectAttempts += 1;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, delay);
  }

  async function recoverAuthenticationAndReconnect() {
    if (closedByClient || refreshing || authRecoveryAttempts >= 1) return;
    refreshing = true;
    authRecoveryAttempts += 1;

    const refreshed = await refreshAccessToken();
    refreshing = false;

    if (closedByClient) return;
    if (refreshed) {
      reconnectAttempts = 0;
      authRecoveryAttempts = 0;
      connect();
      return;
    }

    window.dispatchEvent(new Event("workflow_ai_session_expired"));
  }

  function connect() {
    if (closedByClient) return;

    const tokens = getTokens();
    if (!tokens?.access) return;

    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    const separator = normalizedPath.includes("?") ? "&" : "?";
    const url = `${WS_BASE_URL}${normalizedPath}${separator}token=${encodeURIComponent(tokens.access)}`;

    try {
      socket = new WebSocket(url);
    } catch (error) {
      onError?.(error);
      scheduleReconnect();
      return;
    }

    socket.onopen = (event) => {
      reconnectAttempts = 0;
      authRecoveryAttempts = 0;
      onOpen?.(event);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch {
        // Ignore malformed frames; REST remains the source of truth.
      }
    };

    socket.onclose = (event) => {
      onClose?.(event);

      if (closedByClient) return;

      if (event.code === 4401) {
        recoverAuthenticationAndReconnect();
        return;
      }

      // 4403 means the authenticated user is forbidden; refreshing the same
      // identity cannot solve that, so avoid a noisy retry loop.
      if (event.code === 4403) return;

      scheduleReconnect();
    };

    socket.onerror = (event) => {
      onError?.(event);
    };
  }

  connect();

  return {
    send(data) {
      if (socket?.readyState !== WebSocket.OPEN) return false;
      try {
        socket.send(JSON.stringify(data));
        return true;
      } catch {
        return false;
      }
    },
    close() {
      closedByClient = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      socket?.close(1000, "client closed");
    },
  };
}
