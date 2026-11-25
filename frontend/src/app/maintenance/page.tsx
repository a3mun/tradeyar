
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Settings,
  RefreshCw,
  Clock,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function MaintenancePage() {
  const router = useRouter();

  const [checking, setChecking] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [connectionError, setConnectionError] = useState(false);

  const checkStatus = useCallback(async () => {
    if (checking) return;

    setChecking(true);

    try {
      const res = await fetch(
        `${API_URL}/admin/maintenance/public`,
        {
          cache: "no-store",
        }
      );

      if (!res.ok) {
        throw new Error("خطا در بررسی وضعیت");
      }

      const data = await res.json();

      setLastChecked(new Date());
      setConnectionError(false);

      if (!data.is_maintenance) {
        router.replace("/");
      }
    } catch {
      setConnectionError(true);
    } finally {
      setChecking(false);
    }
  }, [checking, router]);

  useEffect(() => {
    let active = true;

    const check = async () => {
      try {
        const res = await fetch(
          `${API_URL}/admin/maintenance/public`,
          { cache: "no-store" }
        );

        if (!res.ok) {
          throw new Error("خطا در بررسی وضعیت");
        }

        const data = await res.json();

        if (!active) return;

        setLastChecked(new Date());
        setConnectionError(false);

        if (!data.is_maintenance) {
          router.replace("/");
        }
      } catch {
        if (active) {
          setConnectionError(true);
        }
      }
    };

    check();

    const interval = setInterval(check, 10000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [router]);

  const handleRetry = () => {
    checkStatus();
  };

  return (
    <main
      dir="rtl"
      className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#030712] px-4 py-10 text-white"
    >
      {/* Background */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#d6ad60]/5 via-transparent to-transparent" />

      <div className="pointer-events-none absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#d6ad60]/5 blur-[100px]" />

      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-md rounded-3xl border border-[#d6ad60]/20 bg-[#051118]/95 p-7 text-center shadow-2xl backdrop-blur-xl sm:p-10"
      >
        {/* Icon */}
        <div className="mx-auto mb-7 flex h-20 w-20 items-center justify-center rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/10">
          <Settings
            className="h-10 w-10 animate-spin text-[#d6ad60]"
            style={{ animationDuration: "5s" }}
          />
        </div>

        {/* Title */}
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/10 px-3 py-1.5 text-[11px] font-medium text-[#d6ad60]">
          <Clock className="h-3.5 w-3.5" />
          عملیات نگهداری سیستم
        </div>

        <h1 className="font-display text-2xl font-extrabold sm:text-3xl">
          در حال به‌روزرسانی هستیم
        </h1>

        <p className="mt-5 text-justify text-sm leading-8 text-gray-400">
          در حال انجام عملیات فنی و بهبود زیرساخت‌های تریدمون هستیم تا
          بتوانیم خدمات بهتر و پایدارتری ارائه کنیم.
          از صبوری شما سپاسگزاریم. پس از پایان عملیات، دسترسی به سایت
          به‌صورت خودکار برقرار خواهد شد.
        </p>

        {/* Status */}
        <div className="mt-7 rounded-xl border border-white/5 bg-white/[0.03] p-4">
          <div className="flex items-center justify-center gap-2 text-xs text-gray-300">
            {checking ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-[#d6ad60]" />
                در حال بررسی وضعیت سایت...
              </>
            ) : connectionError ? (
              <>
                <AlertCircle className="h-4 w-4 text-amber-400" />
                ارتباط با سرور برقرار نشد
              </>
            ) : (
              <>
                <ShieldCheck className="h-4 w-4 text-[#d6ad60]" />
                وضعیت تعمیرات در حال بررسی است
              </>
            )}
          </div>

          {lastChecked && (
            <p className="mt-2 text-[10px] text-gray-500">
              آخرین بررسی:{" "}
              {lastChecked.toLocaleTimeString("fa-IR", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </p>
          )}
        </div>

        {/* Retry */}
        <button
          type="button"
          onClick={handleRetry}
          disabled={checking}
          className="mt-6 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-5 text-sm font-bold text-[#07111f] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${checking ? "animate-spin" : ""}`}
          />
          {checking ? "در حال بررسی..." : "بررسی مجدد وضعیت سایت"}
        </button>

        <div className="mt-7 border-t border-white/10 pt-5">
          <p className="text-sm font-bold text-[#d6ad60]">
            تریدمون
          </p>
          <p className="mt-1 text-[10px] text-gray-500">
            ابزارهای هوشمند برای تصمیم‌گیری آگاهانه‌تر در بازار
          </p>
        </div>
      </motion.div>
    </main>
  );
}
