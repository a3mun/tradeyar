
"use client";

import {
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowUp,
  WifiOff,
} from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { useScrollVisibility } from "@/lib/hooks/useScrollVisibility";
import { SOURCE_BY_KEY } from "@/lib/sources";
import { formatNumber } from "@/lib/display";
import { getConfidenceLevel } from "@/lib/thresholds";
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

      prevPriceRef.current = displayPrice;

      return () => clearTimeout(timer);
    }

    prevPriceRef.current = displayPrice;
  }, [displayPrice]);

  const meta = SOURCE_BY_KEY[source];
  const sigConf = signal?.confidence ?? 0;
  const sigDir = signal?.direction ?? "neutral";

  const isDirectional = sigDir === "long" || sigDir === "short";
  const confLevel = getConfidenceLevel(sigConf, isDirectional);

  const rawSignal = signal?.signal || "";

  const englishSignal = (() => {
    const upper = rawSignal.toUpperCase();

    if (upper.includes("LONG")) return "LONG";
    if (upper.includes("SHORT")) return "SHORT";
    if (rawSignal.includes("خرید")) return "LONG";
    if (rawSignal.includes("فروش")) return "SHORT";

    return "NEUTRAL";
  })();

  const DirIcon =
    sigDir === "long"
      ? TrendingUp
      : sigDir === "short"
        ? TrendingDown
        : Minus;

  const sigBadgeClass = (() => {
    if (!isDirectional) {
      return "border-white/10 bg-white/5 text-gray-400";
    }

    switch (confLevel) {
      case "golden":
        return "border-[#d6ad60]/40 bg-[#d6ad60]/10 text-[#e5c27e]";

      case "strong":
        return sigDir === "long"
          ? "border-green-500/30 bg-green-500/10 text-green-400"
          : "border-red-500/30 bg-red-500/10 text-red-400";

      case "normal":
        return sigDir === "long"
          ? "border-green-500/20 bg-green-500/5 text-green-400/80"
          : "border-red-500/20 bg-red-500/5 text-red-400/80";

      case "weak":
        return sigDir === "long"
          ? "border-green-500/10 bg-transparent text-green-400/60"
          : "border-red-500/10 bg-transparent text-red-400/60";

      default:
        return "border-white/10 bg-white/5 text-gray-400";
    }
  })();

  const handleClick = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const isConnected = wsStatus === "connected";

  const glassTheme =
    sigDir === "long"
      ? "border-green-400/15 bg-[#071d1b]/55"
      : sigDir === "short"
        ? "border-red-400/15 bg-[#241315]/55"
        : "border-white/[0.12] bg-[#0b1c25]/55";

  return (
    <div
      className={`fixed inset-x-0 top-16 z-40 px-1.5 sm:px-0 transition-transform duration-200 ${
        visible ? "translate-y-0" : "-translate-y-[200%]"
      }`}
      aria-hidden={!visible}
    >
      <button
        onClick={handleClick}
        className={`flex w-full flex-col gap-0.5 rounded-b-xl border-b border-t px-3 py-1.5 text-right shadow-[0_8px_25px_rgba(0,0,0,0.18)] backdrop-blur-2xl backdrop-saturate-150 transition-all duration-300 sm:py-1.5 ${
          glassTheme
        } ring-1 ring-white/[0.025]`}
        aria-label="کارت سیگنال"
      >
        {/* ردیف اصلی */}
        <div className="flex w-full items-center justify-between gap-2">
          <div className="flex min-w-0 flex-1 items-center gap-1.5">
            {isConnected ? (
              <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-green-500" />
            ) : (
              <WifiOff className="h-3 w-3 shrink-0 animate-pulse text-orange-500" />
            )}

            <p className="truncate text-[11px] font-bold leading-tight text-gray-100">
              {tickerName || ticker}
            </p>
          </div>

          {sigConf > 0 && (
            <span
              className={`flex shrink-0 items-center gap-1 rounded-md border px-1.5 py-0.5 text-[9px] font-bold leading-none sm:text-[10px] ${sigBadgeClass}`}
            >
              <DirIcon className="h-2.5 w-2.5" />
              <span className="hidden sm:inline">{englishSignal}</span>
              <span className="sm:hidden">
                {englishSignal.substring(0, 1)}
              </span>
            </span>
          )}

          <div className="flex shrink-0 items-baseline gap-1">
            <span
              className={`num text-[12px] font-bold leading-tight transition-colors duration-300 ${
                priceFlash === "up"
                  ? "text-green-400"
                  : priceFlash === "down"
                    ? "text-red-400"
                    : "text-gray-100"
              }`}
            >
              {formatNumber(displayPrice)}
            </span>

            {priceFlash && (
              <span
                className={`num text-[9px] leading-tight ${
                  priceFlash === "up" ? "text-green-400" : "text-red-400"
                }`}
              >
                {priceFlash === "up" ? "▲" : "▼"}
              </span>
            )}
          </div>

          <ArrowUp className="h-3 w-3 shrink-0 text-gray-400/60" />
        </div>

        {/* ردیف اطلاعات */}
        <div className="flex w-full items-center justify-between gap-2 text-[9px] leading-none text-gray-400">
          <span className="num min-w-0 truncate">{ticker}</span>

          <span className="flex shrink-0 items-center gap-1.5 whitespace-nowrap">
            {meta && (
              <span className="flex items-center gap-0.5">
                <span className="text-[8px]">{meta.icon}</span>
                <span>{meta.label}</span>
              </span>
            )}

            <span className="text-white/20">·</span>
            <span>{timeframe}</span>
          </span>
        </div>
      </button>
    </div>
  );
}
