"use client";

import { useEffect, useState } from "react";
import { Activity, TrendingUp, TrendingDown, Info, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import { formatNumber } from "@/lib/display";

interface OrderBookSummary {
  ok: boolean;
  ticker: string;
  source: string;
  imbalance: number;
  spread_pct: number;
  pressure_fa: string;
  has_bid_wall: boolean;
  has_ask_wall: boolean;
  wall?: { side: string; price: number; quantity: number; ratio: number } | null;
  execution_cost?: {
    fee_pct: number;
    spread_cost_pct: number;
    slippage_pct: number;
    total_pct: number;
  };
}

const OB_SOURCES = new Set(["nobitex", "bitpin", "wallex", "tabdeal"]);

export function OrderBookPanel() {
  const { ticker, source } = useAppStore();
  const [data, setData] = useState<OrderBookSummary | null>(null);
  const [loading, setLoading] = useState(false);

  const supported = OB_SOURCES.has(source) && sourceSupportsPair(source, ticker);

  useEffect(() => {
    if (!ticker || !supported) {
      let cancelled = false;
      queueMicrotask(() => {
        if (cancelled) return;
        setData(null);
        setLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }

    let cancelled = false;

    const load = () => {
      if (document.hidden) return;
      api
        .get<OrderBookSummary>(
          `/orderbook/${encodeURIComponent(ticker)}/summary`,
          { params: { source } }
        )
        .then((res) => {
          if (!cancelled) setData(res.data);
        })
        .catch(() => {
          if (!cancelled) setData(null);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    };

    queueMicrotask(() => {
      if (!cancelled) setLoading(true);
    });
    load();

    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [ticker, source, supported]);

  if (!supported) return null;

  // ─── بدون داده ───
  if (!data) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Layers className="h-4 w-4" />
            عمق بازار
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-2 text-center text-[10px] text-muted-foreground">
            {loading
              ? "عمق بازار در حال دریافت است…"
              : "این صرافی عمق بازار این نماد را منتشر نمی‌کند"}
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

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Layers className="h-4 w-4" />
            عمق بازار
          </CardTitle>
          <span
            className={`flex items-center gap-0.5 rounded-full border px-2 py-0.5 text-[9px] font-bold ${
              isBuy
                ? "border-green-500/30 bg-green-500/10 text-green-500"
                : isSell
                  ? "border-red-500/30 bg-red-500/10 text-red-500"
                  : "border-border bg-muted/30 text-muted-foreground"
            }`}
          >
            {isBuy ? (
              <TrendingUp className="h-2.5 w-2.5" />
            ) : isSell ? (
              <TrendingDown className="h-2.5 w-2.5" />
            ) : (
              <Activity className="h-2.5 w-2.5" />
            )}
            {data.pressure_fa}
          </span>
        </div>
        <p className="mt-1 text-[9px] text-muted-foreground">
          imbalance {(imb * 100).toFixed(0)}% · اسپرد {data.spread_pct.toFixed(3)}%
        </p>
      </CardHeader>

      <CardContent className="space-y-2.5">
        {/* نوار imbalance */}
        <div>
          <div className="mb-1 flex items-center justify-between text-[9px]">
            <span className="text-green-500">خرید {imbPct}%</span>
            <span className="text-muted-foreground">تعادل ۵۰%</span>
            <span className="text-red-500">فروش {100 - imbPct}%</span>
          </div>
          <div className="relative h-2.5 overflow-hidden rounded-full bg-red-500/30">
            <div
              className="absolute inset-y-0 right-0 rounded-full bg-green-500 transition-all duration-500"
              style={{ width: `${imbPct}%` }}
            />
            <div className="absolute inset-y-0 left-1/2 w-px bg-foreground/40" />
          </div>
        </div>

        {/* اسپرد + نقدینگی */}
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-md bg-muted/30 p-2 text-center">
            <p className="text-[9px] text-muted-foreground">اسپرد</p>
            <p className="num text-[11px] font-bold">
              {data.spread_pct.toFixed(3)}%
            </p>
          </div>
          <div className="rounded-md bg-muted/30 p-2 text-center">
            <p className="text-[9px] text-muted-foreground">نقدینگی</p>
            <p className="text-[11px] font-bold">
              {data.spread_pct < 0.1
                ? "عالی"
                : data.spread_pct < 0.3
                  ? "خوب"
                  : data.spread_pct < 0.6
                    ? "متوسط"
                    : "ضعیف"}
            </p>
          </div>
        </div>

        {/* دیوار سفارش */}
        {data.wall && (
          <div
            className={`rounded-md border p-2 text-[10px] ${
              data.wall.side === "bid"
                ? "border-green-500/20 bg-green-500/5 text-green-400"
                : "border-red-500/20 bg-red-500/5 text-red-400"
            }`}
          >
            🧱 دیوار سفارش {data.wall.side === "bid" ? "خرید" : "فروش"} در{" "}
            <span className="num">{formatNumber(data.wall.price)}</span>
            <span className="num mr-1 text-muted-foreground">
              ({data.wall.ratio.toFixed(1)}x میانگین)
            </span>
          </div>
        )}

        {/* هزینه‌ی واقعی */}
        {cost && (
          <div className="rounded-md border border-border/60 bg-muted/20 p-2">
            <p className="mb-1 text-[9px] font-medium">
              💸 هزینه‌ی واقعی معامله
            </p>
            <div className="grid grid-cols-3 gap-1 text-center text-[9px]">
              <div>
                <p className="text-muted-foreground">کارمزد</p>
                <p className="num font-bold">{cost.fee_pct.toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-muted-foreground">اسپرد</p>
                <p className="num font-bold">
                  {cost.spread_cost_pct.toFixed(2)}%
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">اسلیپیج</p>
                <p className="num font-bold">{cost.slippage_pct.toFixed(2)}%</p>
              </div>
            </div>
            <p className="num mt-1.5 text-center text-[11px] font-bold text-orange-400">
              مجموع {cost.total_pct.toFixed(2)}%
            </p>
          </div>
        )}

        {/* هشدار */}
        <p className="flex items-start gap-1.5 rounded-md bg-muted/20 p-2 text-[9px] leading-relaxed text-muted-foreground">
          <Info className="mt-0.5 h-2.5 w-2.5 shrink-0" />
          <span>
            عمق بازار <b>لحظه‌ای</b> است و بین صرافی‌ها فرق می‌کند (گاهی
            متناقض). فقط <b>تأییدکننده</b> است، نه توصیه‌ی معامله.
          </span>
        </p>
      </CardContent>
    </Card>
  );
}