"use client";

/**
 * lib/hooks/useAnalysisCapability.ts
 * تشخیص توانایی تحلیل برای صرافی انتخابی
 * ============================================================
 * ⚠️ اصلاح مهم (نسخه ۱.۷):
 *
 * پیش‌تر برای آبان‌تتر ``canAnalyze = false`` می‌گذاشتم و
 * TFTable/DeepAnalysis/Checklist/FearGreed/Scanner را **مخفی**
 * می‌کردم. این اشتباه بود و جدول تحلیل را خالی نشان می‌داد.
 *
 * **واقعیت:** آبان‌تتر کندل ندارد، ولی زنجیره‌ی fallback خودکار
 * از نوبیتکس/بیت‌پین/والکس کندل می‌گیرد و تحلیل **انجام
 * می‌شود**. اختلاف قیمت BTC-IRT بین آبانتتر و نوبیتکس فقط
 * ۰.۲۳٪ است (تأیید تجربی) — یک بازار با اسپرد، نه دو بازار.
 *
 * پس تحلیل همیشه کار می‌کند و شفافیت از طریق بج منبع
 * (``source_used``) در SignalCard می‌آید — نه با خالی گذاشتن
 * جدول.
 *
 * ⚠️ این هوک هیچ درخواست شبکه‌ای نمی‌زند — همه‌چیز از
 *    متادیتای محلی (`lib/sources.ts`) می‌آید.
 */

import { useMemo } from "react";
import { useAppStore } from "@/store/useAppStore";
import { SOURCE_BY_KEY } from "@/lib/sources";
import type { Source } from "@/lib/types";

export interface AnalysisCapability {
  /** آیا این صرافی OHLCV خودش را دارد؟ */
  hasOhlcv: boolean;
  /** آیا می‌توان تحلیل گرفت؟ (با fallback) */
  canAnalyze: boolean;
  /** آیا کندل از صرافی دیگری می‌آید؟ (شفافیت) */
  usesFallbackOhlcv: boolean;
  /** 🔜 صرافی هنوز پیاده‌سازی نشده */
  planned: boolean;
  /** پیام فارسی برای نمایش */
  message: string;
  /** پیشنهاد عملی به کاربر */
  suggestion: string;
}

export function useAnalysisCapability(
  sourceOverride?: string
): AnalysisCapability {
  const storeSource = useAppStore((s) => s.source);
  const source = (sourceOverride ?? storeSource) as Source;

  return useMemo<AnalysisCapability>(() => {
    const meta = SOURCE_BY_KEY[source];

    // ─── صرافی ناشناخته: محافظه‌کارانه اجازه بده ───
    if (!meta) {
      return {
        hasOhlcv: true,
        canAnalyze: true,
        usesFallbackOhlcv: false,
        planned: false,
        message: "",
        suggestion: "",
      };
    }

    // ─── 🔜 صرافی برنامه‌ریزی‌شده ───
    if (meta.planned) {
      return {
        hasOhlcv: false,
        canAnalyze: false,
        usesFallbackOhlcv: false,
        planned: true,
        message: `${meta.label} هنوز پشتیبانی نمی‌شود`,
        suggestion: "این صرافی در فاز بعدی اضافه می‌شود",
      };
    }

    // ─── ✅ صرافی فعال — تحلیل همیشه کار می‌کند ───
    return {
      hasOhlcv: meta.hasOhlcv,
      canAnalyze: true,
      usesFallbackOhlcv: !meta.hasOhlcv,
      planned: false,
      message: meta.hasOhlcv ? "" : `${meta.label} کندل منتشر نمی‌کند`,
      suggestion: meta.hasOhlcv
        ? ""
        : "تحلیل با کندل صرافی دیگر انجام می‌شود؛ قیمت از خود " +
          meta.label,
    };
  }, [source]);
}

