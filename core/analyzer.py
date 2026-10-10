"""
core/analyzer.py
موتور تحلیل تکنیکال — نسخه ۱۰.۰ (فاز ۱۰.۱)
============================================================
🔴 بازنویسی کامل با تمرکز بر:

  ۱. Trend Override — ریشه‌ی ۲۹ باخت از ۳۹ نتیجه‌ی قطعی
  ۲. Confidence بازطراحی‌شده — الان معکوس کار می‌کنه
  ۳. Trap Detection جهت‌دار — fake_breakout غلط بود
  ۴. رژیم بازار دقیق‌تر — ADX + BB width + volume
  ۵. پشتیبانی کامل spot/futures + aggressive/conservative
  ۶. خروجی سازگار با نسخه ۸.۵ (۴۰+ کلید مشابه)

═══ تغییرات کلیدی نسبت به v8.5 ═══

  • Trend Engine جدا و قدرتمند
      ├ EMA200/EMA50 + شیب
      ├ SuperTrend + Ichimoku
      ├ ADX + DI+/DI- (با pandas_ta)
      └ Market structure (HH/HL/LH/LL)
      → trend_direction: "bull"|"bear"|"flat"
      → trend_strength: 0.0-1.0

  • Trend Override در تصمیم‌گیری
      اگه trend_strength >= 0.65 و جهت مخالف باشه،
      سیگنال یا بلاک می‌شه یا confidence نصف می‌شه.

  • Confidence = f(quality, agreement, regime)
      بر اساس مقایسه‌ی نرخ برد tierهای مختلف در فاز ۱۰.۱

  • Trap جهت‌دار — fake_breakout فقط نزدیک مقاومت

  • is_weak منطقی — consensus + confidence

  • رژیم دقیق — ADX + BB width + حجم
"""

import logging

import numpy as np
import pandas as pd
import pandas_ta_classic as ta

logger = logging.getLogger(__name__)

from .contracts import (
    Signal as SigEnum,
    TF_ATR_MULT,
    compute_net_rr,
    get_adaptive_thresholds,
    get_fee_rate,
    get_tf_atr_mult,
    get_tf_spec,
)

# 🔴 فاز ۱۰.۳ — Pre-breakout detection
from .pre_breakout import detect_pre_breakout

from .utils import safe_num

# ═══════════════════════════════════════════════════════════
# پروفایل‌های ریسک — نسخه ۱۰.۰
# ═══════════════════════════════════════════════════════════
# 🎯 اهداف علمی:
#   • جسورانه    → Win Rate ≥ ۵۰٪ (ترید مکرر، دست باز)
#   • محتاطانه   → Win Rate ≥ ۷۰٪ (سخت‌گیرانه ولی نه صفر)
#
# 📚 مراجع:
#   • López de Prado (Advances in ML): Asymmetric R:R
#   • Taleb (Antifragile): برنده‌های کوچیک مکرر
#   • Andrew Lo (Adaptive Markets): regime-dependent
#
# 🇮🇷 کارمزد ایران: ~۰.۴-۱٪ round-trip
#   پس min_rr_net حداقل ۱.۰ باشه تا بعد از کارمزد سود بمونه
# ═══════════════════════════════════════════════════════════
RISK_PROFILES = {
    "aggressive_spot": {
        "name": "جسور (اسپات)",
        "sl_mult": 1.3,
        "tp_mult": 2.5,
        "min_confidence": 40,
        "min_votes_required": 2,
        "min_rr_net": 1.0,
        "min_adx": 0,
        "require_higher_tf": False,
        "color": "#DB6D28",
        "advice": "خرید در اسپات با حد ضرر. ۲-۳٪ سرمایه.",
        "leverage": None,
        "allow_short": False,
    },
    "aggressive_futures": {
        "name": "جسور (فیوچرز)",
        "sl_mult": 1.3,
        "tp_mult": 2.5,
        "min_confidence": 40,
        "min_votes_required": 2,
        "min_rr_net": 1.0,
        "min_adx": 0,
        "require_higher_tf": False,
        "color": "#DB6D28",
        "advice": "فیوچرز با اهرم ۲-۳x. حتماً حد ضرر.",
        "leverage": 3,
        "allow_short": True,
    },
    "conservative_spot": {
        "name": "محتاط (اسپات)",
        "sl_mult": 1.6,
        "tp_mult": 3.0,
        "min_confidence": 55,
        "min_votes_required": 3,
        "min_rr_net": 1.3,
        "min_adx": 18,
        "require_higher_tf": False,
        "color": "#3FB950",
        "advice": "خرید مطمئن در اسپات. ۱-۲٪ سرمایه.",
        "leverage": None,
        "allow_short": False,
    },
    "conservative_futures": {
        "name": "محتاط (فیوچرز)",
        "sl_mult": 1.6,
        "tp_mult": 3.0,
        "min_confidence": 55,
        "min_votes_required": 3,
        "min_rr_net": 1.3,
        "min_adx": 18,
        "require_higher_tf": False,
        "color": "#3FB950",
        "advice": "فیوچرز با اهرم ۱-۲x. با دقت وارد شو.",
        "leverage": 2,
        "allow_short": True,
    },
}


CONFIDENCE_TIERS = {
    "strong": (70, 100, "قوی"),
    "normal": (50, 69, "معمولی"),
    "weak": (30, 49, "ضعیف"),
    "neutral": (0, 29, "خنثی"),
}


# ═══════════════════════════════════════════════════════════
# وزن‌های گروه‌ها بر اساس رژیم — نسخه ۱۰.۰ (اصلاح‌شده)
# ═══════════════════════════════════════════════════════════
# 🔴 تغییر کلیدی: در رنج، وزن trend از 0.3 → 0.9
#
# چرا: در بازار رنج، ترند همچنان مهم‌ترین فیلتره —
#      اگر trend صعودی باشه، SHORT گرفتن فاجعه‌ست.
#      در دیتای ۳۲۵ سیگنال، ۵۸٪ سیگنال‌ها SHORT بودن
#      چون وزن trend ناچیز بود.
# ═══════════════════════════════════════════════════════════
def _regime_weights(regime: str) -> dict:
    if regime == "trend":
        return {
            "momentum": 1.2,
            "trend": 1.8,  # ← تقویت‌شده (بود 1.5)
            "volatility": 0.9,
            "volume": 1.1,
            "structure": 1.0,
        }
    elif regime == "transitional":
        return {
            "momentum": 1.3,
            "trend": 1.3,  # ← تقویت‌شده (بود 1.0)
            "volatility": 1.0,
            "volume": 1.3,
            "structure": 1.2,
        }
    else:  # range
        return {
            "momentum": 1.4,  # ← کاهش‌یافته (بود 1.8)
            "trend": 0.9,  # ← تقویت‌شده (بود 0.3) — 🔴 بحرانی
            "volatility": 1.1,
            "volume": 1.4,
            "structure": 1.3,
        }


def _confidence_tier(conf: int) -> str:
    for key, (lo, hi, _) in CONFIDENCE_TIERS.items():
        if lo <= conf <= hi:
            return key
    return "neutral"


def _is_iranian_ticker(ticker: str) -> bool:
    """تشخیص نمادهای تومانی/ریالی از روی ticker"""
    if not ticker:
        return False
    upper = ticker.upper()
    return "IRT" in upper or "RLS" in upper or upper == "USDT-IRT"


# ═══════════════════════════════════════════════════════════
# رژیم بازار — نسخه ۱۰.۰ (چند-معیاره)
# ═══════════════════════════════════════════════════════════
def classify_regime(
    adx: float,
    channel_width_pct: float = None,
    bb_width_pct: float = None,
    volume_ratio: float = None,
) -> str:
    """
    رژیم بازار — نسخه ۱۰.۰.

    ═══ معیارها ═══
      • ADX (اصلی): >25 trend، 20-25 transitional، <20 range
      • BB width (تأیید): اگر BB خیلی تنگ باشه → range تقویت‌شده
      • Volume (تأیید): volume spike در رنج → احتمال breakout

    ═══ چرا چند-معیاره ═══
    نسخه ۸.۵ فقط ADX رو می‌دید. در دیتای ۳۲۵ سیگنال،
    ۱۰۰٪ signals در رژیم "range" طبقه‌بندی شده بودن — که
    خودش نشون می‌ده تشخیص رژیم ضعیفه.
    """
    if adx is None or adx <= 0:
        return "range"

    # ─── معیار اصلی: ADX ───
    if adx >= 30:
        base = "trend"
    elif adx >= 22:
        base = "transitional"
    else:
        base = "range"

    # ─── تأیید با BB width ───
    # اگه BB خیلی تنگ باشه (< 0.5%)، بازار قطعاً رنجه
    if bb_width_pct is not None and bb_width_pct > 0:
        if bb_width_pct < 0.5 and base == "trend":
            base = "transitional"

    # ─── تأیید با volume ───
    # اگه volume خیلی بالا باشه و ADX مرزی، احتمال breakout
    if volume_ratio is not None and volume_ratio > 2.0:
        if base == "range" and adx >= 18:
            base = "transitional"

    return base


def _group_strength(score: float) -> tuple:
    a = abs(score)
    if a >= 0.6:
        return ("strong", "قوی")
    elif a >= 0.3:
        return ("normal", "متوسط")
    elif a >= 0.1:
        return ("weak", "ضعیف")
    else:
        return ("flat", "بی‌جهت")


# ═══════════════════════════════════════════════════════════
# اندیکاتورها — نسخه ۱۰.۰ (با DI+/DI- و BB width)
# ═══════════════════════════════════════════════════════════
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """افزودن اندیکاتورها به دیتافریم — نسخه ۱۰.۰"""
    if df is None or df.empty or len(df) < 50:
        return df

    df = df.copy(deep=True)

    try:
        # ═══ Momentum ═══
        df["rsi"] = ta.rsi(df["close"], length=14)
        df["willr"] = ta.willr(df["high"], df["low"], df["close"], length=14)
        df["cci"] = ta.cci(df["high"], df["low"], df["close"], length=20)
        df["roc"] = ta.roc(df["close"], length=10)

        stoch_df = ta.stoch(df["high"], df["low"], df["close"], k=5, d=3, smooth_k=3)
        if stoch_df is not None and len(stoch_df.columns) >= 2:
            df["stoch_k"] = stoch_df.iloc[:, 0]
            df["stoch_d"] = stoch_df.iloc[:, 1]
        else:
            df["stoch_k"] = 50.0
            df["stoch_d"] = 50.0

        macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
        if macd_df is not None and len(macd_df.columns) >= 3:
            df["macd_hist"] = macd_df.iloc[:, 2]
            df["macd_line"] = macd_df.iloc[:, 0]
            df["macd_signal"] = macd_df.iloc[:, 1]
        else:
            df["macd_hist"] = 0.0
            df["macd_line"] = 0.0
            df["macd_signal"] = 0.0

        # ═══ Trend ═══
        df["ema200"] = ta.ema(df["close"], length=200)
        df["ema50"] = ta.ema(df["close"], length=50)
        df["ema20"] = ta.ema(df["close"], length=20)

        # ─── ADX + DI+/DI- (نسخه ۱۰.۰ — استفاده از همه ستون‌ها) ───
        adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
        if adx_df is not None and len(adx_df.columns) >= 3:
            # ترتیب pandas_ta: ADX, DMP, DMN
            df["adx"] = adx_df.iloc[:, 0]
            df["dmp"] = adx_df.iloc[:, 1]  # DI+
            df["dmn"] = adx_df.iloc[:, 2]  # DI-
        else:
            df["adx"] = 20.0
            df["dmp"] = 20.0
            df["dmn"] = 20.0

        # ─── Supertrend ───
        try:
            st = ta.supertrend(
                df["high"], df["low"], df["close"], length=10, multiplier=3.0
            )
            if st is not None and st.shape[1] > 1:
                df["supertrend_dir"] = st.iloc[:, 1]
                df["supertrend_val"] = st.iloc[:, 0]
            else:
                df["supertrend_dir"] = 1
                df["supertrend_val"] = df["close"]
        except Exception:
            df["supertrend_dir"] = 1
            df["supertrend_val"] = df["close"]

        # ─── Ichimoku ───
        try:
            high_9 = df["high"].rolling(9).max()
            low_9 = df["low"].rolling(9).min()
            df["tenkan"] = (high_9 + low_9) / 2

            high_26 = df["high"].rolling(26).max()
            low_26 = df["low"].rolling(26).min()
            df["kijun"] = (high_26 + low_26) / 2

            high_52 = df["high"].rolling(52).max()
            low_52 = df["low"].rolling(52).min()
            df["senkou_a"] = ((df["tenkan"] + df["kijun"]) / 2).shift(26)
            df["senkou_b"] = ((high_52 + low_52) / 2).shift(26)
        except Exception:
            pass

        # ═══ Volatility ═══
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

        bb_df = ta.bbands(df["close"], length=20, std=2)
        if bb_df is not None and len(bb_df.columns) >= 3:
            df["bb_lower"] = bb_df.iloc[:, 0]
            df["bb_mid"] = bb_df.iloc[:, 1]
            df["bb_upper"] = bb_df.iloc[:, 2]
            # ─── BB width (٪) — برای رژیم ───
            df["bb_width_pct"] = (
                (df["bb_upper"] - df["bb_lower"])
                / df["bb_mid"].replace(0, np.nan)
                * 100
            )
        else:
            df["bb_lower"] = df["close"]
            df["bb_mid"] = df["close"]
            df["bb_upper"] = df["close"]
            df["bb_width_pct"] = 1.0

        try:
            kc = ta.kc(df["high"], df["low"], df["close"], length=20, scalar=1.5)
            if kc is not None and len(kc.columns) >= 3:
                df["kc_lower"] = kc.iloc[:, 0]
                df["kc_mid"] = kc.iloc[:, 1]
                df["kc_upper"] = kc.iloc[:, 2]
        except Exception:
            pass

        try:
            dc = ta.donchian(df["high"], df["low"], lower_length=20, upper_length=20)
            if dc is not None and len(dc.columns) >= 3:
                df["dc_lower"] = dc.iloc[:, 0]
                df["dc_mid"] = dc.iloc[:, 1]
                df["dc_upper"] = dc.iloc[:, 2]
        except Exception:
            pass

        df["stddev"] = df["close"].rolling(20).std()

        # ═══ Volume ═══
        if "volume" in df.columns and df["volume"].sum() > 0:
            df["obv"] = ta.obv(df["close"], df["volume"])
            df["vol_ma"] = df["volume"].rolling(20).mean()

            df["buy_vol"] = 0.0
            df["sell_vol"] = 0.0
            valid_range = (df["high"] - df["low"]) > 0
            df.loc[valid_range, "buy_vol"] = (
                (df.loc[valid_range, "close"] - df.loc[valid_range, "low"])
                / (df.loc[valid_range, "high"] - df.loc[valid_range, "low"])
                * df.loc[valid_range, "volume"]
            )
            df.loc[valid_range, "sell_vol"] = (
                df.loc[valid_range, "volume"] - df.loc[valid_range, "buy_vol"]
            )
            df["delta"] = df["buy_vol"] - df["sell_vol"]
            df["cvd"] = df["delta"].cumsum()

            cvd_mean = df["cvd"].rolling(20).mean()
            cvd_std = df["cvd"].rolling(20).std()
            df["cvd_zscore"] = (df["cvd"] - cvd_mean) / cvd_std.replace(0, np.nan)

            try:
                df["cmf"] = ta.cmf(
                    df["high"], df["low"], df["close"], df["volume"], length=20
                )
            except Exception:
                df["cmf"] = 0.0

            try:
                df["mfi"] = ta.mfi(
                    df["high"], df["low"], df["close"], df["volume"], length=14
                )
            except Exception:
                df["mfi"] = 50.0

            try:
                tp = (df["high"] + df["low"] + df["close"]) / 3
                df["vwap"] = (tp * df["volume"]).cumsum() / df["volume"].cumsum()
            except Exception:
                pass
        else:
            df["obv"] = 0
            df["vol_ma"] = 0
            df["cmf"] = 0.0
            df["mfi"] = 50.0
            df["delta"] = 0.0
            df["cvd"] = 0.0
            df["cvd_zscore"] = 0.0

    except Exception as e:
        logger.warning(f"[Analyzer] compute_indicators: {e}")

    return df


