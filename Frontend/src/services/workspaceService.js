import { apiClient } from "./apiClient";

export const workspaceService = {
  conversations: (teamId) => apiClient.get(`/workspace/teams/${teamId}/conversations/`),
  messages: (conversationId) => apiClient.get(`/workspace/conversations/${conversationId}/messages/`),
  sendMessage: (conversationId, text) =>
    apiClient.post(`/workspace/conversations/${conversationId}/messages/`, { text }),
  issues: (teamId) => apiClient.get(`/workspace/teams/${teamId}/issues/`),
  createIssue: (teamId, payload) => apiClient.post(`/workspace/teams/${teamId}/issues/`, payload),
  updateIssueStatus: (issueId, status) => apiClient.patch(`/workspace/issues/${issueId}/status/`, { status }),
  createTask: (conversationId, payload) => apiClient.post(`/workspace/conversations/${conversationId}/tasks/`, payload),
  startTask: (taskId) => apiClient.post(`/workspace/tasks/${taskId}/start/`),
  endTask: (taskId) => apiClient.post(`/workspace/tasks/${taskId}/end/`),
};
