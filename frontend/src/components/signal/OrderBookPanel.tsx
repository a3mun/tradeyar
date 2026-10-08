"use client";

/**
 * OrderBookPanel — عمق بازار (نسخه ۳.۰ — فشرده)
 * ============================================================
 * • فشرده‌سازی همه‌ی بخش‌ها
 * • ارتفاع ~۴۰٪ کمتر
 */

import { useEffect, useState } from "react";
import { Activity, TrendingUp, TrendingDown, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import { formatNumber } from "@/lib/display";
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
  execution_cost?: {
    fee_pct: number;
    spread_cost_pct: number;
    slippage_pct: number;
    total_pct: number;
  } | null;
}

export function OrderBookPanel() {
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
    // 🔴 فاز ۸.۵ — استفاده از endpoint صحیح
    api
      .get(`/orderbook/${ticker}`, { params: { source, depth: 20 } })
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
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <Layers className="h-4 w-4" />
            عمق بازار
          </CardTitle>
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
  const isBuy = imb > 0.55;
  const isSell = imb < 0.45;
  const imbPct = Math.round(imb * 100);
  const cost = data.execution_cost;

  const cssColor = isBuy ? "#22c55e" : isSell ? "#ef4444" : "#94a3b8";
  const label = isBuy ? "فشار خرید" : isSell ? "فشار فروش" : "تعادل";

  // ─── نقدینگی ───
  const liq =
    data.spread_pct < 0.1
      ? "عالی"
      : data.spread_pct < 0.3
        ? "خوب"
        : data.spread_pct < 0.6
          ? "متوسط"
          : "ضعیف";

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <Layers className="h-4 w-4" />
            عمق بازار
          </CardTitle>
          <span
            className="flex items-center gap-0.5 rounded-full border px-2 py-0.5 text-[9px] font-bold"
            style={{
              borderColor: `${cssColor}50`,
              backgroundColor: `${cssColor}15`,
              color: cssColor,
            }}
          >
            {isBuy ? (
              <TrendingUp className="h-2.5 w-2.5" />
            ) : isSell ? (
              <TrendingDown className="h-2.5 w-2.5" />
            ) : (
              <Activity className="h-2.5 w-2.5" />
            )}
            {label}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-2 pb-3">
        {/* ═══ ردیف ۱: عدد + نوار imbalance ═══ */}
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
                background: cssColor,
                opacity: 0.7,
              }}
            />
            <div
              className="absolute top-1/2 h-4 w-2.5 -translate-y-1/2 rounded-sm border-2 border-white bg-slate-900 shadow-md transition-all duration-500"
              style={{ right: `calc(${imbPct}% - 5px)` }}
            />
          </div>
        </div>

        {/* ═══ ردیف ۲: برچسب‌ها ═══ */}
        <div className="flex justify-between text-[8px] text-muted-foreground">
          <span className="text-red-500">🔴 فروش</span>
          <span>تعادل ۵۰٪</span>
          <span className="text-green-500">🟢 خرید</span>
        </div>

        {/* ═══ ردیف ۳: اسپرد + نقدینگی + دیوار (فشرده) ═══ */}
        <div className="grid grid-cols-3 gap-1.5 text-[9px]">
          <div className="rounded border border-border/40 bg-muted/20 px-1.5 py-1 text-center">
            <p className="text-muted-foreground">اسپرد</p>
            <p className="num font-bold">{data.spread_pct.toFixed(3)}%</p>
          </div>
          <div className="rounded border border-border/40 bg-muted/20 px-1.5 py-1 text-center">
            <p className="text-muted-foreground">نقدینگی</p>
            <p className="font-bold">{liq}</p>
          </div>
          <div className="rounded border border-border/40 bg-muted/20 px-1.5 py-1 text-center">
            <p className="text-muted-foreground">دیوار</p>
            <p className="font-bold">
              {data.wall
                ? data.wall.side === "bid"
                  ? "🟢 خرید"
                  : "🔴 فروش"
                : "—"}
            </p>
          </div>
        </div>

        {/* ═══ ردیف ۴: هزینه‌ی معامله (فشرده) ═══ */}
        {cost && (
          <div className="flex items-center justify-between rounded border border-border/40 bg-muted/20 px-2 py-1 text-[9px]">
            <span className="text-muted-foreground">
              هزینه‌ی معامله
            </span>
            <span className="num font-bold text-orange-400">
              {cost.total_pct.toFixed(2)}%
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}