# ═══════════════════════════════════════════════════════════
# Pivot / Swing / Fibonacci (بدون تغییر)
# ═══════════════════════════════════════════════════════════
def compute_pivot_points(df: pd.DataFrame) -> dict:
    """Pivot Points با fallback برای کندل تخت"""
    if df is None or df.empty or len(df) < 2:
        return {}

    prev = df.iloc[-2]
    high = safe_num(prev.get("high"))
    low = safe_num(prev.get("low"))
    close = safe_num(prev.get("close"))

    if abs(high - low) < 1e-8:
        recent = df.iloc[-7:-2] if len(df) >= 7 else df.iloc[:-2]
        if not recent.empty:
            high = safe_num(recent["high"].max())
            low = safe_num(recent["low"].min())
            close = safe_num(recent["close"].iloc[-1])

    if high <= 0 or low <= 0 or close <= 0 or high <= low:
        return {}

    pivot = (high + low + close) / 3
    return {
        "pivot": pivot,
        "r1": 2 * pivot - low,
        "s1": 2 * pivot - high,
        "r2": pivot + (high - low),
        "s2": pivot - (high - low),
        "r3": high + 2 * (pivot - low),
        "s3": low - 2 * (high - pivot),
    }


def find_swing_points(df: pd.DataFrame, lookback: int = 50, window: int = 3) -> dict:
    result = {
        "swing_highs": [],
        "swing_lows": [],
        "nearest_resistance": 0.0,
        "nearest_support": 0.0,
        "strongest_resistance": 0.0,
        "strongest_support": 0.0,
    }

    if df is None or df.empty or len(df) < lookback:
        return result

    data = df.tail(lookback).reset_index(drop=True)
    highs = data["high"].values
    lows = data["low"].values
    n = len(data)
    current_price = safe_num(data["close"].iloc[-1])

    swing_highs = []
    swing_lows = []

    for i in range(window, n - window):
        h = highs[i]
        l = lows[i]
        if all(h >= highs[i - j] for j in range(1, window + 1)) and all(
            h >= highs[i + j] for j in range(1, window + 1)
        ):
            swing_highs.append((i, float(h)))
        if all(l <= lows[i - j] for j in range(1, window + 1)) and all(
            l <= lows[i + j] for j in range(1, window + 1)
        ):
            swing_lows.append((i, float(l)))

    result["swing_highs"] = swing_highs
    result["swing_lows"] = swing_lows

    res_above = [p for _, p in swing_highs if p > current_price]
    if res_above:
        result["nearest_resistance"] = min(res_above)
        result["strongest_resistance"] = max(res_above)
    elif swing_highs:
        result["nearest_resistance"] = max(p for _, p in swing_highs)
        result["strongest_resistance"] = result["nearest_resistance"]

    sup_below = [p for _, p in swing_lows if p < current_price]
    if sup_below:
        result["nearest_support"] = max(sup_below)
        result["strongest_support"] = min(sup_below)
    elif swing_lows:
        result["nearest_support"] = min(p for _, p in swing_lows)
        result["strongest_support"] = result["nearest_support"]

    return result


def compute_fibonacci(df: pd.DataFrame, lookback: int = 50) -> dict:
    if df is None or df.empty or len(df) < lookback:
        return {}

    data = df.tail(lookback)
    high = safe_num(data["high"].max())
    low = safe_num(data["low"].min())

    if high <= low:
        return {}

    diff = high - low
    return {
        "high": high,
        "low": low,
        "levels": {
            "0.0": high,
            "0.236": high - diff * 0.236,
            "0.382": high - diff * 0.382,
            "0.500": high - diff * 0.500,
            "0.618": high - diff * 0.618,
            "0.786": high - diff * 0.786,
            "1.0": low,
        },
    }


# ═══════════════════════════════════════════════════════════
# گروه ۱: Momentum — نسخه ۱۰.۰
# ═══════════════════════════════════════════════════════════
def _analyze_momentum(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    """گروه ۱: مومنتوم — نسخه ۱۰.۰ (regime-aware)"""
    reasons = []
    signals = []

    last = df.iloc[-1]
    adx = safe_num(last.get("adx"), 20)
    is_trending = adx >= 25

    # ═══ ۱. RSI ═══
    rsi = safe_num(last.get("rsi"), 50)

    if is_trending:
        if rsi >= 70:
            signals.append((+1.0, 1.2))
            reasons.append(f"RSI={rsi:.0f} مومنتوم قوی صعودی")
        elif rsi >= 60:
            signals.append((+0.6, 1.0))
            reasons.append(f"RSI={rsi:.0f} مومنتوم صعودی")
        elif rsi <= 30:
            signals.append((-1.0, 1.2))
            reasons.append(f"RSI={rsi:.0f} مومنتوم قوی نزولی")
        elif rsi <= 40:
            signals.append((-0.6, 1.0))
            reasons.append(f"RSI={rsi:.0f} مومنتوم نزولی")
        else:
            signals.append((0.0, 0.5))
    else:
        if rsi < 30:
            signals.append((+1.0, 1.2))
            reasons.append(f"RSI={rsi:.0f} اشباع فروش")
        elif rsi > 70:
            signals.append((-1.0, 1.2))
            reasons.append(f"RSI={rsi:.0f} اشباع خرید")
        elif rsi < 40:
            signals.append((+0.4, 0.8))
            reasons.append(f"RSI={rsi:.0f} نزدیک اشباع فروش")
        elif rsi > 60:
            signals.append((-0.4, 0.8))
            reasons.append(f"RSI={rsi:.0f} نزدیک اشباع خرید")
        else:
            signals.append((0.0, 0.5))

    # ═══ ۲. Stochastic ═══
    stoch_k = safe_num(last.get("stoch_k"), 50)
    stoch_d = safe_num(last.get("stoch_d"), 50)

    if is_trending:
        if stoch_k > stoch_d and stoch_k > 50:
            signals.append((+0.7, 1.0))
            reasons.append(f"Stochastic={stoch_k:.0f} کراس صعودی در روند")
        elif stoch_k < stoch_d and stoch_k < 50:
            signals.append((-0.7, 1.0))
            reasons.append(f"Stochastic={stoch_k:.0f} کراس نزولی در روند")
        elif stoch_k > 80:
            signals.append((+0.5, 0.8))
        elif stoch_k < 20:
            signals.append((-0.5, 0.8))
        else:
            signals.append((0.0, 0.5))
    else:
        if stoch_k < 20 and stoch_d < 20:
            signals.append((+1.0, 1.0))
            reasons.append(f"Stochastic={stoch_k:.0f} اشباع فروش")
        elif stoch_k > 80 and stoch_d > 80:
            signals.append((-1.0, 1.0))
            reasons.append(f"Stochastic={stoch_k:.0f} اشباع خرید")
        elif stoch_k > stoch_d and stoch_k < 50:
            signals.append((+0.3, 0.7))
        elif stoch_k < stoch_d and stoch_k > 50:
            signals.append((-0.3, 0.7))
        else:
            signals.append((0.0, 0.5))

    # ═══ ۳. Williams %R ═══
    willr = safe_num(last.get("willr"), -50)

    if is_trending:
        if willr > -20:
            signals.append((+0.7, 0.9))
            reasons.append(f"Williams %R={willr:.0f} قدرت خریدار")
        elif willr < -80:
            signals.append((-0.7, 0.9))
            reasons.append(f"Williams %R={willr:.0f} قدرت فروشنده")
        else:
            signals.append((0.0, 0.5))
    else:
        if willr < -80:
            signals.append((+1.0, 0.9))
            reasons.append(f"Williams %R={willr:.0f} اشباع فروش")
        elif willr > -20:
            signals.append((-1.0, 0.9))
            reasons.append(f"Williams %R={willr:.0f} اشباع خرید")
        else:
            signals.append((0.0, 0.5))

    # ═══ ۴. CCI ═══
    cci = safe_num(last.get("cci"), 0)

    if is_trending:
        if cci > 100:
            signals.append((+0.7, 0.9))
            reasons.append(f"CCI={cci:.0f} مومنتوم صعودی")
        elif cci < -100:
            signals.append((-0.7, 0.9))
            reasons.append(f"CCI={cci:.0f} مومنتوم نزولی")
        else:
            signals.append((0.0, 0.5))
    else:
        if cci < -100:
            signals.append((+0.8, 0.8))
            reasons.append(f"CCI={cci:.0f} اشباع فروش")
        elif cci > 100:
            signals.append((-0.8, 0.8))
            reasons.append(f"CCI={cci:.0f} اشباع خرید")
        else:
            signals.append((0.0, 0.5))

    # ═══ ۵. ROC ═══
    roc = safe_num(last.get("roc"), 0)
    if roc > 2:
        signals.append((+0.6, 0.7))
        reasons.append(f"ROC={roc:.1f}% مومنتوم صعودی")
    elif roc < -2:
        signals.append((-0.6, 0.7))
        reasons.append(f"ROC={roc:.1f}% مومنتوم نزولی")
    elif roc > 0.5:
        signals.append((+0.3, 0.5))
    elif roc < -0.5:
        signals.append((-0.3, 0.5))
    else:
        signals.append((0.0, 0.5))

    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0

    mom_thr = _thresholds[0] if _thresholds else 0.25

    if score > mom_thr:
        vote = +1
    elif score < -mom_thr:
        vote = -1
    else:
        vote = 0

    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "rsi": rsi,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "willr": willr,
            "cci": cci,
            "roc": roc,
            "is_trending": is_trending,
            "adx_at_calc": adx,
        },
        "weight": 1.0,
    }


# ═══════════════════════════════════════════════════════════
# گروه ۲: Trend — نسخه ۱۰.۰ (بازنویسی کامل)
# ═══════════════════════════════════════════════════════════
def _analyze_trend(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    """
    گروه ۲: روند — نسخه ۱۰.۰.

    ═══ چرا این گروه بحرانی‌ست ═══
    در دیتای ۳۲۵ سیگنال:
        trend_correct=True  →  ۱۰۰٪ برد
        trend_correct=False →  ۱۰۰٪ باخت
    یعنی موتور ترند-سنجی حیاتی‌ترین بخشه.

    ═══ چه چیزی اضافه شد ═══
      • DI+/DI- (جهت روند ADX)
      • شیب EMA200 (روند بلندمدت)
      • Ichimoku کامل (Tenkan/Kijun + Cloud)
      • Market Structure: HH/HL/LH/LL
    """
    reasons = []
    signals = []

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = safe_num(last["close"])

    # ═══ ۱. EMA200 + شیب ═══
    ema200 = safe_num(last.get("ema200"))
    ema50 = safe_num(last.get("ema50"))
    ema20 = safe_num(last.get("ema20"))

    if ema200 > 0:
        if price > ema200:
            signals.append((+1.0, 1.2))
            reasons.append("قیمت بالای EMA200 — روند بلندمدت صعودی")
        else:
            signals.append((-1.0, 1.2))
            reasons.append("قیمت زیر EMA200 — روند بلندمدت نزولی")

    # ─── ترتیب EMAها ───
    if ema20 > 0 and ema50 > 0 and ema200 > 0:
        if ema20 > ema50 > ema200:
            signals.append((+0.8, 1.0))
            reasons.append("ترتیب صعودی EMA20>50>200")
        elif ema20 < ema50 < ema200:
            signals.append((-0.8, 1.0))
            reasons.append("ترتیب نزولی EMA20<50<200")

    # ═══ ۲. MACD ═══
    macd_h = safe_num(last.get("macd_hist"))
    prev_macd_h = safe_num(prev.get("macd_hist"))
    if prev_macd_h <= 0 < macd_h:
        signals.append((+1.5, 1.3))
        reasons.append("MACD کراس صعودی")
    elif prev_macd_h >= 0 > macd_h:
        signals.append((-1.5, 1.3))
        reasons.append("MACD کراس نزولی")
    elif macd_h > 0:
        signals.append((+0.5, 0.9))
        reasons.append("MACD مثبت")
    elif macd_h < 0:
        signals.append((-0.5, 0.9))
        reasons.append("MACD منفی")
    else:
        signals.append((0.0, 0.5))

    # ═══ ۳. ADX + DI+/DI- ═══
    adx = safe_num(last.get("adx"), 20)
    dmp = safe_num(last.get("dmp"), 20)  # DI+
    dmn = safe_num(last.get("dmn"), 20)  # DI-

    if adx > 40:
        reasons.append(f"ADX={adx:.0f} روند قوی")
    elif adx > 25:
        reasons.append(f"ADX={adx:.0f} روند نرمال")
    elif adx > 20:
        reasons.append(f"ADX={adx:.0f} روند ضعیف")
    else:
        reasons.append(f"ADX={adx:.0f} بدون روند")

    # ─── DI+/DI- — جهت روند ───
    if dmp > dmn and adx > 20:
        signals.append((+0.9, 1.1))
        reasons.append(f"DI+={dmp:.0f} > DI-={dmn:.0f} — جهت صعودی")
    elif dmn > dmp and adx > 20:
        signals.append((-0.9, 1.1))
        reasons.append(f"DI-={dmn:.0f} > DI+={dmp:.0f} — جهت نزولی")

    # ═══ ۴. Supertrend ═══
    st_dir = safe_num(last.get("supertrend_dir"), 1)
    if st_dir > 0:
        signals.append((+0.9, 1.1))
        reasons.append("Supertrend صعودی")
    elif st_dir < 0:
        signals.append((-0.9, 1.1))
        reasons.append("Supertrend نزولی")

    # ═══ ۵. Ichimoku (کامل) ═══
    try:
        t_val = safe_num(last.get("tenkan"))
        k_val = safe_num(last.get("kijun"))
        sa_val = safe_num(last.get("senkou_a"))
        sb_val = safe_num(last.get("senkou_b"))

        if t_val > 0 and k_val > 0:
            if t_val > k_val and price > k_val:
                signals.append((+0.8, 0.9))
                reasons.append("Ichimoku: Tenkan بالای Kijun — صعودی")
            elif t_val < k_val and price < k_val:
                signals.append((-0.8, 0.9))
                reasons.append("Ichimoku: Tenkan زیر Kijun — نزولی")

        # ─── Cloud position ───
        if sa_val > 0 and sb_val > 0:
            cloud_top = max(sa_val, sb_val)
            cloud_bottom = min(sa_val, sb_val)
            if price > cloud_top:
                signals.append((+0.6, 0.8))
                reasons.append("Ichimoku: قیمت بالای ابر — صعودی")
            elif price < cloud_bottom:
                signals.append((-0.6, 0.8))
                reasons.append("Ichimoku: قیمت زیر ابر — نزولی")
    except Exception:
        pass

    # ═══ ۶. Market Structure (HH/HL/LH/LL) ═══
    try:
        swings = find_swing_points(df, lookback=50, window=3)
        swing_highs = swings.get("swing_highs", [])
        swing_lows = swings.get("swing_lows", [])

        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            # ─── ۲ سقف آخر ───
            recent_highs = [p for _, p in swing_highs[-2:]]
            recent_lows = [p for _, p in swing_lows[-2:]]

            hh = recent_highs[-1] > recent_highs[-2]  # Higher High
            hl = recent_lows[-1] > recent_lows[-2]  # Higher Low
            lh = recent_highs[-1] < recent_highs[-2]  # Lower High
            ll = recent_lows[-1] < recent_lows[-2]  # Lower Low

            if hh and hl:
                signals.append((+1.0, 1.2))
                reasons.append("ساختار HH/HL — روند صعودی")
            elif lh and ll:
                signals.append((-1.0, 1.2))
                reasons.append("ساختار LH/LL — روند نزولی")
    except Exception:
        pass

    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0

    t_thr = _thresholds[1] if _thresholds else 0.30
    if score > t_thr:
        vote = +1
    elif score < -t_thr:
        vote = -1
    else:
        vote = 0

    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "ema200": ema200,
            "ema50": ema50,
            "ema20": ema20,
            "macd_hist": macd_h,
            "adx": adx,
            "dmp": dmp,
            "dmn": dmn,
            "supertrend_dir": st_dir,
        },
        "weight": 1.0,
    }


