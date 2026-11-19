"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Target, Search, Info, AlertTriangle, Star, Lock, Loader2,
  Clock, Trash2, TrendingUp, ListFilter, BarChart3
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { SOURCE_BY_KEY } from "@/lib/sources";
import type { ScanResponse, ScanItem, Source } from "@/lib/types";
import { CryptoIcon } from "@/components/ui/crypto-icon";

// ═══════════════════════════════════════════════════════════
// ثابت‌ها
// ═══════════════════════════════════════════════════════════
const SOURCES: { key: Source; label: string; disabled?: boolean }[] = [
  { key: "nobitex", label: "نوبیتکس" },
  { key: "bitpin", label: "بیت‌پین" },
  { key: "wallex", label: "والکس" },
  { key: "tabdeal", label: "تبدیل", disabled: true },
  { key: "tsetmc", label: "بورس" },
];

const CATEGORIES_BY_SOURCE: Record<string, string> = {
  nobitex: "crypto", bitpin: "crypto", wallex: "crypto", tabdeal: "crypto", tsetmc: "iran_stocks",
};

const CACHE_TTL_MS = 300_000; // ۵ دقیقه
const DAILY_LIMIT = 20;

interface CachedScan {
  data: ScanResponse;
  scannedTf: string;
  cachedAt: number;
}
const scanCache = new Map<string, CachedScan>();

function getCacheKey(source: Source, timeframe: string, mode: string, mt: string): string {
  return `${source}:${timeframe}:${mode}:${mt}`;
}

type ScanMode = "all" | "pre_breakout" | "dump" | "active";

const MODE_LABELS: Record<ScanMode, { icon: string; label: string; activeClass: string }> = {
  all: { icon: "🔍", label: "همه", activeClass: "border-slate-500 bg-slate-500/10 text-slate-200" },
  active: { icon: "⚡", label: "سیگنال فعال", activeClass: "border-blue-500 bg-blue-500/10 text-blue-400" },
  pre_breakout: { icon: "🚀", label: "آماده پامپ", activeClass: "border-purple-500 bg-purple-500/10 text-purple-400" },
  dump: { icon: "📉", label: "آماده دامپ", activeClass: "border-red-500 bg-red-500/10 text-red-400" },
};

const TIMEFRAMES_BY_SOURCE: Record<string, string[]> = {
  nobitex: ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"],
  bitpin: ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"],
  wallex: ["۱ ساعت", "روزانه"],
  tabdeal: [],
  tsetmc: ["روزانه"],
};

