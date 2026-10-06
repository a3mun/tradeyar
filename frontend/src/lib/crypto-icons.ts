/**
 * lib/crypto-icons.ts
 * لوگوی نمادهای کریپتو — لوکال + fallback CDN
 * ============================================================
 *
 * ═══ چرا لوکال + CDN ═══
 * • لوکال: سرعت بالا، بدون وابستگی به اینترنت
 * • CDN: fallback برای نمادهای جدید یا نایاب
 *
 * ═══ نحوه‌ی استفاده ═══
 * ```tsx
 * import { getCryptoIconUrl, getCryptoIconFallback, isCryptoTicker } from "@/lib/crypto-icons";
 *
 * {isCryptoTicker(data.ticker) && (
 *   <img
 *     src={getCryptoIconUrl(data.ticker)}
 *     alt={data.ticker}
 *     onError={(e) => {
 *       const img = e.target as HTMLImageElement;
 *       if (!img.dataset.fallback) {
 *         img.dataset.fallback = "1";
 *         img.src = getCryptoIconFallback(data.ticker);
 *       } else {
 *         img.style.display = "none";
 *       }
 *     }}
 *   />
 * )}
 * ```
 */

/**
 * URL لوکال لوگوی کریپتو.
 *
 * مثال:
 *   "BTC-USD" → "/crypto-icons/btc.png"
 *   "ETH-IRT" → "/crypto-icons/eth.png"
 *   "PAXG-USD" → "/crypto-icons/paxg.png"
 */
export function getCryptoIconUrl(ticker: string): string {
  if (!ticker) return "";
  const base = ticker.split("-")[0].toLowerCase();
  return `/crypto-icons/${base}.png`;
}

/**
 * URL CDN — fallback وقتی لوکال نیست.
 */
export function getCryptoIconFallback(ticker: string): string {
  if (!ticker) return "";
  const base = ticker.split("-")[0].toLowerCase();
  return `https://assets.coincap.io/assets/icons/${base}@2x.png`;
}

/**
 * آیا این نماد کریپتو هست؟
 *
 * ─── کریپتو ───
 *   BTC-USD, ETH-IRT, USDT-IRT → true
 *
 * ─── بورس تهران ───
 *   فولاد, شپنا, خودرو → false
 */
export function isCryptoTicker(ticker: string): boolean {
  if (!ticker) return false;
  return /^[A-Z]/.test(ticker);
}