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
import { regimeFa, signalColor, confidenceColor } from "@/lib/display";
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

// ═══ 🔴 helper: رنگ sparkline بر اساس SIGNAL (نه direction) ═══
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
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-right">تایم‌فریم</TableHead>
              <TableHead className="text-right">سیگنال</TableHead>
              <TableHead className="text-right">اطمینان</TableHead>
              <TableHead className="text-right">وضعیت</TableHead>
              <TableHead className="text-center w-20">نمودار</TableHead>
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
                    <Skeleton className="h-5 w-10" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-16" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-6 w-16" />
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
                      <TableCell className="text-right font-medium">
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

                return (
                  <TableRow
                    key={tf}
                    onClick={() => handleRowClick(tf)}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                      isActive ? "bg-primary/10" : ""
                    }`}
                  >
                    <TableCell className="text-right font-medium">
                      {tf}
                      {isActive && (
                        <span className="mr-2 text-[9px] text-primary">●</span>
                      )}
                    </TableCell>
                    <TableCell
                      className={`text-right ${signalColor(row.signal)}`}
                    >
                      {row.signal}
                    </TableCell>
                    <TableCell
                      className={`text-right num ${confidenceColor(
                        row.confidence
                      )}`}
                    >
                      {row.confidence}%
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {regimeFa(row.regime)}
                    </TableCell>
                    <TableCell className="text-center">
                      <MiniSparkline
                        data={row.close_series || []}
                        height={22}
                        color={sparkColorFromSignal(row.signal)}
                        className="w-16"
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