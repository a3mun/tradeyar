"use client";

/**
 * CryptoIcon — لوگوی کریپتو + آیکون‌های اختصاصی فارکس/کالا/شاخص
 * ============================================================
 * نسخه ۳.۰ — فاز ۱۶.۶
 *
 * ═══ تغییرات ═══
 *   • افزودن آیکون‌های اختصاصی برای نمادهای فارکس (طلا، نقره، نفت، شاخص‌ها)
 *   • حفظ fallback گرادیانتی برای کریپتوها
 */

import { useState } from "react";
import { 
  Coins, Gem, Droplet, DollarSign, BarChart3, 
  TrendingUp, Landmark, Bitcoin, Banknote, CircleDollarSign
} from "lucide-react";
import {
  getCryptoIconUrl,
  isCryptoTicker,
} from "@/lib/crypto-icons";

interface Props {
  ticker: string;
  size?: "sm" | "md" | "lg";
  className?: string;
  alt?: string;
}

const SIZE_CLASSES = {
  sm: "h-4 w-4 text-[8px]",
  md: "h-5 w-5 text-[9px]",
  lg: "h-6 w-6 text-[11px]",
};

// ═══ آیکون‌های اختصاصی برای نمادهای فارکس/کالا/شاخص ═══
const FOREX_ICON_MAP: Record<string, React.ReactNode> = {
  "XAU-USD": <Coins className="h-full w-full text-[#d6ad60]" />,           // طلا
  "XAG-USD": <Coins className="h-full w-full text-slate-300" />,           // نقره
  "USOIL-USD": <Droplet className="h-full w-full text-slate-500" />,       // نفت WTI
  "UKOIL-USD": <Droplet className="h-full w-full text-amber-700" />,       // نفت برنت
  "DXY-USD": <DollarSign className="h-full w-full text-green-500" />,      // شاخص دلار
  "US500-USD": <BarChart3 className="h-full w-full text-blue-500" />,      // S&P 500
  "US30-USD": <TrendingUp className="h-full w-full text-indigo-500" />,    // داوجونز
  "USTEC-USD": <BarChart3 className="h-full w-full text-purple-500" />,    // ناسداک
  "EUR-USD": <Landmark className="h-full w-full text-sky-400" />,          // یورو
  "BTC-USD": <Bitcoin className="h-full w-full text-[#f7931a]" />,         // بیت‌کوین
  "GC=F": <Coins className="h-full w-full text-[#d6ad60]" />,              // (در صورتی که استفاده شد)
};

// ═══ رنگ gradient بر اساس حرف اول نماد (برای کریپتوها) ═══
const GRADIENT_MAP: Record<string, string> = {
  A: "from-red-500 to-orange-500", B: "from-yellow-500 to-orange-500",
  C: "from-blue-500 to-cyan-500", D: "from-yellow-500 to-amber-500",
  E: "from-purple-500 to-pink-500", F: "from-blue-400 to-indigo-500",
  G: "from-green-500 to-emerald-500", H: "from-pink-500 to-rose-500",
  I: "from-cyan-500 to-blue-500", J: "from-yellow-500 to-orange-500",
  K: "from-red-500 to-pink-500", L: "from-indigo-500 to-purple-500",
  M: "from-purple-500 to-fuchsia-500", N: "from-green-500 to-teal-500",
  O: "from-orange-500 to-red-500", P: "from-purple-500 to-violet-500",
  Q: "from-pink-500 to-purple-500", R: "from-red-500 to-rose-500",
  S: "from-blue-500 to-sky-500", T: "from-cyan-500 to-teal-500",
  U: "from-blue-500 to-indigo-500", V: "from-violet-500 to-purple-500",
  W: "from-slate-500 to-zinc-500", X: "from-yellow-500 to-yellow-600",
  Y: "from-yellow-400 to-yellow-600", Z: "from-blue-500 to-cyan-500",
};

export function CryptoIcon({
  ticker,
  size = "sm",
  className = "",
  alt,
}: Props) {
  const [errored, setErrored] = useState(false);

  if (!ticker) return null;

  // ۱. بررسی اینکه آیا نماد فارکس/کالا است؟ (با آیکون اختصاصی)
  const forexIcon = FOREX_ICON_MAP[ticker];
  if (forexIcon) {
    return (
      <div
        className={`${SIZE_CLASSES[size]} shrink-0 rounded-full bg-white/5 flex items-center justify-center p-0.5 ${className}`}
        title={alt || ticker}
      >
        {forexIcon}
      </div>
    );
  }

  // ۲. اگر کریپتو بود
  if (isCryptoTicker(ticker)) {
    const base = ticker.split("-")[0];
    const firstChar = base[0]?.toUpperCase() || "?";
    const sizeClass = SIZE_CLASSES[size];
    const gradient = GRADIENT_MAP[firstChar] || "from-slate-500 to-zinc-500";

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
        className={`${sizeClass.split(" ")[0]} shrink-0 rounded-full object-contain ${className}`}
        loading="lazy"
        onError={() => setErrored(true)}
      />
    );
  }

  // ۳. اگر نه کریپتو بود و نه فارکس، null برگردان
  return null;
}