import { apiClient } from "./apiClient";

export const payrollService = {
  salary: (employeeId) => apiClient.get(`/payroll/salary/${employeeId}/`),
  setSalary: (employeeId, payload) => apiClient.put(`/payroll/salary/${employeeId}/`, payload),
  generate: (year, month) => apiClient.post("/payroll/generate/", { year, month }),
  payslips: (params) => apiClient.get("/payroll/payslips/", { params }),
  payslipDetail: (id) => apiClient.get(`/payroll/payslips/${id}/`),
  approve: (id) => apiClient.post(`/payroll/payslips/${id}/approve/`),
  downloadUrl: (id) => `${apiClient.defaults.baseURL}/payroll/payslips/${id}/download/`,
};
