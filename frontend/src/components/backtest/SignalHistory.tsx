"use client";

/**
 * SignalHistory — تاریخچه سیگنال‌ها (نسخه ۲.۰)
 * ============================================================
 * ═══ تغییرات نسخه ۲.۰ ═══
 *   • مهلت سیگنال per-بازار (فیوچرز ۵ کندل / اسپات ۱۰ کندل)
 *   • بج «فیوچرز/اسپات» برای تفکیک بصری
 *   • Poll هر ۱۵ ثانیه (به جای ۶۰)
 */

import { useCallback, useEffect, useState } from "react";
import { History, Clock, AlertTriangle, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
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

const SOURCE_MAP: Record<string, { label: string; color: string }> = {
  nobitex: { label: "نوبیتکس", color: "text-purple-400" },
  bitpin: { label: "بیت‌پین", color: "text-green-400" },
  wallex: { label: "والکس", color: "text-blue-400" },
  tabdeal: { label: "تبدیل", color: "text-orange-400" },
  tsetmc: { label: "بورس", color: "text-emerald-400" },
};

// ═══ مهلت سیگنال (هماهنگ با backend — core/contracts.py) ═══
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
  if (min < 60) return `${min} دقیقه`;
  const hr = Math.floor(min / 60);
  const m = min % 60;
  if (hr < 24) return `${hr}h ${m}m`;
  return `${Math.floor(hr / 24)} روز`;
}

export function SignalHistory() {
  const [items, setItems] = useState<SignalHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("all");
  const [visibleCount, setVisibleCount] = useState(8);

  const silentFetch = useCallback(async () => {
    try {
      const res = await api.get("/backtest/history", {
        params: { limit: 200, status },
      });
      setItems(res.data.items || []);
      setError("");
    } catch {
      setError("دریافت تاریخچه ناموفق بود");
    }
  }, [status]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const res = await api.get("/backtest/history", {
          params: { limit: 200, status },
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
  }, [status]);

  // ═══ به‌روزرسانی دوره‌ای — هر ۱۵ ثانیه ═══
  useEffect(() => {
    const id = setInterval(silentFetch, 15000);
    return () => clearInterval(id);
  }, [silentFetch]);

  // ═══ Sort هوشمند ═══
  const sortedItems = [...items].sort((a, b) => {
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
      // ─── منقضی با PnL (نسخه ۲.۰) ───
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
      return <Badge variant="secondary" className="text-[9px]">⏰ منقضی</Badge>;
    }
    return (
      <Badge variant="outline" className="text-[9px] text-yellow-500">
        ⏳ انتظار
      </Badge>
    );
  };
  
  return (
    <CollapsibleCard
      title={
        <span className="flex items-center gap-1.5">
          <History className="h-3.5 w-3.5" />
          تاریخچه سیگنال‌ها
        </span>
      }
      badge={
        <span className="num rounded-full bg-muted px-1.5 text-[9px]">
          {items.length}
        </span>
      }
      subtitle={
        pendingCount > 0
          ? `${pendingCount} سیگنال در انتظار بررسی`
          : "بررسی خودکار روی سرور فعال است"
      }
    >
      <div className="mb-2 flex justify-end">
        <Select
          value={status}
          onValueChange={(v) => {
            if (!v) return;
            setVisibleCount(8);
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
              ? "هنوز سیگنالی ثبت نشده — بعد از اولین تحلیل اینجا میاد"
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

            // ─── آیکن جهت ───
            const DirectionIcon =
              r.direction === "long"
                ? TrendingUp
                : r.direction === "short"
                  ? TrendingDown
                  : Minus;

            // ─── بج بازار ───
            const isFutures = r.market_type === "futures";

            return (
              <div
                key={r.id}
                className="rounded-lg border border-border/40 bg-muted/10 p-2.5"
              >
                {/* ─── خط ۱: نام + ticker + بازار + بج نتیجه ─── */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-bold">{r.name}</span>
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
                      {isFutures ? "📈 فیوچرز" : "💵 اسپات"}
                    </Badge>
                    {r.had_trap && r.trap_type && (
                      <Badge className="bg-orange-600/20 text-orange-400 text-[8px] border-orange-500/30">
                        <AlertTriangle className="h-2 w-2 ml-0.5" />
                        {TRAP_LABEL[r.trap_type] || r.trap_type}
                      </Badge>
                    )}
                  </div>
                  {resultBadge(
                    r.result,
                    r.expired,
                    r.expired_pnl_pct,
                    r.expired_bias
                  )}
                </div>

                {/* ─── خط ۲: سیگنال + confidence + ورود ─── */}
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

                {/* ─── خط ۳: R:R خالص + کارمزد ─── */}
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
                          {formatTimeLeft(leftMin)} مونده
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* ─── خط ۵: خروج (اگه result داره) ─── */}
                {r.result_time && r.exit_price && (
                  <div className="mt-1 text-[9px] text-muted-foreground text-left">
                    خروج: {formatNumber(r.exit_price)} ·{" "}
                    {toJalali(r.result_time)}
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

        <p className="rounded-md bg-green-500/5 p-2 text-[9px] text-green-500">
          ✅ بررسی سیگنال‌ها مستقل روی سرور اجرا می‌شود — بستن این کشو
          تأثیری روی راستی‌آزمایی ندارد.
        </p>
      </div>
    </CollapsibleCard>
  );
}