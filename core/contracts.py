"""
core/contracts.py
قراردادهای مرکزی پروژه — Enum، Type، Constants
نسخه ۱.۲ — اضافه TF_ATR_MULT برای SL/TP TF-محور
============================================================
تغییرات نسخه ۱.۲:
  - اضافه TF_ATR_MULT (ضریب ATR بر اساس تایم‌فریم)
  - بخش جدید ۱۱.۵
"""

from enum import Enum
from datetime import timedelta
from typing import TypedDict, Literal, Optional


# ═══════════════════════════════════════════════════════════
# ۱. منبع دیتا
# ═══════════════════════════════════════════════════════════
class DataSource(str, Enum):
    GLOBAL = "global"
    NOBITEX = "nobitex"
    ABANTETHER = "abantether"
    BITPIN = "bitpin"
    WALLEX = "wallex"
    TSETMC = "tsetmc"

    @classmethod
    def all(cls) -> list[str]:
        return [s.value for s in cls]

    @classmethod
    def display_name(cls, source: str) -> str:
        return {
            "global": "🌍 جهانی",
            "nobitex": "🟣 نوبیتکس",
            "abantether": "⚪ آبان‌تتر",
            "bitpin": "🟢 بیت‌پین",
            "wallex": "🔵 والکس",
            "tsetmc": "🇮🇷 بورس تهران",
        }.get(source, "—")


# ═══════════════════════════════════════════════════════════
# ۲. نوع بازار
# ═══════════════════════════════════════════════════════════
class MarketType(str, Enum):
    SPOT = "spot"
    FUTURES = "futures"

    @classmethod
    def all(cls) -> list[str]:
        return [m.value for m in cls]

    @classmethod
    def display_fa(cls, market_type: str) -> str:
        return {"spot": "💵 اسپات", "futures": "📈 فیوچرز"}.get(market_type, "—")


# ═══════════════════════════════════════════════════════════
# ۳. پروفایل ریسک
# ═══════════════════════════════════════════════════════════
class RiskProfile(str, Enum):
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"

    @classmethod
    def all(cls) -> list[str]:
        return [r.value for r in cls]

    @classmethod
    def display_fa(cls, profile: str) -> str:
        return {"aggressive": "🚀 جسورانه", "conservative": "🛡 محتاطانه"}.get(
            profile, "—"
        )


# ═══════════════════════════════════════════════════════════
# ۴. سیگنال
# ═══════════════════════════════════════════════════════════
class Signal(str, Enum):
    LONG = "LONG"
    LONG_WEAK = "LONG ضعیف"
    SHORT = "SHORT"
    SHORT_WEAK = "SHORT ضعیف"
    NEUTRAL = "خنثی"

    @classmethod
    def is_long(cls, signal: str) -> bool:
        return "LONG" in signal

    @classmethod
    def is_short(cls, signal: str) -> bool:
        return "SHORT" in signal

    @classmethod
    def is_directional(cls, signal: str) -> bool:
        return cls.is_long(signal) or cls.is_short(signal)

    @classmethod
    def is_weak(cls, signal: str) -> bool:
        return "ضعیف" in signal


# ═══════════════════════════════════════════════════════════
# ۵. جهت
# ═══════════════════════════════════════════════════════════
class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


# ═══════════════════════════════════════════════════════════
# ۶. رژیم بازار
# ═══════════════════════════════════════════════════════════
class Regime(str, Enum):
    TREND = "trend"
    TRANSITIONAL = "transitional"
    RANGE = "range"

    @classmethod
    def display_fa(cls, regime: str) -> tuple[str, str]:
        """(icon, name_fa)"""
        return {
            "trend": ("📈", "بازار جهت‌دار"),
            "transitional": ("⚖️", "بازار در حال‌تغییر"),
            "range": ("📊", "بازار بی‌جهت"),
        }.get(regime, ("📊", "بازار بی‌جهت"))

    @classmethod
    def display_text(cls, regime: str) -> str:
        """فقط متن فارسی"""
        _, name = cls.display_fa(regime)
        return name

    @classmethod
    def display_short(cls, regime: str) -> str:
        """متن کوتاه برای جدول"""
        return {
            "trend": "جهت‌دار",
            "transitional": "در حال‌تغییر",
            "range": "بی‌جهت",
        }.get(regime, "بی‌جهت")


