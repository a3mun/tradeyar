"use client";

import { useState, useEffect } from "react";
import {
  Target, Search, Info, AlertTriangle, Star, Lock
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

const SOURCES: { key: Source; label: string; disabled?: boolean }[] = [
  { key: "nobitex", label: "نوبیتکس" },
  { key: "bitpin", label: "بیت‌پین" },
  { key: "wallex", label: "والکس" },
  { key: "tabdeal", label: "تبدیل", disabled: true }, // 🔴 غیرفعال
  { key: "tsetmc", label: "بورس" },
];

const CATEGORIES_BY_SOURCE: Record<string, string> = {
  nobitex: "crypto", bitpin: "crypto", wallex: "crypto", tabdeal: "crypto", tsetmc: "iran_stocks",
};

const CACHE_TTL_MS = 60_000;
interface CachedScan { data: ScanResponse; scannedTf: string; cachedAt: number; }
const scanCache = new Map<string, CachedScan>();

function getCacheKey(source: Source, timeframe: string, mode: string, mt: string): string {
  return `${source}:${timeframe}:${mode}:${mt}`;
}

type ScanMode = "all" | "pre_breakout" | "dump" | "active";

const MODE_LABELS: Record<ScanMode, { icon: string; label: string; color: string }> = {
  all: { icon: "🔍", label: "همه", color: "slate" },
  pre_breakout: { icon: "🚀", label: "آماده پامپ", color: "purple" },
  dump: { icon: "📉", label: "آماده دامپ", color: "red" },
  active: { icon: "📊", label: "سیگنال فعال", color: "blue" },
};

const TIMEFRAMES_BY_SOURCE: Record<string, string[]> = {
  nobitex: ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"],
  bitpin: ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"],
  wallex: ["۱ ساعت", "روزانه"],
  tabdeal: [],
  tsetmc: ["روزانه"],
};

export function Scanner() {
  const {
    setTicker, source: globalSource, setSource, addToWatchlist,
    removeFromWatchlist, watchlist, riskProfile,
  } = useAppStore();

  const [scanSource, setScanSource] = useState<Source>(globalSource);
  const [scanTf, setScanTf] = useState<string>("۱۵ دقیقه");
  const [scanMode, setScanMode] = useState<ScanMode>("all");
  const [data, setData] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheHit, setCacheHit] = useState(false);
  const [remainingScans, setRemainingScans] = useState<number | null>(null);

  const availableTfs = TIMEFRAMES_BY_SOURCE[scanSource] || ["۱۵ دقیقه"];

  // 🔴 چک کردن محدودیت باقی‌مانده در mount
  useEffect(() => {
    // می‌تونیم از یه endpoint جدید استفاده کنیم، ولی فعلاً فقط نمایش میدیم
    setRemainingScans(10); // مقدار پیش‌فرض، بعد از اولین اسکن آپدیت میشه
  }, []);

  const handleSourceChange = (src: Source) => {
    if (src === "tabdeal") return; // غیرفعال
    setScanSource(src);
    setError(null);
    setCacheHit(false);
    if (!TIMEFRAMES_BY_SOURCE[src]?.includes(scanTf)) {
      setScanTf(TIMEFRAMES_BY_SOURCE[src]?.[0] || "۱۵ دقیقه");
    }
  };

  const handleScan = () => {
    const cacheKey = getCacheKey(scanSource, scanTf, scanMode, "futures");
    const cached = scanCache.get(cacheKey);
    if (cached && Date.now() - cached.cachedAt < CACHE_TTL_MS) {
      setData(cached.data);
      setError(null);
      setCacheHit(true);
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
      limit: 10, // 🔴 محدودیت ۱۰
      scan_mode: scanMode,
    })
      .then((res) => {
        setData(res.data);
        setError(null);
        scanCache.set(cacheKey, { data: res.data, scannedTf: scanTf, cachedAt: Date.now() });
        // کاهش شمارنده
        setRemainingScans((prev) => (prev !== null ? Math.max(0, prev - 1) : null));
      })
      .catch((err) => {
        setData(null);
        const status = err.response?.status;
        if (status === 429) {
          setError("محدودیت روزانه اسکن پر شده — فردا ساعت ۱۲ شب ریست میشه");
        } else {
          setError("اسکن ناموفق بود — شاید سرور شلوغه، یه دقیقه دیگه تلاش کن");
        }
      })
      .finally(() => setLoading(false));
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

  const filtered = data?.items || [];
  const scanSourceLabel = SOURCES.find((s) => s.key === scanSource)?.label ?? scanSource;

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
              {data ? `${filtered.length} نتیجه روی ${scanSourceLabel} · ${scanTf}` : "صرافی و حالت رو انتخاب کن، بعد بررسی بزن"}
              {cacheHit && <span className="mr-2 text-green-500">· از cache</span>}
            </p>
          </div>
        </div>

        <div className="space-y-3 pt-2">
          {/* صرافی‌ها */}
          <div>
            <p className="mb-1 text-[9px] font-medium text-muted-foreground">صرافی</p>
            <div className="grid grid-cols-5 gap-1.5">
              {SOURCES.map((s) => {
                const meta = SOURCE_BY_KEY[s.key];
                const isDisabled = s.disabled;
                return (
                  <Button key={s.key} size="sm" variant={scanSource === s.key ? "default" : "outline"}
                    onClick={() => handleSourceChange(s.key)} 
                    disabled={isDisabled}
                    className={`relative h-auto flex-col gap-0.5 px-1 py-2 text-[10px] ${isDisabled ? "opacity-40 cursor-not-allowed" : ""}`}
                    title={isDisabled ? "این صرافی تحلیل ندارد" : s.label}
                  >
                    {isDisabled && (
                      <div className="absolute -top-1 -right-1 bg-red-500 rounded-full p-0.5">
                        <Lock className="h-2 w-2 text-white" />
                      </div>
                    )}
                    <img src={meta?.logo} alt={s.label} className="h-4 w-4 object-contain"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                    <span>{s.label}</span>
                  </Button>
                );
              })}
            </div>
          </div>

          {/* حالت اسکن */}
          <div>
            <p className="mb-1 text-[9px] font-medium text-muted-foreground">حالت اسکن</p>
            <div className="grid grid-cols-4 gap-1">
              {(["all", "active", "pre_breakout", "dump"] as ScanMode[]).map((m) => {
                const isActive = scanMode === m;
                const meta = MODE_LABELS[m];
                const colorMap: Record<string, string> = {
                  purple: isActive ? "border-purple-500 bg-purple-500/10 text-purple-400" : "",
                  red: isActive ? "border-red-500 bg-red-500/10 text-red-400" : "",
                  blue: isActive ? "border-blue-500 bg-blue-500/10 text-blue-400" : "",
                  slate: isActive ? "border-slate-500 bg-slate-500/10 text-slate-300" : "",
                };
                return (
                  <button key={m} onClick={() => setScanMode(m)}
                    className={`rounded-md border-2 py-1 text-[9px] font-medium transition-all ${isActive ? colorMap[meta.color] : "border-border text-muted-foreground hover:bg-muted/50"}`}>
                    {meta.icon} {meta.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* تایم‌فریم */}
          <div>
            <p className="mb-1 text-[9px] font-medium text-muted-foreground">تایم‌فریم</p>
            <div className="flex flex-wrap gap-1">
              {availableTfs.map((tf) => (
                <button key={tf} onClick={() => setScanTf(tf)}
                  className={`rounded-md border-2 px-2 py-1 text-[9px] font-medium transition-all ${scanTf === tf ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:bg-muted/50"}`}>
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* دکمه اسکن + شمارنده */}
          <div className="space-y-1">
            <Button onClick={handleScan} disabled={loading} className="w-full" size="sm">
              {loading ? <><Search className="h-3.5 w-3.5 animate-spin" /> در حال بررسی...</> : <><Search className="h-3.5 w-3.5" /> بررسی روی {scanSourceLabel}</>}
            </Button>
            
            {remainingScans !== null && (
              <p className="text-[9px] text-center text-muted-foreground">
                🔢 درخواست‌های باقی‌مانده امروز: <span className="font-bold text-primary">{remainingScans}</span> از ۱۰
              </p>
            )}
          </div>
          
          <p className="text-[8px] text-muted-foreground text-center">
            ⚠️ نتایج به مدت ۱ دقیقه کش می‌شوند. ساعت ۱۲ شب محدودیت ریست می‌شود.
          </p>
        </div>
      </CardHeader>

      <CardContent className="px-2 sm:px-4">
        {error && !loading && (
          <div className="flex items-center justify-center gap-2 rounded-lg border border-orange-500/30 bg-orange-500/10 py-3 text-xs text-orange-400">
            <AlertTriangle className="h-4 w-4" /> {error}
          </div>
        )}

        {!data && !loading && !error && (
          <div className="flex items-center justify-center gap-2 py-6 text-xs text-muted-foreground">
            <Info className="h-4 w-4" /> حالت و صرافی رو انتخاب کن، بعد «بررسی» بزن
          </div>
        )}

        {(data || loading) && (
          <div className="overflow-x-auto">
            <Table className="w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[35%] text-right text-[10px]">نماد</TableHead>
                  <TableHead className="w-[25%] text-center text-[10px]">سیگنال</TableHead>
                  <TableHead className="w-[15%] text-center text-[10px]">اطمینان</TableHead>
                  <TableHead className="w-[25%] text-center text-[10px]">عملیات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="mx-auto h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="mx-auto h-5 w-12" /></TableCell>
                    <TableCell><Skeleton className="mx-auto h-5 w-32" /></TableCell>
                  </TableRow>
                ))}

                {!loading && filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-xs text-muted-foreground">
                      {data && data.items.length > 0 ? "هیچ نمادی با این فیلتر پیدا نشد" : "فرصتی با این فیلتر پیدا نشد"}
                    </TableCell>
                  </TableRow>
                )}

                {!loading && filtered.map((item) => {
                  const inWatchlist = watchlist.some((w) => w.ticker === item.ticker);
                  const isLong = item.direction === "long";
                  const isShort = item.direction === "short";
                  const sigBadgeCls = isLong ? "bg-green-500/15 text-green-500 border-green-500/30"
                    : isShort ? "bg-red-500/15 text-red-500 border-red-500/30"
                    : "bg-muted/40 text-muted-foreground border-border";

                  return (
                    <TableRow key={item.ticker}>
                      <TableCell className="text-right">
                        <button onClick={() => handleAnalyze(item)}
                          className="flex items-center gap-1.5 rounded-md p-1 text-right transition-colors hover:bg-primary/10 active:bg-primary/20">
                          <CryptoIcon ticker={item.ticker} size="sm" />
                          <div className="min-w-0 flex-1 text-right">
                            <div className="flex items-center justify-end gap-1">
                              {item.is_pre_breakout && (
                                <span className="inline-flex shrink-0 items-center gap-0.5 rounded px-1 py-0 text-[7px] font-bold"
                                  style={{ background: "rgba(168,85,247,0.2)", border: "1px solid rgba(168,85,247,0.5)", color: "#c084fc" }}
                                  title={`آماده پامپ · امتیاز: ${item.pre_breakout_score?.toFixed(0) || 0}٪`}>
                                  🚀 پامپ
                                </span>
                              )}
                              {item.is_pre_breakout_down && (
                                <span className="inline-flex shrink-0 items-center gap-0.5 rounded px-1 py-0 text-[7px] font-bold"
                                  style={{ background: "rgba(239,68,68,0.2)", border: "1px solid rgba(239,68,68,0.5)", color: "#f87171" }}
                                  title={`آماده دامپ · امتیاز: ${item.pre_breakout_score?.toFixed(0) || 0}٪`}>
                                  📉 دامپ
                                </span>
                              )}
                              <p className="truncate text-xs font-bold">{item.name}</p>
                            </div>
                            <p className="num truncate text-[9px] text-muted-foreground">{item.ticker}</p>
                          </div>
                        </button>
                      </TableCell>

                      <TableCell className="text-center">
                        <span className={`inline-block rounded border px-1.5 py-0 text-[9px] font-bold sm:text-[10px] ${sigBadgeCls}`}
                          style={item.signal.includes("ضعیف") ? { opacity: 0.7 } : undefined}>
                          {isLong ? "LONG" : isShort ? "SHORT" : "—"}
                        </span>
                      </TableCell>

                      <TableCell className="text-center">
                        <Badge variant="outline" className={`num text-[9px] sm:text-[10px] ${item.confidence >= 70 ? "border-green-500/40 text-green-500" : item.confidence >= 50 ? "border-yellow-500/40 text-yellow-500" : "border-red-500/40 text-red-500"}`}>
                          {item.confidence}%
                        </Badge>
                      </TableCell>

                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <Button size="sm" variant="outline" onClick={() => handleAnalyze(item)}
                            className="hidden h-7 gap-1 border-blue-500/40 bg-blue-500/10 px-2 text-[10px] text-blue-400 hover:border-blue-500 hover:bg-blue-500/20 md:inline-flex"
                            title="تحلیل عمیق">
                            <Search className="h-3 w-3" /> <span>تحلیل</span>
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handleWatchlist(item)}
                            className={`h-7 w-7 border-yellow-500/40 bg-yellow-500/10 p-0 text-yellow-500 hover:border-yellow-500 hover:bg-yellow-500/20 ${inWatchlist ? "border-yellow-500 bg-yellow-500/20" : ""}`}
                            title={inWatchlist ? "حذف از واچ‌لیست" : "افزودن به واچ‌لیست"}>
                            <Star className={`h-3.5 w-3.5 ${inWatchlist ? "fill-yellow-500" : ""}`} />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}