/**
 * کلاینت Axios برای FastAPI
 */
import axios, { AxiosError, AxiosResponse } from "axios";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (res: AxiosResponse) => res,
  (err: AxiosError) => {
      // ═══ ۴۰۴ رو ignore کن (مورد انتظار برای بعضی جفت‌ها) ═══
      if (
        process.env.NODE_ENV === "development" &&
        err.response?.status !== 404
      ) {
        console.error("[API]", err.config?.url, err.message);
      }
    return Promise.reject(err);
  }
);