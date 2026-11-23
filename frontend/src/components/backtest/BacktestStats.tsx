"use client";

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
  total_wins: number;
  win_rate: number;
  loss_rate: number;
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
  loss_rate: number;
  direction_accuracy: number;
  trend_correct: number;
  trend_wrong: number;
}

interface TfStats {
  total: number;
  tp_hits: number;
  sl_hits: number;
  timeout_wins: number;
  timeout_losses: number;
  win_rate: number;
  loss_rate: number;
  direction_accuracy: number;
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
  { v: 50, label: "۵۰ اخیر" },
  { v: 100, label: "۱۰۰ اخیر" },
  { v: 200, label: "۲۰۰ اخیر" },
];


type AnalyticsOutcome = "tp" | "sl" | "timeout_win" | "timeout_loss" | "flat" | "pending";
interface AnalyticsSignal {
  confidence?: number | null;
  direction?: string | null;
  source?: string | null;
  tf?: string | null;
  result?: string | null;
  exit_reason?: string | null;
  expired?: boolean | null;
  expired_bias?: string | null;
  expired_pnl_pct?: number | null;
  tp_hit_level?: number | null;
}

const TF_ORDER = ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"];
const TF_ORDER_INDEX = new Map(TF_ORDER.map((value, index) => [value, index]));

function classifyOutcome(item: AnalyticsSignal): AnalyticsOutcome {
  if (item.exit_reason === "tp_hit" || item.exit_reason === "tp1_hit" || item.result === "win") return "tp";
  if (item.exit_reason === "sl_hit" || item.result === "loss") return "sl";
  if (item.expired_bias === "win") return "timeout_win";
  if (item.expired_bias === "loss") return "timeout_loss";
  if (item.expired_bias === "flat") return "flat";
  return "pending";
}

function pct(numerator: number, denominator: number): number {
  return denominator > 0 ? (numerator / denominator) * 100 : 0;
}

