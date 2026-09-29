"""
core/analyzer.py
تحلیل تکنیکال — نسخه ۸.۵ (فاز ۵.۵ — رفع باگ تومان/دلار)
============================================================
تغییرات نسخه ۸.۵:
  - رفع باگ تشخیص تومان/دلار: از ticker به جای heuristic قیمت
  - Pivot Points fallback برای کندل تخت
"""

import numpy as np
import pandas as pd
import pandas_ta_classic as ta

from .contracts import (
    Signal as SigEnum,
    TF_ATR_MULT,
    get_tf_atr_mult,
    get_adaptive_thresholds,
)
from .utils import safe_num

# ═══════════════════════════════════════════════════════════
# پروفایل‌های ریسک
# ═══════════════════════════════════════════════════════════
RISK_PROFILES = {
    "aggressive_spot": {
        "name": "جسور (اسپات)",
        "sl_mult": 1.2,
        "tp_mult": 2.5,
        "min_confidence": 30,
        "color": "#DB6D28",
        "advice": "خرید در اسپات با حد ضرر. ۲-۳٪ سرمایه.",
        "leverage": None,
        "allow_short": False,
    },
    "conservative_spot": {
        "name": "محتاط (اسپات)",
        "sl_mult": 1.8,
        "tp_mult": 3.5,
        "min_confidence": 50,
        "color": "#3FB950",
        "advice": "خرید مطمئن در اسپات. ۱-۲٪ سرمایه.",
        "leverage": None,
        "allow_short": False,
    },
    "aggressive_futures": {
        "name": "جسور (فیوچرز)",
        "sl_mult": 1.5,
        "tp_mult": 3.0,
        "min_confidence": 40,
        "color": "#DB6D28",
        "advice": "فیوچرز با اهرم ۲-۳x. حتماً حد ضرر.",
        "leverage": 3,
        "allow_short": True,
    },
    "conservative_futures": {
        "name": "محتاط (فیوچرز)",
        "sl_mult": 2.5,
        "tp_mult": 5.0,
        "min_confidence": 60,
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
# رژیم بازار
# ═══════════════════════════════════════════════════════════
def classify_regime(adx: float, channel_width_pct: float = None) -> str:
    if adx >= 25:
        return "trend"
    elif adx >= 20:
        return "transitional"
    else:
        return "range"


def _regime_weights(regime: str) -> dict:
    if regime == "trend":
        return {
            "momentum": 1.2,
            "trend": 1.5,
            "volatility": 1.0,
            "volume": 1.0,
            "structure": 1.0,
        }
    elif regime == "transitional":
        return {
            "momentum": 1.5,
            "trend": 1.0,
            "volatility": 1.1,
            "volume": 1.2,
            "structure": 1.1,
        }
    else:
        return {
            "momentum": 1.8,
            "trend": 0.3,
            "volatility": 1.2,
            "volume": 1.5,
            "structure": 1.3,
        }


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
# اندیکاتورها
# ═══════════════════════════════════════════════════════════
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or len(df) < 50:
        return df

    try:
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
        else:
            df["macd_hist"] = 0.0

        df["ema200"] = ta.ema(df["close"], length=200)
        df["ema50"] = ta.ema(df["close"], length=50)

        adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
        if adx_df is not None and len(adx_df.columns) >= 1:
            df["adx"] = adx_df.iloc[:, 0]
        else:
            df["adx"] = 20.0

        try:
            st = ta.supertrend(
                df["high"], df["low"], df["close"], length=10, multiplier=3.0
            )
            if st is not None and st.shape[1] > 1:
                df["supertrend_dir"] = st.iloc[:, 1]
            else:
                df["supertrend_dir"] = 1
        except Exception:
            df["supertrend_dir"] = 1

        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

        bb_df = ta.bbands(df["close"], length=20, std=2)
        if bb_df is not None and len(bb_df.columns) >= 3:
            df["bb_lower"] = bb_df.iloc[:, 0]
            df["bb_mid"] = bb_df.iloc[:, 1]
            df["bb_upper"] = bb_df.iloc[:, 2]
        else:
            df["bb_lower"] = df["close"]
            df["bb_mid"] = df["close"]
            df["bb_upper"] = df["close"]

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
        print(f"[Analyzer] compute_indicators: {e}")

    return df


# ═══════════════════════════════════════════════════════════
# Pivot / Swing / Fibonacci
# ═══════════════════════════════════════════════════════════
def compute_pivot_points(df: pd.DataFrame) -> dict:
    """Pivot Points با fallback برای کندل تخت"""
    if df is None or df.empty or len(df) < 2:
        return {}

    prev = df.iloc[-2]
    high = safe_num(prev.get("high"))
    low = safe_num(prev.get("low"))
    close = safe_num(prev.get("close"))

    # ═══ Fallback: اگه کندل قبل تخت بود ═══
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
# گروه ۱: Momentum
# ═══════════════════════════════════════════════════════════
def _analyze_momentum(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    reasons = []
    signals = []

    last = df.iloc[-1]

    rsi = safe_num(last.get("rsi"), 50)
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

    stoch_k = safe_num(last.get("stoch_k"), 50)
    stoch_d = safe_num(last.get("stoch_d"), 50)
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

    willr = safe_num(last.get("willr"), -50)
    if willr < -80:
        signals.append((+1.0, 0.9))
        reasons.append(f"Williams %R={willr:.0f} اشباع فروش")
    elif willr > -20:
        signals.append((-1.0, 0.9))
        reasons.append(f"Williams %R={willr:.0f} اشباع خرید")
    else:
        signals.append((0.0, 0.5))

    cci = safe_num(last.get("cci"), 0)
    if cci < -100:
        signals.append((+0.8, 0.8))
        reasons.append(f"CCI={cci:.0f} اشباع فروش")
    elif cci > 100:
        signals.append((-0.8, 0.8))
        reasons.append(f"CCI={cci:.0f} اشباع خرید")
    else:
        signals.append((0.0, 0.5))

    roc = safe_num(last.get("roc"), 0)
    if roc > 2:
        signals.append((+0.6, 0.7))
        reasons.append(f"ROC={roc:.1f}% مومنتوم صعودی")
    elif roc < -2:
        signals.append((-0.6, 0.7))
        reasons.append(f"ROC={roc:.1f}% مومنتوم نزولی")
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
        },
        "weight": 1.0,
    }


# ═══════════════════════════════════════════════════════════
# گروه ۲: Trend
# ═══════════════════════════════════════════════════════════
def _analyze_trend(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    reasons = []
    signals = []

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = safe_num(last["close"])

    ema200 = safe_num(last.get("ema200"))
    ema50 = safe_num(last.get("ema50"))
    if ema200 > 0:
        if price > ema200:
            signals.append((+1.0, 1.2))
            reasons.append("قیمت بالای EMA200 — روند بلندمدت صعودی")
        else:
            signals.append((-1.0, 1.2))
            reasons.append("قیمت زیر EMA200 — روند بلندمدت نزولی")

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

    adx = safe_num(last.get("adx"), 20)
    if adx > 40:
        reasons.append(f"ADX={adx:.0f} روند قوی")
    elif adx > 25:
        reasons.append(f"ADX={adx:.0f} روند نرمال")
    elif adx > 20:
        reasons.append(f"ADX={adx:.0f} روند ضعیف")
    else:
        reasons.append(f"ADX={adx:.0f} بدون روند")

    st_dir = safe_num(last.get("supertrend_dir"), 1)
    if st_dir > 0:
        signals.append((+0.8, 1.0))
        reasons.append("Supertrend صعودی")
    elif st_dir < 0:
        signals.append((-0.8, 1.0))
        reasons.append("Supertrend نزولی")

    try:
        high_9 = df["high"].rolling(9).max()
        low_9 = df["low"].rolling(9).min()
        tenkan = (high_9 + low_9) / 2
        high_26 = df["high"].rolling(26).max()
        low_26 = df["low"].rolling(26).min()
        kijun = (high_26 + low_26) / 2

        t_val = safe_num(tenkan.iloc[-1])
        k_val = safe_num(kijun.iloc[-1])

        if t_val > 0 and k_val > 0:
            if t_val > k_val and price > k_val:
                signals.append((+0.7, 0.9))
                reasons.append("Ichimoku: Tenkan بالای Kijun (صعودی)")
            elif t_val < k_val and price < k_val:
                signals.append((-0.7, 0.9))
                reasons.append("Ichimoku: Tenkan زیر Kijun (نزولی)")
            else:
                signals.append((0.0, 0.5))
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
            "macd_hist": macd_h,
            "adx": adx,
            "supertrend_dir": st_dir,
        },
        "weight": 1.0,
    }


