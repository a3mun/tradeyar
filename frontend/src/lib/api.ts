/**
 * کلاینت Axios برای FastAPI
 */
import axios, { AxiosError, AxiosResponse } from "axios";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (res: AxiosResponse) => res,
  (err: AxiosError) => {
    if (process.env.NODE_ENV === "development") {
      console.error("[API]", err.config?.url, err.message);
    }
    return Promise.reject(err);
  }
);