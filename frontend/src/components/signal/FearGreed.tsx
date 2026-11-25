"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import type { FearGreedResponse } from "@/lib/types";
import { Gauge  } from "lucide-react";


function fearGreedHint(value: number): { text: string } {
  if (value <= 20) return { text: "ترس شدید" };
  if (value <= 40) return { text: "ترس" };
  if (value <= 60) return { text: "خنثی" };
  if (value <= 80) return { text: "طمع" };
  return { text: "طمع شدید" };
}

export function FearGreed() {
  const { ticker, source } = useAppStore();
  const [data, setData] = useState<FearGreedResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const coherent = sourceSupportsPair(source, ticker);

  useEffect(() => {
    if (!ticker || !coherent) { setData(null); setLoading(false); return; }
    let cancelled = false;
    setLoading(true);
    api.get("/analyze/fear-greed", { params: { ticker, source } })
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch(() => { if (!cancelled) setData(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker, source, coherent]);

  if (loading) {
    return (
      <Card className="h-[160px] flex flex-col border-white/10 bg-[#051118] shadow-xl">
        <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-300">😐 ترس و طمع</CardTitle></CardHeader>
        <CardContent className="flex-1 flex flex-col justify-center space-y-2 pb-3">
          <Skeleton className="h-8 w-full bg-white/5" />
          <Skeleton className="h-1.5 w-full bg-white/5" />
          <Skeleton className="h-6 w-full bg-white/5" />
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className="h-[160px] flex flex-col border-white/10 bg-[#051118] shadow-xl">
        <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-300">😐 ترس و طمع</CardTitle></CardHeader>
        <CardContent className="flex-1 flex items-center justify-center pb-3">
          <p className="text-center text-[10px] text-gray-500">در دسترس نیست</p>
        </CardContent>
      </Card>
    );
  }

  // 🔴 رنگ‌ها خیلی ملایم و تک‌رنگ
  const cssColor = (() => {
    if (data.value <= 20) return "#ef4444";
    if (data.value <= 40) return "#f97316";
    if (data.value <= 60) return "#eab308";
    if (data.value <= 80) return "#84cc16";
    return "#22c55e";
  })();

  const percentage = Math.max(0, Math.min(100, data.value));
  const hint = fearGreedHint(data.value);

  return (
    <Card className="h-[160px] flex flex-col border-white/10 bg-[#051118] shadow-xl">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm text-gray-300">
          <Gauge  className="h-3.5 w-3.5 text-[#d6ad60]" />
          ترس و طمع
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-center space-y-3 pb-3">
        <div className="flex items-center gap-3">
          <span className="num shrink-0 text-2xl font-bold leading-none" style={{ color: cssColor }}>
            {data.value.toFixed(0)}
          </span>
          <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
            <div className="absolute inset-y-0 right-0 rounded-full transition-all duration-500" style={{ width: `${percentage}%`, background: cssColor }} />



          </div>
        </div>

        <div className="flex justify-between text-[8px] text-gray-500">
          <span>ترس</span>
          <span>خنثی</span>
          <span>طمع</span>
        </div>

        <div className="rounded-md border px-2 py-1.5 text-center text-[10px] font-medium" style={{ borderColor: `${cssColor}30`, backgroundColor: `${cssColor}10`, color: cssColor }}>
          {hint.text}
        </div>
      </CardContent>
    </Card>
  );
}