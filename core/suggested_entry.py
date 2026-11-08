"""
core/suggested_entry.py
محاسبه قیمت ورود پیشنهادی — نسخه ۱.۰ (فاز B)
============================================================
هدف: نشان دادن «قیمت بهتر برای ورود» در کارت سیگنال.

═══ سه روش علمی ═══
  ۱. Structural (Swing S/R)  → سطح ساختاری چارت
  ۲. ATR Pullback            → پولبک ۰.۵ × ATR
  ۳. Fib 0.382               → فیبوناچی بین قیمت و SL

قیمت پیشنهادی = نزدیک‌ترین به قیمت فعلی (سریع‌ترین پر شدن سفارش).
"""

import logging

from core.utils import safe_num

logger = logging.getLogger(__name__)


# وزن‌ها (جمع ~۱۰۰)
W_STRUCTURAL = 40
W_ATR = 40
W_FIB = 20


def compute_suggested_entry(
    price: float,
    sl: float,
    atr: float,
    direction: str,
    swing_support: float = 0.0,
    swing_resistance: float = 0.0,
) -> dict:
    """
    محاسبه قیمت ورود پیشنهادی.

    Args:
        price: قیمت فعلی
        sl: حد ضرر
        atr: ATR فعلی
        direction: "long" یا "short"
        swing_support: نزدیک‌ترین حمایت Swing (اگر ۰، از ATR استفاده می‌شود)
        swing_resistance: نزدیک‌ترین مقاومت Swing

    Returns:
        dict با suggested_entry, method, distance_pct, alternatives
    """
    result = {
        "suggested_entry": None,
        "method": None,
        "distance_pct": None,
        "alternatives": {},
    }

    if price <= 0 or direction not in ("long", "short"):
        return result

    try:
        if direction == "long":
            # گزینه‌های ورود
            structural = (
                swing_support
                if swing_support > 0 and swing_support < price
                else price * 0.995  # fallback: ۰.۵٪ پایین
            )
            atr_pullback = price - 0.5 * atr if atr > 0 else price * 0.997
            fib_0382 = price - (price - sl) * 0.382 if sl < price else price * 0.997

            candidates = {
                "structural": structural,
                "atr_pullback": atr_pullback,
                "fib_0382": fib_0382,
            }

            # نزدیک‌ترین به قیمت = بزرگ‌ترین (چون همه زیر قیمت)
            best = max(candidates.values())
            best_method = max(candidates, key=candidates.get)

        else:  # short
            structural = (
                swing_resistance
                if swing_resistance > price and swing_resistance > 0
                else price * 1.005
            )
            atr_pullback = price + 0.5 * atr if atr > 0 else price * 1.003
            fib_0382 = price + (sl - price) * 0.382 if sl > price else price * 1.003

            candidates = {
                "structural": structural,
                "atr_pullback": atr_pullback,
                "fib_0382": fib_0382,
            }

            # نزدیک‌ترین به قیمت = کوچک‌ترین (چون همه بالای قیمت)
            best = min(candidates.values())
            best_method = min(candidates, key=candidates.get)

        distance_pct = abs(best - price) / price * 100

        return {
            "suggested_entry": round(best, 6),
            "method": best_method,
            "distance_pct": round(distance_pct, 3),
            "alternatives": {k: round(v, 6) for k, v in candidates.items()},
        }

    except Exception as e:
        logger.warning(f"[SuggestedEntry] خطا: {e!r}")
        return result


__all__ = ["compute_suggested_entry"]
