"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { signalColor, confidenceColor } from "@/lib/display";
import { sourceSupportsPair } from "@/lib/sources";
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

const SOURCE_BADGE: Record<string, { color: string; label: string }> = {
  nobitex: {
    color: "bg-purple-500/15 text-purple-400 border-purple-500/30",
    label: "🟣 نوبیتکس",
  },
  bitpin: {
    color: "bg-green-500/15 text-green-400 border-green-500/30",
    label: "🟢 بیت‌پین",
  },
  wallex: {
    color: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    label: "🔵 والکس",
  },
  tabdeal: {
    color: "bg-orange-500/15 text-orange-400 border-orange-500/30",
    label: "🟠 تبدیل",
  },
  tsetmc: {
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    label: "🇮🇷 بورس",
  },
};

// ═══ 🔴 helper: رنگ sparkline ═══
function sparkColorFromSignal(signal: string): "green" | "red" | "neutral" {
  if (!signal) return "neutral";
  const s = signal.toUpperCase();
  if (s.includes("LONG") || signal.includes("صعودی") || signal.includes("خرید")) {
    return "green";
  }
  if (s.includes("SHORT") || signal.includes("نزولی") || signal.includes("فروش")) {
    return "red";
  }
  return "neutral";
}

// ═══ 🔴 Bias Bar: وضعیت کلی بازار ═══
// از آراء محاسبه می‌شه — نشون‌دهنده‌ی حال و هوای بازار
interface BiasInfo {
  /** 0-100 — موقعیت نوار از چپ به راست */
  position: number;
  /** رنگ نوار */
  barCls: string;
  /** رنگ متن description */
  textCls: string;
}

function getBiasInfo(
  votesLong: number,
  votesShort: number,
  votesNeutral: number
): BiasInfo {
  const total = votesLong + votesShort + votesNeutral;
  if (total === 0) {
    return { position: 50, barCls: "bg-slate-400/40", textCls: "text-slate-400" };
  }

  // ─── LONG=100، خنثی=50، SHORT=0 ───
  const position = Math.round(
    ((votesLong * 100 + votesNeutral * 50) / total)
  );

  // ─── رنگ بر اساس موقعیت ───
  if (position >= 65) {
    return { position, barCls: "bg-green-500/70", textCls: "text-green-500" };
  }
  if (position >= 55) {
    return { position, barCls: "bg-green-500/40", textCls: "text-green-500/70" };
  }
  if (position >= 45) {
    return { position, barCls: "bg-slate-400/50", textCls: "text-slate-400" };
  }
  if (position >= 35) {
    return { position, barCls: "bg-red-500/40", textCls: "text-red-500/70" };
  }
  return { position, barCls: "bg-red-500/70", textCls: "text-red-500" };
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
  } = useAppStore();
  const [data, setData] = useState<Record<string, AnalyzeResponse>>({});
  const [loading, setLoading] = useState(false);

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

  const handleRowClick = (tf: string) => {
    setTimeframe(tf as Timeframe);
  };

  const src = SOURCE_BADGE[source] || SOURCE_BADGE.nobitex;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div>
          <CardTitle className="text-sm">📊 تحلیل بر اساس تایم‌فریم</CardTitle>
          <p className="text-[10px] text-muted-foreground">
            روی هر ردیف بزن تا تحلیل همون TF باز بشه
          </p>
        </div>
        <Badge className={`text-[10px] border ${src.color}`}>
          {src.label}
        </Badge>
      </CardHeader>
      <CardContent className="px-2 sm:px-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-right w-[75px] sm:w-20">
                تایم‌فریم
              </TableHead>
              <TableHead className="text-right w-[80px] sm:w-24">
                سیگنال
              </TableHead>
              <TableHead className="text-center w-[50px] sm:w-14">
                اطمینان
              </TableHead>
              <TableHead className="text-center w-[80px] sm:w-24">
                وضعیت بازار
              </TableHead>
              <TableHead className="text-center w-[70px] sm:w-16">
                نمودار
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading &&
              TIMEFRAMES.map((tf) => (
                <TableRow key={tf}>
                  <TableCell>
                    <Skeleton className="h-5 w-16" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-10 mx-auto" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-20 mx-auto" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-6 w-16 mx-auto" />
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
                      <TableCell className="text-right font-medium text-xs">
                        {tf}
                      </TableCell>
                      <TableCell
                        colSpan={4}
                        className="text-right text-xs text-muted-foreground"
                      >
                        دیتا نیست
                      </TableCell>
                    </TableRow>
                  );
                }

                const bias = getBiasInfo(
                  row.votes_long || 0,
                  row.votes_short || 0,
                  row.votes_neutral || 0
                );

                return (
                  <TableRow
                    key={tf}
                    onClick={() => handleRowClick(tf)}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                      isActive ? "bg-primary/10" : ""
                    }`}
                  >
                    {/* تایم‌فریم */}
                    <TableCell className="text-right font-medium text-xs">
                      {tf}
                      {isActive && (
                        <span className="mr-1 text-[9px] text-primary">●</span>
                      )}
                    </TableCell>

                    {/* سیگنال — متن خالی، همون واقعیت */}
                    <TableCell
                      className={`text-right text-[10px] sm:text-[11px] font-medium ${signalColor(
                        row.signal
                      )}`}
                    >
                      {row.signal}
                    </TableCell>

                    {/* اطمینان */}
                    <TableCell
                      className={`text-center num text-[10px] sm:text-[11px] ${confidenceColor(
                        row.confidence
                      )}`}
                    >
                      {row.confidence}%
                    </TableCell>

                    {/* ═══ وضعیت بازار (Bias Bar) ═══ */}
                    <TableCell>
                      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted/30">
                        {/* خط مرکز */}
                        <div className="absolute inset-y-0 left-1/2 w-px bg-foreground/30" />
                        {/* نوار پر شده از چپ تا موقعیت */}
                        <div
                          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${bias.barCls}`}
                          style={{ width: `${bias.position}%` }}
                        />
                      </div>
                    </TableCell>

                    {/* نمودار */}
                    <TableCell className="text-center">
                      <MiniSparkline
                        data={row.close_series || []}
                        height={22}
                        color={sparkColorFromSignal(row.signal)}
                        className="w-16 mx-auto"
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