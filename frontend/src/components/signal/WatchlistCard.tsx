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
    <div className="rounded-lg border border-white/5 bg-[#051118] shadow-sm">
      {/* ═══ هدر نازک ═══ */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-right transition-colors hover:bg-white/5"
        aria-expanded={open}
      >
        <span className="flex items-center gap-1.5 text-[10px] font-medium text-gray-200">
          <Star className="h-3 w-3 text-yellow-500" />
          واچ‌لیست
          <span className="num rounded-full bg-yellow-500/15 px-1.5 text-[8px] text-yellow-500">
            {watchlist.length}
          </span>
        </span>
        <span
          className={`flex h-4 w-4 items-center justify-center rounded border transition-all ${
            open
              ? "rotate-180 border-[#d6ad60]/60 bg-[#d6ad60]/20 text-[#d6ad60]"
              : "border-[#d6ad60]/30 bg-[#d6ad60]/10 text-[#d6ad60]"
          }`}
        >
          <ChevronDown className="h-2.5 w-2.5" strokeWidth={2.5} />
        </span>
      </button>

      {/* ═══ محتوا ═══ */}
      {open && (
        <div className="border-t border-white/5 p-1.5">
          <div className="flex flex-wrap gap-1">
            {watchlist.map((w) => {
              const isCurrent = w.ticker === currentTicker;
              return (
                <div
                  key={w.ticker}
                  className={`flex items-center gap-0.5 rounded border px-1.5 py-0.5 text-[10px] leading-tight transition-colors ${
                    isCurrent
                      ? "border-[#d6ad60]/40 bg-[#d6ad60]/10 text-[#d6ad60]"
                      : "border-white/5 bg-white/5 text-gray-300 hover:bg-white/10"
                  }`}
                  title={`${w.name} — ${w.ticker}`}
                >
                  <button
                    onClick={() => setTicker(w.ticker, w.name)}
                    className="flex items-center gap-1"
                  >
                    <CryptoIcon ticker={w.ticker} size="sm" />
                    <span className="font-medium">{w.name}</span>
                  </button>
                  <button
                    onClick={() => removeFromWatchlist(w.ticker)}
                    className="ml-0.5 flex h-3 w-3 items-center justify-center rounded-sm text-gray-500 transition-colors hover:bg-red-500/20 hover:text-red-400"
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