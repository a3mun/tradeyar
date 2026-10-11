"use client";

/**
 * AccordionSection — بخش کشویی مدرن
 * ============================================================
 * نسخه ۱.۳ · فاز ۱۰.۵
 *
 * ═══ ویژگی‌ها ═══
 *   • روی موبایل: کشویی با Chevron باکس‌دار
 *   • روی دسکتاپ: همیشه باز (بدون کشو)
 *   • رفع nested button (Hydration Error)
 *   • Chevron باکس‌دار رنگ tone
 *   • Badge کنار تیتر
 *   • Actions جدا (دکمه تنظیمات)
 *   • Preview خط اول محتوا
 *
 * ═══ قوانین ═══
 *   • Badge/Actions بیرون دکمه اصلی (رفع nested button)
 *   • Chevron + Preview فقط روی موبایل
 *   • Content روی دسکتاپ همیشه نمایش داده می‌شه
 */

import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

interface Props {
  title: ReactNode;
  icon?: ReactNode;
  badge?: ReactNode;
  preview?: string;
  children: ReactNode;
  defaultOpen?: boolean;
  tone?: "primary" | "orange" | "purple" | "default";
  pulse?: boolean;
  actions?: ReactNode;
}

// ═══════════════════════════════════════════════════════════
// استایل‌های tone — هر tone رنگ خودشو داره
// ═══════════════════════════════════════════════════════════
const TONE_STYLES = {
  primary: {
    border: "border-primary/30",
    text: "text-primary",
    chevronBg: "bg-primary/10 border-primary/40 text-primary",
    chevronBgPulse: "border-primary/60 bg-primary/15 text-primary",
    pulseColor: "59, 130, 246", // آبی
  },
  orange: {
    border: "border-orange-500/30",
    text: "text-orange-400",
    chevronBg: "bg-orange-500/10 border-orange-500/40 text-orange-400",
    chevronBgPulse: "border-orange-500/60 bg-orange-500/15 text-orange-500",
    pulseColor: "249, 115, 22", // نارنجی
  },
  purple: {
    border: "border-purple-500/30",
    text: "text-purple-400",
    chevronBg: "bg-purple-500/10 border-purple-500/40 text-purple-400",
    chevronBgPulse: "border-purple-500/60 bg-purple-500/15 text-purple-400",
    pulseColor: "168, 85, 247", // بنفش
  },
  default: {
    border: "border-border/50",
    text: "text-foreground",
    chevronBg: "bg-muted/30 border-border text-muted-foreground",
    chevronBgPulse: "border-primary/40 bg-primary/10 text-primary",
    pulseColor: "59, 130, 246", // آبی
  },
} as const;

export function AccordionSection({
  title,
  icon,
  badge,
  preview,
  children,
  defaultOpen = false,
  tone = "primary",
  pulse = false,
  actions,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const styles = TONE_STYLES[tone];

  // ─── Chevron باکس‌دار ───
  const chevronCls = open
    ? "rotate-180 border-primary bg-primary/20 text-primary"
    : pulse
      ? styles.chevronBgPulse
      : styles.chevronBg;

  const chevronStyle =
    !open && pulse
      ? { animation: "chevron-pulse 1.5s ease-in-out infinite" }
      : undefined;

  return (
    <div
      className={`overflow-hidden rounded-lg border bg-card/50 transition-colors ${
        open ? styles.border : "border-border/50"
      }`}
    >
      {/* ═══ Pulse Animation — رنگ بر اساس tone ═══ */}
      {pulse && (
        <style jsx global>{`
          @keyframes chevron-pulse {
            0%,
            100% {
              box-shadow: 0 0 0 0 rgba(${styles.pulseColor}, 0.4);
            }
            50% {
              box-shadow: 0 0 0 6px rgba(${styles.pulseColor}, 0);
            }
          }
        `}</style>
      )}

      {/* ═══ Header ═══ */}
      <div className="flex w-full items-stretch">
        {/* ─── دکمه اصلی (بدون nested button) ─── */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="min-w-0 flex-1 px-3 py-2.5 text-right transition-colors hover:bg-muted/20 md:cursor-default md:hover:bg-transparent"
          aria-expanded={open}
        >
          <div className="flex items-center justify-between gap-2">
            {/* Right: icon + title + badge */}
            <div className="flex min-w-0 flex-1 items-center gap-2">
              {icon && (
                <span className={`shrink-0 ${styles.text}`}>{icon}</span>
              )}
              <span
                className={`truncate text-xs font-bold sm:text-sm ${styles.text}`}
              >
                {title}
              </span>
              {/* Badge کنار تیتر */}
              {badge && <span className="shrink-0">{badge}</span>}
            </div>

            {/* Left: chevron (فقط موبایل، باکس‌دار بزرگ) */}
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 transition-all duration-200 md:hidden ${chevronCls}`}
              style={chevronStyle}
              aria-hidden
            >
              <ChevronDown className="h-3.5 w-3.5" strokeWidth={2.5} />
            </span>
          </div>

          {/* Preview (فقط موبایل + بسته) */}
          {!open && preview && (
            <div className="relative mt-1.5 h-4 overflow-hidden md:hidden">
              <p className="truncate text-right text-[10px] leading-tight text-muted-foreground">
                {preview}
              </p>
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-2 bg-gradient-to-t from-card/50 to-transparent" />
            </div>
          )}
        </button>

        {/* ─── Actions (خارج از دکمه — رفع nested button) ─── */}
        {actions && (
          <div className="flex shrink-0 items-center px-2">{actions}</div>
        )}
      </div>

      {/* ═══ Content — موبایل: toggle | دسکتاپ: همیشه باز ═══ */}
      <div
        className={`border-t border-border/40 bg-background/30 px-3 py-3 ${
          open ? "block" : "hidden md:block"
        }`}
      >
        {children}
      </div>
    </div>
  );
}