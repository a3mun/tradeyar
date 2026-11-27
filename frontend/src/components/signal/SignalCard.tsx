"use client";

/**
 * SignalCard — کارت سیگنال (نسخه نهایی · UI Overhaul)
 * ============================================================
 * 🔴 تغییرات:
 *   • حذف پیام‌های شلوغ (هزینه، زمان بازار، رای‌گیری رنگی)
 *   • بج‌های مینیمال و تک‌رنگ
 *   • استفاده از min-h برای جلوگیری از پرش در صورت وجود پیام هشدار
 *   • حفظ ارتفاع پایه با flex-1
 */

import { useEffect, useRef, useState } from "react";
import {
  TrendingUp, TrendingDown, Minus, Target, Shield, Percent, Star,
  AlertTriangle, Share2, Loader2, Crosshair,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { useAnalysisCapability } from "@/lib/hooks/useAnalysisCapability";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { SOURCE_BY_KEY, sourceSupportsPair } from "@/lib/sources";
import { AnalysisUnavailable } from "@/components/signal/AnalysisUnavailable";
import { Sparkline } from "@/components/ui/sparkline";
import { CryptoIcon } from "@/components/ui/crypto-icon";
import type { AnalyzeResponse } from "@/lib/types";
import { CopyableNumber } from "@/components/ui/copyable-number";
import { getConfidenceLevel, isSignalActive, type ConfidenceLevel } from "@/lib/thresholds";
import { formatNumber } from "@/lib/display";

// ═══════════════════════════════════════════════════════════
// ثابت‌های استایل
// ═══════════════════════════════════════════════════════════
const LEVEL_STYLES: Record<ConfidenceLevel, { text: string; icon: string }> = {
  golden: { text: "#facc15", icon: "💎" },
  strong: { text: "#22c55e", icon: "🟢" },
  normal: { text: "#3b82f6", icon: "🟡" },
  weak: { text: "#f97316", icon: "🟠" },
  neutral: { text: "#94a3b8", icon: "⚪" },
};

function getSignalPillStyle(direction: string, confLevel: string, isActive: boolean, statusText: string) {
  if (direction === "neutral") {
    return "border-transparent bg-transparent text-muted-foreground/30";
  }

  const isLong = direction === "long";

  // 🔴 حالت دور (خیلی کم‌رنگ)
  if (statusText === "دور") {
    return isLong 
      ? "border-green-500/10 bg-transparent text-green-400/20" 
      : "border-red-500/10 bg-transparent text-red-400/20";
  }

  // 🔴 حالت در حال تشکیل (کم‌رنگ‌تر از فعال)
  if (statusText === "در حال تشکیل") {
    return isLong 
      ? "border-green-500/20 bg-transparent text-green-400/30" 
      : "border-red-500/20 bg-transparent text-red-400/30";
  }

  // 🔴 حالت فعال (پررنگ)
  if (isActive) {
    switch (confLevel) {
      case "golden":
        return "border-[#d6ad60] bg-[#d6ad60]/10 text-[#d6ad60]";
      case "strong":
        return isLong ? "border-green-500/40 bg-green-500/5 text-green-400/90" : "border-red-500/40 bg-red-500/5 text-red-400/90";
      case "normal":
        return isLong ? "border-green-500/30 bg-green-500/5 text-green-400/70" : "border-red-500/30 bg-red-500/5 text-red-400/70";
      case "weak":
        return isLong ? "border-green-500/20 bg-transparent text-green-400/50" : "border-red-500/20 bg-transparent text-red-400/50";
      default:
        return "border-transparent bg-transparent text-muted-foreground/50";
    }
  }

  return "border-transparent bg-transparent text-muted-foreground/50";
}

function playGoldenBeep() {
  try {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;
    const notes = [523.25, 659.25, 783.99];
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      const startAt = now + i * 0.12;
      gain.gain.setValueAtTime(0, startAt);
      gain.gain.linearRampToValueAtTime(0.06, startAt + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, startAt + 0.15);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(startAt);
      osc.stop(startAt + 0.18);
    });
    setTimeout(() => ctx.close().catch(() => {}), 1000);
  } catch (e) {
    console.debug("[Audio] beep failed:", e);
  }
}

