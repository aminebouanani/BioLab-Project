import { apiClient, safeApiCall } from "./client.js";

export function listCases() {
  return safeApiCall(async () => {
    const response = await apiClient.get("/cases");
    return response.data;
  });
}

export function getCase(patientId, orderId, specimenId) {
  return safeApiCall(async () => {
    const response = await apiClient.get(
      `/cases/${encodeURIComponent(patientId)}/${encodeURIComponent(orderId)}`,
      { params: specimenId ? { specimen_id: specimenId } : {} }
    );
    return response.data;
  });
}