# ═══════════════════════════════════════════════════════════
# گروه ۳: Volatility — نسخه ۱۰.۰
# ═══════════════════════════════════════════════════════════
def _analyze_volatility(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    reasons = []
    signals = []

    last = df.iloc[-1]
    price = safe_num(last["close"])

    bb_upper = safe_num(last.get("bb_upper"))
    bb_lower = safe_num(last.get("bb_lower"))
    bb_mid = safe_num(last.get("bb_mid"))
    if bb_upper > 0 and bb_lower > 0:
        if price <= bb_lower * 1.005:
            signals.append((+0.8, 1.1))
            reasons.append("نزدیک باند پایین Bollinger")
        elif price >= bb_upper * 0.995:
            signals.append((-0.8, 1.1))
            reasons.append("نزدیک باند بالا Bollinger")
        elif price < bb_mid:
            signals.append((+0.2, 0.6))
        else:
            signals.append((-0.2, 0.6))

    atr = safe_num(last.get("atr"))
    if atr > 0 and price > 0:
        atr_pct = (atr / price) * 100
        reasons.append(f"ATR={atr_pct:.2f}% نوسان")

    kc_upper = safe_num(last.get("kc_upper"))
    kc_lower = safe_num(last.get("kc_lower"))
    if kc_upper > 0 and kc_lower > 0:
        if price <= kc_lower * 1.005:
            signals.append((+0.7, 0.9))
            reasons.append("نزدیک کانال پایین Keltner")
        elif price >= kc_upper * 0.995:
            signals.append((-0.7, 0.9))
            reasons.append("نزدیک کانال بالای Keltner")

    dc_upper = safe_num(last.get("dc_upper"))
    dc_lower = safe_num(last.get("dc_lower"))
    if dc_upper > 0 and dc_lower > 0:
        if price >= dc_upper * 0.998:
            signals.append((-0.6, 0.8))
            reasons.append("نزدیک سقف Donchian")
        elif price <= dc_lower * 1.002:
            signals.append((+0.6, 0.8))
            reasons.append("نزدیک کف Donchian")

    stddev = safe_num(last.get("stddev"))
    if stddev > 0 and price > 0:
        cv = (stddev / price) * 100
        if cv > 3:
            reasons.append(f"نوسان بالا (StdDev={cv:.2f}%)")
        elif cv < 1:
            reasons.append(f"نوسان کم (StdDev={cv:.2f}%)")

    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0

    o_thr = _thresholds[2] if _thresholds else 0.30
    if score > o_thr:
        vote = +1
    elif score < -o_thr:
        vote = -1
    else:
        vote = 0

    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "atr": atr,
            "kc_upper": kc_upper,
            "kc_lower": kc_lower,
            "dc_upper": dc_upper,
            "dc_lower": dc_lower,
            "stddev": stddev,
        },
        "weight": 1.0,
    }


# ═══════════════════════════════════════════════════════════
# گروه ۴: Volume — نسخه ۱۰.۰
# ═══════════════════════════════════════════════════════════
def _analyze_volume(
    df: pd.DataFrame,
    market_type: str = "spot",
    _thresholds: tuple = None,
    orderbook: dict = None,
) -> dict:
    reasons = []
    signals = []

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = safe_num(last["close"])

    # ═══ عمق بازار ═══
    ob_details = {}
    if orderbook and orderbook.get("imbalance") is not None:
        from .orderbook import imbalance_vote

        imb = float(orderbook["imbalance"])
        ob_vote, ob_score = imbalance_vote(imb)
        pressure = orderbook.get("pressure_fa", "")

        ob_details = {
            "imbalance": imb,
            "spread_pct": orderbook.get("spread_pct"),
            "pressure_fa": pressure,
            "best_bid": orderbook.get("best_bid"),
            "best_ask": orderbook.get("best_ask"),
            "wall": orderbook.get("wall"),
        }

        if ob_vote != 0:
            signals.append((ob_score * 0.8, 0.4))
            reasons.append(f"عمق بازار: {pressure} (imbalance={imb:.2f})")

        wall = orderbook.get("wall")
        if wall:
            side_fa = "خرید" if wall["side"] == "bid" else "فروش"
            reasons.append(
                f"🧱 دیوار سفارش {side_fa} در "
                f"{wall['price']:,.2f} ({wall['ratio']:.1f}x میانگین)"
            )

        sp = orderbook.get("spread_pct") or 0
        if sp > 0.5:
            reasons.append(f"⚠️ اسپرد {sp:.2f}٪ — نقدینگی ضعیف")

    has_volume = "volume" in df.columns and df["volume"].sum() > 0

    if not has_volume:
        total_w = sum(w for _, w in signals)
        score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0
        o_thr = _thresholds[2] if _thresholds else 0.25
        vote = +1 if score > o_thr else (-1 if score < -o_thr else 0)
        return {
            "vote": vote,
            "score": round(score, 3),
            "reasons": reasons or ["حجم در دسترس نیست"],
            "details": {**ob_details, "has_volume": False},
            "weight": 1.0,
        }

    # ═══ OBV ═══
    obv_last = safe_num(last.get("obv"))
    obv_prev = safe_num(prev.get("obv"))
    if obv_last > obv_prev:
        signals.append((+0.5, 0.9))
        reasons.append("OBV صعودی (حجم ورودی)")
    elif obv_last < obv_prev:
        signals.append((-0.5, 0.9))
        reasons.append("OBV نزولی (حجم خروجی)")

    # ═══ Volume spike ═══
    vol = safe_num(last.get("volume"))
    vol_ma = safe_num(last.get("vol_ma"))
    vol_ratio = vol / vol_ma if vol_ma > 0 else 1.0

    if vol_ma > 0:
        if vol_ratio > 1.5:
            reasons.append(f"حجم بالا ({vol_ratio:.1f}x میانگین)")
            close_last = safe_num(last["close"])
            close_prev = safe_num(prev["close"])
            if close_last > close_prev:
                signals.append((+0.6, 0.8))
            else:
                signals.append((-0.6, 0.8))
        elif vol_ratio < 0.5:
            reasons.append(f"حجم کم ({vol_ratio:.1f}x میانگین)")

    # ═══ CVD + Delta ═══
    if "cvd" in df.columns:
        cvd_last = safe_num(last.get("cvd"))
        cvd_prev = safe_num(prev.get("cvd"))
        delta_last = safe_num(last.get("delta"))

        if cvd_last > cvd_prev:
            signals.append((+0.5, 0.9))
            reasons.append("CVD صعودی (فشار خرید)")
        elif cvd_last < cvd_prev:
            signals.append((-0.5, 0.9))
            reasons.append("CVD نزولی (فشار فروش)")

        if delta_last > 0:
            signals.append((+0.4, 0.8))
        elif delta_last < 0:
            signals.append((-0.4, 0.8))

        # ─── Z-Score: با وزن کمتر (اصلاح نسخه ۱۰.۰) ───
        # چرا کمتر: در دیتا، cvd_z افراطی باعث سیگنال‌های غلط می‌شد
        cvd_z = safe_num(last.get("cvd_zscore"), 0)
        if cvd_z > 2.5:
            signals.append((-0.5, 0.7))  # کاهش از 0.6→0.5، وزن 1.0→0.7
            reasons.append(f"CVD Z-Score={cvd_z:.1f} اشباع خرید")
        elif cvd_z < -2.5:
            signals.append((+0.5, 0.7))
            reasons.append(f"CVD Z-Score={cvd_z:.1f} اشباع فروش")

    # ═══ CMF ═══
    cmf = safe_num(last.get("cmf"), 0)
    if cmf > 0.1:
        signals.append((+0.7, 1.0))
        reasons.append(f"CMF={cmf:.2f} جریان پول ورودی")
    elif cmf < -0.1:
        signals.append((-0.7, 1.0))
        reasons.append(f"CMF={cmf:.2f} جریان پول خروجی")

    # ═══ MFI ═══
    mfi = safe_num(last.get("mfi"), 50)
    if mfi < 20:
        signals.append((+0.8, 1.0))
        reasons.append(f"MFI={mfi:.0f} اشباع فروش حجمی")
    elif mfi > 80:
        signals.append((-0.8, 1.0))
        reasons.append(f"MFI={mfi:.0f} اشباع خرید حجمی")

    # ═══ VWAP ═══
    if "vwap" in df.columns:
        vwap = safe_num(last.get("vwap"))
        if vwap > 0:
            if price > vwap * 1.02:
                signals.append((-0.4, 0.7))
                reasons.append("قیمت بالای VWAP — ورود دیرهنگام")
            elif price < vwap * 0.98:
                signals.append((+0.4, 0.7))
                reasons.append("قیمت زیر VWAP — فرصت ورود")

    # ═══ Absorption (جذب) ═══
    if "volume" in df.columns and vol_ma > 0:
        candle_range = safe_num(last["high"]) - safe_num(last["low"])
        if candle_range > 0:
            upper_wick = safe_num(last["high"]) - max(
                safe_num(last["close"]), safe_num(last["open"])
            )
            lower_wick = min(
                safe_num(last["close"]), safe_num(last["open"])
            ) - safe_num(last["low"])

            vol_spike = vol > vol_ma * 1.5

            if vol_spike and lower_wick / candle_range > 0.66:
                signals.append((+0.9, 1.3))
                reasons.append("Absorption صعودی (جذب در کف)")
            elif vol_spike and upper_wick / candle_range > 0.66:
                signals.append((-0.9, 1.3))
                reasons.append("Absorption نزولی (جذب در سقف)")

    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0

    o_thr = _thresholds[2] if _thresholds else 0.25
    if score > o_thr:
        vote = +1
    elif score < -o_thr:
        vote = -1
    else:
        vote = 0

    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "obv": obv_last,
            "vol_ratio": vol_ratio,
            "cmf": cmf,
            "mfi": mfi,
            "cvd": safe_num(last.get("cvd")),
            "delta": safe_num(last.get("delta")),
            **ob_details,
        },
        "weight": 1.0,
    }


# ═══════════════════════════════════════════════════════════
# گروه ۵: Structure — بدون تغییر
# ═══════════════════════════════════════════════════════════
def _analyze_structure(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    reasons = []
    signals = []

    last = df.iloc[-1]
    price = safe_num(last["close"])

    pivots = compute_pivot_points(df)
    swings = find_swing_points(df, lookback=50, window=3)
    fib = compute_fibonacci(df, lookback=50)

    if pivots:
        r1 = pivots.get("r1", 0)
        s1 = pivots.get("s1", 0)
        if r1 > 0 and price >= r1 * 0.995:
            signals.append((-0.6, 1.0))
            reasons.append("نزدیک R1 (Pivot)")
        elif s1 > 0 and price <= s1 * 1.005:
            signals.append((+0.6, 1.0))
            reasons.append("نزدیک S1 (Pivot)")

    nearest_r = swings.get("nearest_resistance", 0)
    nearest_s = swings.get("nearest_support", 0)
    if nearest_r > 0 and price > 0:
        dist_r = (nearest_r - price) / price * 100
        if dist_r < 0.5:
            signals.append((-0.8, 1.2))
            reasons.append("نزدیک مقاومت Swing")
    if nearest_s > 0 and price > 0:
        dist_s = (price - nearest_s) / price * 100
        if dist_s < 0.5:
            signals.append((+0.8, 1.2))
            reasons.append("نزدیک حمایت Swing")

    if fib and fib.get("levels"):
        levels = fib["levels"]
        for ratio in ["0.618", "0.500", "0.382"]:
            fib_price = levels.get(ratio, 0)
            if fib_price > 0 and abs(price - fib_price) / price < 0.005:
                signals.append((+0.4, 0.8))
                reasons.append(f"نزدیک Fibonacci {ratio}")
                break

    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0

    o_thr = _thresholds[2] if _thresholds else 0.30
    if score > o_thr:
        vote = +1
    elif score < -o_thr:
        vote = -1
    else:
        vote = 0

    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "pivots": pivots,
            "swings": swings,
            "fibonacci": fib,
            "nearest_resistance": nearest_r,
            "nearest_support": nearest_s,
        },
        "weight": 1.0,
    }


