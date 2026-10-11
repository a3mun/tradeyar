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
from typing import TypedDict, Literal, NamedTuple, Optional


# ═══════════════════════════════════════════════════════════
# ۱. منبع دیتا
# ═══════════════════════════════════════════════════════════
class DataSource(str, Enum):
    """صرافی‌ها و منابع داده.

    ─── فعال (دارای fetcher) ───
        NOBITEX, BITPIN, WALLEX, TABDEAL, TSETMC

    ─── برنامه‌ریزی‌شده برای فاز ۷ (placeholder) ───
        RAMZINEX, TOOBIT, BINGX

    ─── حذف‌شده در نسخه ۱.۸ ───
        ABANTETHER — کندل نداشت، فقط قیمت تومانی. با تبدیل
        (Tabdeal) جایگزین شد که هم قیمت دارد هم عمق بازار و
        هم بازار تتری.

    ⚠️ اعضای placeholder fetcher ندارند. اگر صدا زده شوند،
       ``resolve_source`` به نوبیتکس fallback می‌کند.
    """

    # ─── فعال ───
    GLOBAL = "global"  # منسوخ — فقط برای سازگاری
    NOBITEX = "nobitex"
    BITPIN = "bitpin"
    WALLEX = "wallex"
    TABDEAL = "tabdeal"
    TSETMC = "tsetmc"

    # ─── placeholder فاز ۷ ───
    RAMZINEX = "ramzinex"
    TOOBIT = "toobit"
    BINGX = "bingx"
    BIT24 = "bit24"

    @classmethod
    def all(cls) -> list[str]:
        return [s.value for s in cls]

    @classmethod
    def active(cls) -> list[str]:
        """منابعی که **واقعاً** کار می‌کنند (بدون placeholder)"""
        return ["nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"]

    @classmethod
    def planned(cls) -> list[str]:
        """منابع برنامه‌ریزی‌شده برای فاز ۷"""
        return ["ramzinex", "toobit", "bingx", "bit24"]

    @classmethod
    def display_name(cls, source: str) -> str:
        return {
            "global": "🌍 جهانی",
            "nobitex": "🟣 نوبیتکس",
            "bitpin": "🟢 بیت‌پین",
            "wallex": "🔵 والکس",
            "tabdeal": "🟠 تبدیل",
            "tsetmc": "🇮🇷 بورس تهران",
            # ─── به‌زودی ───
            "ramzinex": "🟡 رمزینکس (به‌زودی)",
            "toobit": "🟤 توبیت (به‌زودی)",
            "bingx": "🔶 بینگ‌ایکس (به‌زودی)",
            "bit24": "🔹 بیت۲۴ (به‌زودی)",
        }.get(source, "—")


# ─── صرافی‌های placeholder (به‌زودی) ───
PLANNED_SOURCES: frozenset[str] = frozenset({"ramzinex", "toobit", "bingx", "bit24"})

# ─── صرافی‌های فعال ───
ACTIVE_SOURCES: frozenset[str] = frozenset(
    {"nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"}
)


def is_planned_source(source: str) -> bool:
    """آیا این صرافی هنوز پیاده‌سازی نشده (placeholder)؟"""
    return (source or "").lower() in PLANNED_SOURCES


