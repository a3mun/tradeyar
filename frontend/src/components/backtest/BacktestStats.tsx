"use client";

/**
 * BacktestStats — آمار راستی‌آزمایی
 * ============================================================
 * نسخه ۴.۰ · فاز ۱۰.۱
 *
 * ═══ تغییرات نسخه ۴.۰ ═══
 *   • کارت «تقسیم کیفیت» (همه / قوی) اضافه شد
 *   • expandable breakdown ۴-سطحی
 *   • نمایش جداگانه win_rate (TP/SL) از trend_accuracy (جهت)
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


// ═══════════════════════════════════════════════════════════
// تایپ آمار یک دسته
// ═══════════════════════════════════════════════════════════
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
}

export function BacktestStats({
  source = "",
  profile = "",
  time = "all",
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
  const [showBreakdown, setShowBreakdown] = useState(false);

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

  // ═══ آخرین زمان بررسی ═══
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

  // ═══ آمار به تفکیک TF ═══
  useEffect(() => {
    let cancelled = false;
    api
      .get("/backtest/by-tf", {
        params: { time_filter: time, risk_profile: profile },
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
  }, [time, profile]);

  // ═══ آمار تله‌ها ═══
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

  // ═══ دریافت آمار (شامل quality) ═══
  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [statsRes, historyRes, qualityRes] = await Promise.all([
          api.get("/backtest", {
            params: {
              time_filter: time,
              source: source,
              risk_profile: profile,
            },
          }),
          api.get("/backtest/history", {
            params: {
              limit: HISTORY_LIMIT,
              source: source,
              risk_profile: profile,
            },
          }),
          api
            .get("/backtest/by-quality", {
              params: {
                time_filter: time,
                source: source,
                risk_profile: profile,
              },
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
          error: "دریافت آمار ناموفق بود — اتصال به سرور را چک کن",
        });
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [time, source, profile]);

  const fetchStats = useCallback(async () => {
    try {
      const [statsRes, historyRes, qualityRes] = await Promise.all([
        api.get("/backtest", {
          params: {
            time_filter: time,
            source: source,
            risk_profile: profile,
          },
        }),
        api.get("/backtest/history", {
          params: {
            limit: HISTORY_LIMIT,
            source: source,
            risk_profile: profile,
          },
        }),
        api
          .get("/backtest/by-quality", {
            params: {
              time_filter: time,
              source: source,
              risk_profile: profile,
            },
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
  }, [time, source, profile]);

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
      const status = (e as { response?: { status?: number } })?.response
        ?.status;
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
      a.download = `trademun_signals_${Date.now()}.json`;
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
        <br />
        <span className="text-[10px]">اسکن خودکار هر ۱ ساعت اجرا می‌شه.</span>
      </p>
    );
  }

  const winRateColor = (rate: number) =>
    rate >= 55
      ? "text-green-500"
      : rate >= 45
        ? "text-yellow-500"
        : "text-red-500";

  // ═══ رنگ‌بندی هر دسته ═══
  const qualityColor = {
    all: {
      bg: "bg-muted/30",
      border: "border-border/40",
      text: "text-foreground",
      accent: "text-blue-400",
    },
    strong: {
      bg: "bg-purple-500/5",
      border: "border-purple-500/30",
      text: "text-purple-400",
      accent: "text-purple-400",
    },
    normal: {
      bg: "bg-orange-500/5",
      border: "border-orange-500/30",
      text: "text-orange-400",
      accent: "text-orange-400",
    },
    weak: {
      bg: "bg-slate-500/5",
      border: "border-slate-500/30",
      text: "text-slate-400",
      accent: "text-slate-400",
    },
  };

  return (
    <div className="space-y-3">
      {error && (
        <p
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive"
        >
          ⚠️ {error}
        </p>
      )}

      {notice && !error && (
        <p className="rounded-md border border-green-500/30 bg-green-500/5 p-2 text-[11px] text-green-500">
          ✅ {notice}
        </p>
      )}

      {/* ═══ راهنما ═══ */}
      <div className="rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[9px] leading-relaxed text-muted-foreground">
        📊 <b className="text-foreground/80">نرخ برد</b>: فقط سیگنال‌های
        TP/SL خورده · 🎯 <b className="text-foreground/80">دقت روند</b>: شامل
        منقضی‌ها با جهت درست
      </div>

      {/* ═══ آخرین بررسی ═══ */}
      {lastCheckTime && (
        <div className="flex items-center justify-center gap-1.5 rounded-md bg-muted/20 px-2 py-1 text-[10px] text-muted-foreground">
          <Clock className="h-3 w-3" />
          آخرین بررسی:
          <span className="num font-medium text-foreground">
            {formatLastCheck(lastCheckTime)}
          </span>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          🎯 کارت کیفیت — ۲ سطح اصلی
      ═══════════════════════════════════════════════════════ */}
      {quality && (
        <>
          <div className="rounded-lg border border-border/40 bg-muted/10 p-2">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] font-medium text-muted-foreground">
                🎯 آمار به تفکیک کیفیت
              </span>
              {quality.strong.total > 0 && (
                <button
                  onClick={() => setShowBreakdown((p) => !p)}
                  className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] text-muted-foreground hover:bg-muted/30 hover:text-foreground"
                >
                  {showBreakdown ? "بستن" : "تفکیک کامل"}
                  {showBreakdown ? (
                    <ChevronUp className="h-2.5 w-2.5" />
                  ) : (
                    <ChevronDown className="h-2.5 w-2.5" />
                  )}
                </button>
              )}
            </div>

            {/* ─── ۲ کارت اصلی ─── */}
            <div className="grid grid-cols-2 gap-1.5">
              {/* همه */}
              <div
                className={`rounded-md border ${qualityColor.all.border} ${qualityColor.all.bg} px-2 py-2`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-medium text-muted-foreground">
                    همه سیگنال‌ها
                  </span>
                  <span className="num text-[9px] text-muted-foreground">
                    {quality.all.total}
                  </span>
                </div>
                <p
                  className={`num mt-0.5 text-base font-bold ${winRateColor(
                    quality.all.win_rate
                  )}`}
                >
                  {quality.all.win_rate.toFixed(1)}٪
                </p>
                <p className="text-[8px] text-muted-foreground">
                  نرخ برد · دقت روند{" "}
                  <span className="num text-purple-400">
                    {quality.all.trend_accuracy.toFixed(0)}٪
                  </span>
                </p>
              </div>

              {/* قوی */}
              <div
                className={`rounded-md border ${qualityColor.strong.border} ${qualityColor.strong.bg} px-2 py-2`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-medium text-purple-400">
                    🔥 فقط قوی‌ها
                  </span>
                  <span className="num text-[9px] text-muted-foreground">
                    {quality.strong.total}
                  </span>
                </div>
                <p
                  className={`num mt-0.5 text-base font-bold ${winRateColor(
                    quality.strong.win_rate
                  )}`}
                >
                  {quality.strong.win_rate.toFixed(1)}٪
                </p>
                <p className="text-[8px] text-muted-foreground">
                  نرخ برد · دقت روند{" "}
                  <span className="num text-purple-400">
                    {quality.strong.trend_accuracy.toFixed(0)}٪
                  </span>
                </p>
              </div>
            </div>

            {/* ─── breakdown ۴-سطحی ─── */}
            {showBreakdown && (
              <div className="mt-2 space-y-1 border-t border-border/30 pt-2">
                {[
                  { key: "strong" as const, label: "قوی (70+)" },
                  { key: "normal" as const, label: "معمولی (50-69)" },
                  { key: "weak" as const, label: "ضعیف (<50)" },
                ].map(({ key, label }) => {
                  const q = quality[key];
                  if (q.total === 0) return null;
                  const c = qualityColor[key];
                  return (
                    <div
                      key={key}
                      className={`flex items-center justify-between rounded-md border ${c.border} ${c.bg} px-2 py-1`}
                    >
                      <span className={`text-[9px] font-medium ${c.text}`}>
                        {label}
                      </span>
                      <div className="flex items-center gap-2 text-[9px]">
                        <span className="num text-muted-foreground">
                          n={q.total}
                        </span>
                        <span
                          className={`num font-bold ${winRateColor(
                            q.win_rate
                          )}`}
                        >
                          {q.win_rate.toFixed(0)}٪
                        </span>
                        <span className="num text-purple-400">
                          {q.trend_accuracy.toFixed(0)}٪
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* ═══ آمار اصلی — فشرده ═══ */}
      <div className="grid grid-cols-4 gap-1.5 text-center">
        <div className="rounded-md bg-muted/30 px-1.5 py-1">
          <p className="text-[8px] text-muted-foreground">کل</p>
          <p className="num text-sm font-bold">{s.total}</p>
        </div>
        <div className="rounded-md bg-green-500/5 px-1.5 py-1">
          <p className="text-[8px] text-muted-foreground">برد</p>
          <p className="num text-sm font-bold text-green-500">{s.wins}</p>
        </div>
        <div className="rounded-md bg-red-500/5 px-1.5 py-1">
          <p className="text-[8px] text-muted-foreground">باخت</p>
          <p className="num text-sm font-bold text-red-500">{s.losses}</p>
        </div>
        <div className="rounded-md bg-yellow-500/5 px-1.5 py-1">
          <p className="text-[8px] text-muted-foreground">انتظار</p>
          <p className="num text-sm font-bold text-yellow-500">{s.pending}</p>
        </div>
      </div>

      {/* ═══ Win Rate + PF ═══ */}
      <div className="grid grid-cols-2 gap-1.5">
        <div className="rounded-md border border-green-500/20 bg-green-500/5 px-2 py-1.5 text-center">
          <p className="text-[8px] text-muted-foreground">نرخ برد</p>
          <p className={`num text-sm font-bold ${winRateColor(s.win_rate)}`}>
            {s.win_rate.toFixed(1)}%
          </p>
        </div>
        <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-2 py-1.5 text-center">
          <p className="text-[8px] text-muted-foreground">ضریب سود</p>
          <p className="num text-sm font-bold text-blue-500">
            {s.profit_factor.toFixed(2)}
          </p>
        </div>
      </div>

      {/* ═══ دقت روند ═══ */}
      {s.trend_correct != null &&
        s.trend_wrong != null &&
        s.trend_correct + s.trend_wrong > 0 && (
          <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2">
            <div className="mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1 text-[9px] font-medium text-purple-400">
                🎯 دقت پیش‌بینی روند
              </span>
              <span className="num text-sm font-bold text-purple-400">
                {s.trend_accuracy?.toFixed(1) ?? "—"}٪
              </span>
            </div>
            <div className="flex items-center justify-between text-[9px] text-muted-foreground">
              <span className="text-green-500">✅ {s.trend_correct} درست</span>
              <span className="text-red-500">❌ {s.trend_wrong} غلط</span>
            </div>
          </div>
        )}

      {/* ═══ دقت TF ═══ */}
      {tfStats && Object.keys(tfStats).length > 0 && (
        <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2">
          <p className="mb-1.5 text-[9px] font-medium text-purple-400">
            🎯 دقت به تفکیک TF
          </p>
          <div className="space-y-1">
            {Object.entries(tfStats)
              .sort((a, b) => {
                const order = [
                  "۱ دقیقه",
                  "۵ دقیقه",
                  "۱۵ دقیقه",
                  "۳۰ دقیقه",
                  "۱ ساعت",
                  "روزانه",
                ];
                return order.indexOf(a[0]) - order.indexOf(b[0]);
              })
              .map(([tf, stat]) => {
                const acc = stat.trend_accuracy ?? 0;
                const total = stat.trend_total ?? 0;
                if (total === 0) return null;
                const color =
                  acc >= 70
                    ? "text-green-500 bg-green-500"
                    : acc >= 50
                      ? "text-yellow-500 bg-yellow-500"
                      : "text-red-500 bg-red-500";
                return (
                  <div
                    key={tf}
                    className="flex items-center gap-2 text-[9px]"
                  >
                    <span className="w-14 shrink-0 text-muted-foreground">
                      {tf}
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted/40">
                      <div
                        className={`h-full ${color.split(" ")[1]} transition-all`}
                        style={{ width: `${acc}%` }}
                      />
                    </div>
                    <span
                      className={`num w-10 shrink-0 text-left font-bold ${color.split(" ")[0]}`}
                    >
                      {acc.toFixed(0)}٪
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* ═══ تله‌ها ═══ */}
      {trapStats && trapStats.total > 0 && (
        <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-2.5">
          <p className="mb-1.5 text-[10px] font-medium text-orange-400">
            ⚠️ دقت هشدار تله‌ها
          </p>
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-muted-foreground">
              {trapStats.total} سیگنال با تله
            </span>
            <span className="num font-bold text-orange-400">
              {trapStats.accuracy.toFixed(0)}% درست
            </span>
          </div>
        </div>
      )}

      {/* ═══ دکمه‌ها ═══ */}
      <div className="grid grid-cols-3 gap-1.5">
        <Button
          onClick={handleRun}
          disabled={running}
          size="sm"
          variant="default"
        >
          {running ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          بررسی
        </Button>
        <Button
          onClick={handleDownload}
          disabled={downloading}
          size="sm"
          variant="outline"
        >
          {downloading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5" />
          )}
          JSON
        </Button>
        <Button
          onClick={() => setResetOpen(true)}
          size="sm"
          variant="outline"
          className="text-destructive hover:text-destructive"
        >
          <Trash2 className="h-3.5 w-3.5" />
          ریست
        </Button>
      </div>

      <ResetSignalsDialog
        open={resetOpen}
        onOpenChange={setResetOpen}
        onSuccess={handleResetSuccess}
      />
    </div>
  );
}