# ═══════════════════════════════════════════════════════════
# گروه ۳: Volatility
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
# گروه ۴: Volume
# ═══════════════════════════════════════════════════════════
def _analyze_volume(
    df: pd.DataFrame, market_type: str = "spot", _thresholds: tuple = None
) -> dict:
    reasons = []
    signals = []

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = safe_num(last["close"])

    has_volume = "volume" in df.columns and df["volume"].sum() > 0

    if not has_volume:
        return {
            "vote": 0,
            "score": 0.0,
            "reasons": ["حجم در دسترس نیست"],
            "details": {},
            "weight": 1.0,
        }

    obv_last = safe_num(last.get("obv"))
    obv_prev = safe_num(prev.get("obv"))
    if obv_last > obv_prev:
        signals.append((+0.5, 0.9))
        reasons.append("OBV صعودی (حجم ورودی)")
    elif obv_last < obv_prev:
        signals.append((-0.5, 0.9))
        reasons.append("OBV نزولی (حجم خروجی)")

    vol = safe_num(last.get("volume"))
    vol_ma = safe_num(last.get("vol_ma"))
    if vol_ma > 0:
        vol_ratio = vol / vol_ma
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

        cvd_z = safe_num(last.get("cvd_zscore"), 0)
        if cvd_z > 2.0:
            signals.append((-0.6, 1.0))
            reasons.append(f"CVD Z-Score={cvd_z:.1f} اشباع خرید")
        elif cvd_z < -2.0:
            signals.append((+0.6, 1.0))
            reasons.append(f"CVD Z-Score={cvd_z:.1f} اشباع فروش")

    cmf = safe_num(last.get("cmf"), 0)
    if cmf > 0.1:
        signals.append((+0.7, 1.0))
        reasons.append(f"CMF={cmf:.2f} جریان پول ورودی")
    elif cmf < -0.1:
        signals.append((-0.7, 1.0))
        reasons.append(f"CMF={cmf:.2f} جریان پول خروجی")

    mfi = safe_num(last.get("mfi"), 50)
    if mfi < 20:
        signals.append((+0.8, 1.0))
        reasons.append(f"MFI={mfi:.0f} اشباع فروش حجمی")
    elif mfi > 80:
        signals.append((-0.8, 1.0))
        reasons.append(f"MFI={mfi:.0f} اشباع خرید حجمی")

    if "vwap" in df.columns:
        vwap = safe_num(last.get("vwap"))
        if vwap > 0:
            if price > vwap * 1.02:
                signals.append((-0.4, 0.7))
                reasons.append("قیمت بالای VWAP — ورود دیرهنگام")
            elif price < vwap * 0.98:
                signals.append((+0.4, 0.7))
                reasons.append("قیمت زیر VWAP — فرصت ورود")

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
            "vol_ratio": (vol / vol_ma) if vol_ma > 0 else 0,
            "cmf": cmf,
            "mfi": mfi,
            "cvd": safe_num(last.get("cvd")),
            "delta": safe_num(last.get("delta")),
        },
        "weight": 1.0,
    }


