"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Clock,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowDownUp,
  Timer,
} from "lucide-react";
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
import type { SignalHistoryItem } from "@/lib/types";
import { CryptoIcon } from "@/components/ui/crypto-icon";

const SOURCE_MAP: Record<string, { label: string; color: string }> = {
  nobitex: { label: "نوبیتکس", color: "text-purple-400" },
  bitpin: { label: "بیت‌پین", color: "text-green-400" },
  wallex: { label: "والکس", color: "text-blue-400" },
  tabdeal: { label: "تبدیل", color: "text-orange-400" },
  tsetmc: { label: "بورس", color: "text-emerald-400" },
};

const TF_DURATION_MIN: Record<string, number> = {
  "۱ دقیقه": 1,
  "۵ دقیقه": 5,
  "۱۵ دقیقه": 15,
  "۳۰ دقیقه": 30,
  "۱ ساعت": 60,
  "روزانه": 1440,
};

const MAX_CANDLES_FUTURES = 5;
const MAX_CANDLES_SPOT = 10;

function getTimeoutMin(tf: string, marketType: string): number {
  const durationMin = TF_DURATION_MIN[tf] || 5;
  const nCandles =
    marketType === "futures" ? MAX_CANDLES_FUTURES : MAX_CANDLES_SPOT;
  return durationMin * nCandles;
}

const TRAP_LABEL: Record<string, string> = {
  bull_trap: "تله صعودی",
  bear_trap: "تله نزولی",
  fake_breakout: "شکست جعلی",
  exhaustion: "خستگی",
};

function parseUtc(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const hasTz = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  const d = new Date(hasTz ? iso : `${iso}Z`);
  return Number.isFinite(d.getTime()) ? d : null;
}

