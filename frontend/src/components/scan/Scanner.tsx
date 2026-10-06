"use client";

/**
 * Scanner — اسکنر فرصت‌ها (نسخه ۴.۲)
 * ============================================================
 * 🔴 تغییرات نسخه ۴.۲:
 *   • فیلتر قوی نمادهای میم‌کوین (قیمت < ۰.۰۰۰۱)
 *   • موبایل: چیدمان فشرده با قیمت + متن سیگنال
 *   • فرمت علمی برای اعداد خیلی کوچیک
 */

import { useState } from "react";
import {
  Target,
  Search,
  Info,
  X,
  Plus,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  TrendingUp,
  Star,
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
import { CryptoIcon } from "@/components/ui/crypto-icon";

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

const CACHE_TTL_MS = 60_000;

/**
 * 🔴 حد پایین قیمت برای نمایش.
 * میم‌کوین‌های زیر این مقدار، در TF کوتاه فقط کارمزد می‌خورن.
 */
const MIN_PRICE = 0.001;

interface CachedScan {
  data: ScanResponse;
  scannedTf: string;
  cachedAt: number;
}

const scanCache = new Map<string, CachedScan>();

function getCacheKey(source: Source, timeframe: string): string {
  return `${source}:${timeframe}`;
}

type FilterType = "all" | "hot" | "long" | "short";

export function Scanner() {
  const {
    setTicker,
    source: globalSource,
    setSource,
    timeframe,
    addToWatchlist,
    watchlist,
  } = useAppStore();

  const [scanSource, setScanSource] = useState<Source>(globalSource);
  const [filter, setFilter] = useState<FilterType>("all");
  const [data, setData] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [scannedTf, setScannedTf] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheHit, setCacheHit] = useState(false);

  const [recordingTicker, setRecordingTicker] = useState<string | null>(null);
  const [recordedTickers, setRecordedTickers] = useState<Set<string>>(
    new Set()
  );

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

  const handleAnalyze = (item: ScanItem) => {
    setSource(scanSource as never);
    setTimeout(() => setTicker(item.ticker, item.name), 50);
  };

  const handleRecord = async (item: ScanItem) => {
    setRecordingTicker(item.ticker);
    try {
      await api.post("/backtest/record", {
        ticker: item.ticker,
        source: scanSource,
        timeframe,
        market_type: scanSource === "tsetmc" ? "spot" : "futures",
        risk_profile: "aggressive",
        ticker_name: item.name,
      });
      setRecordedTickers((prev) => {
        const next = new Set(prev);
        next.add(item.ticker);
        return next;
      });
    } catch {
      // خطا بی‌صدا
    } finally {
      setRecordingTicker(null);
    }
  };

  const handleWatchlist = (item: ScanItem) => {
    addToWatchlist(item.ticker, item.name, scanSource);
  };

  const isTsetmc = scanSource === "tsetmc";

  // ═══ فیلتر نهایی ═══
  const filtered =
    data?.items.filter((item: ScanItem) => {
      // فیلتر نماد بورس/کریپتو
      if (isTsetmc) {
        if (/^[A-Z]/.test(item.ticker)) return false;
      } else {
        if (!/^[A-Z]/.test(item.ticker)) return false;
      }

      // ═══ 🔴 فیلتر قوی قیمت ═══
      // کریپتو: قیمت باید >= MIN_PRICE باشه
      // بورس: قیمت صفر = نماد متوقف → نشون بده با "—"
      if (!isTsetmc) {
        if (!item.price || item.price < MIN_PRICE) return false;
      }

      if (filter === "all") return true;
      if (filter === "hot") return item.confidence >= 70;
      if (filter === "long") return item.direction === "long";
      if (filter === "short") return item.direction === "short";
      return true;
    }) || [];

  const scanSourceLabel =
    SOURCES.find((s) => s.key === scanSource)?.label ?? scanSource;

  const counts = {
    all:
      data?.items.filter((i) => isTsetmc || i.price >= MIN_PRICE).length ?? 0,
    hot:
      data?.items.filter(
        (i) => (isTsetmc || i.price >= MIN_PRICE) && i.confidence >= 70
      ).length ?? 0,
    long:
      data?.items.filter(
        (i) =>
          (isTsetmc || i.price >= MIN_PRICE) && i.direction === "long"
      ).length ?? 0,
    short:
      data?.items.filter(
        (i) =>
          (isTsetmc || i.price >= MIN_PRICE) && i.direction === "short"
      ).length ?? 0,
  };

// ═══ فرمت فشرده قیمت برای موبایل ═══
const formatCompact = (price: number, ticker: string): string => {
  if (isTsetmc && price === 0) return "—";
  if (price === 0) return "—";

  // ─── اعداد خیلی کوچیک (مثل ONE-USD = 0.0022) ───
  if (price < 0.01) {
    return price.toFixed(5);
  }
  if (price < 1) {
    return price.toFixed(3);
  }
  if (price < 1000) {
    return price.toFixed(2);
  }
  // ─── اعداد بزرگ (مثل BTC-IRT) ───
  return formatNumber(price);
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
                ? `${filtered.length} فرصت روی ${scanSourceLabel} · ${scannedTf}`
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
                  📈 ({counts.long})
                </button>
                <button
                  onClick={() => setFilter("short")}
                  className={`rounded-md border-2 py-1 text-[10px] font-medium transition-all ${
                    filter === "short"
                      ? "border-red-500 bg-red-500/10 text-red-500"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  📉 ({counts.short})
                </button>
              </div>
            )}

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
        <CardContent className="px-2 sm:px-4">
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
            <Table className="w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="text-right">نماد</TableHead>
                  <TableHead className="text-center">سیگنال</TableHead>
                  <TableHead className="text-right">قیمت</TableHead>
                  <TableHead className="text-center">اطمینان</TableHead>
                  <TableHead className="text-center">عملیات</TableHead>
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
                        <Skeleton className="h-5 w-16 mx-auto" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-5 w-16" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-5 w-12 mx-auto" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-5 w-24 mx-auto" />
                      </TableCell>
                    </TableRow>
                  ))}

                {!loading && filtered.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="text-center text-xs text-muted-foreground"
                    >
                      {data && data.items.length > 0
                        ? `هیچ نمادی با قیمت بالای ${MIN_PRICE}$ پیدا نشد — میم‌کوین‌ها فیلتر شدند`
                        : "فرصتی با این فیلتر پیدا نشد"}
                    </TableCell>
                  </TableRow>
                )}

                {!loading &&
                  filtered.map((item) => {
                    const inWatchlist = watchlist.some(
                      (w) => w.ticker === item.ticker
                    );
                    const isRecording = recordingTicker === item.ticker;
                    const isRecorded = recordedTickers.has(item.ticker);

                    // ─── بج سیگنال (LONG/SHORT) ───
                    const isLong = item.direction === "long";
                    const isShort = item.direction === "short";
                    const sigBadgeCls = isLong
                      ? "bg-green-500/15 text-green-500 border-green-500/30"
                      : isShort
                        ? "bg-red-500/15 text-red-500 border-red-500/30"
                        : "bg-muted/40 text-muted-foreground border-border";

                    return (
                      <TableRow key={item.ticker}>
                        {/* ═══ نماد ═══ */}
                        <TableCell className="text-right">
                          <div className="flex items-center gap-1.5">
                            <CryptoIcon ticker={item.ticker} size="sm" />
                            <div className="min-w-0">
                              <p className="truncate text-xs font-bold">
                                {item.name}
                              </p>
                              <p className="num truncate text-[9px] text-muted-foreground">
                                {item.ticker}
                              </p>
                            </div>
                          </div>
                        </TableCell>

                        {/* ═══ سیگنال — بج رنگی ═══ */}
                        <TableCell className="text-center">
                          <span
                            className={`inline-block rounded border px-1.5 py-0 text-[9px] font-bold sm:text-[10px] ${sigBadgeCls}`}
                          >
                            {item.direction === "long"
                              ? "LONG"
                              : item.direction === "short"
                                ? "SHORT"
                                : "—"}
                          </span>
                        </TableCell>

                        {/* ═══ قیمت — فشرده در موبایل ═══ */}
                        <TableCell className="num text-right text-[10px] sm:text-xs">
                          <span className="hidden sm:inline">
                            {isTsetmc && item.price === 0
                              ? "—"
                              : formatNumber(item.price)}
                          </span>
                          <span className="sm:hidden">
                            {formatCompact(item.price, item.ticker)}
                          </span>
                        </TableCell>

                        {/* ═══ اطمینان ═══ */}
                        <TableCell className="text-center">
                          <Badge
                            variant="outline"
                            className={`num text-[9px] sm:text-[10px] ${confidenceColor(
                              item.confidence
                            )}`}
                          >
                            {item.confidence}%
                          </Badge>
                        </TableCell>

                        {/* ═══ عملیات ═══ */}
                        <TableCell>
                          {/* ─── موبایل: آیکون ─── */}
                          <div className="flex items-center justify-center gap-0.5 sm:hidden">
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-6 w-6 text-blue-500"
                              onClick={() => handleAnalyze(item)}
                            >
                              <TrendingUp className="h-3 w-3" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className={`h-6 w-6 ${
                                isRecorded
                                  ? "text-green-500"
                                  : "text-purple-500"
                              }`}
                              onClick={() => handleRecord(item)}
                              disabled={isRecording || isRecorded}
                            >
                              {isRecording ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <CheckCircle2 className="h-3 w-3" />
                              )}
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className={`h-6 w-6 ${
                                inWatchlist
                                  ? "text-yellow-500"
                                  : "text-muted-foreground"
                              }`}
                              onClick={() => handleWatchlist(item)}
                            >
                              <Star
                                className={`h-3 w-3 ${
                                  inWatchlist ? "fill-current" : ""
                                }`}
                              />
                            </Button>
                          </div>

                          {/* ─── دسکتاپ: دکمه فارسی ─── */}
                          <div className="hidden sm:flex items-center justify-center gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-2 text-[9px] text-blue-500 hover:bg-blue-500/10"
                              onClick={() => handleAnalyze(item)}
                            >
                              <TrendingUp className="h-2.5 w-2.5 ml-0.5" />
                              تحلیل
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className={`h-6 px-2 text-[9px] ${
                                isRecorded
                                  ? "text-green-500"
                                  : "text-purple-500 hover:bg-purple-500/10"
                              }`}
                              onClick={() => handleRecord(item)}
                              disabled={isRecording || isRecorded}
                            >
                              {isRecording ? (
                                <Loader2 className="h-2.5 w-2.5 animate-spin ml-0.5" />
                              ) : (
                                <CheckCircle2 className="h-2.5 w-2.5 ml-0.5" />
                              )}
                              {isRecorded ? "ثبت شده" : "راستی‌آزمایی"}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className={`h-6 px-2 text-[9px] ${
                                inWatchlist
                                  ? "text-yellow-500"
                                  : "text-muted-foreground hover:text-yellow-500"
                              }`}
                              onClick={() => handleWatchlist(item)}
                            >
                              <Star
                                className={`h-2.5 w-2.5 ml-0.5 ${
                                  inWatchlist ? "fill-current" : ""
                                }`}
                              />
                              {inWatchlist ? "ذخیره شده" : "واچ‌لیست"}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      )}
    </Card>
  );
}