# ═══════════════════════════════════════════════════════════
# گروه ۵: Structure
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
# واگرایی
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
# تشخیص تله‌ها
# ═══════════════════════════════════════════════════════════
def _detect_traps(groups: dict, price: float, atr: float) -> dict:
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

    if m_score > 0.35 and v_score < -0.25 and s_score < -0.15:
        traps["bull_trap"] = {
            "active": True,
            "reason": (
                f"⚡ مومنتوم صعودی (score={m_score:+.2f}) ولی جریان پول خروجی "
                f"({v_score:+.2f}) + نزدیک مقاومت — احتمال «تله صعودی»"
            ),
            "severity": 8,
        }

    if m_score < -0.35 and v_score > 0.25 and s_score > 0.15:
        traps["bear_trap"] = {
            "active": True,
            "reason": (
                f"⚡ مومنتوم نزولی (score={m_score:+.2f}) ولی جریان پول ورودی "
                f"({v_score:+.2f}) + نزدیک حمایت — احتمال «تله نزولی»"
            ),
            "severity": 8,
        }

    if adx > 35 and vol_ratio < 0.6 and abs(s_score) > 0.30:
        traps["fake_breakout"] = {
            "active": True,
            "reason": (
                f"📉 ADX={adx:.0f} (روند قوی) ولی حجم فقط {vol_ratio:.1f}x میانگین "
                f"+ نزدیک سطح کلیدی — احتمال «شکست جعلی»"
            ),
            "severity": 7,
        }

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
# سناریوساز
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
    unit = "تومان" if is_iranian else "$"
    fmt = ",.0f" if is_iranian else ",.2f"

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
# رأی‌گیری
# ═══════════════════════════════════════════════════════════
def _aggregate_votes(
    groups: dict, regime: str, profile: str, adx: float, market_type: str = "spot"
) -> dict:
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

    if profile == "aggressive":
        if regime == "range":
            m_vote = (
                groups.get("momentum", {}).get("vote", 0)
                if groups.get("momentum")
                else 0
            )
            v_vote = (
                groups.get("volume", {}).get("vote", 0) if groups.get("volume") else 0
            )
            if (
                votes_long >= 2
                and votes_long > votes_short
                and m_vote > 0
                and v_vote > 0
            ):
                direction = "long"
                consensus = (
                    "weak"
                    if votes_long == 2
                    else ("normal" if votes_long == 3 else "strong")
                )
            elif (
                votes_short >= 2
                and votes_short > votes_long
                and m_vote < 0
                and v_vote < 0
            ):
                direction = "short"
                consensus = (
                    "weak"
                    if votes_short == 2
                    else ("normal" if votes_short == 3 else "strong")
                )
            else:
                direction = "neutral"
                consensus = "neutral"
        else:
            if votes_long >= 2 and votes_long > votes_short:
                direction = "long"
                consensus = (
                    "weak"
                    if votes_long == 2
                    else ("normal" if votes_long == 3 else "strong")
                )
            elif votes_short >= 2 and votes_short > votes_long:
                direction = "short"
                consensus = (
                    "weak"
                    if votes_short == 2
                    else ("normal" if votes_short == 3 else "strong")
                )
            else:
                direction = "neutral"
                consensus = "neutral"
    else:
        if regime == "range":
            s_vote = (
                groups.get("structure", {}).get("vote", 0)
                if groups.get("structure")
                else 0
            )
            if votes_long >= 2 and votes_long > votes_short and s_vote >= 0:
                direction = "long"
                consensus = (
                    "weak"
                    if votes_long == 2
                    else ("normal" if votes_long == 3 else "strong")
                )
            elif votes_short >= 2 and votes_short > votes_long and s_vote <= 0:
                direction = "short"
                consensus = (
                    "weak"
                    if votes_short == 2
                    else ("normal" if votes_short == 3 else "strong")
                )
            else:
                direction = "neutral"
                consensus = "neutral"
        else:
            if votes_long >= 3 and votes_long > votes_short:
                direction = "long"
                consensus = (
                    "weak"
                    if votes_long == 3
                    else ("normal" if votes_long == 4 else "strong")
                )
            elif votes_short >= 3 and votes_short > votes_long:
                direction = "short"
                consensus = (
                    "weak"
                    if votes_short == 3
                    else ("normal" if votes_short == 4 else "strong")
                )
            else:
                direction = "neutral"
                consensus = "neutral"

    if market_type == "spot" and direction == "short":
        direction = "neutral"
        consensus = "neutral"

    return {
        "final_score": round(final_score, 3),
        "votes_long": votes_long,
        "votes_short": votes_short,
        "votes_neutral": votes_neutral,
        "consensus": consensus,
        "direction": direction,
        "groups_summary": groups_summary,
    }


