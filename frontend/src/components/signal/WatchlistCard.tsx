"use client";

/**
 * WatchlistCard — واچ‌لیست (نسخه ۲.۰)
 * ============================================================
 * ═══ طراحی نسخه ۲.۰ ═══
 *
 * 🔴 مشکل قبلی:
 *   واچ‌لیست برای هر نماد، هر ۲۰ ثانیه یه درخواست
 *   ``/analyze/quote`` می‌زد. با ۱۰ نماد → **۳۰ req/min**
 *   فقط برای این کارت. خطر rate-limit.
 *
 * ✅ راه‌حل:
 *   واچ‌لیست هدفش **ذخیره‌ی نماد** برای دیدن تحلیل در زمان
 *   دیگه‌ست، نه مانیتور قیمت لحظه‌ای. قیمت زنده در
 *   ``SignalCard`` برای نماد **فعال** میاد.
 *
 *   ─── نتیجه ───
 *   ✅ صفر درخواست اضافه
 *   ✅ بدون rate-limit
 *   ✅ لود فوری
 *
 * ═══ UI جدید (نسخه ۲.۰) ═══
 *   • نوار بسته فشرده: «⭐ واچ‌لیست (۹)»
 *   • باز شده: چیپ‌های کوچیک کنار هم
 *   • هر چیپ: [نام ×] — کلیک روی نام → فعال‌سازی، × → حذف
 *
 * ═══ رفتار ═══
 *   • ``openOnDesktop`` → در دسکتاپ همیشه باز
 *   • در موبایل کشوی بسته، کاربر خودش باز می‌کنه
 */

import { Star, X } from "lucide-react";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { useAppStore } from "@/store/useAppStore";
import { SOURCE_BY_KEY } from "@/lib/sources";

export function WatchlistCard() {
  const {
    watchlist,
    removeFromWatchlist,
    setTicker,
    setSource,
    ticker: currentTicker,
  } = useAppStore();

  if (watchlist.length === 0) {
    return (
      <CollapsibleCard
        title="⭐ واچ‌لیست"
        subtitle="هنوز نمادی اضافه نکردی"
      >
        <p className="py-4 text-center text-[10px] text-muted-foreground">
          برای افزودن، روی ستاره‌ی هر نماد بزن
        </p>
      </CollapsibleCard>
    );
  }
  
  return (
    <CollapsibleCard
      title={
        <span className="flex items-center gap-1.5">
          <Star className="h-3.5 w-3.5 text-yellow-500" />
          واچ‌لیست
        </span>
      }
      badge={
        <span className="num rounded-full bg-yellow-500/15 px-1.5 text-[9px] text-yellow-500">
          {watchlist.length}
        </span>
      }
      subtitle="برای دیدن تحلیل، روی هر نماد بزن"
      keepCollapsibleOnDesktop
    >
      {/* ─── چیپ‌های کوچیک ─── */}
      <div className="flex flex-wrap gap-1">
        {watchlist.map((w) => {
          const meta = SOURCE_BY_KEY[w.source];
          const isCurrent = w.ticker === currentTicker;

          return (
            <div
              key={w.ticker}
              className={`group flex items-center gap-0.5 rounded-md border px-1.5 py-0.5 text-[10px] transition-colors ${
                isCurrent
                  ? "border-primary/40 bg-primary/10"
                  : "border-border bg-muted/20 hover:bg-muted/40"
              }`}
              title={`${w.name} — ${w.ticker}`}
            >
              {/* ─── نام (کلیک → فعال‌سازی) ─── */}
              <button
                onClick={() => {
                  setTicker(w.ticker, w.name);
                  setSource(w.source as never);
                }}
                className={`flex items-center gap-1 whitespace-nowrap ${
                  isCurrent ? "text-primary" : "text-foreground"
                }`}
              >
                <span className="text-[9px]">{meta?.icon ?? "•"}</span>
                <span className="font-medium">{w.name}</span>
              </button>

              {/* ─── حذف (×) ─── */}
              <button
                onClick={() => removeFromWatchlist(w.ticker)}
                className="ml-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-sm text-muted-foreground/60 transition-colors hover:bg-red-500/20 hover:text-red-500"
                aria-label={`حذف ${w.name}`}
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </div>
          );
        })}
      </div>
    </CollapsibleCard>
  );
}