import { apiClient } from "./apiClient";

export const authService = {
  login: (username, password) => apiClient.post("/auth/login/", { username, password }),
  refresh: (refresh) => apiClient.post("/auth/refresh/", { refresh }),
  register: (payload) => apiClient.post("/auth/register/", payload),
  logout: (refresh) => apiClient.post("/auth/logout/", { refresh }),
  changePassword: (old_password, new_password) =>
    apiClient.post("/auth/change-password/", { old_password, new_password }),
  me: () => apiClient.get("/auth/me/"),
  updateProfile: (payload) => apiClient.patch("/auth/me/", payload),
  pendingRegistrations: () => apiClient.get("/auth/registrations/pending/"),
  approveRegistration: (id) => apiClient.post(`/auth/registrations/${id}/approve/`),
  rejectRegistration: (id) => apiClient.post(`/auth/registrations/${id}/reject/`),
};
