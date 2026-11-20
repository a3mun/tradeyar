"use client";

import { TrendingUp, TrendingDown, Minus, ArrowUp, WifiOff } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { useScrollVisibility } from "@/lib/hooks/useScrollVisibility";
import { SOURCE_BY_KEY } from "@/lib/sources";
import { formatNumber } from "@/lib/display";
import { useEffect, useRef, useState } from "react";

export function StickyMiniHeader() {
  const { ticker, tickerName, source, timeframe, getTfData } = useAppStore();
  const { quote, status: wsStatus } = useWebSocket();
  const visible = useScrollVisibility(200);

  const signal = getTfData(timeframe);

  const [lastKnownPrice, setLastKnownPrice] = useState(0);
  const entryPrice = signal?.price ?? 0;
  
  useEffect(() => {
    if (quote?.price && quote.price > 0) {
      setLastKnownPrice(quote.price);
    }
  }, [quote]);

  const displayPrice = quote?.price || lastKnownPrice || entryPrice || 0;

  const [priceFlash, setPriceFlash] = useState<"up" | "down" | null>(null);
  const prevPriceRef = useRef<number | null>(null);
  
  useEffect(() => {
    if (!displayPrice || displayPrice <= 0) return;
    const prev = prevPriceRef.current;
    if (prev != null && prev !== displayPrice) {
      setPriceFlash(displayPrice > prev ? "up" : "down");
      const timer = setTimeout(() => setPriceFlash(null), 2000);
      return () => clearTimeout(timer);
    }
    prevPriceRef.current = displayPrice;
  }, [displayPrice]);

  const meta = SOURCE_BY_KEY[source];
  const sigText = signal?.signal ?? "";
  const sigConf = signal?.confidence ?? 0;
  const sigDir = signal?.direction ?? "neutral";

  const DirIcon = sigDir === "long" ? TrendingUp : sigDir === "short" ? TrendingDown : Minus;

  const sigBadgeClass =
    sigDir === "long"
      ? "border-green-500/30 bg-green-500/10 text-green-400"
      : sigDir === "short"
        ? "border-red-500/30 bg-red-500/10 text-red-400"
        : "border-white/10 bg-white/5 text-gray-400";

  const handleClick = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const isConnected = wsStatus === "connected";

  return (
    <div
      className={`fixed inset-x-0 top-16 z-40 transition-transform duration-200 ${
        visible ? "translate-y-0" : "-translate-y-[200%]"
      }`}
      aria-hidden={!visible}
    >
      <button
        onClick={handleClick}
        className={`flex w-full flex-col gap-0.5 border-b-2 px-3 py-1.5 text-right backdrop-blur-md transition-colors sm:py-2 ${
          sigDir === "long"
            ? "border-green-500/50 bg-[#051118]/80 hover:bg-[#051118]"
            : sigDir === "short"
              ? "border-red-500/50 bg-[#051118]/80 hover:bg-[#051118]"
              : "border-white/5 bg-[#051118]/90 hover:bg-[#051118]"
        }`}
        aria-label="کارت سیگنال"
      >
        <div className="flex w-full items-center justify-between gap-2">
          <div className="flex min-w-0 flex-1 items-center gap-1.5">
            {isConnected ? (
              <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-green-500" />
            ) : (
              <WifiOff className="h-3 w-3 shrink-0 text-orange-500 animate-pulse" />
            )}
            <p className="truncate text-[11px] font-bold leading-tight text-gray-200">
              {tickerName || ticker}
            </p>
          </div>

          {sigText && (
            <span
              className={`hidden shrink-0 items-center gap-0.5 rounded border px-1.5 py-0 text-[9px] font-bold leading-tight sm:flex ${sigBadgeClass}`}
            >
              <DirIcon className="h-2.5 w-2.5" />
              {sigText}
              <span className="num">· {sigConf}%</span>
            </span>
          )}

          <div className="flex shrink-0 items-baseline gap-1">
            <span className={`num text-[12px] font-bold leading-tight transition-colors duration-300 ${priceFlash === "up" ? "text-green-400" : priceFlash === "down" ? "text-red-400" : "text-gray-100"}`}>
              {formatNumber(displayPrice)}
            </span>
            
            {priceFlash && (
              <span className={`num text-[9px] leading-tight ${priceFlash === "up" ? "text-green-400" : "text-red-400"}`}>
                {priceFlash === "up" ? "▲" : "▼"}
              </span>
            )}
          </div>

          <ArrowUp className="h-3 w-3 shrink-0 text-gray-500/50" />
        </div>

        <div className="flex w-full items-center justify-between gap-2 text-[9px] leading-tight text-gray-500">
          <span className="num truncate">{ticker}</span>
          <span className="hidden items-center gap-1.5 sm:flex">
            {meta && (
              <span className="flex items-center gap-0.5">
                <span className="text-[8px]">{meta.icon}</span>
                {meta.label}
              </span>
            )}
            <span className="text-white/10">·</span>
            <span>{timeframe}</span>
          </span>
        </div>
      </button>
    </div>
  );
}