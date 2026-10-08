"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { api } from "@/lib/api";

const OB_SOURCES = new Set(["nobitex", "bitpin", "wallex", "tabdeal"]);

interface OBData {
  imbalance: number;
  spread_pct: number;
  pressure_fa: string;
}

export function OrderBookPressure() {
  const { ticker, source } = useAppStore();
  const { orderbook: wsData } = useWebSocket();
  const [data, setData] = useState<OBData | null>(null);

  const supported =
    OB_SOURCES.has(source) && sourceSupportsPair(source, ticker);

  useEffect(() => {
    if (!supported) {
      setData(null);
      return;
    }
    let cancelled = false;
    api
      .get("/orderbook", { params: { ticker, source, depth: 20 } })
      .then((res) => {
        if (cancelled) return;
        if (res.data?.ok && res.data?.imbalance != null) {
          setData(res.data);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [ticker, source, supported]);

  useEffect(() => {
    if (wsData) setData(wsData as OBData);
  }, [wsData]);

  if (!supported) return null;

  if (!data) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">⚖️ فشار خرید و فروش</CardTitle>
        </CardHeader>
        <CardContent className="pb-3">
          <p className="text-center text-[10px] text-muted-foreground">
            در حال دریافت…
          </p>
        </CardContent>
      </Card>
    );
  }

  const imb = data.imbalance;
  const imbPct = Math.round(imb * 100);
  const isBuy = imb > 0.55;
  const isSell = imb < 0.45;

  const cssColor = isBuy ? "#22c55e" : isSell ? "#ef4444" : "#94a3b8";
  const label = isBuy ? "فشار خرید" : isSell ? "فشار فروش" : "تعادل بازار";
  const icon = isBuy ? "🟢" : isSell ? "🔴" : "⚪";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          ⚖️ فشار خرید و فروش
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pb-3">
        <div className="flex items-center gap-3">
          <span
            className="num shrink-0 text-2xl font-bold leading-none"
            style={{ color: cssColor }}
          >
            {imbPct}
          </span>
          <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="absolute inset-y-0 right-0 rounded-full transition-all duration-500"
              style={{
                width: `${imbPct}%`,
                background: `linear-gradient(to left, ${cssColor}, ${cssColor}dd)`,
              }}
            />
          </div>
        </div>

        <div className="flex justify-between text-[8px] text-muted-foreground">
          <span>🔴 فروش</span>
          <span>⚪ تعادل</span>
          <span>🟢 خرید</span>
        </div>

        <div
          className="rounded-md border px-2 py-1 text-center text-[10px] font-bold"
          style={{
            borderColor: `${cssColor}33`,
            backgroundColor: `${cssColor}0a`,
            color: cssColor,
          }}
        >
          {icon} {label}
        </div>
      </CardContent>
    </Card>
  );
} 