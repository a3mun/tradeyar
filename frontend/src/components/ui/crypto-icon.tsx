"use client";

/**
 * CryptoIcon — لوگوی کریپتو با fallback خودکار
 * ============================================================
 * نسخه ۲.۰ — فاز ۱۰.۲
 *
 * ═══ تغییرات ═══
 *   • حذف CDN خارجی (coincap از ایران دسترسی نداره)
 *   • fallback گرادیانتی محلی (بدون درخواست شبکه)
 *   • نمایش حرف اول نماد با رنگ اختصاصی
 */

import { useState } from "react";
import {
  getCryptoIconUrl,
  isCryptoTicker,
} from "@/lib/crypto-icons";

interface Props {
  /** نماد استاندارد داخلی (BTC-USD, ETH-IRT, فولاد, ...) */
  ticker: string;
  /** اندازه */
  size?: "sm" | "md" | "lg";
  /** کلاس اضافه */
  className?: string;
  /** متن جایگزین */
  alt?: string;
}

const SIZE_CLASSES = {
  sm: "h-4 w-4 text-[8px]",
  md: "h-5 w-5 text-[9px]",
  lg: "h-6 w-6 text-[11px]",
};

// ═══ رنگ gradient بر اساس حرف اول نماد ═══
const GRADIENT_MAP: Record<string, string> = {
  A: "from-red-500 to-orange-500",
  B: "from-yellow-500 to-orange-500",
  C: "from-blue-500 to-cyan-500",
  D: "from-yellow-500 to-amber-500",
  E: "from-purple-500 to-pink-500",
  F: "from-blue-400 to-indigo-500",
  G: "from-green-500 to-emerald-500",
  H: "from-pink-500 to-rose-500",
  I: "from-cyan-500 to-blue-500",
  J: "from-yellow-500 to-orange-500",
  K: "from-red-500 to-pink-500",
  L: "from-indigo-500 to-purple-500",
  M: "from-purple-500 to-fuchsia-500",
  N: "from-green-500 to-teal-500",
  O: "from-orange-500 to-red-500",
  P: "from-purple-500 to-violet-500",
  Q: "from-pink-500 to-purple-500",
  R: "from-red-500 to-rose-500",
  S: "from-blue-500 to-sky-500",
  T: "from-cyan-500 to-teal-500",
  U: "from-blue-500 to-indigo-500",
  V: "from-violet-500 to-purple-500",
  W: "from-slate-500 to-zinc-500",
  X: "from-yellow-500 to-yellow-600",
  Y: "from-yellow-400 to-yellow-600",
  Z: "from-blue-500 to-cyan-500",
};

export function CryptoIcon({
  ticker,
  size = "sm",
  className = "",
  alt,
}: Props) {
  const [errored, setErrored] = useState(false);

  // ─── نماد بورس یا نامعتبر → null ───
  if (!ticker || !isCryptoTicker(ticker)) {
    return null;
  }

  // ─── استخراج نماد پایه (BTC از BTC-USD) ───
  const base = ticker.split("-")[0];
  const firstChar = base[0]?.toUpperCase() || "?";

  const sizeClass = SIZE_CLASSES[size];
  const gradient = GRADIENT_MAP[firstChar] || "from-slate-500 to-zinc-500";

  // ═══ fallback گرادیانتی (بدون شبکه) ═══
  if (errored) {
    return (
      <div
        className={`${sizeClass} shrink-0 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center font-bold text-white shadow-sm ${className}`}
        aria-label={alt || ticker}
        title={base}
      >
        {firstChar}
      </div>
    );
  }

  return (
    <img
      src={getCryptoIconUrl(ticker)}
      alt={alt || ticker}
      className={`${sizeClass.split(" ")[0]} ${sizeClass.split(" ")[1]} shrink-0 rounded-full object-contain ${className}`}
      loading="lazy"
      onError={() => setErrored(true)}
    />
  );
}