"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSignalData } from "@/hooks/useSignalData";
import { formatNumber } from "@/lib/display";
import { TrendingUp } from "lucide-react";

export function SupportResistance() {
  const { data } = useSignalData();

  if (!data) {
    return (
      <Card className="h-[160px] flex flex-col border-white/10 bg-[#051118] shadow-xl">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5 text-sm text-gray-300">
            <TrendingUp className="h-3.5 w-3.5 text-[#d6ad60]" />
            حمایت و مقاومت
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center pb-3">
          <p className="text-center text-[10px] text-gray-500">در حال دریافت...</p>
        </CardContent>
      </Card>
    );
  }

  const price = data.price || 0;
  let support = data.support || 0;
  let resistance = data.resistance || 0;
  const pivots = (data.pivots || {}) as Record<string, number>;

  if (support <= 0 || support >= price) {
    if (pivots.s1 > 0 && pivots.s1 < price) support = pivots.s1;
    else if (pivots.s2 > 0 && pivots.s2 < price) support = pivots.s2;
    else if (pivots.s3 > 0 && pivots.s3 < price) support = pivots.s3;
    else support = price * 0.98;
  }

  if (resistance <= 0 || resistance <= price) {
    if (pivots.r1 > 0 && pivots.r1 > price) resistance = pivots.r1;
    else if (pivots.r2 > 0 && pivots.r2 > price) resistance = pivots.r2;
    else if (pivots.r3 > 0 && pivots.r3 > price) resistance = pivots.r3;
    else resistance = price * 1.02;
  }

  const range = resistance - support;
  const position = range > 0 ? ((price - support) / range) * 100 : 50;
  const clampedPosition = Math.max(0, Math.min(100, position));
  const hasData = support > 0 && resistance > 0 && range > 0;

  let analysis = "";
  let analysisColor = "#94a3b8";

  if (hasData) {
    if (clampedPosition <= 15) { analysis = "نزدیک حمایت"; analysisColor = "#22c55e80"; }
    else if (clampedPosition <= 35) { analysis = "احتمال برگشت"; analysisColor = "#22c55e60"; }
    else if (clampedPosition <= 65) { analysis = "بین حمایت و مقاومت"; analysisColor = "#94a3b8"; }
    else if (clampedPosition <= 85) { analysis = "نزدیک مقاومت"; analysisColor = "#ef444480"; }
    else { analysis = "احتمال ریزش"; analysisColor = "#ef444460"; }
  }

  return (
    <Card className="h-[160px] flex flex-col border-white/10 bg-[#051118] shadow-xl">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm text-gray-300">
          <TrendingUp className="h-3.5 w-3.5 text-[#d6ad60]" />
          حمایت و مقاومت
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-center space-y-3 pb-3">
        {hasData ? (
          <>
            <div className="flex items-center gap-3">
              <span className="num shrink-0 text-2xl font-bold leading-none text-foreground">{Math.round(clampedPosition)}</span>
              <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                <div className="absolute inset-y-0 right-0 rounded-full transition-all duration-500" style={{ width: `${clampedPosition}%`, background: analysisColor }} />
              </div>
            </div>

            <div className="flex justify-between text-[8px] text-gray-500">
              <span>حمایت</span>
              <span>قیمت</span>
              <span>مقاومت</span>
            </div>

            <div className="rounded-md border px-2 py-1.5 text-center text-[10px] font-medium" style={{ borderColor: `${analysisColor}30`, backgroundColor: `${analysisColor}10`, color: analysisColor }}>
              {analysis}
            </div>

            <div className="flex items-center justify-between gap-1 text-[9px]">
              <span className="num text-gray-400">{formatNumber(support)}</span>
              <span className="num font-bold text-gray-200">{formatNumber(price)}</span>
              <span className="num text-gray-400">{formatNumber(resistance)}</span>
            </div>
          </>
        ) : (
          <p className="py-2 text-center text-[10px] text-gray-500">سطوح کلیدی یافت نشد</p>
        )}
      </CardContent>
    </Card>
  );
}