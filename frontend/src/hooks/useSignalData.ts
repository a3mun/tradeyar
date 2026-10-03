"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import type { AnalyzeResponse } from "@/lib/types";

export function useSignalData() {
  const { ticker, tickerName, source, timeframe, marketType, riskProfile } =
    useAppStore();
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) return;

    setLoading(true);
    api
      .post("/analyze", {
        ticker,
        source,
        timeframe,
        market_type: marketType,
        risk_profile: riskProfile,
        ticker_name: tickerName,
      })
      .then((res) => {
        setData(res.data);
      })
      .catch(() => {
        setData(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [ticker, tickerName, source, timeframe, marketType, riskProfile]);

  return { data, loading };
}