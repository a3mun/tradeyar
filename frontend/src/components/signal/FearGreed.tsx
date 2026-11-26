
"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import type { FearGreedResponse } from "@/lib/types";
import { Gauge } from "lucide-react";

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
    if (!ticker || !coherent) {
      setData(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    setLoading(true);
    setData(null);

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

  const value = data
    ? Math.max(0, Math.min(100, Number(data.value) || 0))
    : 0;

  const cssColor =
    value <= 20
      ? "#ef4444"
      : value <= 40
        ? "#f97316"
        : value <= 60
          ? "#eab308"
          : value <= 80
            ? "#84cc16"
            : "#22c55e";

  const hint = fearGreedHint(value);

  return (
    <Card className="box-border flex h-[160px] max-h-[160px] min-h-[160px] min-w-0 w-full flex-col overflow-hidden border-white/10 bg-[#051118] shadow-xl">
      {/* عنوان و بج دسکتاپ */}
      <CardHeader className="shrink-0 px-3 pb-0 pt-2">
        <div className="flex min-w-0 items-center justify-between gap-1.5">
          <CardTitle className="flex min-w-0 items-center gap-1.5 whitespace-nowrap text-sm text-gray-300">
            <Gauge className="h-3.5 w-3.5 shrink-0 text-[#d6ad60]" />
            ترس و طمع
          </CardTitle>

          {data && !loading && (
            <span
              className="hidden shrink-0 rounded-sm border border-white/10 bg-white/5 px-2 py-1 text-[9px] font-medium leading-none sm:inline-flex"
              style={{ color: cssColor }}
            >
              {hint.text}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-2 pb-2 pt-3 sm:px-3">
        {loading ? (
          <div className="flex min-h-0 flex-1 flex-col justify-center gap-3">
            <Skeleton className="h-8 w-full bg-white/5" />
            <Skeleton className="h-2 w-full bg-white/5" />
            <Skeleton className="h-5 w-full bg-white/5" />
          </div>
        ) : !data ? (
          <div className="flex min-h-0 flex-1 items-center justify-center">
            <p className="text-center text-[10px] text-gray-500">
              در دسترس نیست
            </p>
          </div>
        ) : (
          <>
            {/* شاخص */}
            <div className="flex min-w-0 shrink-0 items-center gap-2 sm:gap-3">
              <span
                className="num shrink-0 text-xl font-bold leading-none sm:text-2xl"
                style={{ color: cssColor }}
              >
                {value.toFixed(0)}
              </span>

              <div className="relative h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
                <div
                  className="absolute inset-y-0 right-0 rounded-full transition-all duration-500"
                  style={{
                    width: `${value}%`,
                    backgroundColor: cssColor,
                  }}
                />
              </div>
            </div>

            {/* راهنمای شاخص */}
            <div className="mt-4 flex min-w-0 justify-between gap-1 text-[9px] text-gray-500">
              <span>ترس</span>
              <span>خنثی</span>
              <span>طمع</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}