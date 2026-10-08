"use client";

/**
 * BacktestStats — آمار راستی‌آزمایی
 * ============================================================
 * نسخه ۳.۰ · فاز ۷.۵
 *
 * ═══ تغییرات نسخه ۳.۰ ═══
 *   • فیلترها حذف شدن (توی BacktestPanel هستن)
 *   • source, profile, time از prop میان
 */

import { useCallback, useEffect, useState } from "react";
import {
  Download,
  Loader2,
  RefreshCw,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { BacktestResponse, SignalHistoryItem } from "@/lib/types";
import { ResetSignalsDialog } from "@/components/backtest/ResetSignalsDialog";
import { Clock } from "lucide-react";

const HISTORY_LIMIT = 500;

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
    items: SignalHistoryItem[];
    loading: boolean;
    error: string;
  }

  const [state, setState] = useState<StatsState>({
    data: null,
    items: [],
    loading: true,
    error: "",
  });
  const { data, items, loading, error } = state;

  const [running, setRunning] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [notice, setNotice] = useState("");
  const [resetOpen, setResetOpen] = useState(false);

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

  // ═══ 🔴 فاز ۸.۵ — آخرین زمان بررسی ═══
  const lastCheckTime = (() => {
    if (!items || items.length === 0) return null;
    // ─── آخرین سیگنالی که نتیجه‌ش مشخص شده ───
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
        params: {
          time_filter: time,
          risk_profile: profile,
        },
      })
      .then((res) => {
        if (cancelled) return;
        setTfStats(res.data.items || {});
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

  // ═══ دریافت آمار ═══
  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [statsRes, historyRes] = await Promise.all([
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
        ]);
        if (cancelled) return;
        setState({
          data: statsRes.data,
          items: historyRes.data?.items ?? [],
          loading: false,
          error: "",
        });
      } catch {
        if (cancelled) return;
        setState({
          data: null,
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
      const [statsRes, historyRes] = await Promise.all([
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
      ]);
      setState({
        data: statsRes.data,
        items: historyRes.data?.items ?? [],
        loading: false,
        error: "",
      });
    } catch {
      setState({
        data: null,
        items: [],
        loading: false,
        error: "دریافت آمار ناموفق بود — اتصال به سرور را چک کن",
      });
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
          ? "راستی‌آزمایی همین حالا در حال اجراست — چند لحظه بعد تلاش کن"
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
        <span className="text-[10px]">
          اسکن خودکار هر ۱ ساعت اجرا می‌شه.
        </span>
      </p>
    );
  }

  const winRateColor =
    s.win_rate >= 55
      ? "text-green-500"
      : s.win_rate >= 45
        ? "text-yellow-500"
        : "text-red-500";

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

      {/* ═══ 🔴 راهنمای راستی‌آزمایی ═══ */}
      <div className="rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-[9px] leading-relaxed text-muted-foreground">
        📊 <b className="text-foreground/80">نرخ برد</b>: فقط سیگنال‌های
        قطعی (بدون «ضعیف»). ·{" "}
        🎯 <b className="text-foreground/80">پیش‌بینی روند</b>: اگه قیمت
        بیش از <b className="num">۰.۰۵٪</b> در جهت درست حرکت کنه.
      </div>


      {/* ═══ 🔴 آخرین بررسی ═══ */}
      {lastCheckTime && (
        <div className="flex items-center justify-center gap-1.5 rounded-md bg-muted/20 px-2 py-1 text-[10px] text-muted-foreground">
          <Clock className="h-3 w-3" />
          آخرین بررسی:
          <span className="num font-medium text-foreground">
            {formatLastCheck(lastCheckTime)}
          </span>
        </div>
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
          <p className="num text-sm font-bold text-yellow-500">
            {s.pending}
          </p>
        </div>
      </div>

      {/* ═══ Win Rate + PF — فشرده ═══ */}
      <div className="grid grid-cols-2 gap-1.5">
        <div className="rounded-md border border-green-500/20 bg-green-500/5 px-2 py-1.5 text-center">
          <p className="text-[8px] text-muted-foreground">نرخ برد</p>
          <p className={`num text-sm font-bold ${winRateColor}`}>
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


      {/* ═══ Trend Accuracy ═══ */}
      {s.trend_correct != null &&
        s.trend_wrong != null &&
        s.trend_correct + s.trend_wrong > 0 && (
          <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2">
            <div className="flex items-center justify-between mb-1">
              <span className="flex items-center gap-1 text-[9px] font-medium text-purple-400">
                🎯 دقت پیش‌بینی روند
              </span>
              <span className="num text-sm font-bold text-purple-400">
                {s.trend_accuracy?.toFixed(1) ?? "—"}٪
              </span>
            </div>            <div className="flex items-center justify-between text-[9px] text-muted-foreground">
              <span className="text-green-500">
                ✅ {s.trend_correct} درست
              </span>
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
                        className={`h-full ${
                          color.split(" ")[1]
                        } transition-all`}
                        style={{ width: `${acc}%` }}
                      />
                    </div>
                    <span
                      className={`num w-10 shrink-0 text-left font-bold ${
                        color.split(" ")[0]
                      }`}
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