// frontend/src/lib/api.ts
import axios, { AxiosError } from "axios";
import { getToken, removeToken } from "@/lib/auth";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000",
  timeout: 120000,
});

let accessBlockedUntil = 0;

export function isAccessBlocked(): boolean {
  return Date.now() < accessBlockedUntil;
}

export function handleAuthFailure(status: number, detail?: unknown): boolean {
  if (typeof window === "undefined") return false;
  if (!getToken()) return false;

  const message = typeof detail === "string" ? detail : "";
  const path = window.location.pathname;

  if (status === 401) {
    removeToken();
    if (!path.startsWith("/login")) window.location.href = "/login";
    return true;
  }
  if (status === 403 && message.startsWith("SUBSCRIPTION_REQUIRED")) {
    accessBlockedUntil = Date.now() + 60_000;
    return true;
  }
  return false;
}

// 🔒 فاز ۱۷.۹۲ — پیام‌های دوستانه‌ی فارسی برای خطاهای HTTP.
const FRIENDLY_ERROR_MESSAGES: Record<number, string> = {
  400: "درخواست نامعتبر است. لطفاً ورودی‌ها را بررسی کنید.",
  401: "لطفاً دوباره وارد حساب کاربری خود شوید.",
  403: "شما به این بخش دسترسی ندارید.",
  404: "موردی یافت نشد.",
  429: "تعداد درخواست‌ها زیاد است. لطفاً کمی صبر کنید.",
  500: "خطایی رخ داد. لطفاً بعداً تلاش کنید.",
  502: "سرور موقتاً در دسترس نیست. لطفاً بعداً تلاش کنید.",
  503: "سرویس موقتاً در دسترس نیست. لطفاً بعداً تلاش کنید.",
};

export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;

    if (status && status >= 500) {
      return FRIENDLY_ERROR_MESSAGES[status] ?? FRIENDLY_ERROR_MESSAGES[500];
    }

    if (status && typeof detail === "string" && detail.trim().length > 0) {
      return detail;
    }

    if (status && FRIENDLY_ERROR_MESSAGES[status]) {
      return FRIENDLY_ERROR_MESSAGES[status];
    }

    if (!err.response) {
      return "ارتباط با سرور برقرار نشد. اتصال اینترنت خود را بررسی کنید.";
    }
  }

  return "خطایی رخ داد. لطفاً بعداً تلاش کنید.";
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (err: AxiosError) => {
    const url: string = err.config?.url || "";
    const status: number | undefined = err.response?.status;

    if (status && !url.includes("/auth/") && !url.includes("/backtest/reset")) {
      handleAuthFailure(status, (err.response?.data as { detail?: unknown })?.detail);
    }

    err.message = extractErrorMessage(err);

    if (status !== 404 && !url.includes("/analyze")) {
      console.warn(`[API Error] ${url || "Unknown URL"} - status=${status ?? "network"} - ${err.message}`);
    }
    return Promise.reject(err);
  }
);

export default api;