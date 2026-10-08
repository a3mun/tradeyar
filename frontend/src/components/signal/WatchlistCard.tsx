"use client";

import { Star, X } from "lucide-react";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { useAppStore } from "@/store/useAppStore";
import { SOURCE_BY_KEY } from "@/lib/sources";
import { CryptoIcon } from "@/components/ui/crypto-icon";

export function WatchlistCard() {
  const {
    watchlist,
    removeFromWatchlist,
    setTicker,
    setSource,
    ticker: currentTicker,
  } = useAppStore();

  // ─── اگه خالیه، اصلاً نشون نده ───
  if (watchlist.length === 0) return null;

  return (
    <CollapsibleCard
      title={
        <span className="flex items-center gap-1.5">
          <Star className="h-3.5 w-3.5 text-yellow-500" />
          واچ‌لیست
        </span>
      }
      badge={
        <span className="num rounded-full bg-yellow-500/15 px-1.5 text-[9px] text-yellow-500">
          {watchlist.length}
        </span>
      }
      keepCollapsibleOnDesktop
    >
      {/* ─── چیپ‌های کوچیک ─── */}
      <div className="flex flex-wrap gap-1">
        {watchlist.map((w) => {
          const isCurrent = w.ticker === currentTicker;

          return (
            <div
              key={w.ticker}
              className={`group flex items-center gap-0.5 rounded-md border px-1.5 py-0.5 text-[10px] transition-colors ${
                isCurrent
                  ? "border-primary/40 bg-primary/10"
                  : "border-border bg-muted/20 hover:bg-muted/40"
              }`}
              title={`${w.name} — ${w.ticker}`}
            >
              <button
                onClick={() => {
                  setTicker(w.ticker, w.name);
                  setSource(w.source as never);
                }}
                className="flex items-center gap-1 whitespace-nowrap"
              >
                <CryptoIcon ticker={w.ticker} size="sm" />
                <span className="font-medium">{w.name}</span>
              </button>

              <button
                onClick={() => removeFromWatchlist(w.ticker)}
                className="ml-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-sm text-muted-foreground/60 transition-colors hover:bg-red-500/20 hover:text-red-500"
                aria-label={`حذف ${w.name}`}
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </div>
          );
        })}
      </div>
    </CollapsibleCard>
  );
}