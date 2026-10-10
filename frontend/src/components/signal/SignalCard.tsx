"use client";

/**
 * SignalCard — کارت سیگنال (نسخه ۱۰.۰ · فاز ۱۰.۱)
 * ============================================================
 * 🔴 تغییرات نسخه ۱۰.۰:
 *   • Compact UI — ارتفاع ۳۰٪ کمتر بدون حذف اطلاعات
 *   • قیمت + سیگنال در یک نوار افقی
 *   • Sparkline ۶۰px
 *   • SL/TP/RR نازک‌تر
 *   • Regime + Consensus ادغام با آراء
 *   • لوگو پس‌زمینه + footer آدرس/تاریخ/ساعت
 */

import { useEffect, useRef, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  Shield,
  Percent,
  Star,
  ArrowRightLeft,
  AlertTriangle,
  Share2,
  Loader2,
  Info,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useAnalysisCapability } from "@/lib/hooks/useAnalysisCapability";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import {
  SOURCE_BY_KEY,
  sourceBadgeClass,
  sourceSupportsPair,
} from "@/lib/sources";
import { AnalysisUnavailable } from "@/components/signal/AnalysisUnavailable";
import { Sparkline } from "@/components/ui/sparkline";
import { CryptoIcon } from "@/components/ui/crypto-icon";
import type { AnalyzeResponse } from "@/lib/types";
import {
  regimeIcon,
  regimeFullFa,
  consensusFa,
  consensusColor,
  signalBg,
  formatNumber,
} from "@/lib/display";

const TRAP_LABELS: Record<string, string> = {
  bull_trap: "تله صعودی",
  bear_trap: "تله نزولی",
  fake_breakout: "شکست جعلی",
  exhaustion: "خستگی روند",
};

const MARKET_LABELS: Record<string, { fa: string; cls: string }> = {
  spot: {
    fa: "💵 اسپات",
    cls: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  },
  futures: {
    fa: "📈 فیوچرز",
    cls: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  },
};

const PROFILE_LABELS: Record<string, { fa: string; cls: string }> = {
  aggressive: {
    fa: "🚀 جسورانه",
    cls: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  },
  conservative: {
    fa: "🛡 محتاطانه",
    cls: "bg-green-500/15 text-green-400 border-green-500/30",
  },
};


