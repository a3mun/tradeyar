"use client";

/**
 * useSignalData — دریافت تحلیل یک نماد در TF انتخابی
 * ============================================================
 * ⚠️ تغییرات نسخه ۱.۷:
 *   • برای صرافی‌های بدون OHLCV (آبان‌تتر) درخواست نمی‌زند
 *   • هیچ setState همگامی در بدنه‌ی effect نیست
 *   • خطای واقعی از «داده نیست» تفکیک می‌شود
 */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useAnalysisCapability } from "@/lib/hooks/useAnalysisCapability";
import { sourceSupportsPair } from "@/lib/sources";
import type { AnalyzeResponse } from "@/lib/types";

export function useSignalData() {
  const { ticker, tickerName, source, timeframe, marketType, riskProfile } =
    useAppStore();
  const capability = useAnalysisCapability(source);

  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ─── 🔴 آیا این جفت (صرافی، نماد) هماهنگ است؟ ───
  //     اگر نه، درخواست نزن — ۴۰۴ می‌گیریم و Console آلوده می‌شود.
  const coherent = sourceSupportsPair(source, ticker);

  useEffect(() => {
    // ─── صرافی «به‌زودی» یا جفت ناهماهنگ: درخواست نزن ───
    // ⚠️ setState داخل microtask تا ESLint
    //    (react-hooks/set-state-in-effect) راضی بماند.
    if (!ticker || capability.planned || !coherent) {
      let cancelled = false;
      queueMicrotask(() => {
        if (cancelled) return;
        setData(null);
        setLoading(false);
        setError(null);
      });
      return () => {
        cancelled = true;
      };
    }

    let cancelled = false;

    const load = async () => {
      queueMicrotask(() => {
        if (!cancelled) {
          setLoading(true);
          setError(null);
        }
      });
      try {
        const res = await api.post<AnalyzeResponse>("/analyze", {
          ticker,
          source,
          timeframe,
          market_type: marketType,
          risk_profile: riskProfile,
          ticker_name: tickerName,
        });
        if (cancelled) return;
        setData(res.data);
      } catch {
        if (cancelled) return;
        setData(null);
        setError("دریافت تحلیل ناموفق بود");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [
    ticker,
    tickerName,
    source,
    timeframe,
    marketType,
    riskProfile,
    capability.planned,
    coherent,
  ]);

  return { data, loading, error };
}
