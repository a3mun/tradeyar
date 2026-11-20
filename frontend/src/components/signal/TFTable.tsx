"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Tooltip, TooltipContent, TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair, SOURCE_BY_KEY } from "@/lib/sources";
import { MiniSparkline } from "@/components/ui/sparkline";
import type { AnalyzeResponse, Timeframe } from "@/lib/types";
import {
  getConfidenceLevel, isSignalActive, CONF_BAR_COLOR, type ConfidenceLevel,
} from "@/lib/thresholds";
import { Lock } from "lucide-react";

const TIMEFRAMES: Timeframe[] = [
  "۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه",
];

const TF_ALLOWED_BY_STRATEGY: Record<string, Timeframe[]> = {
  scalp: ["۱ دقیقه", "۵ دقیقه"],
  swing: TIMEFRAMES,
  position: ["۳۰ دقیقه", "۱ ساعت", "روزانه"],
};

// 🔴 استایل‌های تک‌رنگ و مینیمال
const SIGNAL_STYLE_MAP: Record<string, Record<string, string>> = {
  long: {
    golden: "border-[#d6ad60] bg-[#d6ad60]/10 text-[#d6ad60]",
    strong: "border-green-500/30 bg-green-500/5 text-green-400/90",
    normal: "border-green-500/20 bg-green-500/5 text-green-400/70",
    weak: "border-green-500/10 bg-transparent text-green-400/50",
    neutral: "border-transparent bg-transparent text-muted-foreground/50",
  },
  short: {
    golden: "border-[#d6ad60] bg-[#d6ad60]/10 text-[#d6ad60]",
    strong: "border-red-500/30 bg-red-500/5 text-red-400/90",
    normal: "border-red-500/20 bg-red-500/5 text-red-400/70",
    weak: "border-red-500/10 bg-transparent text-red-400/50",
    neutral: "border-transparent bg-transparent text-muted-foreground/50",
  },
  neutral: {
    golden: "border-transparent bg-transparent text-muted-foreground/50",
    strong: "border-transparent bg-transparent text-muted-foreground/50",
    normal: "border-transparent bg-transparent text-muted-foreground/70",
    weak: "border-transparent bg-transparent text-muted-foreground/50",
    neutral: "border-transparent bg-transparent text-muted-foreground/30",
  }
};

function translateSignal(signal: string) {
  return signal.replace(/LONG/g, "خرید").replace(/SHORT/g, "فروش");
}

function sparkColorFromSignal(signal: string): "green" | "red" | "neutral" {
  if (!signal) return "neutral";
  const s = signal.toUpperCase();
  if (s.includes("LONG") || signal.includes("صعودی") || signal.includes("خرید")) return "green";
  if (s.includes("SHORT") || signal.includes("نزولی") || signal.includes("فروش")) return "red";
  return "neutral";
}

type Direction = "long" | "short" | "neutral";

const ROW_HEIGHT = "h-[42px]";

