"use client";

/**
 * BacktestStats — آمار راستی‌آزمایی (نسخه ۹.۰ · فاز ۱۴.۹.۱۲)
 * ============================================================
 * 🔴 بازنویسی کامل:
 *   • حذف by-tf و by-quality (endpoint حذف شد)
 *   • فیلتر استراتژی + TF + پروفایل + منبع + بازه + نمایشی (۳۰/۱۰۰/همه)
 *   • ۲ نمودار دایره‌ای SVG (برد/باخت + پیش‌بینی)
 *   • جدول per-strategy
 *   • جدول تاریخچه حداقلی
 *   • استفاده از endpointهای جدید: /backtest, /backtest/history,
 *     /backtest/by-strategy, /backtest/run, /backtest/reset
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Clock,
  Download,
  Loader2,
  RefreshCw,
  Trash2,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { SignalHistoryItem } from "@/lib/types";
import { ResetSignalsDialog } from "./ResetSignalsDialog";

// ═══════════════════════════════════════════════════════════
// تایپ‌ها
// ═══════════════════════════════════════════════════════════

interface CoreStats {
  total: number;
  expired: number;
  tp_hits: number;
  sl_hits: number;
  timeout_wins: number;
  timeout_losses: number;
  timeout_flats: number;
  closed_real: number;
  tp1_ever_hit: number;
  win_rate: number;
  direction_accuracy: number;
  trend_correct: number;
  trend_wrong: number;
  trend_accuracy: number;
  pending?: number;
}

interface StrategyStats {
  total: number;
  tp1_ever_hit: number;
  tp_hits: number;
  sl_hits: number;
  timeout_wins: number;
  timeout_losses: number;
  win_rate: number;
  direction_accuracy: number;
  trend_correct: number;
  trend_wrong: number;
}

const TF_OPTIONS = ["", "۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"];
const STRATEGY_OPTIONS = [
  { v: "", label: "همه" },
  { v: "scalp", label: "اسکالپ" },
  { v: "swing", label: "سوئینگ" },
  { v: "position", label: "پوزیشن" },
];
const PROFILE_OPTIONS = [
  { v: "", label: "همه" },
  { v: "aggressive", label: "جسورانه" },
  { v: "conservative", label: "محتاطانه" },
];
const SOURCE_OPTIONS = [
  { v: "", label: "همه" },
  { v: "nobitex", label: "نوبیتکس" },
  { v: "bitpin", label: "بیت‌پین" },
  { v: "wallex", label: "والکس" },
  { v: "tabdeal", label: "تبدیل" },
];
const TIME_OPTIONS = [
  { v: "all", label: "همه" },
  { v: "1d", label: "۱ روز" },
  { v: "7d", label: "۷ روز" },
  { v: "30d", label: "۳۰ روز" },
];
const LIMIT_OPTIONS = [
  { v: 30, label: "۳۰ اخیر" },
  { v: 100, label: "۱۰۰ اخیر" },
  { v: 500, label: "همه" },
];

// ═══════════════════════════════════════════════════════════
// نمودار دایره‌ای SVG
// ═══════════════════════════════════════════════════════════

function DonutChart({
  value,
  size = 110,
  strokeWidth = 14,
  color = "#22c55e",
  bgColor = "rgba(255,255,255,0.06)",
  label,
}: {
  value: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  bgColor?: string;
  label?: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(100, value));
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={bgColor}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num text-xl font-bold" style={{ color }}>
          {pct.toFixed(0)}٪
        </span>
        {label && <span className="text-[9px] text-muted-foreground">{label}</span>}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// کامپوننت اصلی
// ═══════════════════════════════════════════════════════════

interface Props {
  source?: string;
  profile?: string;
  time?: string;
  limit?: number;
}

export function BacktestStats({
  source: initSource = "",
  profile: initProfile = "",
  time: initTime = "all",
  limit: initLimit = 100,
}: Props) {
  // فیلترها
  const [source, setSource] = useState(initSource);
  const [profile, setProfile] = useState(initProfile);
  const [time, setTime] = useState(initTime);
  const [strategy, setStrategy] = useState("");
  const [tf, setTf] = useState("");
  const [displayLimit, setDisplayLimit] = useState(initLimit);

  // داده
  const [stats, setStats] = useState<CoreStats | null>(null);
  const [byStrategy, setByStrategy] = useState<Record<string, StrategyStats>>({});
  const [items, setItems] = useState<SignalHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [running, setRunning] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // ═══ fetch ═══
  const fetchAll = useCallback(async () => {
    try {
      setError("");
      const params = new URLSearchParams();
      if (source) params.append("source", source);
      if (profile) params.append("risk_profile", profile);
      if (strategy) params.append("strategy", strategy);
      if (tf) params.append("tf", tf);
      if (time !== "all") params.append("time_filter", time);
      params.append("limit", String(Math.max(displayLimit, 50)));
      
      const historyParams = new URLSearchParams(params);
      historyParams.set("limit", "100");

      const [statsRes, stratRes, histRes] = await Promise.all([
        api.get<{ stats: CoreStats }>(`/backtest?${params.toString()}`),
        api.get<{ items: Record<string, StrategyStats> }>(
          `/backtest/by-strategy?${params.toString()}`
        ),
        api.get<{ items: SignalHistoryItem[] }>(
          `/backtest/history?${historyParams.toString()}`
        ),
      ]);

      setStats(statsRes.data.stats);
      setByStrategy(stratRes.data.items || {});
      setItems(histRes.data.items || []);
      setLoading(false);
    } catch {
      setError("دریافت آمار ناموفق بود");
      setLoading(false);
    }
  }, [source, profile, strategy, tf, time, displayLimit]);

  useEffect(() => {
    setLoading(true);
    fetchAll();
  }, [fetchAll]);

  // ═══ عملیات ═══
  const handleRun = async () => {
    setRunning(true);
    setNotice("");
    setError("");
    try {
      const res = await api.post("/backtest/run");
      const checked = res.data?.checked ?? 0;
      const updated = res.data?.updated ?? 0;
      setNotice(`${checked} سیگنال بررسی شد · ${updated} به‌روز شد`);
      await fetchAll();
    } catch {
      setError("اجرای راستی‌آزمایی ناموفق بود");
    } finally {
      setRunning(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    setError("");
    let url: string | null = null;
    try {
      const params = new URLSearchParams();
      if (source) params.append("source", source);
      if (profile) params.append("risk_profile", profile);
      if (strategy) params.append("strategy", strategy);
      if (tf) params.append("tf", tf);
      params.append("limit", "100");

      const res = await api.get(`/backtest/history?${params.toString()}`);
      const payload = JSON.stringify(res.data?.items ?? [], null, 2);
      const blob = new Blob([payload], { type: "application/json" });
      url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      const ts = new Intl.DateTimeFormat("en-GB", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Tehran",
      })
        .format(new Date())
        .replace(/[/:,\s]/g, "-")
        .replace(/-+/g, "-");

      a.download = `trademun_signals_${ts}.json`;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch {
      setError("دانلود ناموفق بود");
    } finally {
      if (url) URL.revokeObjectURL(url);
      setDownloading(false);
    }
  };

  const handleResetSuccess = (deleted: number) => {
    setNotice(`${deleted} سیگنال حذف شد`);
    setError("");
    fetchAll();
  };

  // ═══ محاسبات ═══
  const pendingCount = useMemo(
    () => items.filter((i) => !i.result && !i.expired).length,
    [items]
  );

  const closedCount = useMemo(
    () => items.filter((i) => i.result || i.expired).length,
    [items]
  );

  const lastCheckTime = useMemo(() => {
    const withResult = items
      .filter((i) => i.result_time)
      .sort(
        (a, b) =>
          new Date(b.result_time || "").getTime() -
          new Date(a.result_time || "").getTime()
      );
    return withResult[0]?.result_time || null;
  }, [items]);

  const formatDate = (iso: string | null | undefined) => {
    if (!iso) return "—";
    try {
      return new Intl.DateTimeFormat("fa-IR", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(iso));
    } catch {
      return "—";
    }
  };

  const formatNumber = (n: number | null | undefined) => {
    if (n === null || n === undefined) return "—";
    if (n >= 1000) return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
    return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
  };

  const resultBadge = (item: SignalHistoryItem) => {
    if (!item.result && !item.expired) {
      return { label: "در انتظار", color: "bg-blue-500/10 text-blue-400 border-blue-500/30", icon: "⏳" };
    }
    if (item.exit_reason === "tp_hit") {
      return { label: "برد (TP)", color: "bg-green-500/10 text-green-500 border-green-500/30", icon: "✅" };
    }
    if (item.exit_reason === "sl_hit") {
      return { label: "باخت (SL)", color: "bg-red-500/10 text-red-500 border-red-500/30", icon: "❌" };
    }
    if (item.exit_reason === "timeout") {
      if (item.expired_bias === "win") {
        return { label: "جهت درست", color: "bg-green-500/10 text-green-400 border-green-400/30", icon: "⏰" };
      }
      if (item.expired_bias === "loss") {
        return { label: "جهت غلط", color: "bg-orange-500/10 text-orange-400 border-orange-400/30", icon: "🟡" };
      }
      return { label: "خنثی", color: "bg-slate-500/10 text-slate-400 border-slate-400/30", icon: "⚪" };
    }
    return { label: "—", color: "bg-slate-500/10 text-slate-400 border-slate-400/30", icon: "" };
  };

  const winRateColor = (rate: number) =>
    rate >= 55 ? "text-green-500" : rate >= 45 ? "text-yellow-500" : "text-red-500";

  // ═══ رندر ═══
  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* هشدار/نوتیف */}
      {error && (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
          ⚠️ {error}
        </p>
      )}
      {notice && !error && (
        <p className="rounded-md border border-green-500/30 bg-green-500/5 p-2 text-[11px] text-green-500">
          ✅ {notice}
        </p>
      )}

      {/* راهنما */}
      <div className="rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[9px] leading-relaxed text-muted-foreground">
        💡 <b className="text-foreground/80">راهنما:</b> «نرخ برد» یعنی درصد سیگنال‌هایی که به TP1 رسیدن. «دقت پیش‌بینی» یعنی درصد دفعاتی که جهت بازار رو درست تشخیص دادیم (حتی اگه به TP نرسه).
      </div>

      {/* فیلتر نمایشی */}
      <div className="flex items-center justify-center gap-1">
        {LIMIT_OPTIONS.map((opt) => (
          <button
            key={opt.v}
            onClick={() => setDisplayLimit(opt.v)}
            className={`rounded-md px-2.5 py-1 text-[10px] font-medium transition ${
              displayLimit === opt.v
                ? "bg-primary text-primary-foreground"
                : "bg-muted/30 text-muted-foreground hover:bg-muted/50"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* فیلترهای پیشرفته */}
      <div>
        <button
          onClick={() => setShowFilters((v) => !v)}
          className="flex w-full items-center justify-between rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[10px] font-medium text-foreground/80"
        >
          <span>⚙️ فیلترها</span>
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform ${showFilters ? "rotate-180" : ""}`}
          />
        </button>
        {showFilters && (
          <div className="mt-1.5 grid grid-cols-2 gap-1.5">
            <FilterSelect label="استراتژی" value={strategy} onChange={setStrategy} options={STRATEGY_OPTIONS} />
            <FilterSelect label="تایم‌فریم" value={tf} onChange={setTf} options={TF_OPTIONS.map((v) => ({ v, label: v || "همه" }))} />
            <FilterSelect label="پروفایل" value={profile} onChange={setProfile} options={PROFILE_OPTIONS} />
            <FilterSelect label="منبع" value={source} onChange={setSource} options={SOURCE_OPTIONS} />
            <FilterSelect label="بازه" value={time} onChange={setTime} options={TIME_OPTIONS} />
          </div>
        )}
      </div>

      {/* ۵ کارت خلاصه */}
      {stats && (
        <div className="grid grid-cols-5 gap-1 text-center">
          <SummaryCard 
            label="کل" 
            value={(stats.tp_hits || 0) + (stats.sl_hits || 0) + (stats.timeout_wins || 0) + (stats.timeout_losses || 0) + (stats.pending || 0)} 
            color="text-foreground" 
            bg="bg-muted/10 border-border/40" 
          />
          <SummaryCard label="برد (TP)" value={stats.tp_hits} color="text-green-500" bg="bg-green-500/5 border-green-500/20" />
          <SummaryCard label="باخت (SL)" value={stats.sl_hits} color="text-red-500" bg="bg-red-500/5 border-red-500/20" />
          <SummaryCard label="در انتظار" value={stats.pending || 0} color="text-yellow-500" bg="bg-yellow-500/5 border-yellow-500/20" />
          <SummaryCard label="تایم‌اوت" value={stats.expired} color="text-blue-400" bg="bg-blue-500/5 border-blue-500/20" />
        </div>
      )}

      {/* ۲ نمودار دایره‌ای */}
      {stats && closedCount > 0 && (
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-2.5 text-center">
            <p className="mb-1 text-[10px] text-muted-foreground">✅ نرخ برد و باخت</p>
            <div className="flex items-center justify-center gap-2">
              <DonutChart
                value={stats.win_rate}
                color="#22c55e"
                label="برد"
              />
              <div className="space-y-1 text-right text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-muted-foreground">برد:</span>
                  <span className="num font-bold text-green-500">{stats.tp1_ever_hit}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-red-500" />
                  <span className="text-muted-foreground">باخت:</span>
                  <span className="num font-bold text-red-500">{stats.sl_hits}</span>
                </div>
              </div>
            </div>
          </div>
          <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2.5 text-center">
            <p className="mb-1 text-[10px] text-muted-foreground">🎯 دقت پیش‌بینی</p>
            <div className="flex items-center justify-center gap-2">
              <DonutChart
                value={stats.direction_accuracy}
                color="#a78bfa"
                label="درست"
              />
              <div className="space-y-1 text-right text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-purple-500" />
                  <span className="text-muted-foreground">درست:</span>
                  <span className="num font-bold text-purple-500">{stats.trend_correct}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-orange-500" />
                  <span className="text-muted-foreground">غلط:</span>
                  <span className="num font-bold text-orange-500">{stats.trend_wrong}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* مجموع سیگنال */}
      {stats && (
        <div className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-center">
          <span className="text-[10px] text-muted-foreground">📊 مجموع سیگنال‌های بررسی‌شده: </span>
          <span className="num text-sm font-bold text-foreground">{stats.total}</span>
        </div>
      )}

      {/* جدول per-strategy */}
      {Object.keys(byStrategy).length > 0 && (
        <div className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
          <p className="mb-2 text-[10px] font-medium text-muted-foreground">📈 به تفکیک استراتژی</p>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b border-border/40 text-muted-foreground">
                  <th className="pb-1 text-right font-normal">استراتژی</th>
                  <th className="pb-1 text-center font-normal">کل</th>
                  <th className="pb-1 text-center font-normal text-green-500">برد</th>
                  <th className="pb-1 text-center font-normal text-red-500">باخت</th>
                  <th className="pb-1 text-center font-normal text-purple-400">پیش‌بینی</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(byStrategy).map(([key, s]) => {
                  const label = key === "scalp" ? "اسکالپ" : key === "swing" ? "سوئینگ" : key === "position" ? "پوزیشن" : key;
                  return (
                    <tr key={key} className="border-b border-border/20 last:border-0">
                      <td className="py-1 font-medium">{label}</td>
                      <td className="num py-1 text-center text-muted-foreground">{s.total}</td>
                      <td className="num py-1 text-center font-bold text-green-500">{s.tp1_ever_hit}</td>
                      <td className="num py-1 text-center font-bold text-red-500">{s.sl_hits}</td>
                      <td className="num py-1 text-center font-bold text-purple-400">
                        {s.direction_accuracy.toFixed(0)}٪
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* تاریخچه (کشویی) */}
      {items.length > 0 && (
        <div>
          <button
            onClick={() => setShowHistory((v) => !v)}
            className="flex w-full items-center justify-between rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[10px] font-medium text-foreground/80"
          >
            <span>📋 تاریخچه سیگنال‌ها ({items.length})</span>
            <ChevronDown
              className={`h-3.5 w-3.5 transition-transform ${showHistory ? "rotate-180" : ""}`}
            />
          </button>
          {showHistory && (
            <div className="mt-1.5 overflow-x-auto rounded-md border border-border/40 bg-muted/5">
              <table className="w-full text-[9px]">
                <thead className="bg-muted/20">
                  <tr className="text-muted-foreground">
                    <th className="px-1.5 py-1 text-right font-normal">نماد</th>
                    <th className="px-1.5 py-1 text-center font-normal">استراتژی</th>
                    <th className="px-1.5 py-1 text-center font-normal">TF</th>
                    <th className="px-1.5 py-1 text-center font-normal">جهت</th>
                    <th className="px-1.5 py-1 text-center font-normal">اطمینان</th>
                    <th className="px-1.5 py-1 text-left font-normal">ورود</th>
                    <th className="px-1.5 py-1 text-left font-normal">خروج</th>
                    <th className="px-1.5 py-1 text-center font-normal">نتیجه</th>
                    <th className="px-1.5 py-1 text-center font-normal">تاریخ</th>
                  </tr>
                </thead>
                <tbody>
                  {items.slice(0, 100).map((it) => {
                    const badge = resultBadge(it);
                    const stratLabel = it.strategy === "scalp" ? "اسکالپ" : it.strategy === "position" ? "پوزیشن" : "سوئینگ";
                    return (
                      <tr key={it.id} className="border-t border-border/20">
                        <td className="px-1.5 py-1 text-right font-medium">{it.ticker}</td>
                        <td className="px-1.5 py-1 text-center text-muted-foreground">{stratLabel}</td>
                        <td className="px-1.5 py-1 text-center text-muted-foreground">{it.tf}</td>
                        <td className={`px-1.5 py-1 text-center font-medium ${it.direction === "long" ? "text-green-500" : it.direction === "short" ? "text-red-500" : "text-muted-foreground"}`}>
                          {it.direction === "long" ? "لانگ" : it.direction === "short" ? "شورت" : "—"}
                        </td>
                        <td className="num px-1.5 py-1 text-center text-muted-foreground">{it.confidence.toFixed(0)}٪</td>
                        <td className="num px-1.5 py-1 text-left text-muted-foreground">{formatNumber(it.price)}</td>
                        <td className="num px-1.5 py-1 text-left text-muted-foreground">{formatNumber(it.exit_price)}</td>
                        <td className="px-1.5 py-1 text-center">
                          <span className={`inline-block rounded px-1 py-0.5 text-[8px] border ${badge.color}`}>
                            {badge.icon} {badge.label}
                          </span>
                        </td>
                        <td className="px-1.5 py-1 text-center text-muted-foreground">{formatDate(it.timestamp)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* دکمه‌ها */}
      <div className="grid grid-cols-3 gap-2 pt-1">
        <Button onClick={handleRun} disabled={running} size="sm" variant="default">
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          بررسی
        </Button>
        <Button onClick={handleDownload} disabled={downloading} size="sm" variant="outline">
          {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
          دانلود JSON
        </Button>
        <Button onClick={() => setResetOpen(true)} size="sm" variant="outline" className="text-destructive hover:text-destructive">
          <Trash2 className="h-3.5 w-3.5" />
          ریست
        </Button>
      </div>

      <ResetSignalsDialog open={resetOpen} onOpenChange={setResetOpen} onSuccess={handleResetSuccess} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// کامپوننت‌های کمکی
// ═══════════════════════════════════════════════════════════

function SummaryCard({
  label,
  value,
  color,
  bg,
}: {
  label: string;
  value: number;
  color: string;
  bg: string;
}) {
  return (
    <div className={`rounded-md border ${bg} px-1 py-1.5`}>
      <p className="text-[8px] text-muted-foreground">{label}</p>
      <p className={`num text-sm font-bold ${color}`}>{value}</p>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { v: string; label: string }[];
}) {
  return (
    <label className="flex flex-col gap-0.5">
      <span className="text-[8px] text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-border/40 bg-background px-1.5 py-1 text-[10px] focus:outline-none focus:ring-1 focus:ring-primary"
      >
        {options.map((o) => (
          <option key={o.v} value={o.v}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}