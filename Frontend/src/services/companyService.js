import { apiClient } from "./apiClient";

export const companyService = {
  publicDepartments: () => apiClient.get("/company/departments/public/"),
  departments: () => apiClient.get("/company/departments/"),
  createDepartment: (payload) => apiClient.post("/company/departments/", payload),
  updateDepartment: (id, payload) => apiClient.patch(`/company/departments/${id}/`, payload),
  companyInfo: () => apiClient.get("/company/info/"),
  payrollRules: () => apiClient.get("/company/payroll-rules/"),
  rules: () => apiClient.get("/company/rules/"),
  createRule: (payload) => apiClient.post("/company/rules/", payload),
  updateRule: (id, payload) => apiClient.patch(`/company/rules/${id}/`, payload),
  deleteRule: (id) => apiClient.delete(`/company/rules/${id}/`),
};
