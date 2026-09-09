import { apiClient } from "./apiClient";

export const employeeService = {
  list: () => apiClient.get("/auth/employees/"),
  listHods: () => apiClient.get("/auth/hods/"),
  createHod: (payload) => apiClient.post("/auth/hods/create/", payload),
  updateUser: (id, payload) => apiClient.patch(`/auth/users/${id}/`, payload),
};
