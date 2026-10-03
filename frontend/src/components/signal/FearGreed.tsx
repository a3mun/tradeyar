"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { fearGreedColor } from "@/lib/display";
import type { FearGreedResponse } from "@/lib/types";

export function FearGreed() {
  const { ticker, source } = useAppStore();
  const [data, setData] = useState<FearGreedResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) return;

    setLoading(true);
    api
      .get("/analyze/fear-greed", {
        params: { ticker, source },
      })
      .then((res) => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [ticker, source]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const color = fearGreedColor(data.value);
  const percentage = Math.max(0, Math.min(100, data.value));

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span>😱 شاخص ترس و طمع</span>
          <span className="text-2xl">{data.icon}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* ═══ مقدار ═══ */}
        <div className="flex items-baseline justify-between">
          <div>
            <p className="num text-3xl font-bold" style={{ color }}>
              {data.value.toFixed(0)}
            </p>
            <p className="text-xs text-muted-foreground">{data.label}</p>
          </div>
          <p className="text-[10px] text-muted-foreground">۰ ← ۱۰۰</p>
        </div>

        {/* ═══ نوار رنگی ═══ */}
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 right-0 rounded-full transition-all duration-500"
            style={{
              width: `${percentage}%`,
              background: `linear-gradient(to left, ${color}, ${color}dd)`,
            }}
          />
        </div>

        {/* ═══ برچسب‌ها ═══ */}
        <div className="flex justify-between text-[9px] text-muted-foreground">
          <span>🚀 طمع شدید</span>
          <span>😐 خنثی</span>
          <span>😱 ترس شدید</span>
        </div>
      </CardContent>
    </Card>
  );
}