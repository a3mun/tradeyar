"use client";

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
import {
  SOURCE_BY_KEY,
  sourceBadgeClass,
  sourceSupportsPair,
} from "@/lib/sources";
import { AnalysisUnavailable } from "@/components/signal/AnalysisUnavailable";
import type { AnalyzeResponse, QuoteResponse } from "@/lib/types";
import {
  regimeIcon,
  regimeFullFa,
  consensusFa,
  consensusColor,
  signalColor,
  signalBg,
  confidenceColor,
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


// ═══ بازه‌ی به‌روزرسانی خودکار (ثانیه) ═══
// چرا ثابت: سیستم همیشه زنده باید باشه، کاربر نیازی به تنظیم نداره.
const REFRESH_SECONDS = 60;

function useLiveQuote(ticker: string, source: string, enabled: boolean) {
  const [price, setPrice] = useState<number | null>(null);
  const [change, setChange] = useState<number>(0);
  const [available, setAvailable] = useState<boolean>(true);

  useEffect(() => {
    if (!enabled || !ticker) return;

    let cancelled = false;

    const fetchQuote = () => {
      if (document.hidden) return;
      api
        .get<QuoteResponse>("/analyze/quote", { params: { ticker, source } })
        .then((res) => {
          if (cancelled) return;
          setPrice(res.data.price);
          setChange(res.data.change_pct || 0);
          setAvailable(true);
        })
        .catch(() => {
          if (cancelled) return;
          setPrice(null);
          setChange(0);
          setAvailable(false);
        });
    };

    fetchQuote();
    const id = setInterval(fetchQuote, 5000);
    const onVisible = () => {
      if (!document.hidden) fetchQuote();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      cancelled = true;
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [ticker, source, enabled]);

  return { price, change, available };
}

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

  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState("");
  const [sharing, setSharing] = useState(false);

  const cardRef = useRef<HTMLDivElement>(null);

  const {
    price: livePrice,
    change: liveChange,
    available: quoteAvailable,
  } = useLiveQuote(ticker, source, !!ticker);

  // ═══ آپدیت ساعت هر ثانیه ═══
  useEffect(() => {
    const update = () => {
      setLastUpdate(
        new Intl.DateTimeFormat("fa-IR", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }).format(new Date())
      );
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  // ═══ دریافت تحلیل (با Timer خودکار) ═══
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

    const loadAnalysis = async (showLoading: boolean) => {
      if (showLoading) {
        queueMicrotask(() => {
          if (!cancelled) {
            setLoading(true);
            setError(null);
          }
        });
      }

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
        if (!cancelled && showLoading) setLoading(false);
      }
    };

    // ─── بار اول: با loading ───
    loadAnalysis(true);

    // ─── Timer خودکار: اگه refreshSeconds > 0 ───
    const intervalId = setInterval(() => {
      if (!document.hidden) {
        loadAnalysis(false);
      }
    }, REFRESH_SECONDS * 1000);
    
    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
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

  // ═══ اشتراک‌گذاری ═══
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
        <CardContent className="space-y-3 p-3">
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

  const entryPrice = data.price ?? 0;
  const sl = data.sl;
  const tp = data.tp;
  const rr = data.rr;

  const displayPrice = livePrice ?? entryPrice;
  const displayChange = livePrice != null ? liveChange : null;

  const distToSl =
    sl != null && displayPrice > 0
      ? ((displayPrice - sl) / displayPrice) * 100
      : null;
  const distToTp =
    tp != null && displayPrice > 0
      ? ((tp - displayPrice) / displayPrice) * 100
      : null;

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
  const trapsDetails = trapReasons.join(" | ");

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

  return (
    <div ref={cardRef}>
      <Card className={`border ${signalBg(data.signal)}`}>
        <div className="space-y-2 p-3 pb-2">
          {/* خط ۱: نام + دکمه‌ها */}
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold">{data.name}</p>
            </div>
            <div className="flex shrink-0 items-center gap-0.5">
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

        <CardContent className="space-y-2.5 px-3 pb-3 pt-1">
          {isFallback && (
            <p className="rounded-md border border-blue-500/20 bg-blue-500/5 p-1.5 text-[9px] text-blue-400">
              ℹ️ {requestedMeta?.label} این نماد را در {data.timeframe} ندارد
              — تحلیل با داده‌ی {usedMeta?.label}
            </p>
          )}

          {activeTraps.length > 0 && (
            <div className="flex items-start gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 p-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
              <div className="min-w-0 flex-1 space-y-0.5">
                <p className="text-[10px] font-bold text-red-500">
                  ⚠️ احتمال {trapLabel}
                </p>
                {trapsDetails && (
                  <p className="text-[8px] leading-relaxed text-red-400/80">
                    {trapsDetails}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* قیمت + سیگنال */}
          <div className="rounded-lg bg-muted/40 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-[9px] text-muted-foreground">قیمت زنده</p>
                <p className="num truncate text-lg font-bold leading-tight tracking-tight sm:text-xl">
                  {formatNumber(displayPrice)}
                </p>
                {displayChange != null && displayChange !== 0 && (
                  <p
                    className={`num text-[9px] ${
                      displayChange >= 0 ? "text-green-500" : "text-red-500"
                    }`}
                  >
                    {displayChange >= 0 ? "▲" : "▼"}{" "}
                    {Math.abs(displayChange).toFixed(2)}%
                    {entryPrice > 0 && (
                      <span className="mr-1.5 text-muted-foreground">
                        · ورود{" "}
                        <span className="num">
                          {formatNumber(entryPrice)}
                        </span>
                      </span>
                    )}
                  </p>
                )}
                {displayChange === 0 && entryPrice > 0 && (
                  <p className="text-[9px] text-muted-foreground">
                    ورود تحلیل:{" "}
                    <span className="num">{formatNumber(entryPrice)}</span>
                  </p>
                )}
              </div>

              <div className="h-9 w-px shrink-0 bg-border/40" />

              <div
                className={`shrink-0 text-center ${signalColor(data.signal)}`}
              >
                <SignalIcon className="mx-auto h-3.5 w-3.5" />
                <p className="text-[13px] font-bold leading-none">
                  {data.signal}
                </p>
                <p
                  className={`num mt-0.5 text-[10px] font-bold ${confidenceColor(data.confidence)}`}
                >
                  {data.confidence}%
                </p>
              </div>
            </div>
          </div>

          {/* SL/TP */}
          {sl != null && tp != null && (
            <div className="grid grid-cols-3 gap-1.5">
              <div className="rounded-md border border-red-500/20 bg-red-500/5 px-1.5 py-1.5 text-center">
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

              <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-1.5 py-1.5 text-center">
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

              <div className="rounded-md border border-green-500/20 bg-green-500/5 px-1.5 py-1.5 text-center">
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

          {/* اقتصاد معامله */}
          {data.fee_pct != null && (
            <div
              className={`flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-[9px] ${
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

          {/* وضعیت + اجماع + زمان */}
          <div className="flex items-center justify-between gap-2 text-[9px] text-muted-foreground">
            <span>
              {regimeIcon(data.regime)} {regimeFullFa(data.regime)}
            </span>
            <span className={consensusColor(data.consensus)}>
              {consensusFa(data.consensus)}
            </span>
            {lastUpdate && <span className="num opacity-70">{lastUpdate}</span>}
          </div>

          {/* نوار آراء */}
          <div className="space-y-1">
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

          {!quoteAvailable && (
            <p className="text-center text-[8px] text-muted-foreground">
              ⚠️ قیمت زنده از {requestedMeta?.label} در دسترس نیست — قیمت
              تحلیل نمایش داده می‌شود
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}