import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authService } from "../services/authService";
import { getTokens, setTokens, clearTokens } from "../services/apiClient";
import { extractErrorMessage, extractErrorCode } from "../services/apiClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);

  const loadUser = useCallback(async () => {
    let tokens = getTokens();
    if (!tokens?.access) {
      setUser(null);
      setInitializing(false);
      return;
    }

    try {
      // Avoid an expected 401 on startup when the access token is already expired.
      // Refresh first when the refresh token is still valid.
      const accessPayload = JSON.parse(atob(tokens.access.split('.')[1]));
      const accessExpired = !accessPayload.exp || accessPayload.exp * 1000 <= Date.now();
      if (accessExpired) {
        if (!tokens.refresh) throw new Error('No refresh token');
        const refreshPayload = JSON.parse(atob(tokens.refresh.split('.')[1]));
        if (!refreshPayload.exp || refreshPayload.exp * 1000 <= Date.now()) {
          throw new Error('Refresh token expired');
        }
        const refreshRes = await authService.refresh(tokens.refresh);
        tokens = { access: refreshRes.data.access, refresh: refreshRes.data.refresh || tokens.refresh };
        setTokens(tokens);
      }

      const res = await authService.me();
      setUser(res.data);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setInitializing(false);
    }
  }, []);

  useEffect(() => {
    loadUser();

    function handleExpiry() {
      clearTokens();
      setUser(null);
    }
    window.addEventListener("workflow_ai_session_expired", handleExpiry);
    return () => window.removeEventListener("workflow_ai_session_expired", handleExpiry);
  }, [loadUser]);

  async function login(username, password) {
    try {
      const res = await authService.login(username, password);
      setTokens({ access: res.data.access, refresh: res.data.refresh });
      setUser(res.data.user);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        code: extractErrorCode(error),
        message: extractErrorMessage(error),
      };
    }
  }

  async function logout() {
    const tokens = getTokens();
    try {
      if (tokens?.refresh) await authService.logout(tokens.refresh);
    } catch {
      // best-effort - clear local state regardless
    }
    clearTokens();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, setUser, initializing, login, logout, reloadUser: loadUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
