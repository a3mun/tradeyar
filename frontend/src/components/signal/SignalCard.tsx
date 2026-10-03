"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  Shield,
  Percent,
  Star,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import type { AnalyzeResponse } from "@/lib/types";
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

const SOURCE_BADGE: Record<string, { color: string; label: string }> = {
  nobitex: { color: "bg-purple-500/15 text-purple-400 border-purple-500/30", label: "🟣 نوبیتکس" },
  bitpin: { color: "bg-green-500/15 text-green-400 border-green-500/30", label: "🟢 بیت‌پین" },
  wallex: { color: "bg-blue-500/15 text-blue-400 border-blue-500/30", label: "🔵 والکس" },
  abantether: { color: "bg-sky-500/15 text-sky-400 border-sky-500/30", label: "🔷 آبان‌تتر" },
  tsetmc: { color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", label: "🇮🇷 بورس" },
};

function useLiveQuote(ticker: string, source: string, enabled: boolean) {
  const [price, setPrice] = useState<number | null>(null);
  const [change, setChange] = useState<number>(0);

  useEffect(() => {
    if (!enabled || !ticker) return;
    const fetchQuote = () => {
      api
        .get("/analyze/quote", { params: { ticker, source } })
        .then((res) => {
          setPrice(res.data.price);
          setChange(res.data.change_pct || 0);
        })
        .catch(() => {});
    };
    fetchQuote();
    const id = setInterval(fetchQuote, 5000);
    return () => clearInterval(id);
  }, [ticker, source, enabled]);

  return { price, change };
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
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState("");

  // ═══ به‌روزرسانی زمان ═══
  useEffect(() => {
    if (!data) return;
    const update = () => {
      const now = new Date();
      setLastUpdate(
        new Intl.DateTimeFormat("fa-IR", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }).format(now)
      );
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [data]);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    api
      .post("/analyze", {
        ticker,
        source,
        timeframe,
        market_type: marketType,
        risk_profile: riskProfile,
        ticker_name: tickerName,
      })
      .then((res) => setData(res.data))
      .catch((err) => {
        const detail = err.response?.data?.detail;
        let msg = "تحلیل ناموفق بود";
        if (typeof detail === "string") msg = detail;
        else if (Array.isArray(detail) && detail.length > 0)
          msg = detail[0]?.msg || msg;
        setError(msg);
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [ticker, tickerName, source, timeframe, marketType, riskProfile]);

  const { price: livePrice, change: liveChange } = useLiveQuote(
    ticker,
    source,
    !!ticker
  );

  if (loading && !data) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/30">
        <CardContent className="py-6 text-center">
          <p className="text-sm text-destructive">⚠️ {error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const displayPrice = livePrice ?? data.price ?? 0;
  const displayChange = livePrice ? liveChange : 0;

  const atr = data.atr ?? 0;
  const multSl = data.atr_mult_sl ?? 1.0;
  const multTp = data.atr_mult_tp ?? 1.5;
  const dirLong = data.direction === "long";
  const dirShort = data.direction === "short";

  const liveSl = dirLong
    ? displayPrice - atr * multSl
    : dirShort
      ? displayPrice + atr * multSl
      : null;

  const liveTp = dirLong
    ? displayPrice + atr * multTp
    : dirShort
      ? displayPrice - atr * multTp
      : null;

  const liveRr =
    liveSl !== null && liveTp !== null && Math.abs(displayPrice - liveSl) > 0
      ? Math.abs(liveTp - displayPrice) / Math.abs(displayPrice - liveSl)
      : null;

  const SignalIcon = dirLong ? TrendingUp : dirShort ? TrendingDown : Minus;
  const src = SOURCE_BADGE[source] || SOURCE_BADGE.nobitex;
  const inWatchlist = watchlist.some((w) => w.ticker === ticker);

  const shortAnalysis =
    data.explanation || data.reasons?.[0] || `${regimeFullFa(data.regime)}`;

  return (
    <Card className={`border ${signalBg(data.signal)}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 pt-3">
        <div className="flex-1">
          <CardTitle className="text-base">{data.name}</CardTitle>
          <p className="text-[10px] text-muted-foreground">
            {data.ticker}
            {lastUpdate && (
              <span className="mr-2 text-muted-foreground/70">
                · به‌روز: {lastUpdate}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
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
            title={inWatchlist ? "حذف از واچ‌لیست" : "افزودن به واچ‌لیست"}
          >
            <Star className={`h-4 w-4 ${inWatchlist ? "fill-current" : ""}`} />
          </button>
          <Badge variant="outline" className="text-[10px] py-0">
            {data.timeframe}
          </Badge>
          <Badge className={`text-[10px] border py-0 ${src.color}`}>
            {src.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 pb-3">
        {/* ═══ قیمت + سیگنال ═══ */}
        <div className="rounded-lg bg-muted/40 p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex-1">
              <p className="text-[9px] text-muted-foreground">قیمت زنده</p>
              <p className="num text-2xl font-bold tracking-tight">
                {formatNumber(displayPrice)}
              </p>
              {displayChange !== 0 && (
                <p
                  className={`num text-[10px] ${
                    displayChange >= 0 ? "text-green-500" : "text-red-500"
                  }`}
                >
                  {displayChange >= 0 ? "▲" : "▼"} {Math.abs(displayChange).toFixed(2)}%
                </p>
              )}
            </div>
            <div className="h-12 w-px bg-border/40" />
            <div className={`text-center ${signalColor(data.signal)}`}>
              <SignalIcon className="mx-auto h-5 w-5" />
              <p className="text-base font-bold leading-none">{data.signal}</p>
              <p className={`num text-[10px] mt-0.5 ${confidenceColor(data.confidence)}`}>
                {data.confidence}%
              </p>
            </div>
          </div>
          {data.action_fa && (
            <p className="mt-2 text-center text-[10px] text-muted-foreground">
              {data.action_fa}
            </p>
          )}
        </div>

        {/* ═══ خلاصه کوتاه تحلیل ═══ */}
        <div className="rounded-lg bg-muted/30 p-2.5 text-center">
          <p className="text-[10px] leading-relaxed text-muted-foreground">
            {shortAnalysis}
          </p>
        </div>

        {/* ═══ SL/TP ═══ */}
        {liveSl !== null && liveTp !== null && (
          <div className="grid grid-cols-3 gap-1.5">
            <div className="rounded-md border border-red-500/20 bg-red-500/5 px-2 py-2 text-center">
              <div className="flex items-center justify-center gap-1 text-[9px] text-muted-foreground">
                <Shield className="h-2.5 w-2.5" />
                ضرر
              </div>
              <p className="num mt-0.5 text-xs font-bold text-red-500">
                {formatNumber(liveSl)}
              </p>
            </div>
            <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-2 py-2 text-center">
              <div className="flex items-center justify-center gap-1 text-[9px] text-muted-foreground">
                <Percent className="h-2.5 w-2.5" />
                R:R
              </div>
              <p className="num mt-0.5 text-xs font-bold text-blue-500">
                {liveRr?.toFixed(1) ?? "—"}
              </p>
            </div>
            <div className="rounded-md border border-green-500/20 bg-green-500/5 px-2 py-2 text-center">
              <div className="flex items-center justify-center gap-1 text-[9px] text-muted-foreground">
                <Target className="h-2.5 w-2.5" />
                هدف
              </div>
              <p className="num mt-0.5 text-xs font-bold text-green-500">
                {formatNumber(liveTp)}
              </p>
            </div>
          </div>
        )}

        {/* ═══ وضعیت + اجماع + آراء ═══ */}
        <div className="grid grid-cols-2 gap-2 text-center">
          <div className="rounded-md bg-muted/30 p-2">
            <p className="text-[9px] text-muted-foreground">وضعیت</p>
            <p className="text-[11px] font-bold">
              {regimeIcon(data.regime)} {regimeFullFa(data.regime)}
            </p>
          </div>
          <div className="rounded-md bg-muted/30 p-2">
            <p className="text-[9px] text-muted-foreground">اجماع</p>
            <p className={`text-[11px] font-bold ${consensusColor(data.consensus)}`}>
              {consensusFa(data.consensus)}
            </p>
          </div>
        </div>

        {/* ═══ آراء — با برچسب ═══ */}
        <div className="grid grid-cols-3 gap-1.5">
          <div className="rounded-md bg-green-500/10 border border-green-500/20 px-2 py-1.5 text-center">
            <p className="text-[9px] text-green-400">صعودی</p>
            <p className="num text-sm font-bold text-green-500">
              {data.votes_long}
            </p>
          </div>
          <div className="rounded-md bg-yellow-500/10 border border-yellow-500/20 px-2 py-1.5 text-center">
            <p className="text-[9px] text-yellow-400">خنثی</p>
            <p className="num text-sm font-bold text-yellow-500">
              {data.votes_neutral}
            </p>
          </div>
          <div className="rounded-md bg-red-500/10 border border-red-500/20 px-2 py-1.5 text-center">
            <p className="text-[9px] text-red-400">نزولی</p>
            <p className="num text-sm font-bold text-red-500">
              {data.votes_short}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}