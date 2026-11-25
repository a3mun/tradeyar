
"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  ArrowDown,
  ArrowUp,
  Crown,
  Info,
  RefreshCw,
  Clock3,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { formatNumber } from "@/lib/display";

import {
  QUOTE_SOURCE_META,
  sourceSupportsPair,
} from "@/lib/sources";

const POLL_MS = 15000;

interface QuoteRow {
  source: string;
  price: number | null;
  prevPrice: number | null;
  available: boolean;
  pending: boolean;
  reason?: string;
}

interface QuoteResult {
  source: string;
  price: number | null;
  available: boolean;
}

export function PriceComparison() {
  const { ticker, timeframe, source: userSource } = useAppStore();

  // فقط صرافی‌هایی که بازار موردنظر را پشتیبانی می‌کنند
  const sources = useMemo(
    () =>
      QUOTE_SOURCE_META.filter((s) =>
        sourceSupportsPair(s.value, ticker)
      ),
    [ticker]
  );

  const [rows, setRows] = useState<QuoteRow[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const prevRef = useRef<Record<string, number>>({});

  // مدیریت درخواست‌ها
  const controllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);
  const inFlightRef = useRef(false);

  const fetchAll = useCallback(async () => {
    if (!ticker || inFlightRef.current || sources.length === 0) {
      return;
    }

    inFlightRef.current = true;

    const requestId = ++requestIdRef.current;
    const controller = new AbortController();

    controllerRef.current = controller;

    setRefreshing(true);

    const isCurrentRequest = () =>
      requestIdRef.current === requestId &&
      !controller.signal.aborted;

    try {
      const requests = sources.map(async (s): Promise<QuoteResult> => {
        try {
          const res = await api.get("/analyze/quote", {
            params: {
              ticker,
              source: s.value,
            },
            signal: controller.signal,
          });

          const rawPrice = res.data.price;

          const price =
            typeof rawPrice === "number" &&
            Number.isFinite(rawPrice)
              ? rawPrice
              : null;

          const result: QuoteResult = {
            source: s.value,
            price,
            available: res.data.available !== false,
          };

          // هر صرافی بلافاصله بعد از پاسخ خودش نمایش داده شود
          if (isCurrentRequest()) {
            setRows((currentRows) =>
              currentRows.map((row) => {
                if (row.source !== s.value) {
                  return row;
                }

                const previousPrice =
                  prevRef.current[s.value] ?? price;

                if (price !== null) {
                  prevRef.current[s.value] = price;
                }

                return {
                  source: s.value,
                  price,
                  prevPrice: previousPrice,
                  available: result.available,
                  pending: false,
                  reason: !result.available
                    ? s.value === "tsetmc"
                      ? "بورس تهران فقط سهام داخلی دارد"
                      : "این نماد روی این صرافی لیست نیست"
                    : undefined,
                };
              })
            );
          }

          return result;
        } catch (err: any) {
          // درخواست لغوشده خطا محسوب نمی‌شود
          if (
            controller.signal.aborted ||
            err?.code === "ERR_CANCELED" ||
            err?.name === "CanceledError" ||
            err?.name === "AbortError"
          ) {
            return {
              source: s.value,
              price: null,
              available: false,
            };
          }

          // 404 یعنی این بازار در صرافی وجود ندارد
          if (err?.response?.status === 404) {
            const result: QuoteResult = {
              source: s.value,
              price: null,
              available: false,
            };

            if (isCurrentRequest()) {
              setRows((currentRows) =>
                currentRows.map((row) =>
                  row.source === s.value
                    ? {
                        ...row,
                        price: null,
                        pending: false,
                        available: false,
                        reason:
                          s.value === "tsetmc"
                            ? "بورس تهران فقط سهام داخلی دارد"
                            : "این نماد روی این صرافی لیست نیست",
                      }
                    : row
                )
              );
            }

            return result;
          }

          // خطای مستقل هر صرافی؛ سایر درخواست‌ها ادامه می‌یابند
          console.error(
            "[PriceComparison]",
            err?.config?.url,
            err?.message
          );

          if (isCurrentRequest()) {
            setRows((currentRows) =>
              currentRows.map((row) =>
                row.source === s.value
                  ? {
                      ...row,
                      price: null,
                      pending: false,
                      available: false,
                      reason: "دریافت قیمت با خطا مواجه شد",
                    }
                  : row
              )
            );
          }

          return {
            source: s.value,
            price: null,
            available: false,
          };
        }
      });

      await Promise.all(requests);

      if (isCurrentRequest()) {
        setLastUpdated(new Date());
      }
    } finally {
      // فقط درخواست فعال اجازه تغییر وضعیت نهایی را دارد
      if (requestIdRef.current === requestId) {
        inFlightRef.current = false;
        controllerRef.current = null;
        setRefreshing(false);
      }
    }
  }, [ticker, sources]);

  useEffect(() => {
    if (!ticker) return;

    let cancelled = false;

    // لغو درخواست قبلی در صورت تغییر نماد
    controllerRef.current?.abort();
    requestIdRef.current++;
    inFlightRef.current = false;
    prevRef.current = {};

    setLastUpdated(null);
    setRefreshing(false);

    // آماده‌سازی ردیف‌ها برای نماد جدید
    queueMicrotask(() => {
      if (cancelled) return;

      setRows(
        sources.map((s) => ({
          source: s.value,
          price: null,
          prevPrice: null,
          available: true,
          pending: true,
        }))
      );

      fetchAll();
    });

    // به‌روزرسانی دوره‌ای بدون هم‌پوشانی درخواست‌ها
    const intervalId = window.setInterval(() => {
      if (!cancelled) {
        fetchAll();
      }
    }, POLL_MS);

    return () => {
      cancelled = true;

      window.clearInterval(intervalId);

      controllerRef.current?.abort();

      requestIdRef.current++;
      inFlightRef.current = false;
      controllerRef.current = null;
    };
  }, [ticker, sources, fetchAll]);

  // ردیف‌های قابل نمایش
  const displayRows = sources.map((s) => {
    return (
      rows.find((r) => r.source === s.value) ?? {
        source: s.value,
        price: null,
        prevPrice: null,
        available: true,
        pending: true,
      }
    );
  });

  // محاسبه قیمت‌های معتبر
  const validPrices = displayRows
    .filter(
      (r) =>
        r.price !== null &&
        Number.isFinite(r.price) &&
        r.price > 0
    )
    .map((r) => r.price as number);

  const minPrice = validPrices.length
    ? Math.min(...validPrices)
    : 0;

  const maxPrice = validPrices.length
    ? Math.max(...validPrices)
    : 0;

  const spread =
    minPrice > 0
      ? ((maxPrice - minPrice) / minPrice) * 100
      : 0;

  const unavailableCount = displayRows.filter(
    (r) => !r.pending && (!r.price || !r.available)
  ).length;

  const pendingCount = displayRows.filter(
    (r) => r.pending
  ).length;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-xs">
            💰 مقایسه قیمت
          </CardTitle>

          <div className="flex items-center gap-1.5">
            {refreshing && (
              <RefreshCw className="h-3 w-3 animate-spin text-muted-foreground" />
            )}

            <span className="text-[9px] text-muted-foreground">
              {refreshing ? "به‌روزرسانی..." : "به‌روز"}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-1 text-[9px] text-muted-foreground">
          <span>
            {ticker} · {timeframe} · اختلاف کل:{" "}
            <span className="num font-semibold">
              {spread.toFixed(2)}%
            </span>
          </span>

          {unavailableCount > 0 && (
            <span className="opacity-70">
              {unavailableCount} صرافی بدون قیمت
            </span>
          )}
        </div>

        {lastUpdated && (
          <div className="flex items-center gap-1 text-[9px] text-muted-foreground/70">
            <Clock3 className="h-2.5 w-2.5" />
            آخرین بررسی:{" "}
            {lastUpdated.toLocaleTimeString("fa-IR", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}

            {pendingCount > 0 && (
              <span className="mr-1">
                · دریافت {pendingCount} مورد باقی مانده
              </span>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-1.5 p-3">
        {displayRows.length === 0 ? (
          <div className="rounded-md bg-muted/10 p-4 text-center text-[10px] text-muted-foreground">
            برای این نماد صرافی پشتیبانی‌شده‌ای وجود ندارد.
          </div>
        ) : (
          displayRows.map((r) => {
            const src = QUOTE_SOURCE_META.find(
              (s) => s.value === r.source
            );

            if (!src) return null;

            // هنوز پاسخ این صرافی نرسیده است
            if (r.pending) {
              return (
                <div
                  key={r.source}
                  className="grid grid-cols-[minmax(0,1fr)_auto_3.5rem] items-center gap-2 rounded-md bg-muted/10 px-2 py-1.5"
                >
                  <span className="flex items-center gap-1 truncate text-[10px] font-medium">
                    <span>{src.icon}</span>
                    <span className="truncate">{src.label}</span>
                  </span>

                  <Skeleton className="h-4 w-16" />

                  <span />
                </div>
              );
            }

            // صرافی قیمت معتبر ندارد
            if (
              r.price === null ||
              !Number.isFinite(r.price) ||
              r.price <= 0
            ) {
              return (
                <div
                  key={r.source}
                  className="grid grid-cols-[minmax(0,1fr)_auto_3.5rem] items-center gap-2 rounded-md bg-muted/10 px-2 py-1.5 opacity-60"
                >
                  <span className="flex items-center gap-1 truncate text-[10px] font-medium">
                    <span>{src.icon}</span>
                    <span className="truncate">{src.label}</span>

                    <span
                      title={
                        r.reason ||
                        "این صرافی در دسترس نیست"
                      }
                      className="shrink-0"
                    >
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

            const up =
              r.prevPrice !== null &&
              r.price > r.prevPrice;

            const down =
              r.prevPrice !== null &&
              r.price < r.prevPrice;

            const isBest =
              r.price === minPrice && minPrice > 0;

            const diffPct =
              minPrice > 0
                ? ((r.price - minPrice) / minPrice) * 100
                : 0;

            const isUserSource =
              r.source === userSource;

            return (
              <div
                key={r.source}
                className={`grid grid-cols-[minmax(0,1fr)_auto_3.5rem] items-center gap-2 rounded-md px-2 py-1.5 transition-colors duration-200 ${
                  isBest
                    ? "border border-green-500/30 bg-green-500/10"
                    : isUserSource
                      ? "border border-blue-500/20 bg-blue-500/5"
                      : "bg-muted/20"
                }`}
              >
                {/* نام صرافی */}
                <span className="flex items-center gap-1 truncate text-[10px] font-medium">
                  {isBest && (
                    <Crown className="h-3 w-3 shrink-0 text-yellow-500" />
                  )}

                  <span>{src.icon}</span>

                  <span className="truncate">
                    {src.label}
                  </span>
                </span>

                {/* قیمت */}
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

                  {up && (
                    <ArrowUp className="h-2.5 w-2.5 shrink-0 text-green-500" />
                  )}

                  {down && (
                    <ArrowDown className="h-2.5 w-2.5 shrink-0 text-red-500" />
                  )}
                </span>

                {/* اختلاف قیمت */}
                <span className="num text-left text-[9px] tabular-nums text-muted-foreground">
                  {!isBest && diffPct > 0.01
                    ? `+${diffPct.toFixed(2)}%`
                    : ""}
                </span>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
