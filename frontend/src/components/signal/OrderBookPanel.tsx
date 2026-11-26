
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
  wall?: {
    side: "bid" | "ask";
    price: number;
    ratio: number;
  } | null;
}

export function OrderBookPanel() {
  const { ticker, source } = useAppStore();
  const { orderbook: wsData } = useWebSocket();

  const [data, setData] = useState<OBData | null>(null);
  const [loading, setLoading] = useState(true);

  const supported =
    OB_SOURCES.has(source) && sourceSupportsPair(source, ticker);

  // دریافت اطلاعات API هنگام تغییر نماد یا صرافی
  useEffect(() => {
    let cancelled = false;

    setData(null);

    if (!supported) {
      setLoading(false);
      return;
    }

    setLoading(true);

    api
      .get(`/orderbook/${ticker}`, {
        params: { source, depth: 20 },
      })
      .then((res) => {
        if (cancelled) return;

        if (res.data?.ok && res.data?.imbalance != null) {
          setData(res.data);
        }
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ticker, source, supported]);

  // دریافت داده WebSocket فقط برای منبع پشتیبانی‌شده
  useEffect(() => {
    if (!supported || !wsData) return;

    const nextData = wsData as OBData;

    if (
      typeof nextData.imbalance !== "number" ||
      typeof nextData.spread_pct !== "number" ||
      !Number.isFinite(nextData.imbalance) ||
      !Number.isFinite(nextData.spread_pct)
    ) {
      return;
    }

    setData(nextData);
    setLoading(false);
  }, [wsData, supported]);

  // حالت بدون داده
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
          <p className="text-center text-[11px] text-gray-500">
            {!supported
              ? "داده‌ای برای این صرافی موجود نیست"
              : loading
                ? "در حال دریافت اطلاعات بازار..."
                : "اطلاعات عمق بازار در دسترس نیست"}
          </p>
        </CardContent>
      </Card>
    );
  }

  // محاسبات فشار خرید و فروش
  const imb = Math.max(0, Math.min(1, data.imbalance));
  const imbPct = Math.round(imb * 100);

  const isBuy = imb > 0.55;
  const isSell = imb < 0.45;

  const label = isBuy
    ? "فشار خرید"
    : isSell
      ? "فشار فروش"
      : "تعادل";

  const valueColor = isBuy
    ? "#4ade80"
    : isSell
      ? "#f87171"
      : "#cbd5e1";

  const barColor = isBuy
    ? "rgba(74, 222, 128, 0.65)"
    : isSell
      ? "rgba(248, 113, 113, 0.65)"
      : "rgba(148, 163, 184, 0.65)";

  const liq =
    data.spread_pct < 0.1
      ? "عالی"
      : data.spread_pct < 0.3
        ? "خوب"
        : data.spread_pct < 0.6
          ? "متوسط"
          : "ضعیف";

  const liqColor =
    liq === "عالی" || liq === "خوب"
      ? "text-emerald-400"
      : liq === "متوسط"
        ? "text-amber-300"
        : "text-rose-400";

  return (
    <Card className="h-[160px] flex flex-col border-white/10 bg-[#051118] shadow-xl">
      <CardHeader className="pb-0">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-1.5 text-sm text-gray-300">
            <Layers className="h-4 w-4 text-[#d6ad60]" />
            عمق بازار
          </CardTitle>

          <span className="flex items-center gap-1 rounded-md border border-white/[0.08] bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-gray-400">
            <Activity className="h-3 w-3" />
            {label}
          </span>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col justify-center space-y-3 pb-3">
        {/* فشار خرید و فروش */}
        <div className="flex items-center gap-3">
          <span
            className="num shrink-0 text-2xl font-bold leading-none tabular-nums"
            style={{ color: valueColor }}
          >
            {imbPct}%
          </span>

          <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
            <div
              className="absolute inset-y-0 right-0 rounded-full transition-all duration-500"
              style={{
                width: `${imbPct}%`,
                background: barColor,
              }}
            />
          </div>
        </div>

        {/* راهنمای نوار */}
        <div className="flex justify-between text-[10px] text-gray-500">
          <span>فروش</span>
          <span>تعادل</span>
          <span>خرید</span>
        </div>

        {/* اطلاعات تکمیلی */}
        <div className="grid grid-cols-3 gap-1.5 text-[9px] min-w-0 w-full">
          <div className="min-w-0 rounded-md border border-white/[0.06] bg-white/[0.035] px-1 py-1 text-center">
            <p className="mb-0.5 text-gray-500 truncate">اسپرد</p>
            <p className="num font-bold text-gray-200 tabular-nums truncate">
              {data.spread_pct.toFixed(3)}%
            </p>
          </div>

          <div className="min-w-0 rounded-md border border-white/[0.06] bg-white/[0.035] px-1 py-1 text-center">
            <p className="mb-0.5 text-gray-500 truncate">نقدینگی</p>
            <p className={`font-bold truncate ${liqColor}`}>{liq}</p>
          </div>

          <div className="min-w-0 rounded-md border border-white/[0.06] bg-white/[0.035] px-1 py-1 text-center">
            <p className="mb-0.5 text-gray-500 truncate">دیوار سفارش</p>
            <p className="font-bold text-gray-200 truncate">
              {data.wall
                ? data.wall.side === "bid"
                  ? "خرید"
                  : "فروش"
                : "—"}
            </p>
          </div>
        </div>

      </CardContent>
    </Card>
  );
}
