"use client";

import { useEffect, useRef, useState } from "react";
import { Search, Loader2, Star } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import type { SymbolItem, Source } from "@/lib/types";
import { CryptoIcon } from "@/components/ui/crypto-icon";

const POPULAR_CRYPTO: SymbolItem[] = [
  { ticker: "USDT-IRT", name: "تتر (تومان)", source: "nobitex" },
  { ticker: "BTC-USD", name: "بیت‌کوین", source: "nobitex" },
  { ticker: "BTC-IRT", name: "بیت‌کوین (تومان)", source: "nobitex" },
  { ticker: "XAUT-USD", name: "تتر گلد", source: "nobitex" },
  { ticker: "PAXG-USD", name: "پکس گلد", source: "nobitex" },
  { ticker: "SOL-USD", name: "سولانا", source: "nobitex" },
  { ticker: "XRP-USD", name: "ریپل", source: "nobitex" },
  { ticker: "DOGE-USD", name: "دوج‌کوین", source: "nobitex" },
  { ticker: "ETH-USD", name: "اتریوم", source: "nobitex" },
  { ticker: "BNB-USD", name: "بایننس", source: "nobitex" },
];

const POPULAR_FOREX: SymbolItem[] = [
  { ticker: "XAU-USD", name: "انس طلا", source: "forex", type: "کالا" },
  { ticker: "XAG-USD", name: "انس نقره", source: "forex", type: "کالا" },
  { ticker: "USOIL-USD", name: "نفت WTI", source: "forex", type: "کالا" },
  { ticker: "UKOIL-USD", name: "نفت برنت", source: "forex", type: "کالا" },
  { ticker: "DXY-USD", name: "شاخص دلار", source: "forex", type: "شاخص" },
  { ticker: "US500-USD", name: "S&P 500", source: "forex", type: "شاخص" },
  { ticker: "US30-USD", name: "داوجونز", source: "forex", type: "شاخص" },
  { ticker: "USTEC-USD", name: "نزدک ۱۰۰", source: "forex", type: "شاخص" },
  { ticker: "EUR-USD", name: "یورو/دلار", source: "forex", type: "فارکس" },
  { ticker: "BTC-USD", name: "بیت‌کوین (جهانی)", source: "forex", type: "کریپتو" },
];

