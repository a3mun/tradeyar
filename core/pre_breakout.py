"""
core/pre_breakout.py
تشخیص فرصت‌های قبل از انفجار — نسخه ۲.۰
============================================================
هدف: پیدا کردن نمادهایی که «آماده رشد» هستند ولی هنوز
      حرکت نکردن.

═══ تغییرات نسخه ۲.۰ ═══
  • direction_bias با ۵ معیار علمی (نه فقط نزدیک سطح)
  • حداقل ۴ رأی از ۵ برای جهت قوی
  • is_pre_breakout فقط صعودی (🚀 آماده پامپ)
  • is_pre_breakout_down جدید (📉 آماده ریزش)
  • فیلتر شکست کاذب (نزدیک مقاومت + حجم کم = reject)

═══ معیارهای علمی ═══
  ۱. Bollinger Squeeze — فشردگی باندها
  ۲. ADX پایین — رژیم رنج
  ۳. Range فشرده — Consolidation
  ۴. Volume Pattern — حجم سالم
  ۵. نزدیک سطح کلیدی — آماده breakout
  ۶. هم‌راستایی EMA20/EMA50

═══ خروجی ═══
  {
    "is_pre_breakout": bool,       # 🚀 فقط صعودی
    "is_pre_breakout_down": bool,  # 📉 فقط نزولی
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
BB_SQUEEZE_PCT = 1.2

# ─── ADX ───
ADX_RANGE_MAX = 22.0

# ─── Range/ATR ───
RANGE_ATR_MAX = 3.0

# ─── Volume ───
VOL_RATIO_MIN = 0.6
VOL_RATIO_MAX = 1.8
VOLUME_SUSPICIOUS_LOW = 0.7  # ← جدید — آستانه شکست کاذب

# ─── فاصله از سطح ───
NEAR_LEVEL_PCT = 3.0

# ─── فاصله EMA20/EMA50 ───
EMA_TIGHT_PCT = 1.5

# ─── حداقل رأی برای جهت ───
MIN_DIRECTION_VOTES = 4  # ← جدید — از ۵ معیار، حداقل ۴

# ─── آستانه‌ی نهایی pre_breakout ───
MIN_SCORE_PRE_BREAKOUT = 60


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
        lookback_squeeze: تعداد کندل برای percentile
        lookback_range: تعداد کندل برای range

    Returns:
        dict با is_pre_breakout، is_pre_breakout_down، score،
        direction_bias، reasons، details
    """
    result = {
        "is_pre_breakout": False,
        "is_pre_breakout_down": False,
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
        volume_suspicious_low = False  # ← جدید (فیلتر روسی)

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

            # ─── فیلتر روسی: حجم خیلی کم = شکست کاذب ───
            if vol_ratio < VOLUME_SUSPICIOUS_LOW:
                volume_suspicious_low = True
                result["reasons"].append(
                    f"⚠️ حجم {vol_ratio:.1f}× پایین‌تر از معمول — " f"احتمال شکست کاذب"
                )

        result["details"]["vol_ratio"] = round(vol_ratio, 2)
        result["details"]["volume_healthy"] = volume_healthy
        result["details"]["volume_suspicious_low"] = volume_suspicious_low

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
                    f"📈 EMA20/EMA50 نزدیک هم ({ema_dist_pct:.2f}٪) — آماده جدایی"
                )

        result["details"]["ema_dist_pct"] = (
            round(abs(ema20 - ema50) / price * 100, 2)
            if ema20 > 0 and ema50 > 0 and price > 0
            else None
        )
        result["details"]["ema_tight"] = ema_tight

        # ═══════════════════════════════════════════════
        # تعیین جهت — نسخه ۲.۰ (۵ معیار، حداقل ۴ رأی)
        # ═══════════════════════════════════════════════
        # ═══ چرا این تغییر ═══
        # نسخه ۱.۰ فقط «نزدیک مقاومت» → up و «نزدیک حمایت» → down
        # می‌کرد. این شکننده بود چون:
        #   • نزدیک مقاومت ممکنه برگشت باشه، نه شکست
        #   • نزدیک حمایت ممکنه جهش باشه، نه شکست
        #
        # نسخه ۲.۰: ۵ معیار مستقل رأی می‌دن و برای جهت
        # «قوی»، حداقل ۴ رأی از ۵ لازمه (توصیه اقتصاددانان).
        rsi = safe_num(last.get("rsi"), 50)
        macd_h = safe_num(last.get("macd_hist"), 0)
        ema200 = safe_num(last.get("ema200"))
        bb_mid = safe_num(last.get("bb_mid"))
        buy_vol = safe_num(last.get("buy_vol"), 0)
        sell_vol = safe_num(last.get("sell_vol"), 0)

        votes_up = 0
        votes_down = 0
        vote_details = []

        # ─── ۱. RSI ───
        if rsi > 55:
            votes_up += 1
            vote_details.append(f"RSI={rsi:.0f} ↑")
        elif rsi < 45:
            votes_down += 1
            vote_details.append(f"RSI={rsi:.0f} ↓")

        # ─── ۲. MACD histogram ───
        if macd_h > 0:
            votes_up += 1
            vote_details.append("MACD+ ↑")
        elif macd_h < 0:
            votes_down += 1
            vote_details.append("MACD- ↓")

        # ─── ۳. قیمت vs EMA200 ───
        if ema200 > 0 and price > ema200:
            votes_up += 1
            vote_details.append(">EMA200 ↑")
        elif ema200 > 0 and price < ema200:
            votes_down += 1
            vote_details.append("<EMA200 ↓")

        # ─── ۴. قیمت vs BB mid ───
        if bb_mid > 0 and price > bb_mid:
            votes_up += 1
            vote_details.append(">BBmid ↑")
        elif bb_mid > 0 and price < bb_mid:
            votes_down += 1
            vote_details.append("<BBmid ↓")

        # ─── ۵. Volume (buy vs sell) ───
        if buy_vol > sell_vol * 1.1:
            votes_up += 1
            vote_details.append("خریدار ↑")
        elif sell_vol > buy_vol * 1.1:
            votes_down += 1
            vote_details.append("فروشنده ↓")

        # ─── تعیین جهت (حداقل ۴ رأی — توصیه کره‌ای) ───
        direction_bias = "neutral"

        if votes_up >= MIN_DIRECTION_VOTES and votes_up > votes_down:
            direction_bias = "up"
        elif votes_down >= MIN_DIRECTION_VOTES and votes_down > votes_up:
            direction_bias = "down"

        result["direction_bias"] = direction_bias
        result["details"]["votes_up"] = votes_up
        result["details"]["votes_down"] = votes_down
        result["details"]["vote_details"] = vote_details

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

        # ═══════════════════════════════════════════════
        # is_pre_breakout — جهت‌دار (نسخه ۲.۰)
        # ═══════════════════════════════════════════════
        # ═══ چرا این تغییر ═══
        # قبلاً فقط score >= 60 بود. یعنی یه نماد نزولی هم
        # is_pre_breakout=True می‌شد و در اسکنر با لیبل
        # «آماده انفجار» نشون داده می‌شد — اشتباه بود.
        #
        # الان: score بالا + جهت مشخص. دو فیلد جدا:
        #   is_pre_breakout      → 🚀 فقط صعودی (پامپ)
        #   is_pre_breakout_down → 📉 فقط نزولی (ریزش)
        high_score = score >= MIN_SCORE_PRE_BREAKOUT

        # ─── فیلتر روسی: شکست کاذب رد بشه ───
        # نزدیک مقاومت + حجم خیلی کم = احتمال fake breakout
        is_fake_breakout_risk = (
            near_resistance and not near_support and volume_suspicious_low
        )

        result["is_pre_breakout"] = (
            high_score and direction_bias == "up" and not is_fake_breakout_risk
        )
        result["is_pre_breakout_down"] = (
            high_score and direction_bias == "down" and not is_fake_breakout_risk
        )

        result["details"]["is_fake_breakout_risk"] = is_fake_breakout_risk

        if is_fake_breakout_risk:
            result["reasons"].append("🚫 شکست کاذب رد شد — حجم کافی نیست")

        return result

    except Exception as e:
        logger.warning(f"[PreBreakout] خطا: {e!r}")
        return result


def pre_breakout_score_for_groups(groups: dict, df: pd.DataFrame) -> float:
    """امتیاز pre-breakout برای اسکنر (بدون محاسبه‌ی کامل)."""
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
    "MIN_DIRECTION_VOTES",
    "MIN_SCORE_PRE_BREAKOUT",
]