function MetricCard({ label, value, detail, tone = "neutral" }: {
  label: string; value: string | number; detail?: string; tone?: "neutral" | "good" | "bad" | "gold" | "info";
}) {
  const tones = {
    neutral: "border-border/40 bg-muted/10 text-foreground",
    good: "border-emerald-500/20 bg-emerald-500/5 text-emerald-400",
    bad: "border-rose-500/20 bg-rose-500/5 text-rose-400",
    gold: "border-amber-500/20 bg-amber-500/5 text-amber-300",
    info: "border-sky-500/20 bg-sky-500/5 text-sky-300",
  };
  return (
    <div className={`rounded-lg border p-2.5 ${tones[tone]}`}>
      <p className="text-[9px] text-muted-foreground">{label}</p>
      <p className="num mt-1 text-base font-bold">{value}</p>
      {detail && <p className="mt-0.5 text-[8px] leading-relaxed text-muted-foreground">{detail}</p>}
    </div>
  );
}

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
        <circle cx={size / 2} cy={size / 2} r={radius} stroke={bgColor} strokeWidth={strokeWidth} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={radius} stroke={color} strokeWidth={strokeWidth} fill="none"
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num text-xl font-bold" style={{ color }}>{pct.toFixed(1)}٪</span>
        {label && <span className="text-[9px] text-muted-foreground">{label}</span>}
      </div>
    </div>
  );
}

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
  limit: initLimit = 200,
}: Props) {
  const [source, setSource] = useState(initSource);
  const [profile, setProfile] = useState(initProfile);
  const [time, setTime] = useState(initTime);
  const [strategy, setStrategy] = useState("");
  const [tf, setTf] = useState("");
  const [outcomeFilter, setOutcomeFilter] = useState("all");
  const [displayLimit, setDisplayLimit] = useState(initLimit);

  const [stats, setStats] = useState<CoreStats | null>(null);
  const [byStrategy, setByStrategy] = useState<Record<string, StrategyStats>>({});
  const [byTf, setByTf] = useState<Record<string, TfStats>>({}); // 🔴 فاز ۱۶.۹
  const [items, setItems] = useState<SignalHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [running, setRunning] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

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
      historyParams.set("limit", String(Math.max(displayLimit, 50)));

      const tfParams = new URLSearchParams(params);
      if (source) tfParams.set("source", source);
      if (profile) tfParams.set("risk_profile", profile);
      if (strategy) tfParams.set("strategy", strategy);
      if (time !== "all") tfParams.set("time_filter", time);
      tfParams.set("limit", String(Math.max(displayLimit, 50)));
      tfParams.delete("tf"); // 🔴 برای by-tf نیاز به فیلتر tf نداریم

      const [statsRes, stratRes, tfRes, histRes] = await Promise.all([
        api.get<{ stats: CoreStats }>(`/backtest?${params.toString()}`),
        api.get<{ items: Record<string, StrategyStats> }>(`/backtest/by-strategy?${params.toString()}`),
        api.get<{ items: Record<string, TfStats> }>(`/backtest/by-tf?${tfParams.toString()}`), // 🔴 جدید
        api.get<{ items: SignalHistoryItem[] }>(`/backtest/history?${historyParams.toString()}`),
      ]);

      setStats(statsRes.data.stats);
      setByStrategy(stratRes.data.items || {});
      setByTf(tfRes.data.items || {}); // 🔴 جدید
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
      params.append("limit", "200");

      const res = await api.get(`/backtest/history?${params.toString()}`);
      const payload = JSON.stringify(res.data?.items ?? [], null, 2);
      const blob = new Blob([payload], { type: "application/json" });
      url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      const ts = new Intl.DateTimeFormat("en-GB", {
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Tehran",
      }).format(new Date()).replace(/[/:,\s]/g, "-").replace(/-+/g, "-");

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

  const pendingCount = useMemo(() => items.filter((i) => !i.result && !i.expired).length, [items]);
  const closedCount = useMemo(() => items.filter((i) => i.result || i.expired).length, [items]);

  const filteredItems = useMemo(() => {
    if (outcomeFilter === "all") return items;
    return items.filter((item) => {
      const row = item as SignalHistoryItem & { tp_hit_level?: number };
      const reason = String(row.exit_reason ?? "").trim().toLowerCase();
      const hitLevel = Number(row.tp_hit_level ?? 0);
      if (outcomeFilter === "tp1") return reason === "tp1_hit" || hitLevel === 1;
      if (outcomeFilter === "tp_full") return reason === "tp_hit" || hitLevel >= 3;
      if (outcomeFilter === "sl") return reason === "sl_hit" || item.result === "loss";
      if (outcomeFilter === "timeout") return reason === "timeout" || item.expired;
      if (outcomeFilter === "pending") return !item.result && !item.expired;
      return true;
    });
  }, [items, outcomeFilter]);

  const analytics = useMemo(() => {
    const rows = filteredItems as unknown as AnalyticsSignal[];
    const counts: Record<AnalyticsOutcome, number> = {
      tp: 0, sl: 0, timeout_win: 0, timeout_loss: 0, flat: 0, pending: 0,
    };
    rows.forEach((item) => { counts[classifyOutcome(item)] += 1; });
    const closed = rows.length - counts.pending;
    const tp1OnlyCount = rows.filter((item) => item.exit_reason === "tp1_hit" || (item.tp_hit_level ?? 0) === 1).length;
    const tpFullCount = rows.filter((item) => item.exit_reason === "tp_hit" || (item.tp_hit_level ?? 0) >= 3).length;
    const decisive = counts.tp + counts.sl + counts.timeout_win + counts.timeout_loss;
    const directionWins = counts.tp + counts.timeout_win;
    const tpSlOnly = counts.tp + counts.sl;
    const timeoutPnls = rows
      .filter((item) => item.exit_reason === "timeout" && typeof item.expired_pnl_pct === "number")
      .map((item) => item.expired_pnl_pct as number)
      .sort((a, b) => a - b);
    const medianPnl = timeoutPnls.length
      ? (timeoutPnls.length % 2
          ? timeoutPnls[Math.floor(timeoutPnls.length / 2)]
          : (timeoutPnls[timeoutPnls.length / 2 - 1] + timeoutPnls[timeoutPnls.length / 2]) / 2)
      : null;
    const buckets = [
      { key: "کمتر از ۴۰", test: (v: number) => v < 40 },
      { key: "۴۰ تا ۴۹", test: (v: number) => v >= 40 && v < 50 },
      { key: "۵۰ تا ۵۹", test: (v: number) => v >= 50 && v < 60 },
      { key: "۶۰ تا ۶۹", test: (v: number) => v >= 60 && v < 70 },
      { key: "۷۰ به بالا", test: (v: number) => v >= 70 },
    ].map((bucket) => {
      const subset = rows.filter((item) => bucket.test(Number(item.confidence ?? 0)));
      const c = { tp: 0, sl: 0, timeout_win: 0, timeout_loss: 0, flat: 0, pending: 0 };
      subset.forEach((item) => { c[classifyOutcome(item)] += 1; });
      const denominator = c.tp + c.sl + c.timeout_win + c.timeout_loss;
      return { ...bucket, total: subset.length, ...c, success: pct(c.tp + c.timeout_win, denominator), denominator };
    });
    const groupBy = (key: "direction" | "source") => {
      const groups = new Map<string, AnalyticsSignal[]>();
      rows.forEach((item) => {
        const value = String(item[key] || "نامشخص");
        groups.set(value, [...(groups.get(value) || []), item]);
      });
      return [...groups.entries()].map(([name, subset]) => {
        const c = { tp: 0, sl: 0, timeout_win: 0, timeout_loss: 0, flat: 0, pending: 0 };
        subset.forEach((item) => { c[classifyOutcome(item)] += 1; });
        const denominator = c.tp + c.sl + c.timeout_win + c.timeout_loss;
        return { name, total: subset.length, ...c, success: pct(c.tp + c.timeout_win, denominator), denominator };
      }).sort((a, b) => b.total - a.total);
    };
    return {
      counts, closed, decisive, directionWins, tpSlOnly, tp1OnlyCount, tpFullCount,
      targetRate: pct(counts.tp, closed),
      directionalRate: pct(directionWins, decisive),
      tpSlRate: pct(counts.tp, tpSlOnly),
      timeoutMean: timeoutPnls.length ? timeoutPnls.reduce((sum, value) => sum + value, 0) / timeoutPnls.length : null,
      timeoutMedian: medianPnl,
      timeoutPnlCount: timeoutPnls.length,
      confidence: buckets,
      directions: groupBy("direction"),
      sources: groupBy("source"),
    };
  }, [filteredItems]);

  const formatDate = (iso: string | null | undefined) => {
    if (!iso) return "—";
    try {
      return new Intl.DateTimeFormat("fa-IR", {
        month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
      }).format(new Date(iso));
    } catch { return "—"; }
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
    const exitReason = String(item.exit_reason ?? "").trim().toLowerCase();
    const tpLevel = Number((item as SignalHistoryItem & { tp_hit_level?: number }).tp_hit_level ?? 0);
    if (exitReason === "tp_hit" || tpLevel >= 3) {
      return { label: "هدف کامل (TP)", color: "bg-green-500/10 text-green-500 border-green-500/30", icon: "✅" };
    }
    if (exitReason === "tp1_hit" || tpLevel === 1) {
      return { label: "هدف اول (TP1)", color: "bg-green-500/10 text-green-500 border-green-500/30", icon: "✅" };
    }
    if (item.result === "win") {
      return { label: "برد ثبت‌شده (سطح هدف نامشخص)", color: "bg-green-500/10 text-green-500 border-green-500/30", icon: "✅" };
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

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
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

      <div className="rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[9px] leading-relaxed text-muted-foreground">
        💡 <b className="text-foreground/80">راهنما:</b> «موفقیت هدف» شامل لمس TP1 یا TP کامل است؛ تعداد TP1 و TP کامل جداگانه نمایش داده می‌شود. «دقت پیش‌بینی» شامل سیگنال‌هایی است که جهت بازار را درست تشخیص داده‌اند (حتی اگر به TP نرسند).
      </div>

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

      <div>
        <button
          onClick={() => setShowFilters((v) => !v)}
          className="flex w-full items-center justify-between rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[10px] font-medium text-foreground/80"
        >
          <span>⚙️ فیلترها</span>
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showFilters ? "rotate-180" : ""}`} />
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

      {stats && closedCount > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {/* نمودار نرخ برد (فقط TP) */}
          <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-2.5 text-center">
            <p className="mb-1 text-[10px] text-muted-foreground">✅ نرخ برد (TP)</p>
            <div className="flex items-center justify-center gap-2">
              <DonutChart value={stats.win_rate} color="#22c55e" label="برد" />
              <div className="space-y-1 text-right text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-muted-foreground">تعداد:</span>
                  <span className="num font-bold text-green-500">{stats.tp_hits}</span>
                </div>
              </div>
            </div>
          </div>
          {/* نمودار دقت پیش‌بینی */}
          <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2.5 text-center">
            <p className="mb-1 text-[10px] text-muted-foreground">🎯 دقت پیش‌بینی</p>
            <div className="flex items-center justify-center gap-2">
              <DonutChart value={stats.direction_accuracy} color="#a78bfa" label="درست" />
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

      {stats && (
        <div className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-center">
          <span className="text-[10px] text-muted-foreground">📊 مجموع سیگنال‌های بررسی‌شده: </span>
          <span className="num text-sm font-bold text-foreground">{stats.total}</span>
        </div>
      )}


      {items.length > 0 && (
        <section className="space-y-2 rounded-xl border border-border/50 bg-card/40 p-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h3 className="text-xs font-semibold text-foreground">تحلیل آماری پیشرفته</h3>
              <p className="text-[9px] text-muted-foreground">محاسبه‌شده از {items.length} رکورد تاریخچه دریافت‌شده با فیلترهای فعلی</p>
            </div>
            <span className="rounded-md border border-primary/20 bg-primary/5 px-2 py-1 text-[8px] text-primary">نمونه فعلی</span>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/30 bg-muted/10 p-2">
            <span className="text-[9px] text-muted-foreground">فیلتر نوع نتیجه برای تحلیل و تاریخچه</span>
            <select value={outcomeFilter} onChange={(e) => setOutcomeFilter(e.target.value)} className="h-7 rounded-md border border-border bg-background px-2 text-[9px]">
              <option value="all">همه نتایج</option>
              <option value="tp1">فقط TP1</option>
              <option value="tp_full">فقط TP کامل</option>
              <option value="sl">فقط SL</option>
              <option value="timeout">فقط Timeout</option>
              <option value="pending">در انتظار</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <MetricCard label="موفقیت جهت در خروج‌های قطعی" value={`${analytics.directionalRate.toFixed(1)}٪`} detail={`${analytics.directionWins} موفق از ${analytics.decisive} نتیجه جهت‌دار`} tone="gold" />
            <MetricCard label="رسیدن به TP1 یا TP" value={`${analytics.targetRate.toFixed(1)}٪`} detail={`${analytics.counts.tp} از ${analytics.closed} خروج‌بسته`} tone="good" />
            <MetricCard label="برد در TP/SL فقط" value={`${analytics.tpSlRate.toFixed(1)}٪`} detail={`${analytics.counts.tp} برد از ${analytics.tpSlOnly} خروج TP/SL؛ تایم‌اوت حذف شده`} tone="info" />
            <MetricCard label="نتایج خنثی" value={analytics.counts.flat} detail={`از ${analytics.closed} خروج‌بسته`} />
          </div>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            <MetricCard label="فقط TP1" value={analytics.tp1OnlyCount} detail="هدف اول لمس شده" tone="good" />
            <MetricCard label="TP کامل" value={analytics.tpFullCount} detail="هدف نهایی لمس شده" tone="good" />
            <MetricCard label="حد ضرر (SL)" value={analytics.counts.sl} detail="خروج با حد ضرر" tone="bad" />
            <MetricCard label="تایم‌اوت؛ جهت درست" value={analytics.counts.timeout_win} detail="بدون رسیدن به هدف، جهت نهایی درست" tone="good" />
            <MetricCard label="تایم‌اوت؛ جهت غلط" value={analytics.counts.timeout_loss} detail="بدون رسیدن به هدف، جهت نهایی غلط" tone="bad" />
          </div>

          <div className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
            <p className="mb-1 text-[10px] font-medium text-foreground">بازده ثبت‌شده در خروج‌های تایم‌اوت</p>
            <div className="grid grid-cols-2 gap-2 text-[10px] sm:grid-cols-3">
              <div><span className="text-muted-foreground">میانگین PnL:</span> <b className={`num ${analytics.timeoutMean !== null && analytics.timeoutMean >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{analytics.timeoutMean === null ? "—" : `${analytics.timeoutMean.toFixed(3)}٪`}</b></div>
              <div><span className="text-muted-foreground">میانه PnL:</span> <b className={`num ${analytics.timeoutMedian !== null && analytics.timeoutMedian >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{analytics.timeoutMedian === null ? "—" : `${analytics.timeoutMedian.toFixed(3)}٪`}</b></div>
              <div><span className="text-muted-foreground">نمونه PnL:</span> <b className="num">{analytics.timeoutPnlCount}</b></div>
            </div>
            <p className="mt-1 text-[8px] leading-relaxed text-muted-foreground">این PnL فقط برای رکوردهای تایم‌اوتی است که مقدار expired_pnl_pct دارند؛ از آن نمی‌توان امید ریاضی کل معاملات را نتیجه گرفت.</p>
          </div>

          <div className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
            <p className="mb-2 text-[10px] font-medium text-foreground">عملکرد بر اساس قدرت سیگنال (Confidence)</p>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[420px] text-[9px]">
                <thead><tr className="border-b border-border/40 text-muted-foreground">
                  <th className="py-1 text-right font-normal">قدرت</th><th className="text-center font-normal">تعداد</th><th className="text-center font-normal">TP</th><th className="text-center font-normal">SL</th><th className="text-center font-normal">تایم‌اوت مثبت/منفی</th><th className="text-center font-normal">موفقیت جهت</th>
                </tr></thead>
                <tbody>{analytics.confidence.map((bucket) => (
                  <tr key={bucket.key} className="border-b border-border/20 last:border-0">
                    <td className="py-1.5 font-medium">{bucket.key}</td>
                    <td className="num text-center">{bucket.total}</td>
                    <td className="num text-center text-emerald-400">{bucket.tp}</td>
                    <td className="num text-center text-rose-400">{bucket.sl}</td>
                    <td className="num text-center">{bucket.timeout_win}/{bucket.timeout_loss}</td>
                    <td className="num text-center font-semibold">{bucket.denominator ? `${bucket.success.toFixed(1)}٪` : "—"}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {[{ title: "تفکیک جهت سیگنال", rows: analytics.directions, labels: { long: "لانگ", short: "شورت" } as Record<string,string> },
              { title: "تفکیک منبع بازار", rows: analytics.sources, labels: { nobitex: "نوبیتکس", bitpin: "بیت‌پین", wallex: "والکس", forex: "فارکس", tabdeal: "تبدیل" } as Record<string,string> }].map((group) => (
              <div key={group.title} className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
                <p className="mb-2 text-[10px] font-medium">{group.title}</p>
                <div className="space-y-1.5">
                  {group.rows.map((row) => (
                    <div key={row.name} className="flex items-center justify-between gap-2 text-[9px]">
                      <span className="text-muted-foreground">{group.labels[row.name] || row.name} <span className="num">({row.total})</span></span>
                      <span className="num font-semibold">{row.denominator ? `${row.success.toFixed(1)}٪` : "بدون نتیجه قطعی"}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <p className="text-[8px] leading-relaxed text-muted-foreground">تعریف‌ها: موفقیت جهت = (TP/TP1 + تایم‌اوت با جهت درست) ÷ نتایج جهت‌دار قطعی؛ نرخ TP/SL فقط خروج‌های TP و SL را می‌سنجد و تایم‌اوت‌ها را کنار می‌گذارد. این معیارها جایگزین سودآوری واقعی یا بک‌تست با کارمزد و اسلیپیج نیستند.</p>
        </section>
      )}

      {/* 🔴 فاز ۱۶.۹ — جدول تفکیک تایم‌فریم‌ها */}
      {Object.keys(byTf).length > 0 && (
        <div className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
          <p className="mb-2 text-[10px] font-medium text-muted-foreground">⏱️ به تفکیک تایم‌فریم</p>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b border-border/40 text-muted-foreground">
                  <th className="pb-1 text-right font-normal">تایم‌فریم</th>
                  <th className="pb-1 text-center font-normal">کل</th>
                  <th className="pb-1 text-center font-normal text-green-500">نرخ برد</th>
                  <th className="pb-1 text-center font-normal text-red-500">نرخ باخت</th>
                  <th className="pb-1 text-center font-normal text-purple-400">پیش‌بینی</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(byTf).sort(([a], [b]) =>
                  (TF_ORDER_INDEX.get(a) ?? 999) - (TF_ORDER_INDEX.get(b) ?? 999) || a.localeCompare(b, "fa")
                ).map(([key, s]) => (
                  <tr key={key} className="border-b border-border/20 last:border-0">
                    <td className="py-1 font-medium">{key}</td>
                    <td className="num py-1 text-center text-muted-foreground">{s.total}</td>
                    <td className="num py-1 text-center font-bold text-green-500">{s.win_rate.toFixed(1)}٪</td>
                    <td className="num py-1 text-center font-bold text-red-500">{s.loss_rate.toFixed(1)}٪</td>
                    <td className="num py-1 text-center font-bold text-purple-400">{s.direction_accuracy.toFixed(0)}٪</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {Object.keys(byStrategy).length > 0 && (
        <div className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
          <p className="mb-2 text-[10px] font-medium text-muted-foreground">📈 به تفکیک استراتژی</p>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b border-border/40 text-muted-foreground">
                  <th className="pb-1 text-right font-normal">استراتژی</th>
                  <th className="pb-1 text-center font-normal">کل</th>
                  <th className="pb-1 text-center font-normal text-green-500">نرخ برد</th>
                  <th className="pb-1 text-center font-normal text-red-500">نرخ باخت</th>
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
                      <td className="num py-1 text-center font-bold text-green-500">{s.win_rate.toFixed(1)}٪</td>
                      <td className="num py-1 text-center font-bold text-red-500">{s.loss_rate.toFixed(1)}٪</td>
                      <td className="num py-1 text-center font-bold text-purple-400">{s.direction_accuracy.toFixed(0)}٪</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {items.length > 0 && (
        <div>
          <button
            onClick={() => setShowHistory((v) => !v)}
            className="flex w-full items-center justify-between rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[10px] font-medium text-foreground/80"
          >
            <span>📋 تاریخچه سیگنال‌ها ({filteredItems.length} / {items.length})</span>
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showHistory ? "rotate-180" : ""}`} />
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
                  {filteredItems.slice(0, 200).map((it) => {
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
          <Trash2 className="h-3.5 w-3.5" /> ریست
        </Button>
      </div>

      <ResetSignalsDialog open={resetOpen} onOpenChange={setResetOpen} onSuccess={handleResetSuccess} />
    </div>
  );
}

function SummaryCard({ label, value, color, bg }: { label: string; value: number; color: string; bg: string; }) {
  return (
    <div className={`rounded-md border ${bg} px-1 py-1.5`}>
      <p className="text-[8px] text-muted-foreground">{label}</p>
      <p className={`num text-sm font-bold ${color}`}>{value}</p>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: { v: string; label: string }[]; }) {
  return (
    <label className="flex flex-col gap-0.5">
      <span className="text-[8px] text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-border/40 bg-background px-1.5 py-1 text-[10px] focus:outline-none focus:ring-1 focus:ring-primary"
      >
        {options.map((o) => (<option key={o.v} value={o.v}>{o.label}</option>))}
      </select>
    </label>
  );
}