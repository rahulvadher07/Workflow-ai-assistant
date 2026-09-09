import { apiClient } from "./apiClient";

export const leaveService = {
  hodRequests: () => apiClient.get("/leave/hod-requests/"),
  approveHod: (id) => apiClient.post(`/leave/hod-requests/${id}/approve/`),
  rejectHod: (id) => apiClient.post(`/leave/hod-requests/${id}/reject/`),
};