def is_active_source(source: str) -> bool:
    """آیا این صرافی فعال است (fetcher دارد)؟"""
    return (source or "").lower() in ACTIVE_SOURCES


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
# ۱۰. تایم‌فریم‌ها — جدول واحد حقیقت (نسخه ۱.۶)
# ═══════════════════════════════════════════════════════════
# ⚠️ اصلاح مهم (نسخه ۱.۶): سخت‌گیری TF حذف شد.
#
# نسخه‌ی پیشین یک whitelist سخت داشت (``is_tf_supported``) که
# **قبل** از درخواست، ترکیب‌های «ممنوع» را رد می‌کرد:
#
#     walnut + ۵ دقیقه  → None (بدون حتی یک درخواست)
#     walnut + ۱۵ دقیقه → None  ← 🔴 این غلط بود! والکس ۱۵ دارد
#
# دو ایراد:
#   ۱. پشتیبانی TF **per-نماد** است، نه per-صرافی. ممکن است
#      BTC-USDT همه‌ی TFها را بدهد ولی SHIB-USDT فقط چند تا.
#      پس whitelist صرافی محور از اساس اشتباه است.
#   ۲. والکس resolution «15» را دارد، پس «۱۵ دقیقه» نباید رد شود.
#
# قاعده‌ی جدید:
#   • فقط قیدهایی که **واقعاً** وجود دارند در کد می‌مانند:
#       - TSETMC  → فقط «روزانه»
#       - والکس   → «۳۰ دقیقه» ندارد (نه به‌عنوان ۳۰ و نه معادلش)
#       - آبان‌تتر → OHLCV ندارد (فقط قیمت)
#   • بقیه: درخواست می‌فرستیم و **پاسخ صرافی** تصمیم می‌گیرد.
#   • اگر صرافی دیتا نداد → ``None`` (که با کش منفی سریع می‌شود).
#
# ─── پشتیبانی واقعی (کشف‌شده از API، ۲۰۲۶-۱۰-۰۳) ───
#
#   TF        نوبیتکس  بیت‌پین  والکس
#   ─────────────────────────────────────
#   ۱ دقیقه      ✓        ✓       ✗   (res=1 → no_data)
#   ۵ دقیقه      ✓        ✓       ✗   (res=5 → error)
#   ۱۵ دقیقه     ✓        ✓       ✓   (res=15)  ✅ اصلاح‌شده
#   ۳۰ دقیقه     ✓        ✓       ✗   (res=30 → error)
#   ۱ ساعت       ✓        ✓       ✓   (res=60)
#   روزانه       ✓        ✓       ✓   (res=1D)
#
# ⚠️ نقشه‌ی والکس فقط برای TFهایی است که **خود والکس مستقیم**
#    دارد. هیچ تبدیل بی‌صدایی انجام نمی‌شود: اگر والکس TF را
#    نداشته باشد، ``None`` می‌دهد و زنجیره‌ی fallback به
#    نوبیتکس می‌رود — که داده‌ی **درست** می‌دهد.


class TFSpec(NamedTuple):
    """
    مشخصات کامل یک تایم‌فریم.

    Attributes:
        name_fa:    نام فارسی (کلید همه‌ی لایه‌ها) — "۵ دقیقه"
        interval:   فرمت داخلی نوبیتکس/contracts — "5m"
        udf_res:    resolution در UDF history — "5" یا "1D"
        bitpin_res: resolution بیت‌پین — "5m" یا "1d"
        wallex_res: resolution والکس — "15" یا "1D"؛ None = پشتیبانی نمی‌شود
        period:     بازه‌ی نوبیتکس — "5d"
        period_days: بازه به روز (برای بیت‌پین/والکس) — 10
        timeout_min: مهلت سیگنال به دقیقه
    """

    name_fa: str
    interval: str
    udf_res: str
    bitpin_res: str
    wallex_res: Optional[str]
    period: str
    period_days: int
    timeout_min: int


TIMEFRAME_SPECS: dict[str, TFSpec] = {
    "۱ دقیقه": TFSpec("۱ دقیقه", "1m", "1", "1m", "1", "1d", 2, 30),
    "۵ دقیقه": TFSpec("۵ دقیقه", "5m", "5", "5m", None, "5d", 10, 120),  # ← والکس ندارد
    "۱۵ دقیقه": TFSpec("۱۵ دقیقه", "15m", "15", "15m", "15", "5d", 20, 360),
    "۳۰ دقیقه": TFSpec(
        "۳۰ دقیقه", "30m", "30", "30m", None, "1mo", 30, 720
    ),  # ← والکس ندارد
    "۱ ساعت": TFSpec("۱ ساعت", "1h", "60", "1h", "60", "3mo", 180, 2880),
    "روزانه": TFSpec("روزانه", "1d", "1D", "1d", "1D", "6mo", 730, 10080),
}

TF_NAMES = list(TIMEFRAME_SPECS)

# ─── سازگاری عقب‌رو ───
# کدهای قدیمی (app.py، scanner، backtester) این را به‌صورت
# (interval, period, tf_name) باز می‌کنند.
TIMEFRAMES = [(s.interval, s.period, s.name_fa) for s in TIMEFRAME_SPECS.values()]

# ─── نقشه‌ی معکوس ───
TF_BY_INTERVAL: dict[str, str] = {
    s.interval: s.name_fa for s in TIMEFRAME_SPECS.values()
}


