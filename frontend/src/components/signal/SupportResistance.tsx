
"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSignalData } from "@/hooks/useSignalData";
import { formatNumber } from "@/lib/display";
import { TrendingUp } from "lucide-react";

export function SupportResistance() {
  const { data } = useSignalData();

  if (!data) {
    return (
      <Card className="box-border flex h-[160px] max-h-[160px] min-h-[160px] min-w-0 w-full flex-col overflow-hidden border-white/10 bg-[#051118] shadow-xl">
        <CardHeader className="shrink-0 px-3 pb-2 pt-3">
          <CardTitle className="flex items-center gap-1.5 text-sm text-gray-300">
            <TrendingUp className="h-3.5 w-3.5 shrink-0 text-[#d6ad60]" />
            حمایت و مقاومت
          </CardTitle>
        </CardHeader>

        <CardContent className="flex min-h-0 flex-1 items-center justify-center px-3">
          <p className="text-center text-[10px] text-gray-500">
            در حال دریافت...
          </p>
        </CardContent>
      </Card>
    );
  }

  const price = Number(data.price) || 0;
  const pivots = (data.pivots || {}) as Record<string, number>;

  let support = Number(data.support) || 0;
  let resistance = Number(data.resistance) || 0;

  if (support <= 0 || support >= price) {
    support =
      [pivots.s1, pivots.s2, pivots.s3]
        .map(Number)
        .filter((value) => value > 0 && value < price)
        .sort((a, b) => b - a)[0] || 0;
  }

  if (resistance <= 0 || resistance <= price) {
    resistance =
      [pivots.r1, pivots.r2, pivots.r3]
        .map(Number)
        .filter((value) => value > price)
        .sort((a, b) => a - b)[0] || 0;
  }

  const hasData =
    price > 0 &&
    support > 0 &&
    resistance > support;

  const range = hasData ? resistance - support : 0;

  const position = hasData
    ? ((price - support) / range) * 100
    : 0;

  const progress = Math.max(0, Math.min(100, position));

  let analysis = "بین حمایت و مقاومت";
  let analysisColor = "#94a3b8";

  if (progress <= 15) {
    analysis = "نزدیک حمایت";
    analysisColor = "#22c55e";
  } else if (progress <= 35) {
    analysis = "محدوده حمایتی";
    analysisColor = "#4ade80";
  } else if (progress <= 65) {
    analysis = "بین حمایت و مقاومت";
    analysisColor = "#94a3b8";
  } else if (progress <= 85) {
    analysis = "محدوده مقاومتی";
    analysisColor = "#fb923c";
  } else {
    analysis = "نزدیک مقاومت";
    analysisColor = "#ef4444";
  }

  return (
    <Card className="box-border flex h-[160px] max-h-[160px] min-h-[160px] min-w-0 w-full flex-col overflow-hidden border-white/10 bg-[#051118] shadow-xl">

      <CardHeader className="shrink-0 px-3 pb-0 pt-2">
        <div className="flex min-w-0 flex-col items-start gap-1 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="flex min-w-0 items-center gap-1.5 whitespace-nowrap text-sm text-gray-300">
            <TrendingUp className="h-3.5 w-3.5 shrink-0 text-[#d6ad60]" />
            حمایت و مقاومت
          </CardTitle>

        {hasData && (
          <span
            className="hidden sm:inline-flex shrink-0 rounded-sm border border-white/10 bg-white/5 px-2 py-1 text-[9px] font-medium leading-none"
            style={{ color: analysisColor }}
          >
            {analysis}
          </span>
        )}
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-2 pb-2 pt-3 sm:px-3">
        {hasData ? (
          <>
            {/* موقعیت قیمت */}
            <div className="flex min-w-0 shrink-0 items-center gap-2 sm:gap-3">
              <span className="num shrink-0 text-xl font-bold leading-none text-foreground sm:text-2xl">
                {Math.round(progress)}
                <span className="text-xs text-gray-500">٪</span>
              </span>

              <div className="relative h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-white/10">
                <div
                  className="absolute inset-y-0 right-0 rounded-full transition-all duration-500"
                  style={{
                    width: `${progress}%`,
                    backgroundColor: analysisColor,
                  }}
                />
              </div>
            </div>

            {/* قیمت‌ها */}
            <div className="mt-4 grid min-w-0 shrink-0 grid-cols-3 gap-0 text-center">
              <div className="flex min-w-0 flex-col items-center gap-1 px-0.5">
                <span className="text-[9px] text-gray-500">
                  حمایت
                </span>
                <span
                  dir="ltr"
                  title={formatNumber(support)}
                  className="num block w-full min-w-0 truncate text-[10px] font-semibold text-[#86a99a] sm:text-xs"
                >
                  {formatNumber(support)}
                </span>
              </div>

              <div className="flex min-w-0 flex-col items-center gap-1 border-x border-white/5 px-0.5">
                <span className="text-[9px] text-gray-500">
                  قیمت فعلی
                </span>
                <span
                  dir="ltr"
                  title={formatNumber(price)}
                  className="num block w-full min-w-0 truncate text-[10px] font-semibold text-gray-200 sm:text-xs"
                >
                  {formatNumber(price)}
                </span>
              </div>

              <div className="flex min-w-0 flex-col items-center gap-1 px-0.5">
                <span className="text-[9px] text-gray-500">
                  مقاومت
                </span>
                <span
                  dir="ltr"
                  title={formatNumber(resistance)}
                  className="num block w-full min-w-0 truncate text-[10px] font-semibold text-[#c58b8b] sm:text-xs"
                >
                  {formatNumber(resistance)}
                </span>
              </div>
            </div>
          </>
        ) : (
          <div className="flex min-h-0 flex-1 items-center justify-center">
            <p className="text-center text-[10px] text-gray-500">
              سطوح معتبر حمایت و مقاومت در دسترس نیست
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