function toJalali(iso: string): string {
  const d = parseUtc(iso);
  if (!d) return "—";
  try {
    return new Intl.DateTimeFormat("fa-IR", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return "—";
  }
}

function timeLeftMin(
  iso: string,
  tf: string,
  marketType: string,
  result: string | null
): number {
  if (result) return -1;
  const start = parseUtc(iso);
  if (!start) return -1;
  const timeoutMin = getTimeoutMin(tf, marketType);
  const diff = start.getTime() + timeoutMin * 60 * 1000 - Date.now();
  return Math.floor(diff / 60000);
}

function formatTimeLeft(min: number): string {
  if (min < 0) return "منقضی";
  if (min < 60) return `${min} د`;
  const hr = Math.floor(min / 60);
  const m = min % 60;
  if (hr < 24) return `${hr}h ${m}m`;
  return `${Math.floor(hr / 24)} روز`;
}

type SortBy = "expiry" | "newest" | "oldest";

interface Props {
  source?: string;
}

export function SignalHistory({ source = "" }: Props) {
  const [items, setItems] = useState<SignalHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("all");
  const [sortBy, setSortBy] = useState<SortBy>("expiry");
  const [visibleCount, setVisibleCount] = useState(10);

  const silentFetch = useCallback(async () => {
    try {
      const res = await api.get("/backtest/history", {
        params: { limit: 200, status, source },
      });
      setItems(res.data.items || []);
      setError("");
    } catch {
      setError("دریافت تاریخچه ناموفق بود");
    }
  }, [status, source]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await api.get("/backtest/history", {
          params: { limit: 200, status, source },
        });
        if (cancelled) return;
        setItems(res.data.items || []);
        setError("");
      } catch {
        if (cancelled) return;
        setItems([]);
        setError("دریافت تاریخچه ناموفق بود");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [status, source]);

  useEffect(() => {
    const id = setInterval(silentFetch, 15000);
    return () => clearInterval(id);
  }, [silentFetch]);

  const sortedItems = useMemo(() => {
    const arr = [...items];
    if (sortBy === "expiry") {
      // ─── pending ها اول، مرتب بر اساس زمان باقی‌مانده ───
      arr.sort((a, b) => {
        const aPending = !a.result && !a.expired;
        const bPending = !b.result && !b.expired;
        if (aPending && !bPending) return -1;
        if (!aPending && bPending) return 1;
        if (aPending && bPending) {
          const aLeft = timeLeftMin(a.timestamp, a.tf, a.market_type, a.result);
          const bLeft = timeLeftMin(b.timestamp, b.tf, b.market_type, b.result);
          return aLeft - bLeft;
        }
        const bt = parseUtc(b.timestamp)?.getTime() ?? 0;
        const at = parseUtc(a.timestamp)?.getTime() ?? 0;
        return bt - at;
      });
    } else if (sortBy === "newest") {
      arr.sort((a, b) => {
        const bt = parseUtc(b.timestamp)?.getTime() ?? 0;
        const at = parseUtc(a.timestamp)?.getTime() ?? 0;
        return bt - at;
      });
    } else {
      arr.sort((a, b) => {
        const bt = parseUtc(b.timestamp)?.getTime() ?? 0;
        const at = parseUtc(a.timestamp)?.getTime() ?? 0;
        return at - bt;
      });
    }
    return arr;
  }, [items, sortBy]);

  const pendingCount = items.filter((i) => !i.result && !i.expired).length;

  const resultBadge = (
    result: string | null,
    expired: boolean,
    expiredPnlPct: number | null | undefined,
    expiredBias: string | null | undefined
  ) => {
    if (result === "win")
      return <Badge className="bg-green-600 text-[9px]">✅ برد</Badge>;
    if (result === "loss")
      return <Badge className="bg-red-600 text-[9px]">❌ باخت</Badge>;
    if (expired || result === "expired") {
      if (expiredPnlPct != null) {
        const pnl = expiredPnlPct;
        const isWin = expiredBias === "win";
        const isLoss = expiredBias === "loss";
        const cls = isWin
          ? "bg-green-500/20 text-green-400 border-green-500/30"
          : isLoss
            ? "bg-red-500/20 text-red-400 border-red-500/30"
            : "bg-muted/40 text-muted-foreground border-border";
        return (
          <Badge className={`num gap-0.5 border text-[9px] ${cls}`}>
            ⏰ {pnl >= 0 ? "+" : ""}
            {pnl.toFixed(2)}٪
          </Badge>
        );
      }
      return (
        <Badge variant="secondary" className="text-[9px]">
          ⏰ منقضی
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="text-[9px] text-yellow-500">
        ⏳ انتظار
      </Badge>
    );
  };

  return (
    <div className="space-y-2">
      {/* ═══ فیلترها ═══ */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-muted-foreground">
            {pendingCount > 0 && (
              <span className="text-yellow-500">{pendingCount} در انتظار</span>
            )}
            {pendingCount === 0 && `${items.length} سیگنال`}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* مرتب‌سازی */}
          <Select
            value={sortBy}
            onValueChange={(v) => v && setSortBy(v as SortBy)}
          >
            <SelectTrigger className="h-7 w-32 text-[10px]">
              <ArrowDownUp className="ml-1 h-3 w-3" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="expiry">
                <span className="flex items-center gap-1 text-[10px]">
                  <Timer className="h-3 w-3" />
                  نزدیک‌ترین انقضا
                </span>
              </SelectItem>
              <SelectItem value="newest">
                <span className="text-[10px]">جدیدترین</span>
              </SelectItem>
              <SelectItem value="oldest">
                <span className="text-[10px]">قدیمی‌ترین</span>
              </SelectItem>
            </SelectContent>
          </Select>

          {/* وضعیت */}
          <Select
            value={status}
            onValueChange={(v) => {
              if (!v) return;
              setVisibleCount(10);
              setStatus(v);
            }}
          >
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
      </div>

      {/* ═══ لیست ═══ */}
      <div className="space-y-2">
        {error && (
          <p
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive"
          >
            ⚠️ {error}
          </p>
        )}

        {!loading && !error && items.length === 0 && (
          <p className="py-4 text-center text-[11px] text-muted-foreground">
            {status === "all"
              ? "هنوز سیگنالی ثبت نشده"
              : "سیگنالی با این فیلتر پیدا نشد"}
          </p>
        )}

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
            const hasResult = Boolean(r.result);
            const isPending = !hasResult && !r.expired;
            const leftMin = isPending
              ? timeLeftMin(r.timestamp, r.tf, r.market_type, r.result)
              : -1;

            const DirectionIcon =
              r.direction === "long"
                ? TrendingUp
                : r.direction === "short"
                  ? TrendingDown
                  : Minus;

            const isFutures = r.market_type === "futures";

            return (
              <div
                key={r.id}
                className="rounded-lg border border-border/40 bg-muted/10 p-2.5"
              >
                {/* ─── خط ۱: نماد + بازار + نتیجه ─── */}
                <div className="flex items-center justify-between mb-1.5 gap-2">
                  <div className="flex items-center gap-1.5 min-w-0 flex-1">
                    <CryptoIcon ticker={r.ticker} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-bold">{r.name}</p>
                      <div className="flex items-center gap-1">
                        <span className="num text-[9px] text-muted-foreground">
                          {r.ticker}
                        </span>
                        <Badge
                          variant="outline"
                          className={`num gap-0.5 border py-0 text-[8px] ${
                            isFutures
                              ? "border-purple-500/30 text-purple-400"
                              : "border-sky-500/30 text-sky-400"
                          }`}
                        >
                          {isFutures ? "📈" : "💵"}
                        </Badge>
                        {r.had_trap && r.trap_type && (
                          <Badge className="bg-orange-600/20 text-orange-400 text-[8px] border-orange-500/30">
                            <AlertTriangle className="h-2 w-2" />
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  {resultBadge(
                    r.result,
                    r.expired,
                    r.expired_pnl_pct,
                    r.expired_bias
                  )}
                </div>

                {/* ─── خط ۲: سیگنال + قیمت ورود ─── */}
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <span className="flex items-center gap-1">
                    <DirectionIcon
                      className={`h-3 w-3 ${signalColor(r.signal)}`}
                    />
                    <span className={`font-medium ${signalColor(r.signal)}`}>
                      {r.signal}
                    </span>
                    <span className={`num text-[9px] ${signalColor(r.signal)}`}>
                      ({r.confidence}%)
                    </span>
                  </span>
                  <span className="num text-muted-foreground">
                    ورود: {formatNumber(r.price)}
                  </span>
                </div>

                {/* ─── خط ۳: R:R + کارمزد ─── */}
                {(r.rr_net != null || r.rr != null) && (
                  <div className="flex items-center justify-between text-[9px] mb-1">
                    <span className="text-blue-500">
                      R:R خالص{" "}
                      <span className="num font-bold">
                        {r.rr_net != null
                          ? r.rr_net.toFixed(2)
                          : r.rr != null
                            ? r.rr.toFixed(2)
                            : "—"}
                      </span>
                    </span>
                    {r.fee_pct != null && (
                      <span className="num text-muted-foreground">
                        کارمزد {r.fee_pct.toFixed(2)}%
                      </span>
                    )}
                  </div>
                )}

                {/* ─── خط ۴: منبع + TF + زمان ─── */}
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
                          {formatTimeLeft(leftMin)}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

        {!loading && sortedItems.length > visibleCount && (
          <button
            onClick={() => setVisibleCount((c) => c + 10)}
            className="w-full rounded-md border border-border py-1.5 text-[10px] text-muted-foreground transition-colors hover:bg-muted/50"
          >
            نمایش {Math.min(10, sortedItems.length - visibleCount)} مورد بیشتر
            ({visibleCount} از {sortedItems.length})
          </button>
        )}
      </div>
    </div>
  );
}