// ═══════════════════════════════════════════════════════════
// کامپوننت اصلی
// ═══════════════════════════════════════════════════════════
export function Scanner() {
  const {
    setTicker, source: globalSource, setSource, addToWatchlist,
    removeFromWatchlist, watchlist, riskProfile,
  } = useAppStore();

  const [scanSource, setScanSource] = useState<Source>("nobitex");
  const [scanTf, setScanTf] = useState<string>("۱۵ دقیقه");
  const [scanMode, setScanMode] = useState<ScanMode>("all");
  const [data, setData] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheHit, setCacheHit] = useState(false);
  const [lastScanTime, setLastScanTime] = useState<string | null>(null);
  const [remainingScans, setRemainingScans] = useState<number>(DAILY_LIMIT);
  
  // برای اجبار به رفرش UI بعد از پاک کردن کش
  const [cacheVersion, setCacheVersion] = useState(0);

  // همگام‌سازی با globalSource
  useEffect(() => {
    const validSources = SOURCES.filter(s => !s.disabled).map(s => s.key);
    if (!validSources.includes(globalSource as Source)) {
      setScanSource("nobitex");
    } else {
      setScanSource(globalSource as Source);
    }
  }, [globalSource]);

  const availableTfs = TIMEFRAMES_BY_SOURCE[scanSource] || ["۱۵ دقیقه"];

  // 🔴 بررسی کش با تغییر تنظیمات
  useEffect(() => {
    const cacheKey = getCacheKey(scanSource, scanTf, scanMode, "futures");
    const cached = scanCache.get(cacheKey);
    
    if (cached && Date.now() - cached.cachedAt < CACHE_TTL_MS) {
      setData(cached.data);
      setError(null);
      setCacheHit(true);
      setLastScanTime(new Date(cached.cachedAt).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" }));
    } else {
      // 🔴 اگر کش برای این ترکیب نبود، لیست رو خالی کن تا کاربر خودش اسکن کنه
      setData(null);
      setCacheHit(false);
      setLastScanTime(null);
    }
  }, [scanSource, scanTf, scanMode, cacheVersion]); // cacheVersion برای رفرش بعد از پاک کردن کش

  // 🔴 اسکن
  const handleScan = useCallback(() => {
    const cacheKey = getCacheKey(scanSource, scanTf, scanMode, "futures");
    const cached = scanCache.get(cacheKey);

    // اگر کش معتبر است، آن را نمایش بده و سهمیه را کم نکن
    if (cached && Date.now() - cached.cachedAt < CACHE_TTL_MS) {
      setData(cached.data);
      setError(null);
      setCacheHit(true);
      setLastScanTime(new Date(cached.cachedAt).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" }));
      return;
    }

    // محدودیت روزانه
    if (remainingScans <= 0) {
      setError("محدودیت اسکن روزانه پر شده — فردا ساعت ۱۲ شب ریست میشه");
      return;
    }

    setLoading(true);
    setError(null);
    setCacheHit(false);
    const category = CATEGORIES_BY_SOURCE[scanSource] || "crypto";

    api.post("/scan", {
      source: scanSource,
      category,
      timeframe: scanTf,
      market_type: "futures",
      risk_profile: riskProfile,
      limit: 10,
      scan_mode: scanMode,
    })
      .then((res) => {
        const now = Date.now();
        setData(res.data);
        setError(null);
        scanCache.set(cacheKey, { data: res.data, scannedTf: scanTf, cachedAt: now });
        setRemainingScans((prev) => Math.max(0, prev - 1));
        setCacheHit(false); // نتیجه جدید است، نه کش
        setLastScanTime(new Date(now).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" }));
      })
      .catch((err) => {
        setData(null);
        const status = err.response?.status;
        if (status === 429) {
          setError("محدودیت اسکن روزانه پر شده — فردا ساعت ۱۲ شب ریست میشه");
          setRemainingScans(0);
        } else {
          setError("اسکن ناموفق بود — لطفاً دوباره تلاش کنید");
        }
      })
      .finally(() => setLoading(false));
  }, [scanSource, scanTf, scanMode, riskProfile, remainingScans]);

  // 🔴 پاک کردن کش
  const handleClearCache = () => {
    scanCache.clear();
    setData(null);
    setCacheHit(false);
    setLastScanTime(null);
    setCacheVersion(v => v + 1); // رفرش UI
  };

  const handleAnalyze = (item: ScanItem) => {
    setSource(scanSource as never);
    setTimeout(() => setTicker(item.ticker, item.name), 50);
  };

  const handleWatchlist = (item: ScanItem) => {
    const inWatchlist = watchlist.some((w) => w.ticker === item.ticker);
    if (inWatchlist) removeFromWatchlist(item.ticker);
    else addToWatchlist(item.ticker, item.name, scanSource);
  };

  // 🔴 چک کردن اینکه آیا برای یک صرافی/تایم‌فریم خاص کش داریم یا نه
  const hasCacheForTf = (tf: string) => {
    const key = getCacheKey(scanSource, tf, scanMode, "futures");
    const cached = scanCache.get(key);
    return !!(cached && Date.now() - cached.cachedAt < CACHE_TTL_MS);
  };

  const hasCacheForSource = (src: Source) => {
    const tfs = TIMEFRAMES_BY_SOURCE[src] || [];
    return tfs.some(tf => {
      const key = getCacheKey(src, tf, scanMode, "futures");
      const cached = scanCache.get(key);
      return !!(cached && Date.now() - cached.cachedAt < CACHE_TTL_MS);
    });
  };

  const filtered = data?.items || [];
  const scanSourceLabel = SOURCES.find((s) => s.key === scanSource)?.label ?? scanSource;

  return (
    <Card className="overflow-hidden border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] shadow-xl">

      <CardHeader className="pb-2">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base font-bold text-white">
              <Target className="h-5 w-5 text-[#d6ad60]" />
              اسکنر فرصت‌ها
            </CardTitle>
            <p className="mt-1 text-[11px] text-gray-400">
              {data
                ? `${filtered.length} فرصت روی ${scanSourceLabel} · ${scanTf}`
                : "تنظیمات را انتخاب کنید و دکمه بررسی را بزنید"}
            </p>
          </div>
          
          {/* دکمه‌ها و بج‌ها */}
          <div className="flex flex-wrap items-center gap-2">
            {cacheHit && (
              <Badge className="gap-1 bg-green-500/10 text-green-400 border-green-500/30 text-[10px] px-2 py-0.5">
                <Clock className="h-3 w-3" /> نتیجه اسکن قبلی
              </Badge>
            )}
            {(data || lastScanTime) && (
              <button
                onClick={handleClearCache}
                className="flex items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-2 py-1 text-[10px] font-medium text-red-400 transition-colors hover:bg-red-500/20"
                title="پاک کردن سابقه اسکن‌های کش شده"
              >
                <Trash2 className="h-3 w-3" />
                پاک کردن سابقه
              </button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 px-4 pb-4">
        {/* انتخاب صرافی */}
        <div className="space-y-1.5">
          <p className="text-[10px] font-medium text-gray-500">صرافی</p>
          <div className="grid grid-cols-5 gap-2">
            {SOURCES.map((s) => {
              const meta = SOURCE_BY_KEY[s.key];
              const isActive = scanSource === s.key;
              const hasCache = hasCacheForSource(s.key);
              
              return (
                <button
                  key={s.key}
                  onClick={() => {
                    if (s.disabled) return;
                    setScanSource(s.key);
                    if (!TIMEFRAMES_BY_SOURCE[s.key]?.includes(scanTf)) {
                      setScanTf(TIMEFRAMES_BY_SOURCE[s.key]?.[0] || "۱۵ دقیقه");
                    }
                  }}
                  disabled={s.disabled}
                  className={`relative flex flex-col items-center justify-center gap-1 rounded-xl border px-1 py-2 transition-all duration-200 ${
                    isActive
                      ? "border-[#d6ad60] bg-[#d6ad60]/10 shadow-[0_0_12px_rgba(214,173,96,0.2)]"
                      : "border-white/5 bg-white/5 hover:border-white/10 hover:bg-white/10"
                  } ${s.disabled ? "cursor-not-allowed opacity-40" : ""}`}
                >
                  {hasCache && (
                    <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.8)]" />
                  )}
                  {s.disabled && (
                    <div className="absolute -top-1 -right-1 rounded-full bg-red-500 p-0.5">
                      <Lock className="h-2 w-2 text-white" />
                    </div>
                  )}
                  <img
                    src={meta?.logo}
                    alt={s.label}
                    className="h-5 w-5 object-contain"
                    onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
                  />
                  <span className={`text-[9px] font-medium ${isActive ? "text-[#d6ad60]" : "text-gray-400"}`}>
                    {s.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* حالت اسکن */}
        <div className="space-y-1.5">
          <p className="text-[10px] font-medium text-gray-500">حالت اسکن</p>
          <div className="grid grid-cols-4 gap-1.5">
            {(["all", "active", "pre_breakout", "dump"] as ScanMode[]).map((m) => {
              const isActive = scanMode === m;
              const meta = MODE_LABELS[m];
              return (
                <button
                  key={m}
                  onClick={() => setScanMode(m)}
                  className={`flex items-center justify-center gap-1 rounded-lg border py-1.5 text-[9px] font-medium transition-all duration-200 ${
                    isActive ? meta.activeClass : "border-white/10 bg-white/5 text-gray-400 hover:bg-white/10"
                  }`}
                >
                  <span>{meta.icon}</span>
                  <span>{meta.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* تایم‌فریم */}
        <div className="space-y-1.5">
          <p className="text-[10px] font-medium text-gray-500">تایم‌فریم</p>
          <div className="flex flex-wrap gap-1.5">
            {availableTfs.map((tf) => {
              const isActive = scanTf === tf;
              const hasCache = hasCacheForTf(tf);
              
              return (
                <button
                  key={tf}
                  onClick={() => setScanTf(tf)}
                  className={`relative rounded-lg border px-2.5 py-1 text-[9px] font-medium transition-all duration-200 ${
                    isActive
                      ? "border-[#d6ad60] bg-[#d6ad60]/10 text-[#d6ad60]"
                      : "border-white/10 bg-white/5 text-gray-400 hover:bg-white/10"
                  }`}
                >
                  {hasCache && (
                    <span className="absolute -top-1 -right-1 h-1.5 w-1.5 rounded-full bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.8)]" />
                  )}
                  {tf}
                </button>
              );
            })}
          </div>
        </div>

        {/* دکمه اسکن + اطلاعات وضعیت */}
        <div className="space-y-2 pt-1">
          <Button
            onClick={handleScan}
            disabled={loading || remainingScans <= 0}
            className="w-full gap-2 rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] py-2 text-sm font-bold text-[#07111f] shadow-lg transition-transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
          >
            {loading ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> در حال بررسی...</>
            ) : remainingScans <= 0 ? (
              <><AlertTriangle className="h-4 w-4" /> محدودیت اسکن پر شده</>
            ) : (
              <><Search className="h-4 w-4" /> بررسی روی {scanSourceLabel}</>
            )}
          </Button>

          {/* نمایش وضعیت آخرین اسکن */}
          {lastScanTime && (
            <p className="flex items-center justify-center gap-1 text-[9px] text-gray-500">
              <Clock className="h-3 w-3" />
              نتیجه اسکن قبلی: {lastScanTime}
            </p>
          )}
        </div>

        {/* پیام خطا */}
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-orange-500/30 bg-orange-500/10 p-2 text-xs text-orange-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* جدول نتایج */}
        <div className="overflow-hidden rounded-xl border border-white/5">
          <Table className="w-full text-xs">
            <TableHeader className="bg-white/5">
              <TableRow className="border-white/5">
                <TableHead className="w-[30%] py-2 text-right text-[10px] font-medium text-gray-400">نماد</TableHead>
                <TableHead className="w-[20%] py-2 text-center text-[10px] font-medium text-gray-400">سیگنال</TableHead>
                <TableHead className="w-[15%] py-2 text-center text-[10px] font-medium text-gray-400">اطمینان</TableHead>
                <TableHead className="w-[35%] py-2 text-center text-[10px] font-medium text-gray-400">عملیات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading &&
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i} className="border-white/5">
                    <TableCell><Skeleton className="h-4 w-20 bg-white/10" /></TableCell>
                    <TableCell><Skeleton className="mx-auto h-4 w-12 bg-white/10" /></TableCell>
                    <TableCell><Skeleton className="mx-auto h-4 w-8 bg-white/10" /></TableCell>
                    <TableCell><Skeleton className="mx-auto h-4 w-16 bg-white/10" /></TableCell>
                  </TableRow>
                ))}

              {!loading && filtered.length === 0 && (
                <TableRow className="border-white/5">
                  <TableCell colSpan={4} className="py-8 text-center text-xs text-gray-500">
                    {data ? "هیچ فرصتی با این فیلتر پیدا نشد" : "دکمه «بررسی» را بزنید تا لیست پر شود"}
                  </TableCell>
                </TableRow>
              )}

              {!loading && filtered.map((item) => {
                const inWatchlist = watchlist.some((w) => w.ticker === item.ticker);
                const isLong = item.direction === "long";
                const isShort = item.direction === "short";
                const sigBadge = isLong
                  ? "bg-green-500/15 text-green-400 border-green-500/30"
                  : isShort
                  ? "bg-red-500/15 text-red-400 border-red-500/30"
                  : "bg-gray-500/15 text-gray-400 border-gray-500/30";

                return (
                  <TableRow key={item.ticker} className="border-white/5 transition-colors hover:bg-white/5">
                    <TableCell className="text-right">
                      <button
                        onClick={() => handleAnalyze(item)}
                        className="flex items-center gap-2 rounded-md p-1 text-right transition-colors hover:bg-white/5 active:bg-white/10"
                      >
                        <CryptoIcon ticker={item.ticker} size="sm" />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-end gap-1">
                            {item.is_pre_breakout && (
                              <span className="rounded px-1 text-[7px] font-bold bg-purple-500/20 text-purple-300" title="آماده پامپ">🚀</span>
                            )}
                            {item.is_pre_breakout_down && (
                              <span className="rounded px-1 text-[7px] font-bold bg-red-500/20 text-red-300" title="آماده دامپ">📉</span>
                            )}
                            <p className="truncate text-xs font-bold text-white">{item.name}</p>
                          </div>
                          <p className="num truncate text-[9px] text-gray-500">{item.ticker}</p>
                        </div>
                      </button>
                    </TableCell>
                    <TableCell className="text-center">
                      <span className={`inline-block rounded border px-1.5 py-0.5 text-[9px] font-bold ${sigBadge}`}>
                        {isLong ? "LONG" : isShort ? "SHORT" : "—"}
                      </span>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="outline" className={`num text-[9px] ${item.confidence >= 70 ? "border-green-500/40 text-green-400" : item.confidence >= 50 ? "border-yellow-500/40 text-yellow-400" : "border-red-500/40 text-red-400"}`}>
                        {item.confidence}%
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => handleAnalyze(item)}
                          className="flex items-center gap-1 rounded-md border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[9px] font-medium text-blue-400 transition-colors hover:bg-blue-500/20"
                          title="تحلیل این نماد"
                        >
                          <BarChart3 className="h-3 w-3" />
                          تحلیل
                        </button>
                        <button
                          onClick={() => handleWatchlist(item)}
                          className={`flex h-6 w-6 items-center justify-center rounded-md border border-transparent transition-colors hover:bg-white/10 ${inWatchlist ? "text-yellow-500" : "text-gray-500 hover:text-yellow-500"}`}
                          title={inWatchlist ? "حذف از واچ‌لیست" : "افزودن به واچ‌لیست"}
                        >
                          <Star className={`h-3.5 w-3.5 ${inWatchlist ? "fill-yellow-500" : ""}`} />
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}