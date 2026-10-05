"use client";

/**
 * SymbolSelector — انتخاب نماد (نسخه ۲.۰)
 * ============================================================
 * 🔴 تغییر نسخه ۲.۰:
 *   بخش «واچ‌لیست چیپ‌ها» حذف شد. دلیل:
 *   ``WatchlistCard`` نسخه‌ی مرتب‌تر و جمع‌وجورتر داره.
 *   نگه‌داشتن هر دو یعنی UI تکراری.
 *
 * ═══ ساختار ═══
 *   ۱. جستجو (با dropdown نتایج)
 *   ۲. ۶ نماد برتر (popular) — grid چیپ‌ها
 */

import { useEffect, useRef, useState } from "react";
import { Search, TrendingUp, Loader2, Star } from "lucide-react";
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

function normalize(text: string): string {
  return text
    .trim()
    .replace(/\u200c/g, "")
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
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSelect = (item: SymbolItem) => {
    const isIranianStock = !item.ticker[0]?.match(/[A-Za-z]/);
    const finalSource = isIranianStock ? "tsetmc" : source;

    selectSymbol(item.ticker, item.name, finalSource as never);
    setQuery("");
    setResults([]);
    setShowDropdown(false);
  };

  useEffect(() => {
    if (source === "tsetmc" && /^[A-Z]/.test(ticker)) {
      setTicker("فولاد", "فولاد مبارکه");
    }
    if (
      ["nobitex", "bitpin", "wallex", "tabdeal"].includes(source) &&
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

    selectSymbol(tk, tk, finalSource as never);
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
              const inWatchlist = watchlist.some(
                (w) => w.ticker === item.ticker
              );
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
                    <p className="text-[10px] text-muted-foreground">
                      {item.ticker}
                    </p>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (inWatchlist) removeFromWatchlist(item.ticker);
                      else addToWatchlist(item.ticker, item.name, item.source);
                    }}
                    className={`rounded p-1 ${
                      inWatchlist
                        ? "text-yellow-500"
                        : "text-muted-foreground hover:text-yellow-500"
                    }`}
                    aria-label={
                      inWatchlist ? "حذف از واچ‌لیست" : "افزودن به واچ‌لیست"
                    }
                  >
                    <Star
                      className={`h-3.5 w-3.5 ${
                        inWatchlist ? "fill-current" : ""
                      }`}
                    />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ═══ Popular — ۶ نماد برتر ═══ */}
      <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-6">
        {popular.slice(0, 6).map((item) => (
          <button
            key={item.ticker}
            onClick={() => handleSelect(item)}
            className={`flex min-w-0 items-center justify-center gap-1 truncate rounded-lg border px-1.5 py-1.5 text-[10px] font-medium transition-all hover:bg-muted ${
              ticker === item.ticker
                ? "border-primary bg-primary/10 text-primary"
                : "border-border"
            }`}
          >
            <span className="truncate">{item.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}