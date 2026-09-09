import { apiClient } from "./apiClient";

export const notificationService = {
  list: () => apiClient.get("/notifications/"),
  unreadCount: () => apiClient.get("/notifications/unread-count/"),
  markRead: (id) => apiClient.patch(`/notifications/${id}/read/`),
  markAllRead: () => apiClient.post("/notifications/mark-all-read/"),
  dailyBrief: () => apiClient.get("/notifications/daily-brief/"),
  create: (payload) => apiClient.post("/notifications/create/", payload),
};
