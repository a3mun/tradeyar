"use client";

/**
 * TFTable — تحلیل بر اساس تایم‌فریم (نسخه ۱۸.۲ · فاز ۱۵)
 * ============================================================
 * 🔴 تغییرات نسخه ۱۸.۲:
 *   • بج‌های نماد/صرافی/استراتژی در موبایل کوچیک‌تر شدن
 *   • تاخیر 1s در fetch اولیه برای کاهش فشار سرور (هماهنگی با SignalCard)
 *   • polling 60s
 */

import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair, SOURCE_BY_KEY } from "@/lib/sources";
import { MiniSparkline } from "@/components/ui/sparkline";
import type { AnalyzeResponse, Timeframe } from "@/lib/types";
import {
  getConfidenceLevel,
  isSignalActive,
  CONF_BAR_COLOR,
  type ConfidenceLevel,
} from "@/lib/thresholds";

const TIMEFRAMES: Timeframe[] = [
  "۱ دقیقه",
  "۵ دقیقه",
  "۱۵ دقیقه",
  "۳۰ دقیقه",
  "۱ ساعت",
  "روزانه",
];

const TF_ALLOWED_BY_STRATEGY: Record<string, Timeframe[]> = {
  scalp: ["۱ دقیقه", "۵ دقیقه"],
  swing: TIMEFRAMES,
  position: ["۳۰ دقیقه", "۱ ساعت", "روزانه"],
};

const STRATEGY_LABELS: Record<string, { fa: string; cls: string }> = {
  scalp: {
    fa: "⚡ اسکالپ",
    cls: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  },
  swing: {
    fa: "🌊 سوئینگ",
    cls: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
  },
  position: {
    fa: "🏛 پوزیشن",
    cls: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  },
};

function translateSignal(signal: string) {
  let s = signal;
  s = s.replace(/LONG/g, "خرید");
  s = s.replace(/SHORT/g, "فروش");
  return s;
}

function sparkColorFromSignal(signal: string): "green" | "red" | "neutral" {
  if (!signal) return "neutral";
  const s = signal.toUpperCase();
  if (s.includes("LONG") || signal.includes("صعودی") || signal.includes("خرید"))
    return "green";
  if (s.includes("SHORT") || signal.includes("نزولی") || signal.includes("فروش"))
    return "red";
  return "neutral";
}

type Direction = "long" | "short" | "neutral";

interface SignalStyle {
  bg: string;
  border: string;
  color: string;
  boxShadow: string;
  textShadow: string;
  opacity: number;
}

const SIGNAL_STYLE_MAP: Record<
  Direction,
  Record<ConfidenceLevel, SignalStyle>
> = {
  long: {
    golden: { bg: "rgba(250,204,21,0.20)", border: "#facc15", color: "#facc15", boxShadow: "0 0 16px rgba(250,204,21,0.6)", textShadow: "none", opacity: 1 },
    strong: { bg: "rgba(34,197,94,0.20)", border: "#22c55e", color: "#4ade80", boxShadow: "0 0 10px rgba(34,197,94,0.4)", textShadow: "none", opacity: 1 },
    normal: { bg: "rgba(34,197,94,0.10)", border: "rgba(34,197,94,0.5)", color: "#4ade80", boxShadow: "none", textShadow: "none", opacity: 0.9 },
    weak: { bg: "rgba(34,197,94,0.05)", border: "rgba(34,197,94,0.3)", color: "rgba(74,222,128,0.8)", boxShadow: "none", textShadow: "none", opacity: 0.8 },
    neutral: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.4)", boxShadow: "none", textShadow: "none", opacity: 0.5 },
  },
  short: {
    golden: { bg: "rgba(239,68,68,0.20)", border: "#facc15", color: "#facc15", boxShadow: "0 0 16px rgba(250,204,21,0.6)", textShadow: "none", opacity: 1 },
    strong: { bg: "rgba(239,68,68,0.20)", border: "#ef4444", color: "#f87171", boxShadow: "0 0 10px rgba(239,68,68,0.4)", textShadow: "none", opacity: 1 },
    normal: { bg: "rgba(239,68,68,0.10)", border: "rgba(239,68,68,0.5)", color: "#f87171", boxShadow: "none", textShadow: "none", opacity: 0.9 },
    weak: { bg: "rgba(239,68,68,0.05)", border: "rgba(239,68,68,0.3)", color: "rgba(248,113,113,0.8)", boxShadow: "none", textShadow: "none", opacity: 0.8 },
    neutral: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.4)", boxShadow: "none", textShadow: "none", opacity: 0.5 },
  },
  neutral: {
    golden: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.4)", boxShadow: "none", textShadow: "none", opacity: 0.5 },
    strong: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.4)", boxShadow: "none", textShadow: "none", opacity: 0.5 },
    normal: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.8)", boxShadow: "none", textShadow: "none", opacity: 0.7 },
    weak: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.6)", boxShadow: "none", textShadow: "none", opacity: 0.5 },
    neutral: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.3)", boxShadow: "none", textShadow: "none", opacity: 0.3 },
  },
};