def get_tf_spec(tf_name: str) -> TFSpec:
    """
    مشخصات تایم‌فریم را برمی‌گرداند.

    ⚠️ برای نام ناشناخته، **پیش‌فرض ۵ دقیقه** می‌دهد ولی هشدار
       لاگ می‌کند — تا اشتباه تایپی بی‌صدا رد نشود.
    """
    import logging

    spec = TIMEFRAME_SPECS.get(tf_name)
    if spec is None:
        logging.getLogger(__name__).warning(
            f"[Contracts] تایم‌فریم ناشناخته {tf_name!r} — پیش‌فرض «۵ دقیقه»"
        )
        return TIMEFRAME_SPECS["۵ دقیقه"]
    return spec


# ═══════════════════════════════════════════════════════════
# قیدهای واقعی (نسخه ۱.۶)
# ═══════════════════════════════════════════════════════════
# ⚠️ اینجا فقط قیدهایی است که **قطعاً** وجود دارند.
#    هیچ whitelist صرافی‌محوری اینجا نیست — تصمیم با صرافی است.


def source_lacks_ohlcv(source: str) -> bool:
    """
    آیا این منبع OHLCV خودش را ندارد (کندل نمی‌دهد)؟

    • **تبدیل (Tabdeal)** — API عمومی‌اش endpoint OHLCV ندارد
      (۱۲ مسیر مختلف تست شد، همه ۴۰۴). ولی قیمت و عمق بازار
      دارد. برای تحلیل، کندل از صرافی دیگر می‌آید.
    • **آبان‌تتر** — حذف شد (نسخه ۱.۸).

    ⚠️ این تابع «کندل ندارد» را می‌گوید، نه «تحلیل نمی‌شود».
       زنجیره‌ی fallback خودکار کندل را از منبع دیگر می‌گیرد.
    """
    return source == "tabdeal"


def is_ohlcv_supported(tf_name: str, source: str) -> bool:
    """
    آیا این منبع **قطعاً** از این تایم‌فریم OHLCV نمی‌دهد؟

    این تابع فقط «قیدهای سخت» را چک می‌کند، نه یک whitelist:

      • TSETMC  → فقط «روزانه» (بورس تهران intraday ندارد)
      • والکس   → «۳۰ دقیقه» ندارد (پشتیبانی خود API نه)
      • تبدیل   → OHLCV عمومی ندارد (بدون توجه به TF)

    بقیه‌ی ترکیب‌ها ``True`` می‌گیرند و درخواست فرستاده می‌شود؛
    اگر صرافی دیتا نداد، ``None`` برمی‌گردد (و کش منفی سریعش
    می‌کند). این‌طوری پشتیبانی **per-نماد** به‌درستی کار می‌کند.

    Returns:
        False اگر قطعاً پشتیبانی نشود، True در غیر این صورت.
    """
    if not tf_name or source not in TIMEFRAME_SOURCES:
        return False

    # ─── TSETMC: فقط روزانه ───
    if source == "tsetmc":
        return tf_name == "روزانه"

    # ─── تبدیل: OHLCV عمومی ندارد (فقط قیمت + عمق) ───
    if source == "tabdeal":
        return False

    # ─── والکس: «۳۰ دقیقه» را ندارد ───
    # (res=30 روی API خطا می‌دهد؛ 60 هم معادل ۳۰ دقیقه نیست)
    if source == "wallex" and tf_name == "۳۰ دقیقه":
        return False

    # ─── نوبیتکس / بیت‌پین / والکس بقیه: درخواست بفرست ───
    return True


# ─── منابع شناخته‌شده ───
TIMEFRAME_SOURCES = frozenset({"nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"})


def is_tf_supported(tf_name: str, source: str) -> bool:
    """
    نام قدیمی ``is_ohlcv_supported`` — برای سازگاری عقب‌رو.

    ⚠️ در نسخه ۱.۶ این تابع **دیگر whitelist نیست**. فقط
    قیدهای قطعی را چک می‌کند. کد جدید باید
    ``is_ohlcv_supported`` را صدا بزند.
    """
    return is_ohlcv_supported(tf_name, source)


TF_SHORT = {
    "۱ دقیقه": "1m",
    "۵ دقیقه": "5m",
    "۱۵ دقیقه": "15m",
    "۳۰ دقیقه": "30m",
    "۱ ساعت": "1h",
    "روزانه": "1D",
}


