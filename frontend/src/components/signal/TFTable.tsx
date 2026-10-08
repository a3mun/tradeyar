"use client";

/**
 * TFTable — تحلیل بر اساس تایم‌فریم (نسخه ۳.۳)
 * ============================================================
 * 🔴 تغییرات نسخه ۳.۳:
 *   • همگام‌سازی لحظه‌ای با wsSignal از store (فاز ۸.۱)
 *   • وقتی SignalCard سیگنال WS جدید می‌گیره، TFTable هم
 *     دوباره /analyze/multi رو صدا می‌زنه.
 */

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
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

// ═══ رنگ sparkline ═══
function sparkColorFromSignal(
  signal: string
): "green" | "red" | "neutral" {
  if (!signal) return "neutral";
  const s = signal.toUpperCase();
  if (
    s.includes("LONG") ||
    signal.includes("صعودی") ||
    signal.includes("خرید")
  )
    return "green";
  if (
    s.includes("SHORT") ||
    signal.includes("نزولی") ||
    signal.includes("فروش")
  )
    return "red";
  return "neutral";
}

// ═══ نوع سیگنال ═══
type SignalKind =
  | "long"
  | "short"
  | "weak-long"
  | "weak-short"
  | "neutral";

function getSignalKind(signal: string): SignalKind {
  if (!signal) return "neutral";
  const s = signal.toUpperCase();
  const isLong = s.includes("LONG") || signal.includes("صعودی");
  const isShort = s.includes("SHORT") || signal.includes("نزولی");
  const isWeak = signal.includes("ضعیف");

  if (isLong && isWeak) return "weak-long";
  if (isShort && isWeak) return "weak-short";
  if (isLong) return "long";
  if (isShort) return "short";
  return "neutral";
}

// ═══ نوع وضعیت ═══
type StatusKind =
  | "signal-long"
  | "signal-short"
  | "near-long"
  | "near-short"
  | "near-neutral"
  | "forming-long"
  | "forming-short"
  | "forming"
  | "wait";

function getStatusKind(
  confidence: number,
  direction: string,
  signal: string
): { kind: StatusKind; label: string } {
  const sigKind = getSignalKind(signal);

  if (sigKind === "long") return { kind: "signal-long", label: "سیگنال" };
  if (sigKind === "short") return { kind: "signal-short", label: "سیگنال" };

  if (sigKind === "weak-long") return { kind: "near-long", label: "نزدیک" };
  if (sigKind === "weak-short") return { kind: "near-short", label: "نزدیک" };

  const isLong = direction === "long" || signal.includes("صعودی");
  const isShort = direction === "short" || signal.includes("نزولی");

  if (confidence >= 40) {
    if (isLong) return { kind: "near-long", label: "نزدیک" };
    if (isShort) return { kind: "near-short", label: "نزدیک" };
    return { kind: "near-neutral", label: "نزدیک" };
  }
  if (confidence >= 20) {
    if (isLong) return { kind: "forming-long", label: "تشکیل" };
    if (isShort) return { kind: "forming-short", label: "تشکیل" };
    return { kind: "forming", label: "تشکیل" };
  }
  return { kind: "wait", label: "دور" };
}

// ═══ استایل سیگنال ═══
const SIGNAL_STYLES: Record<SignalKind, React.CSSProperties> = {
  long: {
    background: "rgba(34,197,94,0.18)",
    color: "#4ade80",
    borderColor: "#22c55e",
    textShadow:
      "0 0 8px rgba(34,197,94,0.9), 0 0 12px rgba(34,197,94,0.5)",
    boxShadow:
      "0 0 12px rgba(34,197,94,0.5), 0 0 24px rgba(34,197,94,0.25), inset 0 0 8px rgba(34,197,94,0.15)",
    animation: "pulse-green 2s ease-in-out infinite",
  },
  short: {
    background: "rgba(239,68,68,0.18)",
    color: "#f87171",
    borderColor: "#ef4444",
    textShadow:
      "0 0 8px rgba(239,68,68,0.9), 0 0 12px rgba(239,68,68,0.5)",
    boxShadow:
      "0 0 12px rgba(239,68,68,0.5), 0 0 24px rgba(239,68,68,0.25), inset 0 0 8px rgba(239,68,68,0.15)",
    animation: "pulse-red 2s ease-in-out infinite",
  },
  "weak-long": {
    background: "rgba(34,197,94,0.08)",
    color: "#86c493",
    borderColor: "rgba(34,197,94,0.4)",
    opacity: 0.9,
  },
  "weak-short": {
    background: "rgba(239,68,68,0.08)",
    color: "#c48a8a",
    borderColor: "rgba(239,68,68,0.4)",
    opacity: 0.9,
  },
  neutral: {
    background: "rgba(100,116,139,0.06)",
    color: "#94a3b8",
    borderColor: "rgba(100,116,139,0.18)",
    opacity: 0.65,
  },
};

