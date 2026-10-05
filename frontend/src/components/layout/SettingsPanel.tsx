"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Settings, Check } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import {
  PLANNED_SOURCE_META,
  REMOVED_SOURCE_META,
  SOURCE_BY_KEY,
  SOURCE_META,
} from "@/lib/sources";
import type { Timeframe } from "@/lib/types";

const TIMEFRAMES: Timeframe[] = [
  "۱ دقیقه",
  "۵ دقیقه",
  "۱۵ دقیقه",
  "۳۰ دقیقه",
  "۱ ساعت",
  "روزانه",
];

export function SettingsPanel() {
  const {
    source,
    timeframe,
    marketType,
    riskProfile,
    refreshSeconds,
    setSource,
    setTimeframe,
    setMarketType,
    setRiskProfile,
    setRefreshSeconds,
  } = useAppStore();

  const selectedMeta = SOURCE_BY_KEY[source];

  return (
    <Card>
      <CardHeader className="px-3 pb-2 pt-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Settings className="h-4 w-4" />
          تنظیمات
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2.5 px-3 pb-3">
        {/* ═══ صرافی‌های فعال ═══ */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">
            صرافی
          </label>
          <div className="grid grid-cols-3 gap-1.5">
            {SOURCE_META.map((s) => {
              const isActive = source === s.value;
              const hasNote = Boolean(s.note || s.unsupportedTfs?.length);

              const inner = (
                <>
                  {isActive && (
                    <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-green-500 text-white shadow-md">
                      <Check className="h-2.5 w-2.5" strokeWidth={3} />
                    </span>
                  )}
                  <img
                    src={s.logo}
                    alt={s.label}
                    className="h-6 w-6 object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                  <span
                    className={`text-[9px] font-bold ${
                      isActive ? "text-green-500" : ""
                    }`}
                  >
                    {s.label}
                  </span>
                  {!s.hasOhlcv ? (
                    <span className="absolute -bottom-1 rounded-full bg-orange-500/20 px-1 text-[6px] text-orange-400">
                      بدون کندل
                    </span>
                  ) : null}
                </>
              );

              const btnClass = `relative flex flex-col items-center gap-0.5 rounded-md border-2 p-1.5 transition-all ${
                isActive
                  ? "border-green-500 bg-green-500/10 shadow-md shadow-green-500/20"
                  : "border-border opacity-70 hover:bg-muted/50"
              }`;

              if (!hasNote) {
                return (
                  <button
                    key={s.value}
                    onClick={() => setSource(s.value)}
                    className={btnClass}
                    aria-pressed={isActive}
                  >
                    {inner}
                  </button>
                );
              }

              return (
                <Tooltip key={s.value}>
                  <TooltipTrigger
                    render={
                      <button
                        onClick={() => setSource(s.value)}
                        className={btnClass}
                        aria-pressed={isActive}
                      />
                    }
                  >
                    {inner}
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-[11px]">
                      {s.note ?? `${s.label} — تحلیل با صرافی دیگر`}
                    </p>
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </div>
        </div>

        {/* ═══ صرافی‌های غیرفعال — کنار هم، رنگی ولی کمرنگ ═══ */}
        <div className="flex flex-wrap items-center gap-1">
          {/* به‌زودی */}
          {PLANNED_SOURCE_META.map((s) => (
            <Tooltip key={s.value}>
              <TooltipTrigger
                render={
                  <div className="cursor-not-allowed" aria-disabled="true" />
                }
              >
                <div className="relative flex flex-col items-center gap-0.5 rounded-md border border-dashed border-border/60 p-1 opacity-60">
                  {s.logo ? (
                    <img
                      src={s.logo}
                      alt={s.label}
                      className="h-4 w-4 object-contain"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <span className="text-[10px] leading-none">{s.icon}</span>
                  )}
                  <span className="text-[7px] text-muted-foreground">
                    {s.label}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-[11px]">{s.label} — به‌زودی</p>
              </TooltipContent>
            </Tooltip>
          ))}

          {/* حذف‌شده */}
          {REMOVED_SOURCE_META.map((s) => (
            <Tooltip key={s.value}>
              <TooltipTrigger
                render={
                  <div className="cursor-not-allowed" aria-disabled="true" />
                }
              >
                <div className="relative flex flex-col items-center gap-0.5 rounded-md border border-red-500/20 bg-red-500/5 p-1 opacity-50">
                  {s.logo ? (
                    <img
                      src={s.logo}
                      alt={s.label}
                      className="h-4 w-4 object-contain"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <span className="text-[10px] leading-none">{s.icon}</span>
                  )}
                  <span className="text-[7px] text-red-400/70 line-through">
                    {s.label}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-[11px]">{s.reason}</p>
              </TooltipContent>
            </Tooltip>
          ))}
        </div>

        {/* ═══ نکات صرافی انتخابی ═══ */}
        {selectedMeta && !selectedMeta.hasOhlcv && (
          <p className="rounded-md border border-sky-500/20 bg-sky-500/5 px-2 py-1.5 text-[9px] text-sky-400">
            ℹ️ {selectedMeta.label} کندل ندارد — تحلیل از صرافی دیگر،
            قیمت از خودش.
          </p>
        )}
        {selectedMeta?.unsupportedTfs?.length ? (
          <p className="rounded-md border border-yellow-500/20 bg-yellow-500/5 px-2 py-1.5 text-[9px] text-yellow-500">
            ℹ️ {selectedMeta.label} برای «
            {selectedMeta.unsupportedTfs.join("، ")}» داده ندارد — خودکار
            از صرافی دیگر.
          </p>
        ) : null}

        {/* ═══ تایم‌فریم ═══ */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">
            تایم‌فریم
          </label>
          <div className="grid grid-cols-3 gap-1">
            {TIMEFRAMES.map((tf) => {
              const isActive = timeframe === tf;
              return (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`rounded-md border-2 px-1.5 py-1 text-[10px] font-medium transition-all ${
                    isActive
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:bg-muted/50"
                  }`}
                >
                  {tf}
                </button>
              );
            })}
          </div>
        </div>

        {/* ═══ پروفایل ریسک ═══ */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">
            پروفایل ریسک
          </label>
          <div className="grid grid-cols-2 gap-1.5">
            <Button
              size="sm"
              variant={riskProfile === "aggressive" ? "default" : "outline"}
              onClick={() => setRiskProfile("aggressive")}
              className="h-7 text-[11px]"
            >
              🚀 جسورانه
            </Button>
            <Button
              size="sm"
              variant={riskProfile === "conservative" ? "default" : "outline"}
              onClick={() => setRiskProfile("conservative")}
              className="h-7 text-[11px]"
            >
              🛡️ محتاطانه
            </Button>
          </div>
        </div>

        {/* ═══ بازار ═══ */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">
            نوع بازار
          </label>
          <div className="grid grid-cols-2 gap-1.5">
            <Button
              size="sm"
              variant={marketType === "spot" ? "default" : "outline"}
              onClick={() => setMarketType("spot")}
              className="h-7 text-[11px]"
            >
              💵 اسپات
            </Button>
            <Button
              size="sm"
              variant={marketType === "futures" ? "default" : "outline"}
              onClick={() => setMarketType("futures")}
              className="h-7 text-[11px]"
            >
              📈 فیوچرز
            </Button>
          </div>
        </div>

      </CardContent>
    </Card>
  );
}