"use client";

import { useEffect, useState } from "react";
import { Activity, Layers } from "lucide-react";
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
  wall?: { side: "bid" | "ask"; price: number; ratio: number; } | null;
}

export function OrderBookPanel() {
  const { ticker, source } = useAppStore();
  const { orderbook: wsData } = useWebSocket();
  const [data, setData] = useState<OBData | null>(null);

  const supported = OB_SOURCES.has(source) && sourceSupportsPair(source, ticker);

  useEffect(() => {
    if (!supported) { setData(null); return; }
    let cancelled = false;
    api.get(`/orderbook/${ticker}`, { params: { source, depth: 20 } })
      .then((res) => {
        if (cancelled) return;
        if (res.data?.ok && res.data?.imbalance != null) setData(res.data);
      }).catch(() => {});
    return () => { cancelled = true; };
  }, [ticker, source, supported]);
    
  useEffect(() => { if (wsData) setData(wsData as OBData); }, [wsData]);

  if (!supported || !data) {
    return (
      <Card className="h-[160px] flex flex-col border-white/10 bg-[#051118] shadow-xl">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5 text-sm text-gray-300">
            <Layers className="h-4 w-4 text-[#d6ad60]" />
            عمق بازار
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center pb-3">
          <p className="text-center text-[10px] text-gray-500">
            {!supported ? "داده‌ای برای این صرافی موجود نیست" : "در حال دریافت..."}
          </p>
        </CardContent>
      </Card>
    );
  }

  const imb = data.imbalance;
  const isBuy = imb > 0.55;
  const isSell = imb < 0.45;
  const imbPct = Math.round(imb * 100);

  // 🔴 تک‌رنگ کردن نوارها: طلایی، خاکستری، یا رنگ تیره‌ی سبز/قرمز خیلی محو
  const cssColor = isBuy ? "#22c55e80" : isSell ? "#ef444480" : "#64748b";
  const label = isBuy ? "فشار خرید" : isSell ? "فشار فروش" : "تعادل";

  const liq = data.spread_pct < 0.1 ? "عالی" : data.spread_pct < 0.3 ? "خوب" : data.spread_pct < 0.6 ? "متوسط" : "ضعیف";

  return (
    <Card className="h-[160px] flex flex-col border-white/10 bg-[#051118] shadow-xl">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-1.5 text-sm text-gray-300">
            <Layers className="h-4 w-4 text-[#d6ad60]" />
            عمق بازار
          </CardTitle>
          <span className="flex items-center gap-1 rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[9px] font-medium text-gray-400">
            <Activity className="h-2.5 w-2.5" />
            {label}
          </span>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col justify-center space-y-3 pb-3">
        <div className="flex items-center gap-3">
          <span className="num shrink-0 text-2xl font-bold leading-none" style={{ color: isBuy ? "#4ade80" : isSell ? "#f87171" : "#94a3b8" }}>
            {imbPct}
          </span>
          <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
            <div className="absolute inset-y-0 right-0 rounded-full transition-all duration-500" style={{ width: `${imbPct}%`, background: cssColor }} />
          </div>
        </div>

        <div className="flex justify-between text-[8px] text-gray-500">
          <span>فروش</span>
          <span>تعادل</span>
          <span>خرید</span>
        </div>

        <div className="grid grid-cols-3 gap-1.5 text-[9px]">
          <div className="rounded border border-white/5 bg-white/5 px-1.5 py-1 text-center">
            <p className="text-gray-500 mb-0.5">اسپرد</p>
            <p className="num font-bold text-gray-300">{data.spread_pct.toFixed(3)}%</p>
          </div>
          <div className="rounded border border-white/5 bg-white/5 px-1.5 py-1 text-center">
            <p className="text-gray-500 mb-0.5">نقدینگی</p>
            <p className="font-bold text-gray-300">{liq}</p>
          </div>
          <div className="rounded border border-white/5 bg-white/5 px-1.5 py-1 text-center">
            <p className="text-gray-500 mb-0.5">دیوار</p>
            <p className="font-bold text-gray-300">
              {data.wall ? (data.wall.side === "bid" ? "خرید" : "فروش") : "—"}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}