"use client";

/**
 * StickyMiniHeader — کارت سیگنال (خلاصه‌ی SignalCard)
 * ============================================================
 * نسخه ۲.۰ · فاز ۱۴.۷.۴
 * 🔴 تغییرات:
 *   • حذف useWebSocket().signal (حذف شد)
 *   • استفاده از tfDataCache (هم‌راستا با SignalCard)
 */

import { TrendingUp, TrendingDown, Minus, ArrowUp } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { useScrollVisibility } from "@/lib/hooks/useScrollVisibility";
import { SOURCE_BY_KEY } from "@/lib/sources";
import { formatNumber } from "@/lib/display";

export function StickyMiniHeader() {
  const { ticker, tickerName, source, timeframe, getTfData } = useAppStore();
  const { quote, status: wsStatus } = useWebSocket();
  const visible = useScrollVisibility(200);

  // 🔴 از cache مشترک بخون (هم‌راستا با SignalCard)
  const signal = getTfData(timeframe);

  const displayPrice = quote?.price ?? signal?.price ?? 0;
  const displayChange = quote?.change_pct ?? null;

  const meta = SOURCE_BY_KEY[source];
  const sigText = signal?.signal ?? "";
  const sigConf = signal?.confidence ?? 0;
  const sigDir = signal?.direction ?? "neutral";

  const DirIcon =
    sigDir === "long" ? TrendingUp : sigDir === "short" ? TrendingDown : Minus;

  const sigBadgeClass =
    sigDir === "long"
      ? "border-green-500/40 bg-green-500/10 text-green-500"
      : sigDir === "short"
        ? "border-red-500/40 bg-red-500/10 text-red-500"
        : "border-border bg-muted/30 text-muted-foreground";

  const handleClick = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

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
            ? "border-green-500/50 bg-green-500/5 hover:bg-green-500/10"
            : sigDir === "short"
              ? "border-red-500/50 bg-red-500/5 hover:bg-red-500/10"
              : "border-border/60 bg-background/95 hover:bg-background"
        }`}
        aria-label="کارت سیگنال"
      >
        <div className="flex w-full items-center justify-between gap-2">
          <div className="flex min-w-0 flex-1 items-center gap-1.5">
            {wsStatus === "connected" && (
              <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-green-500" />
            )}
            <p className="truncate text-[11px] font-bold leading-tight">
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
            <span className="num text-[12px] font-bold leading-tight">
              {formatNumber(displayPrice)}
            </span>
            {displayChange != null && displayChange !== 0 && (
              <span
                className={`num text-[9px] leading-tight ${
                  displayChange >= 0 ? "text-green-500" : "text-red-500"
                }`}
              >
                {displayChange >= 0 ? "▲" : "▼"}
                {Math.abs(displayChange).toFixed(2)}٪
              </span>
            )}
          </div>

          <ArrowUp className="h-3 w-3 shrink-0 text-muted-foreground/50" />
        </div>

        <div className="flex w-full items-center justify-between gap-2 text-[9px] leading-tight text-muted-foreground">
          <span className="num truncate">{ticker}</span>
          <span className="hidden items-center gap-1.5 sm:flex">
            {meta && (
              <span className="flex items-center gap-0.5">
                <span className="text-[8px]">{meta.icon}</span>
                {meta.label}
              </span>
            )}
            <span>·</span>
            <span>{timeframe}</span>
          </span>
        </div>
      </button>
    </div>
  );
}