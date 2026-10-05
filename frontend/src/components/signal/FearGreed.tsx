"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { fearGreedColor } from "@/lib/display";
import { sourceSupportsPair } from "@/lib/sources";
import type { FearGreedResponse } from "@/lib/types";

// ═══ تحلیل متنی بر اساس مقدار ═══
function fearGreedHint(value: number): {
  text: string;
  advice: string;
  icon: string;
} {
  if (value <= 20) {
    return {
      text: "ترس شدید",
      advice: "احتمال کف — فرصت خرید بلندمدت",
      icon: "😱",
    };
  }
  if (value <= 40) {
    return {
      text: "ترس",
      advice: "احتمال ضعف — صبر کن برای تأیید",
      icon: "😰",
    };
  }
  if (value <= 60) {
    return {
      text: "خنثی",
      advice: "بازار بی‌جهت — صبر کن",
      icon: "😐",
    };
  }
  if (value <= 80) {
    return {
      text: "طمع",
      advice: "احتمال رشد — مراقب اشباع",
      icon: "🤑",
    };
  }
  return {
    text: "طمع شدید",
    advice: "احتمال سقف — فروش پله‌ای",
    icon: "🚀",
  };
}

export function FearGreed() {
  const { ticker, source } = useAppStore();
  const [data, setData] = useState<FearGreedResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const coherent = sourceSupportsPair(source, ticker);

  useEffect(() => {
    if (!ticker || !coherent) {
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
    queueMicrotask(() => {
      if (!cancelled) setLoading(true);
    });

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
        <CardHeader className="pb-3">
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
  const hint = fearGreedHint(data.value);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-sm">
          <span>😱 شاخص ترس و طمع</span>
          <span className="text-xl">{hint.icon}</span>
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
          <p className="num text-[10px] text-muted-foreground">0 ← 100</p>
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

        {/* ═══ تحلیل متنی (خط جدید) ═══ */}
        <div
          className="rounded-md border p-2"
          style={{
            borderColor: `${color}33`,
            backgroundColor: `${color}0a`,
          }}
        >
          <p className="text-[10px] font-bold" style={{ color }}>
            💡 {hint.text}
          </p>
          <p className="mt-0.5 text-[10px] leading-relaxed text-muted-foreground">
            {hint.advice}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}