# ═══════════════════════════════════════════════════════════
# ۱۱. Timeout مخصوص هر TF (نسخه ۲.۰ — بر اساس کندل + نوع بازار)
# ═══════════════════════════════════════════════════════════
# ═══ چرا بر اساس کندل، نه ساعت ثابت؟ ═══
#
# مهلت ساعت ثابت **غیرمنطقی** است:
#   • ۱ دقیقه با مهلت ۳۰ دقیقه = ۳۰ کندل
#   • ۱ ساعت با مهلت ۲ روز = ۴۸ کندل
#   • روزانه با مهلت ۷ روز = ۷ کندل — **خیلی کم!**
#
# ═══ چرا تفکیک فیوچرز و اسپات؟ ═══
#
# فیوچرز:
#   • اهرم (۲-۱۰x) → حساس به نوسان
#   • بهره روزانه → هزینه انتظار
#   • افق کوتاه → ۵ کندل
#
# اسپات:
#   • بدون اهرم → تحمل بالاتر
#   • بدون بهره → بدون هزینه انتظار
#   • افق بلندتر → ۱۰ کندل
#
# ═══ چرا این اعداد؟ ═══
#
#   ۵ کندل فیوچرز:  از معیار ATR (میانگین نوسان در ۱۴ کندل)
#                   اگه در ۵ کندل TP نخورد، تحلیل غلط بوده
#
#   ۱۰ کندل اسپات:  تعادل بین «زود expire» و «جا ماندن»
#                   برای بازار نوسانی ایران منطقی
#
# ═══ جدول محاسبه ═══
#
#   TF        فیوچرز (۵ کندل)     اسپات (۱۰ کندل)
#   ─────────────────────────────────────────
#   ۱ دقیقه     ۵ دقیقه               ۱۰ دقیقه
#   ۵ دقیقه     ۲۵ دقیقه              ۵۰ دقیقه
#   ۱۵ دقیقه    ۱ ساعت ۱۵ دقیقه       ۲ ساعت ۳۰ دقیقه
#   ۳۰ دقیقه    ۲ ساعت ۳۰ دقیقه       ۵ ساعت
#   ۱ ساعت      ۵ ساعت                ۱۰ ساعت
#   روزانه      ۵ روز                 ۱۰ روز
SIGNAL_MAX_CANDLES_FUTURES = 5
SIGNAL_MAX_CANDLES_SPOT = 10

# ─── مدت هر کندل به دقیقه ───
_TF_DURATION_MINUTES = {
    "۱ دقیقه": 1,
    "۵ دقیقه": 5,
    "۱۵ دقیقه": 15,
    "۳۰ دقیقه": 30,
    "۱ ساعت": 60,
    "روزانه": 1440,
}


def get_signal_timeout(tf_name: str, market_type: str = "spot") -> timedelta:
    """
    محاسبه مهلت سیگنال بر اساس TF و نوع بازار.

    Args:
        tf_name: نام فارسی تایم‌فریم
        market_type: ``"spot"`` یا ``"futures"``

    Returns:
        timedelta مهلت سیگنال.

    Examples:
        >>> get_signal_timeout("۵ دقیقه", "futures")
        timedelta(minutes=25)
        >>> get_signal_timeout("روزانه", "spot")
        timedelta(days=10)
    """
    duration_min = _TF_DURATION_MINUTES.get(tf_name, 5)
    if (market_type or "").lower() == "futures":
        n_candles = SIGNAL_MAX_CANDLES_FUTURES
    else:
        n_candles = SIGNAL_MAX_CANDLES_SPOT
    return timedelta(minutes=duration_min * n_candles)


# ─── سازگاری عقب‌رو (نام قدیمی که دیکشنری بود) ───
# ⚠️ این فقط برای کدهای قدیمی است. کد جدید باید از
#    ``get_signal_timeout()`` استفاده کند.
SIGNAL_TIMEOUT = {tf: get_signal_timeout(tf, "spot") for tf in _TF_DURATION_MINUTES}


# ═══════════════════════════════════════════════════════════
# ۱۱.۵ ضریب ATR برای SL/TP بر اساس TF
# ═══════════════════════════════════════════════════════════
# در TF پایین، ATR نویزی‌تره → ضریب کمتر (SL/TP تنگ‌تر)
# در TF بالا، ATR پایدارتره → ضریب بیشتر (SL/TP بازتر)
TF_ATR_MULT = {
    "۱ دقیقه": 1.0,  # کمترین — نویز بالا، SL تنگ
    "۵ دقیقه": 1.2,
    "۱۵ دقیقه": 1.4,
    "۳۰ دقیقه": 1.5,
    "۱ ساعت": 1.6,
    "روزانه": 2.0,
}


