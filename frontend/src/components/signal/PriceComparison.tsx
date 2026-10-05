"use client";

/**
 * PriceComparison — مقایسه قیمت بین صرافی‌ها
 * ============================================================
 * 🔴 قواعد مهم (نسخه ۱.۸):
 *
 * ۱. **قیمت مستقل است.** هر صرافی قیمت خودش را می‌دهد. هرگز
 *    قیمت صرافی دیگر با برچسب این صرافی برنمی‌گردد (بک‌اند هم
 *    تضمین می‌کند).
 *
 * ۲. **فقط صرافی‌هایی که بازار دارند پرسیده می‌شوند.** پیش‌تر
 *    همه‌ی صرافی‌ها کورکورانه پرسیده می‌شدند و برای BTC-USD از
 *    ``tsetmc`` (بورس) جواب ۴۰۴ می‌آمد → Console آلوده.
 *    حالا با ``sourceSupportsPair`` **قبل از درخواست** فیلتر
 *    می‌شود (بدون هزینه‌ی شبکه).
 *
 * ۳. اگر با این حال ۴۰۴ آمد، **بی‌صدا** رد می‌شود (نه log error).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Crown, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { formatNumber } from "@/lib/display";
import {
  QUOTE_SOURCE_META,
  sourceSupportsPair,
} from "@/lib/sources";

const POLL_MS = 10000;

interface QuoteRow {
  source: string;
  price: number | null;
  prevPrice: number | null;
  /** آیا صرافی این بازار را دارد؟ */
  available: boolean;
  /** علت در دسترس نبودن (برای tooltip) */
  reason?: string;
}

