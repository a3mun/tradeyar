"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Settings, Check } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import type { Source, Timeframe, MarketType, RiskProfile } from "@/lib/types";

const SOURCES: {
  value: Source;
  label: string;
  logo: string;
  warning?: string;
  disabled?: boolean;
}[] = [
  { value: "nobitex", label: "نوبیتکس", logo: "/logos/nobitex.png" },
  { value: "bitpin", label: "بیت‌پین", logo: "/logos/bitpin.png" },
  { value: "wallex", label: "والکس", logo: "/logos/wallex.png" },
  {
    value: "abantether",
    label: "آبان‌تتر",
    logo: "/logos/abantether.png",
    warning: "فقط قیمت",
  },
  { value: "tsetmc", label: "بورس", logo: "/logos/tsetmc.png" },
  {
    value: "tabdeal" as Source,
    label: "تبدیل",
    logo: "/logos/tabdeal.png",
    disabled: true,
  },
];

const TIMEFRAMES: Timeframe[] = [
  "۱ دقیقه",
  "۵ دقیقه",
  "۱۵ دقیقه",
  "۳۰ دقیقه",
  "۱ ساعت",
  "روزانه",
];

const REFRESH_OPTIONS = [
  { value: 0, label: "خاموش" },
  { value: 5, label: "۵ ثانیه" },
  { value: 30, label: "۳۰ ثانیه" },
  { value: 60, label: "۶۰ ثانیه" },
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

  const selectedSource = SOURCES.find((s) => s.value === source);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Settings className="h-4 w-4" />
          تنظیمات
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* ═══ صرافی — با بج انتخاب ═══ */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-medium text-muted-foreground">
            صرافی
          </label>
          <div className="grid grid-cols-3 gap-1.5">
            {SOURCES.map((s) => {
              const isActive = source === s.value;
              return (
                <button
                  key={s.value}
                  onClick={() => !s.disabled && setSource(s.value)}
                  disabled={s.disabled}
                  className={`relative flex flex-col items-center gap-1 rounded-lg border-2 p-2 transition-all ${
                    s.disabled
                      ? "border-border opacity-40 cursor-not-allowed"
                      : isActive
                        ? "border-green-500 bg-green-500/10 shadow-md shadow-green-500/20"
                        : "border-border hover:bg-muted/50 opacity-70"
                  }`}
                >
                  {isActive && (
                    <span className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-green-500 text-white shadow-md">
                      <Check className="h-3 w-3" strokeWidth={3} />
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
                  {s.disabled && (
                    <span className="absolute -bottom-1 text-[7px] text-yellow-500">
                      به‌زودی
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          {selectedSource?.warning && (
            <p className="text-[10px] text-yellow-500">
              ⚠️ {selectedSource.warning} — تحلیل از نوبیتکس
            </p>
          )}
        </div>

        <Separator />

        {/* ═══ تایم‌فریم — دکمه‌ای ═══ */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-medium text-muted-foreground">
            تایم‌فریم
          </label>
          <div className="grid grid-cols-3 gap-1.5">
            {TIMEFRAMES.map((tf) => {
              const isActive = timeframe === tf;
              return (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`rounded-lg border-2 px-2 py-1.5 text-[10px] font-medium transition-all ${
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

        <Separator />

        {/* ═══ پروفایل ═══ */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-medium text-muted-foreground">
            پروفایل ریسک
          </label>
          <div className="grid grid-cols-2 gap-2">
            <Button
              size="sm"
              variant={riskProfile === "aggressive" ? "default" : "outline"}
              onClick={() => setRiskProfile("aggressive")}
              className="text-xs"
            >
              🚀 جسورانه
            </Button>
            <Button
              size="sm"
              variant={riskProfile === "conservative" ? "default" : "outline"}
              onClick={() => setRiskProfile("conservative")}
              className="text-xs"
            >
              🛡️ محتاطانه
            </Button>
          </div>
        </div>

        <Separator />

        {/* ═══ بازار ═══ */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-medium text-muted-foreground">
            نوع بازار
          </label>
          <div className="grid grid-cols-2 gap-2">
            <Button
              size="sm"
              variant={marketType === "spot" ? "default" : "outline"}
              onClick={() => setMarketType("spot")}
              className="text-xs"
            >
              💵 اسپات
            </Button>
            <Button
              size="sm"
              variant={marketType === "futures" ? "default" : "outline"}
              onClick={() => setMarketType("futures")}
              className="text-xs"
            >
              📈 فیوچرز
            </Button>
          </div>
        </div>

        <Separator />

        {/* ═══ Refresh ═══ */}
        <div className="space-y-2">
          <label className="text-[11px] font-medium text-muted-foreground">
            به‌روزرسانی خودکار
          </label>
          <div className="grid grid-cols-2 gap-1.5">
            {REFRESH_OPTIONS.map((r) => (
              <Button
                key={r.value}
                size="sm"
                variant={refreshSeconds === r.value ? "default" : "outline"}
                onClick={() => setRefreshSeconds(r.value)}
                className="text-[10px] h-7"
              >
                {r.label}
              </Button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}