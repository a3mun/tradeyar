"use client";

import { useEffect, useRef, useState } from "react";
import { Info, AlertTriangle, CheckCircle2, XCircle, MinusCircle, Brain } from "lucide-react";
import { AccordionSection } from "@/components/ui/accordion-section";
import type { ChecklistData } from "@/lib/types";

interface Props {
  data: ChecklistData;
}

// 🔴 هوک شمارنده (Count-up)
function useCountUp(target: number, duration: number = 1500) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          let start = 0;
          const stepTime = Math.abs(Math.floor(duration / target));
          const timer = setInterval(() => {
            start += 1;
            setCount(start);
            if (start >= target) {
              clearInterval(timer);
            }
          }, stepTime);
        }
      },
      { threshold: 0.1 }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }
    return () => observer.disconnect();
  }, [target, duration, hasAnimated]);

  return { count, ref };
}

export function Checklist({ data }: Props) {
  if (!data || !data.items || data.items.length === 0) return null;

  const warnings = data.items.filter((i) => i.color === "red");
  const greens = data.items.filter((i) => i.color === "green").length;
  const percentage = data.percentage || 0;

  const progressColor = "text-blue-500";
  const borderColor = "border-blue-500/30";
  const bgColor = "bg-blue-500/5";

  const previewText = warnings.length
    ? `${greens} تأیید · ${warnings.length} هشدار`
    : `${data.final} · ${greens} تأیید`;

  // 🔴 مقدار هدف برای شمارنده (می‌توانی بعداً داینامیک کنی)
  const totalIndicators = 32;
  const { count, ref: counterRef } = useCountUp(totalIndicators, 1500);

  return (
    <AccordionSection
      title="چک‌لیست معاملاتی"
      icon={<CheckCircle2 className="h-3.5 w-3.5" />}
      preview={previewText}
      tone="primary"
      pulse
      badge={
        <span className={`num rounded-full border px-2 py-0.5 text-[9px] font-bold ${progressColor} border-blue-500/30 bg-blue-500/10`}>
          {percentage} امتیاز
        </span>
      }
    >
      <div className="space-y-4">
        {/* ═══ هدر: دایره امتیاز + خلاصه ═══ */}
        <div className={`flex items-center gap-4 rounded-xl border ${borderColor} ${bgColor} p-3 shadow-sm`}>
          <div className="relative flex h-16 w-16 shrink-0 items-center justify-center">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 36 36">
              <path className="text-white/10" strokeWidth="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              <path className={`transition-all duration-1000 ${progressColor}`} strokeDasharray={`${percentage}, 100`} strokeWidth="3" strokeLinecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            </svg>
            <div className="absolute flex flex-col items-center justify-center">
              <span className={`num text-sm font-bold leading-none ${progressColor}`}>{percentage}</span>
              <span className="text-[7px] text-muted-foreground mt-0.5">امتیاز</span>
            </div>
          </div>

          <div className="flex-1 space-y-1">
            <p className="text-[12px] font-bold text-foreground/90">{data.final}</p>
            <p className="flex items-center gap-1 text-[10px] text-muted-foreground/80">
              <Info className="h-3 w-3" />
              این امتیاز نشان‌دهنده مساعد بودن شرایط تکنیکال است (نه تضمین جهت سیگنال).
            </p>
            {warnings.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {warnings.slice(0, 2).map((w, i) => (
                  <span key={i} className="flex items-center gap-1 rounded-md bg-red-500/10 px-1.5 py-0.5 text-[9px] text-red-400 border border-red-500/20">
                    <AlertTriangle className="h-2.5 w-2.5" />
                    {w.label}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ═══ آیتم‌ها ═══ */}
        <div className="space-y-2">
          {data.items.map((item, idx) => {
            const isGreen = item.color === "green";
            const isRed = item.color === "red";
            const isYellow = item.color === "yellow";

            const Icon = isGreen ? CheckCircle2 : isRed ? XCircle : MinusCircle;
            const iconColor = isGreen ? "text-green-500" : isRed ? "text-red-500" : "text-yellow-500";
            const itemBgColor = isGreen ? "bg-green-500/5" : isRed ? "bg-red-500/5" : "bg-yellow-500/5";
            const itemBorderColor = isGreen ? "border-green-500/20" : isRed ? "border-red-500/20" : "border-yellow-500/20";

            return (
              <div key={`${item.group}-${idx}`} className={`group relative overflow-hidden rounded-lg border ${itemBorderColor} ${itemBgColor} p-2.5 transition-all hover:bg-white/5`}>
                <div className="flex items-start gap-2.5">
                  <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconColor}`} />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[11px] font-bold text-foreground/90">{item.icon} {item.label}</p>
                      <span className="num shrink-0 rounded bg-black/20 px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">وزن: {Math.round(item.weight)}٪</span>
                    </div>
                    <p className="text-[10px] leading-relaxed text-muted-foreground">{item.detail}</p>
                    {item.reasons && item.reasons.length > 0 && (
                      <ul className="mt-1.5 space-y-1">
                        {item.reasons.map((r, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-[9.5px] text-foreground/60">
                            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-current opacity-50" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* 🔴 بخش جدید: شمارنده اندیکاتورها */}
        <div ref={counterRef} className="mt-4 flex items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-[10px] text-muted-foreground">
          <Brain className="h-3.5 w-3.5 text-blue-400" />
          <span>
            برای این تحلیل، <b className="num text-blue-400 text-sm">{count}</b> اندیکاتور تکنیکال در ۵ گروه استفاده شد.
          </span>
        </div>

      </div>
    </AccordionSection>
  );
}