def get_tf_atr_mult(tf_name: str) -> float:
    """دریافت ضریب ATR برای یه TF (با fallback به ۱.۰)"""
    return TF_ATR_MULT.get(tf_name, 1.0)


# ═══════════════════════════════════════════════════════════
# ۱۱.۵ کارمزد صرافی‌ها (نسخه ۳.۰) — 🔴 جدایی IRT و USDT
# ═══════════════════════════════════════════════════════════
# ═══ چرا نسخه ۳.۰ ═══
#
# 🔴 کشف مهم از جدول رسمی صرافی‌ها:
#   کارمزد **USDT** و **IRT** در یک صرافی **یکسان نیست**:
#
#     نوبیتکس USDT: 0.10% / 0.13%
#     نوبیتکس IRT:  0.25% / 0.25%   ← دو برابر!
#
#   نسخه‌ی قبلی فقط یک نرخ داشت و همیشه محافظه‌کارانه 0.15/0.25
#   می‌گرفت. حالا بر اساس **ticker** تشخیص می‌ده.
#
# ═══ چه چیزی محاسبه می‌شود ═══
#   فقط **ورود و خروج** (باز و بستن پوزیشن).
#   کارمزد نگهداری (فاندینگ/بهره) **محاسبه نمی‌شود** —
#   کاربر خودش از صرافی چک می‌کند.
#
# ═══ بیت‌پین و تعهدی ═══
#   بیت‌پین محصول تعهدی/فیوچرز استاندارد نداره. برای
#   market_type=futures روی بیت‌پین، **کارمزد اسپات** حساب
#   می‌شود. سیگنال داده می‌شود ولی هزینه صادقانه است.

EXCHANGE_FEES: dict[str, dict] = {
    "nobitex": {
        "spot_usdt": {"maker": 0.0010, "taker": 0.0013},  # ۰.۱۰٪ / ۰.۱۳٪
        "spot_irt": {"maker": 0.0025, "taker": 0.0025},  # ۰.۲۵٪ / ۰.۲۵٪
        "futures": {"maker": 0.0010, "taker": 0.0013},  # تعهدی نوبیتکس
    },
    "bitpin": {
        "spot_usdt": {"maker": 0.0030, "taker": 0.0035},  # ۰.۳۰٪ / ۰.۳۵٪
        "spot_irt": {"maker": 0.0030, "taker": 0.0035},
        # ─── بیت‌پین تعهدی استاندارد ندارد → اسپات ───
        "futures": {"maker": 0.0030, "taker": 0.0035},
    },
    "wallex": {
        "spot_usdt": {"maker": 0.0020, "taker": 0.0020},  # ۰.۲۰٪ / ۰.۲۰٪
        "spot_irt": {"maker": 0.0035, "taker": 0.0035},  # ۰.۳۵٪ / ۰.۳۵٪
        "futures": {"maker": 0.0020, "taker": 0.0020},
    },
    "tabdeal": {
        "spot_usdt": {"maker": 0.0033, "taker": 0.0035},  # ۰.۳۳٪ / ۰.۳۵٪
        "spot_irt": {"maker": 0.0033, "taker": 0.0035},
        "futures": {"maker": 0.0033, "taker": 0.0035},
    },
    "tsetmc": {
        "spot_usdt": {"maker": 0.0012, "taker": 0.0012},  # کارگزار بورس
        "spot_irt": {"maker": 0.0012, "taker": 0.0012},
        "futures": {"maker": 0.0012, "taker": 0.0012},
    },
}

# ─── پیش‌فرض محافظه‌کارانه (منبع ناشناخته) ───
DEFAULT_FEES = {
    "spot_usdt": {"maker": 0.0025, "taker": 0.0030},
    "spot_irt": {"maker": 0.0025, "taker": 0.0030},
    "futures": {"maker": 0.0025, "taker": 0.0030},
}

FEE_MODE_TYPICAL = "typical"  # limit ورود، market خروج
FEE_MODE_WORST = "worst"  # market ↔ market
FEE_MODE_BEST = "best"  # limit ↔ limit


