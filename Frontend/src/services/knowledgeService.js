import { apiClient } from "./apiClient";

export const knowledgeService = {
  list: () => apiClient.get("/company/knowledge/"),
  upload: (formData) =>
    apiClient.post("/company/knowledge/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  remove: (id) => apiClient.delete(`/company/knowledge/${id}/`),
};