# ═══════════════════════════════════════════════════════════
# ۷. اجماع
# ═══════════════════════════════════════════════════════════
class Consensus(str, Enum):
    STRONG = "strong"
    NORMAL = "normal"
    WEAK = "weak"
    NEUTRAL = "neutral"

    @classmethod
    def display_fa(cls, consensus: str) -> str:
        return {
            "strong": "🔥 اجماع قوی",
            "normal": "✅ اجماع معمولی",
            "weak": "⚠️ اجماع ضعیف",
            "neutral": "⚪ بدون اجماع",
        }.get(consensus, "—")


# ═══════════════════════════════════════════════════════════
# ۸. وضعیت سیگنال
# ═══════════════════════════════════════════════════════════
class SignalResult(str, Enum):
    WIN = "win"
    LOSS = "loss"
    PENDING = "pending"
    EXPIRED = "expired"

    @classmethod
    def display_fa(cls, result: Optional[object]) -> str:
        if result is True or result == "win":
            return "✅ برد"
        if result is False or result == "loss":
            return "❌ باخت"
        if result == "expired":
            return "⏰ منقضی"
        return "⏳ در انتظار"


# ═══════════════════════════════════════════════════════════
# ۹. گروه‌های تحلیل
# ═══════════════════════════════════════════════════════════
class AnalysisGroup(str, Enum):
    MOMENTUM = "momentum"
    TREND = "trend"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    STRUCTURE = "structure"

    @classmethod
    def all(cls) -> list[str]:
        return [g.value for g in cls]

    @classmethod
    def display_fa(cls, group: str) -> tuple[str, str, str]:
        """(icon, name_fa, description)"""
        return {
            "momentum": ("⚡", "مومنتوم", "RSI، Stochastic، Williams، CCI، ROC"),
            "trend": ("📈", "روند", "EMA200، MACD، ADX، Supertrend، Ichimoku"),
            "volatility": ("📊", "نوسان", "Bollinger، ATR، Keltner، Donchian، StdDev"),
            "volume": ("💧", "حجم", "OBV، CVD، Delta، CMF، MFI، Absorption"),
            "structure": ("🏗", "ساختار", "Pivot، Swing، Fibonacci، S/R"),
        }.get(group, ("•", group, ""))


# ═══════════════════════════════════════════════════════════
# ۱۰. تایم‌فریم‌ها
# ═══════════════════════════════════════════════════════════
TIMEFRAMES = [
    ("1m", "1d", "۱ دقیقه"),
    ("5m", "5d", "۵ دقیقه"),
    ("15m", "5d", "۱۵ دقیقه"),
    ("30m", "1mo", "۳۰ دقیقه"),
    ("1h", "3mo", "۱ ساعت"),
    ("1d", "6mo", "روزانه"),
]

TF_NAMES = [tf[2] for tf in TIMEFRAMES]
TF_SHORT = {
    "۱ دقیقه": "1m",
    "۵ دقیقه": "5m",
    "۱۵ دقیقه": "15m",
    "۳۰ دقیقه": "30m",
    "۱ ساعت": "1h",
    "روزانه": "1D",
}


# ═══════════════════════════════════════════════════════════
# ۱۱. Timeout مخصوص هر TF
# ═══════════════════════════════════════════════════════════
SIGNAL_TIMEOUT = {
    "۱ دقیقه": timedelta(minutes=30),
    "۵ دقیقه": timedelta(hours=2),
    "۱۵ دقیقه": timedelta(hours=6),
    "۳۰ دقیقه": timedelta(hours=12),
    "۱ ساعت": timedelta(days=2),
    "روزانه": timedelta(days=7),
}


# ═══════════════════════════════════════════════════════════
# ۱۱.۵ ضریب ATR برای SL/TP بر اساس TF (جدید در ۱.۲)
# ═══════════════════════════════════════════════════════════
# در TF پایین، ATR نویزی‌تره → ضریب کمتر (SL/TP تنگ‌تر)
# در TF بالا، ATR پایدارتره → ضریب بیشتر (SL/TP بازتر)
#
# این ضریب در analyzer.py در محاسبه SL/TP ضرب می‌شه:
#     effective_sl = atr * profile_sl_mult * TF_ATR_MULT[tf]
#     effective_tp = atr * profile_tp_mult * TF_ATR_MULT[tf]
# ─── نسخه ۱.۳: افزایش ضریب برای TF های پایین ───
# دلیل: نویز بالا در TF پایین + SL/TP تنگ باعث باخت می‌شد
TF_ATR_MULT = {
    "۱ دقیقه": 1.8,  # ← 3.6 برابر (0.5 → 1.8)
    "۵ دقیقه": 1.5,  # ← 1.9 برابر (0.8 → 1.5)
    "۱۵ دقیقه": 1.3,  # ← 1.3 برابر
    "۳۰ دقیقه": 1.3,  # ← 1.1 برابر
    "۱ ساعت": 1.4,  # ← 0.9 برابر
    "روزانه": 1.8,  # ← کاهش (خیلی بزرگ بود)
}