// ═══ استایل وضعیت ═══
const STATUS_STYLES: Record<StatusKind, React.CSSProperties> = {
  "signal-long": {
    background: "rgba(34,197,94,0.18)",
    color: "#4ade80",
    borderColor: "rgba(34,197,94,0.6)",
    boxShadow: "0 0 8px rgba(34,197,94,0.4)",
    fontWeight: "bold",
  },
  "signal-short": {
    background: "rgba(239,68,68,0.18)",
    color: "#f87171",
    borderColor: "rgba(239,68,68,0.6)",
    boxShadow: "0 0 8px rgba(239,68,68,0.4)",
    fontWeight: "bold",
  },
  "near-long": {
    background: "rgba(34,197,94,0.08)",
    color: "#86c493",
    borderColor: "rgba(34,197,94,0.4)",
    opacity: 0.9,
  },
  "near-short": {
    background: "rgba(239,68,68,0.08)",
    color: "#c48a8a",
    borderColor: "rgba(239,68,68,0.4)",
    opacity: 0.9,
  },
  "near-neutral": {
    background: "rgba(100,116,139,0.06)",
    color: "#94a3b8",
    borderColor: "rgba(100,116,139,0.18)",
    opacity: 0.65,
  },
  "forming-long": {
    background: "rgba(34,197,94,0.04)",
    color: "#5f8a6b",
    borderColor: "rgba(34,197,94,0.18)",
    opacity: 0.55,
  },
  "forming-short": {
    background: "rgba(239,68,68,0.04)",
    color: "#8a5f5f",
    borderColor: "rgba(239,68,68,0.18)",
    opacity: 0.55,
  },
  forming: {
    background: "rgba(100,116,139,0.05)",
    color: "#7a8595",
    borderColor: "rgba(100,116,139,0.15)",
    opacity: 0.55,
  },
  wait: {
    background: "rgba(100,116,139,0.03)",
    color: "#5b6472",
    borderColor: "rgba(100,116,139,0.1)",
    opacity: 0.45,
  },
};

function confTextStyle(kind: SignalKind): React.CSSProperties {
  switch (kind) {
    case "long":
      return { color: "#4ade80" };
    case "short":
      return { color: "#f87171" };
    case "weak-long":
      return { color: "#86c493", opacity: 0.9 };
    case "weak-short":
      return { color: "#c48a8a", opacity: 0.9 };
    default:
      return { color: "#64748b" };
  }
}

function confBarColor(kind: SignalKind): string {
  switch (kind) {
    case "long":
      return "#22c55e";
    case "short":
      return "#ef4444";
    case "weak-long":
      return "#86c493";
    case "weak-short":
      return "#c48a8a";
    default:
      return "#64748b";
  }
}