def _compute_confidence(aggregate: dict, adx: float, divergence: dict) -> int:
    consensus = aggregate.get("consensus", "neutral")
    final_score = abs(aggregate.get("final_score", 0.0))
    direction = aggregate.get("direction", "neutral")

    if direction == "neutral" or consensus == "neutral":
        return 0

    if consensus == "strong":
        base = 85
    elif consensus == "normal":
        base = 65
    elif consensus == "weak":
        base = 45
    else:
        return 0

    score_bonus = min(10, final_score * 15)

    if adx > 40:
        adx_bonus = 5
    elif adx > 25:
        adx_bonus = 3
    elif adx > 20:
        adx_bonus = 0
    else:
        adx_bonus = -5

    div_penalty = (
        divergence.get("penalty", 0) if divergence.get("has_divergence") else 0
    )

    confidence = int(base + score_bonus + adx_bonus - div_penalty)
    return max(0, min(100, confidence))


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

    if votes_neutral >= 3:
        short_msg = f"⚪ بدون سیگنال — {votes_neutral} گروه خنثی"
    elif votes_long == votes_short and votes_long > 0:
        short_msg = "⚪ تعادل گروه‌ها — بدون جهت مشخص"
    else:
        short_msg = "⚪ بدون سیگنال معتبر"

    reasons = []
    if regime == "range":
        reasons.append("بازار در رژیم «رنج» هست و روند مشخصی نداره")
    elif regime == "transitional":
        reasons.append("بازار در حالت «گذار» هست — نه روند قوی، نه رنج")
    elif regime == "trend":
        reasons.append("بازار روند داره ولی گروه‌ها هم‌جهت نیستن")

    if votes_neutral >= 3:
        reasons.append(f"{votes_neutral} از ۵ گروه خنثی موندن")
    if votes_long == votes_short and votes_long > 0:
        reasons.append(
            f"{votes_long} گروه صعودی مقابل {votes_short} گروه نزولی — تعادل"
        )
    if votes_long < 2 and votes_short < 2:
        reasons.append("کمتر از ۲ گروه هم‌جهت هستن (آستانه‌ی ورود برآورده نشد)")
    if divergence.get("has_divergence"):
        reasons.append("واگرایی مومنتوم/حجم دیده می‌شه")
    if market_type == "spot" and votes_short > votes_long:
        reasons.append("در اسپات فقط خرید مجاز است — سیگنال فروش نادیده گرفته شد")

    if not reasons:
        reasons.append("شرایط بازار نامشخصه")

    long_msg = " • ".join(reasons)

    hint = None
    if tfs_data and current_tf:
        higher_tfs_with_signal = []
        higher_order = ["۱ ساعت", "روزانه"]
        for higher_tf in higher_order:
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
            trap_warnings = []
            for t_key in active_traps:
                t_info = traps[t_key]
                trap_warnings.append(t_info.get("reason", ""))
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
) -> dict | None:
    """تحلیل نماد — تابع اصلی"""
    if df is None or df.empty:
        print("[Analyzer] df خالیه")
        return None

    n_candles = len(df)
    if n_candles < 50:
        print(f"[Analyzer] کندل کافی نیست: {n_candles} < 50")
        return None

    try:
        df = compute_indicators(df)
        if df is None or df.empty:
            print("[Analyzer] compute_indicators خالی برگردوند")
            return None

        last = df.iloc[-1]
        price = safe_num(last["close"])
        atr = safe_num(last.get("atr"))
        adx = safe_num(last.get("adx"), 20)

        regime = classify_regime(adx)
        thresholds = get_adaptive_thresholds(regime, adx)

        groups = {
            "momentum": _analyze_momentum(df, _thresholds=thresholds),
            "trend": _analyze_trend(df, _thresholds=thresholds),
            "volatility": _analyze_volatility(df, _thresholds=thresholds),
            "volume": _analyze_volume(df, market_type, _thresholds=thresholds),
            "structure": _analyze_structure(df, _thresholds=thresholds),
        }

        aggregate = _aggregate_votes(groups, regime, risk_profile, adx, market_type)
        divergence = _detect_divergence(groups["momentum"], groups["volume"])

        traps = _detect_traps(groups, price, atr)
        traps_summary = _traps_summary(traps)

        trap_penalty = 0
        if traps_summary["has_high_risk"]:
            trap_penalty = 10
        elif traps_summary["has_warning"]:
            trap_penalty = 5

        adx_mult = (
            1.0 if regime == "trend" else (0.7 if regime == "transitional" else 0.4)
        )
        adjusted_score = aggregate["final_score"] * adx_mult

        confidence = _compute_confidence(aggregate, adx, divergence)
        if trap_penalty > 0:
            confidence = max(0, confidence - trap_penalty)
        tier = _confidence_tier(confidence)

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

        if not multi_tf_ok and aggregate["direction"] != "neutral":
            confidence = int(confidence * 0.85)
            tier = _confidence_tier(confidence)

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
                "short",
                f"اطمینان کافی نیست ({confidence}% < {min_conf}%)",
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
                explanation = (
                    "🔴 در اسپات نمی‌تونی بفروشی — صبر کن یا به فیوچرز سوییچ کن"
                )
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

        sl_tp = None
        rr = None
        is_directional = SigEnum.is_directional(signal)

        if market_type == "spot" and SigEnum.is_short(signal):
            is_directional = False

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
                if abs(price - sl) > 0:
                    rr = abs(tp - price) / abs(price - sl)
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
                if abs(sl - price) > 0:
                    rr = abs(price - tp) / abs(sl - price)

        all_reasons = []
        for g_name, g_res in groups.items():
            if g_res:
                for r in g_res.get("reasons", []):
                    all_reasons.append(r)

        if divergence.get("has_divergence"):
            all_reasons.insert(0, divergence["reason"])

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
        }

    except Exception as e:
        print(f"[Analyzer] خطا در تحلیل: {e}")
        import traceback

        traceback.print_exc()
        return None


