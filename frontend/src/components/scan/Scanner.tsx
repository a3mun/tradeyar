"use client";

/**
 * Scanner — اسکنر فرصت‌ها (نسخه ۶.۰ · فاز ۱۰.۳)
 * ============================================================
 * 🔴 تغییرات نسخه ۶.۰:
 *   • انتخاب mode قبل اسکن: انفجاری / فعال / هر دو
 *   • Spot و Futures جدا
 *   • حذف ستون قیمت (بی‌اهمیت)
 *   • نماد راست‌چین، بقیه وسط‌چین
 *   • badge «🚀 انفجار» با امتیاز
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
  Rocket,
  Activity,
  Layers,
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

// ═══ Cache ═══
const CACHE_TTL_MS = 60_000;

interface CachedScan {
  data: ScanResponse;
  scannedTf: string;
  cachedAt: number;
}

const scanCache = new Map<string, CachedScan>();

function getCacheKey(source: Source, timeframe: string, mode: string, mt: string): string {
  return `${source}:${timeframe}:${mode}:${mt}`;
}

// ═══ حداقل قیمت ═══
const MIN_PRICE = 0.001;

// 🔴 فاز ۱۰.۳ — نوع scan mode
type ScanMode = "pre_breakout" | "active" | "all";

// 🔴 فاز ۱۰.۳ — نوع بازار
type MarketKind = "spot" | "futures";

const MODE_LABELS: Record<ScanMode, { icon: string; label: string; color: string }> = {
  pre_breakout: { icon: "🚀", label: "آماده انفجار", color: "purple" },
  active: { icon: "📊", label: "سیگنال فعال", color: "blue" },
  all: { icon: "🔍", label: "هر دو", color: "slate" },
};

const MARKET_LABELS: Record<MarketKind, { icon: string; label: string }> = {
  spot: { icon: "💵", label: "اسپات" },
  futures: { icon: "📈", label: "فیوچرز" },
};

// ═══ فیلترهای نمایش روی نتیجه ═══
type FilterType = "all" | "pre_breakout" | "hot" | "long" | "short";


export function Scanner() {
  const {
    setTicker,
    source: globalSource,
    setSource,
    timeframe,
    addToWatchlist,
    watchlist,
    riskProfile,
  } = useAppStore();

  const [scanSource, setScanSource] = useState<Source>(globalSource);
  const [scanMode, setScanMode] = useState<ScanMode>("all");
  const [scanMarket, setScanMarket] = useState<MarketKind>("futures");
  const [filter, setFilter] = useState<FilterType>("all");
  const [data, setData] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [scannedTf, setScannedTf] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheHit, setCacheHit] = useState(false);

  const [recordingTicker, setRecordingTicker] = useState<string | null>(null);
  const [recordedTickers, setRecordedTickers] = useState<Set<string>>(new Set());

  const applyCacheIfFresh = (
    src: Source,
    tf: string,
    mode: ScanMode,
    mt: MarketKind
  ) => {
    const key = getCacheKey(src, tf, mode, mt);
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
    if (!applyCacheIfFresh(src, timeframe, scanMode, scanMarket)) {
      setData(null);
    }
  };

  const handleModeChange = (mode: ScanMode) => {
    setScanMode(mode);
    setError(null);
    setCacheHit(false);
    if (!applyCacheIfFresh(scanSource, timeframe, mode, scanMarket)) {
      setData(null);
    }
  };

  const handleMarketChange = (mt: MarketKind) => {
    setScanMarket(mt);
    setError(null);
    setCacheHit(false);
    if (!applyCacheIfFresh(scanSource, timeframe, scanMode, mt)) {
      setData(null);
    }
  };

  const handleScan = () => {
    const cacheKey = getCacheKey(scanSource, timeframe, scanMode, scanMarket);
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

    api
      .post("/scan", {
        source: scanSource,
        category,
        timeframe,
        market_type: scanMarket,
        risk_profile: riskProfile,
        limit: 50,
        scan_mode: scanMode,
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
          setError("تعداد درخواست‌ها بیش از حد مجاز — یک دقیقه دیگر تلاش کن");
        } else {
          setError("اسکن ناموفق بود — دوباره تلاش کن");
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
        market_type: scanMarket,
        risk_profile: riskProfile,
        ticker_name: item.name,
      });
      setRecordedTickers((prev) => {
        const next = new Set(prev);
        next.add(item.ticker);
        return next;
      });
    } catch {
      // silent
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
      if (isTsetmc) {
        if (/^[A-Z]/.test(item.ticker)) return false;
      } else {
        if (!/^[A-Z]/.test(item.ticker)) return false;
      }

      if (!isTsetmc) {
        if (!item.price || item.price < MIN_PRICE) return false;
      }

      if (filter === "all") return true;
      if (filter === "pre_breakout") return item.is_pre_breakout === true;
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
    pre_breakout:
      data?.items.filter(
        (i) => (isTsetmc || i.price >= MIN_PRICE) && i.is_pre_breakout === true
      ).length ?? 0,
    hot:
      data?.items.filter(
        (i) => (isTsetmc || i.price >= MIN_PRICE) && i.confidence >= 70
      ).length ?? 0,
    long:
      data?.items.filter(
        (i) => (isTsetmc || i.price >= MIN_PRICE) && i.direction === "long"
      ).length ?? 0,
    short:
      data?.items.filter(
        (i) => (isTsetmc || i.price >= MIN_PRICE) && i.direction === "short"
      ).length ?? 0,
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
            <p className="mt-1 text-[10px] text-muted-foreground">
              {data
                ? `${filtered.length} نتیجه روی ${scanSourceLabel} · ${scannedTf}`
                : "صرافی و حالت رو انتخاب کن، بعد بررسی بزن"}
              {cacheHit && (
                <span className="mr-2 text-green-500">· از cache</span>
              )}
            </p>
          </div>
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

        {collapsed ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCollapsed(false)}
            className="mt-2 w-full"
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
                return (
                  <Button
                    key={s.key}
                    size="sm"
                    variant={scanSource === s.key ? "default" : "outline"}
                    onClick={() => handleSourceChange(s.key)}
                    className="relative h-auto flex-col gap-0.5 px-1 py-2 text-[10px]"
                  >
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

            {/* ═══ Scan Mode ═══ */}
            <div>
              <p className="mb-1 text-[9px] font-medium text-muted-foreground">
                حالت اسکن
              </p>
              <div className="grid grid-cols-3 gap-1">
                {(["pre_breakout", "active", "all"] as ScanMode[]).map((m) => {
                  const isActive = scanMode === m;
                  const meta = MODE_LABELS[m];
                  const colorMap: Record<string, string> = {
                    purple: isActive
                      ? "border-purple-500 bg-purple-500/10 text-purple-400"
                      : "",
                    blue: isActive
                      ? "border-blue-500 bg-blue-500/10 text-blue-400"
                      : "",
                    slate: isActive
                      ? "border-slate-500 bg-slate-500/10 text-slate-300"
                      : "",
                  };
                  return (
                    <button
                      key={m}
                      onClick={() => handleModeChange(m)}
                      className={`rounded-md border-2 py-1 text-[10px] font-medium transition-all ${
                        isActive
                          ? colorMap[meta.color]
                          : "border-border text-muted-foreground hover:bg-muted/50"
                      }`}
                    >
                      {meta.icon} {meta.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ═══ Market Type ═══ */}
            <div>
              <p className="mb-1 text-[9px] font-medium text-muted-foreground">
                نوع بازار
              </p>
              <div className="grid grid-cols-2 gap-1">
                {(["spot", "futures"] as MarketKind[]).map((mt) => {
                  const isActive = scanMarket === mt;
                  const meta = MARKET_LABELS[mt];
                  return (
                    <button
                      key={mt}
                      onClick={() => handleMarketChange(mt)}
                      className={`rounded-md border-2 py-1 text-[10px] font-medium transition-all ${
                        isActive
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border text-muted-foreground hover:bg-muted/50"
                      }`}
                    >
                      {meta.icon} {meta.label}
                    </button>
                  );
                })}
              </div>
            </div>

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
                  بررسی روی {scanSourceLabel}
                </>
              )}
            </Button>

            {/* ═══ فیلترهای نمایش نتیجه ═══ */}
            {data && (
              <div className="grid grid-cols-5 gap-1">
                <button
                  onClick={() => setFilter("all")}
                  className={`rounded-md border-2 py-1 text-[9px] font-medium transition-all ${
                    filter === "all"
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  همه ({counts.all})
                </button>
                <button
                  onClick={() => setFilter("pre_breakout")}
                  className={`rounded-md border-2 py-1 text-[9px] font-medium transition-all ${
                    filter === "pre_breakout"
                      ? "border-purple-500 bg-purple-500/10 text-purple-400"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  🚀 ({counts.pre_breakout})
                </button>
                <button
                  onClick={() => setFilter("hot")}
                  className={`rounded-md border-2 py-1 text-[9px] font-medium transition-all ${
                    filter === "hot"
                      ? "border-orange-500 bg-orange-500/10 text-orange-400"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  🔥 ({counts.hot})
                </button>
                <button
                  onClick={() => setFilter("long")}
                  className={`rounded-md border-2 py-1 text-[9px] font-medium transition-all ${
                    filter === "long"
                      ? "border-green-500 bg-green-500/10 text-green-500"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  📈 ({counts.long})
                </button>
                <button
                  onClick={() => setFilter("short")}
                  className={`rounded-md border-2 py-1 text-[9px] font-medium transition-all ${
                    filter === "short"
                      ? "border-red-500 bg-red-500/10 text-red-500"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  📉 ({counts.short})
                </button>
              </div>
            )}
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
              حالت و صرافی رو انتخاب کن، بعد «بررسی» بزن
            </div>
          )}

          {(data || loading) && (
            <div className="overflow-x-hidden">
              <Table className="w-full table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[42%] text-right text-[10px]">
                      نماد
                    </TableHead>
                    <TableHead className="w-[38%] text-center text-[10px]">
                      سیگنال
                    </TableHead>
                    <TableHead className="w-[20%] text-center text-[10px]">
                      اطمینان
                    </TableHead>
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
                          <Skeleton className="mx-auto h-5 w-20" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="mx-auto h-5 w-12" />
                        </TableCell>
                      </TableRow>
                    ))}

                  {!loading && filtered.length === 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={3}
                        className="text-center text-xs text-muted-foreground"
                      >
                        {data && data.items.length > 0
                          ? "هیچ نمادی با فیلترهای فعلی پیدا نشد"
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

                      const isLong = item.direction === "long";
                      const isShort = item.direction === "short";
                      const sigBadgeCls = isLong
                        ? "bg-green-500/15 text-green-500 border-green-500/30"
                        : isShort
                          ? "bg-red-500/15 text-red-500 border-red-500/30"
                          : "bg-muted/40 text-muted-foreground border-border";

                      return (
                        <TableRow key={item.ticker}>
                          {/* ═══ نماد (راست‌چین) ═══ */}
                          <TableCell className="text-right">
                            <div className="flex items-center gap-1.5">
                              <CryptoIcon ticker={item.ticker} size="sm" />
                              <div className="min-w-0 text-right">
                                <p className="truncate text-xs font-bold">
                                  {item.name}
                                </p>
                                <p className="num truncate text-[9px] text-muted-foreground">
                                  {item.ticker}
                                </p>
                              </div>
                            </div>
                          </TableCell>

                          {/* ═══ سیگنال (وسط‌چین) ═══ */}
                          <TableCell className="text-center">
                            <div className="flex flex-col items-center gap-0.5">
                              <span
                                className={`inline-block rounded border px-1.5 py-0 text-[9px] font-bold sm:text-[10px] ${sigBadgeCls}`}
                                style={
                                  item.signal.includes("ضعیف")
                                    ? { opacity: 0.7 }
                                    : undefined
                                }
                              >
                                {isLong
                                  ? "LONG"
                                  : isShort
                                    ? "SHORT"
                                    : "—"}
                                {item.signal.includes("ضعیف") && (
                                  <span className="mr-0.5 text-[7px] opacity-70">
                                    ضعیف
                                  </span>
                                )}
                              </span>

                              {/* 🔴 badge آماده انفجار */}
                              {item.is_pre_breakout && (
                                <span
                                  className="inline-flex items-center gap-0.5 rounded border px-1 py-0 text-[7px] font-bold"
                                  style={{
                                    background: "rgba(168,85,247,0.15)",
                                    borderColor: "rgba(168,85,247,0.4)",
                                    color: "#c084fc",
                                    textShadow: "0 0 4px rgba(168,85,247,0.6)",
                                  }}
                                  title={`امتیاز پیش‌رشد: ${item.pre_breakout_score.toFixed(0)}٪ · جهت: ${item.pre_breakout_bias === "up" ? "صعودی" : item.pre_breakout_bias === "down" ? "نزولی" : "مشخص"}`}
                                >
                                  <Rocket className="h-2 w-2" />
                                  انفجار
                                </span>
                              )}
                            </div>
                          </TableCell>

                          {/* ═══ اطمینان (وسط‌چین) ═══ */}
                          <TableCell className="text-center">
                            <Badge
                              variant="outline"
                              className={`num text-[9px] sm:text-[10px] ${
                                item.confidence >= 70
                                  ? "border-green-500/40 text-green-500"
                                  : item.confidence >= 50
                                    ? "border-yellow-500/40 text-yellow-500"
                                    : "border-red-500/40 text-red-500"
                              }`}
                            >
                              {item.confidence}%
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}