const POPULAR_IRAN_STOCKS: SymbolItem[] = [
  { ticker: "فولاد", name: "فولاد", source: "tsetmc" },
  { ticker: "فارس", name: "پتروشیمی فارس", source: "tsetmc" },
  { ticker: "وتجارت", name: "بانک تجارت", source: "tsetmc" },
  { ticker: "خساپا", name: "سایپا", source: "tsetmc" },
  { ticker: "خودرو", name: "ایران خودرو", source: "tsetmc" },
  { ticker: "طلا", name: "صندوق طلا", source: "tsetmc" },
  { ticker: "نقرابی", name: "صندوق نقره", source: "tsetmc" },
  { ticker: "عیار", name: "صندوق عیار", source: "tsetmc" },
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

type TabType = "crypto" | "forex" | "iran_stocks";

const FOREX_SET = new Set([
  "XAU-USD", "XAG-USD", "USOIL-USD", "UKOIL-USD",
  "DXY-USD", "US500-USD", "US30-USD", "USTEC-USD",
  "EUR-USD", "DE30-USD",
]);
function isTickerForex(ticker: string): boolean {
  return FOREX_SET.has(ticker);
}

// 🔴 رنگ بج نوع (مشترک برای گرید و dropdown)
const TYPE_BADGE_CLASS: Record<string, string> = {
  "کالا":   "bg-yellow-500/20 text-yellow-400",
  "شاخص":   "bg-purple-500/20 text-purple-400",
  "فارکس":  "bg-cyan-500/20 text-cyan-400",
  "کریپتو": "bg-orange-500/20 text-orange-400",
};

export function SymbolSelector() {
  const {
    ticker,
    source,
    watchlist,
    addToWatchlist,
    removeFromWatchlist,
    forceSelectSymbol,
  } = useAppStore();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SymbolItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  const activeTab: TabType =
    source === "forex"
      ? "forex"
      : source === "tsetmc"
        ? "iran_stocks"
        : "crypto";

  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentList =
    activeTab === "crypto"
      ? POPULAR_CRYPTO
      : activeTab === "forex"
        ? POPULAR_FOREX
        : POPULAR_IRAN_STOCKS;

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
        .get("/symbols/search", { params: { q: query.trim(), limit: 15 } })
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

  // 🔴 انتخاب — همیشه source صریح ست می‌شه
  const handleSelect = (item: SymbolItem) => {
    const isIranianStock = !item.ticker[0]?.match(/[A-Za-z]/);
    
    // 🔴 فیکس خطای تایپ: type-cast به Source
    const finalSource = (isIranianStock ? "tsetmc" : item.source) as Source;

    // 🔴 برای نمادهای کریپتو، اگر صرافی فعلی از این نماد پشتیبانی می‌کند، آن را نگه دار
    if (item.source === "nobitex" || item.source === "bitpin" || item.source === "wallex" || item.source === "tabdeal") {
      const currentSource = useAppStore.getState().source;
      // اگر در تب کریپتو هستیم و صرافی فعلی هم کریپتوست، همان را نگه دار
      if (currentSource !== "forex" && currentSource !== "tsetmc") {
        forceSelectSymbol(item.ticker, item.name, currentSource);
        setQuery("");
        setResults([]);
        setShowDropdown(false);
        return;
      }
    }

    // برای فارکس و بورس، همیشه source آیتم را ست کن
    forceSelectSymbol(item.ticker, item.name, finalSource);
    setQuery("");
    setResults([]);
    setShowDropdown(false);
  };
  

  const handleTabChange = (tab: TabType) => {
    if (tab === "forex") {
      forceSelectSymbol("XAU-USD", "انس طلا", "forex");
    } else if (tab === "crypto") {
      forceSelectSymbol("BTC-USD", "بیت‌کوین", "nobitex");
    } else if (tab === "iran_stocks" && POPULAR_IRAN_STOCKS.length > 0) {
      const s = POPULAR_IRAN_STOCKS[0];
      forceSelectSymbol(s.ticker, s.name, "tsetmc");
    }
  };

  const handleManualSubmit = () => {
    if (!query.trim()) return;
    const tk = query.trim().toUpperCase();
    const isIranianStock = !tk[0]?.match(/[A-Za-z]/);
    const finalSource: Source = isIranianStock
      ? "tsetmc"
      : isTickerForex(tk)
        ? "forex"
        : (source as Source);

    forceSelectSymbol(tk, tk, finalSource);

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
              placeholder="جستجو: BTC، فولاد، XAU، EURUSD..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleManualSubmit()}
              onFocus={() => results.length > 0 && setShowDropdown(true)}
              className="h-8 pr-9 text-xs"
            />
          </div>
          <Button
            onClick={handleManualSubmit}
            size="sm"
            className="h-8 px-3 text-xs"
          >
            تحلیل
          </Button>
        </div>

        {showDropdown && results.length > 0 && (
          <div className="absolute top-full right-0 left-0 z-50 mt-1 max-h-80 overflow-y-auto rounded-lg border border-border bg-popover shadow-lg">
            {results.map((item) => {
              const inWatchlist = watchlist.some(
                (w) => w.ticker === item.ticker
              );
              const badgeClass =
                item.type && TYPE_BADGE_CLASS[item.type]
                  ? TYPE_BADGE_CLASS[item.type]
                  : "bg-muted/30 text-muted-foreground";

              return (
                <div
                  key={`${item.source}-${item.ticker}`}
                  className="flex w-full items-center justify-between gap-2 border-b border-border/40 px-3 py-2 text-xs transition-colors last:border-b-0 hover:bg-muted/50"
                >
                  <button
                    onClick={() => handleSelect(item)}
                    className="flex flex-1 items-center gap-2 text-right"
                  >
                    <CryptoIcon ticker={item.ticker} size="sm" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className="truncate font-medium">{item.name}</p>
                        {/* 🔴 بج نوع */}
                        {item.type && (
                          <span
                            className={`rounded px-1 py-0 text-[7px] font-bold ${badgeClass}`}
                          >
                            {item.type}
                          </span>
                        )}
                        {/* 🔴 بج source برای فارکس */}
                        {item.source === "forex" && (
                          <span className="rounded bg-cyan-500/10 px-1 py-0 text-[7px] font-bold text-cyan-400">
                            Biquote
                          </span>
                        )}
                      </div>
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

      {/* ═══ بخش نمادها ═══ */}
      <div className="rounded-xl border border-white/5 bg-[#0a101a]/50 backdrop-blur-md overflow-hidden shadow-sm">
        {/* سربرگ تب‌ها */}
        <div className="flex p-1 gap-1 border-b border-white/5 bg-white/5">
          {(
            [
              { key: "crypto", label: "ارز دیجیتال" },
              { key: "forex", label: "بازار جهانی" },
              { key: "iran_stocks", label: "بورس تهران" },
            ] as { key: TabType; label: string }[]
          ).map((tab) => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={`relative flex-1 rounded-lg py-1.5 text-[11px] transition-all duration-300 font-display ${
                activeTab === tab.key
                  ? "bg-gradient-to-b from-[#d6ad60] to-[#b88e45] text-[#101827] shadow-[0_2px_10px_rgba(214,173,96,0.3)] font-bold"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* گرید نمادها */}
        <div className="p-2">
          <div className="grid grid-cols-5 gap-1.5 sm:grid-cols-10">
            {currentList.map((item) => {
              const isActive = ticker === item.ticker;
              const badgeClass =
                item.type && TYPE_BADGE_CLASS[item.type]
                  ? TYPE_BADGE_CLASS[item.type]
                  : "bg-muted/30 text-muted-foreground";

              return (
                <button
                  key={item.ticker}
                  onClick={() => handleSelect(item)}
                  className={`group relative flex min-w-0 flex-col items-center justify-center gap-1 overflow-hidden rounded-xl border px-1 py-2 text-center transition-all duration-300
                    ${
                      isActive
                        ? "border-[#d6ad60]/50 bg-gradient-to-b from-[#d6ad60]/20 to-transparent text-[#d6ad60] shadow-[0_0_15px_rgba(214,173,96,0.15)] ring-1 ring-[#d6ad60]/30"
                        : "border-white/5 bg-white/5 text-foreground/70 hover:border-white/20 hover:bg-white/10 hover:text-foreground hover:shadow-lg"
                    }
                  `}
                >
                  <div className="absolute inset-0 -z-10 bg-gradient-to-tr from-transparent via-white/5 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

                  {isActive && (
                    <div className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-[#d6ad60] shadow-[0_0_8px_#d6ad60] animate-pulse" />
                  )}

                  {item.type && (
                    <span
                      className={`absolute top-0.5 left-0.5 rounded px-1 py-0 text-[7px] font-bold ${badgeClass}`}
                    >
                      {item.type}
                    </span>
                  )}

                  {activeTab !== "iran_stocks" && (
                    <CryptoIcon
                      ticker={item.ticker}
                      size="sm"
                      className={`transition-transform duration-300 ${
                        isActive ? "scale-110" : "group-hover:scale-110"
                      }`}
                    />
                  )}

                  <span
                    className={`w-full truncate text-[10px] leading-tight ${
                      isActive ? "font-bold" : "font-medium"
                    }`}
                  >
                    {item.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}