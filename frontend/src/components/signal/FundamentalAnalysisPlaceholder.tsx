"use client";

import { Building2, Sparkles, TrendingUp, AlertCircle } from "lucide-react";

export function FundamentalAnalysisPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-white/5 px-4 py-8 text-center backdrop-blur-sm">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[#d6ad60]/10">
        <Building2 className="h-6 w-6 text-[#d6ad60]" />
      </div>
      <h3 className="mb-2 text-sm font-bold text-foreground">
        تحلیل بنیادین (فاندامنتال)
      </h3>
      <p className="mb-4 max-w-sm text-xs leading-relaxed text-muted-foreground">
        به زودی می‌توانید اخبار اقتصادی، صورت‌های مالی، شاخص‌های کلان و تحلیل بنیادین نمادها را در این بخش مشاهده کنید.
      </p>
      
      {/* نشانگرهای "به زودی" برای جذابیت بصری */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <span className="flex items-center gap-1 rounded-full border border-white/10 bg-[#051118] px-2.5 py-1 text-[9px] font-medium text-gray-400">
          <Sparkles className="h-3 w-3 text-yellow-500" /> اخبار اقتصادی
        </span>
        <span className="flex items-center gap-1 rounded-full border border-white/10 bg-[#051118] px-2.5 py-1 text-[9px] font-medium text-gray-400">
          <TrendingUp className="h-3 w-3 text-emerald-500" /> داده‌های کلان
        </span>
        <span className="flex items-center gap-1 rounded-full border border-white/10 bg-[#051118] px-2.5 py-1 text-[9px] font-medium text-gray-400">
          <AlertCircle className="h-3 w-3 text-red-500" /> تحلیل بنیادی
        </span>
      </div>
    </div>
  );
}