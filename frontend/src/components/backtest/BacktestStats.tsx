"use client";

/**
 * BacktestStats — آمار راستی‌آزمایی (نسخه ۸.۰ · فاز ۱۰.۱۰)
 * ============================================================
 * 🔴 تغییرات:
 *   • بازطراحی کامل UI با تمرکز بر خوانایی و نمودارهای میله‌ای
 *   • افزودن باکس مدرن برای تله‌ها
 *   • بهینه‌سازی رنگ‌ها و فاصله‌ها
 */

import { useCallback, useEffect, useState } from "react";
import {
  Clock,
  Download,
  Loader2,
  RefreshCw,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { BacktestResponse, SignalHistoryItem } from "@/lib/types";
import { ResetSignalsDialog } from "./ResetSignalsDialog";

const HISTORY_LIMIT = 500;

interface QualityStats {
  total: number;
  wins: number;
  losses: number;
  pending: number;
  expired: number;
  win_rate: number;
  direction_accuracy: number;
}

interface QualityResponse {
  all: QualityStats;
  strong: QualityStats;
  normal: QualityStats;
  weak: QualityStats;
}

interface Props {
  source?: string;
  profile?: string;
  time?: string;
  limit: number;
}

export function BacktestStats({
  source = "",
  profile = "",
  time = "all",
  limit,
}: Props) {
  interface StatsState {
    data: BacktestResponse | null;
    quality: QualityResponse | null;
    items: SignalHistoryItem[];
    loading: boolean;
    error: string;
  }

  const [state, setState] = useState<StatsState>({
    data: null,
    quality: null,
    items: [],
    loading: true,
    error: "",
  });
  const { data, quality, items, loading, error } = state;

  const [running, setRunning] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [notice, setNotice] = useState("");
  const [resetOpen, setResetOpen] = useState(false);

  const [tfStats, setTfStats] = useState<
    Record<
      string,
      {
        total: number;
        win_rate: number;
        direction_accuracy: number;
        trend_accuracy: number;
      }
    >
  >({});

  const lastCheckTime = (() => {
    if (!items || items.length === 0) return null;
    const withResult = items
      .filter((i) => i.result_time)
      .sort(
        (a, b) =>
          new Date(b.result_time || "").getTime() -
          new Date(a.result_time || "").getTime()
      );
    if (withResult.length === 0) return null;
    return withResult[0].result_time;
  })();

  const formatLastCheck = (iso: string | null | undefined) => {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return new Intl.DateTimeFormat("fa-IR", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(d);
    } catch {
      return "—";
    }
  };

  useEffect(() => {
    let cancelled = false;
    api
      .get("/backtest/by-tf", {
        params: { time_filter: time, risk_profile: profile, limit: limit },
      })
      .then((res) => {
        if (!cancelled) setTfStats(res.data.items || {});
      })
      .catch(() => {
        if (!cancelled) setTfStats({});
      });
    return () => {
      cancelled = true;
    };
  }, [time, profile, limit]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [statsRes, historyRes, qualityRes] = await Promise.all([
          api.get("/backtest", {
            params: { time_filter: time, source, risk_profile: profile, limit },
          }),
          api.get("/backtest/history", {
            params: { limit: HISTORY_LIMIT, source, risk_profile: profile },
          }),
          api
            .get("/backtest/by-quality", {
              params: { time_filter: time, source, risk_profile: profile, limit },
            })
            .catch(() => ({ data: { items: null } })),
        ]);
        if (cancelled) return;
        setState({
          data: statsRes.data,
          quality: qualityRes.data?.items ?? null,
          items: historyRes.data?.items ?? [],
          loading: false,
          error: "",
        });
      } catch {
        if (cancelled) return;
        setState({
          data: null,
          quality: null,
          items: [],
          loading: false,
          error: "دریافت آمار ناموفق بود",
        });
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [time, source, profile, limit]);

  const fetchStats = useCallback(async () => {
    try {
      const [statsRes, historyRes, qualityRes] = await Promise.all([
        api.get("/backtest", {
          params: { time_filter: time, source, risk_profile: profile, limit },
        }),
        api.get("/backtest/history", {
          params: { limit: HISTORY_LIMIT, source, risk_profile: profile },
        }),
        api
          .get("/backtest/by-quality", {
            params: { time_filter: time, source, risk_profile: profile, limit },
          })
          .catch(() => ({ data: { items: null } })),
      ]);
      setState({
        data: statsRes.data,
        quality: qualityRes.data?.items ?? null,
        items: historyRes.data?.items ?? [],
        loading: false,
        error: "",
      });
    } catch {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: "دریافت آمار ناموفق بود",
      }));
    }
  }, [time, source, profile, limit]);

  const setError = (msg: string) =>
    setState((prev) => ({ ...prev, error: msg }));

  const handleRun = async () => {
    setRunning(true);
    setNotice("");
    setState((prev) => ({ ...prev, error: "" }));
    try {
      const res = await api.post("/backtest/run");
      const checked = res.data?.checked ?? 0;
      const updated = res.data?.updated ?? 0;
      setNotice(`${checked} سیگنال بررسی شد · ${updated} به‌روز شد`);
      await fetchStats();
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      setError(
        status === 409
          ? "راستی‌آزمایی همین حالا در حال اجراست"
          : "اجرای راستی‌آزمایی ناموفق بود"
      );
    } finally {
      setRunning(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    setState((prev) => ({ ...prev, error: "" }));
    let url: string | null = null;
    try {
      const res = await api.get("/backtest/history", {
        params: { limit: 1000 },
      });
      const payload = JSON.stringify(res.data?.items ?? [], null, 2);
      const blob = new Blob([payload], { type: "application/json" });
      url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      const now = new Date();
      const ts = new Intl.DateTimeFormat("en-GB", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Tehran",
      })
        .format(now)
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
    setState((prev) => ({ ...prev, error: "" }));
    fetchStats();
  };

  const s = data?.stats;

  const pendingCount = items.filter((i) => !i.result && !i.expired).length;
  const totalCount = items.length;
  const closedCount = totalCount - pendingCount;

  const trapStats = (() => {
    const traps = items.filter((i) => i.had_trap);
    if (traps.length === 0) return null;
    const withResult = traps.filter((i) => i.result);
    if (withResult.length === 0) return { total: traps.length, accuracy: 0 };
    const correct = withResult.filter((i) => i.result === "loss").length;
    return {
      total: traps.length,
      accuracy: (correct / withResult.length) * 100,
    };
  })();

  if (loading && !s) {
    return (
      <div className="space-y-2 py-4">
        <div className="h-20 animate-pulse rounded-lg bg-muted/30" />
        <div className="h-20 animate-pulse rounded-lg bg-muted/30" />
      </div>
    );
  }

  if (!s || totalCount === 0) {
    return (
      <div className="space-y-3">
        <p className="py-6 text-center text-[11px] text-muted-foreground">
          هنوز سیگنالی برای این فیلتر ثبت نشده.
        </p>
        <Button
          onClick={handleRun}
          disabled={running}
          size="sm"
          variant="default"
          className="w-full"
        >
          {running ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          بررسی
        </Button>
      </div>
    );
  }

  const winRateColor = (rate: number) =>
    rate >= 55 ? "text-green-500" : rate >= 45 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="space-y-3">
      {error && (
        <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
          ⚠️ {error}
        </p>
      )}

      {notice && !error && (
        <p className="rounded-md border border-green-500/30 bg-green-500/5 p-2 text-[11px] text-green-500">
          ✅ {notice}
        </p>
      )}

      <div className="rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[9px] leading-relaxed text-muted-foreground">
        💡 <b className="text-foreground/80">راهنما:</b> «نرخ موفقیت معامله» یعنی درصد معاملاتی که به هدف (TP) رسیدن. «دقت پیش‌بینی روند» یعنی درصد دفعاتی که جهت کلی بازار رو درست تشخیص دادیم (حتی اگه به TP نرسه).
      </div>

      {lastCheckTime && (
        <div className="flex items-center justify-center gap-1.5 rounded-md bg-muted/20 px-2 py-1 text-[10px] text-muted-foreground">
          <Clock className="h-3 w-3" />
          آخرین بررسی: <span className="num font-medium text-foreground">{formatLastCheck(lastCheckTime)}</span>
        </div>
      )}

      {/* ═══ ۵ کارت خلاصه وضعیت ═══ */}
      <div className="grid grid-cols-5 gap-1 text-center">
        <div className="rounded-md border border-border/40 bg-muted/10 px-1 py-1.5">
          <p className="text-[8px] text-muted-foreground">کل</p>
          <p className="num text-sm font-bold">{totalCount}</p>
        </div>
        <div className="rounded-md border border-green-500/20 bg-green-500/5 px-1 py-1.5">
          <p className="text-[8px] text-muted-foreground">برد (TP)</p>
          <p className="num text-sm font-bold text-green-500">{s.tp_hits ?? 0}</p>
        </div>
        <div className="rounded-md border border-red-500/20 bg-red-500/5 px-1 py-1.5">
          <p className="text-[8px] text-muted-foreground">باخت (SL)</p>
          <p className="num text-sm font-bold text-red-500">{s.sl_hits ?? 0}</p>
        </div>
        <div className="rounded-md border border-yellow-500/20 bg-yellow-500/5 px-1 py-1.5">
          <p className="text-[8px] text-muted-foreground">در انتظار</p>
          <p className="num text-sm font-bold text-yellow-500">{pendingCount}</p>
        </div>
        <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-1 py-1.5">
          <p className="text-[8px] text-muted-foreground">تایم‌اوت</p>
          <p className="num text-sm font-bold text-blue-400">{s.expired ?? 0}</p>
        </div>
      </div>

      {/* ═══ معیارهای اصلی ═══ */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-2 text-center shadow-sm">
          <p className="text-[10px] text-muted-foreground mb-1 flex items-center justify-center gap-1">✅ نرخ موفقیت معامله (TP)</p>
          <p className={`num text-xl font-bold ${winRateColor(s.win_rate)}`}>
            {s.win_rate.toFixed(1)}%
          </p>
        </div>
        <div className="rounded-lg border border-purple-500/30 bg-purple-500/10 p-2 text-center shadow-sm">
          <p className="text-[10px] text-muted-foreground mb-1 flex items-center justify-center gap-1">🎯 دقت پیش‌بینی روند</p>
          <p className={`num text-xl font-bold ${winRateColor(s.direction_accuracy ?? 0)}`}>
            {(s.direction_accuracy ?? 0).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* ═══ تفکیک دقیق (نمودار میله‌ای) ═══ */}
      <div className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
        <div className="mb-2 flex items-center justify-between text-[10px] text-muted-foreground px-1">
          <span className="font-medium">جزئیات نتایج (از {closedCount} معامله بسته‌شده)</span>
        </div>
        
        {closedCount === 0 ? (
          <p className="text-center text-[10px] text-muted-foreground py-2">
            هنوز معامله‌ای بسته نشده است.
          </p>
        ) : (
          <div className="space-y-2">
            {[
              { label: "برد واقعی (TP)", count: s.tp_hits ?? 0, color: "bg-green-500", textColor: "text-green-500" },
              { label: "باخت واقعی (SL)", count: s.sl_hits ?? 0, color: "bg-red-500", textColor: "text-red-500" },
              { label: "جهت درست (تایم‌اوت در سود)", count: s.timeout_wins ?? 0, color: "bg-green-400", textColor: "text-green-400" },
              { label: "جهت غلط (تایم‌اوت در ضرر)", count: s.timeout_losses ?? 0, color: "bg-red-400", textColor: "text-red-400" },
              { label: "خنثی (تایم‌اوت سر به سر)", count: s.timeout_flats ?? 0, color: "bg-muted-foreground", textColor: "text-muted-foreground" },
            ].map((item) => {
              if (item.count === 0) return null;
              const percent = (item.count / closedCount) * 100;
              return (
                <div key={item.label} className="flex items-center gap-2 text-[9px]">
                  <span className="w-32 shrink-0 text-muted-foreground text-right">{item.label}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted/40">
                    <div className={`h-full ${item.color}`} style={{ width: `${percent}%` }} />
                  </div>
                  <span className={`num w-14 text-left font-bold ${item.textColor}`}>
                    {item.count} ({percent.toFixed(0)}٪)
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ═══ نرخ موفقیت بر اساس قدرت سیگنال ═══ */}
      {quality && (quality.strong.total > 0 || quality.normal.total > 0 || quality.weak.total > 0) && (
        <div className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
          <div className="mb-1.5 flex items-center justify-between text-[10px] text-muted-foreground px-1">
            <span className="font-medium">نرخ موفقیت بر اساس قدرت سیگنال</span>
          </div>
          
          <div className="space-y-1">
            {[
              { key: "strong" as const, label: "قوی (بالای ۷۵٪)" },
              { key: "normal" as const, label: "معمولی (۶۰ تا ۷۴٪)" },
              { key: "weak" as const, label: "ضعیف (۴۵ تا ۵۹٪)" },
            ].map(({ key, label }) => {
              const q = quality[key];
              if (q.total === 0) return null;
              const c = key === "strong" ? "bg-purple-500/5 border-purple-500/30 text-purple-400" 
                        : key === "normal" ? "bg-orange-500/5 border-orange-500/30 text-orange-400" 
                        : "bg-slate-500/5 border-slate-500/30 text-slate-400";
              return (
                <div key={key} className={`flex items-center justify-between rounded-md border ${c} px-2 py-1`}>
                  <span className={`text-[9px] font-medium`}>{label}</span>
                  <div className="flex items-center gap-2 text-[9px]">
                    <span className="num text-muted-foreground">تعداد: {q.total}</span>
                    <span className={`num font-bold ${winRateColor(q.win_rate)}`}>{q.win_rate.toFixed(0)}٪ برد</span>
                    <span className="num text-purple-400 font-medium">{(q.direction_accuracy ?? 0).toFixed(0)}٪ پیش‌بینی</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══ دقت روند (با تفکیک تایم‌فریم) ═══ */}
      {(s.trend_correct ?? 0) + (s.trend_wrong ?? 0) > 0 && (
        <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2.5">
          <div className="mb-1 flex items-center justify-between">
            <span className="flex items-center gap-1 text-[10px] font-medium text-purple-400">🎯 دقت پیش‌بینی روند در تایم‌فریم‌ها</span>
            <span className="num text-sm font-bold text-purple-400">{(s.trend_accuracy ?? 0).toFixed(1)}٪</span>
          </div>
          <div className="flex items-center justify-between text-[9px] text-muted-foreground mb-2">
            <span className="text-green-500">✅ {s.trend_correct ?? 0} درست</span>
            <span className="text-red-500">❌ {s.trend_wrong ?? 0} غلط</span>
          </div>

          {Object.keys(tfStats).length > 0 && (
            <div className="mt-1.5 space-y-1.5 border-t border-purple-500/20 pt-2">
              <div className="text-[9px] text-muted-foreground mb-1">دقت به تفکیک تایم‌فریم:</div>
              {Object.entries(tfStats)
                .sort((a, b) => {
                  const order = ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"];
                  return order.indexOf(a[0]) - order.indexOf(b[0]);
                })
                .map(([tf, stat]) => {
                  const acc = stat.trend_accuracy ?? 0;
                  if (stat.total === 0) return null;
                  const color = acc >= 70 ? "text-green-500 bg-green-500" : acc >= 50 ? "text-yellow-500 bg-yellow-500" : "text-red-500 bg-red-500";
                  return (
                    <div key={tf} className="flex items-center gap-2 text-[9px]">
                      <span className="w-12 shrink-0 text-muted-foreground">{tf}</span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted/40">
                        <div className={`h-full ${color.split(" ")[1]}`} style={{ width: `${acc}%` }} />
                      </div>
                      <span className={`num w-8 text-left font-bold ${color.split(" ")[0]}`}>{acc.toFixed(0)}٪</span>
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      )}

      {/* ═══ تله‌ها ═══ */}
      {trapStats && trapStats.total > 0 && (
        <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 p-2.5 shadow-sm">
          <p className="mb-1.5 flex items-center gap-1 text-[10px] font-medium text-orange-400">
            <AlertTriangle className="h-3.5 w-3.5" /> دقت هشدار تله‌ها
          </p>
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-muted-foreground">{trapStats.total} سیگنال همراه با تله</span>
            <span className="num font-bold text-orange-400">{trapStats.accuracy.toFixed(0)}% درست</span>
          </div>
        </div>
      )}

      {/* ═══ دکمه‌ها ═══ */}
      <div className="grid grid-cols-3 gap-2 pt-2">
        <Button onClick={handleRun} disabled={running} size="sm" variant="default">
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} بررسی
        </Button>
        <Button onClick={handleDownload} disabled={downloading} size="sm" variant="outline">
          {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />} دانلود JSON
        </Button>
        <Button onClick={() => setResetOpen(true)} size="sm" variant="outline" className="text-destructive hover:text-destructive">
          <Trash2 className="h-3.5 w-3.5" /> ریست
        </Button>
      </div>

      <ResetSignalsDialog open={resetOpen} onOpenChange={setResetOpen} onSuccess={handleResetSuccess} />
    </div>
  );
}