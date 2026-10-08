"use client";

/**
 * FearGreed — شاخص ترس و طمع (نسخه ۱.۰ — اصلی)
 * ============================================================
 * • میله‌ی خاکستری که با عدد شاخص پر می‌شه
 * • توضیح یک‌خطی
 */

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import type { FearGreedResponse } from "@/lib/types";

function fearGreedHint(value: number): { text: string; icon: string } {
  if (value <= 20) return { text: "ترس شدید — احتمال کف", icon: "😱" };
  if (value <= 40) return { text: "ترس — صبر کن برای تأیید", icon: "😰" };
  if (value <= 60) return { text: "خنثی — بازار بی‌جهت", icon: "😐" };
  if (value <= 80) return { text: "طمع — مراقب اشباع", icon: "🤑" };
  return { text: "طمع شدید — احتمال سقف", icon: "🚀" };
}

export function FearGreed() {
  const { ticker, source } = useAppStore();
  const [data, setData] = useState<FearGreedResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const coherent = sourceSupportsPair(source, ticker);

  useEffect(() => {
    if (!ticker || !coherent) {
      setData(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api
      .get("/analyze/fear-greed", { params: { ticker, source } })
      .then((res) => {
        if (!cancelled) setData(res.data);
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
  }, [ticker, source, coherent]);

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="pb-3">
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const cssColor = (() => {
    if (data.value <= 20) return "#dc2626";
    if (data.value <= 40) return "#ea580c";
    if (data.value <= 60) return "#ca8a04";
    if (data.value <= 80) return "#65a30d";
    return "#16a34a";
  })();

  const percentage = Math.max(0, Math.min(100, data.value));
  const hint = fearGreedHint(data.value);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          {hint.icon} ترس و طمع
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pb-3">
        {/* ═══ عدد + نوار خاکستری ═══ */}
        <div className="flex items-center gap-3">
          <span
            className="num shrink-0 text-2xl font-bold leading-none"
            style={{ color: cssColor }}
          >
            {data.value.toFixed(0)}
          </span>
          <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
            {/* پر شدن از راست با رنگ شاخص */}
            <div
              className="absolute inset-y-0 right-0 rounded-full transition-all duration-500"
              style={{
                width: `${percentage}%`,
                background: `linear-gradient(to left, ${cssColor}, ${cssColor}dd)`,
              }}
            />
          </div>
        </div>

        {/* ═══ برچسب‌ها ═══ */}
        <div className="flex justify-between text-[8px] text-muted-foreground">
          <span>😱 ترس</span>
          <span>😐 خنثی</span>
          <span>🚀 طمع</span>
        </div>

        {/* ═══ تحلیل یک‌خطی ═══ */}
        <div
          className="rounded-md border px-2 py-1 text-center text-[10px] font-bold"
          style={{
            borderColor: `${cssColor}33`,
            backgroundColor: `${cssColor}0a`,
            color: cssColor,
          }}
        >
          {hint.text}
        </div>
      </CardContent>
    </Card>
  );
}