const ROW_HEIGHT = "h-[42px]";
const POLL_INTERVAL_MS = 60_000;

export function TFTable() {
  const {
    ticker,
    tickerName,
    source,
    timeframe,
    marketType,
    riskProfile,
    strategy,
    setTimeframe,
    getTfData,
    setTfData,
    wsSignal,
  } = useAppStore();

  const [data, setData] = useState<Record<string, AnalyzeResponse>>({});
  const [showDisabledHint, setShowDisabledHint] = useState<string | null>(null);

  const allowedTfs = useMemo(() => {
    return TF_ALLOWED_BY_STRATEGY[strategy] || TIMEFRAMES;
  }, [strategy]);

  useEffect(() => {
    if (wsSignal && wsSignal.ticker === ticker && wsSignal.data) {
      const newSignal = wsSignal.data as unknown as AnalyzeResponse;
      if (newSignal.strategy && newSignal.strategy !== strategy) return;
      if (newSignal.ticker && newSignal.ticker !== ticker) return;
      const tf = newSignal.timeframe;
      if (tf) {
        setData((prev) => ({ ...prev, [tf]: newSignal }));
        setTfData(tf, newSignal);
      }
    }
  }, [wsSignal, ticker, strategy, setTfData]);

  const fetchMultiData = async () => {
    if (!ticker || !sourceSupportsPair(source, ticker)) {
      setData({});
      return;
    }
    try {
      const res = await api.post("/analyze/multi", {
        ticker,
        source,
        timeframe: "۵ دقیقه",
        market_type: marketType,
        risk_profile: riskProfile,
        strategy,
        ticker_name: tickerName,
      });
      const tfs = (res.data.timeframes || {}) as Record<string, AnalyzeResponse>;
      setData(tfs);
      for (const [tf, tfData] of Object.entries(tfs)) {
        if (tfData) setTfData(tf, tfData);
      }
    } catch {
      // silent
    }
  };

  useEffect(() => {
    setData({});
    const cachedData: Record<string, AnalyzeResponse> = {};
    let hasAny = false;
    for (const tf of TIMEFRAMES) {
      const c = getTfData(tf);
      if (c) {
        cachedData[tf] = c;
        hasAny = true;
      }
    }
    if (hasAny) setData(cachedData);

    // 🔴 فوری اجرا میشه (اول جدول)
    fetchMultiData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, tickerName, source, marketType, riskProfile, strategy]);

  useEffect(() => {
    if (!ticker || !sourceSupportsPair(source, ticker)) return;
    const interval = setInterval(() => fetchMultiData(), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, source, tickerName, marketType, riskProfile, strategy]);

  const handleRowClick = (tf: string) => {
    if (!allowedTfs.includes(tf as Timeframe)) {
      setShowDisabledHint(tf);
      setTimeout(() => setShowDisabledHint(null), 3000);
      return;
    }
    setTimeframe(tf as Timeframe);
  };

  const sourceMeta = SOURCE_BY_KEY[source];
  const strategyMeta = STRATEGY_LABELS[strategy] || STRATEGY_LABELS.swing;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div>
          <CardTitle className="text-sm font-display">📊 تحلیل بر اساس تایم‌فریم</CardTitle>
          <p className="text-[9px] text-muted-foreground">
            روی هر ردیف بزن تا تحلیل همون TF باز بشه
          </p>
        </div>
        {ticker && (
          <div className="flex shrink-0 flex-wrap items-center gap-1">
            {/* 🔴 بج نماد - استایل شبیه به SignalCard */}
            <Badge
              className="border py-0 text-[8px] sm:text-[10px] border-blue-500/30 bg-blue-500/15 text-blue-400"
              style={{ fontFamily: "monospace" }}
            >
              {ticker}
            </Badge>
            
            {/* 🔴 بج صرافی - استایل شبیه به SignalCard */}
            {sourceMeta && (
              <Badge
                className="border py-0 text-[8px] sm:text-[10px] border-purple-500/30 bg-purple-500/15 text-purple-400 gap-1"
              >
                <span className="text-[7px] sm:text-[8px]">{sourceMeta.icon}</span>
                {sourceMeta.label}
              </Badge>
            )}
            
            {/* 🔴 بج استراتژی - استایل شبیه به SignalCard */}
            <Tooltip>
              <TooltipTrigger>
                <Badge
                  className={`border py-0 text-[7px] sm:text-[9px] cursor-help ${strategyMeta.cls}`}
                >
                  {strategyMeta.fa}
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-[10px]">
                  {strategy === "scalp" && "⚡ اسکالپ: فقط TFهای ۱ و ۵ دقیقه"}
                  {strategy === "swing" && "🌊 سوئینگ: همه‌ی TFها فعال"}
                  {strategy === "position" && "🏛 پوزیشن: فقط ۳۰ دقیقه، ۱ ساعت، روزانه"}
                </p>
              </TooltipContent>
            </Tooltip>
          </div>
        )}
      </CardHeader>

      {/* 🔴 حداقل ارتفاع برای جلوگیری از پرش هنگام تغییر نماد/صرافی */}
      <CardContent className="px-1 sm:px-3 min-h-[300px]">
        <Table className="table-fixed w-full">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[20%] sm:w-[18%] text-right text-[9px] sm:text-[10px] py-1">تایم‌فریم</TableHead>
              <TableHead className="w-[32%] sm:w-[30%] text-center text-[9px] sm:text-[10px] py-1">سیگنال</TableHead>
              <TableHead className="w-[18%] text-center text-[9px] sm:text-[10px] py-1">اطمینان</TableHead>
              <TableHead className="w-[30%] sm:w-[34%] text-center text-[9px] sm:text-[10px] py-1">نمودار</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {TIMEFRAMES.map((tf) => {
              const row = data[tf];
              const isActive = tf === timeframe;
              const isAllowed = allowedTfs.includes(tf);
              const isHinting = showDisabledHint === tf;

              if (!isAllowed) {
                return (
                  <TableRow
                    key={tf}
                    onClick={() => handleRowClick(tf)}
                    className={`${ROW_HEIGHT} cursor-not-allowed opacity-40 hover:bg-transparent`}
                  >
                    <TableCell className="text-right text-[10px] sm:text-[11px] font-medium py-0 text-muted-foreground">
                      {tf}
                      <span className="mr-1 text-[8px]">🔒</span>
                    </TableCell>
                    <TableCell colSpan={3} className="text-center text-[10px] text-muted-foreground py-0">
                      {isHinting
                        ? `برای استراتژی «${strategyMeta.fa}» قابل استفاده نیست`
                        : "غیرفعال برای این استراتژی"}
                    </TableCell>
                  </TableRow>
                );
              }

              if (!row) {
                return (
                  <TableRow key={tf} className={`opacity-50 ${ROW_HEIGHT}`} onClick={() => handleRowClick(tf)}>
                    <TableCell className="text-right text-[10px] font-medium py-0 text-muted-foreground">{tf}</TableCell>
                    <TableCell className="text-center py-0"><div className="mx-auto h-4 w-20 animate-pulse rounded bg-muted-foreground/15" /></TableCell>
                    <TableCell className="text-center py-0"><div className="mx-auto h-3 w-10 animate-pulse rounded bg-muted-foreground/15" /></TableCell>
                    <TableCell className="text-center py-0"><div className="mx-auto h-4 w-16 animate-pulse rounded bg-muted-foreground/15" /></TableCell>
                  </TableRow>
                );
              }

              const conf = row.confidence || 0;
              const dirFromBackend: Direction =
                row.direction === "long" ? "long" : row.direction === "short" ? "short" : "neutral";

              const isActiveSignal = isSignalActive(
                conf, row.direction || "neutral", row.signal || "", strategy, riskProfile
              );

              const isDirectional = dirFromBackend === "long" || dirFromBackend === "short";
              const confLevel = getConfidenceLevel(conf, isDirectional);

              const styleDirection = isActiveSignal ? dirFromBackend : "neutral";
              const sigStyle = SIGNAL_STYLE_MAP[styleDirection][confLevel];
              const confStyle = CONF_BAR_COLOR[confLevel];

              const rowClass = isActive
                ? confLevel === "golden"
                  ? `cursor-pointer transition-colors hover:bg-muted/50 bg-yellow-500/5 border-r-2 border-yellow-500/50 ${ROW_HEIGHT}`
                  : dirFromBackend === "long"
                    ? `cursor-pointer transition-colors hover:bg-muted/50 bg-primary/5 border-r-2 border-green-500/50 ${ROW_HEIGHT}`
                    : dirFromBackend === "short"
                      ? `cursor-pointer transition-colors hover:bg-muted/50 bg-primary/5 border-r-2 border-red-500/50 ${ROW_HEIGHT}`
                      : `cursor-pointer transition-colors hover:bg-muted/50 bg-primary/10 ${ROW_HEIGHT}`
                : `cursor-pointer transition-colors hover:bg-muted/50 ${ROW_HEIGHT}`;

              const goldenMark = confLevel === "golden" ? "💎 " : "";

              let displaySignal = "خنثی";
              const rawSignal = row.signal || "";

              if (isActiveSignal) {
                displaySignal = translateSignal(rawSignal);
              } else if (rawSignal.includes("در حال تشکیل")) {
                displaySignal = "در حال تشکیل";
              } else if (rawSignal.includes("دور")) {
                displaySignal = "دور";
              } else if (conf >= 25) {
                displaySignal = "در حال تشکیل";
              } else if (conf >= 10) {
                displaySignal = "دور";
              } else {
                displaySignal = "خنثی";
              }

              let textColor = sigStyle.color;
              if (!isActiveSignal && conf >= 15) {
                if (dirFromBackend === "short") {
                  textColor = conf >= 30 ? "rgba(248,113,113,0.6)" : "rgba(248,113,113,0.4)";
                } else if (dirFromBackend === "long") {
                  textColor = conf >= 30 ? "rgba(74,222,128,0.6)" : "rgba(74,222,128,0.4)";
                }
              }

              return (
                <TableRow key={tf} onClick={() => handleRowClick(tf)} className={rowClass}>
                  <TableCell className="text-right text-[10px] sm:text-[11px] font-medium py-0">
                    {tf}
                    {isActive && <span className="mr-1 text-[8px] text-primary">●</span>}
                  </TableCell>
                  <TableCell className="text-center py-0">
                    <span
                      className="inline-flex w-full max-w-[130px] items-center justify-center rounded border px-1 sm:px-1.5 py-0.5 text-[9px] sm:text-[10px] font-bold tracking-wide transition-all duration-300"
                      style={{
                        background: sigStyle.bg,
                        borderColor: sigStyle.border,
                        color: textColor,
                        boxShadow: sigStyle.boxShadow,
                        textShadow: sigStyle.textShadow,
                        opacity: sigStyle.opacity,
                        borderWidth: !isActiveSignal ? 0 : confLevel === "golden" ? "2px" : "1px",
                      }}
                    >
                      {goldenMark}
                      {displaySignal}
                    </span>
                  </TableCell>
                  <TableCell className="text-center py-0">
                    <div className="leading-none">
                      <div className="num text-[10px] sm:text-[11px] font-bold mb-0.5" style={{ color: confStyle.text }}>
                        {`${conf}%`}
                      </div>
                      <div className="mx-auto h-0.5 w-8 sm:w-10 overflow-hidden rounded-full bg-muted-foreground/15">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${conf}%`, background: confStyle.bar }}
                        />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-center px-1 py-0">
                    <MiniSparkline
                      data={row.close_series || []}
                      height={22}
                      color={sparkColorFromSignal(row.signal || "")}
                      className="mx-auto w-16 sm:w-20"
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}