"use client";

/**
 * EconomicCalendarPlaceholder — تقویم اقتصادی فارکس (نسخه ۱.۰ · فاز ۱۶.۱)
 * ============================================================
 * 🔴 هدف: جایگزین موقت تا زمان پیاده‌سازی API تقویم اقتصادی.
 */

import { CalendarDays, Clock, Construction } from "lucide-react";

export function EconomicCalendarPlaceholder() {
  return (
    <div className="relative overflow-hidden rounded-xl border border-dashed border-[#d6ad60]/30 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-4 sm:p-6">
      {/* بک‌گراند تزئینی */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute -top-10 -right-10 h-40 w-40 rounded-full bg-[#d6ad60] blur-3xl" />
        <div className="absolute -bottom-10 -left-10 h-40 w-40 rounded-full bg-[#60a5fa] blur-3xl" />
      </div>

      <div className="relative flex flex-col items-center text-center gap-3">
        {/* آیکون بزرگ */}
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#d6ad60]/10 border border-[#d6ad60]/30">
          <CalendarDays className="h-7 w-7 text-[#d6ad60]" />
        </div>

        {/* عنوان و تگ */}
        <div className="flex items-center gap-2 flex-wrap justify-center">
          <h3 className="text-base sm:text-lg font-bold text-foreground">
            تقویم اقتصادی فارکس
          </h3>
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-[10px] font-bold text-amber-400">
            <Clock className="h-3 w-3" />
            به زودی
          </span>
        </div>

        {/* توضیح */}
        <p className="max-w-md text-xs sm:text-sm text-muted-foreground leading-relaxed">
          به‌زودی می‌تونی از این بخش،{" "}
          <span className="text-[#d6ad60] font-bold">رویدادهای مهم اقتصادی</span>{" "}
          (مثل جلسات فدرال رزرو، آمار تورم، نرخ بیکاری و ...) رو ببینی و بفهمی کِی بازار نوسان بالایی داره.
        </p>

        {/* ویژگی‌های آینده */}
        <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2 w-full max-w-2xl">
          <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
            <Construction className="h-4 w-4 text-[#d6ad60] shrink-0" />
            <span className="text-[10px] sm:text-[11px] text-muted-foreground text-right">
              نمایش لحظه‌ای رویدادها
            </span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
            <Construction className="h-4 w-4 text-[#60a5fa] shrink-0" />
            <span className="text-[10px] sm:text-[11px] text-muted-foreground text-right">
              هشدار قبل از رویداد
            </span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
            <Construction className="h-4 w-4 text-[#22c55e] shrink-0" />
            <span className="text-[10px] sm:text-[11px] text-muted-foreground text-right">
              تأثیر روی نمادها
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}