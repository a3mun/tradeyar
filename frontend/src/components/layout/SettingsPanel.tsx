"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Settings, Check, AlertTriangle } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { SOURCE_BY_KEY } from "@/lib/sources";
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
  { name: "آبان‌تتر", logo: "/logos/abantether.png", isRemoved: true },
];

const EXCHANGES_GOLD = [
  { name: "آلفا گلد", logo: "/logos/alfagold.png" },
  { name: "دریا گلد", logo: "/logos/daryagold.png" },
];

const TIMEFRAMES: Timeframe[] = [
  "۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه",
];

export function SettingsPanel() {
  const {
    ticker, source, timeframe, marketType, riskProfile,
    setSource, setTimeframe, setMarketType, setRiskProfile,
  } = useAppStore();

  const { strategy, setStrategy } = useAppStore();

  const isTsetmc = Boolean(ticker) && ticker.charCodeAt(0) > 127;
  const selectedMeta = SOURCE_BY_KEY[source];
  const isWallex = selectedMeta?.value === "wallex";

  return (
    <Card className="text-sm border-white/10 bg-[#0d1b2d]">
      <CardHeader className="px-3 py-0.5">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Settings className="h-4 w-4 text-[#d6ad60]" />
          تنظیمات
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 px-3 pb-2">
        
        {/* ۱. صرافی‌های اصلی */}
        <div className="space-y-1.5">
          <label className="text-[10px] font-medium text-muted-foreground">صرافی</label>
          <div className="grid grid-cols-3 gap-1.5">
            {EXCHANGES_MAJOR.map((s) => {
              const isActive = source === s.value;
              const hasNote = Boolean(SOURCE_BY_KEY[s.value]?.note || SOURCE_BY_KEY[s.value]?.unsupportedTfs?.length);
              
              const textColor = isActive ? "text-[#07111f]" : "text-gray-300";
              
              const inner = (
                <>
                  {isActive && (
                    <span className="absolute -top-1.5 -right-1.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[#10b981] text-white shadow-sm z-10">
                      <Check className="h-2 w-2" strokeWidth={4} />
                    </span>
                  )}
                  <img src={s.logo} alt={s.name} className={`h-5 w-5 object-contain drop-shadow-md ${isActive ? '' : 'opacity-80'}`} />
                  <span className={`text-[10px] font-bold ${textColor}`}>{s.name}</span>
                </>
              );

              // 🔴 حذف افکت شیشه‌ای و استفاده از سرمه‌ای خالص
              const btnClass = `relative flex flex-col items-center justify-center gap-0.5 rounded-lg border py-1.5 px-1 transition-all ${
                isActive 
                  ? "border-[#d6ad60] bg-[#d6ad60] shadow-[0_0_15px_rgba(214,173,96,0.4)]" 
                  : "border-white/10 bg-[#0d1b2d] hover:bg-white/5"
              }`;

              if (!hasNote) {
                return <button key={s.value} onClick={() => setSource(s.value)} className={btnClass}>{inner}</button>;
              }

              return (
                <Tooltip key={s.value}>
                  <TooltipTrigger render={<button onClick={() => setSource(s.value)} className={btnClass} />}>
                    {inner}
                  </TooltipTrigger>
                  <TooltipContent><p className="text-[11px]">{SOURCE_BY_KEY[s.value]?.note}</p></TooltipContent>
                </Tooltip>
              );
            })}
          </div>
        </div>

        {/* ۲. به زودی */}
        <div className="space-y-0.5">
          <p className="text-[9px] text-gray-400 text-right font-medium">صرافی‌های دیگر به‌زودی اضافه می‌شوند.</p>
          <div className="flex flex-wrap items-center gap-1">
            {EXCHANGES_COMING_SOON.map((s, i) => (
              <div key={i} className={`relative flex flex-col items-center gap-0.5 rounded-md border p-1 ${s.isRemoved ? "border-red-500/20 bg-red-500/5 opacity-60" : "border-dashed border-white/10 bg-[#0d1b2d] opacity-70"}`} title={s.isRemoved ? `${s.name} — حذف شده` : `${s.name} — به‌زودی`}>
                <img src={s.logo} alt={s.name} className="h-4 w-4 object-contain grayscale drop-shadow-sm" />
                <span className={`text-[7px] font-bold ${s.isRemoved ? "text-red-400/70 line-through" : "text-gray-400"}`}>{s.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ۳. تحلیل اختصاصی انس طلا */}
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 bg-[#d6ad60]/10 p-1 rounded border border-[#d6ad60]/20">
            <AlertTriangle className="h-3 w-3 text-[#d6ad60]" />
            <span className="text-[9px] text-[#d6ad60] font-bold">تحلیل اختصاصی انس طلا (فقط از طریق افزونه)</span>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-1 pr-1">
            {EXCHANGES_GOLD.map((s, i) => (
              <div key={i} className="flex flex-col items-center gap-0.5">
                <div className="h-7 w-7 rounded-full bg-[#d6ad60]/10 border border-[#d6ad60]/40 flex items-center justify-center overflow-hidden p-1">
                  <img src={s.logo} alt={s.name} className="h-full w-full object-contain drop-shadow-md" />
                </div>
                <span className="text-[8px] font-bold text-[#d6ad60]">{s.name}</span>
              </div>
            ))}
          </div>
          <p className="text-[8px] text-gray-500 leading-relaxed text-justify mt-1">
            برای دریافت اطلاعات بیشتر و دانلود افزونه، به <span className="text-[#d6ad60] font-bold">داشبورد کاربری</span> مراجعه کنید.
          </p>
        </div>

        {/* ۴. هشدارها */}
        {isWallex && (
          <p className="rounded-md border border-amber-500/20 bg-amber-500/5 px-2 py-1 text-[9px] text-amber-400 text-justify leading-relaxed">
            ⚠️ صرافی والکس فقط تایم‌فریم‌های <b>۱ ساعت</b> و <b>روزانه</b> را به صورت معتبر ارائه می‌دهد.
          </p>
        )}
        
        {selectedMeta && !selectedMeta.hasOhlcv && !isWallex && (
          <p className="rounded-md border border-sky-500/20 bg-sky-500/5 px-2 py-1 text-[9px] text-sky-400">
            ℹ️ {selectedMeta.label} کندل ندارد — تحلیل از صرافی دیگر، قیمت از خودش.
          </p>
        )}

        {!isTsetmc && selectedMeta?.unsupportedTfs?.length && !isWallex ? (
          <p className="rounded-md border border-yellow-500/20 bg-yellow-500/5 px-2 py-1 text-[9px] text-yellow-500">
            ℹ️ {selectedMeta.label} برای «{selectedMeta.unsupportedTfs.join("، ")}» داده ندارد — خودکار از صرافی دیگر.
          </p>
        ) : null}

        {/* ۵. تایم‌فریم */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">تایم‌فریم</label>
          <div className="grid grid-cols-3 gap-1">
            {TIMEFRAMES.map((tf) => {
              const isActive = timeframe === tf;
              const isDisabled = isTsetmc && tf !== "روزانه";
              
              return (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  disabled={isDisabled}
                  className={`rounded-lg border py-1 text-[10px] font-bold transition-all ${
                    isActive ? "border-[#d6ad60] bg-[#d6ad60] text-[#101827] shadow-[0_0_8px_rgba(214,173,96,0.3)]" : "border-white/10 bg-[#0d1b2d] text-gray-300 hover:bg-white/5"
                  } ${isDisabled ? "opacity-40 cursor-not-allowed" : ""}`}
                >
                  {tf}
                </button>
              );
            })}
          </div>
        </div>

        {/* ۶. پروفایل ریسک */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">پروفایل ریسک</label>
          <div className="grid grid-cols-2 gap-1">
            <Button size="sm" onClick={() => setRiskProfile("aggressive")} className={`h-7 text-[10px] font-bold ${riskProfile === "aggressive" ? "bg-[#d6ad60] text-[#101827] border-none shadow-sm" : "border border-white/10 text-gray-300 hover:bg-white/5 bg-[#0d1b2d]"}`}>🚀 جسورانه</Button>
            <Button size="sm" onClick={() => setRiskProfile("conservative")} className={`h-7 text-[10px] font-bold ${riskProfile === "conservative" ? "bg-[#d6ad60] text-[#101827] border-none shadow-sm" : "border border-white/10 text-gray-300 hover:bg-white/5 bg-[#0d1b2d]"}`}>🛡️ محتاطانه</Button>
          </div>
        </div>


        {/* 🔴 فاز C — استراتژی (بازطراحی‌شده) */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">
            📊 استراتژی معاملاتی
          </label>
          <div className="grid grid-cols-3 gap-1">
            {[
              { key: "scalp" as const, label: "⚡ اسکالپ", hint: "سریع" },
              { key: "swing" as const, label: "🌊 سوئینگ", hint: "میان‌مدت" },
              { key: "position" as const, label: "🏛 پوزیشن", hint: "بلندمدت" },
            ].map((s) => {
              const isActive = strategy === s.key;
              // 🔴 قفل: فقط تداخل غیرممکن (اسکالپ با محتاطانه)
              const isLocked = s.key === "scalp" && riskProfile !== "aggressive";
              
              return (
                <button
                  key={s.key}
                  onClick={() => setStrategy(s.key)}
                  className={`rounded-lg border py-1.5 text-[10px] font-bold transition-all ${
                    isActive
                      ? "border-[#d6ad60] bg-[#d6ad60] text-[#101827] shadow-[0_0_8px_rgba(214,173,96,0.3)]"
                      : "border-white/10 bg-[#0d1b2d] text-gray-300 hover:bg-white/5"
                  } ${isLocked ? "opacity-50" : ""}`}
                  title={
                    isLocked
                      ? "اسکالپ فقط با پروفایل جسورانه سازگار است — کلیک کن تا خودکار اصلاح شود"
                      : ""
                  }
                >
                  <div>{s.label}</div>
                  <div
                    className={`text-[8px] font-normal ${
                      isActive ? "text-[#101827]/70" : "opacity-60"
                    }`}
                  >
                    {s.hint}
                  </div>
                </button>
              );
            })}
          </div>
          <p className="text-[8px] text-gray-500 leading-relaxed text-justify">
            💡 <span className="text-[#d6ad60] font-bold">اسکالپ</span> فقط با فیوچرز + جسورانه سازگار است.
            <span className="text-[#d6ad60] font-bold"> پوزیشن</span> با اسپات + TF روزانه.
            <span className="text-[#d6ad60] font-bold"> سوئینگ</span> انعطاف‌پذیر است. تغییر نامنطبق، خودکار اصلاح می‌شود.
          </p>
        </div>


        {/* ۷. بازار */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">نوع بازار</label>
          <div className="grid grid-cols-2 gap-1">
            <Button size="sm" onClick={() => setMarketType("spot")} className={`h-7 text-[10px] font-bold ${marketType === "spot" ? "bg-[#d6ad60] text-[#101827] border-none shadow-sm" : "border border-white/10 text-gray-300 hover:bg-white/5 bg-[#0d1b2d]"}`}>💵 اسپات</Button>
            <Button size="sm" onClick={() => setMarketType("futures")} disabled={isTsetmc} className={`h-7 text-[10px] font-bold ${marketType === "futures" ? "bg-[#d6ad60] text-[#101827] border-none shadow-sm" : "border border-white/10 text-gray-300 hover:bg-white/5 bg-[#0d1b2d]"} ${isTsetmc ? "opacity-40 cursor-not-allowed" : ""}`}>📈 فیوچرز</Button>
          </div>
        </div>

      </CardContent>
    </Card>
  );
}