export function PriceComparison() {
  const { ticker, timeframe, source: userSource } = useAppStore();

  // ─── 🔴 فیلتر قبل از درخواست: فقط صرافی‌های دارای این بازار ───
  const sources = QUOTE_SOURCE_META.filter((s) =>
    sourceSupportsPair(s.value, ticker)
  );

  const [rows, setRows] = useState<QuoteRow[]>([]);
  const [loading, setLoading] = useState(true);
  const prevRef = useRef<Record<string, number>>({});

  const fetchAll = useCallback(() => {
    Promise.all(
      sources.map((s) =>
        api
          .get("/analyze/quote", { params: { ticker, source: s.value } })
          .then((res) => ({
            source: s.value,
            price: (res.data.price as number | null) ?? null,
            available: res.data.available !== false,
          }))
          .catch(() => ({
            // ─── ۴۰۴ = این صرافی این بازار را ندارد (نه خطا) ───
            // ⚠️ بی‌صدا رد می‌شود تا Console تمیز بماند.
            source: s.value,
            price: null,
            available: false,
          }))
      )
    ).then((results) => {
      const newRows: QuoteRow[] = results.map((r) => ({
        source: r.source,
        price: r.price,
        prevPrice: prevRef.current[r.source] ?? r.price,
        available: r.available,
        reason: !r.available
          ? r.source === "tsetmc"
            ? "بورس تهران فقط سهام داخلی دارد"
            : "این نماد روی این صرافی لیست نیست"
          : undefined,
      }));
      results.forEach((r) => {
        if (r.price !== null) prevRef.current[r.source] = r.price;
      });
      setRows(newRows);
      setLoading(false);
    });
    // ⚠️ sources آرایه‌ی جدید در هر رندر است — به ticker وابسته‌ایم
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  useEffect(() => {
    if (!ticker) return;

    let cancelled = false;

    // ─── setState داخل microtask تا ESLint
    //     (react-hooks/set-state-in-effect) راضی بماند ───
    queueMicrotask(() => {
      if (cancelled) return;
      setLoading(true);
      prevRef.current = {};
      fetchAll();
    });

    const id = setInterval(() => {
      if (!cancelled) fetchAll();
    }, POLL_MS);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [ticker, fetchAll]);

  const validPrices = rows.filter((r) => r.price).map((r) => r.price!);
  const minPrice = validPrices.length ? Math.min(...validPrices) : 0;
  const maxPrice = validPrices.length ? Math.max(...validPrices) : 0;
  const spread = minPrice > 0 ? ((maxPrice - minPrice) / minPrice) * 100 : 0;
  const unavailableCount = rows.filter((r) => !r.price).length;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs">💰 مقایسه قیمت</CardTitle>
        <p className="text-[9px] text-muted-foreground">
          {ticker} · {timeframe} · اختلاف کل:{" "}
          <span className="num">{spread.toFixed(2)}%</span>
          {unavailableCount > 0 && (
            <span className="mr-1 text-muted-foreground/70">
              · {unavailableCount} صرافی این بازار را ندارد
            </span>
          )}
        </p>
      </CardHeader>
      <CardContent className="space-y-1.5 p-3">
        {loading
          ? sources.map((s) => (
              <Skeleton key={s.value} className="h-7 w-full" />
            ))
          : rows.map((r) => {
              const src = QUOTE_SOURCE_META.find((s) => s.value === r.source);
              if (!src) return null;

              const up =
                r.price !== null && r.prevPrice !== null && r.price > r.prevPrice;
              const down =
                r.price !== null && r.prevPrice !== null && r.price < r.prevPrice;
              const isBest = r.price === minPrice && minPrice > 0;
              const diffPct =
                r.price && minPrice > 0 ? ((r.price - minPrice) / minPrice) * 100 : 0;
              const isUserSource = r.source === userSource;

              // ─── صرافی این بازار را ندارد ───
              if (!r.price) {
                return (
                  <div
                    key={r.source}
                    className="grid grid-cols-[minmax(0,1fr)_auto_3.5rem] items-center gap-2 rounded-md bg-muted/10 px-2 py-1.5 opacity-60"
                  >
                    <span className="flex items-center gap-1 truncate text-[10px] font-medium">
                      <span>{src.icon}</span>
                      <span className="truncate">{src.label}</span>
                      <span title={r.reason} className="shrink-0">
                        <Info className="h-2.5 w-2.5 text-muted-foreground" />
                      </span>
                    </span>
                    <span className="num text-left text-[11px] text-muted-foreground">
                      —
                    </span>
                    <span />
                  </div>
                );
              }

              return (
                <div
                  key={r.source}
                  className={`grid grid-cols-[minmax(0,1fr)_auto_3.5rem] items-center gap-2 rounded-md px-2 py-1.5 ${
                    isBest
                      ? "border border-green-500/30 bg-green-500/10"
                      : isUserSource
                        ? "border border-blue-500/20 bg-blue-500/5"
                        : "bg-muted/20"
                  }`}
                >
                  {/* ─── ستون ۱: نام (عرض انعطاف، truncate) ─── */}
                  <span className="flex items-center gap-1 truncate text-[10px] font-medium">
                    {isBest && (
                      <Crown className="h-3 w-3 shrink-0 text-yellow-500" />
                    )}
                    <span>{src.icon}</span>
                    <span className="truncate">{src.label}</span>
                  </span>

                  {/* ─── ستون ۲: قیمت (راست‌چین، هم‌تراز) ─── */}
                  <span className="flex items-center justify-end gap-1">
                    <span
                      className={`num text-[11px] font-bold tabular-nums ${
                        isBest
                          ? "text-green-500"
                          : up
                            ? "text-green-500"
                            : down
                              ? "text-red-500"
                              : "text-foreground"
                      }`}
                    >
                      {formatNumber(r.price)}
                    </span>
                    {up && <ArrowUp className="h-2.5 w-2.5 shrink-0 text-green-500" />}
                    {down && (
                      <ArrowDown className="h-2.5 w-2.5 shrink-0 text-red-500" />
                    )}
                  </span>

                  {/* ─── ستون ۳: اختلاف (عرض ثابت — همیشه هم‌تراز) ─── */}
                  <span className="num text-left text-[9px] tabular-nums text-muted-foreground">
                    {!isBest && diffPct > 0.01 ? `+${diffPct.toFixed(2)}%` : ""}
                  </span>
                </div>
              );
            })}
      </CardContent>
    </Card>
  );
}