def _detect_irt(ticker: str) -> bool:
    """
    آیا این نماد تومانی/ریالی است؟

    ─── تشخیص ───
        BTC-IRT, USDT-IRT, PAXG-IRT → True
        BTC-USD, ETH-USD            → False
        فولاد (بورس)                → True  (به ریال است)
    """
    if not ticker:
        return False
    upper = ticker.upper()
    if "-IRT" in upper or "-RLS" in upper or upper.endswith("IRT"):
        return True
    # ─── نماد بورس تهران (شروع با حرف غیرلاتین) ───
    return not ticker[0].isascii()


def get_fee_table(
    source: str,
    market_type: str = "spot",
    ticker: str = "",
    **kwargs,
) -> dict:
    """
    جدول کارمزد برای صرافی + بازار + نوع ارز.

    Args:
        source: کلید صرافی
        market_type: spot/futures
        ticker: نماد — برای تشخیص IRT در برابر USDT

    Returns:
        ``{"maker": float, "taker": float}``
    """
    entry = EXCHANGE_FEES.get((source or "").lower())
    if not entry:
        entry = DEFAULT_FEES

    mt = "futures" if (market_type or "").lower() == "futures" else "spot"

    # ─── برای فیوچرز: نرخ مستقیم ───
    if mt == "futures":
        table = entry.get("futures")
        if table:
            return {
                "maker": float(table.get("maker", 0.0025)),
                "taker": float(table.get("taker", 0.0030)),
            }

    # ─── برای اسپات: تفکیک IRT / USDT ───
    is_irt = _detect_irt(ticker)
    key = "spot_irt" if is_irt else "spot_usdt"
    table = entry.get(key) or entry.get("spot_usdt")
    if not table:
        table = DEFAULT_FEES[key]

    return {
        "maker": float(table.get("maker", 0.0025)),
        "taker": float(table.get("taker", 0.0030)),
    }


def get_fee_rate(
    source: str,
    mode: str = FEE_MODE_TYPICAL,
    market_type: str = "spot",
    ticker: str = "",
    **kwargs,  # ← سازگاری با hold_hours قدیمی
) -> float:
    """
    کارمزد **رفت‌وبرگشتی** به‌صورت اعشاری.

    ═══ نحوه‌ی محاسبه ═══
        typical: maker + taker  (limit ورود، market خروج)
        worst:   taker × 2      (هر دو market)
        best:    maker × 2      (هر دو limit)

    ═══ چه چیزی محاسبه نمی‌شود ═══
        ❌ کارمزد نگهداری (فاندینگ فیوچرز، بهره تعهدی)
        ❌ شارژ روزانه
    دلیل: کاربر فقط می‌خواهد بداند ورود و خروج چقدر هزینه دارد.

    Args:
        source: کلید صرافی
        mode: typical/worst/best
        market_type: spot/futures
        ticker: نماد — برای تشخیص IRT

    Returns:
        کارمزد کل رفت‌وبرگشتی (مثلاً 0.0023 = ۰.۲۳٪)
    """
    table = get_fee_table(source, market_type, ticker)
    maker, taker = table["maker"], table["taker"]

    if mode == FEE_MODE_WORST:
        return taker * 2
    if mode == FEE_MODE_BEST:
        return maker * 2
    return maker + taker  # typical