def get_tf_atr_mult(tf_name: str) -> float:
    """دریافت ضریب ATR برای یه TF (با fallback به ۱.۰)"""
    return TF_ATR_MULT.get(tf_name, 1.0)


# ═══════════════════════════════════════════════════════════
# ۱۱.۶ آستانه‌های تطبیقی رأی‌گیری (جدید در ۱.۳)
# ═══════════════════════════════════════════════════════════
# در رژیم trend با ADX بالا، آستانه‌ها رو کم می‌کنیم تا سیستم
# سیگنال‌های ضعیف رو هم ببینه (با هشدار تله)
#
# ساختار: {regime: {adx_range: (momentum_thr, trend_thr, other_thr)}}
ADAPTIVE_THRESHOLDS = {
    "trend": {
        "strong": (0.18, 0.22, 0.22),  # ADX > 45
        "normal": (0.22, 0.26, 0.26),  # ADX 30-45
        "weak": (0.25, 0.30, 0.30),  # ADX < 30
    },
    "transitional": {
        "default": (0.25, 0.30, 0.30),
    },
    "range": {
        "default": (0.25, 0.30, 0.30),
    },
}


def get_adaptive_thresholds(regime: str, adx: float) -> tuple:
    """
    دریافت آستانه‌های رأی‌گیری بر اساس رژیم و ADX.

    Returns:
        (momentum_thr, trend_thr, other_thr)
    """
    if regime == "trend":
        if adx > 45:
            return ADAPTIVE_THRESHOLDS["trend"]["strong"]
        elif adx > 30:
            return ADAPTIVE_THRESHOLDS["trend"]["normal"]
        else:
            return ADAPTIVE_THRESHOLDS["trend"]["weak"]
    else:
        return ADAPTIVE_THRESHOLDS[regime]["default"]


# ═══════════════════════════════════════════════════════════
# ۱۲. نمادهای Popular
# ═══════════════════════════════════════════════════════════
POPULAR_SYMBOLS = [
    ("BTC-USD", "₿ بیت‌کوین (USDT)", "nobitex"),
    ("BTC-IRT", "₿ بیت‌کوین (تومان)", "nobitex"),
    ("USDT-IRT", "💵 تتر/تومان", "nobitex"),
    ("ETH-USD", "Ξ اتریوم", "nobitex"),
    ("PAXG-USD", "🪙 پکس گلد (USDT)", "nobitex"),
    ("PAXG-IRT", "🪙 پکس گلد (تومان)", "nobitex"),
]


# ═══════════════════════════════════════════════════════════
# ۱۳. TTL کش‌ها
# ═══════════════════════════════════════════════════════════
class CacheTTL:
    TICKER = 5
    LIVE_PRICE = 5
    SIGNAL_CARD = 30
    TF_TABLE = 30
    ANALYSIS = 300
    SCAN = 300


# ═══════════════════════════════════════════════════════════
# ۱۴. Type Hints
# ═══════════════════════════════════════════════════════════
class SLTPDict(TypedDict, total=False):
    sl: float
    tp: float
    type: str


class GroupResult(TypedDict, total=False):
    vote: int
    score: float
    weight: float
    reasons: list[str]
    details: dict
    strength: str
    strength_fa: str


class TickerItem(TypedDict, total=False):
    name: str
    emoji: str
    price: Optional[float]
    change_pct: Optional[float]
    unit: str


class MarketInfo(TypedDict, total=False):
    name: str
    icon: str
    is_open: bool
    next_event: str


class LogEntry(TypedDict, total=False):
    timestamp: str
    ticker: str
    name: str
    signal: str
    price: float
    tf: str
    market_type: str
    source: str
    sl: float
    tp: float
    sl_tp_type: str
    result: Optional[object]
    result_time: Optional[str]
    exit_price: Optional[float]
    expired: bool


