// frontend/src/lib/api.ts
import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000",
  timeout: 120000, // 🔴 افزایش تایم‌اوت به ۲ دقیقه برای تحلیل‌های سنگین
});

// اینترسپتور برای مدیریت خطاها
api.interceptors.response.use(
  (response) => response,
  (err) => {
    if (
      err.response?.status !== 404 &&
      !err.config?.url?.includes("/analyze")
    ) {
      console.warn(`[API Error] ${err.config?.url || "Unknown URL"} - ${err.message}`);
    }
    return Promise.reject(err);
  }
);

export default api;