const TRAP_LABELS: Record<string, string> = {
  bull_trap: "تله صعودی", bear_trap: "تله نزولی", fake_breakout: "شکست جعلی", exhaustion: "خستگی روند",
};

const TF_TO_SHORT: Record<string, string> = {
  "۱ دقیقه": "1m", "۵ دقیقه": "5m", "۱۵ دقیقه": "15m", "۳۰ دقیقه": "30m", "۱ ساعت": "1h", "روزانه": "1d",
};

function tfShort(tf: string): string { return TF_TO_SHORT[tf] || tf; }

// 🔴 تابع ترجمه سیگنال‌ها به فارسی
function translateSignal(signal: string) {
  if (!signal) return "";
  return signal
    .replace(/LONG/g, "خرید")
    .replace(/SHORT/g, "فروش")
    .replace(/ضعیف/g, "Weak")
    .replace(/قوی/g, "Strong");
}

function getEnglishSignal(signal: string) {
  if (!signal) return "";
  return signal
    .replace(/LONG/g, "LONG")
    .replace(/SHORT/g, "SHORT")
    .replace(/خرید/g, "LONG")
    .replace(/فروش/g, "SHORT")
    .replace(/ضعیف/g, "Weak")
    .replace(/قوی/g, "Strong");
}

const GOLDEN_STYLES = `
@keyframes golden-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(250,204,21,0.3), 0 0 20px rgba(250,204,21,0.1); border-color: rgba(250,204,21,0.4); }
  50% { box-shadow: 0 0 16px rgba(250,204,21,0.6), 0 0 32px rgba(250,204,21,0.2); border-color: rgba(250,204,21,0.8); }
}
`;

