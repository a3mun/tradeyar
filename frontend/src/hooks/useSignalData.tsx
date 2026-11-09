"use client";

/**
 * useSignalData — منبع حقیقت برای تحلیل نماد
 * ============================================================
 * نسخه ۳.۰ · فاز ۱۴.۷.۴
 * 🔴 تغییرات:
 *   • حذف fetch مستقل (رفع تناقض با SignalCard)
 *   • از tfDataCache (useAppStore) می‌خونه — هم‌راستا با SignalCard
 *   • Zustand reactive (بدون polling)
 *   • بدون useWebSocket.signal (حذف شد)
 */

import {
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useAppStore } from "@/store/useAppStore";
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
  const timeframe = useAppStore((s) => s.timeframe);
  const getTfData = useAppStore((s) => s.getTfData);

  // 🔴 Zustand reactive — هر تغییر tfDataCache → re-render
  // (subscribe به tfDataCache، نه خودش)
  const tfDataCache = useAppStore((s) => s.tfDataCache);

  // محاسبه data از cache (reactive)
  const data = useMemo(() => {
    // استفاده از getTfData برای اعتبار TTL و key
    void tfDataCache; // ← trigger re-render
    return getTfData(timeframe);
  }, [timeframe, getTfData, tfDataCache]);

  const value = useMemo<SignalDataState>(
    () => ({
      data,
      loading: !data,
      error: null,
    }),
    [data]
  );

  return (
    <SignalDataContext.Provider value={value}>
      {children}
    </SignalDataContext.Provider>
  );
}

export function useSignalData(): SignalDataState {
  return useContext(SignalDataContext);
}