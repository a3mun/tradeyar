"use client";

/**
 * PositionSizeCalculatorPlaceholder — ماشین‌حساب سود/ضرر (نسخه ۱.۰ · فاز ۱۶.۱)
 * ============================================================
 * 🔴 هدف: جایگزین موقت تا زمان پیاده‌سازی ماشین‌حساب واقعی.
 */

import { Calculator, Clock, TrendingUp, ShieldCheck, Wallet } from "lucide-react";

export function PositionSizeCalculatorPlaceholder() {
  return (
    <div className="relative overflow-hidden rounded-xl border border-dashed border-[#a78bfa]/30 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-4 sm:p-6">
      {/* بک‌گراند تزئینی */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute -top-10 -left-10 h-40 w-40 rounded-full bg-[#a78bfa] blur-3xl" />
        <div className="absolute -bottom-10 -right-10 h-40 w-40 rounded-full bg-[#22c55e] blur-3xl" />
      </div>

      <div className="relative flex flex-col items-center text-center gap-3">
        {/* آیکون بزرگ */}
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#a78bfa]/10 border border-[#a78bfa]/30">
          <Calculator className="h-7 w-7 text-[#a78bfa]" />
        </div>

        {/* عنوان و تگ */}
        <div className="flex items-center gap-2 flex-wrap justify-center">
          <h3 className="text-base sm:text-lg font-bold text-foreground">
            ماشین‌حساب سود و ضرر
          </h3>
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-[10px] font-bold text-amber-400">
            <Clock className="h-3 w-3" />
            به زودی
          </span>
        </div>

        {/* توضیح */}
        <p className="max-w-md text-xs sm:text-sm text-muted-foreground leading-relaxed">
          به‌زودی با وارد کردن{" "}
          <span className="text-[#a78bfa] font-bold">سرمایه، درصد ریسک، قیمت ورود و حد ضرر</span>{" "}
          می‌تونی حجم دقیق پوزیشن و سود/ضرر احتمالی رو محاسبه کنی.
        </p>

        {/* ویژگی‌های آینده */}
        <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2 w-full max-w-2xl">
          <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
            <Wallet className="h-4 w-4 text-[#a78bfa] shrink-0" />
            <span className="text-[10px] sm:text-[11px] text-muted-foreground text-right">
              حجم دقیق پوزیشن
            </span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
            <TrendingUp className="h-4 w-4 text-[#22c55e] shrink-0" />
            <span className="text-[10px] sm:text-[11px] text-muted-foreground text-right">
              سود بالقوه
            </span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
            <ShieldCheck className="h-4 w-4 text-[#f59e0b] shrink-0" />
            <span className="text-[10px] sm:text-[11px] text-muted-foreground text-right">
              مدیریت ریسک
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}