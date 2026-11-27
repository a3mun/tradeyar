// frontend/src/lib/api.ts
import axios from "axios";
import { getToken, removeToken } from "@/lib/auth";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000",
  timeout: 120000, // 🔴 افزایش تایم‌اوت به ۲ دقیقه برای تحلیل‌های سنگین
});

/**
 * 🔒 رفتار یکسان برای خطای احراز هویت/اشتراک (axios، fetch و WebSocket):
 *   • ۴۰۱ با توکن موجود  → توکن منقضی/نامعتبر: خروج و رفتن به /login
 *   • ۴۰۳ با SUBSCRIPTION_REQUIRED → هیچ هدایتی نمی‌شود (کاربر منقضی باید
 *     بتواند داشبورد، تیکت‌ها و صفحه‌ی اشتراک را ببیند)؛ فقط درخواست‌های
 *     پس‌زمینه‌ی تحلیل تا ۶۰ ثانیه متوقف می‌شوند و صفحه‌ی اصلی خودش پیام
 *     «اشتراک لازم است» را نشان می‌دهد.
 * اگر کاربر اصلاً توکن ندارد (بازدیدکننده‌ی صفحات عمومی) هیچ کاری نمی‌شود.
 */
let accessBlockedUntil = 0;

/** آیا تحلیل‌های پس‌زمینه باید فعلاً متوقف باشند؟ (بعد از ۴۰۳ اشتراک) */
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

// ارسال خودکار توکن ورود در همه‌ی درخواست‌ها
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// اینترسپتور برای مدیریت خطاها
api.interceptors.response.use(
  (response) => response,
  (err) => {
    const url: string = err.config?.url || "";
    const status: number | undefined = err.response?.status;

    // ورود/OTP و ریست ادمین (کلید ادمین جدا دارد) از هدایت خودکار مستثنی‌اند
    if (status && !url.includes("/auth/") && !url.includes("/backtest/reset")) {
      handleAuthFailure(status, err.response?.data?.detail);
    }

    if (status !== 404 && !url.includes("/analyze")) {
      console.warn(`[API Error] ${url || "Unknown URL"} - ${err.message}`);
    }
    return Promise.reject(err);
  }
);

export default api;
