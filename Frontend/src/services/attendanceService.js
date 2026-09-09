import { apiClient } from "./apiClient";

export const attendanceService = {
  punch: () => apiClient.post("/attendance/punch/"),
  today: () => apiClient.get("/attendance/me/today/"),
  history: (month) => apiClient.get("/attendance/me/", { params: month ? { month } : {} }),
  department: (params) => apiClient.get("/attendance/department/", { params }),
  monthly: (employeeId, month) =>
    apiClient.get(`/attendance/employee/${employeeId}/monthly/`, { params: month ? { month } : {} }),
};