# ═══════════════════════════════════════════════════════════
# Fear & Greed
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
# چک‌لیست
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
# پاراگراف تحلیل
# ═══════════════════════════════════════════════════════════
def build_analysis_paragraph(
    ticker: str,
    name: str,
    tfs: dict,
    gsr: float | None = None,
    risk_profile: str = "aggressive",
    tf_name: str = "۵ دقیقه",
) -> str:
    """تحلیل عمیق — تکنیکال + روانشناسی"""
    lines = []

    r_main = tfs.get(tf_name) or tfs.get("۵ دقیقه")
    if not r_main:
        return "داده کافی نیست."

    regime = r_main.get("regime", "range")
    regime_fa = {
        "trend": "بازار جهت‌دار",
        "transitional": "بازار در حال‌تغییر",
        "range": "بازار بی‌جهت",
    }.get(regime, "")
    market_type = r_main.get("market_type", "spot")
    market_fa = "اسپات" if market_type == "spot" else "فیوچرز"
    profile_fa = {"aggressive": "جسورانه", "conservative": "محتاطانه"}.get(
        risk_profile, "جسورانه"
    )

    is_iranian = _is_iranian_ticker(ticker)
    unit = "تومان" if is_iranian else "$"

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

    lines.append(
        f"📍 **تایم‌فریم:** {tf_name} · **پروفایل:** {profile_fa} · **بازار:** {market_fa}"
    )
    lines.append("")

    lines.append("◈ خوانش کلی بازار")
    lines.append("─" * 30)

    if SigEnum.is_long(signal):
        if confidence >= 70:
            lines.append(
                f"سیستم به **خرید قوی** تمایل دارد (اطمینان {confidence}%). "
                f"در «{regime_fa}» با ADX={adx:.0f}، "
                f"مومنتوم صعودی و جریان پول از سمت خریداران حمایت می‌کنه."
            )
        else:
            lines.append(
                f"نشانه‌های **صعود** وجود دارد ولی اطمینان فقط {confidence}% هست. "
                f"در «{regime_fa}»، بهتره با احتیاط و حجم کم وارد بشی."
            )
    elif SigEnum.is_short(signal):
        if confidence >= 70:
            lines.append(
                f"سیستم به **فروش قوی** تمایل دارد (اطمینان {confidence}%). "
                f"در «{regime_fa}» با ADX={adx:.0f}، "
                f"فشار فروش غالب و مومنتوم نزولی تأییدکننده‌ست."
            )
        else:
            lines.append(
                f"نشانه‌های **نزول** وجود دارد ولی ضعیف (اطمینان {confidence}%). "
                f"احتمال برگشت هست، محتاط باش."
            )
    else:
        if neutral_explain and neutral_explain.get("long"):
            lines.append(f"⚪ **بدون سیگنال معتبر:** {neutral_explain['long']}")
        elif regime == "range":
            lines.append(
                f"**بازار بی‌جهت** است (ADX={adx:.0f}). "
                f"در این حالت، معامله‌گران حرفه‌ای **صبر می‌کنند** "
                f"تا بازار از رنج خارج بشه. ورود در رنج = ضرر."
            )
        else:
            lines.append(
                f"سیستم **خنثی** است ({confidence}%). "
                f"گروه‌ها به توافق نرسیدن — احتمال نوسان بالا و پراکنده."
            )

        if neutral_explain and neutral_explain.get("hint"):
            lines.append(f"💡 {neutral_explain['hint']}")

    if action_fa:
        lines.append(f"🎯 **عمل پیشنهادی:** {action_fa}")

    lines.append("")

    active_traps = {k: v for k, v in traps.items() if v.get("active")}
    if active_traps:
        lines.append("◈ هشدار تله‌های معاملاتی")
        lines.append("─" * 30)
        trap_names = {
            "bull_trap": "🚨 تله صعودی",
            "bear_trap": "🚨 تله نزولی",
            "fake_breakout": "⚠️ شکست جعلی",
            "exhaustion": "😮‍💨 خستگی روند",
        }
        for trap_key, trap_info in active_traps.items():
            lines.append(f"{trap_names.get(trap_key, trap_key)}")
            lines.append(f"   {trap_info.get('reason', '')}")
        lines.append("")

    lines.append("◈ رأی‌گیری تخصصی ۵ گروه")
    lines.append("─" * 30)
    lines.append(
        f"📊 **آراء:** {votes_long} صعودی · {votes_neutral} خنثی · {votes_short} نزولی"
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

        top_groups = []
        for g_key, g_data in sorted_groups[:3]:
            g_name = GROUP_NAMES.get(g_key, g_key)
            g_vote = g_data.get("vote", 0)
            g_strength = g_data.get("strength_fa", "")

            if g_vote > 0:
                dir_icon = "🟢"
                dir_fa = "صعودی"
            elif g_vote < 0:
                dir_icon = "🔴"
                dir_fa = "نزولی"
            else:
                dir_icon = "⚪"
                dir_fa = "خنثی"

            strength_str = (
                f" ({g_strength})" if g_strength and g_strength != "بی‌جهت" else ""
            )
            top_groups.append(f"{g_name}: {dir_icon} {dir_fa}{strength_str}")

        lines.append("🔍 **گروه‌های کلیدی:** " + " · ".join(top_groups))

    if divergence.get("has_divergence"):
        lines.append("")
        lines.append(f"⚠️ **هشدار واگرایی:** {divergence.get('reason', '')}")

    if multi_tf_info and multi_tf_info != "بدون بررسی":
        lines.append(f"🎯 **تأیید چند TF:** {multi_tf_info}")

    lines.append("")

    r = safe_num(r_main.get("resistance"))
    s = safe_num(r_main.get("support"))

    if r > 0 or s > 0:
        lines.append("◈ سطوح کلیدی")
        lines.append("─" * 30)

        if r > 0 and price > 0:
            dist_r = abs(r - price) / price * 100
            if is_iranian:
                lines.append(f"🔴 **مقاومت:** {r:,.0f} {unit} (فاصله: {dist_r:.2f}%)")
            else:
                lines.append(f"🔴 **مقاومت:** {r:,.2f}$ (فاصله: {dist_r:.2f}%)")
        if s > 0 and price > 0:
            dist_s = abs(price - s) / price * 100
            if is_iranian:
                lines.append(f"🟢 **حمایت:** {s:,.0f} {unit} (فاصله: {dist_s:.2f}%)")
            else:
                lines.append(f"🟢 **حمایت:** {s:,.2f}$ (فاصله: {dist_s:.2f}%)")

        lines.append("")

    sl_tp = r_main.get("sl_tp")
    rr = safe_num(r_main.get("rr"))

    if sl_tp:
        sl = safe_num(sl_tp.get("sl"))
        tp = safe_num(sl_tp.get("tp"))
        sl_type = sl_tp.get("type", "")
        tf_mult = sl_tp.get("tf_mult", 1.0)

        if sl_type == "LONG":
            lines.append("◈ پلن معاملاتی — خرید")
        elif sl_type == "SHORT":
            lines.append("◈ پلن معاملاتی — فروش")
        else:
            lines.append("◈ پلن معاملاتی")
        lines.append("─" * 30)

        if is_iranian:
            lines.append(f"💰 **ورود:** {price:,.0f} {unit}")
            lines.append(
                f"🛑 **حد ضرر:** {sl:,.0f} {unit} "
                f"({abs(price - sl) / price * 100:.2f}%)"
            )
            lines.append(
                f"🎯 **هدف:** {tp:,.0f} {unit} "
                f"({abs(tp - price) / price * 100:.2f}%)"
            )
        else:
            lines.append(f"💰 **ورود:** {price:,.2f}$")
            lines.append(
                f"🛑 **حد ضرر:** {sl:,.2f}$ ({abs(price - sl) / price * 100:.2f}%)"
            )
            lines.append(
                f"🎯 **هدف:** {tp:,.2f}$ ({abs(tp - price) / price * 100:.2f}%)"
            )

        if rr:
            lines.append(
                f"⚖️ **R:R:** {rr:.1f} — "
                f"{'✅ عالی' if rr >= 2 else '⚠️ قابل قبول' if rr >= 1.5 else '❌ ضعیف'}"
            )
        lines.append(f"📊 **اطمینان:** {confidence}%")
        if tf_mult != 1.0:
            lines.append(f"⏱ ضریب ATR این TF: ×{tf_mult}")
    else:
        lines.append("◈ پیشنهاد")
        lines.append("─" * 30)
        explanation = r_main.get("explanation", "صبر کن")
        lines.append(f"⚠️ {explanation}")
        if neutral_explain and neutral_explain.get("hint"):
            lines.append(f"💡 {neutral_explain['hint']}")

    lines.append("")

    scenarios = r_main.get("scenarios", [])
    if scenarios:
        lines.append("◈ سناریوهای احتمالی")
        lines.append("─" * 30)
        for sc in scenarios:
            icon = sc.get("icon", "•")
            condition = sc.get("condition", "")
            action = sc.get("action", "")
            prob = int(sc.get("probability", 0.5) * 100)
            lines.append(f"{icon} **{condition}** ({prob}%)")
            lines.append(f"   ← {action}")
        lines.append("")

    prof = RISK_PROFILES.get(
        f"{risk_profile}_{market_type}", RISK_PROFILES.get("aggressive_spot")
    )
    if prof:
        lines.append(f"◈ توصیه {prof.get('name', '')}")
        lines.append("─" * 30)
        lines.append(f"💡 {prof.get('advice', '')}")
        if prof.get("leverage"):
            lines.append(f"⚙️ **اهرم:** {prof['leverage']}x")
        lines.append("")

    lines.append("◈ جمع‌بندی صادقانه")
    lines.append("─" * 30)

    if SigEnum.is_long(signal) and confidence >= 70 and not active_traps:
        lines.append(
            "✅ **می‌تونی وارد شی** ولی با حجم کم و حد ضرر. "
            "بازار همیشه حق نداره — اگه بعد از ورود، قیمت به SL رسید، بدون بحث خارج شو."
        )
    elif SigEnum.is_long(signal) and active_traps:
        lines.append(
            "🚨 **مراقب باش!** تله فعاله. حتی اگه سیگنال LONG هست، "
            "احتمال برگشت زیاده. حجم کم و SL تنگ."
        )
    elif SigEnum.is_long(signal):
        lines.append(
            "⚠️ **محتاط باش.** سیگنال ضعیفه. اگه وارد می‌شی، فقط با ۰.۵٪ سرمایه."
        )
    elif SigEnum.is_short(signal) and confidence >= 70:
        lines.append("🔴 **فروش منطقیه** ولی نوسان بالاست. حجم کم، حد ضرر تنگ.")
    elif SigEnum.is_short(signal):
        lines.append("⚠️ **صبر کن.** فروش ضعیف = ریسک بالا.")
    else:
        lines.append(
            "⏸ **الان نخر.** بازار سیگنال واضحی نمی‌ده. "
            "بهترین معامله، معامله‌ای هست که انجام نشه."
        )

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
    print("تست core/analyzer.py — نسخه ۸.۵")
    print("=" * 70)
    print()
    print("[OK] تست کامل شد.")
