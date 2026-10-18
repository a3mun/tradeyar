"use client";

/**
 * BacktestStats — آمار راستی‌آزمایی (نسخه ۶.۱ · فاز ۱۰.۸)
 * ============================================================
 * 🔴 تغییرات:
 *   • حذف قفل داخلی (چون قفل به BacktestPanel منتقل شد)
 */

import { useCallback, useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  Loader2,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { BacktestResponse, SignalHistoryItem } from "@/lib/types";
import { ResetSignalsDialog } from "@/components/backtest/ResetSignalsDialog";

const HISTORY_LIMIT = 500;

interface QualityStats {
  total: number;
  wins: number;
  losses: number;
  pending: number;
  expired: number;
  win_rate: number;
  profit_factor: number;
  avg_rr: number;
  avg_rr_net: number;
  expectancy: number;
  trend_correct: number;
  trend_wrong: number;
  trend_accuracy: number;
  expired_win: number;
  expired_loss: number;
  expired_flat: number;
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
  const [showQualityBreakdown, setShowQualityBreakdown] = useState(false);
  const [showTfBreakdown, setShowTfBreakdown] = useState(false);

  const [tfStats, setTfStats] = useState<
    Record<
      string,
      {
        total: number;
        trend_correct: number;
        trend_wrong: number;
        trend_total: number;
        trend_accuracy: number;
        win_rate: number;
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

  const trapStats = (() => {
    const traps = items.filter((i) => i.had_trap);
    if (traps.length === 0) return null;
    const withResult = traps.filter((i) => i.result);
    if (withResult.length === 0) return null;
    const correct = withResult.filter((i) => i.result === "loss").length;
    return {
      total: traps.length,
      accuracy: (correct / withResult.length) * 100,
    };
  })();

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

  if (loading && !s) {
    return (
      <div className="space-y-2 py-4">
        <div className="h-20 animate-pulse rounded-lg bg-muted/30" />
        <div className="h-20 animate-pulse rounded-lg bg-muted/30" />
      </div>
    );
  }

  if (!s || s.total === 0) {
    return (
      <p className="py-6 text-center text-[11px] text-muted-foreground">
        هنوز سیگنالی برای این فیلتر ثبت نشده.
      </p>
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
        💡 <b className="text-foreground/80">راهنما:</b> «نرخ برد» با در نظر گرفتن کارمزد معاملات حساب می‌شود، اما «دقت روند» فقط مسیر بازار را می‌سنجد. اولویت ما دقت روند است، چرا که حتی با کارمزد صفر، اگر مسیر بازار را اشتباه پیش‌بینی کنیم، معامله ضرر می‌دهد.
      </div>

      {lastCheckTime && (
        <div className="flex items-center justify-center gap-1.5 rounded-md bg-muted/20 px-2 py-1 text-[10px] text-muted-foreground">
          <Clock className="h-3 w-3" />
          آخرین بررسی: <span className="num font-medium text-foreground">{formatLastCheck(lastCheckTime)}</span>
        </div>
      )}

      {quality && (
        <div className="rounded-lg border border-border/40 bg-muted/10 p-2">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-medium text-muted-foreground">
              🎯 آمار به تفکیک کیفیت و روند
            </span>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <div className="rounded-md border border-border/40 bg-muted/30 px-2 py-1.5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[9px] font-medium text-muted-foreground">
                  همه سیگنال‌ها
                </span>
                <span className="num text-[9px] text-muted-foreground">
                  {quality.all.total}
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <p className={`num text-sm font-bold ${winRateColor(quality.all.win_rate)}`}>
                  {quality.all.win_rate.toFixed(1)}٪ <span className="text-[8px] font-normal text-muted-foreground">نرخ برد</span>
                </p>
                <p className="num text-[10px] text-purple-400 font-medium">
                  {quality.all.trend_accuracy.toFixed(0)}٪ <span className="text-[8px] font-normal text-muted-foreground">دقت روند</span>
                </p>
              </div>
            </div>

            <div className="rounded-md border border-purple-500/30 bg-purple-500/5 px-2 py-1.5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[9px] font-medium text-purple-400">
                  🔥 فقط قوی‌ها
                </span>
                <span className="num text-[9px] text-muted-foreground">
                  {quality.strong.total}
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <p className={`num text-sm font-bold ${winRateColor(quality.strong.win_rate)}`}>
                  {quality.strong.win_rate.toFixed(1)}٪ <span className="text-[8px] font-normal text-muted-foreground">نرخ برد</span>
                </p>
                <p className="num text-[10px] text-purple-400 font-medium">
                  {quality.strong.trend_accuracy.toFixed(0)}٪ <span className="text-[8px] font-normal text-muted-foreground">دقت روند</span>
                </p>
              </div>
            </div>
          </div>

          {quality.strong.total > 0 && (
            <div className="mt-2 border-t border-border/30 pt-2">
              <button
                onClick={() => setShowQualityBreakdown((p) => !p)}
                className="flex w-full items-center justify-between rounded px-1 py-0.5 text-[9px] text-muted-foreground hover:bg-muted/30 hover:text-foreground"
              >
                <span>تفکیک دقیق کیفیت</span>
                {showQualityBreakdown ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </button>
              
              {showQualityBreakdown && (
                <div className="mt-1.5 space-y-1">
                  {[
                    { key: "strong" as const, label: "قوی (70+)" },
                    { key: "normal" as const, label: "معمولی (50-69)" },
                    { key: "weak" as const, label: "ضعیف (<50)" },
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
                          <span className="num text-muted-foreground">n={q.total}</span>
                          <span className={`num font-bold ${winRateColor(q.win_rate)}`}>{q.win_rate.toFixed(0)}٪ برد</span>
                          <span className="num text-purple-400 font-medium">{q.trend_accuracy.toFixed(0)}٪ روند</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {(s.trend_correct ?? 0) + (s.trend_wrong ?? 0) > 0 && (
            <div className="mt-2 border-t border-border/30 pt-2">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[9px] font-medium text-purple-400">🎯 دقت روند (کل): {s.trend_accuracy?.toFixed(1)}٪</span>
                <span className="text-[8px] text-muted-foreground">{s.trend_correct ?? 0} درست / {s.trend_wrong ?? 0} غلط</span>
              </div>
              
              {Object.keys(tfStats).length > 0 && (
                <button
                  onClick={() => setShowTfBreakdown((p) => !p)}
                  className="flex w-full items-center justify-between rounded px-1 py-0.5 text-[9px] text-muted-foreground hover:bg-muted/30 hover:text-foreground"
                >
                  <span>نمایش تفکیک تایم‌فریم</span>
                  {showTfBreakdown ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </button>
              )}

              {showTfBreakdown && (
                <div className="mt-1.5 space-y-1">
                  {Object.entries(tfStats)
                    .sort((a, b) => {
                      const order = ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"];
                      return order.indexOf(a[0]) - order.indexOf(b[0]);
                    })
                    .map(([tf, stat]) => {
                      const acc = stat.trend_accuracy ?? 0;
                      if (stat.trend_total === 0) return null;
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
        </div>
      )}

      {trapStats && trapStats.total > 0 && (
        <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-2.5">
          <p className="mb-1.5 text-[10px] font-medium text-orange-400">⚠️ دقت هشدار تله‌ها</p>
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-muted-foreground">{trapStats.total} سیگنال با تله</span>
            <span className="num font-bold text-orange-400">{trapStats.accuracy.toFixed(0)}% درست</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-1.5">
        <Button onClick={handleRun} disabled={running} size="sm" variant="default">
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} بررسی
        </Button>
        <Button onClick={handleDownload} disabled={downloading} size="sm" variant="outline">
          {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />} JSON
        </Button>
        <Button onClick={() => setResetOpen(true)} size="sm" variant="outline" className="text-destructive hover:text-destructive">
          <Trash2 className="h-3.5 w-3.5" /> ریست
        </Button>
      </div>

      <ResetSignalsDialog open={resetOpen} onOpenChange={setResetOpen} onSuccess={handleResetSuccess} />
    </div>
  );
}