def compute_net_rr(
    entry: float,
    sl: float,
    tp: float,
    fee_rate: float,
) -> dict:
    """
    محاسبه‌ی R:R **خام** و **واقعی** (بعد از هزینه).

    ═══ منطق ═══
    هزینه روی **هر دو طرف** اعمال می‌شود:
        سود خالص = (TP − entry) − هزینه
        ضرر خالص = (entry − SL) + هزینه
    """
    if not (entry > 0 and sl > 0 and tp > 0):
        return {}

    risk_gross = abs(entry - sl)
    reward_gross = abs(tp - entry)

    if risk_gross <= 0:
        return {}

    rr_gross = reward_gross / risk_gross
    fee_abs = entry * fee_rate

    reward_net = reward_gross - fee_abs
    risk_net = risk_gross + fee_abs

    rr_net = (reward_net / risk_net) if risk_net > 0 else 0.0

    reward_pct = reward_gross / entry * 100
    fee_pct = fee_rate * 100
    fee_ratio = (reward_pct / fee_pct) if fee_pct > 0 else 0.0
    breakeven_pct = fee_rate * 100

    # 🔴 فاز ۱۰.۵ — is_worthwhile ترکیبی (توصیه آمریکایی)
    # سه شرط: rr_net > 1.5 AND fee_ratio > 5 AND timeframe_viable
    #
    # ═══ چرا این تغییر ═══
    # قبلاً: rr_net ≥ 1.0 AND fee_ratio ≥ 3.0
    #   → خیلی آسان‌گیر بود، سیگنال‌های ضعیف هم is_worthwhile=True می‌گرفتن
    #
    # الان: هر سه شرط لازم
    #   → فقط سیگنال‌های واقعاً ارزشمند قبول می‌شن
    timeframe_viable = rr_net >= 1.3
    is_worthwhile = rr_net > 1.5 and fee_ratio > 5.0 and timeframe_viable

    return {
        "rr_gross": round(rr_gross, 3),
        "rr_net": round(rr_net, 3),
        "fee_pct": round(fee_pct, 4),
        "fee_ratio": round(fee_ratio, 2),
        "breakeven_pct": round(breakeven_pct, 4),
        "is_worthwhile": is_worthwhile,
        "timeframe_viable": timeframe_viable,
        "rr_decay_pct": (
            round((rr_gross - rr_net) / rr_gross * 100, 1) if rr_gross > 0 else 0.0
        ),
    }


def get_fee_info(
    source: str,
    market_type: str = "spot",
    ticker: str = "",
) -> dict:
    """اطلاعات کارمزد صرافی برای نمایش در فرانت"""
    table = get_fee_table(source, market_type, ticker)
    maker, taker = table["maker"], table["taker"]

    return {
        "source": source,
        "market_type": market_type,
        "is_irt": _detect_irt(ticker),
        "maker_pct": round(maker * 100, 4),
        "taker_pct": round(taker * 100, 4),
        "round_trip_typical_pct": round((maker + taker) * 100, 4),
        "round_trip_worst_pct": round(taker * 2 * 100, 4),
    }


# ─── نام‌های قدیمی (سازگاری عقب‌رو) ───
DEFAULT_FEE = DEFAULT_FEES["spot_usdt"]


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
    ("BTC-USD", "بیت‌کوین (USDT)", "nobitex"),
    ("BTC-IRT", "بیت‌کوین (تومان)", "nobitex"),
    ("USDT-IRT", "تتر/تومان", "nobitex"),
    ("ETH-USD", "اتریوم", "nobitex"),
    ("PAXG-USD", "پکس گلد (USDT)", "nobitex"),
    ("PAXG-IRT", "پکس گلد (تومان)", "nobitex"),
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


# ═══════════════════════════════════════════════════════════
# ۱۴.۵ Order Book — فاز ۶.۵ (فقط Type، بدون منطق)
# ═══════════════════════════════════════════════════════════
# ⚠️ این قرارداد است، نه پیاده‌سازی. در فاز ۶.۵ پر می‌شود.
#
# چرا در contracts: تا لایه‌های مختلف (fetcher، analyzer، API،
# فرانت) قرارداد **یکسان** داشته باشند.


class OrderBookLevel(TypedDict, total=False):
    """یک سطح قیمت در عمق بازار"""

    price: float
    quantity: float
    orders: Optional[int]


class OrderBookDict(TypedDict, total=False):
    """
    عمق بازار — قرارداد لایه‌ی داده (فاز ۶.۵).

    فیلدهای مشتق که تحلیل از آن‌ها استفاده می‌کند:
      • spread / spread_pct  → هزینه‌ی واقعی ورود و خروج
      • imbalance            → فشار خرید/فروش لحظه‌ای (۰..۱)
      • bid_wall / ask_wall  → دیوار سفارش (حجم غیرعادی)
    """

    ticker: str
    source: str
    timestamp: str  # ISO UTC-aware
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]

    best_bid: float
    best_ask: float
    spread: float
    spread_pct: float
    imbalance: float


class OrderBookSummary(TypedDict, total=False):
    """خلاصه‌ی عمق بازار برای نمایش سبک (فاز ۶.۵)"""

    imbalance: float
    spread_pct: float
    has_bid_wall: bool
    has_ask_wall: bool
    pressure_fa: str  # «فشار خرید» / «فشار فروش» / «متعادل»


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
