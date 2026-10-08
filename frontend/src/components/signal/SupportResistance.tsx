"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSignalData } from "@/hooks/useSignalData";
import { formatNumber } from "@/lib/display";

export function SupportResistance() {
  const { data } = useSignalData();

  if (!data) return null;

  const price = data.price || 0;
  let support = data.support || 0;
  let resistance = data.resistance || 0;

  const pivots = (data.pivots || {}) as Record<string, number>;

  // ═══ 🔴 fallback هوشمند برای support ═══
  // support باید **زیر** price باشه
  if (support <= 0 || support >= price) {
    if (pivots.s1 > 0 && pivots.s1 < price) {
      support = pivots.s1;
    } else if (pivots.s2 > 0 && pivots.s2 < price) {
      support = pivots.s2;
    } else if (pivots.s3 > 0 && pivots.s3 < price) {
      support = pivots.s3;
    } else {
      // آخرین راه: -۲٪ از price
      support = price * 0.98;
    }
  }

  // ═══ 🔴 fallback هوشمند برای resistance ═══
  // resistance باید **بالای** price باشه
  if (resistance <= 0 || resistance <= price) {
    if (pivots.r1 > 0 && pivots.r1 > price) {
      resistance = pivots.r1;
    } else if (pivots.r2 > 0 && pivots.r2 > price) {
      resistance = pivots.r2;
    } else if (pivots.r3 > 0 && pivots.r3 > price) {
      resistance = pivots.r3;
    } else {
      // آخرین راه: +۲٪ از price
      resistance = price * 1.02;
    }
  }

  const range = resistance - support;
  const position = range > 0 ? ((price - support) / range) * 100 : 50;
  const clampedPosition = Math.max(0, Math.min(100, position));

  const hasData = support > 0 && resistance > 0 && range > 0;

  // ═══ تحلیل ۵ سطحی ═══
  let analysis = "";
  let analysisColor = "#94a3b8";
  let analysisIcon = "⚪";

  if (hasData) {
    if (clampedPosition <= 5) {
      analysis = "روی حمایت — فرصت خرید";
      analysisColor = "#22c55e";
      analysisIcon = "🟢";
    } else if (clampedPosition <= 30) {
      analysis = "نزدیک حمایت — احتمال برگشت";
      analysisColor = "#22c55e";
      analysisIcon = "🟢";
    } else if (clampedPosition <= 70) {
      analysis = "بین حمایت و مقاومت";
      analysisColor = "#94a3b8";
      analysisIcon = "⚪";
    } else if (clampedPosition <= 95) {
      analysis = "نزدیک مقاومت — مراقب باش";
      analysisColor = "#ef4444";
      analysisIcon = "🔴";
    } else {
      analysis = "روی مقاومت — احتمال برگشت";
      analysisColor = "#ef4444";
      analysisIcon = "🔴";
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          🎯 حمایت و مقاومت
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pb-3">
        {hasData ? (
          <>
            <div className="flex items-center gap-3">
              <span className="num shrink-0 text-2xl font-bold leading-none">
                {Math.round(clampedPosition)}
              </span>
              <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="absolute inset-y-0 right-0 rounded-full transition-all duration-500"
                  style={{
                    width: `${clampedPosition}%`,
                    background: analysisColor,
                    opacity: 0.7,
                  }}
                />
                <div
                  className="absolute top-1/2 h-4 w-2.5 -translate-y-1/2 rounded-sm border-2 border-white bg-slate-900 shadow-md transition-all duration-500"
                  style={{ right: `calc(${clampedPosition}% - 5px)` }}
                />
              </div>
            </div>

            <div className="flex justify-between text-[8px] text-muted-foreground">
              <span className="text-green-500">🟢 حمایت</span>
              <span>🎯 قیمت</span>
              <span className="text-red-500">🔴 مقاومت</span>
            </div>

            <div
              className="rounded-md border px-2 py-1 text-center text-[10px] font-bold transition-colors duration-300"
              style={{
                borderColor: `${analysisColor}33`,
                backgroundColor: `${analysisColor}0a`,
                color: analysisColor,
              }}
            >
              {analysisIcon} {analysis}
            </div>

            <div className="flex items-center justify-between gap-1 text-[9px]">
              <span className="num text-green-500">
                {formatNumber(support)}
              </span>
              <span className="num font-bold text-foreground">
                {formatNumber(price)}
              </span>
              <span className="num text-red-500">
                {formatNumber(resistance)}
              </span>
            </div>
          </>
        ) : (
          <p className="py-2 text-center text-[10px] text-muted-foreground">
            سطوح کلیدی شناسایی نشد
          </p>
        )}
      </CardContent>
    </Card>
  );
}