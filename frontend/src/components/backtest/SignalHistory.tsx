"use client";

import { useEffect, useState } from "react";
import { History, Clock, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { signalColor, formatNumber } from "@/lib/display";

interface HistoryItem {
  id: number;
  timestamp: string;
  ticker: string;
  name: string;
  signal: string;
  confidence: number;
  price: number;
  tf: string;
  source: string;
  result: string | null;
  expired: boolean;
  result_time: string | null;
  exit_price: number | null;
  had_trap: boolean;
  trap_type: string | null;
}

const SOURCE_MAP: Record<string, { label: string; color: string }> = {
  nobitex: { label: "نوبیتکس", color: "text-purple-400" },
  bitpin: { label: "بیت‌پین", color: "text-green-400" },
  wallex: { label: "والکس", color: "text-blue-400" },
  abantether: { label: "آبان‌تتر", color: "text-sky-400" },
  tsetmc: { label: "بورس", color: "text-emerald-400" },
};

const TF_TIMEOUT_MIN: Record<string, number> = {
  "۱ دقیقه": 30,
  "۵ دقیقه": 120,
  "۱۵ دقیقه": 360,
  "۳۰ دقیقه": 720,
  "۱ ساعت": 2880,
  "روزانه": 10080,
};

const TRAP_LABEL: Record<string, string> = {
  bull_trap: "تله صعودی",
  bear_trap: "تله نزولی",
  fake_breakout: "شکست جعلی",
  exhaustion: "خستگی",
};

function toJalali(iso: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("fa-IR", {
      year: "2-digit",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return "—";
  }
}

function timeLeftMin(iso: string, tf: string, result: string | null): number {
  if (result) return -1;
  try {
    const start = new Date(iso).getTime();
    const timeoutMin = TF_TIMEOUT_MIN[tf] || 120;
    const expire = start + timeoutMin * 60 * 1000;
    const diff = expire - Date.now();
    return Math.floor(diff / 60000);
  } catch {
    return -1;
  }
}

function formatTimeLeft(min: number): string {
  if (min < 0) return "منقضی";
  if (min < 60) return `${min} دقیقه`;
  const hr = Math.floor(min / 60);
  const m = min % 60;
  if (hr < 24) return `${hr}h ${m}m`;
  return `${Math.floor(hr / 24)} روز`;
}

export function SignalHistory() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("all");
  const [visibleCount, setVisibleCount] = useState(8);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      await api.post("/backtest/run").catch(() => {});
      const res = await api.get("/backtest/history", {
        params: { limit: 50, status },
      });
      setItems(res.data.items || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setVisibleCount(8);
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  useEffect(() => {
    const id = setInterval(fetchHistory, 30000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  // ═══ Sort هوشمند ═══
  const sortedItems = [...items].sort((a, b) => {
    // pending ها اول
    const aPending = !a.result && !a.expired;
    const bPending = !b.result && !b.expired;
    if (aPending && !bPending) return -1;
    if (!aPending && bPending) return 1;

    // هر دو pending: مهلت نزدیک‌تر اول
    if (aPending && bPending) {
      const aLeft = timeLeftMin(a.timestamp, a.tf, a.result);
      const bLeft = timeLeftMin(b.timestamp, b.tf, b.result);
      return aLeft - bLeft;
    }

    // بقیه: جدیدترین اول
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });

  if (!loading && items.length === 0) return null;

  const resultBadge = (result: string | null, expired: boolean) => {
    if (result === "win")
      return <Badge className="bg-green-600 text-[9px]">✅ برد</Badge>;
    if (result === "loss")
      return <Badge className="bg-red-600 text-[9px]">❌ باخت</Badge>;
    if (expired || result === "expired")
      return <Badge variant="secondary" className="text-[9px]">⏰ منقضی</Badge>;
    return (
      <Badge variant="outline" className="text-[9px] text-yellow-500">
        ⏳ انتظار
      </Badge>
    );
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <History className="h-4 w-4" />
            تاریخچه سیگنال‌ها
          </CardTitle>
          <Select value={status} onValueChange={(v) => v && setStatus(v)}>
            <SelectTrigger className="h-7 w-24 text-[10px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه</SelectItem>
              <SelectItem value="pending">انتظار</SelectItem>
              <SelectItem value="win">برد</SelectItem>
              <SelectItem value="loss">باخت</SelectItem>
              <SelectItem value="expired">منقضی</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent className="px-3">
        <div className="space-y-2">
          {loading &&
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}

          {!loading &&
            sortedItems.slice(0, visibleCount).map((r) => {
              const src = SOURCE_MAP[r.source] || {
                label: r.source,
                color: "text-muted-foreground",
              };
              const leftMin = timeLeftMin(r.timestamp, r.tf, r.result);
              const isPending = !r.result && !r.expired;

              return (
                <div
                  key={r.id}
                  className="rounded-lg border border-border/40 bg-muted/10 p-2.5"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold">{r.name}</span>
                      <span className="text-[9px] text-muted-foreground">
                        {r.ticker}
                      </span>
                      {r.had_trap && r.trap_type && (
                        <Badge className="bg-orange-600/20 text-orange-400 text-[8px] border-orange-500/30">
                          <AlertTriangle className="h-2 w-2 ml-0.5" />
                          {TRAP_LABEL[r.trap_type] || r.trap_type}
                        </Badge>
                      )}
                    </div>
                    {resultBadge(r.result, r.expired)}
                  </div>

                  <div className="flex items-center justify-between text-[10px] mb-1">
                    <span className={`font-medium ${signalColor(r.signal)}`}>
                      {r.signal} ({r.confidence}%)
                    </span>
                    <span className="num text-muted-foreground">
                      ورود: {formatNumber(r.price)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <span className={src.color}>● {src.label}</span>
                      <span>·</span>
                      <span>{r.tf}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="h-2.5 w-2.5" />
                      <span>{toJalali(r.timestamp)}</span>
                      {isPending && leftMin >= 0 && (
                        <>
                          <span>·</span>
                          <span
                            className={
                              leftMin < 10
                                ? "text-red-500 font-bold"
                                : "text-yellow-500"
                            }
                          >
                            {formatTimeLeft(leftMin)} مونده
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {r.result_time && r.exit_price && (
                    <div className="mt-1 text-[9px] text-muted-foreground text-left">
                      خروج: {formatNumber(r.exit_price)} · {toJalali(r.result_time)}
                    </div>
                  )}
                </div>
              );
            })}

          {!loading && sortedItems.length > visibleCount && (
            <button
              onClick={() => setVisibleCount((c) => c + 8)}
              className="w-full rounded-md border border-border py-1.5 text-[10px] text-muted-foreground transition-colors hover:bg-muted/50"
            >
              نمایش {Math.min(8, sortedItems.length - visibleCount)} مورد بیشتر
              ({visibleCount} از {sortedItems.length})
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}