# ═══════════════════════════════════════════════════════════
# واگرایی — بدون تغییر
# ═══════════════════════════════════════════════════════════
def _detect_divergence(momentum: dict, volume: dict) -> dict:
    m_vote = momentum.get("vote", 0)
    v_vote = volume.get("vote", 0)
    m_score = momentum.get("score", 0.0)
    v_score = volume.get("score", 0.0)

    result = {"has_divergence": False, "type": None, "penalty": 0, "reason": ""}

    if m_vote > 0 and v_vote < 0 and abs(v_score) > 0.3:
        result["has_divergence"] = True
        result["type"] = "bull_trap"
        result["penalty"] = 15
        result["reason"] = (
            f"⚠️ واگرایی: مومنتوم صعودی ({m_score:+.2f}) "
            f"ولی جریان پول خروجی ({v_score:+.2f}) — احتمال تله صعودی"
        )
    elif m_vote < 0 and v_vote > 0 and abs(v_score) > 0.3:
        result["has_divergence"] = True
        result["type"] = "bear_trap"
        result["penalty"] = 15
        result["reason"] = (
            f"⚠️ واگرایی: مومنتوم نزولی ({m_score:+.2f}) "
            f"ولی جریان پول ورودی ({v_score:+.2f}) — احتمال تله نزولی"
        )

    return result


# ═══════════════════════════════════════════════════════════
# تشخیص تله‌ها — نسخه ۱۰.۰ (جهت‌دار)
# ═══════════════════════════════════════════════════════════
def _detect_traps(groups: dict, price: float, atr: float) -> dict:
    """
    تشخیص تله‌ها — نسخه ۱۰.۰ (اصلاح‌شده).

    ═══ ریشه‌ی باگ نسخه ۸.۵ ═══
    شرط fake_breakout:
        if adx > 35 and vol_ratio < 0.6 and abs(s_score) > 0.30

    ``abs(s_score)`` هم نزدیک مقاومت و هم نزدیک حمایت رو
    یکسان می‌دید. نتیجه: در دیتای ۳۲۵ سیگنال، ۳۰ بار
    fake_breakout فعال شد که اکثراً غلط بود.

    ═══ اصلاح نسخه ۱۰.۰ ═══
    ``s_score`` جهت‌دار چک می‌شه:
        • s_score < -0.30 → نزدیک مقاومت → fake_breakout صعودی
        • s_score > +0.30 → نزدیک حمایت → fake_breakout نزولی
    """
    traps = {
        "bull_trap": {"active": False, "reason": "", "severity": 0},
        "bear_trap": {"active": False, "reason": "", "severity": 0},
        "fake_breakout": {"active": False, "reason": "", "severity": 0},
        "exhaustion": {"active": False, "reason": "", "severity": 0},
    }

    if not groups:
        return traps

    m = groups.get("momentum", {}) or {}
    t = groups.get("trend", {}) or {}
    v = groups.get("volume", {}) or {}
    s = groups.get("structure", {}) or {}
    vol = groups.get("volatility", {}) or {}

    m_score = m.get("score", 0.0)
    v_score = v.get("score", 0.0)
    s_score = s.get("score", 0.0)
    vol_score = vol.get("score", 0.0)

    t_details = t.get("details", {})
    v_details = v.get("details", {})

    adx = t_details.get("adx", 20)
    vol_ratio = v_details.get("vol_ratio", 1.0)

    # ═══ Bull trap: momentum صعودی ولی volume خروجی + نزدیک مقاومت ═══
    if m_score > 0.35 and v_score < -0.25 and s_score < -0.15:
        traps["bull_trap"] = {
            "active": True,
            "reason": (
                f"⚡ مومنتوم صعودی (score={m_score:+.2f}) ولی جریان پول خروجی "
                f"({v_score:+.2f}) + نزدیک مقاومت — احتمال «تله صعودی»"
            ),
            "severity": 8,
        }

    # ═══ Bear trap: momentum نزولی ولی volume ورودی + نزدیک حمایت ═══
    if m_score < -0.35 and v_score > 0.25 and s_score > 0.15:
        traps["bear_trap"] = {
            "active": True,
            "reason": (
                f"⚡ مومنتوم نزولی (score={m_score:+.2f}) ولی جریان پول ورودی "
                f"({v_score:+.2f}) + نزدیک حمایت — احتمال «تله نزولی»"
            ),
            "severity": 8,
        }

    # ═══ Fake breakout — جهت‌دار (🔴 اصلاح کلیدی) ═══
    if adx > 30 and vol_ratio < 0.6:
        # ─── نزدیک مقاومت: احتمال fake breakout صعودی ───
        if s_score < -0.30:
            traps["fake_breakout"] = {
                "active": True,
                "reason": (
                    f"📉 ADX={adx:.0f} (روند قوی) ولی حجم فقط "
                    f"{vol_ratio:.1f}x میانگین + نزدیک مقاومت "
                    f"— احتمال «شکست جعلی صعودی»"
                ),
                "severity": 7,
            }
        # ─── نزدیک حمایت: احتمال fake breakout نزولی ───
        elif s_score > 0.30:
            traps["fake_breakout"] = {
                "active": True,
                "reason": (
                    f"📈 ADX={adx:.0f} (روند قوی) ولی حجم فقط "
                    f"{vol_ratio:.1f}x میانگین + نزدیک حمایت "
                    f"— احتمال «شکست جعلی نزولی»"
                ),
                "severity": 7,
            }

    # ═══ Exhaustion ═══
    if adx > 45 and abs(m_score) < 0.25 and abs(vol_score) > 0.3:
        traps["exhaustion"] = {
            "active": True,
            "reason": (
                f"😮‍💨 ADX={adx:.0f} (روند قوی) ولی مومنتوم ضعیف "
                f"({m_score:+.2f}) — روند در حال «خستگی»"
            ),
            "severity": 6,
        }

    return traps


def _traps_summary(traps: dict) -> dict:
    active = [k for k, v in traps.items() if v.get("active")]
    max_severity = max((v.get("severity", 0) for v in traps.values()), default=0)

    return {
        "active_count": len(active),
        "active_names": active,
        "max_severity": max_severity,
        "has_high_risk": max_severity >= 7,
        "has_warning": max_severity >= 5,
    }


# ═══════════════════════════════════════════════════════════
# سناریوساز — بدون تغییر ساختاری
# ═══════════════════════════════════════════════════════════
def build_scenarios(
    price: float,
    atr: float,
    groups: dict,
    support: float,
    resistance: float,
    regime: str,
    direction: str = "neutral",
    traps: dict = None,
    ticker: str = "",
) -> list[dict]:
    scenarios = []

    if not groups:
        return scenarios

    is_iranian = _is_iranian_ticker(ticker)
    is_tsetmc = bool(ticker) and not ticker[0].isascii()

    if is_tsetmc:
        unit = "ریال"
    elif is_iranian:
        unit = "تومان"
    else:
        unit = "$"

    m = groups.get("momentum", {}) or {}
    t = groups.get("trend", {}) or {}
    v = groups.get("volume", {}) or {}

    m_score = m.get("score", 0.0)
    v_score = v.get("score", 0.0)
    m_details = m.get("details", {})
    t_details = t.get("details", {})

    rsi = m_details.get("rsi", 50)
    adx = t_details.get("adx", 20)

    def _fmt(val):
        if is_iranian:
            return f"{val:,.0f} {unit}"
        return f"${val:,.2f}"

    if regime == "trend" and adx > 35 and price > 0 and atr > 0:
        if direction == "neutral" and m_score < 0.3 and v_score < 0.3:
            sl = price - atr * 1.2
            scenarios.append(
                {
                    "condition": f"اگه حجم بالاتر بره و RSI از {rsi:.0f} بالاتر بره",
                    "action": f"ورود LONG — SL={_fmt(sl)}",
                    "probability": 0.55,
                    "color": "green",
                    "type": "entry",
                    "icon": "🟢",
                }
            )
        elif direction == "long":
            sl = price - atr * 1.2
            tp = price + atr * 3.0
            scenarios.append(
                {
                    "condition": "اگه حجم تأیید کنه و RSI بالای ۵۰ بره",
                    "action": f"LONG با SL={_fmt(sl)} · TP={_fmt(tp)}",
                    "probability": 0.65,
                    "color": "green",
                    "type": "entry",
                    "icon": "🟢",
                }
            )

    if resistance > 0 and price > 0:
        dist_r = (resistance - price) / price * 100
        if dist_r < 1.5:
            scenarios.append(
                {
                    "condition": f"اگه قیمت از R ({_fmt(resistance)}) رد نشه",
                    "action": "مراقب باش — احتمال برگشت یا شکست",
                    "probability": 0.55,
                    "color": "red",
                    "type": "reversal",
                    "icon": "🔴",
                }
            )
        elif dist_r < 3.0:
            scenarios.append(
                {
                    "condition": f"اگه قیمت با حجم بالا از {_fmt(resistance)} رد بشه",
                    "action": "ورود LONG بعد از تأیید حجم",
                    "probability": 0.50,
                    "color": "green",
                    "type": "breakout",
                    "icon": "🚀",
                }
            )

    if support > 0 and price > 0:
        dist_s = (price - support) / price * 100
        if dist_s < 1.5:
            scenarios.append(
                {
                    "condition": f"اگه قیمت به حمایت ({_fmt(support)}) برسه",
                    "action": "فرصت خرید — SL زیر حمایت",
                    "probability": 0.60,
                    "color": "green",
                    "type": "entry",
                    "icon": "💚",
                }
            )

    if traps and traps.get("fake_breakout", {}).get("active"):
        scenarios.append(
            {
                "condition": "اگه قیمت سریع برگرده داخل محدوده",
                "action": "شکست جعلیه — منتظر تأیید بمون",
                "probability": 0.70,
                "color": "yellow",
                "type": "warning",
                "icon": "⚠️",
            }
        )

    if traps and traps.get("bull_trap", {}).get("active"):
        scenarios.append(
            {
                "condition": "اگه قیمت ناگهان برگرده پایین",
                "action": "تله صعودیه — وارد LONG نشو",
                "probability": 0.65,
                "color": "red",
                "type": "warning",
                "icon": "🚨",
            }
        )

    if traps and traps.get("bear_trap", {}).get("active"):
        scenarios.append(
            {
                "condition": "اگه قیمت ناگهان برگرده بالا",
                "action": "تله نزولیه — وارد SHORT نشو",
                "probability": 0.65,
                "color": "red",
                "type": "warning",
                "icon": "🚨",
            }
        )

    if len(scenarios) < 2:
        scenarios.append(
            {
                "condition": "اگه شرایط فعلی ادامه داشته باشه",
                "action": "صبر کن — بازار سیگنال واضحی نداره",
                "probability": 0.70,
                "color": "yellow",
                "type": "wait",
                "icon": "⏸",
            }
        )

    scenarios.sort(key=lambda x: -x["probability"])
    return scenarios[:3]


# ═══════════════════════════════════════════════════════════
# 🎯 Trend Override — هسته‌ی اصلاح فاز ۱۰.۱
# ═══════════════════════════════════════════════════════════
def _apply_trend_override(
    direction: str,
    aggregate: dict,
    groups: dict,
    regime: str,
) -> tuple[str, int, str]:
    """
    اگه روند قوی باشه، سیگنال مخالف رو بلاک یا تنبیه می‌کنه.

    ═══ چرا حیاتی ═══
    در دیتای ۳۲۵ سیگنال:
        trend_correct=True  →  ۱۰۰٪ برد (۱۰/۱۰)
        trend_correct=False →  ۱۰۰٪ باخت (۲۹/۲۹)

    یعنی وقتی trend engine درست می‌گه، سیگنال نهایی باید هم‌جهت
    باهاش باشه. نسخه ۸.۵ این کار رو نمی‌کرد.

    ═══ منطق ═══
      • trend_score >= +0.65 → bull قوی
      • trend_score <= -0.65 → bear قوی
      • اگر direction مخالف trend قوی:
          - با momentum هم‌جهت با trend: بلاک کامل
          - بدون momentum تأیید: نصف confidence

    Returns:
        (new_direction, penalty_pct, override_reason)
    """
    trend = groups.get("trend", {}) or {}
    momentum = groups.get("momentum", {}) or {}

    trend_score = trend.get("score", 0.0)
    momentum_score = momentum.get("score", 0.0)

    # ─── آستانه‌ی روند قوی ───
    STRONG_TREND = 0.65
    MEDIUM_TREND = 0.45

    override_reason = ""
    penalty = 0

    trend_bull = trend_score >= STRONG_TREND
    trend_bear = trend_score <= -STRONG_TREND

    if not (trend_bull or trend_bear):
        # ─── روند قوی نیست → فقط تنبیه نرم ───
        if trend_score >= MEDIUM_TREND and direction == "short":
            return direction, 25, "⚠️ روند صعودی متوسط ولی SHORT — کاهش اطمینان"
        if trend_score <= -MEDIUM_TREND and direction == "long":
            return direction, 25, "⚠️ روند نزولی متوسط ولی LONG — کاهش اطمینان"
        return direction, 0, ""

    # ═══ روند قوی = bull ═══
    if trend_bull and direction == "short":
        # ─── آيا momentum هم صعودی؟ (تأیید دوگانه) ───
        if momentum_score >= 0.30:
            # ─── بلاک کامل ───
            return (
                "neutral",
                0,
                f"🚫 SHORT بلاک شد — روند قوی صعودی (trend={trend_score:+.2f}) "
                f"و مومنتوم تأییدکننده ({momentum_score:+.2f})",
            )
        else:
            # ─── فقط تنبیه شدید ───
            return (
                direction,
                60,
                f"⚠️ روند قوی صعودی (trend={trend_score:+.2f}) ولی SHORT صادر شده "
                f"— کاهش شدید اطمینان",
            )

    # ═══ روند قوی = bear ═══
    if trend_bear and direction == "long":
        if momentum_score <= -0.30:
            return (
                "neutral",
                0,
                f"🚫 LONG بلاک شد — روند قوی نزولی (trend={trend_score:+.2f}) "
                f"و مومنتوم تأییدکننده ({momentum_score:+.2f})",
            )
        else:
            return (
                direction,
                60,
                f"⚠️ روند قوی نزولی (trend={trend_score:+.2f}) ولی LONG صادر شده "
                f"— کاهش شدید اطمینان",
            )

    return direction, 0, ""


