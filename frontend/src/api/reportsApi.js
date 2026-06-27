import { apiClient, safeApiCall } from "./client.js";

export function listReports() {
  return safeApiCall(async () => {
    const response = await apiClient.get("/reports");
    return response.data;
  });
}

export function getReport(reportId) {
  return safeApiCall(async () => {
    const response = await apiClient.get(`/reports/${encodeURIComponent(reportId)}`);
    return response.data;
  });
}

export function generateReport(payload) {
  return safeApiCall(async () => {
    const response = await apiClient.post("/reports/generate", payload);
    return response.data;
  });
}

export function regenerateReport(reportId) {
  return safeApiCall(async () => {
    const response = await apiClient.post(`/reports/${encodeURIComponent(reportId)}/regenerate`);
    return response.data;
  });
}

export function validateReport(reportId, comment) {
  return safeApiCall(async () => {
    const response = await apiClient.post(`/reports/${encodeURIComponent(reportId)}/validate`, {
      comment: comment || null
    });
    return response.data;
  });
}

export function rejectReport(reportId, comment) {
  return safeApiCall(async () => {
    const response = await apiClient.post(`/reports/${encodeURIComponent(reportId)}/reject`, {
      comment: comment || null
    });
    return response.data;
  });
}

export function checkOutdated(reportId) {
  return safeApiCall(async () => {
    const response = await apiClient.post(`/reports/${encodeURIComponent(reportId)}/check-outdated`);
    return response.data;
  });
}

export function getChatHistory(reportId) {
  return safeApiCall(async () => {
    const response = await apiClient.get(`/reports/${encodeURIComponent(reportId)}/chat`);
    return response.data;
  });
}

export function askReportQuestion(reportId, question) {
  return safeApiCall(async () => {
    const response = await apiClient.post(`/reports/${encodeURIComponent(reportId)}/chat`, {
      question
    });
    return response.data;
  });
}
