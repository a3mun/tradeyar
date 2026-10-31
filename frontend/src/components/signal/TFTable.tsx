"use client";

/**
 * TFTable — تحلیل بر اساس تایم‌فریم (نسخه نهایی ۱۷.۰ · آستانه‌های جدید)
 * ============================================================
 */

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair, SOURCE_BY_KEY } from "@/lib/sources";
import { MiniSparkline } from "@/components/ui/sparkline";
import type { AnalyzeResponse, Timeframe } from "@/lib/types";

const TIMEFRAMES: Timeframe[] = [
  "۱ دقیقه",
  "۵ دقیقه",
  "۱۵ دقیقه",
  "۳۰ دقیقه",
  "۱ ساعت",
  "روزانه",
];

// 🔴 تبدیل کلمات انگلیسی به فارسی
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

type ConfidenceLevel = "golden" | "strong" | "normal" | "weak" | "neutral";

// 🔴 آستانه‌های جدید (شروع از ۴۰٪)
function getConfidenceLevel(confidence: number, isActiveSignal: boolean): ConfidenceLevel {
  if (!isActiveSignal) {
    if (confidence >= 30) return "normal"; // در حال تشکیل
    if (confidence >= 15) return "weak"; // دور
    return "neutral"; // خنثی
  }
  if (confidence >= 85) return "golden";
  if (confidence >= 70) return "strong";
  if (confidence >= 55) return "normal"; // معمولی
  if (confidence >= 40) return "weak"; // ضعیف
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

// 🔴 رنگ‌بندی استاندارد
const SIGNAL_STYLE_MAP: Record<Direction, Record<ConfidenceLevel, SignalStyle>> = {
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
    // 🔴 حالت‌های غیرفعال (خنثی، دور، در حال تشکیل) بدون قاب و پس‌زمینه
    golden: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.4)", boxShadow: "none", textShadow: "none", opacity: 0.5 },
    strong: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.4)", boxShadow: "none", textShadow: "none", opacity: 0.5 },
    normal: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.8)", boxShadow: "none", textShadow: "none", opacity: 0.7 }, // در حال تشکیل
    weak: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.6)", boxShadow: "none", textShadow: "none", opacity: 0.5 }, // دور
    neutral: { bg: "transparent", border: "transparent", color: "rgba(148,163,184,0.3)", boxShadow: "none", textShadow: "none", opacity: 0.3 }, // خنثی
  },
};

// 🔴 رنگ درصد اطمینان: آبی
const CONF_COLORS: Record<ConfidenceLevel, { text: string; bar: string }> = {
  golden: { text: "#60a5fa", bar: "#3b82f6" }, 
  strong: { text: "#93c5fd", bar: "#60a5fa" },
  normal: { text: "#bfdbfe", bar: "#93c5fd" },
  weak: { text: "#dbeafe", bar: "#bfdbfe" }, 
  neutral: { text: "#e2e8f0", bar: "#cbd5e1" }, 
};

const ROW_HEIGHT = "h-[42px]";

