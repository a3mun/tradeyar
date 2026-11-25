
"use client";

import { useEffect, useRef, useState } from "react";
import {
  Info,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  MinusCircle,
  Brain,
} from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import type { ChecklistData } from "@/lib/types";

interface Props {
  data?: ChecklistData;
}

const STRATEGY_LABELS: Record<string, { fa: string; icon: string }> = {
  scalp: { fa: "اسکالپ", icon: "⚡" },
  swing: { fa: "سوئینگ", icon: "🌊" },
  position: { fa: "پوزیشن", icon: "🏛" },
};

function useCountUp(target: number, duration: number = 1200) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const element = ref.current;

    if (!element || target <= 0) {
      setCount(0);
      return;
    }

    let timer: ReturnType<typeof setInterval> | undefined;
    let observer: IntersectionObserver | undefined;

    const startAnimation = () => {
      if (hasAnimated.current) return;

      hasAnimated.current = true;

      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        setCount(target);
        return;
      }

      const startedAt = Date.now();
      const interval = 30;

      timer = setInterval(() => {
        const progress = Math.min(
          (Date.now() - startedAt) / duration,
          1
        );

        setCount(Math.round(target * progress));

        if (progress >= 1 && timer) {
          clearInterval(timer);
          timer = undefined;
        }
      }, interval);
    };

    if (typeof IntersectionObserver === "undefined") {
      startAnimation();
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0]?.isIntersecting) {
            startAnimation();
            observer?.disconnect();
          }
        },
        { threshold: 0.1 }
      );

      observer.observe(element);
    }

    return () => {
      observer?.disconnect();

      if (timer) {
        clearInterval(timer);
      }
    };
  }, [target, duration]);

  return { count, ref };
}

export function Checklist({ data }: Props) {
  const { strategy } = useAppStore();

  const items = data?.items ?? [];
  const hasData = items.length > 0;

  const warnings = items.filter((item) => item.color === "red");

  const rawPercentage = Number(data?.percentage ?? 0);
  const percentage = Number.isFinite(rawPercentage)
    ? Math.min(100, Math.max(0, Math.round(rawPercentage)))
    : 0;

  const activeGroups = new Set(
    items
      .map((item) => item.group)
      .filter((group) => typeof group === "string" && group.trim())
  );

  const strategyMeta =
    STRATEGY_LABELS[strategy] || STRATEGY_LABELS.swing;

  const { count: itemCount, ref: counterRef } = useCountUp(
    items.length
  );

  const { count: groupCount, ref: groupCounterRef } = useCountUp(
    activeGroups.size
  );

  const progressColor = "text-[#d6ad60]";
  const borderColor = "border-[#d6ad60]/20";
  const bgColor = "bg-[#d6ad60]/5";

  if (!hasData) {
    return (
      <div className="space-y-2 py-2">
        <div className="h-4 w-3/4 animate-pulse rounded bg-muted/30" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-muted/30" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-muted/30" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-muted/30" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* هدر */}
      <div
        className={`flex items-center gap-4 rounded-xl border ${borderColor} ${bgColor} p-3 shadow-sm`}
      >
        <div className="relative flex h-16 w-16 shrink-0 items-center justify-center">
          <svg className="h-full w-full -rotate-90" viewBox="0 0 36 36">
            <path
              className="text-white/10"
              strokeWidth="3"
              stroke="currentColor"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              className={`transition-all duration-1000 ${progressColor}`}
              strokeDasharray={`${percentage}, 100`}
              strokeWidth="3"
              strokeLinecap="round"
              stroke="currentColor"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>

          <div className="absolute flex flex-col items-center justify-center">
            <span
              className={`num text-sm font-bold leading-none ${progressColor}`}
            >
              {percentage}
            </span>
            <span className="text-[7px] text-muted-foreground mt-0.5">
              امتیاز
            </span>
          </div>
        </div>

        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-1">
            <span className="text-[10px]">{strategyMeta.icon}</span>
            <span className="text-[9px] font-bold text-muted-foreground">
              استراتژی: {strategyMeta.fa}
            </span>
          </div>

          <p className="text-[12px] font-bold text-foreground/90">
            {data?.final}
          </p>

          <p className="flex items-center gap-1 text-[10px] text-muted-foreground/80">
            <Info className="h-3 w-3 shrink-0" />
            این امتیاز نشان‌دهنده مساعد بودن شرایط تکنیکال است (نه تضمین جهت
            سیگنال).
          </p>

          {warnings.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {warnings.slice(0, 2).map((warning, index) => (
                <span
                  key={`${warning.group}-${index}`}
                  className="flex items-center gap-1 rounded-md border border-red-500/20 bg-red-500/5 px-1.5 py-0.5 text-[9px] text-red-400/80"
                >
                  <AlertTriangle className="h-2.5 w-2.5" />
                  {warning.label}
                </span>
              ))}

              {warnings.length > 2 && (
                <span className="rounded-md border border-red-500/20 bg-red-500/5 px-1.5 py-0.5 text-[9px] text-red-400/80">
                  {warnings.length - 2}+ مورد دیگر
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* آیتم‌ها */}
      <div className="space-y-2">
        {items.map((item, idx) => {
          const isGreen = item.color === "green";
          const isRed = item.color === "red";

          const Icon = isGreen
            ? CheckCircle2
            : isRed
              ? XCircle
              : MinusCircle;

          const iconColor = isGreen
            ? "text-green-500/80"
            : isRed
              ? "text-red-500/80"
              : "text-[#d6ad60]/80";

          const itemBgColor = isGreen
            ? "bg-green-500/5"
            : isRed
              ? "bg-red-500/5"
              : "bg-[#d6ad60]/5";

          const itemBorderColor = isGreen
            ? "border-green-500/20"
            : isRed
              ? "border-red-500/20"
              : "border-[#d6ad60]/20";

          const weight = Number(item.weight);
          const safeWeight = Number.isFinite(weight)
            ? Math.round(weight)
            : 0;

          return (
            <div
              key={`${item.group}-${idx}`}
              className={`group relative overflow-hidden rounded-lg border ${itemBorderColor} ${itemBgColor} p-2.5 transition-all hover:bg-white/5`}
            >
              <div className="flex items-start gap-2.5">
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconColor}`} />

                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[11px] font-bold text-foreground/90">
                      {item.icon} {item.label}
                    </p>

                    <span className="num shrink-0 rounded bg-black/20 px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                      وزن: {safeWeight}٪
                    </span>
                  </div>

                  <p className="text-[10px] leading-relaxed text-muted-foreground">
                    {item.detail}
                  </p>

                  {item.reasons && item.reasons.length > 0 && (
                    <ul className="mt-1.5 space-y-1">
                      {item.reasons.map((reason, index) => (
                        <li
                          key={index}
                          className="flex items-start gap-1.5 text-[9.5px] text-foreground/60"
                        >
                          <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-current opacity-50" />
                          {reason}
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


    </div>
  );
}
