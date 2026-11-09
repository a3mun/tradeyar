"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Settings,
  Check,
  Lock,
  Sparkles,
  TrendingUp,
  Building2,
} from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { SOURCE_BY_KEY } from "@/lib/sources";
import { useIsTouchDevice } from "@/lib/hooks/useDeviceType";
import { InfoToast } from "@/components/ui/info-toast";
import type { Timeframe, Source } from "@/lib/types";

const EXCHANGES_MAJOR: { name: string; logo: string; value: Source }[] = [
  { name: "نوبیتکس", logo: "/logos/nobitex.png", value: "nobitex" },
  { name: "بیت‌پین", logo: "/logos/bitpin.png", value: "bitpin" },
  { name: "والکس", logo: "/logos/wallex.png", value: "wallex" },
  { name: "تبدیل", logo: "/logos/tabdeal.png", value: "tabdeal" },
  { name: "بورس تهران", logo: "/logos/tsetmc.png", value: "tsetmc" },
];

const EXCHANGES_COMING_SOON = [
  { name: "رمزینکس", logo: "/logos/ramzinex.png" },
  { name: "توبیت", logo: "/logos/toobit.png" },
  { name: "بینگ‌ایکس", logo: "/logos/bingx.png" },
  { name: "بیت۲۴", logo: "/logos/bit24.png" },
  {
    name: "آبان‌تتر",
    logo: "/logos/abantether.png",
    isRemoved: true,
    reason: "API صرافی دارای اشکال — موقتاً حذف شد",
  },
];

const EXCHANGES_GOLD = [
  { name: "آلفا گلد", logo: "/logos/alfagold.png" },
  { name: "دریا گلد", logo: "/logos/daryagold.png" },
];

const TIMEFRAMES: Timeframe[] = [
  "۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه",
];

const TF_ALLOWED_BY_STRATEGY: Record<string, Timeframe[]> = {
  scalp: ["۱ دقیقه", "۵ دقیقه"],
  swing: TIMEFRAMES,
  position: ["۳۰ دقیقه", "۱ ساعت", "روزانه"],
};

const STRATEGIES = [
  {
    key: "scalp" as const,
    icon: Sparkles,
    label: "اسکالپ",
    hint: "سریع",
    tooltip: "⚡ اسکالپ: نوسان‌گیری سریع (۱-۵ دقیقه)\n🔒 فقط با فیوچرز + جسورانه",
  },
  {
    key: "swing" as const,
    icon: TrendingUp,
    label: "سوئینگ",
    hint: "میان‌مدت",
    tooltip: "🌊 سوئینگ: معاملات میان‌مدت\n✓ انعطاف‌پذیر — هر بازاری",
  },
  {
    key: "position" as const,
    icon: Building2,
    label: "پوزیشن",
    hint: "بلندمدت",
    tooltip: "🏛 پوزیشن: سرمایه‌گذاری بلندمدت\n✓ ۳۰ دقیقه تا روزانه",
  },
];