# ═══════════════════════════════════════════════════════════
# رأی‌گیری — نسخه ۱۰.۰
# ═══════════════════════════════════════════════════════════
def _aggregate_votes(
    groups: dict,
    regime: str,
    profile: str,
    adx: float,
    market_type: str = "spot",
    tf_hint: str = "۵ دقیقه",
) -> dict:
    """
    رأی‌گیری وزنی — نسخه ۱۰.۰.

    ═══ تغییرات ═══
      • Trend Override بعد از شمارش آرا اعمال می‌شه
      • آستانه‌ی رأی منطقی‌تر (بر اساس profile)
      • min_votes_required از profile config میاد
    """
    weights = _regime_weights(regime)

    weighted_sum = 0.0
    total_weight = 0.0
    votes_long = 0
    votes_short = 0
    votes_neutral = 0
    groups_summary = {}

    for group_name, result in groups.items():
        if result is None:
            continue
        w = weights.get(group_name, 1.0)
        vote = result.get("vote", 0)
        score = result.get("score", 0.0)

        weighted_sum += score * w
        total_weight += w

        if vote > 0:
            votes_long += 1
        elif vote < 0:
            votes_short += 1
        else:
            votes_neutral += 1

        strength_key, strength_fa = _group_strength(score)
        groups_summary[group_name] = {
            "vote": vote,
            "score": score,
            "weight": w,
            "strength": strength_key,
            "strength_fa": strength_fa,
            "reasons": result.get("reasons", []),
        }

    final_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    # ═══ Regime multiplier ═══
    if regime == "trend":
        final_score *= 1.2
    elif regime == "range":
        final_score *= 0.85  # ← نرم‌تر (بود 0.7)

    # ═══ پروفایل ═══
    profile_key = f"{profile}_{market_type}"
    profile_cfg = RISK_PROFILES.get(
        profile_key,
        RISK_PROFILES.get(f"{profile}_spot", RISK_PROFILES["aggressive_spot"]),
    )

    # ═══ آستانه‌ی رأی ═══
    if tf_hint in ("۱ دقیقه", "۵ دقیقه"):
        _tf_threshold = 1
    elif tf_hint in ("۱۵ دقیقه", "۳۰ دقیقه"):
        _tf_threshold = 2
    else:
        _tf_threshold = 2

    min_votes = profile_cfg.get("min_votes_required", _tf_threshold)
    required_votes = max(min_votes, _tf_threshold)

    min_adx = profile_cfg.get("min_adx", 0)
    adx_ok = adx >= min_adx

    # ═══ تعیین جهت ═══
    if profile == "aggressive":
        if votes_long >= required_votes and votes_long > votes_short:
            direction = "long"
            consensus = (
                "weak"
                if votes_long <= required_votes
                else ("normal" if votes_long <= required_votes + 1 else "strong")
            )
        elif votes_short >= required_votes and votes_short > votes_long:
            direction = "short"
            consensus = (
                "weak"
                if votes_short <= required_votes
                else ("normal" if votes_short <= required_votes + 1 else "strong")
            )
        else:
            direction = "neutral"
            consensus = "neutral"
    else:
        # محتاطانه
        if not adx_ok:
            direction = "neutral"
            consensus = "neutral"
        elif votes_long >= required_votes and votes_long > votes_short:
            direction = "long"
            consensus = "normal" if votes_long == required_votes else "strong"
        elif votes_short >= required_votes and votes_short > votes_long:
            direction = "short"
            consensus = "normal" if votes_short == required_votes else "strong"
        else:
            direction = "neutral"
            consensus = "neutral"

    # ─── اسپات: SHORT غیرمجاز ───
    if market_type == "spot" and direction == "short":
        direction = "neutral"
        consensus = "neutral"

    # ═══ 🔴 Trend Override ═══
    direction, penalty, override_reason = _apply_trend_override(
        direction, {"final_score": final_score}, groups, regime
    )

    return {
        "final_score": round(final_score, 3),
        "votes_long": votes_long,
        "votes_short": votes_short,
        "votes_neutral": votes_neutral,
        "consensus": consensus,
        "direction": direction,
        "required_votes": required_votes,
        "adx_ok": adx_ok,
        "groups_summary": groups_summary,
        "override_reason": override_reason,
        "override_penalty_pct": penalty,
    }


# ═══════════════════════════════════════════════════════════
# Confidence — نسخه ۱۰.۰ (بازطراحی کامل)
# ═══════════════════════════════════════════════════════════
def _compute_confidence(
    aggregate: dict,
    adx: float,
    divergence: dict,
    groups: dict = None,
) -> int:
    """
    Confidence — نسخه ۱۰.۰.

    ═══ چرا بازطراحی ═══
    در دیتای ۳۲۵ سیگنال:
        Confidence 60-79 → WR: ۰٪   ← بدترین
        Confidence 40-49 → WR: ۳۹٪  ← بهترین

    پس confidence قبلی معکوس بود. علت: بر اساس **تعداد رأی**
    محاسبه می‌شد، نه **کیفیت** سیگنال.

    ═══ نسخه ۱۰.۰ ═══
    confidence = 3 جزء:
        ۱. base = f(consensus, votes)              (۰-۵۰)
        ۲. quality = f(trend_strength, momentum, adx) (۰-۳۵)
        ۳. agreement = f(هم‌جهتی گروه‌ها)          (۰-۱۵)

    ═══ اثر ═══
    سیگنال با trend قوی و مومنتوم هم‌جهت = confidence بالا
    سیگنال با گروه‌های متناقض = confidence پایین
    """
    consensus = aggregate.get("consensus", "neutral")
    direction = aggregate.get("direction", "neutral")
    votes_long = aggregate.get("votes_long", 0)
    votes_short = aggregate.get("votes_short", 0)
    votes_neutral = aggregate.get("votes_neutral", 0)
    final_score = aggregate.get("final_score", 0.0)

    if direction == "neutral" or consensus == "neutral":
        return 0

    # ═══ ۱. base — بر اساس consensus ═══
    base_map = {"strong": 45, "normal": 32, "weak": 18}
    base = base_map.get(consensus, 0)

    # ═══ ۲. quality — بر اساس کیفیت سیگنال ═══
    quality = 0

    # ─── ۲.۱ شیب final_score ───
    quality += min(15, abs(final_score) * 20)

    # ─── ۲.۲ ADX ───
    if adx > 40:
        quality += 8
    elif adx > 30:
        quality += 5
    elif adx > 25:
        quality += 2
    elif adx < 18:
        quality -= 5

    # ─── ۲.۳ trend + momentum هم‌جهت (اگه groups داریم) ───
    if groups:
        t = groups.get("trend", {}) or {}
        m = groups.get("momentum", {}) or {}
        v = groups.get("volume", {}) or {}

        t_score = t.get("score", 0.0)
        m_score = m.get("score", 0.0)
        v_score = v.get("score", 0.0)

        if direction == "long":
            # ─── همه صعودی ───
            if t_score > 0.3 and m_score > 0.3 and v_score > 0.2:
                quality += 12
            elif t_score > 0.3 and m_score > 0.2:
                quality += 8
            elif t_score > 0.3 or m_score > 0.3:
                quality += 4
        elif direction == "short":
            if t_score < -0.3 and m_score < -0.3 and v_score < -0.2:
                quality += 12
            elif t_score < -0.3 and m_score < -0.2:
                quality += 8
            elif t_score < -0.3 or m_score < -0.3:
                quality += 4

    quality = max(0, min(35, quality))

    # ═══ ۳. agreement — بر اساس همرأیی ═══
    if direction == "long":
        majority = votes_long
    else:
        majority = votes_short

    agreement = 0
    if majority >= 4:
        agreement = 15
    elif majority == 3:
        agreement = 10
    elif majority == 2:
        agreement = 5

    # ═══ جمع ═══
    confidence = base + quality + agreement

    # ═══ تنبیه واگرایی ═══
    if divergence.get("has_divergence"):
        confidence -= divergence.get("penalty", 0)

    # ═══ تنبیه trend override ═══
    override_penalty = aggregate.get("override_penalty_pct", 0)
    if override_penalty > 0:
        confidence = int(confidence * (1 - override_penalty / 100))

    return max(0, min(100, int(confidence)))


# ═══════════════════════════════════════════════════════════
# توضیح خنثی
# ═══════════════════════════════════════════════════════════
def _explain_neutral(
    aggregate: dict,
    regime: str,
    divergence: dict,
    market_type: str = "spot",
    tfs_data: dict = None,
    current_tf: str = None,
    traps: dict = None,
) -> dict:
    votes_long = aggregate.get("votes_long", 0)
    votes_short = aggregate.get("votes_short", 0)
    votes_neutral = aggregate.get("votes_neutral", 0)

    override_reason = aggregate.get("override_reason", "")

    if override_reason:
        short_msg = "🚫 روند قوی — سیگنال مخالف بلاک شد"
    elif votes_neutral >= 3:
        short_msg = f"⚪ بدون سیگنال — {votes_neutral} گروه خنثی"
    elif votes_long == votes_short and votes_long > 0:
        short_msg = "⚪ تعادل گروه‌ها — بدون جهت مشخص"
    else:
        short_msg = "⚪ بدون سیگنال معتبر"

    reasons = []
    if override_reason:
        reasons.append(override_reason)
    if regime == "range":
        reasons.append("بازار در رژیم «رنج» هست")
    elif regime == "transitional":
        reasons.append("بازار در حالت «گذار» هست")
    elif regime == "trend":
        reasons.append("بازار روند داره ولی گروه‌ها هم‌جهت نیستن")

    if votes_neutral >= 3:
        reasons.append(f"{votes_neutral} از ۵ گروه خنثی موندن")
    if votes_long == votes_short and votes_long > 0:
        reasons.append(
            f"{votes_long} گروه صعودی مقابل {votes_short} گروه نزولی — تعادل"
        )
    if votes_long < 2 and votes_short < 2 and not override_reason:
        reasons.append("کمتر از ۲ گروه هم‌جهت هستن")
    if divergence.get("has_divergence"):
        reasons.append("واگرایی مومنتوم/حجم دیده می‌شه")
    if market_type == "spot" and votes_short > votes_long:
        reasons.append("در اسپات فقط خرید مجاز است")

    if not reasons:
        reasons.append("شرایط بازار نامشخصه")

    long_msg = " • ".join(reasons)

    hint = None
    if tfs_data and current_tf:
        higher_tfs_with_signal = []
        for higher_tf in ["۱ ساعت", "روزانه"]:
            if higher_tf == current_tf:
                continue
            r = tfs_data.get(higher_tf)
            if r and SigEnum.is_directional(r.get("signal", "")):
                conf = r.get("confidence", 0)
                sig = r.get("signal", "")
                higher_tfs_with_signal.append(f"{higher_tf} ({sig} · {conf}%)")

        if higher_tfs_with_signal:
            hint = "💡 TF بالاتر سیگنال داره: " + " | ".join(higher_tfs_with_signal)

    if traps:
        active_traps = [k for k, v in traps.items() if v.get("active")]
        if active_traps:
            trap_warnings = [traps[t_key].get("reason", "") for t_key in active_traps]
            if trap_warnings:
                trap_msg = "🚨 هشدار: " + " | ".join(trap_warnings)
                hint = (hint + "\n" + trap_msg) if hint else trap_msg

    return {
        "short": short_msg,
        "long": long_msg,
        "hint": hint,
        "traps": traps or {},
    }