// ═══════════════════════════════════════════════════════════
// کامپوننت
// ═══════════════════════════════════════════════════════════
export function SignalCard() {
  const {
    ticker, tickerName, source, timeframe, marketType, riskProfile, strategy,
    watchlist, addToWatchlist, removeFromWatchlist, getTfData, setTfData,
  } = useAppStore();

  const capability = useAnalysisCapability(source);
  const { quote, status: wsStatus } = useWebSocket();

  const tfDataCache = useAppStore((s) => s.tfDataCache);
  void tfDataCache; 

  const data: AnalyzeResponse | null = getTfData(timeframe);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);
  const [priceFlash, setPriceFlash] = useState<"up" | "down" | null>(null);
  const [polledPrice, setPolledPrice] = useState<number>(0);
  const [brentPrice, setBrentPrice] = useState<number | null>(null);
  const [sparklineSeries, setSparklineSeries] = useState<number[]>([]);
  const [now, setNow] = useState<Date>(() => new Date());

  const prevPriceRef = useRef<number | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const lastGoldenKeyRef = useRef<string>("");
  const lastKnownPriceRef = useRef<number>(0);

  // ═══ fetch تحلیل ═══
  useEffect(() => {
    if (!ticker) { setLoading(false); setError(null); return; }
    const supports = sourceSupportsPair(source, ticker);
    if (!supports && source !== "tsetmc") { setLoading(false); setError(null); return; }
    const cached = getTfData(timeframe);
    if (cached) { setLoading(false); setError(null); return; }
    
    let cancelled = false;
    setLoading(true);
    setError(null);

    api.post<AnalyzeResponse>("/analyze", {
        ticker, source, timeframe, market_type: marketType,
        risk_profile: riskProfile, strategy, ticker_name: tickerName || ticker,
      })
      .then((res) => {
        if (cancelled) return;
        setTfData(timeframe, res.data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
        let msg = "تحلیل ناموفق بود";
        if (typeof detail === "string") msg = detail;
        else if (Array.isArray(detail) && detail.length > 0) {
          const first = detail[0] as { msg?: string } | undefined;
          msg = first?.msg || msg;
        }
        setError(msg);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [ticker, source, timeframe, marketType, riskProfile, strategy, tickerName, getTfData, setTfData]);

  useEffect(() => { if (data) { setLoading(false); setError(null); } }, [data]);

  useEffect(() => {
    if (!loading) return;
    const timer = setTimeout(() => {
      const cached = getTfData(timeframe);
      if (cached) { setLoading(false); setError(null); }
      else { setLoading(false); setError("داده‌ی این نماد در این تایم‌فریم در دسترس نیست"); }
    }, 30_000);
    return () => clearTimeout(timer);
  }, [loading, timeframe, getTfData]);

  // ═══ polling قیمت ═══
  useEffect(() => {
    if (!ticker || !source) return;
    if (!sourceSupportsPair(source, ticker) && source !== "tsetmc") { setPolledPrice(0); return; }
    let cancelled = false;
    const fetchQuote = async () => {
      try {
        const res = await api.get("/analyze/quote", { params: { ticker, source } });
        if (!cancelled && res.data?.price && res.data.price > 0) setPolledPrice(res.data.price);
      } catch {}
    };
    fetchQuote();
    const id = setInterval(fetchQuote, 5000);
    return () => { cancelled = true; clearInterval(id); };
  }, [ticker, source]);
  


  // دریافت قیمت نفت برنت از همان منبع نوار بالای سایت
  useEffect(() => {
    let cancelled = false;

    const fetchBrentPrice = async () => {
      try {
        const res = await api.get("/symbols/iran-prices");
        const value = res.data?.prices?.brent;

        if (
          !cancelled &&
          typeof value === "number" &&
          Number.isFinite(value) &&
          value > 0
        ) {
          setBrentPrice(value);
        }
      } catch {
        // در خطای موقت، آخرین قیمت معتبر حفظ می‌شود.
      }
    };

    fetchBrentPrice();

    const intervalId = setInterval(fetchBrentPrice, 60000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, []);



  // ═══ Sparkline ═══
  useEffect(() => {
    if (!ticker) { setSparklineSeries([]); return; }
    if (capability.planned || !sourceSupportsPair(source, ticker)) { setSparklineSeries([]); return; }
    let cancelled = false;
    api.get<{ ok: boolean; close_series: number[]; price: number }>("/analyze/sparkline", { params: { ticker, source, timeframe } })
      .then((res) => {
        if (cancelled) return;
        setSparklineSeries(res.data.close_series || []);
        if (res.data.price && res.data.price > 0 && prevPriceRef.current === null) {
          prevPriceRef.current = res.data.price;
        }
      })
      .catch(() => { if (!cancelled) { setSparklineSeries([]); } });
    return () => { cancelled = true; };
  }, [ticker, source, timeframe, strategy, capability.planned]);

  // ═══ reset ═══
  useEffect(() => {
    setSparklineSeries([]);
    prevPriceRef.current = null;
    lastGoldenKeyRef.current = "";
  }, [strategy, ticker, timeframe, marketType, riskProfile]);

  useEffect(() => {
    setPolledPrice(0);
    lastKnownPriceRef.current = 0;
    prevPriceRef.current = null;
  }, [ticker, source]);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // ═══ livePrice ═══
  const entryPrice = data?.price ?? 0;
  const quoteMatchesCurrent = quote != null && quote.price > 0 && quote.ticker === ticker && quote.source === source;
  const livePrice = (() => {
    const fromWs = quoteMatchesCurrent ? quote.price : 0;
    const fromPoll = polledPrice > 0 ? polledPrice : 0;
    const fromData = entryPrice > 0 ? entryPrice : 0;
    const fallback = lastKnownPriceRef.current;
    let final = fromWs || fromPoll || fallback;
    if (final === 0 && fromData > 0) final = fromData;
    if (final > 0) lastKnownPriceRef.current = final;
    return final;
  })();

  // ═══ flash سبز/قرمز ═══
  useEffect(() => {
    if (!livePrice || livePrice <= 0) return;
    const prev = prevPriceRef.current;
    if (prev != null && prev !== livePrice) {
      const dir = livePrice > prev ? "up" : "down";
      setPriceFlash(dir);
      prevPriceRef.current = livePrice;
      const flashTimer = setTimeout(() => setPriceFlash(null), 400);
      return () => { clearTimeout(flashTimer); };
    }
    prevPriceRef.current = livePrice;
  }, [livePrice]);

  // ═══ Sparkline آخرین نقطه ═══
  useEffect(() => {
    if (!livePrice || livePrice <= 0) return;
    const TF_TO_MS: Record<string, number> = {
      "۱ دقیقه": 60_000, "۵ دقیقه": 300_000, "۱۵ دقیقه": 900_000,
      "۳۰ دقیقه": 1_800_000, "۱ ساعت": 3_600_000, "روزانه": 86_400_000,
    };
    const intervalMs = TF_TO_MS[timeframe] || 60_000;
    const updateSparkline = () => {
      setSparklineSeries((prev) => {
        if (!prev || prev.length < 2) return prev;
        const next = [...prev];
        next[next.length - 1] = livePrice;
        return next;
      });
    };
    updateSparkline();
    const id = setInterval(updateSparkline, intervalMs);
    return () => clearInterval(id);
  }, [livePrice, timeframe]);

  // ═══ beep ═══
  const isDirForBeep = data?.direction === "long" || data?.direction === "short";
  const confLevelForBeep = getConfidenceLevel(data?.confidence || 0, isDirForBeep);

  useEffect(() => {
    if (confLevelForBeep !== "golden" || !data) return;
    const goldenKey = `${data.ticker}|${data.timeframe}|${data.signal}|${data.confidence}`;
    if (lastGoldenKeyRef.current === goldenKey) return;
    lastGoldenKeyRef.current = goldenKey;
    const t = setTimeout(() => playGoldenBeep(), 300);
    return () => clearTimeout(t);
  }, [confLevelForBeep, data]);

  // ═══ share ═══
  const handleShare = async () => {
    if (!cardRef.current || sharing || !data) return;
    setSharing(true);
    try {
      let captionText = `تحلیل ${data.name || data.ticker} از Trademun\n🔗 trademun.ir`;
      try {
        const captionRes = await api.post<{ ok: boolean; caption: string }>("/share/caption", {
          ticker: data.ticker, name: data.name, source: data.source_used || data.source,
          tf: data.timeframe, signal: data.signal, direction: data.direction,
          confidence: data.confidence, strategy: data.strategy, market_type: data.market_type,
          risk_profile: data.risk_profile, price: data.price, sl: data.sl, tp: data.tp,
          rr: data.rr, rr_net: data.rr_net, tp_levels: data.tp_levels, traps: data.traps,
        });
        if (captionRes.data.ok && captionRes.data.caption) captionText = captionRes.data.caption;
      } catch (e) { console.warn("خطا در گرفتن کپشن", e); }

      const { toBlob } = await import("html-to-image");
      const blob = await toBlob(cardRef.current, { backgroundColor: "#0a0e1a", pixelRatio: 2, cacheBust: true });
      if (!blob) throw new Error("toBlob failed");
      const fileName = `trademun-${data.ticker}-${Date.now()}.png`;
      const file = new File([blob], fileName, { type: "image/png" });
      const isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
      const nav = navigator as Navigator & { canShare?: (d: { files: File[]; text?: string }) => boolean };
      if (isMobile && typeof nav.share === "function" && typeof nav.canShare === "function" && nav.canShare({ files: [file], text: captionText })) {
        try { await nav.share({ files: [file], title: `سیگنال ${data.ticker}`, text: captionText }); return; }
        catch (err) { if ((err as Error)?.name === "AbortError") return; }
      }
      const link = document.createElement("a");
      link.download = fileName;
      const url = URL.createObjectURL(blob);
      link.href = url; document.body.appendChild(link); link.click(); document.body.removeChild(link); URL.revokeObjectURL(url);
      try { await navigator.clipboard.writeText(captionText); } catch (clipErr) { console.warn(clipErr); }
    } catch (err) { console.error("[Share] خطا:", err); }
    finally { setSharing(false); }
  };

  // ═══════════════════════════════════════════════════════════
  // حالت‌های نمایش
  // ═══════════════════════════════════════════════════════════
  if (capability.planned) {
    return <AnalysisUnavailable message={capability.message} suggestion={capability.suggestion} alternatives={[]} variant="planned" />;
  }

  if (loading || !data) {
    return (
      <Card className="relative z-10 border border-border/40 bg-[#051118] backdrop-blur-md h-[400px] flex flex-col justify-center">
        <CardContent className="space-y-3 p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="space-y-1"><Skeleton className="h-4 w-24" /><Skeleton className="h-3 w-16" /></div>
            </div>
            <Skeleton className="h-7 w-24 rounded-full" />
          </div>
          <div className="grid grid-cols-2 gap-2"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>
          <Skeleton className="h-[60px] w-full rounded-md" />
          <div className="grid grid-cols-3 gap-1.5"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return <AnalysisUnavailable message="تحلیل برای این نماد در دسترس نیست" suggestion={error} variant="no-data" />;
  }

  // ═══ محاسبات نمایش ═══
  const sl = data.sl;
  const tp = data.tp;
  const rr = data.rr;
  const displayChange = quote != null ? quote.change_pct : null;

  const isDirectional = data.direction === "long" || data.direction === "short";
  const confidenceLevel = getConfidenceLevel(data.confidence || 0, isDirectional);
  const isActiveSignal = isSignalActive(data.confidence || 0, data.direction || "neutral", data.signal || "", strategy, riskProfile);
  const levelStyle = LEVEL_STYLES[confidenceLevel];
  const SignalIcon = data.direction === "long" ? TrendingUp : data.direction === "short" ? TrendingDown : Minus;

  const requestedMeta = SOURCE_BY_KEY[source];
  const usedSource = data.source_used ?? source;
  const usedMeta = SOURCE_BY_KEY[usedSource] ?? requestedMeta;
  const isFallback = Boolean(data.is_fallback) && usedSource !== source;
  const inWatchlist = watchlist.some((w) => w.ticker === ticker);

  const isCFDSymbol = data.ticker === "UKOIL-USD" || data.ticker === "USOIL-USD";

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

  const wsConnected = wsStatus === "connected";
  const series = sparklineSeries.length >= 2 ? sparklineSeries : data.close_series && data.close_series.length >= 2 ? data.close_series : null;
  // 🔴 تشخیص وضعیت متن برای هماهنگی با جدول
  let cardStatusText = "فعال";
  if (!isActiveSignal) {
    if (data.signal?.includes("در حال تشکیل") || (data.confidence || 0) >= 25) {
      cardStatusText = "در حال تشکیل";
    } else if (data.signal?.includes("دور") || (data.confidence || 0) >= 10) {
      cardStatusText = "دور";
    } else {
      cardStatusText = "خنثی";
    }
  }

  const signalPillClass = getSignalPillStyle(data.direction || "neutral", confidenceLevel, isActiveSignal, cardStatusText);
  
  // ═══════════════════════════════════════════════════════════
  // رندر اصلی
  // ═══════════════════════════════════════════════════════════
  return (
    <div ref={cardRef} data-signal-card className="relative">
      <style jsx global>{GOLDEN_STYLES}</style>
      
      {/* 🔴 تغییر: h-[400px] به min-h-[400px] برای جلوگیری از بریده شدن */}
      <Card className={`relative z-10 border border-white/10 bg-[#051118] shadow-xl transition-all min-h-[400px] flex flex-col ${confidenceLevel === "golden" ? "shadow-[0_0_15px_rgba(250,204,21,0.1)]" : ""}`} style={confidenceLevel === "golden" ? { animation: "golden-pulse 2s ease-in-out infinite" } : undefined}>
        
        {/* هدر کارت */}
        <div className="flex items-center justify-between gap-2 p-2 pb-0 shrink-0">
          <div className="flex min-w-0 flex-1 items-center gap-1.5">
            <CryptoIcon ticker={data.ticker} size="md" />
            <p className="truncate text-sm font-bold">{data.name}</p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Tooltip>
              <TooltipTrigger>
                <span className={`flex items-center gap-0.5 rounded px-1 py-0.5 text-[8px] ${wsConnected ? "text-[#d6ad60]" : "text-muted-foreground"}`}>
                  {wsConnected ? <span className="h-1.5 w-1.5 rounded-full bg-[#d6ad60] animate-pulse" /> : <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />}
                </span>
              </TooltipTrigger>
              <TooltipContent><p className="text-[10px]">{wsConnected ? "اتصال زنده فعال" : "اتصال زنده قطع است"}</p></TooltipContent>
            </Tooltip>
            <button onClick={handleShare} disabled={sharing} className="rounded-md p-1 text-muted-foreground transition-colors hover:text-[#d6ad60] disabled:opacity-50">
              {sharing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Share2 className="h-3.5 w-3.5" />}
            </button>
            <button onClick={() => inWatchlist ? removeFromWatchlist(ticker) : addToWatchlist(ticker, tickerName || ticker, source)} className={`rounded-md p-1 transition-colors ${inWatchlist ? "text-[#d6ad60]" : "text-muted-foreground hover:text-[#d6ad60]"}`}>
              <Star className={`h-3.5 w-3.5 ${inWatchlist ? "fill-current" : ""}`} />
            </button>
          </div>
        </div>

        {/* زیرنویس هدر (تک‌رنگ) */}
        <div className="flex flex-wrap items-center gap-2 px-2 text-[10px] text-muted-foreground mt-0.5 shrink-0">
          <span className="num font-medium">{data.ticker}</span>
          <span className="text-border">|</span>
          <span className="num">{tfShort(data.timeframe)}</span>
          <span className="text-border">|</span>
          <span>{data.market_type === "futures" ? "فیوچرز" : "اسپات"}</span>
          <span className="text-border">|</span>
          <span>{riskProfile === "aggressive" ? "جسورانه" : "محتاطانه"}</span>
          <span className="text-border">|</span>
          <span>{source === "forex" ? "فارکس" : requestedMeta?.label}</span>
          
          {/* 🔴 بج اخطار تله (منتقل شده به اینجا) */}
          {activeTraps.length > 0 && (
            <Tooltip>
              <TooltipTrigger>
                <div className="flex items-center gap-1 rounded border border-red-500/30 bg-red-500/10 px-1 py-0.5">
                  <AlertTriangle className="h-2.5 w-2.5 shrink-0 text-red-500" />
                  <span className="text-[8px] font-bold text-red-500">تله - شکست جعلی</span>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p className="text-[10px] leading-relaxed">احتمال {trapLabel}: {trapReasons.join(" | ")}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* بدنه کارت */}
        <CardContent className="flex flex-col flex-1 space-y-1.5 px-2 pb-1 pt-1.5">
          
          <div className="shrink-0">

            {isCFDSymbol && (
              <div className="rounded-md bg-muted/20 px-2 py-0 text-[9px] text-muted-foreground mb-0.5">
                ℹ️ قیمت نمایش‌داده‌شده بر اساس CFD بازار فارکس است و ممکن است با بازار اصلی اختلاف داشته باشد.
                {data.ticker === "UKOIL-USD" && brentPrice !== null && (
                  <span className="font-bold text-[#d6ad60]">
                    {" "}(نفت برنت: {formatNumber(brentPrice, { maxDecimals: 2 })} دلار)
                  </span>
                )}
              </div>
            )}


            {isFallback && (
              <p className="rounded-md border border-border/30 bg-muted/20 px-2 py-1 text-[9px] text-muted-foreground mb-1.5">
                ℹ️ قیمت از {requestedMeta?.label} — تحلیل بر اساس {usedMeta?.label}
              </p>
            )}



            {/* قیمت و سیگنال */}
            <div className="rounded-lg border border-border/20 bg-muted/10 px-2.5 py-1.5">
              <div className="flex items-center justify-between gap-2">
                <div className="shrink-0 flex flex-col items-start gap-0.5 min-w-[80px]">
                  <span className={`text-[10px] font-bold ${data.direction === "long" ? "text-green-500" : data.direction === "short" ? "text-red-500" : "text-muted-foreground"}`}>
                    {data.direction === "long" ? "▲ صعودی" : data.direction === "short" ? "▼ نزولی" : "● خنثی"}
                  </span>
                  {displayChange != null && displayChange !== 0 && (
                    <span className={`num text-[9px] font-medium ${displayChange >= 0 ? "text-green-500" : "text-red-500"}`}>
                      {displayChange >= 0 ? "▲" : "▼"} {Math.abs(displayChange).toFixed(2)}%
                    </span>
                  )}
                </div>

                <p className={`num flex-1 text-center text-2xl font-bold leading-tight tracking-tight transition-colors duration-300 ${priceFlash === "up" ? "text-green-500" : priceFlash === "down" ? "text-red-500" : "text-foreground"}`}>
                  {formatNumber(livePrice)}
                </p>

                <div className="shrink-0 flex flex-row items-center gap-2 min-w-[90px]">
                  {/* باکس سیگنال دو خطی (بزرگ‌تر) */}
                  <div className={`inline-flex flex-col items-center justify-center rounded-md border px-3 py-1 ${signalPillClass}`}>
                    {/* انگلیسی بالا */}
                    <p className="text-[12px] font-bold leading-none whitespace-nowrap uppercase tracking-wider">
                      {isActiveSignal 
                        ? getEnglishSignal(data.signal).replace("خرید", "LONG").replace("فروش", "SHORT")
                        : "NEUTRAL"}
                    </p>
                    {/* فارسی پایین (کوچیک‌تر) */}
                    <p className="text-[9px] opacity-80 leading-none mt-0.5 whitespace-nowrap font-medium">
                      {isActiveSignal 
                        ? translateSignal(data.signal).replace("Weak", "ضعیف").replace("Strong", "قوی")
                        : cardStatusText === "در حال تشکیل" 
                          ? "در حال تشکیل" 
                          : cardStatusText === "دور" 
                            ? "دور" 
                            : "خنثی"}
                    </p>
                  </div>
                  
                  {/* درصد اطمینان (کوچیک‌تر و کم‌رنگ‌تر) */}
                  <div className="flex flex-col items-center justify-center">
                     <p className="num text-[9px] font-bold text-muted-foreground/80">
                       {data.confidence}%
                     </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* نمودار */}
          <div className="shrink-0">
            {series ? (
              <Sparkline data={series} height={60} showArea showDot sl={sl} tp={tp} entry={entryPrice} color={data.signal.includes("LONG") || data.signal.includes("صعودی") ? "green" : data.signal.includes("SHORT") || data.signal.includes("نزولی") ? "red" : "neutral"} />
            ) : (
              <div className="relative flex items-center justify-center overflow-hidden rounded-md bg-muted/10" style={{ height: 60 }}>
                <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
              </div>
            )}
          </div>

          {/* SL / RR / TP */}
          <div className="grid grid-cols-3 gap-1.5 min-h-[48px] shrink-0">
            {sl != null && tp != null ? (
              <>
                <div className="flex flex-col items-center justify-center rounded-md border border-border/20 bg-muted/5 px-1.5 py-1">
                  <div className="flex items-center gap-0.5 text-[8px] text-muted-foreground"><Shield className="h-2.5 w-2.5" />حد ضرر</div>
                  <div className="mt-0.5 text-[10px] font-bold text-red-500/90"><CopyableNumber value={sl} /></div>
                </div>
                <div className="flex flex-col items-center justify-center rounded-md border border-border/20 bg-muted/5 px-1.5 py-1">
                  <div className="flex items-center gap-0.5 text-[8px] text-muted-foreground"><Percent className="h-2.5 w-2.5" />R:R</div>
                  <p className="num mt-0.5 text-[11px] font-bold text-foreground">
                    {data.rr_net != null ? data.rr_net.toFixed(2) : rr != null ? rr.toFixed(2) : "—"}
                  </p>
                </div>
                <div className="flex flex-col items-center justify-center rounded-md border border-border/20 bg-muted/5 px-1.5 py-1">
                  <div className="flex items-center gap-0.5 text-[8px] text-muted-foreground"><Target className="h-2.5 w-2.5" />هدف نهایی</div>
                  <div className="mt-0.5 text-[10px] font-bold text-green-500/90"><CopyableNumber value={tp} /></div>
                </div>
              </>
            ) : (
              <div className="col-span-3 flex items-center justify-center rounded-md border border-border/20 bg-muted/5 py-2">
                 <p className="text-[9px] text-muted-foreground">بدون سیگنال - اطلاعات کافی برای SL/TP موجود نیست، لطفا تایم فریم دیگری انتخب نمایید.</p>
              </div>
            )}
          </div>

          {/* نقطه ورود و خروج پله‌ای */}
          {(data.suggested_entry || data.tp_levels?.tp1) && (
            <div className="grid grid-cols-2 gap-1.5 shrink-0">
              {data.suggested_entry && data.direction !== "neutral" ? (
                <div className="flex flex-row items-center justify-between rounded-md border border-border/20 bg-muted/5 px-2 py-1.5">
                  <span className="text-[10px] font-bold text-[#d6ad60]">نقطه ورود</span>
                  <div className="text-[15px] font-bold text-foreground leading-none">
                    <CopyableNumber value={data.suggested_entry} />
                  </div>
                </div>
              ) : <div/>}

              {data.tp_levels && data.tp_levels.tp1 != null ? (
                <div className="flex flex-col justify-center rounded-md border border-border/20 bg-muted/5 px-2 py-0">
                  <div className="flex items-center justify-center gap-1 mb-0">
                    <span className="text-[10px] font-bold text-muted-foreground">خروج پله‌ای</span>
                  </div>
                  <div className="space-y-0 mt-1">
                    {[{ label: "TP1", value: data.tp_levels.tp1 }, { label: "TP2", value: data.tp_levels.tp2 }, { label: "TP3", value: data.tp_levels.tp3 }].map(({ label, value }) => (
                      <div key={label} className="flex items-center justify-between">
                        <span className="text-[8px] text-muted-foreground">{label}</span>
                        <span className="num font-bold text-[9px] text-foreground"><CopyableNumber value={value} /></span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : <div/>}
            </div>
          )}

        </CardContent>

        {/* فوتر کارت (mt-auto برای چسبیدن به پایین در صورت وجود فضای خالی) */}
        <div className="flex items-center justify-between border-t border-border/20 px-3 py-1 text-[9px] shrink-0 mt-auto">
          <div className="flex items-center gap-1.5 flex-row-reverse">
            <img src="/icon-192.png" alt="trademun" className="h-3.5 w-3.5 opacity-70 grayscale" />
            <span className="shrink-0 text-muted-foreground/60" style={{ fontFamily: "monospace", letterSpacing: "0.3px" }}>
              trademun.ir
            </span>
          </div>

          <span className="num flex shrink-0 items-center gap-1 text-muted-foreground/60" style={{ fontFamily: "monospace" }}>
            <span>
              {(() => {
                const parts = new Intl.DateTimeFormat("fa-IR-u-nu-latn", {
                  year: "numeric", month: "2-digit", day: "2-digit", timeZone: "Asia/Tehran",
                }).formatToParts(now);
                return parts.map((p) => p.value).join("");
              })()}
            </span>
            <span className="text-muted-foreground/30">·</span>
            <span className="text-muted-foreground/80">
              {new Intl.DateTimeFormat("en-GB", {
                hour: "2-digit", minute: "2-digit", second: "2-digit",
                hour12: false, timeZone: "Asia/Tehran",
              }).format(now)}
            </span>
          </span>
        </div>
      </Card>
    </div>
  );
}