"""
core/pump_detector.py
تشخیص Pump و Dump — نسخه ۱.۰ (فاز B)
============================================================
هدف: هشدار زودهنگام درباره پامپ/دامپ در اسکنر فرصت‌ها.

⚠️ این ماژول **فقط در اسکنر** استفاده می‌شود — نه در تحلیل اصلی.
دلیل: پامپ فعال + سیگنال SHORT با هم = دوگانگی برای کاربر.
در کارت سیگنال اصلی، این سیگنال نمایش داده نمی‌شود.

═══ ۹ معیار علمی (روانشناسی اقتصادی) ═══
  ۱. Volume Spike      → FOMO / وحشت
  ۲. Price Velocity    → شتاب هیجانی
  ۳. RSI Extreme       → اشباع خرید/فروش
  ۴. ATR Spike         → نوسان انفجاری
  ۵. BB Breakout       → شکست آماری
  ۶. CVD Divergence    → پول هوشمند خلاف جهت
  ۷. Wick Rejection    → رد شدن قیمت
  ۸. Funding Rate      → (در آینده)
  ۹. Orderbook Wall    → (در آینده)

═══ خروجی ═══
  {
    "pump_score": 0-100,
    "dump_score": 0-100,
    "warning_level": "none" | "watch" | "alert",
    "type": "none" | "pump" | "dump" | "both",
    "reasons": [...],
  }
"""

import logging

import numpy as np
import pandas as pd

from core.utils import safe_num

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# آستانه‌ها
# ═══════════════════════════════════════════════════════════
VOLUME_SPIKE_MULT = 3.0  # حجم > ۳× میانگین
ATR_SPIKE_MULT = 2.0  # ATR > ۲× میانگین
VELOCITY_MULT = 2.0  # شتاب قیمت > ۲× ATR در ۳ کندل
RSI_OVERBOUGHT = 80
RSI_OVERSOLD = 20
BB_SIGMA_BREAK = 2.5  # بالای ۲.۵σ
WICK_REJECTION_RATIO = 0.6  # ۶۰٪ کندل = سایه

# وزن‌ها (جمع = ۱۰۰)
W_VOLUME = 25
W_VELOCITY = 20
W_RSI = 15
W_ATR = 15
W_BB = 10
W_CVD = 10
W_WICK = 5

# آستانه هشدار
WATCH_THRESHOLD = 50
ALERT_THRESHOLD = 70