export function TFTable() {
  const {
    ticker,
    tickerName,
    source,
    timeframe,
    marketType,
    riskProfile,
    setTimeframe,
    wsSignal, // ← فاز ۸.۱
  } = useAppStore();

  const [data, setData] = useState<Record<string, AnalyzeResponse>>({});
  const [loading, setLoading] = useState(false);
  const lastFingerprintRef = useRef<string>("");

  // ═══ useEffect ۱: fetch اولیه ═══
  useEffect(() => {
    if (!ticker || !sourceSupportsPair(source, ticker)) {
      let cancelled = false;
      queueMicrotask(() => {
        if (cancelled) return;
        setData({});
        setLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }

    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) setLoading(true);
    });

    api
      .post("/analyze/multi", {
        ticker,
        source,
        timeframe: "۵ دقیقه",
        market_type: marketType,
        risk_profile: riskProfile,
        ticker_name: tickerName,
      })
      .then((res) => {
        if (cancelled) return;
        setData(res.data.timeframes || {});
      })
      .catch(() => {
        if (!cancelled) setData({});
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ticker, tickerName, source, marketType, riskProfile]);

  // ═══ useEffect ۲: 🔴 فاز ۸.۱ — همگام‌سازی با wsSignal ═══
  useEffect(() => {
    if (!wsSignal || !wsSignal.data) return;

    // ─── چک: همون نماد/منبع؟ ───
    if (wsSignal.ticker !== ticker || wsSignal.source !== source) {
      return;
    }

    // ─── چک fingerprint ───
    const fp = (wsSignal.data as AnalyzeResponse).fingerprint || "";
    if (!fp || fp === lastFingerprintRef.current) {
      return;
    }
    lastFingerprintRef.current = fp;

    // ─── refetch multi (بدون loading spinner) ───
    api
      .post("/analyze/multi", {
        ticker,
        source,
        timeframe: "۵ دقیقه",
        market_type: marketType,
        risk_profile: riskProfile,
        ticker_name: tickerName,
      })
      .then((res) => {
        setData(res.data.timeframes || {});
      })
      .catch(() => {
        // silent
      });
  }, [
    wsSignal,
    ticker,
    source,
    tickerName,
    marketType,
    riskProfile,
  ]);

  // ═══ 🔴 فاز ۸.۳ — refetch multi هر ۱۵s (هماهنگی با SignalCard) ═══
  // چرا: WS signal هر ۳۰s میاد ولی این کند. ۱۵s میانگین می‌گیریم.
  useEffect(() => {
    if (!ticker || !sourceSupportsPair(source, ticker)) return;

    const refetch = () => {
      api
        .post("/analyze/multi", {
          ticker,
          source,
          timeframe: "۵ دقیقه",
          market_type: marketType,
          risk_profile: riskProfile,
          ticker_name: tickerName,
        })
        .then((res) => setData(res.data.timeframes || {}))
        .catch(() => {});
    };

    const interval = setInterval(refetch, 15000);
    return () => clearInterval(interval);
  }, [ticker, source, tickerName, marketType, riskProfile]);


  const handleRowClick = (tf: string) => {
    setTimeframe(tf as Timeframe);
  };

  const sourceMeta = SOURCE_BY_KEY[source];

  return (
    <Card>
      <style jsx global>{`
        @keyframes pulse-green {
          0%, 100% {
            box-shadow: 0 0 12px rgba(34, 197, 94, 0.5),
              0 0 24px rgba(34, 197, 94, 0.25),
              inset 0 0 8px rgba(34, 197, 94, 0.15);
          }
          50% {
            box-shadow: 0 0 16px rgba(34, 197, 94, 0.7),
              0 0 32px rgba(34, 197, 94, 0.4),
              inset 0 0 12px rgba(34, 197, 94, 0.25);
          }
        }
        @keyframes pulse-red {
          0%, 100% {
            box-shadow: 0 0 12px rgba(239, 68, 68, 0.5),
              0 0 24px rgba(239, 68, 68, 0.25),
              inset 0 0 8px rgba(239, 68, 68, 0.15);
          }
          50% {
            box-shadow: 0 0 16px rgba(239, 68, 68, 0.7),
              0 0 32px rgba(239, 68, 68, 0.4),
              inset 0 0 12px rgba(239, 68, 68, 0.25);
          }
        }
      `}</style>

      {/* ═══ هدر ═══ */}
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
                letterSpacing: "0.3px",
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
        <Table className="table-fixed">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[18%] text-right text-[9px]">
                تایم‌فریم
              </TableHead>
              <TableHead className="w-[24%] text-center text-[9px]">
                سیگنال
              </TableHead>
              <TableHead className="w-[16%] text-center text-[9px]">
                اطمینان
              </TableHead>
              <TableHead className="w-[22%] text-center text-[9px]">
                وضعیت
              </TableHead>
              <TableHead className="w-[20%] text-center text-[9px]">
                نمودار
              </TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {loading &&
              TIMEFRAMES.map((tf) => (
                <TableRow key={tf}>
                  <TableCell>
                    <Skeleton className="h-4 w-14" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="mx-auto h-5 w-16" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="mx-auto h-4 w-10" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="mx-auto h-5 w-16" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="mx-auto h-5 w-14" />
                  </TableCell>
                </TableRow>
              ))}

            {!loading &&
              TIMEFRAMES.map((tf) => {
                const row = data[tf];
                const isActive = tf === timeframe;

                if (!row) {
                  return (
                    <TableRow key={tf} className="opacity-50">
                      <TableCell className="text-right text-[10px] font-medium">
                        {tf}
                      </TableCell>
                      <TableCell
                        colSpan={4}
                        className="text-center text-[10px] text-muted-foreground"
                      >
                        دیتا نیست
                      </TableCell>
                    </TableRow>
                  );
                }

                const sigKind = getSignalKind(row.signal || "");
                const { kind: statusKind, label: statusLabel } = getStatusKind(
                  row.confidence || 0,
                  row.direction || "neutral",
                  row.signal || ""
                );
                const conf = row.confidence || 0;

                const rowClass =
                  isActive && sigKind === "long"
                    ? "cursor-pointer transition-colors hover:bg-muted/50 bg-primary/5 border-r-2 border-green-500/50"
                    : isActive && sigKind === "short"
                      ? "cursor-pointer transition-colors hover:bg-muted/50 bg-primary/5 border-r-2 border-red-500/50"
                      : isActive
                        ? "cursor-pointer transition-colors hover:bg-muted/50 bg-primary/10"
                        : "cursor-pointer transition-colors hover:bg-muted/50";

                return (
                  <TableRow
                    key={tf}
                    onClick={() => handleRowClick(tf)}
                    className={rowClass}
                  >
                    <TableCell className="text-right text-[10px] font-medium">
                      {tf}
                      {isActive && (
                        <span className="mr-1 text-[8px] text-primary">
                          ●
                        </span>
                      )}
                    </TableCell>

                    <TableCell className="text-center">
                      <span
                        className="inline-flex w-full max-w-[90px] items-center justify-center rounded border px-1.5 py-0.5 text-[9px] font-bold tracking-wide transition-all duration-300"
                        style={SIGNAL_STYLES[sigKind]}
                      >
                        {row.signal || "خنثی"}
                      </span>
                    </TableCell>

                    <TableCell className="text-center">
                      <div className="leading-tight">
                        <div
                          className="num mb-0.5 text-[10px] font-bold"
                          style={confTextStyle(sigKind)}
                        >
                          {conf}%
                        </div>
                        <div className="mx-auto h-0.5 w-8 overflow-hidden rounded-full bg-muted-foreground/15">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${conf}%`,
                              background: confBarColor(sigKind),
                            }}
                          />
                        </div>
                      </div>
                    </TableCell>

                    <TableCell className="text-center">
                      <span
                        className="inline-flex w-full max-w-[80px] items-center justify-center rounded border px-1.5 py-0.5 text-[9px] transition-all duration-300"
                        style={STATUS_STYLES[statusKind]}
                      >
                        {statusLabel}
                      </span>
                    </TableCell>

                    <TableCell className="text-center">
                      <MiniSparkline
                        data={row.close_series || []}
                        height={20}
                        color={sparkColorFromSignal(row.signal || "")}
                        className="mx-auto w-12"
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
          </TableBody>
        </Table>

        {!loading && Object.keys(data).length > 0 && (
          <p className="mt-3 text-[9px] leading-relaxed text-muted-foreground">
            💡 <b style={{ color: "#4ade80" }}>سیگنال</b> قطعی صادر شده ·{" "}
            <b style={{ color: "#86c493" }}>نزدیک</b> سیگنال ضعیف ·{" "}
            <b style={{ color: "#7a8595" }}>تشکیل</b> در حال آماده شدن ·{" "}
            <b style={{ color: "#5b6472" }}>دور</b> راه زیادی مونده
          </p>
        )}
      </CardContent>
    </Card>
  );
}