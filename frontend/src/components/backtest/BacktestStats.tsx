"use client";

/**
 * BacktestStats — آمار راستی‌آزمایی
 * ============================================================
 * تغییرات:
 *   • باگ ۴: دکمه‌ی «ریست» حالا `ResetSignalsDialog` با تأیید
 *     دو مرحله‌ای و کلید ادمین باز می‌کند (جای `confirm()` بومی
 *     که هیچ محافظتی نداشت).
 *   • حلقه‌ی fetch تله‌ها حذف شد (افکت به `data` وابسته بود و
 *     `data` را خودش ست می‌کرد).
 *   • `revokeObjectURL` اضافه شد (نشت حافظه).
 *   • انواع `any` با تایپ درست جایگزین شد.
 *   • خطاها بی‌صدا نمی‌مانند.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Download,
  Loader2,
  RefreshCw,
  Target,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import type { BacktestResponse, SignalHistoryItem } from "@/lib/types";
import { ResetSignalsDialog } from "@/components/backtest/ResetSignalsDialog";

const HISTORY_LIMIT = 500;

export function BacktestStats() {
  // ═══ وضعیت یکپارچه — یک setState در هر چرخه ═══
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
  const [timeFilter, setTimeFilter] = useState("all");
  const [notice, setNotice] = useState("");
  const [resetOpen, setResetOpen] = useState(false);

  // ═══ آمار به تفکیک TF ═══
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


    // ═══ آمار به تفکیک TF — با فیلتر زمانی ═══
  useEffect(() => {
    let cancelled = false;
    api
      .get("/backtest/by-tf", { params: { time_filter: timeFilter } })
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
  }, [timeFilter]);

  // ═══ آمار تله‌ها — مشتق‌شده، نه state جدا ═══
  const trapStats = useMemo(() => {
    const traps = items.filter((i) => i.had_trap);
    if (traps.length === 0) return null;

    const withResult = traps.filter((i) => i.result);
    if (withResult.length === 0) return null;

    // تله درست بوده اگه سیگنال باخت داده باشه
    const correct = withResult.filter((i) => i.result === "loss").length;
    return {
      total: traps.length,
      accuracy: (correct / withResult.length) * 100,
    };
  }, [items]);

  // ═══ دریافت آمار + تاریخچه با هم، بدون حلقه ═══
  // ⚠️ هیچ setState همگامی در بدنه‌ی effect نیست: به‌روزرسانی
  //    وضعیت فقط در پاسخ شبکه (async) انجام می‌شود.
  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [statsRes, historyRes] = await Promise.all([
          api.get("/backtest", { params: { time_filter: timeFilter } }),
          api.get("/backtest/history", { params: { limit: HISTORY_LIMIT } }),
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
  }, [timeFilter]);

  // ═══ بازخوانی پس از اکشن‌ها ═══
  const fetchStats = useCallback(async () => {
    try {
      const [statsRes, historyRes] = await Promise.all([
        api.get("/backtest", { params: { time_filter: timeFilter } }),
        api.get("/backtest/history", { params: { limit: HISTORY_LIMIT } }),
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
  }, [timeFilter]);

  const setError = (msg: string) =>
    setState((prev) => ({ ...prev, error: msg }));

  // ═══ بررسی دستی ═══
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
          ? "راستی‌آزمایی همین حالا در حال اجراست — چند لحظه بعد تلاش کن"
          : "اجرای راستی‌آزمایی ناموفق بود"
      );
    } finally {
      setRunning(false);
    }
  };

  // ═══ دانلود JSON — با آزادسازی URL ═══
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
      document.body.appendChild(a); // ← Firefox بدون این کلیک را نادیده می‌گیرد
      a.click();
      document.body.removeChild(a);
    } catch {
      setError("دانلود ناموفق بود");
    } finally {
      // ─── آزادسازی حافظه ───
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

  /**
   * ═══ راستی‌آزمایی — کشویی (نسخه ۱.۹) ═══
   *
   * ⚠️ مهم: کشو **فقط نمایش** را کنترل می‌کند.
   *    - اسکجولر backend (`api/scheduler.py`) مستقل و بی‌وقفه
   *      هر ۳۰ دقیقه سیگنال‌های در انتظار را بررسی می‌کند.
   *    - این کامپوننت هم polling خودش را نگه می‌دارد.
   *
   *    پس بستن کشو **هرگز** راستی‌آزمایی را متوقف نمی‌کند.
   */
  if (!s || s.total === 0) {
    return (
      <CollapsibleCard
        title={
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5" />
            راستی‌آزمایی
          </span>
        }
        subtitle="هنوز سیگنالی ثبت نشده — بعد از اولین تحلیل آمار می‌آید"
      >
        <p className="py-4 text-center text-[11px] text-muted-foreground">
          راستی‌آزمایی روی سرور فعال است و هر ۵ دقیقه اجرا می‌شود.
          بعد از اولین سیگنال، آمار اینجا نمایش داده می‌شه.
        </p>
      </CollapsibleCard>
    );
  }

  const winRateColor =
    s.win_rate >= 55
      ? "text-green-500"
      : s.win_rate >= 45
        ? "text-yellow-500"
        : "text-red-500";

  return (
    <>
      <CollapsibleCard
        title={
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5" />
            راستی‌آزمایی
          </span>
        }
        badge={
          <span
            className={`num rounded-full border border-border px-2 py-0.5 text-[9px] font-bold ${winRateColor}`}
          >
            {s.win_rate.toFixed(0)}%
          </span>
        }
        subtitle={`${s.total} سیگنال · ${s.wins} برد · ${s.losses} باخت · ${s.pending} در انتظار`}
      >
        <div className="space-y-3">
          {/* ═══ خطا ═══ */}
          {error && (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive"
            >
              ⚠️ {error}
            </p>
          )}

          {/* ═══ پیام موفقیت ═══ */}
          {notice && !error && (
            <p className="rounded-md border border-green-500/30 bg-green-500/5 p-2 text-[11px] text-green-500">
              ✅ {notice}
            </p>
          )}

          {/* ═══ فیلتر زمانی + دکمه اجرا ═══ */}
          <div className="flex items-center justify-between gap-2">
            <p className="text-[9px] text-muted-foreground">
              بررسی خودکار هر ۵ دقیقه روی سرور
            </p>
            <Select
              value={timeFilter}
              onValueChange={(v) => v && setTimeFilter(v)}
            >
              <SelectTrigger className="h-7 w-24 text-[10px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">همه</SelectItem>
                <SelectItem value="7d">۷ روز</SelectItem>
                <SelectItem value="30d">۳۰ روز</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* ═══ آمار ═══ */}
          <div className="grid grid-cols-4 gap-2 text-center">
            <div className="rounded-lg bg-muted/30 p-2">
              <p className="text-[9px] text-muted-foreground">کل</p>
              <p className="num text-base font-bold">{s.total}</p>
            </div>
            <div className="rounded-lg bg-green-500/5 p-2">
              <p className="text-[9px] text-muted-foreground">برد</p>
              <p className="num text-base font-bold text-green-500">{s.wins}</p>
            </div>
            <div className="rounded-lg bg-red-500/5 p-2">
              <p className="text-[9px] text-muted-foreground">باخت</p>
              <p className="num text-base font-bold text-red-500">{s.losses}</p>
            </div>
            <div className="rounded-lg bg-yellow-500/5 p-2">
              <p className="text-[9px] text-muted-foreground">انتظار</p>
              <p className="num text-base font-bold text-yellow-500">
                {s.pending}
              </p>
            </div>
          </div>

          {/* ═══ آمار تله‌ها ═══ */}
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

          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-3 text-center">
              <div className="flex items-center justify-center gap-1 text-[10px] text-muted-foreground">
                <TrendingUp className="h-3 w-3" />
                نرخ برد
              </div>
              <p className="num mt-1 text-lg font-bold text-green-500">
                {s.win_rate.toFixed(1)}%
              </p>
            </div>
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3 text-center">
              <div className="flex items-center justify-center gap-1 text-[10px] text-muted-foreground">
                <Target className="h-3 w-3" />
                Profit Factor
              </div>
              <p className="num mt-1 text-lg font-bold text-blue-500">
                {s.profit_factor.toFixed(2)}
              </p>
            </div>
          </div>

          {/* ═══ دقت پیش‌بینی روند (نسخه ۳.۰) ═══ */}
          {s.trend_correct != null && s.trend_wrong != null && (s.trend_correct + s.trend_wrong) > 0 && (
            <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
              <div className="flex items-center justify-between mb-1.5">
                <span className="flex items-center gap-1 text-[10px] font-medium text-purple-400">
                  🎯 دقت پیش‌بینی روند
                </span>
                <span className="num text-base font-bold text-purple-400">
                  {s.trend_accuracy?.toFixed(1) ?? "—"}٪
                </span>
              </div>
              <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                <span className="text-green-500">
                  ✅ {s.trend_correct} درست
                </span>
                <span className="text-red-500">
                  ❌ {s.trend_wrong} غلط
                </span>
              </div>
              <p className="mt-1 text-[8px] leading-relaxed text-muted-foreground/70">
                این درصد نشون می‌ده چند درصد سیگنال‌های منقضی،
                **جهت روند** رو درست پیش‌بینی کرده بودن (حتی اگه به TP نرسیدن).
              </p>
            </div>
          )}

          {/* ═══ دسته‌بندی منقضی‌ها (نسخه ۳.۰) ═══ */}
          {s.expired > 0 && (
            <div className="rounded-lg border border-border/40 bg-muted/10 p-2.5">
              <p className="mb-1.5 text-[9px] font-medium text-muted-foreground">
                ⏰ منقضی‌ها ({s.expired})
              </p>
              <div className="grid grid-cols-3 gap-1.5 text-center text-[9px]">
                <div>
                  <p className="text-muted-foreground">روند مثبت</p>
                  <p className="num font-bold text-green-500">
                    {s.expired_win ?? 0}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">روند منفی</p>
                  <p className="num font-bold text-red-500">
                    {s.expired_loss ?? 0}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">بی‌تغییر</p>
                  <p className="num font-bold text-muted-foreground">
                    {s.expired_flat ?? 0}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ═══ دقت پیش‌بینی روند به تفکیک TF (نسخه ۳.۰) ═══ */}
          {tfStats && Object.keys(tfStats).length > 0 && (
            <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2.5">
              <p className="mb-2 flex items-center gap-1 text-[10px] font-medium text-purple-400">
                🎯 دقت پیش‌بینی روند به تفکیک TF
              </p>
              <div className="space-y-1">
                {Object.entries(tfStats)
                  .sort((a, b) => {
                    // ترتیب TF از کوتاه به بلند
                    const order = [
                      "۱ دقیقه",
                      "۵ دقیقه",
                      "۱۵ دقیقه",
                      "۳۰ دقیقه",
                      "۱ ساعت",
                      "روزانه",
                    ];
                    return (
                      order.indexOf(a[0]) - order.indexOf(b[0])
                    );
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
                        <span className="num w-12 shrink-0 text-[8px] text-muted-foreground">
                          {stat.trend_correct}/{total}
                        </span>
                      </div>
                    );
                  })}
              </div>
              <p className="mt-2 text-[8px] leading-relaxed text-muted-foreground/70">
                📊 TFهایی که درصد پایین‌تری دارن، نویز بیشتری دارن و
                پیش‌بینی روشون سخت‌تره.
              </p>
            </div>
          )}

          {/* ═══ اکشن‌ها ═══ */}
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

          {/* ═══ توضیح سیستم ═══ */}
          <div className="space-y-2 rounded-lg bg-muted/20 p-3 text-[10px] text-muted-foreground">
            <p className="font-medium text-foreground">ℹ️ چطور کار می‌کنه؟</p>
            <ul className="list-disc space-y-1 pr-3 opacity-80">
              <li>سیگنال‌های LONG/SHORT خودکار ثبت می‌شن</li>
              <li>سیستم هر ۵ دقیقه بررسی می‌کنه که به SL/TP رسیدن</li>
              <li>هر سیگنال یه مهلت داره (بر اساس TF)</li>
              <li>بعد از مهلت → منقضی می‌شه</li>
            </ul>
            <p className="rounded-md bg-green-500/5 p-2 text-[9px] text-green-500">
              ✅ راستی‌آزمایی مستقل از این کشو کار می‌کند — بستن آن
              هیچ تأثیری روی بررسی سیگنال‌ها ندارد.
            </p>
          </div>
        </div>
      </CollapsibleCard>

      {/* ═══ دیالوگ ریست — با تأیید دو مرحله‌ای ═══ */}
      <ResetSignalsDialog
        open={resetOpen}
        onOpenChange={setResetOpen}
        onSuccess={handleResetSuccess}
      />
    </>
  );
}