def detect_pump_dump(
    df: pd.DataFrame,
    atr_ma_period: int = 20,
    velocity_lookback: int = 3,
) -> dict:
    """
    تشخیص پامپ و دامپ.

    Args:
        df: DataFrame با OHLCV + اندیکاتورها (rsi، atr، bb_upper، bb_lower، cvd)
        atr_ma_period: دوره میانگین ATR
        velocity_lookback: تعداد کندل برای محاسبه شتاب

    Returns:
        dict با pump_score, dump_score, warning_level, type, reasons
    """
    result = {
        "pump_score": 0.0,
        "dump_score": 0.0,
        "warning_level": "none",
        "type": "none",
        "reasons": [],
        "active_signals": [],
    }

    if df is None or len(df) < max(atr_ma_period, velocity_lookback + 5):
        return result

    try:
        last = df.iloc[-1]
        price = safe_num(last.get("close"))
        if price <= 0:
            return result

        pump_pts = 0.0
        dump_pts = 0.0
        reasons = []
        active = []

        # ═══ ۱. Volume Spike ═══
        vol = safe_num(last.get("volume"))
        vol_ma = safe_num(last.get("vol_ma"))
        if vol_ma > 0 and vol > vol_ma * VOLUME_SPIKE_MULT:
            ratio = vol / vol_ma
            # جهت حجم بر اساس کندل
            prev = df.iloc[-2] if len(df) > 1 else last
            prev_close = safe_num(prev.get("close"))
            is_up = price > prev_close
            if is_up:
                pump_pts += W_VOLUME
                reasons.append(f"🔺 حجم انفجاری {ratio:.1f}× با کندل صعودی")
            else:
                dump_pts += W_VOLUME
                reasons.append(f"🔻 حجم انفجاری {ratio:.1f}× با کندل نزولی")
            active.append("volume_spike")

        # ═══ ۲. Price Velocity ═══
        atr = safe_num(last.get("atr"))
        if atr > 0 and len(df) > velocity_lookback:
            past = df.iloc[-velocity_lookback - 1]
            past_close = safe_num(past.get("close"))
            if past_close > 0:
                velocity_pct = (price - past_close) / past_close * 100
                atr_pct = atr / price * 100
                velocity_ratio = abs(velocity_pct) / atr_pct if atr_pct > 0 else 0
                if velocity_ratio > VELOCITY_MULT:
                    if velocity_pct > 0:
                        pump_pts += W_VELOCITY
                        reasons.append(
                            f"🚀 شتاب صعودی {velocity_pct:+.2f}% در {velocity_lookback} کندل"
                        )
                    else:
                        dump_pts += W_VELOCITY
                        reasons.append(
                            f"💥 شتاب نزولی {velocity_pct:+.2f}% در {velocity_lookback} کندل"
                        )
                    active.append("velocity")

        # ═══ ۳. RSI Extreme ═══
        rsi = safe_num(last.get("rsi"), 50)
        if rsi >= RSI_OVERBOUGHT:
            pump_pts += W_RSI
            reasons.append(f"🔥 RSI={rsi:.0f} اشباع خرید شدید")
            active.append("rsi_overbought")
        elif rsi <= RSI_OVERSOLD:
            dump_pts += W_RSI
            reasons.append(f"❄️ RSI={rsi:.0f} اشباع فروش شدید")
            active.append("rsi_oversold")

        # ═══ ۴. ATR Spike ═══
        if atr > 0 and "atr" in df.columns and len(df) >= atr_ma_period:
            atr_ma = safe_num(df["atr"].tail(atr_ma_period).mean())
            if atr_ma > 0:
                atr_ratio = atr / atr_ma
                if atr_ratio > ATR_SPIKE_MULT:
                    # جهت ATR بر اساس کندل
                    is_up = price > safe_num(df.iloc[-2].get("close"))
                    if is_up:
                        pump_pts += W_ATR
                        reasons.append(f"⚡ نوسان انفجاری {atr_ratio:.1f}× (صعودی)")
                    else:
                        dump_pts += W_ATR
                        reasons.append(f"⚡ نوسان انفجاری {atr_ratio:.1f}× (نزولی)")
                    active.append("atr_spike")

        # ═══ ۵. BB Breakout ═══
        bb_upper = safe_num(last.get("bb_upper"))
        bb_lower = safe_num(last.get("bb_lower"))
        bb_mid = safe_num(last.get("bb_mid"))
        if bb_upper > 0 and bb_lower > 0 and bb_mid > 0:
            bb_std = (bb_upper - bb_mid) / 2  # σ
            if bb_std > 0:
                if price > bb_mid + BB_SIGMA_BREAK * bb_std:
                    pump_pts += W_BB
                    reasons.append("📈 شکست بالای ۲.۵σ باند بولینگر")
                    active.append("bb_breakout_up")
                elif price < bb_mid - BB_SIGMA_BREAK * bb_std:
                    dump_pts += W_BB
                    reasons.append("📉 شکست زیر ۲.۵σ باند بولینگر")
                    active.append("bb_breakout_down")

        # ═══ ۶. CVD Divergence ═══
        if "cvd" in df.columns and len(df) > 5:
            cvd_now = safe_num(last.get("cvd"))
            cvd_5ago = safe_num(df.iloc[-6].get("cvd"))
            price_5ago = safe_num(df.iloc[-6].get("close"))
            if price_5ago > 0:
                price_change = price - price_5ago
                cvd_change = cvd_now - cvd_5ago
                # واگرایی: قیمت بالا، CVD پایین (یا برعکس)
                if price_change > 0 and cvd_change < 0:
                    pump_pts += W_CVD
                    reasons.append("⚠️ واگرایی: قیمت بالا، CVD پایین (خروج پول)")
                    active.append("cvd_divergence_bear")
                elif price_change < 0 and cvd_change > 0:
                    dump_pts += W_CVD
                    reasons.append("⚠️ واگرایی: قیمت پایین، CVD بالا (ورود پول)")
                    active.append("cvd_divergence_bull")

        # ═══ ۷. Wick Rejection ═══
        high = safe_num(last.get("high"))
        low = safe_num(last.get("low"))
        open_ = safe_num(last.get("open"))
        candle_range = high - low
        if candle_range > 0:
            upper_wick = high - max(price, open_)
            lower_wick = min(price, open_) - low
            upper_wick_ratio = upper_wick / candle_range
            lower_wick_ratio = lower_wick / candle_range
            if upper_wick_ratio > WICK_REJECTION_RATIO:
                dump_pts += W_WICK
                reasons.append(
                    f"🔻 سایه بالایی بلند ({upper_wick_ratio*100:.0f}%) — رد شدن"
                )
                active.append("wick_rejection_top")
            elif lower_wick_ratio > WICK_REJECTION_RATIO:
                pump_pts += W_WICK
                reasons.append(
                    f"🔺 سایه پایینی بلند ({lower_wick_ratio*100:.0f}%) — حمایت"
                )
                active.append("wick_rejection_bottom")

        # ═══ محاسبه نهایی ═══
        pump_score = min(100.0, pump_pts)
        dump_score = min(100.0, dump_pts)

        if pump_score >= ALERT_THRESHOLD:
            warning = "alert"
        elif pump_score >= WATCH_THRESHOLD or dump_score >= WATCH_THRESHOLD:
            warning = "watch"
        else:
            warning = "none"

        # تعیین نوع
        if pump_score >= WATCH_THRESHOLD and dump_score >= WATCH_THRESHOLD:
            type_ = "both"  # نوسان بالا در دو طرف
        elif pump_score >= WATCH_THRESHOLD:
            type_ = "pump"
        elif dump_score >= WATCH_THRESHOLD:
            type_ = "dump"
        else:
            type_ = "none"

        result.update(
            {
                "pump_score": round(pump_score, 1),
                "dump_score": round(dump_score, 1),
                "warning_level": warning,
                "type": type_,
                "reasons": reasons,
                "active_signals": active,
            }
        )
        return result

    except Exception as e:
        logger.warning(f"[PumpDetector] خطا: {e!r}")
        return result


__all__ = [
    "detect_pump_dump",
    "WATCH_THRESHOLD",
    "ALERT_THRESHOLD",
]
