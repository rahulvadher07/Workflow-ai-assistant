import axios from "axios";
import { emitDataChange } from "./dataChangeBus";

function resourceFromUrl(url = "") {
  const path = String(url).split("?")[0];
  if (path.includes("/notifications")) return "notifications";
  if (path.includes("/attendance")) return "attendance";
  if (path.includes("/leave")) return "leave";
  if (path.includes("/workspace")) return "workspace";
  if (path.includes("/teams")) return "teams";
  if (path.includes("/payroll")) return "payroll";
  if (path.includes("/company")) return "company";
  if (path.includes("/auth")) return "auth";
  return "global";
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (typeof window !== "undefined" && window.location.port !== "5173" ? "/api" : "http://localhost:8000/api");

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

function getTokens() {
  try {
    return JSON.parse(localStorage.getItem("workflow_ai_tokens") || "null");
  } catch {
    return null;
  }
}

function setTokens(tokens) {
  localStorage.setItem("workflow_ai_tokens", JSON.stringify(tokens));
}

function clearTokens() {
  localStorage.removeItem("workflow_ai_tokens");
}

apiClient.interceptors.request.use((config) => {
  const tokens = getTokens();
  if (tokens?.access) {
    config.headers.Authorization = `Bearer ${tokens.access}`;
  }
  return config;
});

let refreshPromise = null;

apiClient.interceptors.response.use(
  (response) => {
    const method = String(response.config?.method || "get").toLowerCase();
    if (!["get", "head", "options"].includes(method) && typeof window !== "undefined") {
      const detail = {
        resource: resourceFromUrl(response.config?.url || ""),
        url: response.config?.url || "",
        method,
      };
      emitDataChange(detail);
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    // Don't try to refresh on the auth endpoints themselves
    const isAuthEndpoint = originalRequest.url?.includes("/auth/login/") || originalRequest.url?.includes("/auth/refresh/");

    if (status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;
      const tokens = getTokens();

      if (!tokens?.refresh) {
        clearTokens();
        window.dispatchEvent(new Event("workflow_ai_session_expired"));
        return Promise.reject(error);
      }

      try {
        if (!refreshPromise) {
          refreshPromise = axios
            .post(`${API_BASE_URL}/auth/refresh/`, { refresh: tokens.refresh })
            .then((res) => {
              const newTokens = { access: res.data.access, refresh: res.data.refresh || tokens.refresh };
              setTokens(newTokens);
              return newTokens;
            })
            .finally(() => {
              refreshPromise = null;
            });
        }
        const newTokens = await refreshPromise;
        originalRequest.headers.Authorization = `Bearer ${newTokens.access}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        clearTokens();
        window.dispatchEvent(new Event("workflow_ai_session_expired"));
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export function extractErrorMessage(error) {
  const data = error?.response?.data;
  if (data?.error?.message) return data.error.message;
  if (typeof data === "string") return data;
  return "Something went wrong. Please try again.";
}

export function extractErrorCode(error) {
  return error?.response?.data?.error?.code || null;
}

export { getTokens, setTokens, clearTokens, API_BASE_URL };