export function TFTable() {
  const {
    ticker, source, timeframe, riskProfile, strategy,
    setTimeframe, getTfData, tfDataCache,
  } = useAppStore();

  const [showDisabledHint, setShowDisabledHint] = useState<string | null>(null);

  const isTsetmc = Boolean(ticker) && ticker.charCodeAt(0) > 127;

  const allowedTfs = useMemo(() => {
    if (isTsetmc) {
      return ["روزانه"] as Timeframe[];
    }
    return TF_ALLOWED_BY_STRATEGY[strategy] || TIMEFRAMES;
  }, [strategy, isTsetmc]);
  
  const data = useMemo(() => {
    const cachedData: Record<string, AnalyzeResponse> = {};
    for (const tf of TIMEFRAMES) {
      const c = getTfData(tf);
      if (c) cachedData[tf] = c;
    }
    return cachedData;
  }, [tfDataCache, ticker, source, timeframe, riskProfile, strategy, getTfData]);
  
  const handleRowClick = (tf: string) => {
    if (!allowedTfs.includes(tf as Timeframe)) {
      setShowDisabledHint(tf);
      setTimeout(() => setShowDisabledHint(null), 3000);
      return;
    }
    setTimeframe(tf as Timeframe);
  };

  const sourceMeta = SOURCE_BY_KEY[source];

  return (
    <Card className="border-white/10 bg-[#051118] shadow-xl flex flex-col h-[400px]">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div>
          <CardTitle className="text-sm font-display text-gray-200">📊 تحلیل بر اساس تایم‌فریم</CardTitle>
          <p className="text-[9px] text-gray-500">روی هر ردیف بزن تا تحلیل همون TF باز بشه</p>
        </div>
        {ticker && (
          <div className="flex shrink-0 flex-wrap items-center gap-1.5">
            <span className="rounded-md border border-white/5 bg-white/5 px-2 py-0.5 text-[9px] font-bold text-gray-300" style={{ fontFamily: "monospace" }}>
              {ticker}
            </span>
            {sourceMeta && (
              <span className="rounded-md border border-[#d6ad60]/20 bg-[#d6ad60]/5 px-2 py-0.5 text-[9px] text-[#d6ad60]">
                {sourceMeta.label}
              </span>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent className="px-1 sm:px-3 flex-1 overflow-hidden">
        <Table className="table-fixed w-full">
          <TableHeader>
              <TableRow className="hover:bg-transparent border-b border-white/10">
              <TableHead className="w-[20%] sm:w-[18%] text-right text-[9px] sm:text-[10px] py-1 text-gray-500">تایم‌فریم</TableHead>
              <TableHead className="w-[32%] sm:w-[30%] text-center text-[9px] sm:text-[10px] py-1 text-gray-500">سیگنال</TableHead>
              <TableHead className="w-[18%] text-center text-[9px] sm:text-[10px] py-1 text-gray-500">اطمینان</TableHead>
              <TableHead className="w-[30%] sm:w-[34%] text-center text-[9px] sm:text-[10px] py-1 text-gray-500">نمودار</TableHead>
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
                  <TableRow key={tf} onClick={() => handleRowClick(tf)} className={`${ROW_HEIGHT} cursor-not-allowed opacity-40 hover:bg-transparent border-white/10`}>
                    <TableCell className="text-right text-[10px] sm:text-[11px] font-medium py-0 text-muted-foreground flex items-center gap-1 justify-end">
                      {tf} <Lock className="h-2.5 w-2.5" />
                    </TableCell>
                    <TableCell colSpan={3} className="text-center text-[9px] text-muted-foreground py-0">
                    {isHinting 
                      ? (isTsetmc ? "بورس تهران فقط روزانه" : "برای این استراتژی غیرفعال است")
                      : (isTsetmc ? "غیرفعال برای بورس تهران" : "غیرفعال")
                    }
                  </TableCell>
                  </TableRow>
                );
              }

              if (!row) {
                return (
                  <TableRow key={tf} className={`opacity-50 ${ROW_HEIGHT} border-white/10`} onClick={() => handleRowClick(tf)}>
                    <TableCell className="text-right text-[10px] font-medium py-0 text-muted-foreground">{tf}</TableCell>
                    <TableCell className="text-center py-0"><div className="mx-auto h-4 w-16 animate-pulse rounded bg-muted-foreground/10" /></TableCell>
                    <TableCell className="text-center py-0"><div className="mx-auto h-3 w-8 animate-pulse rounded bg-muted-foreground/10" /></TableCell>
                    <TableCell className="text-center py-0"><div className="mx-auto h-4 w-16 animate-pulse rounded bg-muted-foreground/10" /></TableCell>
                  </TableRow>
                );
              }

              const conf = row.confidence || 0;
              const dirFromBackend: Direction = row.direction === "long" ? "long" : row.direction === "short" ? "short" : "neutral";
              const isActiveSignal = isSignalActive(conf, row.direction || "neutral", row.signal || "", strategy, riskProfile);
              const isDirectional = dirFromBackend === "long" || dirFromBackend === "short";
              const confLevel = getConfidenceLevel(conf, isDirectional);

              const styleDirection = isActiveSignal ? dirFromBackend : "neutral";
              const sigClass = SIGNAL_STYLE_MAP[styleDirection][confLevel];
              const confStyle = CONF_BAR_COLOR[confLevel];

              // 🔴 ردیف فعال فقط با یک خط طلایی در سمت راست مشخص میشه
              const rowClass = isActive
                ? "cursor-pointer transition-all duration-200 bg-white/[0.02] border-r-2 border-[#d6ad60]"
                : "cursor-pointer transition-all duration-200 hover:bg-[#d6ad60]/5 border-r-2 border-transparent";

              const goldenMark = confLevel === "golden" ? "💎 " : "";
              let displaySignal = "خنثی";
              const rawSignal = row.signal || "";

              if (isActiveSignal) displaySignal = translateSignal(rawSignal);
              else if (rawSignal.includes("در حال تشکیل")) displaySignal = "در حال تشکیل";
              else if (rawSignal.includes("دور")) displaySignal = "دور";
              else if (conf >= 25) displaySignal = "در حال تشکیل";
              else if (conf >= 10) displaySignal = "دور";
              else displaySignal = "خنثی";

              return (
                <TableRow key={tf} onClick={() => handleRowClick(tf)} className={`${rowClass} ${ROW_HEIGHT} border-white/10`}>
                  <TableCell className="text-right text-[10px] sm:text-[11px] font-medium py-0 rounded-r-md">
                    <span className={isActive ? "text-[#d6ad60] font-bold" : "text-gray-300"}>{tf}</span>
                  </TableCell>
                  <TableCell className="text-center py-0">
                    <span className={`inline-flex w-full max-w-[110px] items-center justify-center rounded border px-1 sm:px-1.5 py-0.5 text-[9px] sm:text-[10px] font-bold tracking-wide transition-all duration-300 ${sigClass}`}>
                      {goldenMark}{displaySignal}
                    </span>
                  </TableCell>
                  <TableCell className="text-center py-0">
                    <div className="leading-none flex flex-col items-center justify-center gap-1.5">
                      <div className="num text-[11px] sm:text-[12px] font-bold" style={{ color: isActiveSignal ? confStyle.text : "#64748b" }}>
                        {`${conf}%`}
                      </div>
                      <div className="h-1 w-10 sm:w-12 overflow-hidden rounded-full bg-white/10">
                        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${conf}%`, background: isActiveSignal ? confStyle.bar : "#475569", boxShadow: isActiveSignal ? `0 0 8px ${confStyle.bar}` : "none" }} />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-center px-1 py-0 rounded-l-md">
                    <MiniSparkline data={row.close_series || []} height={22} color={sparkColorFromSignal(row.signal || "")} className="mx-auto w-14 sm:w-20 opacity-80" />
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