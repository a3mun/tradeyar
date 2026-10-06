"use client";

/**
 * CryptoIcon — لوگوی کریپتو با fallback خودکار
 * ============================================================
 * ═══ چرا کامپوننت مشترک ═══
 * جلوگیری از تکرار منطق fallback در ۵-۶ کامپوننت.
 *
 * ═══ نحوه‌ی استفاده ═══
 * ```tsx
 * <CryptoIcon ticker="BTC-USD" size="sm" />
 * <CryptoIcon ticker="ETH-IRT" size="md" />
 * <CryptoIcon ticker="فولاد" size="sm" />  ← null (بورس)
 * ```
 */

import { getCryptoIconUrl, getCryptoIconFallback, isCryptoTicker } from "@/lib/crypto-icons";

interface Props {
  /** نماد استاندارد داخلی (BTC-USD, ETH-IRT, فولاد, ...) */
  ticker: string;
  /** اندازه — sm: h-4, md: h-5, lg: h-6 */
  size?: "sm" | "md" | "lg";
  /** کلاس اضافه */
  className?: string;
  /** متن جایگزین */
  alt?: string;
}

const SIZE_CLASSES = {
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-6 w-6",
};

export function CryptoIcon({
  ticker,
  size = "sm",
  className = "",
  alt,
}: Props) {
  // ─── نماد بورس یا نامعتبر → null ───
  if (!ticker || !isCryptoTicker(ticker)) {
    return null;
  }

  return (
    <img
      src={getCryptoIconUrl(ticker)}
      alt={alt || ticker}
      className={`${SIZE_CLASSES[size]} shrink-0 rounded-full object-contain ${className}`}
      loading="lazy"
      onError={(e) => {
        const img = e.target as HTMLImageElement;
        // ─── تلاش اول: fallback به CDN ───
        if (!img.dataset.fallback) {
          img.dataset.fallback = "1";
          img.src = getCryptoIconFallback(ticker);
        } else {
          // ─── fallback هم کار نکرد → مخفی کن ───
          img.style.display = "none";
        }
      }}
    />
  );
}