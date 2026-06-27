import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_AI_BACKEND_URL || "http://127.0.0.1:8001";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000
});

export function getErrorMessage(error) {
  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error?.response?.data?.message) {
    return error.response.data.message;
  }
  if (error?.code === "ECONNABORTED") {
    return "The AI backend request timed out. Remote MedGemma may still be generating.";
  }
  if (error?.message === "Network Error") {
    return `AI backend unavailable at ${API_BASE_URL}. Start uvicorn on port 8001 and check CORS.`;
  }
  return error?.message || "Unexpected dashboard error.";
}

export async function safeApiCall(fn) {
  try {
    return await fn();
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}