export function SignalCard() {
  const {
    ticker,
    tickerName,
    source,
    timeframe,
    marketType,
    riskProfile,
    watchlist,
    addToWatchlist,
    removeFromWatchlist,
  } = useAppStore();

  const capability = useAnalysisCapability(source);
  const { quote, signal: wsSignal, status: wsStatus } = useWebSocket();
  const setWsSignal = useAppStore((s) => s.setWsSignal);

  // ═══ state ها ═══
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);

  const [priceFlash, setPriceFlash] = useState<"up" | "down" | null>(null);
  const [animPrice, setAnimPrice] = useState<number>(0);
  const [dotPulse, setDotPulse] = useState(false);
  const prevPriceRef = useRef<number | null>(null);
  const animRef = useRef<number>(0);
  const cardRef = useRef<HTMLDivElement>(null);

  const [sparklineSeries, setSparklineSeries] = useState<number[]>([]);
  const [sparklinePrice, setSparklinePrice] = useState<number>(0);

  // ═══ ساعت زنده ═══
  const [now, setNow] = useState<Date>(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // ═══ /analyze ═══
  useEffect(() => {
    if (!ticker) return;

    if (capability.planned || !sourceSupportsPair(source, ticker)) {
      let cancelled = false;
      queueMicrotask(() => {
        if (cancelled) return;
        setData(null);
        setError(null);
        setLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }

    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) {
        setLoading(true);
        setError(null);
      }
    });

    (async () => {
      try {
        const res = await api.post<AnalyzeResponse>("/analyze", {
          ticker,
          source,
          timeframe,
          market_type: marketType,
          risk_profile: riskProfile,
          ticker_name: tickerName,
        });
        if (cancelled) return;
        setData(res.data);
        setError(null);
      } catch (err: unknown) {
        if (cancelled) return;
        const detail = (err as { response?: { data?: { detail?: unknown } } })
          ?.response?.data?.detail;
        let msg = "تحلیل ناموفق بود";
        if (typeof detail === "string") msg = detail;
        else if (Array.isArray(detail) && detail.length > 0) {
          const first = detail[0] as { msg?: string } | undefined;
          msg = first?.msg || msg;
        }
        setError(msg);
        setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    ticker,
    tickerName,
    source,
    timeframe,
    marketType,
    riskProfile,
    capability.planned,
  ]);

  // ═══ wsSignal → data ═══
  useEffect(() => {
    if (wsSignal) {
      setData(wsSignal as unknown as AnalyzeResponse);
    }
  }, [wsSignal]);

  // ═══ wsSignal → store ═══
  useEffect(() => {
    if (!wsSignal) return;
    const sig = wsSignal as unknown as {
      ticker?: string;
      timeframe?: string;
      source?: string;
    };
    setWsSignal({
      ticker: String(sig.ticker || ""),
      timeframe: String(sig.timeframe || ""),
      source: sig.source || source,
      data: wsSignal,
      receivedAt: Date.now(),
    });
  }, [wsSignal, source, setWsSignal]);

  // ═══ Sparkline ═══
  useEffect(() => {
    if (!ticker) {
      setSparklineSeries([]);
      setSparklinePrice(0);
      return;
    }
    if (capability.planned || !sourceSupportsPair(source, ticker)) {
      setSparklineSeries([]);
      setSparklinePrice(0);
      return;
    }

    let cancelled = false;

    api
      .get<{
        ok: boolean;
        close_series: number[];
        price: number;
      }>("/analyze/sparkline", {
        params: { ticker, source, timeframe },
      })
      .then((res) => {
        if (cancelled) return;
        setSparklineSeries(res.data.close_series || []);
        setSparklinePrice(res.data.price || 0);

        if (res.data.price && res.data.price > 0) {
          if (prevPriceRef.current === null) {
            prevPriceRef.current = res.data.price;
            if (animRef.current === 0) {
              setAnimPrice(res.data.price);
              animRef.current = res.data.price;
            }
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSparklineSeries([]);
          setSparklinePrice(0);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ticker, source, timeframe, capability.planned]);

  // ═══ Flash + Count-up ═══
  const entryPrice = data?.price ?? 0;
  const livePrice = quote?.price ?? entryPrice ?? 0;

  useEffect(() => {
    if (!livePrice || livePrice <= 0) return;

    const prev = prevPriceRef.current;

    if (prev != null && prev !== livePrice) {
      const dir = livePrice > prev ? "up" : "down";
      setPriceFlash(dir);
      setDotPulse(true);

      const start = performance.now();
      const from = animRef.current || prev;
      const to = livePrice;
      const duration = 400;

      let rafId: number;
      const tick = (t: number) => {
        const elapsed = t - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const val = from + (to - from) * eased;

        setAnimPrice(val);
        animRef.current = val;

        if (progress < 1) {
          rafId = requestAnimationFrame(tick);
        } else {
          setAnimPrice(to);
          animRef.current = to;
        }
      };

      rafId = requestAnimationFrame(tick);

      const flashTimer = setTimeout(() => setPriceFlash(null), 400);
      const pulseTimer = setTimeout(() => setDotPulse(false), 700);
      prevPriceRef.current = livePrice;

      return () => {
        clearTimeout(flashTimer);
        clearTimeout(pulseTimer);
        cancelAnimationFrame(rafId);
      };
    } else {
      prevPriceRef.current = livePrice;
      if (animRef.current === 0) {
        setAnimPrice(livePrice);
        animRef.current = livePrice;
      }
    }
  }, [livePrice]);

  // ═══ Share ═══
  const handleShare = async () => {
    if (!cardRef.current || sharing || !data) return;
    setSharing(true);

    try {
      const { toBlob } = await import("html-to-image");

      const blob = await toBlob(cardRef.current, {
        backgroundColor: "#0a0e1a",
        pixelRatio: 2,
        cacheBust: true,
      });
      if (!blob) throw new Error("toBlob failed");

      const fileName = `trademun-${data.ticker}-${Date.now()}.png`;
      const file = new File([blob], fileName, { type: "image/png" });

      const isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
      const nav = navigator as Navigator & {
        canShare?: (d: { files: File[] }) => boolean;
      };
      if (
        isMobile &&
        typeof nav.share === "function" &&
        typeof nav.canShare === "function" &&
        nav.canShare({ files: [file] })
      ) {
        try {
          await nav.share({
            files: [file],
            title: `سیگنال ${data.ticker}`,
            text: `تحلیل ${data.name || data.ticker} از Trademun`,
          });
          return;
        } catch (err) {
          if ((err as Error)?.name === "AbortError") return;
        }
      }

      const link = document.createElement("a");
      link.download = fileName;
      const url = URL.createObjectURL(blob);
      link.href = url;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("[Share] خطا:", err);
    } finally {
      setSharing(false);
    }
  };

  // ═══ Early returns ═══
  if (capability.planned) {
    return (
      <AnalysisUnavailable
        message={capability.message}
        suggestion={capability.suggestion}
        alternatives={[]}
        variant="planned"
      />
    );
  }

  if (loading && !data) {
    return (
      <Card>
        <CardContent className="space-y-2 p-3">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <AnalysisUnavailable
        message="تحلیل برای این نماد در دسترس نیست"
        suggestion={error}
        variant="no-data"
      />
    );
  }

  if (!data) return null;

  // ═══ متغیرهای مشتق ═══
  const sl = data.sl;
  const tp = data.tp;
  const rr = data.rr;

  const displayChange = quote != null ? quote.change_pct : null;

  const distToSl =
    sl != null && livePrice > 0 ? ((livePrice - sl) / livePrice) * 100 : null;
  const distToTp =
    tp != null && livePrice > 0 ? ((tp - livePrice) / livePrice) * 100 : null;

  const SignalIcon =
    data.direction === "long"
      ? TrendingUp
      : data.direction === "short"
        ? TrendingDown
        : Minus;

  const requestedMeta = SOURCE_BY_KEY[source];
  const usedSource = data.source_used ?? source;
  const usedMeta = SOURCE_BY_KEY[usedSource] ?? requestedMeta;
  const isFallback = Boolean(data.is_fallback) && usedSource !== source;

  const inWatchlist = watchlist.some((w) => w.ticker === ticker);

  const activeTraps: string[] = [];
  const trapReasons: string[] = [];
  const traps = data.traps || {};
  for (const [key, val] of Object.entries(traps)) {
    const v = val as { active?: boolean; reason?: string } | null;
    if (v && v.active) {
      activeTraps.push(key);
      if (v.reason) trapReasons.push(v.reason);
    }
  }
  const trapLabel = activeTraps.map((k) => TRAP_LABELS[k] || k).join(" · ");

  const marketLabel =
    MARKET_LABELS[data.market_type || marketType] || MARKET_LABELS.spot;
  const profileLabel =
    PROFILE_LABELS[data.risk_profile || riskProfile] ||
    PROFILE_LABELS.aggressive;

  const totalVotes =
    (data.votes_long || 0) +
      (data.votes_neutral || 0) +
      (data.votes_short || 0) || 1;
  const longPct = ((data.votes_long || 0) / totalVotes) * 100;
  const neutralPct = ((data.votes_neutral || 0) / totalVotes) * 100;
  const shortPct = ((data.votes_short || 0) / totalVotes) * 100;

  const isDirectional =
    data.direction === "long" || data.direction === "short";

  const feeTooltipContent = (
    <div className="space-y-1.5 text-[11px]">
      <p className="font-bold">💸 اقتصاد معامله</p>
      {data.fee_pct != null && (
        <div>
          <p>
            کارمزد رفت‌وبرگشتی:{" "}
            <span className="num font-bold">{data.fee_pct.toFixed(2)}%</span>
          </p>
          {data.execution_cost && (
            <>
              <p className="text-muted-foreground">
                • کارمزد خالص:{" "}
                <span className="num">
                  {data.execution_cost.fee_pct.toFixed(2)}%
                </span>
              </p>
              <p className="text-muted-foreground">
                • اسپرد:{" "}
                <span className="num">
                  {data.execution_cost.spread_cost_pct.toFixed(2)}%
                </span>
              </p>
              <p className="text-muted-foreground">
                • اسلیپیج:{" "}
                <span className="num">
                  {data.execution_cost.slippage_pct.toFixed(2)}%
                </span>
              </p>
              <p className="mt-1">
                مجموع:{" "}
                <span className="num font-bold">
                  {data.execution_cost.total_pct.toFixed(2)}%
                </span>
              </p>
            </>
          )}
        </div>
      )}
      {data.breakeven_pct != null && (
        <p>
          نقطه سربه‌سر:{" "}
          <span className="num font-bold">
            {data.breakeven_pct.toFixed(2)}%
          </span>
        </p>
      )}
      {data.rr_gross != null && data.rr_net != null && (
        <p>
          R:R خام <span className="num">{data.rr_gross.toFixed(2)}</span> →
          خالص <span className="num">{data.rr_net.toFixed(2)}</span>
        </p>
      )}
      {data.rr_decay_pct != null && data.rr_decay_pct > 0 && (
        <p className="text-orange-400">
          افت R:R:{" "}
          <span className="num font-bold">{data.rr_decay_pct.toFixed(0)}%</span>
        </p>
      )}
      {data.sl_tp_scaled && data.scale_reason && (
        <p className="text-yellow-500">🔧 {data.scale_reason}</p>
      )}
    </div>
  );

  const wsConnected = wsStatus === "connected";

  const series =
    sparklineSeries.length >= 2
      ? sparklineSeries
      : data.close_series && data.close_series.length >= 2
        ? data.close_series
        : null;

  // ═══ رنگ سیگنال ═══
  const signalColor =
    data.direction === "long"
      ? "text-green-500"
      : data.direction === "short"
        ? "text-red-500"
        : "text-slate-400";

  return (
    <div
      ref={cardRef}
      data-signal-card
      className="relative overflow-hidden"
    >
      {/* 🔴 لوگو پس‌زمینه */}
      <div
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          backgroundImage: "url('/icon-192.png')",
          backgroundSize: "55%",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          opacity: 0.04,
        }}
      />

      <Card className={`relative z-10 border ${signalBg(data.signal)}`}>
        {/* ═══════════════════════════════════════════════════════
            ردیف هدر: نام + ticker + بج‌ها + دکمه‌ها
        ═══════════════════════════════════════════════════════ */}
        <div className="space-y-1.5 px-3 pt-2.5">
          {/* خط ۱: نام + دکمه‌ها */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 flex-1 items-center gap-1.5">
              <CryptoIcon ticker={data.ticker} size="md" />
              <p className="truncate text-sm font-bold">{data.name}</p>
            </div>
            <div className="flex shrink-0 items-center gap-0.5">
              <Tooltip>
                <TooltipTrigger>
                  <span
                    className={`flex items-center gap-0.5 rounded px-1 py-0.5 text-[8px] ${
                      wsConnected ? "text-green-500" : "text-orange-400"
                    }`}
                  >
                    {wsConnected ? (
                      <Wifi className="h-3 w-3" />
                    ) : (
                      <WifiOff className="h-3 w-3" />
                    )}
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-[10px]">
                    {wsConnected
                      ? "اتصال زنده فعال"
                      : wsStatus === "reconnecting"
                        ? "در حال اتصال مجدد…"
                        : "اتصال زنده قطع است"}
                  </p>
                </TooltipContent>
              </Tooltip>

              <button
                onClick={handleShare}
                disabled={sharing}
                className="rounded-md p-1 text-muted-foreground transition-colors hover:text-primary disabled:opacity-50"
                aria-label="اشتراک‌گذاری کارت"
                title="اشتراک‌گذاری کارت"
              >
                {sharing ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Share2 className="h-3.5 w-3.5" />
                )}
              </button>

              <button
                onClick={() =>
                  inWatchlist
                    ? removeFromWatchlist(ticker)
                    : addToWatchlist(ticker, tickerName || ticker, source)
                }
                className={`rounded-md p-1 transition-colors ${
                  inWatchlist
                    ? "text-yellow-500"
                    : "text-muted-foreground hover:text-yellow-500"
                }`}
                aria-label={
                  inWatchlist ? "حذف از واچ‌لیست" : "افزودن به واچ‌لیست"
                }
                aria-pressed={inWatchlist}
              >
                <Star
                  className={`h-3.5 w-3.5 ${inWatchlist ? "fill-current" : ""}`}
                />
              </button>
            </div>
          </div>

          {/* خط ۲: ticker + بج‌ها | صرافی + TF */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-1">
              <span className="num text-[10px] font-medium text-muted-foreground">
                {data.ticker}
              </span>
              <Badge className={`border py-0 text-[8px] ${marketLabel.cls}`}>
                {marketLabel.fa}
              </Badge>
              <Badge className={`border py-0 text-[8px] ${profileLabel.cls}`}>
                {profileLabel.fa}
              </Badge>
            </div>

            <div className="flex shrink-0 items-center gap-1">
              {isFallback ? (
                <Tooltip>
                  <TooltipTrigger>
                    <Badge
                      className={`gap-0.5 border py-0 text-[8px] ${sourceBadgeClass(usedSource)}`}
                    >
                      <ArrowRightLeft className="h-2 w-2" />
                      {usedMeta?.label}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-[11px]">
                      درخواست روی <b>{requestedMeta?.label}</b> بود ولی این
                      نماد/تایم‌فریم آنجا نبود — داده از{" "}
                      <b>{usedMeta?.label}</b> گرفته شد.
                    </p>
                  </TooltipContent>
                </Tooltip>
              ) : (
                <Badge
                  className={`border py-0 text-[8px] ${sourceBadgeClass(source)}`}
                >
                  {requestedMeta?.icon} {requestedMeta?.label}
                </Badge>
              )}

              <Badge variant="outline" className="py-0 text-[8px]">
                {data.timeframe}
              </Badge>
            </div>
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════
            بدنه کارت
        ═══════════════════════════════════════════════════════ */}
        <CardContent className="space-y-2 px-3 pb-2.5 pt-2">
          {/* ═══ Fallback warning ═══ */}
          {isFallback && (
            <p className="rounded-md border border-blue-500/20 bg-blue-500/5 px-2 py-1 text-[9px] text-blue-400">
              ℹ️ {requestedMeta?.label} این نماد را در {data.timeframe} ندارد
              — داده از {usedMeta?.label}
            </p>
          )}

          {/* ═══ Trap chip — با توضیح یک‌خطی ═══ */}
          {activeTraps.length > 0 && (
            <Tooltip>
              <TooltipTrigger>
                <div className="flex items-center gap-1.5 rounded-md border border-red-500/30 bg-red-500/10 px-2 py-1">
                  <AlertTriangle className="h-3 w-3 shrink-0 text-red-500" />
                  <span className="text-[9px] font-bold text-red-500 shrink-0">
                    احتمال {trapLabel}
                  </span>
                  {trapReasons[0] && (
                    <>
                      <span className="text-red-500/40">·</span>
                      <span className="truncate text-[9px] text-red-400/80">
                        {trapReasons[0].length > 45
                          ? trapReasons[0].slice(0, 45) + "…"
                          : trapReasons[0]}
                      </span>
                    </>
                  )}
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p className="text-[10px] leading-relaxed">
                  {trapReasons.join(" | ")}
                </p>
              </TooltipContent>
            </Tooltip>
          )}

          {/* ═══════════════════════════════════════════════════════
              قیمت + سیگنال — نوار افقی فشرده
          ═══════════════════════════════════════════════════════ */}
          <div className="rounded-lg bg-muted/40 px-2.5 py-2">
            <div className="flex items-center gap-3">
              {/* ─── چپ: قیمت ─── */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1 text-[9px] text-muted-foreground">
                  <span>قیمت زنده</span>
                  {wsConnected && (
                    <span
                      className={`inline-block h-1 w-1 rounded-full bg-green-500 ${
                        dotPulse ? "animate-ping" : ""
                      }`}
                    />
                  )}
                </div>
                <p
                  className={`num truncate text-lg font-bold leading-tight tracking-tight transition-colors duration-300 ${
                    priceFlash === "up"
                      ? "text-green-500"
                      : priceFlash === "down"
                        ? "text-red-500"
                        : ""
                  }`}
                >
                  {formatNumber(animPrice || livePrice)}
                </p>
                {/* زیرنویس: تغییر + ورود در یک خط */}
                <div className="num flex items-center gap-1.5 text-[9px]">
                  {displayChange != null && displayChange !== 0 ? (
                    <span
                      className={
                        displayChange >= 0 ? "text-green-500" : "text-red-500"
                      }
                    >
                      {displayChange >= 0 ? "▲" : "▼"}{" "}
                      {Math.abs(displayChange).toFixed(2)}%
                    </span>
                  ) : (
                    <span className="text-muted-foreground/50">—</span>
                  )}
                  {entryPrice > 0 && (
                    <span className="text-muted-foreground/70">
                      · ورود {formatNumber(entryPrice)}
                    </span>
                  )}
                </div>
              </div>

              {/* ─── جداکننده ─── */}
              <div className="h-12 w-px shrink-0 bg-border/40" />

              {/* ─── راست: سیگنال ─── */}
              <div className="shrink-0 text-center">
                <div className={`${signalColor}`}>
                  <SignalIcon className="mx-auto h-4 w-4" />
                  <p className="text-[13px] font-bold leading-none mt-0.5">
                    {data.signal}
                  </p>
                </div>
                <p className="num mt-1 text-[11px] font-bold text-blue-500">
                  {data.confidence}%
                </p>

                {/* نشان «قوی» */}
                {data.confidence >= 70 &&
                  isDirectional &&
                  !data.signal.includes("ضعیف") && (
                    <span
                      className="mt-1 inline-flex items-center gap-0.5 rounded border px-1 py-0 text-[8px] font-bold"
                      style={{
                        background: data.signal.includes("LONG")
                          ? "rgba(34,197,94,0.15)"
                          : "rgba(239,68,68,0.15)",
                        borderColor: data.signal.includes("LONG")
                          ? "rgba(34,197,94,0.4)"
                          : "rgba(239,68,68,0.4)",
                        color: data.signal.includes("LONG")
                          ? "#4ade80"
                          : "#f87171",
                        textShadow: data.signal.includes("LONG")
                          ? "0 0 6px rgba(34,197,94,0.8)"
                          : "0 0 6px rgba(239,68,68,0.8)",
                      }}
                    >
                      ⚡ قوی
                    </span>
                  )}
              </div>
            </div>
          </div>

          {/* ═══════════════════════════════════════════════════════
              Sparkline — ۶۰px
          ═══════════════════════════════════════════════════════ */}
          {series ? (
            <Sparkline
              data={series}
              height={60}
              showArea
              showDot
              sl={sl}
              tp={tp}
              entry={entryPrice}
              color={
                data.signal.includes("LONG") ||
                data.signal.includes("صعودی")
                  ? "green"
                  : data.signal.includes("SHORT") ||
                      data.signal.includes("نزولی")
                    ? "red"
                    : "neutral"
              }
            />
          ) : (
            <div
              className="relative flex items-center justify-center overflow-hidden rounded-md bg-muted/10"
              style={{ height: 60 }}
            >
              <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/5 to-transparent" />
              <div className="relative flex items-center gap-2 text-[10px] text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>در حال پردازش نمودار…</span>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              SL/TP/RR — نازک‌تر
          ═══════════════════════════════════════════════════════ */}
          {sl != null && tp != null && (
            <div className="grid grid-cols-3 gap-1.5">
              {/* SL */}
              <div className="rounded-md border border-red-500/20 bg-red-500/5 px-1.5 py-1 text-center">
                <div className="flex items-center justify-center gap-0.5 text-[8px] text-muted-foreground">
                  <Shield className="h-2.5 w-2.5" />
                  حد ضرر
                </div>
                <p className="num mt-0.5 truncate text-[10px] font-bold text-red-500">
                  {formatNumber(sl)}
                </p>
                {distToSl != null && (
                  <p className="num text-[8px] text-muted-foreground">
                    {distToSl >= 0 ? "−" : "+"}
                    {Math.abs(distToSl).toFixed(2)}%
                  </p>
                )}
              </div>

              {/* R:R */}
              <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-1.5 py-1 text-center">
                <div className="flex items-center justify-center gap-0.5 text-[8px] text-muted-foreground">
                  <Percent className="h-2.5 w-2.5" />
                  R:R
                </div>
                <p className="num mt-0.5 text-[11px] font-bold text-blue-500">
                  {data.rr_net != null
                    ? data.rr_net.toFixed(2)
                    : rr != null
                      ? rr.toFixed(2)
                      : "—"}
                </p>
                {data.rr_gross != null && data.rr_net != null && (
                  <p className="num text-[8px] text-muted-foreground">
                    خام {data.rr_gross.toFixed(2)}
                  </p>
                )}
              </div>

              {/* TP */}
              <div className="rounded-md border border-green-500/20 bg-green-500/5 px-1.5 py-1 text-center">
                <div className="flex items-center justify-center gap-0.5 text-[8px] text-muted-foreground">
                  <Target className="h-2.5 w-2.5" />
                  هدف
                </div>
                <p className="num mt-0.5 truncate text-[10px] font-bold text-green-500">
                  {formatNumber(tp)}
                </p>
                {distToTp != null && (
                  <p className="num text-[8px] text-muted-foreground">
                    {distToTp >= 0 ? "+" : "−"}
                    {Math.abs(distToTp).toFixed(2)}%
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              اقتصاد معامله — فشرده
          ═══════════════════════════════════════════════════════ */}
          {data.fee_pct != null && (
            <div
              className={`flex items-center justify-between gap-2 rounded-md px-2 py-1 text-[9px] ${
                data.timeframe_viable === false ||
                data.is_worthwhile === false
                  ? "border border-orange-500/25 bg-orange-500/5 text-orange-400"
                  : "bg-muted/20 text-muted-foreground"
              }`}
            >
              <span className="flex items-center gap-1">
                {data.timeframe_viable === false ||
                data.is_worthwhile === false
                  ? "⚠️ "
                  : "ℹ️ "}
                هزینه{" "}
                <span className="num font-medium">
                  {data.fee_pct.toFixed(2)}%
                </span>
                {data.rr_decay_pct != null && data.rr_decay_pct > 0 && (
                  <>
                    {" "}
                    · افت R:R{" "}
                    <span className="num">
                      {data.rr_decay_pct.toFixed(0)}%
                    </span>
                  </>
                )}
                <Tooltip>
                  <TooltipTrigger>
                    <span className="ml-0.5 inline-flex items-center text-muted-foreground/70 transition-colors hover:text-foreground">
                      <Info className="h-3 w-3" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs border-border bg-popover text-popover-foreground">
                    {feeTooltipContent}
                  </TooltipContent>
                </Tooltip>
              </span>
              {data.rr_net != null && (
                <span className="num font-medium">
                  خالص {data.rr_net.toFixed(2)}
                </span>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              Regime + Consensus + آراء — ادغام‌شده
          ═══════════════════════════════════════════════════════ */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-2 text-[9px] text-muted-foreground">
              <span>
                {regimeIcon(data.regime)} {regimeFullFa(data.regime)}
              </span>
              <span className={consensusColor(data.consensus)}>
                {consensusFa(data.consensus)}
              </span>
            </div>

            {/* نوار آراء */}
            <div className="flex h-2 w-full overflow-hidden rounded-full bg-muted/40">
              {longPct > 0 && (
                <div
                  className="bg-green-500 transition-all duration-300"
                  style={{ width: `${longPct}%` }}
                  title={`صعودی ${data.votes_long}`}
                />
              )}
              {neutralPct > 0 && (
                <div
                  className="bg-yellow-500 transition-all duration-300"
                  style={{ width: `${neutralPct}%` }}
                  title={`خنثی ${data.votes_neutral}`}
                />
              )}
              {shortPct > 0 && (
                <div
                  className="bg-red-500 transition-all duration-300"
                  style={{ width: `${shortPct}%` }}
                  title={`نزولی ${data.votes_short}`}
                />
              )}
            </div>

            <div className="flex items-center justify-between text-[8px] text-muted-foreground">
              <span className="text-green-500">
                ▲ {data.votes_long} صعودی
              </span>
              <span className="text-yellow-500">
                ● {data.votes_neutral} خنثی
              </span>
              <span className="text-red-500">
                ▼ {data.votes_short} نزولی
              </span>
            </div>
          </div>
        </CardContent>

        {/* ═══════════════════════════════════════════════════════
            Footer: آدرس + تاریخ + ساعت
        ═══════════════════════════════════════════════════════ */}
        <div className="flex items-center justify-between border-t border-border/20 px-3 pb-2 pt-1.5 text-[9px]">
          <span
            className="text-muted-foreground/50"
            style={{ fontFamily: "monospace", letterSpacing: "0.3px" }}
          >
            trademun.ir
          </span>
          <span
            className="num flex items-center gap-1 text-muted-foreground/60"
            style={{ fontFamily: "monospace" }}
          >
            <span>
              {(() => {
                const parts = new Intl.DateTimeFormat("fa-IR-u-nu-latn", {
                  year: "numeric",
                  month: "2-digit",
                  day: "2-digit",
                  timeZone: "Asia/Tehran",
                }).formatToParts(now);
                return parts.map((p) => p.value).join("");
              })()}
            </span>
            <span className="text-muted-foreground/30">·</span>
            <span className="text-muted-foreground/80">
              {new Intl.DateTimeFormat("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false,
                timeZone: "Asia/Tehran",
              }).format(now)}
            </span>
          </span>
        </div>
      </Card>
    </div>
  );
}