# ═══════════════════════════════════════════════════════════
# تابع اصلی تحلیل
# ═══════════════════════════════════════════════════════════
def analyze_symbol(
    df: pd.DataFrame,
    risk_profile: str = "aggressive",
    tf_name: str = "۵ دقیقه",
    tfs_data: dict = None,
    market_type: str = "spot",
    ticker: str = "",
    source: str = "nobitex",
    orderbook: dict = None,
) -> dict | None:
    """
    تحلیل نماد — تابع اصلی. نسخه ۱۰.۰
    """
    if df is None or df.empty:
        return None

    n_candles = len(df)
    if n_candles < 50:
        return None

    try:
        df = compute_indicators(df)
        if df is None or df.empty:
            return None

        last = df.iloc[-1]
        price = safe_num(last["close"])
        atr = safe_num(last.get("atr"))
        adx = safe_num(last.get("adx"), 20)
        bb_width_pct = safe_num(last.get("bb_width_pct"), None)

        # ─── volume ratio برای رژیم ───
        vol = safe_num(last.get("volume"))
        vol_ma = safe_num(last.get("vol_ma"))
        vol_ratio = vol / vol_ma if vol_ma > 0 else 1.0

        # ═══ رژیم — نسخه ۱۰.۰ ═══
        regime = classify_regime(
            adx,
            bb_width_pct=bb_width_pct,
            volume_ratio=vol_ratio,
        )
        thresholds = get_adaptive_thresholds(regime, adx)

        # ═══ ۵ گروه ═══
        groups = {
            "momentum": _analyze_momentum(df, _thresholds=thresholds),
            "trend": _analyze_trend(df, _thresholds=thresholds),
            "volatility": _analyze_volatility(df, _thresholds=thresholds),
            "volume": _analyze_volume(
                df, market_type, _thresholds=thresholds, orderbook=orderbook
            ),
            "structure": _analyze_structure(df, _thresholds=thresholds),
        }

        # ═══ 🔴 فاز ۱۰.۳ — Pre-breakout detection ═══
        # ─── نیاز به nearest_resistance/support از groups structure ───
        structure_details = groups["structure"].get("details", {})
        df_with_levels = df.copy()
        df_with_levels["nearest_resistance"] = structure_details.get(
            "nearest_resistance", 0
        )
        df_with_levels["nearest_support"] = structure_details.get("nearest_support", 0)

        try:
            pre_breakout = detect_pre_breakout(df_with_levels)
        except Exception as e:
            logger.debug(f"[Analyzer] pre_breakout: {e!r}")
            pre_breakout = {
                "is_pre_breakout": False,
                "score": 0,
                "direction_bias": "neutral",
                "reasons": [],
                "details": {},
            }

        aggregate = _aggregate_votes(
            groups, regime, risk_profile, adx, market_type, tf_name
        )
        divergence = _detect_divergence(groups["momentum"], groups["volume"])

        traps = _detect_traps(groups, price, atr)
        traps_summary = _traps_summary(traps)

        trap_penalty = 0
        if traps_summary["has_high_risk"]:
            trap_penalty = 10
        elif traps_summary["has_warning"]:
            trap_penalty = 5

        adjusted_score = aggregate["final_score"]

        # ═══ Confidence — نسخه ۱۰.۰ ═══
        confidence = _compute_confidence(aggregate, adx, divergence, groups)
        if trap_penalty > 0:
            confidence = max(0, confidence - trap_penalty)
        tier = _confidence_tier(confidence)

        # ═══ Multi-TF Confluence ═══
        multi_tf_ok = True
        multi_tf_info = "بدون بررسی"
        if tfs_data:
            direction = aggregate["direction"]
            if direction != "neutral":
                higher_signals = []
                for tf_check in ["۱ ساعت", "روزانه"]:
                    if tf_check in tfs_data and tf_check != tf_name:
                        r = tfs_data[tf_check]
                        if r:
                            sig = r.get("signal", "")
                            if SigEnum.is_long(sig):
                                higher_signals.append(+1)
                            elif SigEnum.is_short(sig):
                                higher_signals.append(-1)
                            else:
                                higher_signals.append(0)

                if higher_signals:
                    if direction == "long":
                        confirms = sum(1 for s in higher_signals if s > 0)
                    else:
                        confirms = sum(1 for s in higher_signals if s < 0)

                    if confirms >= 2:
                        multi_tf_info = (
                            f"✅ تأیید {confirms}/{len(higher_signals)} TF بالاتر"
                        )
                    elif confirms == 1:
                        multi_tf_info = f"⚠️ تأیید ۱/{len(higher_signals)} TF بالاتر"
                        multi_tf_ok = False
                    else:
                        multi_tf_info = "❌ عدم تأیید TF های بالاتر"
                        multi_tf_ok = False

        # ═══ Multi-TF boost ═══
        if tfs_data and aggregate["direction"] != "neutral":
            direction_agg = aggregate["direction"]
            higher_confirms = 0
            higher_total = 0

            for tf_check in ["۱ ساعت", "روزانه"]:
                if tf_check in tfs_data and tf_check != tf_name:
                    r = tfs_data[tf_check]
                    if r:
                        higher_total += 1
                        sig = r.get("signal", "")
                        if direction_agg == "long" and SigEnum.is_long(sig):
                            higher_confirms += 1
                        elif direction_agg == "short" and SigEnum.is_short(sig):
                            higher_confirms += 1

            if higher_total > 0:
                if higher_confirms == higher_total:
                    confidence = min(100, int(confidence * 1.15))
                elif higher_confirms >= higher_total / 2:
                    confidence = min(100, int(confidence * 1.08))
                elif higher_confirms == 0:
                    confidence = int(confidence * 0.75)

                tier = _confidence_tier(confidence)

        if not multi_tf_ok and aggregate["direction"] != "neutral":
            confidence = int(confidence * 0.9)
            tier = _confidence_tier(confidence)

        # ═══ Microstructure Boost ═══
        if (
            aggregate["direction"] != "neutral"
            and orderbook
            and orderbook.get("imbalance") is not None
        ):
            ob_boost = 0
            imb = orderbook.get("imbalance", 0.5)
            direction_agg = aggregate["direction"]

            if direction_agg == "long" and imb > 0.6:
                ob_boost += 10
            elif direction_agg == "short" and imb < 0.4:
                ob_boost += 10
            elif direction_agg == "long" and imb < 0.4:
                ob_boost -= 15
            elif direction_agg == "short" and imb > 0.6:
                ob_boost -= 15

            try:
                if vol_ma > 0 and vol > vol_ma * 1.5:
                    ob_boost += 5
            except Exception:
                pass

            if ob_boost != 0:
                confidence = max(0, min(100, confidence + ob_boost))
                tier = _confidence_tier(confidence)

        # ═══ تعیین سیگنال ═══
        direction = aggregate["direction"]
        profile_key = f"{risk_profile}_{market_type}"
        profile = RISK_PROFILES.get(
            profile_key,
            RISK_PROFILES.get(f"{risk_profile}_spot", RISK_PROFILES["aggressive_spot"]),
        )
        min_conf = profile["min_confidence"]
        consensus = aggregate.get("consensus", "neutral")
        allow_short = profile.get("allow_short", True)

        neutral_explain_dict = {}
        if direction == "neutral" or confidence < min_conf:
            neutral_explain_dict = _explain_neutral(
                aggregate,
                regime,
                divergence,
                market_type,
                tfs_data=tfs_data,
                current_tf=tf_name,
                traps=traps,
            )

        if direction == "neutral":
            signal = "خنثی"
            explanation = neutral_explain_dict.get("short", "بدون سیگنال معتبر")
        elif confidence < min_conf:
            signal = "خنثی"
            explanation = neutral_explain_dict.get(
                "short", f"اطمینان کافی نیست ({confidence}% < {min_conf}%)"
            )
        elif direction == "long":
            if tier == "strong":
                signal = "LONG"
                explanation = "سیگنال خرید قوی — با حد ضرر"
            elif tier == "normal":
                signal = "LONG"
                explanation = "سیگنال خرید معمولی"
            else:
                signal = "LONG ضعیف"
                explanation = "سیگنال خرید ضعیف — با احتیاط"
        elif direction == "short":
            if not allow_short:
                signal = "خنثی"
                explanation = "🔴 در اسپات نمی‌تونی بفروشی — صبر کن"
            elif tier == "strong":
                signal = "SHORT"
                explanation = "سیگنال فروش قوی"
            elif tier == "normal":
                signal = "SHORT"
                explanation = "سیگنال فروش معمولی"
            else:
                signal = "SHORT ضعیف"
                explanation = "سیگنال فروش ضعیف — با احتیاط"
        else:
            signal = "خنثی"
            explanation = "بدون سیگنال"

        if market_type == "spot":
            if SigEnum.is_long(signal):
                action_fa = "🟢 بخر — بعداً بفروش"
            elif SigEnum.is_short(signal):
                action_fa = "🔴 فروش در اسپات معنی نداره"
            else:
                action_fa = "⚪ صبر کن"
        else:
            if SigEnum.is_long(signal):
                action_fa = "🟢 LONG بزن"
            elif SigEnum.is_short(signal):
                action_fa = "🔴 SHORT بزن"
            else:
                action_fa = "⚪ صبر کن"

        # ═══ SL/TP ═══
        sl_tp = None
        rr = None
        fee_warning = None
        is_directional = SigEnum.is_directional(signal)

        if market_type == "spot" and SigEnum.is_short(signal):
            is_directional = False

        _soft_rr_net = None

        if atr > 0 and is_directional:
            tf_mult = get_tf_atr_mult(tf_name)
            effective_sl_mult = profile["sl_mult"] * tf_mult
            effective_tp_mult = profile["tp_mult"] * tf_mult

            if SigEnum.is_long(signal):
                sl = price - atr * effective_sl_mult
                tp = price + atr * effective_tp_mult
                sl_tp = {
                    "sl": sl,
                    "tp": tp,
                    "type": "LONG",
                    "tf_mult": tf_mult,
                    "effective_sl_mult": effective_sl_mult,
                    "effective_tp_mult": effective_tp_mult,
                }
            elif SigEnum.is_short(signal) and market_type == "futures":
                sl = price + atr * effective_sl_mult
                tp = price - atr * effective_tp_mult
                sl_tp = {
                    "sl": sl,
                    "tp": tp,
                    "type": "SHORT",
                    "tf_mult": tf_mult,
                    "effective_sl_mult": effective_sl_mult,
                    "effective_tp_mult": effective_tp_mult,
                }

            if sl_tp:
                base_fee = get_fee_rate(
                    source or "nobitex",
                    market_type=market_type,
                    ticker=ticker,
                )

                if orderbook and orderbook.get("spread_pct") is not None:
                    from .orderbook import execution_cost_pct

                    cost = execution_cost_pct(orderbook["spread_pct"], base_fee)
                    fee_rate = cost["total_pct"] / 100
                    execution_cost = cost
                else:
                    fee_rate = base_fee
                    execution_cost = None

                MIN_COST_RATIO = 8.0
                min_total_pct = (
                    execution_cost["total_pct"] * MIN_COST_RATIO
                    if execution_cost
                    else 0
                )
                actual_total_pct = (
                    (abs(price - sl_tp["sl"]) + abs(sl_tp["tp"] - price)) / price * 100
                )

                scaled = False
                if min_total_pct > 0 and actual_total_pct < min_total_pct:
                    scale = min_total_pct / actual_total_pct
                    scale = min(scale, 10.0)

                    if SigEnum.is_long(signal):
                        sl_tp["sl"] = price - abs(price - sl_tp["sl"]) * scale
                        sl_tp["tp"] = price + abs(sl_tp["tp"] - price) * scale
                    else:
                        sl_tp["sl"] = price + abs(sl_tp["sl"] - price) * scale
                        sl_tp["tp"] = price - abs(price - sl_tp["tp"]) * scale

                    sl_tp["sl_tp_scaled"] = True
                    sl_tp["scale_factor"] = round(scale, 2)
                    sl_tp["original_sl"] = sl
                    sl_tp["original_tp"] = tp
                    sl_tp["scale_reason"] = (
                        f"ATR این تایم‌فریم از هزینه‌ی معامله کوچک‌تر بود"
                    )
                    scaled = True

                TF_MIN_SL_PCT = {
                    "۱ دقیقه": 0.4,
                    "۵ دقیقه": 0.6,
                    "۱۵ دقیقه": 0.9,
                    "۳۰ دقیقه": 1.2,
                    "۱ ساعت": 1.6,
                    "روزانه": 2.5,
                }
                tf_min_sl_pct = TF_MIN_SL_PCT.get(tf_name, 1.0)
                sl_dist_pct = abs(price - sl_tp["sl"]) / price * 100
                if sl_dist_pct < tf_min_sl_pct:
                    scale_tf = tf_min_sl_pct / sl_dist_pct

                    if SigEnum.is_long(signal):
                        sl_tp["sl"] = price - abs(price - sl_tp["sl"]) * scale_tf
                        sl_tp["tp"] = price + abs(sl_tp["tp"] - price) * scale_tf
                    else:
                        sl_tp["sl"] = price + abs(sl_tp["sl"] - price) * scale_tf
                        sl_tp["tp"] = price - abs(price - sl_tp["tp"]) * scale_tf

                    prev_factor = sl_tp.get("scale_factor", 1.0)
                    sl_tp["sl_tp_scaled"] = True
                    sl_tp["scale_factor"] = round(prev_factor * scale_tf, 2)
                    if "original_sl" not in sl_tp:
                        sl_tp["original_sl"] = sl
                        sl_tp["original_tp"] = tp
                    sl_tp["scale_reason"] = (
                        f"حداقل فاصله‌ی SL برای «{tf_name}» برآورده نشده بود"
                    )
                    scaled = True

                fee_stats = compute_net_rr(price, sl_tp["sl"], sl_tp["tp"], fee_rate)

                rr = fee_stats.get("rr_gross")
                sl_tp.update(fee_stats)
                sl_tp["fee_rate"] = fee_rate
                sl_tp["fee_rate_base"] = base_fee
                if execution_cost:
                    sl_tp["execution_cost"] = execution_cost

                if not fee_stats.get("is_worthwhile", True):
                    extra = f" (شامل کارمزد+اسپرد+اسلیپیج)" if execution_cost else ""
                    scale_note = " · حد ضرر/هدف بزرگ‌تر شد" if scaled else ""
                    fee_warning = (
                        f"⚠️ R:R خالص {fee_stats['rr_net']:.2f} "
                        f"(خام {fee_stats['rr_gross']:.2f}) — "
                        f"هزینه‌ی معامله {fee_stats['fee_pct']:.2f}٪{extra} "
                        f"({fee_stats['rr_decay_pct']:.0f}٪ از R:R را می‌خورد)"
                        f"{scale_note}"
                    )
                elif scaled:
                    fee_warning = (
                        f"ℹ️ حد ضرر/هدف بزرگ‌تر شد تا با هزینه‌ی "
                        f"{fee_stats['fee_pct']:.2f}٪ معامله معنادار بماند "
                        f"(R:R خالص {fee_stats['rr_net']:.2f})"
                    )
                else:
                    fee_warning = None

                _soft_rr_net = fee_stats.get("rr_net")

        # ═══ جمع‌آوری دلایل ═══
        all_reasons = []
        for g_name, g_res in groups.items():
            if g_res:
                for r in g_res.get("reasons", []):
                    all_reasons.append(r)

        if fee_warning:
            all_reasons.insert(0, fee_warning)

        if divergence.get("has_divergence"):
            all_reasons.insert(0, divergence["reason"])

        if aggregate.get("override_reason"):
            all_reasons.insert(0, aggregate["override_reason"])

        # ═══ Fee-Adjusted Confidence ═══
        if _soft_rr_net is not None and is_directional:
            if _soft_rr_net < 0.8:
                signal = "خنثی"
                direction = "neutral"
                action_fa = "⚪ صبر کن — R:R خالص پایین"
                explanation = f"R:R خالص {_soft_rr_net:.2f} — معامله ضررده است"
                all_reasons.insert(
                    0, f"🚫 R:R خالص {_soft_rr_net:.2f} — معامله صرف نمی‌کند"
                )
                confidence = 0
                tier = "neutral"
            elif _soft_rr_net < 1.0:
                confidence = int(confidence * 0.7)
                tier = _confidence_tier(confidence)
                all_reasons.insert(0, f"⚠️ R:R خالص {_soft_rr_net:.2f} پایین — احتیاط")
            elif _soft_rr_net < 1.3:
                confidence = int(confidence * 0.9)
                tier = _confidence_tier(confidence)

        if _soft_rr_net is not None and is_directional:
            if _soft_rr_net < 0.8:
                confidence = int(confidence * 0.5)
                tier = _confidence_tier(confidence)
            elif _soft_rr_net < 1.2:
                confidence = int(confidence * 0.8)
                tier = _confidence_tier(confidence)

            if confidence < min_conf and signal != "خنثی":
                signal = "خنثی"
                direction = "neutral"
                action_fa = "⚪ صبر کن — R:R پایین"
                explanation = (
                    f"R:R خالص {_soft_rr_net:.2f} — زیر حداقل {min_conf}٪ اطمینان"
                )

        support = groups["structure"]["details"].get("nearest_support", 0)
        resistance = groups["structure"]["details"].get("nearest_resistance", 0)

        return {
            "price": price,
            "rsi": safe_num(last.get("rsi"), 50),
            "willr": safe_num(last.get("willr"), -50),
            "stoch_k": safe_num(last.get("stoch_k"), 50),
            "stoch_d": safe_num(last.get("stoch_d"), 50),
            "adx": adx,
            "macd_hist": safe_num(last.get("macd_hist")),
            "atr": atr,
            "ema200": safe_num(last.get("ema200")),
            "bb_upper": safe_num(last.get("bb_upper")),
            "bb_lower": safe_num(last.get("bb_lower")),
            "vwap": safe_num(last.get("vwap")) if "vwap" in df.columns else None,
            "support": support,
            "resistance": resistance,
            "pivots": groups["structure"]["details"].get("pivots", {}),
            "swings": groups["structure"]["details"].get("swings", {}),
            "fibonacci": groups["structure"]["details"].get("fibonacci", {}),
            "score": round(adjusted_score, 3),
            "raw_score": aggregate["final_score"],
            "signal": signal,
            "explanation": explanation,
            "neutral_explain": neutral_explain_dict,
            "action_fa": action_fa,
            "confidence": confidence,
            "confidence_tier": tier,
            "reasons": all_reasons,
            "groups": aggregate["groups_summary"],
            "votes_long": aggregate["votes_long"],
            "votes_short": aggregate["votes_short"],
            "votes_neutral": aggregate["votes_neutral"],
            "consensus": consensus,
            "direction": direction,
            "multi_tf_info": multi_tf_info,
            "multi_tf_ok": multi_tf_ok,
            "regime": regime,
            "risk_profile": risk_profile,
            "market_type": market_type,
            "leverage": profile.get("leverage"),
            "allow_short": allow_short,
            "divergence": divergence,
            "sl_tp": sl_tp,
            "rr": rr,
            "is_ranging": regime == "range",
            "close_series": df["close"].tail(30).tolist(),
            "traps": traps,
            "traps_summary": traps_summary,
            "orderbook": orderbook,
            "trap_penalty": trap_penalty,
            "thresholds_used": thresholds,
            "ticker": ticker,
            "is_iranian": _is_iranian_ticker(ticker),
            "scenarios": build_scenarios(
                price=price,
                atr=atr,
                groups=aggregate["groups_summary"],
                support=support,
                resistance=resistance,
                regime=regime,
                direction=direction,
                traps=traps,
                ticker=ticker,
            ),
            "trend_score": groups["trend"].get("score", 0.0),
            "trend_vote": groups["trend"].get("vote", 0),
            "override_reason": aggregate.get("override_reason", ""),
            # 🔴 فاز ۱۰.۳ — Pre-breakout
            "pre_breakout": pre_breakout,
            "pre_breakout_score": pre_breakout.get("score", 0),
            "is_pre_breakout": pre_breakout.get("is_pre_breakout", False),
        }

    except Exception as e:
        logger.exception(f"[Analyzer] خطا در تحلیل: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# Fear & Greed — بدون تغییر
# ═══════════════════════════════════════════════════════════
def compute_fear_greed(df: pd.DataFrame) -> float:
    try:
        if df is None or df.empty or len(df) < 20:
            return 50.0

        df = compute_indicators(df)
        if df is None or df.empty:
            return 50.0

        rsi = safe_num(df["rsi"].iloc[-1], 50)
        price = safe_num(df["close"].iloc[-1])
        atr = safe_num(df["atr"].iloc[-1]) if "atr" in df.columns else 0
        macd_h = safe_num(df["macd_hist"].iloc[-1]) if "macd_hist" in df.columns else 0

        ema50_series = ta.ema(df["close"], length=50)
        ema50 = (
            safe_num(ema50_series.iloc[-1], price)
            if ema50_series is not None and len(ema50_series) > 0
            else price
        )

        rsi_score = max(0, min(100, rsi))

        if atr > 0:
            stretch = ((price - ema50) / atr) * 10 + 50
            stretch = max(0, min(100, stretch))
        else:
            stretch = 50.0

        macd_score = max(0, min(100, 50 + (macd_h * 10)))

        fg = rsi_score * 0.45 + stretch * 0.30 + macd_score * 0.25
        return max(0.0, min(100.0, float(fg)))

    except Exception:
        return 50.0


# ═══════════════════════════════════════════════════════════
# چک‌لیست — بدون تغییر
# ═══════════════════════════════════════════════════════════
GROUP_LABELS = {
    "momentum": ("⚡", "مومنتوم", "RSI, Stochastic, Williams, CCI, ROC"),
    "trend": ("📈", "روند", "EMA200, MACD, ADX, Supertrend, Ichimoku"),
    "volatility": ("📊", "نوسان", "Bollinger, ATR, Keltner, Donchian, StdDev"),
    "volume": ("💧", "حجم", "OBV, CVD, Delta, CMF, MFI, Absorption"),
    "structure": ("🏗", "ساختار", "Pivot, Swing, Fibonacci, S/R"),
}


def build_checklist_weighted(tfs: dict, main_tf: str = "۵ دقیقه") -> tuple:
    r_main = tfs.get(main_tf)
    if not r_main:
        r_main = tfs.get("۵ دقیقه")
    if not r_main:
        return [], 0, "داده کافی نیست", "red"

    items = []
    regime = r_main.get("regime", "range")
    weights = _regime_weights(regime)

    groups = r_main.get("groups", {})
    total_w = 0
    earned_w = 0

    multi_tf_ok = r_main.get("multi_tf_ok", True)
    multi_tf_info = r_main.get("multi_tf_info", "")
    if multi_tf_info:
        items.append(
            {
                "group": "multi_tf",
                "label": "🎯 تأیید چند تایم‌فریمی",
                "icon": "🎯",
                "detail": multi_tf_info,
                "score": 1.0 if multi_tf_ok else 0.0,
                "weight": 20,
                "color": "green" if multi_tf_ok else "red",
            }
        )
        total_w += 20
        if multi_tf_ok:
            earned_w += 20

    divergence = r_main.get("divergence", {})
    if divergence.get("has_divergence"):
        items.append(
            {
                "group": "divergence",
                "label": "⚠️ واگرایی مومنتوم/حجم",
                "icon": "⚠️",
                "detail": divergence.get("reason", ""),
                "score": -1.0,
                "weight": 15,
                "color": "red",
            }
        )
        total_w += 15

    traps = r_main.get("traps", {})
    if traps:
        trap_names = {
            "bull_trap": "تله صعودی",
            "bear_trap": "تله نزولی",
            "fake_breakout": "شکست جعلی",
            "exhaustion": "خستگی روند",
        }
        for trap_key, trap_info in traps.items():
            if trap_info.get("active"):
                items.append(
                    {
                        "group": "trap_" + trap_key,
                        "label": f"🚨 {trap_names.get(trap_key, trap_key)}",
                        "icon": "🚨",
                        "detail": trap_info.get("reason", ""),
                        "score": -1.0,
                        "weight": trap_info.get("severity", 5),
                        "color": "red",
                    }
                )
                total_w += trap_info.get("severity", 5)

    for g_key, (icon, g_name, g_desc) in GROUP_LABELS.items():
        if g_key not in groups:
            continue

        g_res = groups[g_key]
        g_score = g_res.get("score", 0.0)
        g_vote = g_res.get("vote", 0)
        g_reasons = g_res.get("reasons", [])
        g_strength_fa = g_res.get("strength_fa", "")
        g_weight_pct = int(weights.get(g_key, 1.0) * 100 / 6 * 1.5)

        if g_vote > 0:
            g_color = "green"
        elif g_vote < 0:
            g_color = "red"
        else:
            g_color = "yellow"

        detail_with_strength = f"{g_desc}"
        if g_strength_fa and g_strength_fa != "بی‌جهت":
            detail_with_strength = f"قدرت: {g_strength_fa} · {g_desc}"

        items.append(
            {
                "group": g_key,
                "label": f"{icon} {g_name}",
                "icon": icon,
                "detail": detail_with_strength,
                "reasons": g_reasons[:3],
                "score": g_score,
                "weight": g_weight_pct,
                "color": g_color,
                "vote": g_vote,
            }
        )
        total_w += g_weight_pct
        if g_vote == 0:
            earned_w += g_weight_pct * 0.5
        else:
            earned_w += g_weight_pct

    sl_tp = r_main.get("sl_tp")
    rr = safe_num(r_main.get("rr"))
    if sl_tp:
        items.append(
            {
                "group": "sl_tp",
                "label": "🛑 حد ضرر و هدف",
                "icon": "🛑",
                "detail": f"R:R = {rr:.1f}" if rr else "تعریف‌شده",
                "score": 1.0 if rr and rr >= 1.5 else 0.5,
                "weight": 15,
                "color": "green" if rr and rr >= 1.5 else "yellow",
            }
        )
        total_w += 15
        earned_w += 15 if (rr and rr >= 1.5) else 7
    else:
        items.append(
            {
                "group": "sl_tp",
                "label": "🛑 حد ضرر و هدف",
                "icon": "🛑",
                "detail": "تعریف نشده",
                "score": 0.0,
                "weight": 15,
                "color": "red",
            }
        )
        total_w += 15

    percentage = int(earned_w / total_w * 100) if total_w > 0 else 0

    signal = r_main.get("signal", "خنثی")
    confidence = r_main.get("confidence", 0)
    regime_fa = {
        "trend": "جهت‌دار",
        "transitional": "در حال‌تغییر",
        "range": "بی‌جهت",
    }.get(regime, "")

    if SigEnum.is_long(signal):
        if confidence >= 70:
            final = f"🟢 سیگنال خرید قوی — {confidence}% ({regime_fa})"
            final_color = "green"
        else:
            final = f"🟢 سیگنال خرید — {confidence}% ({regime_fa})"
            final_color = "green"
    elif SigEnum.is_short(signal):
        if confidence >= 70:
            final = f"🔴 سیگنال فروش قوی — {confidence}% ({regime_fa})"
            final_color = "red"
        else:
            final = f"🔴 سیگنال فروش — {confidence}% ({regime_fa})"
            final_color = "red"
    else:
        neutral_short = ""
        ne = r_main.get("neutral_explain", {})
        if ne and ne.get("short"):
            neutral_short = ne["short"]
        else:
            neutral_short = f"⚪ خنثی — {regime_fa}"
        final = neutral_short
        final_color = "yellow"

    return items, percentage, final, final_color


# ═══════════════════════════════════════════════════════════
# زمینه‌ی بنیادی (بدون تغییر)
# ═══════════════════════════════════════════════════════════
def _build_fundamental_context(
    df: pd.DataFrame,
    r_main: dict,
    ticker: str,
    is_iranian: bool,
    unit: str,
    fee_pct: float = None,
) -> list[str]:
    """ساخت خطوط زمینه‌ی بنیادی/ساختاری برای تحلیل عمیق."""
    out: list[str] = []

    try:
        if df is None or df.empty or len(df) < 60:
            return out

        last = df.iloc[-1]
        price = safe_num(last.get("close"))
        atr = safe_num(last.get("atr"))

        if price <= 0:
            return out

        fmt = (
            (lambda v: f"{v:,.2f}$")
            if not is_iranian
            else (lambda v: f"{v:,.0f} {unit}")
        )

        if atr > 0:
            atr_pct = atr / price * 100
            if atr_pct < 0.3:
                vol_fa = "بسیار کم — حرکت کند، خطر رکود"
            elif atr_pct < 1.0:
                vol_fa = "کم — مناسب پوزیشن‌های محتاط"
            elif atr_pct < 3.0:
                vol_fa = "متوسط — متعادل"
            elif atr_pct < 6.0:
                vol_fa = "بالا — سود و ضرر سریع"
            else:
                vol_fa = "بسیار بالا — ریسک شدید، اهرم خطرناک"

            out.append(f"📊 **نوسان:** {atr_pct:.2f}٪ — {vol_fa}")

            if fee_pct and fee_pct > 0:
                ratio = atr_pct / fee_pct
                if ratio < 1:
                    out.append(
                        f"🔴 **نوسان از هزینه کمتر است** "
                        f"({atr_pct:.2f}٪ ÷ {fee_pct:.2f}٪ = {ratio:.1f}×) "
                        f"— معامله در این TF صرفه ندارد"
                    )
                elif ratio < 3:
                    out.append(
                        f"🟡 **نوسان کم است** (نسبت {ratio:.1f}× هزینه) "
                        f"— برای پوشش هزینه حرکت بزرگ‌تری لازم است"
                    )
                else:
                    out.append(
                        f"🟢 **نوسان کافی است** (نسبت {ratio:.1f}× هزینه) "
                        f"— معامله می‌تواند هزینه‌ها را پوشش دهد"
                    )

        lookback = min(90, len(df))
        window = df.tail(lookback)
        hi = safe_num(window["high"].max())
        lo = safe_num(window["low"].min())

        if hi > lo > 0:
            pos = (price - lo) / (hi - lo) * 100
            if pos >= 90:
                zone = "نزدیک سقف بازه — احتمال مقاومت یا شکست"
            elif pos >= 70:
                zone = "نیمه‌ی بالای بازه — روند صعودی"
            elif pos >= 40:
                zone = "میانه‌ی بازه — بی‌طرف"
            elif pos >= 15:
                zone = "نیمه‌ی پایین بازه — ضعیف"
            else:
                zone = "نزدیک کف بازه — احتمال حمایت یا شکست"

            out.append(f"📍 **موقعیت در {lookback} کندل:** {pos:.0f}٪ — {zone}")
            out.append(
                f"   سقف {fmt(hi)} · کف {fmt(lo)} · "
                f"فاصله از سقف {(hi - price) / price * 100:.1f}٪"
            )

        adx = safe_num(last.get("adx"), 0)
        ema200 = safe_num(last.get("ema200"))
        ema50 = safe_num(last.get("ema50"))

        bits = []
        if adx > 0:
            bits.append(
                f"ADX={adx:.0f} "
                f"({'روند قوی' if adx >= 40 else 'روند نرمال' if adx >= 25 else 'بدون روند'})"
            )
        if ema200 > 0 and ema50 > 0:
            if price > ema200 and ema50 > ema200:
                bits.append("صعودی (قیمت > EMA50 > EMA200)")
            elif price < ema200 and ema50 < ema200:
                bits.append("نزولی (قیمت < EMA50 < EMA200)")
            else:
                bits.append("مختلط (EMAها هم‌جهت نیستند)")

        if bits:
            out.append("📈 **ساختار روند:** " + " · ".join(bits))

        vol = safe_num(last.get("volume"))
        vol_ma = safe_num(last.get("vol_ma"))
        if vol_ma > 0:
            vr = vol / vol_ma
            if vr >= 1.5:
                v_txt = f"بالا ({vr:.1f}× میانگین)"
            elif vr <= 0.5:
                v_txt = f"کم ({vr:.1f}× میانگین)"
            else:
                v_txt = f"نرمال ({vr:.1f}× میانگین)"

            if len(df) > 2:
                prev_close = safe_num(df["close"].iloc[-2])
                up = price > prev_close
                if vr >= 1.5:
                    v_txt += " · هم‌جهت با قیمت ✅" if up else " · هم‌جهت با نزول ✅"
                elif vr <= 0.5:
                    v_txt += " · حجم تأییدکننده نیست ⚠️"

            out.append(f"💧 **حجم:** {v_txt}")

        r_lvl = safe_num(r_main.get("resistance"))
        s_lvl = safe_num(r_main.get("support"))
        if r_lvl > 0 and s_lvl > 0:
            out.append(
                f"🎯 **فضای حرکت:** تا مقاومت "
                f"{(r_lvl - price) / price * 100:+.2f}٪ · "
                f"تا حمایت {(s_lvl - price) / price * 100:+.2f}٪"
            )

        out.append(
            "ℹ️ *داده‌ی بنیادی (ارزش بازار، اخبار، on-chain) در فاز "
            "بعد اضافه می‌شود — این بخش از قیمت و ساختار بازار "
            "استخراج شده.*"
        )

    except Exception as e:
        logger.warning(f"[Analyzer] زمینه‌ی بنیادی: {e!r}")
        return []

    return out


# ═══════════════════════════════════════════════════════════
# تحلیل پاراگرافی (با حفظ کلیدهای چک‌شده در تست)
# ═══════════════════════════════════════════════════════════
def build_analysis_paragraph(
    ticker: str,
    name: str,
    tfs: dict,
    gsr: float | None = None,
    risk_profile: str = "aggressive",
    tf_name: str = "۵ دقیقه",
) -> str:
    """
    تحلیل پاراگرافی — نسخه ۱۰.۱

    ═══ تغییرات ═══
    • بخش‌بندی واضح‌تر (۶ بخش با header)
    • حذف تکرار (RF، ۵ گروه، سطوح)
    • خلاصه‌ی صادقانه در بالا
    • ترتیب: نتیجه → عمل → تکنیکال → سطوح → پلن → جمع‌بندی
    """
    lines = []

    r_main = tfs.get(tf_name) or tfs.get("۵ دقیقه")
    if not r_main:
        return "داده کافی نیست."

    regime = r_main.get("regime", "range")
    regime_fa = {
        "trend": "جهت‌دار",
        "transitional": "در حال‌تغییر",
        "range": "بی‌جهت",
    }.get(regime, "بی‌جهت")
    is_iranian = _is_iranian_ticker(ticker)
    is_tsetmc = bool(ticker) and not ticker[0].isascii()

    if is_tsetmc:
        unit = "ریال"
    elif is_iranian:
        unit = "تومان"
    else:
        unit = "$"
    market_type = r_main.get("market_type", "spot")
    market_fa = "اسپات" if market_type == "spot" else "فیوچرز"
    profile_fa = {"aggressive": "جسورانه", "conservative": "محاطبانه"}.get(
        risk_profile, "جسورانه"
    )

    signal = r_main.get("signal", "خنثی")
    confidence = r_main.get("confidence", 0)
    price = safe_num(r_main.get("price"))
    adx = safe_num(r_main.get("adx"), 20)
    votes_long = r_main.get("votes_long", 0)
    votes_short = r_main.get("votes_short", 0)
    votes_neutral = r_main.get("votes_neutral", 0)
    action_fa = r_main.get("action_fa", "")
    groups = r_main.get("groups", {})
    divergence = r_main.get("divergence", {})
    multi_tf_info = r_main.get("multi_tf_info", "")
    neutral_explain = r_main.get("neutral_explain", {})
    traps = r_main.get("traps", {})
    override_reason = r_main.get("override_reason", "")

    # ═══════════════════════════════════════════════════════
    # ۱. سرصفحه
    # ═══════════════════════════════════════════════════════
    lines.append(f"📍 {tf_name} · {profile_fa} · {market_fa}")
    lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۲. خلاصه‌ی یک‌خطی (برجسته)
    # ═══════════════════════════════════════════════════════
    if SigEnum.is_long(signal):
        if confidence >= 70:
            summary = f"✅ سیگنال **خرید قوی** — اطمینان {confidence}٪"
        else:
            summary = f"🟢 سیگنال خرید — اطمینان {confidence}٪"
    elif SigEnum.is_short(signal):
        if confidence >= 70:
            summary = f"🔴 سیگنال **فروش قوی** — اطمینان {confidence}٪"
        else:
            summary = f"🔴 سیگنال فروش — اطمینان {confidence}٪"
    else:
        if override_reason:
            summary = "🚫 روند قوی — سیگنال مخالف بلاک شد"
        else:
            summary = f"⚪ بدون سیگنال — صبر کن"

    lines.append(f"## {summary}")
    lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۳. عمل پیشنهادی (کوتاه)
    # ═══════════════════════════════════════════════════════
    if action_fa:
        lines.append(f"**🎯 عمل:** {action_fa}")
        lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۴. خلاصه‌ی بازار (۲-۳ خط)
    # ═══════════════════════════════════════════════════════
    lines.append("### 📊 وضعیت بازار")
    lines.append("")

    if SigEnum.is_long(signal) or SigEnum.is_short(signal):
        direction_fa = "صعودی" if SigEnum.is_long(signal) else "نزولی"
        strength = (
            "قوی" if confidence >= 70 else "معمولی" if confidence >= 50 else "ضعیف"
        )
        lines.append(
            f"روند **{direction_fa}** با قدرت {strength} در بازار «{regime_fa}» "
            f"(ADX={adx:.0f})."
        )
    else:
        if neutral_explain and neutral_explain.get("long"):
            lines.append(neutral_explain["long"])
        elif regime == "range":
            lines.append(
                f"بازار **بی‌جهت** (ADX={adx:.0f}). در این حالت صبر کن تا جهت مشخص شه."
            )
        else:
            lines.append(f"گروه‌ها به توافق نرسیدن. بازار سیگنال واضحی نمی‌ده.")

    if override_reason:
        lines.append(f"⚠️ {override_reason}")

    lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۵. تله‌ها (اگه فعال باشن)
    # ═══════════════════════════════════════════════════════
    active_traps = {k: v for k, v in traps.items() if v.get("active")}
    if active_traps:
        lines.append("### 🚨 هشدار تله")
        lines.append("")
        trap_names = {
            "bull_trap": "تله صعودی",
            "bear_trap": "تله نزولی",
            "fake_breakout": "شکست جعلی",
            "exhaustion": "خستگی روند",
        }
        for trap_key, trap_info in active_traps.items():
            lines.append(
                f"- **{trap_names.get(trap_key, trap_key)}:** "
                f"{trap_info.get('reason', '')}"
            )
        lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۶. رأی‌گیری گروه‌ها (خلاصه)
    # ═══════════════════════════════════════════════════════
    lines.append("### 🗳 آراء گروه‌ها")
    lines.append("")
    lines.append(
        f"**{votes_long}** صعودی · **{votes_neutral}** خنثی · **{votes_short}** نزولی"
    )

    if groups:
        sorted_groups = sorted(
            groups.items(),
            key=lambda x: abs(x[1].get("score", 0)),
            reverse=True,
        )
        GROUP_NAMES = {
            "momentum": "مومنتوم",
            "trend": "روند",
            "volatility": "نوسان",
            "volume": "حجم",
            "structure": "ساختار",
        }
        group_strs = []
        for g_key, g_data in sorted_groups[:3]:
            g_name = GROUP_NAMES.get(g_key, g_key)
            g_vote = g_data.get("vote", 0)
            g_strength = g_data.get("strength_fa", "")

            if g_vote > 0:
                icon = "🟢"
            elif g_vote < 0:
                icon = "🔴"
            else:
                icon = "⚪"

            s_str = f" ({g_strength})" if g_strength and g_strength != "بی‌جهت" else ""
            group_strs.append(f"{g_name} {icon}{s_str}")

        lines.append(" • ".join(group_strs))

    if divergence.get("has_divergence"):
        lines.append(f"⚠️ **واگرایی:** {divergence.get('reason', '')}")

    if multi_tf_info and multi_tf_info != "بدون بررسی":
        lines.append(f"🎯 {multi_tf_info}")

    lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۷. سطوح کلیدی (فشرده)
    # ═══════════════════════════════════════════════════════
    r = safe_num(r_main.get("resistance"))
    s = safe_num(r_main.get("support"))

    if (r > 0 or s > 0) and price > 0:
        lines.append("### 🎯 سطوح کلیدی")
        lines.append("")

        if r > 0:
            dist_r = (r - price) / price * 100
            if is_tsetmc:
                lines.append(f"🔴 **مقاومت:** {r:,.0f} ریال ({dist_r:+.2f}٪)")
            elif is_iranian:
                lines.append(f"🔴 **مقاومت:** {r:,.0f} تومان ({dist_r:+.2f}٪)")
            else:
                lines.append(f"🔴 **مقاومت:** {r:,.2f}$ ({dist_r:+.2f}٪)")

        if s > 0:
            dist_s = (s - price) / price * 100
            if is_tsetmc:
                lines.append(f"🟢 **حمایت:** {s:,.0f} ریال ({dist_s:+.2f}٪)")
            elif is_iranian:
                lines.append(f"🟢 **حمایت:** {s:,.0f} تومان ({dist_s:+.2f}٪)")
            else:
                lines.append(f"🟢 **حمایت:** {s:,.2f}$ ({dist_s:+.2f}٪)")

        lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۸. پلن معاملاتی (اگه سیگنال داره)
    # ═══════════════════════════════════════════════════════
    sl_tp = r_main.get("sl_tp")
    rr = safe_num(r_main.get("rr"))

    if sl_tp:
        sl = safe_num(sl_tp.get("sl"))
        tp = safe_num(sl_tp.get("tp"))
        sl_type = sl_tp.get("type", "")

        lines.append(f"### 📋 پلن معاملاتی")
        lines.append("")

        if is_iranian:
            lines.append(f"💰 ورود: **{price:,.0f}** {unit}")
            lines.append(
                f"🛑 حد ضرر: **{sl:,.0f}** " f"({abs(price - sl) / price * 100:.2f}٪)"
            )
            lines.append(
                f"🎯 هدف: **{tp:,.0f}** " f"({abs(tp - price) / price * 100:.2f}٪)"
            )
        else:
            lines.append(f"💰 ورود: **{price:,.2f}$**")
            lines.append(
                f"🛑 حد ضرر: **{sl:,.2f}$** " f"({abs(price - sl) / price * 100:.2f}٪)"
            )
            lines.append(
                f"🎯 هدف: **{tp:,.2f}$** " f"({abs(tp - price) / price * 100:.2f}٪)"
            )

        rr_net = sl_tp.get("rr_net")
        if rr_net is not None:
            grade = (
                "✅ عالی"
                if rr_net >= 2
                else (
                    "✅ خوب"
                    if rr_net >= 1.5
                    else "🟡 قابل قبول" if rr_net >= 1.0 else "❌ ضعیف"
                )
            )
            lines.append(f"⚖️ R:R واقعی: **{rr_net:.2f}** — {grade}")

        fee_pct = sl_tp.get("fee_pct")
        if fee_pct is not None:
            lines.append(f"💸 هزینه معامله: **{fee_pct:.2f}٪**")

        lines.append("")
    else:
        # ═══ اگه سیگنال نداره → بخش پیشنهاد ═══
        lines.append("### 💡 پیشنهاد")
        lines.append("")
        explanation = r_main.get("explanation", "صبر کن")
        lines.append(f"⚠️ {explanation}")

        if neutral_explain and neutral_explain.get("hint"):
            lines.append(f"💡 {neutral_explain['hint']}")

        lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۹. عمق بازار (خلاصه — اگه داره)
    # ═══════════════════════════════════════════════════════
    ob = r_main.get("orderbook")
    if ob and ob.get("imbalance") is not None:
        imb = ob["imbalance"]
        pressure = ob.get("pressure_fa", "")
        spread_pct = ob.get("spread_pct", 0)
        lines.append(
            f"📖 **عمق بازار:** {pressure} (imbalance={imb:.2f}، اسپرد={spread_pct:.3f}٪)"
        )
        lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۱۰. زمینه‌ی بنیادی (فشرده)
    # ═══════════════════════════════════════════════════════
    fundamental = r_main.get("fundamental_lines") or []
    if fundamental:
        lines.append("### 🧭 زمینه")
        lines.append("")
        for f_line in fundamental:
            lines.append(f"{f_line}")
        lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۱۱. سناریوها (فقط ۲ تا)
    # ═══════════════════════════════════════════════════════
    scenarios = r_main.get("scenarios", [])
    if scenarios:
        lines.append("### 🎬 سناریوها")
        lines.append("")
        for sc in scenarios[:2]:
            icon = sc.get("icon", "•")
            condition = sc.get("condition", "")
            action = sc.get("action", "")
            prob = int(sc.get("probability", 0.5) * 100)
            lines.append(f"{icon} **{condition}** ({prob}٪)")
            lines.append(f"   ← {action}")
        lines.append("")

    # ═══════════════════════════════════════════════════════
    # ۱۲. جمع‌بندی صادقانه (برجسته — مهم‌ترین)
    # ═══════════════════════════════════════════════════════
    lines.append("### ⚡ جمع‌بندی")
    lines.append("")

    if SigEnum.is_long(signal) and confidence >= 70 and not active_traps:
        lines.append("✅ **می‌تونی وارد شی** — با حجم کم و حد ضرر.")
    elif SigEnum.is_long(signal) and active_traps:
        lines.append("🚨 **مراقب باش!** تله فعاله. حتی با سیگنال LONG، حجم کم.")
    elif SigEnum.is_long(signal):
        lines.append("⚠️ سیگنال ضعیفه. اگه وارد می‌شی، فقط با ۰.۵٪ سرمایه.")
    elif SigEnum.is_short(signal) and confidence >= 70:
        lines.append("🔴 فروش منطقیه — ولی نوسان بالاست. حد ضرر تنگ بذار.")
    elif SigEnum.is_short(signal):
        lines.append("⚠️ سیگنال فروش ضعیفه. **صبر کن.**")
    else:
        lines.append("⏸ **الان نخر.** بهترین معامله، معامله‌ای هست که انجام نشه.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Exports
# ═══════════════════════════════════════════════════════════
__all__ = [
    "RISK_PROFILES",
    "CONFIDENCE_TIERS",
    "classify_regime",
    "compute_indicators",
    "compute_pivot_points",
    "find_swing_points",
    "compute_fibonacci",
    "analyze_symbol",
    "compute_fear_greed",
    "build_checklist_weighted",
    "build_analysis_paragraph",
    "GROUP_LABELS",
    "_detect_traps",
    "_traps_summary",
    "build_scenarios",
]


if __name__ == "__main__":
    print("=" * 70)
    print("تست core/analyzer.py — نسخه ۱۰.۰")
    print("=" * 70)
    print()
    print(f"RISK_PROFILES keys: {list(RISK_PROFILES.keys())}")
    print(f"CONFIDENCE_TIERS: {list(CONFIDENCE_TIERS.keys())}")
    print()
    print("[OK] تست کامل شد.")
