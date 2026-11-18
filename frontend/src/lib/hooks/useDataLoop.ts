"use client";

import { useEffect, useRef } from "react";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import type { AnalyzeResponse } from "@/lib/types";

const POLL_BY_TF: Record<string, number> = {
  "۱ دقیقه": 10_000, "۵ دقیقه": 15_000, "۱۵ دقیقه": 20_000,
  "۳۰ دقیقه": 30_000, "۱ ساعت": 45_000, "روزانه": 60_000,
};

export function useDataLoop() {
  const { ticker, tickerName, source, timeframe, marketType, riskProfile, strategy, setTfData } = useAppStore();
  const fetchingRef = useRef(false);

  useEffect(() => {
    if (!ticker || !sourceSupportsPair(source, ticker)) return;

    let cancelled = false;

    const fetchStream = async () => {
      if (cancelled || fetchingRef.current) return;
      fetchingRef.current = true;

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const response = await fetch(`${apiUrl}/analyze/multi-stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ticker, source, timeframe,
            market_type: marketType, risk_profile: riskProfile,
            strategy, ticker_name: tickerName,
          }),
        });

        if (!response.body) throw new Error("No stream body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done || cancelled) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.slice(6);
              if (dataStr === "[DONE]") break;
              try {
                const parsed = JSON.parse(dataStr);
                for (const [tf, data] of Object.entries(parsed)) {
                  setTfData(tf, data as AnalyzeResponse);
                }
              } catch {}
            }
          }
        }
      } catch (err) {
        console.warn("[useDataLoop] stream failed:", err);
      } finally {
        fetchingRef.current = false;
      }
    };

    fetchStream();
    const interval = POLL_BY_TF[timeframe] || 20_000;
    const timerId = setInterval(fetchStream, interval);

    const handleVisibility = () => {
      if (document.visibilityState === "visible" && !cancelled) fetchStream();
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      cancelled = true;
      clearInterval(timerId);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [ticker, tickerName, source, timeframe, marketType, riskProfile, strategy, setTfData]);
}