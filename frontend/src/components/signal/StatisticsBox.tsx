"use client";

import { useEffect, useMemo, useState } from "react";
import { BarChart3, RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";

// ═══════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════
type Summary = {
  total: number;
  tp1_hits: number;
  sl_hits: number;
  timeout_wins: number;
  timeout_losses: number;
  flat: number;
  success_rate: number;
};

type SiteStats = {
  real_total_signals: number;
  tp1_hits: number;
  tp_full_hits: number;
  sl_hits: number;
  timeout_wins: number;
  timeout_losses: number;
  timeout_flats: number;
  tp1_rate: number;
  real_win_rate: number;
  real_loss_rate: number;
  real_direction_accuracy: number;
  is_hidden?: boolean;
  has_override?: { win_rate: boolean; direction_accuracy: boolean; total_signals: boolean };
  by_timeframe: Record<string, Summary>;
  by_risk: Record<string, Summary>;
  by_confidence: Record<string, Summary>;
  by_strategy: Record<string, Summary>;
};

// ═══════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════
function pct(value: number | undefined): string {
  return `${Number(value || 0).toLocaleString("fa-IR", { maximumFractionDigits: 1 })}٪`;
}
function count(value: number | undefined): string {
  return Number(value || 0).toLocaleString("fa-IR");
}

// 🔴 رنگ‌بندی بر اساس درصد موفقیت
function getBarColor(rate: number) {
  if (rate < 20) return "bg-green-500/60";
  if (rate < 30) return "bg-green-500/70";
  if (rate < 40) return "bg-green-500/80";
  if (rate < 50) return "bg-green-500/90";
  return "bg-green-500";
}

// ═══════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════
function Breakdown({ title, rows, labels }: { title: string; rows: Record<string, Summary>; labels: Record<string, string>; }) {
  const entries = Object.entries(rows || {}).filter(([, v]) => v.total > 0);
  if (!entries.length) return null;

  return (
    <div className="rounded-lg border border-white/5 bg-black/20 p-2.5">
      <h4 className="mb-2 text-[10px] font-bold text-gray-300">{title}</h4>
      <div className="space-y-3">
        {entries.map(([key, item]) => {
          const rate = item.success_rate || 0;
          const barColor = getBarColor(rate);
          const wins = item.tp1_hits || 0;
          const losses = item.sl_hits || 0;
          const neutrals = (item.timeout_wins || 0) + (item.timeout_losses || 0) + (item.flat || 0);

          return (
            <div key={key} className="space-y-1">
              <div className="flex items-center justify-between gap-2 text-[9px]">
                <span className="text-gray-400">{labels[key] || key}</span>
                <span className="num font-bold text-gray-200">{pct(rate)}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
                <div className={`h-full rounded-full ${barColor}`} style={{ width: `${rate}%` }} />
              </div>
              <p className="text-[8px] text-gray-500 flex gap-1.5">
                <span className="text-green-500/80">برد {count(wins)}</span>
                <span>·</span>
                <span className="text-red-500/80">باخت {count(losses)}</span>
                <span>·</span>
                <span className="text-gray-400">خنثی {count(neutrals)}</span>
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════
export function StatisticsBox() {
  const [limit, setLimit] = useState(100);
  const [stats, setStats] = useState<SiteStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    const params = new URLSearchParams({ time_filter: "all", limit: String(limit) });

    api.get<SiteStats & { ok: boolean }>(`/backtest/site-stats?${params.toString()}`)
      .then((res) => {
        if (!cancelled) setStats(res.data);
      })
      .catch(() => {
        if (!cancelled) {
          setStats(null);
          setError(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [limit]);

  const byTfLabels = useMemo(() => Object.fromEntries([
    { value: "۱ دقیقه", label: "۱ دقیقه" },
    { value: "۵ دقیقه", label: "۵ دقیقه" },
    { value: "۱۵ دقیقه", label: "۱۵ دقیقه" },
    { value: "۳۰ دقیقه", label: "۳۰ دقیقه" },
    { value: "۱ ساعت", label: "۱ ساعت" },
    { value: "روزانه", label: "روزانه" },
  ].map((x) => [x.value, x.label])), []);
  
  const byRiskLabels = { aggressive: "جسورانه", conservative: "محتاطانه", نامشخص: "نامشخص" };
  const byConfidenceLabels = { lt40: "کمتر از ۴۰٪", "40_49": "۴۰ تا ۴۹٪", "50_59": "۵۰ تا ۵۹٪", "60_69": "۶۰ تا ۶۹٪", "70p": "۷۰٪ به بالا" };
  const byStrategyLabels = { scalp: "اسکالپ", swing: "سوئینگ", position: "پوزیشن" };

  if (loading) {
    return (
      <section className="flex h-48 items-center justify-center rounded-xl border border-white/5 bg-[#051118]">
        <RefreshCw className="h-5 w-5 animate-spin text-[#d6ad60]" />
      </section>
    );
  }

  if (error || !stats) {
    return (
      <section className="flex h-48 items-center justify-center rounded-xl border border-white/5 bg-[#051118] text-[10px] text-red-400">
        دریافت آمار ممکن نشد.
      </section>
    );
  }

  // 🔴 اگر آمار مخفی شده باشد
  if (stats.is_hidden) {
    return (
      <section className="flex flex-col items-center justify-center rounded-xl border border-amber-500/20 bg-amber-500/5 p-8 text-center">
        <ShieldAlert className="h-8 w-8 text-amber-500 mb-3" />
        <p className="text-sm font-bold text-amber-400">در حال بررسی داده‌های راستی‌آزمایی</p>
        <p className="mt-1 text-[10px] text-muted-foreground">به‌زودی آمار دقیق در این بخش نمایش داده می‌شود.</p>
      </section>
    );
  }

  const totalSignals = stats.real_total_signals || 1;
  const closedSignals = stats.tp1_hits + stats.sl_hits;
  const winRateAll = (stats.tp1_hits / totalSignals) * 100;
  const winRateClosed = closedSignals > 0 ? (stats.tp1_hits / closedSignals) * 100 : 0;

  return (
    <section className="space-y-3 rounded-xl border border-white/5 bg-[#051118] p-3 sm:p-4">
      
      {/* هدر */}
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-gray-100 flex items-center gap-1.5">
            <BarChart3 className="h-4 w-4 text-[#d6ad60]" /> عملکرد سیگنال‌ها
          </h3>
          <p className="mt-0.5 text-[9px] text-gray-500">معیار اصلی: لمس TP1 (اولین هدف)</p>
        </div>
      </div>

      {/* فیلتر تعداد سیگنال */}
      <div className="grid grid-cols-3 gap-1 rounded-lg bg-black/20 p-1">
        {[{ v: 50, label: "۵۰ سیگنال اخیر" }, { v: 100, label: "۱۰۰ سیگنال اخیر" }, { v: 200, label: "۲۰۰ سیگنال اخیر" }].map((x) => (
          <button
            key={x.v}
            type="button"
            onClick={() => setLimit(x.v)}
            className={`rounded-md px-2 py-2 text-[10px] transition ${
              limit === x.v ? "bg-[#d6ad60]/15 font-bold text-[#d6ad60]" : "text-gray-400 hover:bg-white/5"
            }`}
          >
            {x.label}
          </button>
        ))}
      </div>

      {/* کارت‌های اصلی */}
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-lg border border-white/5 bg-black/20 p-2.5 text-center">
          <p className="text-[9px] text-gray-500 mb-1">نرخ برد (کل)</p>
          <p className="num text-lg font-bold text-green-400">{pct(winRateAll)}</p>
          <p className="mt-0.5 text-[8px] text-gray-500">{count(stats.tp1_hits)} از {count(totalSignals)}</p>
        </div>
        <div className="rounded-lg border border-white/5 bg-black/20 p-2.5 text-center">
          <p className="text-[9px] text-gray-500 mb-1">نرخ برد (بدون تایم‌اوت)</p>
          <p className="num text-lg font-bold text-emerald-400">{pct(winRateClosed)}</p>
          <p className="mt-0.5 text-[8px] text-gray-500">{count(stats.tp1_hits)} از {count(closedSignals)} قطعی</p>
        </div>
        <div className="rounded-lg border border-white/5 bg-black/20 p-2.5 text-center">
          <p className="text-[9px] text-gray-500 mb-1">دقت پیش‌بینی روند</p>
          <p className="num text-lg font-bold text-blue-400">{pct(stats.real_direction_accuracy)}</p>
          <p className="mt-0.5 text-[8px] text-gray-500">جهت درست</p>
        </div>
      </div>

      {/* ۴ بخش نمودار میله‌ای */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <Breakdown title="⏱️ بر اساس تایم‌فریم" rows={stats.by_timeframe || {}} labels={byTfLabels} />
        <Breakdown title="🛡️ بر اساس ریسک" rows={stats.by_risk || {}} labels={byRiskLabels} />
        <Breakdown title="🎯 بر اساس درصد اطمینان" rows={stats.by_confidence || {}} labels={byConfidenceLabels} />
        <Breakdown title="📈 بر اساس استراتژی" rows={stats.by_strategy || {}} labels={byStrategyLabels} />
      </div>

      <p className="text-[8px] leading-relaxed text-gray-500 text-center pt-1 border-t border-white/5 mt-2">
        آمار بر اساس {limit} سیگنال بسته‌شده اخیر محاسبه شده است. «خنثی» شامل سیگنال‌هایی است که در تایم‌فریم مشخص به TP یا SL نرسیده‌اند.
      </p>
    </section>
  );
}