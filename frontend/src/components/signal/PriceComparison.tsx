"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, ArrowDown, Crown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { formatNumber } from "@/lib/display";

const SOURCES = [
  { key: "nobitex", label: "نوبیتکس", icon: "🟣" },
  { key: "bitpin", label: "بیت‌پین", icon: "🟢" },
  { key: "wallex", label: "والکس", icon: "🔵" },
  { key: "abantether", label: "آبان‌تتر", icon: "🔷" },
];

interface QuoteRow {
  source: string;
  price: number | null;
  prevPrice: number | null;
}

export function PriceComparison() {
  const { ticker, timeframe } = useAppStore();
  const [rows, setRows] = useState<QuoteRow[]>([]);
  const [loading, setLoading] = useState(true);
  const prevRef = useRef<Record<string, number>>({});

  const fetchAll = () => {
    Promise.all(
      SOURCES.map((s) =>
        api
          .get("/analyze/quote", { params: { ticker, source: s.key } })
          .then((res) => ({ source: s.key, price: res.data.price as number | null }))
          .catch(() => ({ source: s.key, price: null }))
      )
    ).then((results) => {
      const newRows: QuoteRow[] = results.map((r) => ({
        source: r.source,
        price: r.price,
        prevPrice: prevRef.current[r.source] ?? r.price,
      }));
      results.forEach((r) => {
        if (r.price !== null) prevRef.current[r.source] = r.price;
      });
      setRows(newRows);
      setLoading(false);
    });
  };

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    prevRef.current = {};
    fetchAll();
    const id = setInterval(fetchAll, 10000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  const validPrices = rows.filter((r) => r.price).map((r) => r.price!);
  const minPrice = validPrices.length ? Math.min(...validPrices) : 0;
  const maxPrice = validPrices.length ? Math.max(...validPrices) : 0;
  const spread = minPrice > 0 ? ((maxPrice - minPrice) / minPrice) * 100 : 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs">💰 مقایسه قیمت</CardTitle>
        <p className="text-[9px] text-muted-foreground">
          {ticker} · {timeframe} · اختلاف کل: {spread.toFixed(2)}%
        </p>
      </CardHeader>
      <CardContent className="space-y-1.5 p-3">
        {loading
          ? SOURCES.map((s) => <Skeleton key={s.key} className="h-7 w-full" />)
          : rows.map((r) => {
              const src = SOURCES.find((s) => s.key === r.source);
              if (!src) return null;
              const up =
                r.price !== null && r.prevPrice !== null && r.price > r.prevPrice;
              const down =
                r.price !== null && r.prevPrice !== null && r.price < r.prevPrice;
              const isBest = r.price === minPrice && minPrice > 0;
              const diffPct =
                r.price && minPrice > 0 ? ((r.price - minPrice) / minPrice) * 100 : 0;

              return (
                <div
                  key={r.source}
                  className={`flex items-center justify-between gap-2 rounded-md px-2 py-1.5 ${
                    isBest
                      ? "bg-green-500/10 border border-green-500/30"
                      : "bg-muted/20"
                  }`}
                >
                  <span className="text-[10px] font-medium flex items-center gap-1">
                    {isBest && <Crown className="h-3 w-3 text-yellow-500" />}
                    {src.icon} {src.label}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`num text-[11px] font-bold ${
                        isBest
                          ? "text-green-500"
                          : up
                            ? "text-green-500"
                            : down
                              ? "text-red-500"
                              : "text-foreground"
                      }`}
                    >
                      {r.price ? formatNumber(r.price) : "—"}
                    </span>
                    {up && <ArrowUp className="h-2.5 w-2.5 text-green-500" />}
                    {down && <ArrowDown className="h-2.5 w-2.5 text-red-500" />}
                    {!isBest && r.price && diffPct > 0.01 && (
                      <span className="num text-[9px] text-muted-foreground">
                        +{diffPct.toFixed(2)}%
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
      </CardContent>
    </Card>
  );
}