export function SettingsPanel() {
  const {
    ticker,
    source,
    timeframe,
    marketType,
    riskProfile,
    strategy,
    setSource,
    setTimeframe,
    setMarketType,
    setRiskProfile,
    setStrategy,
  } = useAppStore();

  const isTouch = useIsTouchDevice();
  const [toast, setToast] = useState<string | null>(null);

  const isTsetmc = Boolean(ticker) && ticker.charCodeAt(0) > 127;
  const selectedMeta = SOURCE_BY_KEY[source];
  const isWallex = selectedMeta?.value === "wallex";
  const allowedTfs = TF_ALLOWED_BY_STRATEGY[strategy] || TIMEFRAMES;

  // ═══════════════════════════════════════════════════════════════
  // 🔴 قفل‌ها (استراتژی هرگز قفل نمی‌شه — فقط بقیه)
  // ═══════════════════════════════════════════════════════════════
  
  // 🔴 استراتژی: فقط برای tsetmc قفل (اسکالپ بی‌معنی)
  const isScalpLocked = isTsetmc;
  
  // 🔴 بازار: اگر اسکالپ فعاله → اسپات قفل
  const isSpotLocked = strategy === "scalp";
  
  // 🔴 ریسک: اگر اسکالپ فعاله → محتاطانه قفل
  const isConservativeLocked = strategy === "scalp";

  // کلیک روی استراتژی
  const handleStrategyClick = (
    key: "scalp" | "swing" | "position",
    tooltip: string
  ) => {
    // 🔴 فقط اسکالپ برای tsetmc قفل
    if (isTsetmc && key === "scalp") {
      if (isTouch) setToast("بورس تهران: اسکالپ معنی ندارد — سوئینگ یا پوزیشن");
      return;
    }
    setStrategy(key);
    if (isTouch) setToast(tooltip);
  };

  // Status badge
  const strategyLabel =
    STRATEGIES.find((s) => s.key === strategy)?.label || "";
  const marketLabel = marketType === "spot" ? "اسپات" : "فیوچرز";
  const riskLabel = riskProfile === "aggressive" ? "جسورانه" : "محتاطانه";

  return (
    <>
      <InfoToast message={toast} onClose={() => setToast(null)} />

      <Card className="text-sm border-white/10 bg-[#0d1b2d]">
        <CardHeader className="px-3 py-1">
          <CardTitle className="flex items-center gap-2 text-sm font-display">
            <Settings className="h-4 w-4 text-[#d6ad60]" />
            تنظیمات
          </CardTitle>
          {/* 🔴 وضعیت فعلی */}
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <span className="rounded border border-[#d6ad60]/30 bg-[#d6ad60]/10 px-1.5 py-0.5 text-[7px] font-extrabold text-[#d6ad60]">
              {strategyLabel}
            </span>
            <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[7px] font-extrabold text-gray-300">
              {marketLabel}
            </span>
            <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[7px] font-extrabold text-gray-300">
              {riskLabel}
            </span>
            <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[7px] font-extrabold text-gray-300">
              {timeframe}
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-2.5 px-3 pb-2.5">
          {/* ═══ ۱. صرافی ═══ */}
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-muted-foreground">
              صرافی
            </label>
            <div className="grid grid-cols-3 gap-1">
              {EXCHANGES_MAJOR.map((s) => {
                const isActive = source === s.value;
                const hasNote = Boolean(
                  SOURCE_BY_KEY[s.value]?.note ||
                    SOURCE_BY_KEY[s.value]?.unsupportedTfs?.length
                );
                const textColor = isActive ? "text-[#07111f]" : "text-gray-200";

                const inner = (
                  <>
                    {isActive && (
                      <span className="absolute -top-1 -right-1 flex h-3 w-3 items-center justify-center rounded-full bg-[#10b981] text-white shadow-sm z-10">
                        <Check className="h-1.5 w-1.5" strokeWidth={4} />
                      </span>
                    )}
                    <img
                      src={s.logo}
                      alt={s.name}
                      className={`h-4 w-4 object-contain ${
                        isActive ? "" : "opacity-80"
                      }`}
                    />
                    <span className={`text-[10px] font-extrabold ${textColor}`}>
                      {s.name}
                    </span>
                  </>
                );

                const btnClass = `relative flex flex-col items-center justify-center gap-0.5 rounded-lg border py-1 px-1 transition-all ${
                  isActive
                    ? "border-[#d6ad60] bg-[#d6ad60] shadow-[0_0_8px_rgba(214,173,96,0.3)]"
                    : "border-white/10 bg-[#0d1b2d] hover:bg-white/5 active:scale-95"
                }`;

                if (!hasNote) {
                  return (
                    <button
                      key={s.value}
                      onClick={() => setSource(s.value)}
                      className={btnClass}
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
                        />
                      }
                    >
                      {inner}
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-[10px]">
                        {SOURCE_BY_KEY[s.value]?.note}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
          </div>

          {/* ═══ ۲. به‌زودی ═══ */}
          <div className="flex items-center gap-1.5 text-[8px] text-gray-500">
            <span className="shrink-0">به‌زودی:</span>
            <div className="flex flex-wrap items-center gap-1">
              {EXCHANGES_COMING_SOON.map((s, i) => {
                const isRemoved = "isRemoved" in s && s.isRemoved;
                const reason =
                  "reason" in s
                    ? (s as { reason: string }).reason
                    : `${s.name} — به‌زودی`;

                return (
                  <Tooltip key={i}>
                    <TooltipTrigger
                      render={
                        <div
                          className={`flex items-center gap-0.5 rounded border px-1 py-0.5 ${
                            isRemoved
                              ? "border-red-500/20 bg-red-500/5 opacity-60"
                              : "border-dashed border-white/10 bg-[#0d1b2d] opacity-70"
                          }`}
                        />
                      }
                    >
                      <img
                        src={s.logo}
                        alt={s.name}
                        className="h-2.5 w-2.5 object-contain grayscale"
                      />
                      <span
                        className={`text-[7px] font-bold ${
                          isRemoved
                            ? "text-red-400/70 line-through"
                            : "text-gray-400"
                        }`}
                      >
                        {s.name}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-[10px]">{reason}</p>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
          </div>

          {/* ═══ ۳. انس طلا ═══ */}
          <div className="flex items-center justify-between gap-2 rounded-md border border-[#d6ad60]/20 bg-[#d6ad60]/5 px-2 py-1">
            <div className="flex items-center gap-1.5">
              <span className="text-[8px] font-bold text-[#d6ad60]">
                انس طلا
              </span>
              <div className="flex items-center gap-1.5">
                {EXCHANGES_GOLD.map((s, i) => (
                  <div key={i} className="flex items-center gap-0.5">
                    <img
                      src={s.logo}
                      alt={s.name}
                      className="h-3.5 w-3.5 object-contain"
                    />
                    <span className="text-[7px] text-[#d6ad60]/80 font-bold">
                      {s.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <span className="text-[7px] text-gray-500 whitespace-nowrap font-bold">
              فقط با افزونه کروم
            </span>
          </div>

          {/* ═══ هشدارها ═══ */}
          {isWallex && (
            <p className="rounded-md border border-amber-500/20 bg-amber-500/5 px-2 py-0.5 text-[8px] text-amber-400">
              ⚠️ والکس: فقط ۱ ساعت و روزانه
            </p>
          )}
          {selectedMeta && !selectedMeta.hasOhlcv && !isWallex && (
            <p className="rounded-md border border-sky-500/20 bg-sky-500/5 px-2 py-0.5 text-[8px] text-sky-400">
              ℹ️ {selectedMeta.label}: کندل ندارد — تحلیل از صرافی دیگر
            </p>
          )}
          {!isTsetmc && selectedMeta?.unsupportedTfs?.length && !isWallex && (
            <p className="rounded-md border border-yellow-500/20 bg-yellow-500/5 px-2 py-0.5 text-[8px] text-yellow-500">
              ℹ️ بدون {selectedMeta.unsupportedTfs.join("، ")}
            </p>
          )}

          {/* ═══ ۴. استراتژی (اول) ═══ */}
          <div className="space-y-1">
            <label className="flex items-center justify-between text-[10px] font-medium text-muted-foreground">
              <span>📊 استراتژی</span>
              <span className="text-[8px] text-[#d6ad60]/70">
                {allowedTfs.length} TF فعال
              </span>
            </label>
            <div className="grid grid-cols-3 gap-1">
              {STRATEGIES.map((s) => {
                const isActive = strategy === s.key;
                const isLocked = isTsetmc && s.key === "scalp";
                const Icon = s.icon;

                return (
                  <Tooltip key={s.key}>
                    <TooltipTrigger
                      render={
                        <button
                          onClick={() =>
                            handleStrategyClick(s.key, s.tooltip)
                          }
                          className={`relative rounded-lg border py-1.5 px-1 transition-all active:scale-95 ${
                            isActive
                              ? "border-[#d6ad60] bg-[#d6ad60] text-[#101827] shadow-[0_0_8px_rgba(214,173,96,0.4)]"
                              : "border-white/10 bg-[#0d1b2d] text-gray-200 hover:bg-white/5"
                          } ${isLocked ? "opacity-60" : ""}`}
                        />
                      }
                    >
                      <div className="flex flex-col items-center gap-0.5">
                        <div className="flex items-center gap-0.5">
                          <Icon className="h-3.5 w-3.5" />
                          <span className="text-[10px] font-extrabold">
                            {s.label}
                          </span>
                          {isLocked && (
                            <Lock className="h-2.5 w-2.5 opacity-80" />
                          )}
                        </div>
                        <span
                          className={`text-[8px] font-bold ${
                            isActive ? "text-[#101827]/80" : "opacity-70"
                          }`}
                        >
                          {s.hint}
                        </span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-[10px] whitespace-pre-line">
                        {s.tooltip}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
          </div>

          {/* ═══ ۵. نوع بازار ═══ */}
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-muted-foreground">
              نوع بازار
            </label>
            <div className="grid grid-cols-2 gap-1">
              <Button
                size="sm"
                onClick={() => setMarketType("spot")}
                disabled={isSpotLocked}
                className={`h-7 text-[10px] font-extrabold ${
                  marketType === "spot"
                    ? "bg-[#d6ad60] text-[#101827] border-none shadow-sm hover:bg-[#d6ad60]/90"
                    : "border border-white/10 text-gray-200 hover:bg-white/5 bg-[#0d1b2d]"
                } ${isSpotLocked ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                💵 اسپات
              </Button>
              <Button
                size="sm"
                onClick={() => setMarketType("futures")}
                disabled={isTsetmc}
                className={`h-7 text-[10px] font-extrabold ${
                  marketType === "futures"
                    ? "bg-[#d6ad60] text-[#101827] border-none shadow-sm hover:bg-[#d6ad60]/90"
                    : "border border-white/10 text-gray-200 hover:bg-white/5 bg-[#0d1b2d]"
                } ${isTsetmc ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                📈 فیوچرز
              </Button>
            </div>
          </div>

          {/* ═══ ۶. پروفایل ریسک ═══ */}
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-muted-foreground">
              پروفایل ریسک
            </label>
            <div className="grid grid-cols-2 gap-1">
              <Button
                size="sm"
                onClick={() => setRiskProfile("aggressive")}
                className={`h-7 text-[10px] font-extrabold ${
                  riskProfile === "aggressive"
                    ? "bg-[#d6ad60] text-[#101827] border-none shadow-sm hover:bg-[#d6ad60]/90"
                    : "border border-white/10 text-gray-200 hover:bg-white/5 bg-[#0d1b2d]"
                }`}
              >
                🚀 جسورانه
              </Button>
              <Button
                size="sm"
                onClick={() => setRiskProfile("conservative")}
                disabled={isConservativeLocked}
                className={`h-7 text-[10px] font-extrabold ${
                  riskProfile === "conservative"
                    ? "bg-[#d6ad60] text-[#101827] border-none shadow-sm hover:bg-[#d6ad60]/90"
                    : "border border-white/10 text-gray-200 hover:bg-white/5 bg-[#0d1b2d]"
                } ${isConservativeLocked ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                🛡️ محتاطانه
              </Button>
            </div>
          </div>

          {/* ═══ ۷. تایم‌فریم ═══ */}
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-muted-foreground">
              تایم‌فریم
            </label>
            <div className="grid grid-cols-3 gap-1">
              {TIMEFRAMES.map((tf) => {
                const isActive = timeframe === tf;
                const isTsetmcLocked = isTsetmc && tf !== "روزانه";
                const isStrategyLocked = !allowedTfs.includes(tf);
                const isDisabled = isTsetmcLocked || isStrategyLocked;

                return (
                  <Tooltip key={tf}>
                    <TooltipTrigger
                      render={
                        <button
                          onClick={() => !isDisabled && setTimeframe(tf)}
                          disabled={isDisabled}
                          className={`rounded-lg border py-1.5 text-[10px] font-extrabold transition-all ${
                            isActive
                              ? "border-[#d6ad60] bg-[#d6ad60] text-[#101827] shadow-[0_0_8px_rgba(214,173,96,0.4)]"
                              : "border-white/10 bg-[#0d1b2d] text-gray-200 hover:bg-white/5"
                          } ${
                            isDisabled
                              ? "opacity-30 cursor-not-allowed"
                              : "active:scale-95"
                          }`}
                        />
                      }
                    >
                      {tf}
                    </TooltipTrigger>
                    {isDisabled && (
                      <TooltipContent>
                        <p className="text-[10px]">
                          {isTsetmcLocked
                            ? "بورس تهران فقط روزانه"
                            : `با «${
                                STRATEGIES.find((s) => s.key === strategy)
                                  ?.label
                              }» سازگار نیست`}
                        </p>
                      </TooltipContent>
                    )}
                  </Tooltip>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}