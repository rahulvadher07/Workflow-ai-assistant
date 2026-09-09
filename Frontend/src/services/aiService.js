import { apiClient } from "./apiClient";

export const aiService = {
  chat: (conversationId, message) =>
    apiClient.post("/ai/chat/", { conversation_id: conversationId ?? null, message }),
  conversation: (id) => apiClient.get(`/ai/conversations/${id}/`),
};
