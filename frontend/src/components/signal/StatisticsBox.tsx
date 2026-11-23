"use client";

import { useEffect, useMemo, useState } from "react";
import { BarChart3, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

type Summary = {
  total: number;
  tp1_hits: number;
  sl_hits: number;
  timeout_wins: number;
  timeout_losses: number;
  flat: number;
  success_rate: number;
};
type DailyPoint = {
  date: string;
  tp1: number;
  tp_full: number;
  sl: number;
  timeout_win: number;
  timeout_loss: number;
  flat: number;
  total: number;
};
type SiteStats = {
  total_signals: number;
  real_total_signals: number;
  pending: number;
  tp1_hits: number;
  tp1_only_hits: number;
  tp_full_hits: number;
  sl_hits: number;
  timeout_wins: number;
  timeout_losses: number;
  timeout_flats: number;
  tp1_rate: number;
  real_win_rate: number;
  real_loss_rate: number;
  real_direction_accuracy: number;
  win_rate: number;
  direction_accuracy: number;
  has_override: { win_rate: boolean; direction_accuracy: boolean; total_signals: boolean };
  by_timeframe: Record<string, Summary>;
  by_risk: Record<string, Summary>;
  by_confidence: Record<string, Summary>;
  series: DailyPoint[];
  sample_limit: number;
};

const TF_OPTIONS = [
  { value: "", label: "همه تایم‌فریم‌ها" },
  { value: "۱ دقیقه", label: "۱ دقیقه" },
  { value: "۵ دقیقه", label: "۵ دقیقه" },
  { value: "۱۵ دقیقه", label: "۱۵ دقیقه" },
  { value: "۳۰ دقیقه", label: "۳۰ دقیقه" },
  { value: "۱ ساعت", label: "۱ ساعت" },
  { value: "روزانه", label: "روزانه" },
];
const RISK_OPTIONS = [
  { value: "", label: "همه ریسک‌ها" },
  { value: "conservative", label: "محتاطانه" },
  { value: "aggressive", label: "جسورانه" },
];
const CONFIDENCE_OPTIONS = [
  { value: "", label: "همه درصدهای اطمینان" },
  { value: "lt40", label: "کمتر از ۴۰٪" },
  { value: "40_49", label: "۴۰ تا ۴۹٪" },
  { value: "50_59", label: "۵۰ تا ۵۹٪" },
  { value: "60_69", label: "۶۰ تا ۶۹٪" },
  { value: "70p", label: "۷۰٪ به بالا" },
];

function pct(value: number | undefined): string {
  return `${Number(value || 0).toLocaleString("fa-IR", { maximumFractionDigits: 1 })}٪`;
}
function count(value: number | undefined): string {
  return Number(value || 0).toLocaleString("fa-IR");
}
function dayLabel(value: string): string {
  const date = new Date(`${value}T12:00:00Z`);
  return new Intl.DateTimeFormat("fa-IR", { month: "numeric", day: "numeric" }).format(date);
}

function MiniBars({ series }: { series: DailyPoint[] }) {
  const data = series.slice(-30);
  const max = Math.max(1, ...data.map((d) => d.tp1 + d.sl + d.timeout_win + d.timeout_loss + d.flat));
  if (!data.length) {
    return <div className="flex h-28 items-center justify-center text-[10px] text-muted-foreground">در این بازه داده‌ای برای نمودار وجود ندارد.</div>;
  }
  return (
    <div className="space-y-2">
      <div className="flex h-28 items-end gap-1">
        {data.map((d) => {
          const wins = d.tp1;
          const losses = d.sl + d.timeout_loss;
          const other = d.timeout_win + d.flat;
          const total = wins + losses + other;
          return (
            <div key={d.date} className="group flex h-full min-w-0 flex-1 flex-col justify-end" title={`${dayLabel(d.date)} · TP1: ${d.tp1} · SL: ${d.sl} · timeout: ${d.timeout_win + d.timeout_loss + d.flat}`}>
              <div className="flex h-full flex-col justify-end overflow-hidden rounded-t-sm bg-muted/30">
                {other > 0 && <div className="w-full bg-slate-500/50" style={{ height: `${(other / max) * 100}%` }} />}
                {losses > 0 && <div className="w-full bg-rose-500/75" style={{ height: `${(losses / max) * 100}%` }} />}
                {wins > 0 && <div className="w-full bg-emerald-500/90" style={{ height: `${(wins / max) * 100}%` }} />}
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex items-center justify-between text-[8px] text-muted-foreground">
        <span>{dayLabel(data[0].date)}</span><span>{dayLabel(data[data.length - 1].date)}</span>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[9px] text-muted-foreground">
        <span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-emerald-500" />TP1 یا TP کامل</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-rose-500" />SL / جهت ناموفق</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-slate-500" />جهت درست یا خنثی در timeout</span>
      </div>
    </div>
  );
}

function Breakdown({ title, rows, labels }: {
  title: string;
  rows: Record<string, Summary>;
  labels: Record<string, string>;
}) {
  const entries = Object.entries(rows || {}).filter(([, v]) => v.total > 0);
  if (!entries.length) return null;
  return (
    <div className="rounded-lg border border-border/40 p-2.5">
      <h4 className="mb-2 text-[10px] font-semibold">{title}</h4>
      <div className="space-y-2">
        {entries.map(([key, item]) => (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between gap-2 text-[9px]">
              <span>{labels[key] || key}</span>
              <span className="num font-semibold">{pct(item.success_rate)} <span className="font-normal text-muted-foreground">· {count(item.total)} سیگنال</span></span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted/60">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.max(0, Math.min(100, item.success_rate || 0))}%` }} />
            </div>
            <p className="text-[8px] text-muted-foreground">TP1/TP: {count(item.tp1_hits)} · SL: {count(item.sl_hits)} · timeout ناموفق: {count(item.timeout_losses)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function StatisticsBox() {
  const [period, setPeriod] = useState("7d");
  const [tf, setTf] = useState("");
  const [risk, setRisk] = useState("");
  const [confidence, setConfidence] = useState("");
  const [stats, setStats] = useState<SiteStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    const params = new URLSearchParams({ time_filter: period, limit: "200" });
    if (tf) params.set("tf", tf);
    if (risk) params.set("risk_profile", risk);
    if (confidence) params.set("confidence_bucket", confidence);
    api.get<SiteStats & { ok: boolean }>(`/backtest/site-stats?${params.toString()}`)
      .then((res) => { if (!cancelled) setStats(res.data); })
      .catch(() => { if (!cancelled) { setStats(null); setError(true); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [period, tf, risk, confidence]);

  const periodLabel = period === "7d" ? "۷ روز اخیر" : period === "30d" ? "۳۰ روز اخیر" : "۲۰۰ سیگنال بسته‌شده اخیر";
  const byTfLabels = useMemo(() => Object.fromEntries(TF_OPTIONS.filter((x) => x.value).map((x) => [x.value, x.label])), []);
  const byRiskLabels = { aggressive: "جسورانه", conservative: "محتاطانه", نامشخص: "نامشخص" };
  const byConfidenceLabels = { lt40: "کمتر از ۴۰٪", "40_49": "۴۰ تا ۴۹٪", "50_59": "۵۰ تا ۵۹٪", "60_69": "۶۰ تا ۶۹٪", "70p": "۷۰٪ به بالا" };

  return (
    <section className="space-y-3 rounded-xl border border-border/50 bg-card/40 p-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-xs font-semibold text-foreground">عملکرد راستی‌آزمایی سیگنال‌های تریدمون</h3>
          <p className="mt-0.5 text-[9px] text-muted-foreground">معیار اصلی: لمس TP1 یا هدف بالاتر</p>
        </div>
        <BarChart3 className="h-5 w-5 text-muted-foreground" />
      </div>

      <div className="grid grid-cols-3 gap-1 rounded-lg bg-muted/20 p-1">
        {[{ v: "7d", label: "۷ روز" }, { v: "30d", label: "۳۰ روز" }, { v: "all", label: "۲۰۰ اخیر" }].map((x) => (
          <button key={x.v} type="button" onClick={() => setPeriod(x.v)}
            className={`rounded-md px-2 py-2 text-[10px] transition ${period === x.v ? "bg-primary/15 font-semibold text-primary" : "text-muted-foreground hover:bg-muted/50"}`}>
            {x.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-3">
        <select aria-label="تایم‌فریم" value={tf} onChange={(e) => setTf(e.target.value)} className="h-8 rounded-md border border-border bg-background px-2 text-[10px]">
          {TF_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
        </select>
        <select aria-label="ریسک" value={risk} onChange={(e) => setRisk(e.target.value)} className="h-8 rounded-md border border-border bg-background px-2 text-[10px]">
          {RISK_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
        </select>
        <select aria-label="درصد اطمینان" value={confidence} onChange={(e) => setConfidence(e.target.value)} className="h-8 rounded-md border border-border bg-background px-2 text-[10px]">
          {CONFIDENCE_OPTIONS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
        </select>
      </div>

      {loading && <div className="flex items-center justify-center py-7"><RefreshCw className="h-4 w-4 animate-spin text-primary" /></div>}
      {!loading && error && <p className="py-5 text-center text-[10px] text-destructive">دریافت آمار ممکن نشد. اتصال endpoint آمار عمومی را بررسی کنید.</p>}
      {!loading && !error && stats && (
        <>
          <div className="flex items-center justify-between text-[9px] text-muted-foreground">
            <span>بازه: {periodLabel}</span>
            <span>نمونه بسته‌شده: {count(stats.real_total_signals)}</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] p-2.5">
              <p className="text-[9px] text-muted-foreground">نرخ رسیدن به TP1 یا TP</p>
              <p className="num mt-1 text-2xl font-bold text-emerald-400">{pct(stats.tp1_rate)}</p>
              <p className="mt-1 text-[8px] text-muted-foreground">{count(stats.tp1_hits)} سیگنال از نمونه قطعی</p>
            </div>
            <div className="rounded-lg border border-border/50 bg-muted/10 p-2.5">
              <p className="text-[9px] text-muted-foreground">تعداد سیگنال در انتظار</p>
              <p className="num mt-1 text-2xl font-bold">{count(stats.pending)}</p>
              <p className="mt-1 text-[8px] text-muted-foreground">هنوز نتیجه نهایی ندارند</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-1.5">
            <div className="rounded-md bg-emerald-500/5 p-2 text-center"><p className="num text-sm font-bold text-emerald-400">{count(stats.tp1_hits)}</p><p className="text-[8px] text-muted-foreground">TP1 یا TP</p></div>
            <div className="rounded-md bg-rose-500/5 p-2 text-center"><p className="num text-sm font-bold text-rose-400">{count(stats.sl_hits)}</p><p className="text-[8px] text-muted-foreground">حد ضرر</p></div>
            <div className="rounded-md bg-muted/40 p-2 text-center"><p className="num text-sm font-bold">{count(stats.timeout_wins + stats.timeout_losses + stats.timeout_flats)}</p><p className="text-[8px] text-muted-foreground">Timeout</p></div>
          </div>

          <div className="rounded-lg border border-border/40 p-2.5">
            <div className="mb-2 flex items-center justify-between"><h4 className="text-[10px] font-semibold">نمودار عملکرد روزانه</h4><span className="text-[8px] text-muted-foreground">تعداد خروج‌ها، نه سود خالص</span></div>
            <MiniBars series={stats.series || []} />
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Breakdown title="عملکرد بر اساس تایم‌فریم" rows={stats.by_timeframe || {}} labels={byTfLabels} />
            <Breakdown title="عملکرد بر اساس ریسک" rows={stats.by_risk || {}} labels={byRiskLabels} />
            <Breakdown title="عملکرد بر اساس درصد اطمینان" rows={stats.by_confidence || {}} labels={byConfidenceLabels} />
          </div>

          {(stats.has_override?.win_rate || stats.has_override?.direction_accuracy || stats.has_override?.total_signals) && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/[0.04] p-2.5">
              <p className="text-[9px] font-semibold text-amber-300">مقادیر دستی ثبت‌شده توسط مدیر</p>
              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[9px]">
                {stats.has_override.win_rate && <span>نرخ برد دستی: <b className="num">{pct(stats.win_rate)}</b></span>}
                {stats.has_override.direction_accuracy && <span>دقت جهت دستی: <b className="num">{pct(stats.direction_accuracy)}</b></span>}
                {stats.has_override.total_signals && <span>تعداد دستی: <b className="num">{count(stats.total_signals)}</b></span>}
              </div>
              <p className="mt-1 text-[8px] text-muted-foreground">این مقادیر جدا از محاسبه واقعی TP1 نمایش داده می‌شوند و جایگزین آن نیستند.</p>
            </div>
          )}

          <p className="text-[8px] leading-relaxed text-muted-foreground">
            آمار بر اساس حداکثر ۲۰۰ سیگنال بسته‌شده اخیر در بازه انتخابی محاسبه شده است. نرخ TP1 یعنی سهم سیگنال‌هایی که به TP1 یا هدف بالاتر رسیده‌اند، از خروج‌های دارای جهت مشخص؛ موارد خنثی از مخرج حذف شده‌اند. این آمار معادل سود خالص حساب نیست.
          </p>
        </>
      )}
    </section>
  );
}
