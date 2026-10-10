"""
core/pre_breakout.py
تشخیص فرصت‌های قبل از انفجار — نسخه ۱.۰
============================================================
هدف: پیدا کردن نمادهایی که «آماده رشد» هستند ولی هنوز
      حرکت نکردن.

═══ معیارهای علمی ═══

  ۱. Bollinger Squeeze (فشردگی باندها)
       • bb_width_pct < 20th percentile تاریخی
       • نشانه‌ی انرژی ذخیره‌شده

  ۲. ADX پایین (رژیم رنج)
       • ADX < 20
       • بازار جهت نگرفته

  ۳. Range فشرده (Consolidation)
       • (max(high, N) - min(low, N)) < 2.5 × ATR
       • یعنی قیمت در بازه‌ی تنگ نوسان می‌کنه

  ۴. Volume Pattern (حجم در حال افزایش)
       • vol_ratio (current / ma20) بین 0.7 و 1.5
       • نه خیلی کم، نه خیلی زیاد
       • چرا: volume spike قبل از breakout شروع می‌شه

  ۵. نزدیک بودن به سطح کلیدی
       • close - nearest_resistance < 3%
       • یا close - nearest_support < 3%
       • آماده‌ی breakout به هر دو طرف

  ۶. هم‌راستایی میانگین‌ها (اختیاری)
       • |EMA20 - EMA50| / price < 1%
       • میانگین‌ها نزدیک هم (آماده جدایی)

═══ خروجی ═══

  {
    "is_pre_breakout": bool,
    "score": 0-100,
    "direction_bias": "up" | "down" | "neutral",
    "reasons": [str, ...],
    "details": {...}
  }
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

from core.utils import safe_num

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# آستانه‌ها
# ═══════════════════════════════════════════════════════════
# ─── فشردگی Bollinger (درصد) ───
BB_SQUEEZE_PCT = 1.2  # زیر این مقدار = فشرده

# ─── ADX ───
ADX_RANGE_MAX = 22.0  # بالاتر از این = ترند

# ─── Range/ATR ───
RANGE_ATR_MAX = 3.0  # بازه بیشتر از این = پهن

# ─── Volume ───
VOL_RATIO_MIN = 0.6
VOL_RATIO_MAX = 1.8

# ─── فاصله از سطح ───
NEAR_LEVEL_PCT = 3.0

# ─── فاصله EMA20/EMA50 ───
EMA_TIGHT_PCT = 1.5


# ═══════════════════════════════════════════════════════════
# تشخیص اصلی
# ═══════════════════════════════════════════════════════════
def detect_pre_breakout(
    df: pd.DataFrame,
    *,
    lookback_squeeze: int = 100,
    lookback_range: int = 20,
) -> dict:
    """
    تشخیص فرصت‌های قبل از انفجار.

    Args:
        df: DataFrame با ستون‌های OHLCV + اندیکاتورها
            (باید با compute_indicators پردازش شده باشه)
        lookback_squeeze: تعداد کندل برای محاسبه‌ی percentile
        lookback_range: تعداد کندل برای محاسبه‌ی range

    Returns:
        dict با is_pre_breakout، score، direction_bias، reasons، details
    """
    result = {
        "is_pre_breakout": False,
        "score": 0,
        "direction_bias": "neutral",
        "reasons": [],
        "details": {},
    }

    if df is None or df.empty or len(df) < max(lookback_squeeze, 50):
        return result

    try:
        last = df.iloc[-1]
        price = safe_num(last.get("close"))

        if price <= 0:
            return result

        # ═══════════════════════════════════════════════
        # ۱. Bollinger Squeeze
        # ═══════════════════════════════════════════════
        bb_width = safe_num(last.get("bb_width_pct"))
        squeeze_active = False
        squeeze_percentile = 100.0

        if bb_width > 0 and "bb_width_pct" in df.columns:
            # ─── percentile تاریخی ───
            hist = df["bb_width_pct"].tail(lookback_squeeze).dropna()
            hist = hist[hist > 0]

            if len(hist) >= 30:
                squeeze_percentile = (hist < bb_width).mean() * 100

                if squeeze_percentile < 20:
                    squeeze_active = True
                    result["reasons"].append(
                        f"📊 فشردگی Bollinger (percentile {squeeze_percentile:.0f}%) — "
                        f"انرژی ذخیره‌شده"
                    )

        result["details"]["bb_width_pct"] = round(bb_width, 3)
        result["details"]["squeeze_percentile"] = round(squeeze_percentile, 1)
        result["details"]["squeeze_active"] = squeeze_active

        # ═══════════════════════════════════════════════
        # ۲. ADX پایین (رژیم رنج)
        # ═══════════════════════════════════════════════
        adx = safe_num(last.get("adx"), 20)
        range_active = adx < ADX_RANGE_MAX

        if range_active:
            result["reasons"].append(f"⚖️ ADX={adx:.0f} — بازار هنوز جهت نگرفته")

        result["details"]["adx"] = round(adx, 1)
        result["details"]["range_active"] = range_active

        # ═══════════════════════════════════════════════
        # ۳. Range فشرده
        # ═══════════════════════════════════════════════
        atr = safe_num(last.get("atr"))
        range_ratio = 0.0
        range_tight = False

        if atr > 0 and len(df) >= lookback_range:
            recent = df.tail(lookback_range)
            high_max = safe_num(recent["high"].max())
            low_min = safe_num(recent["low"].min())

            if high_max > low_min and high_max > 0:
                range_pct = (high_max - low_min) / price * 100
                range_ratio = (high_max - low_min) / atr

                if range_ratio < RANGE_ATR_MAX:
                    range_tight = True
                    result["reasons"].append(
                        f"📉 بازه‌ی {lookback_range} کندل فقط "
                        f"{range_ratio:.1f}× ATR — Consolidation"
                    )

        result["details"]["range_ratio"] = round(range_ratio, 2)
        result["details"]["range_tight"] = range_tight

        # ═══════════════════════════════════════════════
        # ۴. Volume Pattern
        # ═══════════════════════════════════════════════
        vol_ratio = 0.0
        volume_healthy = False

        vol = safe_num(last.get("volume"))
        vol_ma = safe_num(last.get("vol_ma"))

        if vol_ma > 0:
            vol_ratio = vol / vol_ma

            if VOL_RATIO_MIN <= vol_ratio <= VOL_RATIO_MAX:
                volume_healthy = True
                if vol_ratio > 1.0:
                    result["reasons"].append(
                        f"💧 حجم {vol_ratio:.1f}× میانگین — در حال افزایش"
                    )

        result["details"]["vol_ratio"] = round(vol_ratio, 2)
        result["details"]["volume_healthy"] = volume_healthy

        # ═══════════════════════════════════════════════
        # ۵. نزدیک بودن به سطح کلیدی
        # ═══════════════════════════════════════════════
        nearest_r = safe_num(last.get("nearest_resistance"))
        nearest_s = safe_num(last.get("nearest_support"))
        near_resistance = False
        near_support = False

        if nearest_r > 0:
            dist_r_pct = abs(nearest_r - price) / price * 100
            if dist_r_pct < NEAR_LEVEL_PCT:
                near_resistance = True
                result["reasons"].append(
                    f"🎯 {dist_r_pct:.1f}٪ از مقاومت — نزدیک breakout"
                )

        if nearest_s > 0:
            dist_s_pct = abs(price - nearest_s) / price * 100
            if dist_s_pct < NEAR_LEVEL_PCT:
                near_support = True
                result["reasons"].append(f"🛡 {dist_s_pct:.1f}٪ از حمایت — نزدیک bounce")

        result["details"]["dist_resistance_pct"] = (
            round(abs(nearest_r - price) / price * 100, 2) if nearest_r > 0 else None
        )
        result["details"]["dist_support_pct"] = (
            round(abs(price - nearest_s) / price * 100, 2) if nearest_s > 0 else None
        )

        # ═══════════════════════════════════════════════
        # ۶. هم‌راستایی EMA20/EMA50
        # ═══════════════════════════════════════════════
        ema20 = safe_num(last.get("ema20"))
        ema50 = safe_num(last.get("ema50"))
        ema_tight = False

        if ema20 > 0 and ema50 > 0 and price > 0:
            ema_dist_pct = abs(ema20 - ema50) / price * 100
            if ema_dist_pct < EMA_TIGHT_PCT:
                ema_tight = True
                result["reasons"].append(
                    f"📈 EMA20/EMA50 نزدیک هم ({ema_dist_pct:.2f}٪) — " f"آماده جدایی"
                )

        result["details"]["ema_dist_pct"] = (
            round(abs(ema20 - ema50) / price * 100, 2)
            if ema20 > 0 and ema50 > 0 and price > 0
            else None
        )
        result["details"]["ema_tight"] = ema_tight

        # ═══════════════════════════════════════════════
        # تعیین جهت
        # ═══════════════════════════════════════════════
        direction_bias = "neutral"

        # ─── معیار: RSI متمایل به کدوم سمت ───
        rsi = safe_num(last.get("rsi"), 50)
        macd_h = safe_num(last.get("macd_hist"), 0)

        # ─── نزدیک سطح ───
        if near_resistance and not near_support:
            direction_bias = "up"  # آماده breakout صعودی
        elif near_support and not near_resistance:
            direction_bias = "down"  # آماده breakout نزولی

        # ─── یا بر اساس RSI + MACD ───
        elif rsi > 55 and macd_h > 0:
            direction_bias = "up"
        elif rsi < 45 and macd_h < 0:
            direction_bias = "down"

        result["direction_bias"] = direction_bias

        # ═══════════════════════════════════════════════
        # امتیاز نهایی (0-100)
        # ═══════════════════════════════════════════════
        score = 0

        if squeeze_active:
            score += 25
        if range_active:
            score += 15
        if range_tight:
            score += 15
        if volume_healthy:
            score += 15
        if near_resistance or near_support:
            score += 20
        if ema_tight:
            score += 10

        result["score"] = score
        result["is_pre_breakout"] = score >= 60  # حداقل ۳ معیار

        return result

    except Exception as e:
        logger.warning(f"[PreBreakout] خطا: {e!r}")
        return result


def pre_breakout_score_for_groups(groups: dict, df: pd.DataFrame) -> float:
    """
    امتیاز pre-breakout برای اسکنر (بدون محاسبه‌ی کامل).

    ⚠️ برای سرعت بالا، فقط معیارهای موجود در df + groups چک می‌شن.
    """
    try:
        result = detect_pre_breakout(df)
        return float(result.get("score", 0))
    except Exception:
        return 0.0


__all__ = [
    "detect_pre_breakout",
    "pre_breakout_score_for_groups",
    "BB_SQUEEZE_PCT",
    "ADX_RANGE_MAX",
    "RANGE_ATR_MAX",
]
