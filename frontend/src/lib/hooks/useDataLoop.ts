"use client";

import { useEffect, useRef } from "react";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import type { AnalyzeResponse } from "@/lib/types";
import { getToken } from "@/lib/auth";
import { handleAuthFailure, isAccessBlocked } from "@/lib/api";

const POLL_BY_TF: Record<string, number> = {
  "۱ دقیقه": 10_000, "۵ دقیقه": 15_000, "۱۵ دقیقه": 20_000,
  "۳۰ دقیقه": 30_000, "۱ ساعت": 45_000, "روزانه": 60_000,
};

export function useDataLoop() {
  const { ticker, tickerName, source, timeframe, marketType, riskProfile, strategy, setTfData } = useAppStore();
  const fetchingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!ticker || !sourceSupportsPair(source, ticker)) return;

    let cancelled = false;

    const fetchStream = async () => {
      // 🔒 بدون ورود، یا وقتی اشتراک تمام شده، درخواست نفرست
      if (!getToken() || isAccessBlocked()) return;
      // اگر fetch قبلی باز است، لغو کن تا درخواست جدید پاس شود
      if (fetchingRef.current) {
        abortRef.current?.abort();
      }
      if (cancelled) return;

      const controller = new AbortController();
      abortRef.current = controller;
      fetchingRef.current = true;

      // 🔴 timeout سخت — برای tsetmc کمی کوتاه‌تر
      const timeoutMs = source === "tsetmc" ? 15_000 : 25_000;
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const token = getToken();
        const response = await fetch(`${apiUrl}/analyze/multi-stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          signal: controller.signal,
          body: JSON.stringify({
            ticker, source, timeframe,
            market_type: marketType, risk_profile: riskProfile,
            strategy, ticker_name: tickerName,
          }),
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            let detail: unknown;
            try {
              detail = (await response.clone().json())?.detail;
            } catch {
              /* پاسخ JSON نبود */
            }
            handleAuthFailure(response.status, detail);
          }
          throw new Error(`HTTP ${response.status}`);
        }
        if (!response.body) throw new Error("No stream body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done || cancelled) break;

          buffer += decoder.decode(value, { stream: true });
          // 🔴 پشتیبانی از \n\n و \r\n\r\n
          const lines = buffer.split(/\r?\n\r?\n/);
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("data: ")) {
              const dataStr = trimmed.slice(6).trim();
              if (dataStr === "[DONE]") {
                return; // خروج از کل تابع تا finally اجرا شود
              }
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
        const e = err as Error;
        if (e?.name === "AbortError") {
          console.debug("[useDataLoop] abort (timeout/cleanup)");
        } else if (e?.message?.includes("Failed to fetch")) {
          console.debug("[useDataLoop] network interrupted");
        } else {
          console.warn("[useDataLoop] stream failed:", err);
        }
      } finally {
        clearTimeout(timeoutId);
        // 🔴 همیشه قفل را آزاد کن
        fetchingRef.current = false;
        if (abortRef.current === controller) abortRef.current = null;
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
      abortRef.current?.abort();
      abortRef.current = null;
      fetchingRef.current = false;
    };
  }, [ticker, tickerName, source, timeframe, marketType, riskProfile, strategy, setTfData]);
}