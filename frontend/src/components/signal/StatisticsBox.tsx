"use client";

/**
 * StatisticsBox — آمار عملکرد (نسخه ۱.۰ · فاز ۱۴.۹.۶)
 * ============================================================
 * جایگزین BacktestPanel در صفحه اصلی.
 * فقط خلاصه‌ی آمار (نه تاریخچه کامل).
 */

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

interface QuickStats {
  total: number;
  win_rate: number;
  tp_hit_rate: number;
  avg_rr_net: number;
}

export function StatisticsBox() {
  const { source, riskProfile } = useAppStore();
  const [stats, setStats] = useState<QuickStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Lazy fetch — بعد از mount (که CollapsibleSection فقط وقتی باز شد انجام می‌ده)
    setLoading(true);
    const params = new URLSearchParams();
    if (source) params.append("source", source);
    if (riskProfile) params.append("risk_profile", riskProfile);
    params.append("time_filter", "all");
    params.append("limit", "500");

    api
      .get<{ stats: QuickStats }>(`/backtest?${params.toString()}`)
      .then((res) => setStats(res.data.stats))
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, [source, riskProfile]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!stats || stats.total === 0) {
    return (
      <div className="py-6 text-center text-[11px] text-muted-foreground">
        هنوز سیگنالی برای آمارگیری ثبت نشده
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded-lg border border-border/40 bg-muted/20 px-2 py-2 text-center">
          <div className="text-[9px] text-muted-foreground">کل</div>
          <div className="num mt-0.5 text-base font-bold">{stats.total}</div>
          <div className="text-[8px] text-muted-foreground/70">سیگنال</div>
        </div>

        <div className="rounded-lg border border-green-500/20 bg-green-500/5 px-2 py-2 text-center">
          <div className="text-[9px] text-green-400">برد</div>
          <div className="num mt-0.5 text-base font-bold text-green-400">
            {stats.win_rate.toFixed(0)}٪
          </div>
          <div className="text-[8px] text-green-500/60">win rate</div>
        </div>

        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-2 py-2 text-center">
          <div className="text-[9px] text-blue-400">TP</div>
          <div className="num mt-0.5 text-base font-bold text-blue-400">
            {stats.tp_hit_rate.toFixed(0)}٪
          </div>
          <div className="text-[8px] text-blue-500/60">hit rate</div>
        </div>

        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-2 py-2 text-center">
          <div className="text-[9px] text-amber-400">R:R</div>
          <div className="num mt-0.5 text-base font-bold text-amber-400">
            {stats.avg_rr_net.toFixed(2)}
          </div>
          <div className="text-[8px] text-amber-500/60">خالص</div>
        </div>
      </div>

      <p className="rounded-md bg-muted/20 px-2 py-1.5 text-[9px] text-muted-foreground leading-relaxed">
        📊 آمار کل (فیلتر نشده). برای جزئیات و تاریخچه، به پنل مدیر برو.
      </p>
    </div>
  );
}