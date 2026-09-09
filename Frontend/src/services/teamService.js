import { apiClient } from "./apiClient";

export const teamService = {
  list: () => apiClient.get("/teams/"),
  detail: (id) => apiClient.get(`/teams/${id}/`),
  create: (payload) => apiClient.post("/teams/", payload),
  addMember: (teamId, payload) => apiClient.post(`/teams/${teamId}/members/`, payload),
  removeMember: (teamId, employeeId) => apiClient.delete(`/teams/${teamId}/members/${employeeId}/`),
};
