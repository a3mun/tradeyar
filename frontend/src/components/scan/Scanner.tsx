"use client";

import { useState } from "react";
import { Target, Filter, Search, Info, X, Plus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import type { ScanResponse, ScanItem } from "@/lib/types";

import type { Source } from "@/lib/types";

const SOURCES: { key: Source; label: string; icon: string }[] = [
  { key: "nobitex", label: "نوبیتکس", icon: "🟣" },
  { key: "bitpin", label: "بیت‌پین", icon: "🟢" },
  { key: "wallex", label: "والکس", icon: "🔵" },
  { key: "abantether", label: "آبان‌تتر", icon: "🔷" },
  { key: "tsetmc", label: "بورس", icon: "🇮🇷" },
];

const CATEGORIES_BY_SOURCE: Record<string, string> = {
  nobitex: "crypto",
  bitpin: "crypto",
  wallex: "crypto",
  abantether: "crypto",
  tsetmc: "iran_stocks",
};

export function Scanner() {
  const { setTicker, source: globalSource, setSource, timeframe, addToWatchlist } =
    useAppStore();
const [scanSource, setScanSource] = useState<Source>(globalSource);
    const [filter, setFilter] = useState<"all" | "long" | "short">("all");
  const [data, setData] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [scannedTf, setScannedTf] = useState("");
  const [collapsed, setCollapsed] = useState(false);

  const handleScan = () => {
    setLoading(true);
    setScannedTf(timeframe);
    const category = CATEGORIES_BY_SOURCE[scanSource] || "crypto";
    const marketType = scanSource === "tsetmc" ? "spot" : "futures";

    api
      .post("/scan", {
        category,
        timeframe,
        market_type: marketType,
        risk_profile: "aggressive",
        limit: 15,
      })
  .then((res) => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  const filtered =
    data?.items.filter((item: ScanItem) => {
      // ─── فیلتر TSETMC: فقط نمادهای بورسی (فارسی) ───
      if (scanSource === "tsetmc") {
        if (/^[A-Z]/.test(item.ticker)) return false;
      }
      // ─── فیلتر صرافی‌های کریپتو: فقط نمادهای کریپتو ───
      else {
        if (!/^[A-Z]/.test(item.ticker)) return false;
      }
      // ─── فیلتر سیگنال ───
      if (filter === "all") return true;
      if (filter === "long") return item.direction === "long";
      if (filter === "short") return item.direction === "short";
      return true;
    }) || [];
  
  const filterLabel =
    filter === "all" ? "همه" : filter === "long" ? "فقط صعودی" : "فقط نزولی";

  const isTsetmc = scanSource === "tsetmc";

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
                ? `${data.total} فرصت روی ${SOURCES.find((s) => s.key === scanSource)?.label} · ${scannedTf}`
                : "صرافی رو انتخاب کن و روی «بررسی فرصت» بزن"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {data && (
              <>
                <Select
                  value={filter}
                  onValueChange={(v) => setFilter(v as "all" | "long" | "short")}
                >
                  <SelectTrigger className="h-8 w-24 text-xs">
                    <Filter className="h-3 w-3" />
                    <SelectValue>{filterLabel}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">همه</SelectItem>
                    <SelectItem value="long">صعودی</SelectItem>
                    <SelectItem value="short">نزولی</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setCollapsed(true)}
                  className="h-8 w-8"
                  title="جمع کردن"
                >
                  <X className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </div>

        {/* ═══ اگر جمع شده ═══ */}
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
              {SOURCES.map((s) => (
                <Button
                  key={s.key}
                  size="sm"
                  variant={scanSource === s.key ? "default" : "outline"}
                  onClick={() => {
                    setScanSource(s.key as Source);
                    setData(null);
                  }}
                  className="h-auto flex-col gap-0.5 px-1 py-2 text-[10px]"
                >
                  <span className="text-sm leading-none">{s.icon}</span>
                  <span>{s.label}</span>
                </Button>
              ))}
            </div>

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
                  بررسی فرصت‌ها روی {SOURCES.find((s) => s.key === scanSource)?.label}
                </>
              )}
            </Button>
          </div>
        )}
      </CardHeader>

      {!collapsed && (
        <CardContent>
          {!data && !loading && (
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
                      <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                    </TableRow>
                  ))}

                {!loading && filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-xs text-muted-foreground">
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
                        setSource(scanSource as any);
                        setTimeout(() => setTicker(item.ticker, item.name), 50);
                      }}
                    >
                      <TableCell className="text-right">
                        <p className="text-xs font-bold">{item.name}</p>
                        <p className="text-[10px] text-muted-foreground">{item.ticker}</p>
                      </TableCell>
                      <TableCell className={`text-right text-xs ${signalColor(item.signal)}`}>
                        {item.signal}
                      </TableCell>
                      <TableCell className="num text-right text-xs">
                        {isTsetmc && item.price === 0 ? "—" : formatNumber(item.price)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge
                          variant="outline"
                          className={`num text-[10px] ${confidenceColor(item.confidence)}`}
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
                            addToWatchlist(item.ticker, item.name, scanSource);
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