export function TFTable() {
  const {
    ticker,
    tickerName,
    source,
    timeframe,
    marketType,
    riskProfile,
    setTimeframe,
    wsSignal,
  } = useAppStore();

  const [data, setData] = useState<Record<string, AnalyzeResponse>>({});

  useEffect(() => {
    if (wsSignal && wsSignal.ticker === ticker && wsSignal.data) {
      const newSignal = wsSignal.data as unknown as AnalyzeResponse;
      const tf = newSignal.timeframe;
      if (tf) {
        setData((prev) => ({ ...prev, [tf]: newSignal }));
      }
    }
  }, [wsSignal, ticker]);

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
        ticker_name: tickerName,
      });
      setData(res.data.timeframes || {});
    } catch {
      // silent fail
    }
  };

  useEffect(() => {
    fetchMultiData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, tickerName, source, marketType, riskProfile]);

  useEffect(() => {
    if (!ticker || !sourceSupportsPair(source, ticker)) return;

    const interval = setInterval(() => {
      fetchMultiData();
    }, 5000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, source, tickerName, marketType, riskProfile]);

  const handleRowClick = (tf: string) => setTimeframe(tf as Timeframe);
  const sourceMeta = SOURCE_BY_KEY[source];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div>
          <CardTitle className="text-sm">📊 تحلیل بر اساس تایم‌فریم</CardTitle>
          <p className="text-[9px] text-muted-foreground">
            روی هر ردیف بزن تا تحلیل همون TF باز بشه
          </p>
        </div>
        {ticker && (
          <div className="flex shrink-0 items-center gap-1">
            <span
              className="inline-flex items-center rounded-md border px-2 py-0.5 text-[10px]"
              style={{
                background: "rgba(59,130,246,0.08)",
                borderColor: "rgba(59,130,246,0.25)",
                color: "#93c5fd",
                fontFamily: "monospace",
              }}
            >
              {ticker}
            </span>
            {sourceMeta && (
              <span
                className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px]"
                style={{
                  background: "rgba(139,92,246,0.08)",
                  borderColor: "rgba(139,92,246,0.25)",
                  color: "#c4b5fd",
                }}
              >
                <span className="text-[8px]">{sourceMeta.icon}</span>
                {sourceMeta.label}
              </span>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent className="px-1 sm:px-3">
        <Table className="table-fixed w-full">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[20%] sm:w-[18%] text-right text-[9px] sm:text-[10px] py-1">
                تایم‌فریم
              </TableHead>
              <TableHead className="w-[32%] sm:w-[30%] text-center text-[9px] sm:text-[10px] py-1">
                سیگنال
              </TableHead>
              <TableHead className="w-[18%] text-center text-[9px] sm:text-[10px] py-1">
                اطمینان
              </TableHead>
              <TableHead className="w-[30%] sm:w-[34%] text-center text-[9px] sm:text-[10px] py-1">
                نمودار
              </TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {TIMEFRAMES.map((tf) => {
              const row = data[tf];
              const isActive = tf === timeframe;

              if (!row) {
                return (
                  <TableRow key={tf} className={`opacity-50 ${ROW_HEIGHT}`}>
                    <TableCell className="text-right text-[10px] font-medium py-0">
                      {tf}
                    </TableCell>
                    <TableCell colSpan={3} className="text-center text-[10px] text-muted-foreground py-0">
                      دیتا نیست
                    </TableCell>
                  </TableRow>
                );
              }

              const conf = row.confidence || 0;
              
              // 🔴 سیگنال فقط وقتی فعال است که درصد >= ۴۰ باشد
              const isActiveSignal = conf >= 40;
              
              const dirFromBackend: Direction = row.direction === "long" ? "long" : row.direction === "short" ? "short" : "neutral";
              const styleDirection = isActiveSignal ? dirFromBackend : "neutral";
              
              const confLevel = getConfidenceLevel(conf, isActiveSignal);
              const sigStyle = SIGNAL_STYLE_MAP[styleDirection][confLevel];
              const confStyle = CONF_COLORS[isActiveSignal ? confLevel : "neutral"];

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
              
              // 🔴 تعیین متن نمایشی (۴۰٪ به بالا سیگنال)
              let displaySignal = "خنثی";
              if (conf >= 40) {
                displaySignal = translateSignal(row.signal || "خنثی");
              } else if (conf >= 30) {
                displaySignal = "در حال تشکیل";
              } else if (conf >= 15) {
                displaySignal = "دور";
              }

              // 🔴 تغییر رنگ متن برای دور و در حال تشکیل بر اساس جهت
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
                        // 🔴 حذف کامل قاب برای حالت‌های غیرفعال
                        borderWidth: !isActiveSignal ? 0 : (confLevel === "golden" ? "2px" : "1px"),
                      }}
                    >
                      {goldenMark}
                      {displaySignal}
                    </span>
                  </TableCell>
                  <TableCell className="text-center py-0">
                    <div className="leading-none">
                      <div
                        className="num text-[10px] sm:text-[11px] font-bold mb-0.5"
                        style={{ color: confStyle.text }}
                      >
                        {`${conf}%`}
                      </div>
                      <div className="mx-auto h-0.5 w-8 sm:w-10 overflow-hidden rounded-full bg-muted-foreground/15">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${conf}%`,
                            background: confStyle.bar,
                          }}
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