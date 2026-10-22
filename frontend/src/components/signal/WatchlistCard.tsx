"use client";

import { useState } from "react";
import { Star, X, ChevronDown } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { CryptoIcon } from "@/components/ui/crypto-icon";

export function WatchlistCard() {
  const {
    watchlist,
    removeFromWatchlist,
    setTicker,
    ticker: currentTicker,
  } = useAppStore();

  const [open, setOpen] = useState(false);

  if (watchlist.length === 0) return null;

  return (
    <div className="rounded-lg border border-border/60 bg-card">
      {/* ═══ هدر نازک ═══ */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-2 py-1 text-right transition-colors hover:bg-muted/30"
        aria-expanded={open}
      >
        <span className="flex items-center gap-1 text-[10px] font-medium">
          <Star className="h-3 w-3 text-yellow-500" />
          واچ‌لیست
          <span className="num rounded-full bg-yellow-500/15 px-1 text-[8px] text-yellow-500">
            {watchlist.length}
          </span>
        </span>
        <span
          className={`flex h-4 w-4 items-center justify-center rounded border-2 transition-all ${
            open
              ? "rotate-180 border-primary bg-primary/20 text-primary"
              : "border-primary/40 bg-primary/10 text-primary"
          }`}
        >
          <ChevronDown className="h-2.5 w-2.5" strokeWidth={2.5} />
        </span>
      </button>

      {/* ═══ محتوا ═══ */}
      {open && (
        <div className="border-t border-border/40 p-1.5">
          <div className="flex flex-wrap gap-0.5">
            {watchlist.map((w) => {
              const isCurrent = w.ticker === currentTicker;
              return (
                <div
                  key={w.ticker}
                  className={`flex items-center gap-0.5 rounded border px-1 py-0 text-[10px] leading-tight transition-colors ${
                    isCurrent
                      ? "border-primary/40 bg-primary/10"
                      : "border-border/60 bg-muted/10 hover:bg-muted/30"
                  }`}
                  title={`${w.name} — ${w.ticker}`}
                >
                  <button
                    onClick={() => setTicker(w.ticker, w.name)}
                    className="flex items-center gap-0.5"
                  >
                    <CryptoIcon ticker={w.ticker} size="sm" />
                    <span className="font-medium">{w.name}</span>
                  </button>
                  <button
                    onClick={() => removeFromWatchlist(w.ticker)}
                    className="ml-0.5 flex h-2.5 w-2.5 items-center justify-center rounded-sm text-muted-foreground/60 transition-colors hover:bg-red-500/20 hover:text-red-500"
                    aria-label={`حذف ${w.name}`}
                  >
                    <X className="h-2 w-2" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}