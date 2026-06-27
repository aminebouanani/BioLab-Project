import { apiClient, API_BASE_URL, safeApiCall } from "./client.js";

export function getLatestPdf(reportId) {
  return safeApiCall(async () => {
    const response = await apiClient.get(`/reports/${encodeURIComponent(reportId)}/pdf`);
    return response.data;
  });
}

export function generateFinalPdf(reportId) {
  return safeApiCall(async () => {
    const response = await apiClient.post(`/reports/${encodeURIComponent(reportId)}/generate-pdf`);
    return response.data;
  });
}

export function pdfDownloadUrl(reportId) {
  return `${API_BASE_URL}/reports/${encodeURIComponent(reportId)}/pdf/download`;
}
