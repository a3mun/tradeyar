"use client";

/**
 * Scanner — اسکنر فرصت‌ها (نسخه ۳.۰)
 * ============================================================
 * ═══ تغییرات نسخه ۳.۰ ═══
 *   • فیلتر دکمه‌ای رنگی (به جای Select)
 *   • دکمه «🔥 فرصت ویژه» (confidence >= ۷۰)
 *   • فیلتر `price > 0` (جلوگیری از نمایش قیمت صفر)
 */

import { useState } from "react";
import {
  Target,
  Search,
  Info,
  X,
  Plus,
  AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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
import { signalColor, confidenceColor, formatNumber } from "@/lib/display";
import { SOURCE_BY_KEY } from "@/lib/sources";
import type { ScanResponse, ScanItem } from "@/lib/types";
import type { Source } from "@/lib/types";

const SOURCES: { key: Source; label: string }[] = [
  { key: "nobitex", label: "نوبیتکس" },
  { key: "bitpin", label: "بیت‌پین" },
  { key: "wallex", label: "والکس" },
  { key: "tabdeal", label: "تبدیل" },
  { key: "tsetmc", label: "بورس" },
];

const CATEGORIES_BY_SOURCE: Record<string, string> = {
  nobitex: "crypto",
  bitpin: "crypto",
  wallex: "crypto",
  tabdeal: "crypto",
  tsetmc: "iran_stocks",
};

// ═══ Cache — نگه‌داشتن نتیجه‌ی اخیر هر صرافی ═══
const CACHE_TTL_MS = 60_000;

interface CachedScan {
  data: ScanResponse;
  scannedTf: string;
  cachedAt: number;
}

const scanCache = new Map<string, CachedScan>();

function getCacheKey(source: Source, timeframe: string): string {
  return `${source}:${timeframe}`;
}

// ═══ انواع فیلتر ═══
type FilterType = "all" | "hot" | "long" | "short";

export function Scanner() {
  const {
    setTicker,
    source: globalSource,
    setSource,
    timeframe,
    addToWatchlist,
  } = useAppStore();
  const [scanSource, setScanSource] = useState<Source>(globalSource);
  const [filter, setFilter] = useState<FilterType>("all");
  const [data, setData] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [scannedTf, setScannedTf] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheHit, setCacheHit] = useState(false);

  // ═══ cache ═══
  const applyCacheIfFresh = (src: Source, tf: string) => {
    const key = getCacheKey(src, tf);
    const cached = scanCache.get(key);
    if (cached && Date.now() - cached.cachedAt < CACHE_TTL_MS) {
      setData(cached.data);
      setScannedTf(cached.scannedTf);
      setError(null);
      setCacheHit(true);
      return true;
    }
    return false;
  };

  const handleSourceChange = (src: Source) => {
    setScanSource(src);
    setError(null);
    setCacheHit(false);
    if (!applyCacheIfFresh(src, timeframe)) {
      setData(null);
    }
  };

  // ═══ اسکن ═══
  const handleScan = () => {
    const cacheKey = getCacheKey(scanSource, timeframe);
    const cached = scanCache.get(cacheKey);
    if (cached && Date.now() - cached.cachedAt < CACHE_TTL_MS) {
      setData(cached.data);
      setScannedTf(cached.scannedTf);
      setError(null);
      setCacheHit(true);
      return;
    }

    setLoading(true);
    setError(null);
    setCacheHit(false);
    setScannedTf(timeframe);
    const category = CATEGORIES_BY_SOURCE[scanSource] || "crypto";
    const marketType = scanSource === "tsetmc" ? "spot" : "futures";

    api
      .post("/scan", {
        source: scanSource,
        category,
        timeframe,
        market_type: marketType,
        risk_profile: "aggressive",
        limit: 50,
      })
      .then((res) => {
        setData(res.data);
        setError(null);
        scanCache.set(cacheKey, {
          data: res.data,
          scannedTf: timeframe,
          cachedAt: Date.now(),
        });
      })
      .catch((err) => {
        setData(null);
        const status = err.response?.status;
        if (status === 429) {
          setError(
            "تعداد درخواست‌ها بیش از حد مجاز — لطفاً یک دقیقه دیگر تلاش کنید"
          );
        } else {
          setError("اسکن ناموفق بود — دوباره تلاش کنید");
        }
      })
      .finally(() => setLoading(false));
  };

  // ═══ فیلتر ═══
  const filtered =
    data?.items.filter((item: ScanItem) => {
      // ─── فیلتر بر اساس نوع صرافی ───
      if (scanSource === "tsetmc") {
        if (/^[A-Z]/.test(item.ticker)) return false;
      } else {
        if (!/^[A-Z]/.test(item.ticker)) return false;
      }

      // ─── فیلتر قیمت صفر ───
      if (!item.price || item.price <= 0) return false;

      // ─── فیلتر نوع سیگنال ───
      if (filter === "all") return true;
      if (filter === "hot") return item.confidence >= 70;
      if (filter === "long") return item.direction === "long";
      if (filter === "short") return item.direction === "short";
      return true;
    }) || [];

  const isTsetmc = scanSource === "tsetmc";
  const scanSourceLabel =
    SOURCES.find((s) => s.key === scanSource)?.label ?? scanSource;

  // ═══ شمارش هر فیلتر (برای نمایش در بج) ═══
  const counts = {
    all: data?.items.filter((i) => i.price > 0).length ?? 0,
    hot: data?.items.filter((i) => i.price > 0 && i.confidence >= 70).length ?? 0,
    long:
      data?.items.filter((i) => i.price > 0 && i.direction === "long").length ??
      0,
    short:
      data?.items.filter((i) => i.price > 0 && i.direction === "short").length ??
      0,
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Target className="h-4 w-4" />
              اسکنر فرصت‌ها
            </CardTitle>
            <p className="text-[10px] text-muted-foreground mt-1">
              {data
                ? `${data.total} فرصت روی ${scanSourceLabel} · ${scannedTf}`
                : "صرافی رو انتخاب کن و روی «بررسی فرصت» بزن"}
              {cacheHit && (
                <span className="mr-2 text-green-500">· از cache</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {data && (
              <Button
                size="icon"
                variant="ghost"
                onClick={() => setCollapsed(true)}
                className="h-8 w-8"
                title="جمع کردن"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {collapsed ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCollapsed(false)}
            className="w-full mt-2"
          >
            <Plus className="h-3.5 w-3.5" />
            باز کردن اسکنر
          </Button>
        ) : (
          <div className="space-y-2 pt-2">
            {/* ═══ صرافی‌ها ═══ */}
            <div className="grid grid-cols-5 gap-1.5">
              {SOURCES.map((s) => {
                const meta = SOURCE_BY_KEY[s.key];
                const hasCache =
                  scanCache.has(getCacheKey(s.key, timeframe)) &&
                  Date.now() -
                    (scanCache.get(getCacheKey(s.key, timeframe))?.cachedAt ??
                      0) <
                    CACHE_TTL_MS;
                return (
                  <Button
                    key={s.key}
                    size="sm"
                    variant={scanSource === s.key ? "default" : "outline"}
                    onClick={() => handleSourceChange(s.key)}
                    className="relative h-auto flex-col gap-0.5 px-1 py-2 text-[10px]"
                  >
                    {hasCache && (
                      <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-green-500" />
                    )}
                    <img
                      src={meta?.logo}
                      alt={s.label}
                      className="h-4 w-4 object-contain"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                    <span>{s.label}</span>
                  </Button>
                );
              })}
            </div>

            {/* ═══ فیلترهای دکمه‌ای (نسخه ۳.۰) ═══ */}
            {data && (
              <div className="grid grid-cols-4 gap-1">
                <button
                  onClick={() => setFilter("all")}
                  className={`rounded-md border-2 py-1 text-[10px] font-medium transition-all ${
                    filter === "all"
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  همه ({counts.all})
                </button>
                <button
                  onClick={() => setFilter("hot")}
                  className={`rounded-md border-2 py-1 text-[10px] font-medium transition-all ${
                    filter === "hot"
                      ? "border-orange-500 bg-orange-500/10 text-orange-400"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  🔥 ویژه ({counts.hot})
                </button>
                <button
                  onClick={() => setFilter("long")}
                  className={`rounded-md border-2 py-1 text-[10px] font-medium transition-all ${
                    filter === "long"
                      ? "border-green-500 bg-green-500/10 text-green-500"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  📈 صعودی ({counts.long})
                </button>
                <button
                  onClick={() => setFilter("short")}
                  className={`rounded-md border-2 py-1 text-[10px] font-medium transition-all ${
                    filter === "short"
                      ? "border-red-500 bg-red-500/10 text-red-500"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  📉 نزولی ({counts.short})
                </button>
              </div>
            )}

            {/* ═══ دکمه بررسی ═══ */}
            <Button
              onClick={handleScan}
              disabled={loading}
              className="w-full"
              size="sm"
            >
              {loading ? (
                <>
                  <Search className="h-3.5 w-3.5 animate-spin" />
                  در حال بررسی...
                </>
              ) : (
                <>
                  <Search className="h-3.5 w-3.5" />
                  بررسی فرصت‌ها روی {scanSourceLabel}
                </>
              )}
            </Button>
          </div>
        )}
      </CardHeader>

      {!collapsed && (
        <CardContent>
          {error && !loading && (
            <div className="flex items-center justify-center gap-2 rounded-lg border border-orange-500/30 bg-orange-500/10 py-3 text-xs text-orange-400">
              <AlertTriangle className="h-4 w-4" />
              {error}
            </div>
          )}

          {!data && !loading && !error && (
            <div className="flex items-center justify-center gap-2 py-6 text-xs text-muted-foreground">
              <Info className="h-4 w-4" />
              صرافی رو انتخاب کن، بعد روی «بررسی فرصت‌ها» بزن
            </div>
          )}

          {(data || loading) && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-right">نماد</TableHead>
                  <TableHead className="text-right">سیگنال</TableHead>
                  <TableHead className="text-right">قیمت</TableHead>
                  <TableHead className="text-right">اطمینان</TableHead>
                  <TableHead className="text-right">—</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading &&
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <Skeleton className="h-5 w-24" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-5 w-20" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-5 w-16" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-5 w-12" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-5 w-8" />
                      </TableCell>
                    </TableRow>
                  ))}

                {!loading && filtered.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="text-center text-xs text-muted-foreground"
                    >
                      فرصتی با این فیلتر پیدا نشد
                    </TableCell>
                  </TableRow>
                )}

                {!loading &&
                  filtered.map((item) => (
                    <TableRow
                      key={item.ticker}
                      className="group cursor-pointer transition-colors hover:bg-muted/50"
                      onClick={() => {
                        setSource(scanSource as never);
                        setTimeout(
                          () => setTicker(item.ticker, item.name),
                          50
                        );
                      }}
                    >
                      <TableCell className="text-right">
                        <p className="text-xs font-bold">{item.name}</p>
                        <p className="num text-[10px] text-muted-foreground">
                          {item.ticker}
                        </p>
                      </TableCell>
                      <TableCell
                        className={`text-right text-xs ${signalColor(
                          item.signal
                        )}`}
                      >
                        {item.signal}
                      </TableCell>
                      <TableCell className="num text-right text-xs">
                        {isTsetmc && item.price === 0
                          ? "—"
                          : formatNumber(item.price)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge
                          variant="outline"
                          className={`num text-[10px] ${confidenceColor(
                            item.confidence
                          )}`}
                        >
                          {item.confidence}%
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-5 w-5 opacity-0 transition-opacity group-hover:opacity-100"
                          onClick={(e) => {
                            e.stopPropagation();
                            addToWatchlist(
                              item.ticker,
                              item.name,
                              scanSource
                            );
                          }}
                          title="افزودن به واچ‌لیست"
                        >
                          <Plus className="h-3 w-3" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      )}
    </Card>
  );
}