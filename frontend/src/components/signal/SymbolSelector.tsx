"use client";

import { useEffect, useRef, useState } from "react";
import { Search, Loader2, Star } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import type { SymbolItem } from "@/lib/types";
import { CryptoIcon } from "@/components/ui/crypto-icon";

const POPULAR_FALLBACK: SymbolItem[] = [
  { ticker: "USDT-IRT", name: "تتر (تومان)", source: "nobitex" },
  { ticker: "BTC-USD", name: "بیت‌کوین", source: "nobitex" },
  { ticker: "BTC-IRT", name: "بیت‌کوین (تومان)", source: "nobitex" },
  { ticker: "XAUT-USD", name: "تتر گلد", source: "nobitex" },
  { ticker: "XAUT-IRT", name: "تتر گلد (تومان)", source: "nobitex" },
  { ticker: "PAXG-USD", name: "پکس گلد", source: "nobitex" },
  { ticker: "SOL-USD", name: "سولانا", source: "nobitex" },
  { ticker: "XRP-USD", name: "ریپل", source: "nobitex" },
  { ticker: "DOGE-USD", name: "دوج‌کوین", source: "nobitex" },
  { ticker: "ETH-USD", name: "اتریوم", source: "nobitex" },
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
    <div className="space-y-2">
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
              className="h-8 pr-9 text-xs"
            />
          </div>
          <Button onClick={handleManualSubmit} size="sm" className="h-8 px-3 text-xs">
            تحلیل
          </Button>
        </div>

        {showDropdown && results.length > 0 && (
          <div className="absolute top-full right-0 left-0 z-50 mt-1 max-h-72 overflow-y-auto rounded-lg border border-border bg-popover shadow-lg">
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
                    className="flex flex-1 items-center gap-2 text-right"
                  >
                    <CryptoIcon ticker={item.ticker} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{item.name}</p>
                      <p className="num truncate text-[10px] text-muted-foreground">
                        {item.ticker}
                      </p>
                    </div>
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

      {/* ═══ Popular — ۱۰ نماد، شیشه‌ای ═══ */}
      <div className="grid grid-cols-5 gap-1.5 sm:grid-cols-10">
        {POPULAR_FALLBACK.map((item) => {
          const isActive = ticker === item.ticker;
          return (
            <button
              key={item.ticker}
              onClick={() => handleSelect(item)}
              className={`group relative flex min-w-0 flex-col items-center justify-center gap-1 overflow-hidden rounded-xl border px-1 py-2 text-center text-[11px] font-medium leading-tight transition-all duration-300
                ${
                  isActive
                    ? "border-primary/50 bg-primary/20 text-primary shadow-[0_0_15px_rgba(var(--primary),0.3)] backdrop-blur-md"
                    : "border-white/10 bg-white/5 text-foreground/80 backdrop-blur-sm hover:border-white/20 hover:bg-white/10 hover:text-foreground hover:shadow-lg"
                }
              `}
            >
              <div className="absolute inset-0 -z-10 bg-gradient-to-br from-white/10 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
              <CryptoIcon ticker={item.ticker} size="sm" className="transition-transform duration-300 group-hover:scale-110" />
              <span className="w-full truncate text-[10px]">{item.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}