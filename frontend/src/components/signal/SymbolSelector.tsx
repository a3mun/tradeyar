"use client";

import { useEffect, useRef, useState } from "react";
import { Search, TrendingUp, Loader2, Star, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import type { SymbolItem } from "@/lib/types";

const POPULAR_FALLBACK: SymbolItem[] = [
  { ticker: "BTC-USD", name: "₿ بیت‌کوین (USDT)", source: "nobitex" },
  { ticker: "BTC-IRT", name: "₿ بیت‌کوین (تومان)", source: "nobitex" },
  { ticker: "USDT-IRT", name: "💵 تتر/تومان", source: "nobitex" },
  { ticker: "ETH-USD", name: "Ξ اتریوم", source: "nobitex" },
  { ticker: "PAXG-USD", name: "🪙 پکس گلد", source: "nobitex" },
  { ticker: "PAXG-IRT", name: "🪙 پکس گلد (تومان)", source: "nobitex" },
];

// ═══ نرمال‌سازی متن (نیم‌فاصله، ی عربی، ک عربی) ═══
function normalize(text: string): string {
  return text
    .trim()
    .replace(/\u200c/g, "") // نیم‌فاصله
    .replace(/\s+/g, "")
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک")
    .toLowerCase();
}

export function SymbolSelector() {
  const {
    ticker,
    setTicker,
    source,
    watchlist,
    addToWatchlist,
    removeFromWatchlist,
    selectSymbol,
  } = useAppStore();
  const [popular, setPopular] = useState<SymbolItem[]>(POPULAR_FALLBACK);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SymbolItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .get("/symbols/popular")
      .then((res) => {
        if (res.data.items?.length > 0) setPopular(res.data.items);
      })
      .catch(() => {});
  }, []);

  // ═══ Live search ═══
  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setShowDropdown(false);
      return;
    }

    setSearching(true);
    const timer = setTimeout(() => {
      api
        .get("/symbols/search", { params: { q: query.trim(), limit: 12 } })
        .then((res) => {
          // ─── فیلتر سمت کلاینت (نیم‌فاصله) ───
          const q = normalize(query);
          const filtered = (res.data.items || []).filter(
            (item: SymbolItem) =>
              normalize(item.name).includes(q) ||
              normalize(item.ticker).includes(q)
          );
          setResults(filtered);
          setShowDropdown(true);
        })
        .catch(() => setResults([]))
        .finally(() => setSearching(false));
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSelect = (item: SymbolItem) => {
    // ═══ صرافی فعلی کاربر حفظ می‌شه (نه صرافی item) ═══
    // ─── استثنا: نماد بورسی → صرافی باید tsetmc بشه ───
    const isIranianStock = !item.ticker[0]?.match(/[A-Za-z]/);
    const finalSource = isIranianStock ? "tsetmc" : source;

    selectSymbol(item.ticker, item.name, finalSource as any);
    setQuery("");
    setResults([]);
    setShowDropdown(false);
  };
  
  // ═══ تغییر صرافی به TSETMC → نماد کریپتو رو پاک کن ═══
  useEffect(() => {
    // اگه source=tsetmc و ticker انگلیسی هست، برو سراغ فولاد
    if (source === "tsetmc" && /^[A-Z]/.test(ticker)) {
      setTicker("فولاد", "فولاد مبارکه");
    }
    // اگه source کریپتویی و ticker فارسی هست، برو سراغ BTC
    if (
      ["nobitex", "bitpin", "wallex", "abantether"].includes(source) &&
      !/^[A-Z]/.test(ticker)
    ) {
      setTicker("BTC-USD", "بیت‌کوین (USDT)");
    }
  }, [source, ticker, setTicker]);
  
  const handleManualSubmit = () => {
    if (!query.trim()) return;
    const tk = query.trim().toUpperCase();
    const isIranianStock = !tk[0]?.match(/[A-Za-z]/);
    const finalSource = isIranianStock ? "tsetmc" : source;

    selectSymbol(tk, tk, finalSource as any);
    setQuery("");
    setResults([]);
    setShowDropdown(false);
  };
  
  return (
    <div className="space-y-3">
      {/* ═══ Search ═══ */}
      <div className="relative" ref={dropdownRef}>
        <div className="flex gap-2">
          <div className="relative flex-1">
            {searching ? (
              <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
            ) : (
              <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            )}
            <Input
              placeholder="جستجو: BTC، فولاد، PAXG..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleManualSubmit()}
              onFocus={() => results.length > 0 && setShowDropdown(true)}
              className="pr-10"
            />
          </div>
          <Button onClick={handleManualSubmit} size="default">
            تحلیل
          </Button>
        </div>

        {showDropdown && results.length > 0 && (
          <div className="absolute top-full right-0 left-0 z-50 mt-1 max-h-80 overflow-y-auto rounded-lg border border-border bg-popover shadow-lg">
            {results.map((item) => {
              const inWatchlist = watchlist.some((w) => w.ticker === item.ticker);
              return (
                <div
                  key={item.ticker}
                  className="flex w-full items-center justify-between gap-2 border-b border-border/40 px-3 py-2 text-xs transition-colors last:border-b-0 hover:bg-muted/50"
                >
                  <button
                    onClick={() => handleSelect(item)}
                    className="flex-1 text-right"
                  >
                    <p className="font-medium">{item.name}</p>
                    <p className="text-[10px] text-muted-foreground">{item.ticker}</p>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      inWatchlist
                        ? removeFromWatchlist(item.ticker)
                        : addToWatchlist(item.ticker, item.name, item.source);
                    }}
                    className={`rounded p-1 ${
                      inWatchlist
                        ? "text-yellow-500"
                        : "text-muted-foreground hover:text-yellow-500"
                    }`}
                  >
                    <Star className={`h-3.5 w-3.5 ${inWatchlist ? "fill-current" : ""}`} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ═══ Popular ═══ */}
      <div className="flex flex-wrap gap-2">
        {popular.map((item) => (
          <button
            key={item.ticker}
            onClick={() => handleSelect(item)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all hover:bg-muted ${
              ticker === item.ticker
                ? "border-primary bg-primary/10 text-primary"
                : "border-border"
            }`}
          >
            <TrendingUp className="h-3 w-3" />
            <span>{item.name}</span>
          </button>
        ))}
      </div>

      {/* ═══ Watchlist ═══ */}
      {watchlist.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <Star className="h-3 w-3" />
            واچ‌لیست ({watchlist.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {watchlist.map((item) => (
              <div
                key={item.ticker}
                className={`group flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs transition-all hover:bg-muted ${
                  ticker === item.ticker
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border"
                }`}
              >
                <button
                  onClick={() => handleSelect({
                    ticker: item.ticker,
                    name: item.name,
                    source: item.source,
                  })}
                  className="font-medium"
                >
                  {item.name}
                </button>
                <button
                  onClick={() => removeFromWatchlist(item.ticker)}
                  className="opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <X className="h-3 w-3 text-destructive" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}