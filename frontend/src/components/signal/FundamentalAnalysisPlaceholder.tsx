
"use client";

import {
  Building2,
  Sparkles,
  Globe2,
  Coins,
  Landmark,
  ArrowUpRight,
  Clock3,
} from "lucide-react";

const features = [
  {
    icon: Globe2,
    title: "اقتصاد کلان",
    description: "تورم، اشتغال و سیاست بانک‌های مرکزی",
    color: "text-sky-400",
    bg: "bg-sky-400/10",
    border: "border-sky-400/15",
  },
  {
    icon: Coins,
    title: "بازار کالاها",
    description: "طلا، نقره، نفت و تغییرات قیمت جهانی",
    color: "text-amber-400",
    bg: "bg-amber-400/10",
    border: "border-amber-400/15",
  },
  {
    icon: Landmark,
    title: "سیاست پولی",
    description: "نرخ بهره و تصمیمات بانک‌های مرکزی",
    color: "text-violet-400",
    bg: "bg-violet-400/10",
    border: "border-violet-400/15",
  },
  {
    icon: Sparkles,
    title: "تحلیل اختصاصی نماد",
    description: "عوامل مثبت، منفی و سناریوهای بنیادی",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
    border: "border-emerald-400/15",
  },
];

export function FundamentalAnalysisPlaceholder() {
  return (
    <div
      dir="rtl"
      className="relative isolate overflow-hidden rounded-xl border border-[#d6ad60]/20 bg-gradient-to-br from-[#051118] via-[#071521] to-[#08111c] p-4 sm:p-5"
    >
      {/* Decorative background */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -right-16 -top-20 h-48 w-48 rounded-full bg-[#d6ad60]/[0.06] blur-3xl" />
        <div className="absolute -bottom-20 -left-12 h-40 w-40 rounded-full bg-sky-500/[0.05] blur-3xl" />
      </div>

      <div className="relative space-y-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
               
          </div>

          <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-[#d6ad60]/25 bg-[#d6ad60]/10 px-2.5 py-1.5 text-[10px] font-bold text-[#e5c47e]">
            <Clock3 className="h-3 w-3" />
            به‌زودی
          </span>
        </div>

        {/* Main description */}
        <div className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-3.5">
          <div className="mb-2 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-[#d6ad60]" />
            <span className="text-xs font-bold text-foreground">
              فراتر از نمودار و اندیکاتورها
            </span>
          </div>

          <p className="text-[11px] leading-7 text-muted-foreground">
            در این بخش، عوامل اقتصادی و اتفاقات بازارهای جهانی بررسی می‌شوند
            تا بتوانید شرایط بنیادی نماد انتخاب‌شده و دلایل احتمالی تغییرات
            آن را بهتر درک کنید.
          </p>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {features.map((feature) => {
            const Icon = feature.icon;

            return (
              <div
                key={feature.title}
                className="flex items-start gap-3 rounded-lg border border-white/[0.07] bg-white/[0.025] p-3 transition-colors hover:border-white/[0.12] hover:bg-white/[0.04]"
              >
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${feature.border} ${feature.bg}`}
                >
                  <Icon className={`h-4 w-4 ${feature.color}`} />
                </div>

                <div className="min-w-0">
                  <h4 className="text-[11px] font-bold text-foreground">
                    {feature.title}
                  </h4>
                  <p className="mt-1 text-[10px] leading-5 text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2 border-t border-white/[0.07] pt-3">
          <span className="text-[10px] text-muted-foreground">
            مستقل از تحلیل تکنیکال
          </span>

          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-[#d6ad60]">
            در حال توسعه
            <ArrowUpRight className="h-3 w-3" />
          </span>
        </div>
      </div>
    </div>
  );
}
