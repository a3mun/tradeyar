"use client";

/**
 * useSignalData — منبع حقیقت برای تحلیل نماد
 * ============================================================
 * نسخه ۲.۰ · فاز ۷
 * ⚠️ این فایل باید با پسوند .tsx باشد (به‌خاطر JSX در Provider)
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { useAnalysisCapability } from "@/lib/hooks/useAnalysisCapability";
import { sourceSupportsPair } from "@/lib/sources";
import type { AnalyzeResponse } from "@/lib/types";

interface SignalDataState {
  data: AnalyzeResponse | null;
  loading: boolean;
  error: string | null;
}

const SignalDataContext = createContext<SignalDataState>({
  data: null,
  loading: false,
  error: null,
});

export function SignalDataProvider({ children }: { children: ReactNode }) {
  const { ticker, tickerName, source, timeframe, marketType, riskProfile } =
    useAppStore();
  const capability = useAnalysisCapability(source);
  const { signal: wsSignal } = useWebSocket();

  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const coherent = sourceSupportsPair(source, ticker);
  const currentKeyRef = useRef<string>("");

  // ═══ ۱. بار اول: POST /analyze ═══
  useEffect(() => {
    const key = `${ticker}|${source}|${timeframe}|${marketType}|${riskProfile}`;
    currentKeyRef.current = key;

    if (!ticker || capability.planned || !coherent) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const res = await api.post<AnalyzeResponse>("/analyze", {
          ticker,
          source,
          timeframe,
          market_type: marketType,
          risk_profile: riskProfile,
          ticker_name: tickerName,
        });
        if (cancelled || currentKeyRef.current !== key) return;
        setData(res.data);
      } catch {
        if (cancelled || currentKeyRef.current !== key) return;
        setData(null);
        setError("دریافت تحلیل ناموفق بود");
      } finally {
        if (!cancelled && currentKeyRef.current === key) {
          setLoading(false);
        }
      }
    })();

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

  // ═══ ۲. WS signal → جایگزینی data ═══
  useEffect(() => {
    if (!wsSignal) return;
    const sig = wsSignal as { ticker?: string };
    if (sig.ticker && sig.ticker !== ticker) return;
    setData(wsSignal as unknown as AnalyzeResponse);
    setLoading(false);
    setError(null);
  }, [wsSignal, ticker]);

  return (
    <SignalDataContext.Provider value={{ data, loading, error }}>
      {children}
    </SignalDataContext.Provider>
  );
}

// ═══ Hook مصرف‌کننده ═══
export function useSignalData(): SignalDataState {
  return useContext(SignalDataContext);
}