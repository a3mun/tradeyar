"use client";

import { useEffect, useRef } from "react";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { sourceSupportsPair } from "@/lib/sources";
import type { AnalyzeResponse } from "@/lib/types";

// 🔴 فاز ۱۶.۵ — دوره‌ی آپدیت بر اساس تایم‌فریم
const POLL_BY_TF: Record<string, number> = {
  "۱ دقیقه": 10_000,   // اسکالپ: ۱۰ ثانیه
  "۵ دقیقه": 15_000,   // ۱۵ ثانیه
  "۱۵ دقیقه": 20_000,  // ۲۰ ثانیه
  "۳۰ دقیقه": 30_000,  // ۳۰ ثانیه
  "۱ ساعت": 45_000,    // ۴۵ ثانیه
  "روزانه": 60_000,    // ۱ دقیقه
};

export function useDataLoop() {
  const {
    ticker, tickerName, source, timeframe,
    marketType, riskProfile, strategy, setTfData,
  } = useAppStore();

  const fetchingRef = useRef(false);

  useEffect(() => {
    if (!ticker || !sourceSupportsPair(source, ticker)) return;

    let cancelled = false;

    const fetchMulti = async () => {
      if (cancelled || fetchingRef.current) return;
      fetchingRef.current = true;

      try {
        const res = await api.post<{ ok: boolean; timeframes: Record<string, AnalyzeResponse> }>("/analyze/multi", {
          ticker,
          source,
          timeframe: "۵ دقیقه",
          market_type: marketType,
          risk_profile: riskProfile,
          strategy,
          ticker_name: tickerName,
        });

        if (cancelled) return;

        const tfs = res.data.timeframes || {};
        for (const [tf, tfData] of Object.entries(tfs)) {
          if (tfData) setTfData(tf, tfData);
        }
      } catch {
        // silent
      } finally {
        fetchingRef.current = false;
      }
    };

    // اجرای فوری در بدو ورود یا تغییر تنظیمات
    fetchMulti();

    // تنظیم تایمر بر اساس تایم‌فریم
    const interval = POLL_BY_TF[timeframe] || 20_000;
    const timerId = setInterval(fetchMulti, interval);

    return () => {
      cancelled = true;
      clearInterval(timerId);
    };
  }, [ticker, tickerName, source, timeframe, marketType, riskProfile, strategy, setTfData]);
}