class AppDefaults:
    """پیش‌فرض‌های اپ"""

    THEME = "dark"
    DATA_SOURCE = DataSource.NOBITEX.value  # ← از global به nobitex
    SYMBOL = "BTC-USD"  # ← از GC=F به BTC-USD
    MARKET_TYPE = MarketType.FUTURES.value
    RISK_PROFILE = RiskProfile.AGGRESSIVE.value
    TIMEFRAME = "۵ دقیقه"
    REFRESH_SECONDS = 60

    MAX_CUSTOM_SYMBOLS = 20
    MAX_SIGNAL_LOG = 2000


# ═══════════════════════════════════════════════════════════
# ۱۶. نمادهای اصلی
# ═══════════════════════════════════════════════════════════
SYMBOLS = {
    # ─── جهانی ───
    "GC=F": "طلا",
    "SI=F": "نقره",
    "BZ=F": "نفت برنت",
    # ─── کریپتو USDT ───
    "BTC-USD": "بیت‌کوین",
    "ETH-USD": "اتریوم",
    "SOL-USD": "سولانا",
    "XRP-USD": "ریپل",
    "BNB-USD": "بایننس کوین",
    "ADA-USD": "کاردانو",
    "DOGE-USD": "دوج‌کوین",
    "TON-USD": "تون‌کوین",
    "PAXG-USD": "پکس گلد",
    "XAUT-USD": "تتر گلد",
    # ─── جفت‌ارزهای تومانی ───
    "USDT-IRT": "تتر/تومان",
    "BTC-IRT": "بیت‌کوین/تومان",
    "ETH-IRT": "اتریوم/تومان",
    "BNB-IRT": "بایننس/تومان",
    "SOL-IRT": "سولانا/تومان",
    "XRP-IRT": "ریپل/تومان",
    "ADA-IRT": "کاردانو/تومان",
    "DOGE-IRT": "دوج/تومان",
    "TRX-IRT": "ترون/تومان",
    "TON-IRT": "تون/تومان",
    "MATIC-IRT": "پالیگان/تومان",
    "LINK-IRT": "چین‌لینک/تومان",
    "AVAX-IRT": "آوالانچ/تومان",
    "SHIB-IRT": "شیبا/تومان",
    "PAXG-IRT": "پکس‌گلد/تومان",
    "XAUT-IRT": "تتر گلد/تومان",
}

# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("تست core/contracts.py — نسخه ۱.۲")
    print("=" * 60)
    print()
    print(f"Regime.display_fa('trend')       = {Regime.display_fa('trend')}")
    print(f"Regime.display_text('trend')     = {Regime.display_text('trend')}")
    print(f"AnalysisGroup.display_fa('trend') = {AnalysisGroup.display_fa('trend')}")
    print(f"Signal.is_long('LONG ضعیف')       = {Signal.is_long('LONG ضعیف')}")
    print(f"Signal.is_short('SHORT ضعیف')     = {Signal.is_short('SHORT ضعیف')}")
    print()
    print("TF_ATR_MULT:")
    for tf, mult in TF_ATR_MULT.items():
        print(f"   {tf:12} → {mult}")
    print()
    print(f"get_tf_atr_mult('۵ دقیقه') = {get_tf_atr_mult('۵ دقیقه')}")
    print(f"get_tf_atr_mult('نامعلوم') = {get_tf_atr_mult('نامعلوم')}")
    print(f"Regime.display_fa('trend')       = {Regime.display_fa('trend')}")
    print(f"Regime.display_text('trend')     = {Regime.display_text('trend')}")
    print(f"Regime.display_short('trend')    = {Regime.display_short('trend')}")
    print(f"Regime.display_fa('range')       = {Regime.display_fa('range')}")
    print(f"Regime.display_fa('transitional')= {Regime.display_fa('transitional')}")
    print(f"AppDefaults.DATA_SOURCE = {AppDefaults.DATA_SOURCE}")
    print(f"AppDefaults.SYMBOL      = {AppDefaults.SYMBOL}")
    print("آستانه‌های تطبیقی:")
    for regime in ["trend", "transitional", "range"]:
        for adx in [15, 35, 50]:
            thresholds = get_adaptive_thresholds(regime, adx)
        print(
            f"   {regime:12} ADX={adx:2} → mom={thresholds[0]:.2f} trend={thresholds[1]:.2f}"
        )
    print()
    print("[OK] تست کامل شد.")
