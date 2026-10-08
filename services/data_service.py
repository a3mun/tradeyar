"""
services/data_service.py
لایه دیتا — با کش، single-flight و کش منفی تفکیک‌شده
============================================================
نسخه ۱.۶ — سخت‌گیری TF حذف شد.

اصلاح کلیدی:
    پیش‌تر ``_resolve_source_for_tf`` از یک whitelist صرافی‌محور
    استفاده می‌کرد و ترکیب‌هایی مثل «والکس + ۱۵ دقیقه» را
    **بدون حتی یک درخواست** رد می‌کرد — که غلط بود، چون والکس
    resolution «15» را دارد.

    در حال حاضر فقط **قیدهای قطعی** در ``core.contracts``
    بررسی می‌شوند (TSETMC روزانه، آبان‌تتر بدون OHLCV،
    والکس بدون ۳۰ دقیقه) و بقیه با درخواست واقعی تصمیم
    گرفته می‌شود. اگر صرافی دیتا نداد، ``None`` برمی‌گردد و
    کش منفی آن را سریع می‌کند.

نکته‌ی مهم درباره TTL کش منفی:
    • خطای **قطعی** (نماد/TF وجود ندارد) → ۲۴ ساعت
    • خطای **موقت** (شبکه، timeout) → ۵ دقیقه
    تفکیک لازم است چون یک قطعی اینترنت کوتاه نباید نماد سالم
    را یک روز کامل بخواباند.
"""

import logging

from core.contracts import (
    TIMEFRAME_SPECS,
    get_tf_spec,
    is_ohlcv_supported,
    source_lacks_ohlcv,
)
from core.data_fetcher import (
    fetch_history_by_source,
    fetch_iran_prices,
    fetch_quote_by_source,
    get_data_source,
    is_valid_nobitex_symbol,
    resolve_symbol_and_source,
)
from core.sources import get_default_symbol_for_source
from core.tz import interval_matches_tf, interval_mismatch_detail

from services.cache import (
    NEGATIVE_TTL_STATIC,
    NEGATIVE_TTL_TRANSIENT,
    clear_negative,
    data_cache,
    get_negative,
    get_ttl,
    key_lock,
    quote_cache,
    set_negative,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# جدول تایم‌فریم — مشتق‌شده از contracts (یک منبع حقیقت)
# ═══════════════════════════════════════════════════════════
TF_MAP: dict[str, tuple[str, str]] = {
    s.name_fa: (s.interval, s.period) for s in TIMEFRAME_SPECS.values()
}


def get_tf_params(tf_name: str) -> tuple[str, str]:
    """(interval, period) برای نوبیتکس — با هشدار برای TF ناشناخته"""
    spec = get_tf_spec(tf_name)
    return (spec.interval, spec.period)


# ═══════════════════════════════════════════════════════════
# زنجیره‌ی fallback
# ═══════════════════════════════════════════════════════════
_FALLBACK_ORDER = ["nobitex", "bitpin", "wallex"]


def _resolve_source_for_tf(source: str, tf_name: str) -> str:
    """
    اگر منبع انتخابی کاربر **قطعاً** این TF را نداشته باشد،
    اولین منبع جایگزین که دارد برگردانده می‌شود.

    ⚠️ این تابع دیگر whitelist نیست: فقط ``is_ohlcv_supported``
       را چک می‌کند که قیدهای قطعی را می‌داند. برای ترکیب‌های
       مشکوک، منبع کاربر حفظ می‌شود و درخواست واقعی فرستاده
       می‌شود.

    ⚠️ جایگزینی **شفاف** است و لاگ می‌شود، چون کاربر باید بداند
       قیمت‌ها از کدام صرافی آمده.
    """
    # ─── تبدیل OHLCV ندارد → نوبیتکس ───
    # ⚠️ جایگزینی فقط به‌خاطر **کندل** است. قیمت نمایشی
    #    همچنان مستقل از خود تبدیل گرفته می‌شود (quote جدا).
    if source_lacks_ohlcv(source):
        logger.info(f"[DataService] «{source}» کندل ندارد — استفاده از نوبیتکس")
        return "nobitex"

    if is_ohlcv_supported(tf_name, source):
        return source

    # ─── منبع اصلی نمی‌تواند → اولین جایگزین ───
    for candidate in _FALLBACK_ORDER:
        if candidate == source:
            continue
        if is_ohlcv_supported(tf_name, candidate):
            logger.info(
                f"[DataService] «{source}» تایم‌فریم «{tf_name}» را ندارد "
                f"— استفاده از «{candidate}»"
            )
            return candidate

    logger.warning(
        f"[DataService] هیچ منبعی «{tf_name}» را ندارد — از «{source}» تلاش می‌کنیم"
    )
    return source


# ═══════════════════════════════════════════════════════════
# OHLCV
# ═══════════════════════════════════════════════════════════
def fetch_ohlcv(
    ticker,
    tf_name,
    source="nobitex",
    use_cache=True,
):
    """
    دریافت OHLCV با کش، single-flight و کش منفی.

    Args:
        ticker: نماد (BTC-USD، فولاد، ...)
        tf_name: نام فارسی تایم‌فریم («۵ دقیقه»، «روزانه»، ...)
        source: منبع درخواستی کاربر
        use_cache: استفاده از کش

    Returns:
        DataFrame با ایندکس **UTC-aware**، یا None
    """
    if not ticker:
        return None

    if not tf_name:
        logger.error("[DataService] tf_name خالی")
        return None

    # ═══ قید قطعی: TSETMC فقط روزانه ═══
    if source == "tsetmc" and tf_name != "روزانه":
        logger.debug(f"[DataService] TSETMC فقط روزانه — «{tf_name}» رد شد")
        return None

    spec = get_tf_spec(tf_name)
    interval, period = spec.interval, spec.period

    # ═══ انتخاب منبع نهایی (فقط برای قیدهای قطعی) ═══
    effective_source = _resolve_source_for_tf(source, tf_name)

    cache_key = f"ohlcv:{ticker}:{source}:{tf_name}"

    if use_cache:
        # ─── ۱. کش مثبت ───
        cached = data_cache.get(cache_key)
        if cached is not None:
            # 🔴 کپی اجباری (نسخه ۱.۸ — رفع race condition)
            #
            # چرا: ``compute_indicators`` ستون‌های اندیکاتور را **روی
            # همین DataFrame** می‌نویسد (``df["rsi"] = ...``). اگر
            # همان آبجکت کش‌شده به چند فراخوانی داده شود، دو thread
            # هم‌زمان روی یک آبجکت می‌نویسند و pandas با خطای
            # ``Length of values does not match length of index``
            # می‌شکند → تحلیل کاملاً خالی برمی‌گردد.
            #
            # این دقیقاً همان «جدول TF رندوم عوض می‌شود» بود: React
            # StrictMode دو درخواست هم‌زمان می‌زند و نتیجه صفر می‌شد.
            #
            # کپی shallow کافی است چون فقط **ستون** اضافه می‌شود،
            # ولی برای اطمینان از استقلال کامل، deep می‌کنیم.
            # هزینه: ~۱ms برای ۵۰۰ کندل — در برابر تحلیل ۲۰۰ms ناچیز.
            return cached.copy(deep=True)

        # ─── ۲. کش منفی ───
        if get_negative(cache_key):
            logger.debug(f"[DataService] کش منفی: {cache_key}")
            return None

    # ═══ single-flight: فقط یک thread شبکه را می‌زند ═══
    with key_lock(cache_key):
        if use_cache:
            cached = data_cache.get(cache_key)
            if cached is not None:
                return cached.copy(deep=True)
            if get_negative(cache_key):
                return None

        return _fetch_ohlcv_uncached(
            ticker=ticker,
            tf_name=tf_name,
            source=source,
            effective_source=effective_source,
            interval=interval,
            period=period,
            cache_key=cache_key,
            use_cache=use_cache,
        )


def _fetch_ohlcv_uncached(
    *,
    ticker: str,
    tf_name: str,
    source: str,
    effective_source: str,
    interval: str,
    period: str,
    cache_key: str,
    use_cache: bool,
):
    """
    دریافت واقعی — بدون کش. فقط از داخل ``key_lock`` صدا زده شود.

    ═══ استراتژی (نسخه ۱.۶) ═══
    زنجیره‌ی صرافی‌ها را طی می‌کنیم و هر پاسخ را **اعتبارسنجی**
    می‌کنیم:

      ۱. دیتا خالی/None → صرافی بعدی
      ۲. دیتا آمد ولی بازه‌ی کندل با TF نمی‌خواند → صرافی بعدی
         (🔴 این حالت والکس را می‌گیرد: res=15 → کندل ۱ دقیقه)
      ۳. دیتای درست → برگردان و کش کن

    این روش به whitelist نیازی ندارد: **پاسخ واقعی صرافی**
    تصمیم می‌گیرد، پس پشتیبانی per-نماد هم درست کار می‌کند.

    ═══ خطای قطعی در برابر موقت ═══
      • همه‌ی صرافی‌ها امتحان شدند و هیچ‌کدام دیتای درست نداشتند
        → خطای **قطعی** → کش منفی ۲۴ ساعته
      • استثنا/خطای شبکه در همه
        → خطای **موقت** → کش منفی ۵ دقیقه‌ای
    """
    # ═══ ترتیب صرافی‌ها: منبع کاربر اول، بعد بقیه ═══
    chain: list[str] = []
    _, resolved_source, switch_msg = resolve_symbol_and_source(ticker, effective_source)
    if switch_msg:
        logger.info(f"[DataService] {switch_msg}")

    if resolved_source:
        chain.append(resolved_source)
    for candidate in _FALLBACK_ORDER:
        if candidate not in chain and is_ohlcv_supported(tf_name, candidate):
            chain.append(candidate)

    if not chain:
        logger.warning(f"[DataService] هیچ صرافی‌ای برای {ticker}/{tf_name}")
        if use_cache:
            set_negative(cache_key, ttl=NEGATIVE_TTL_STATIC, permanent=True)
        return None

    tried: list[str] = []
    mismatched: list[str] = []

    for candidate in chain:
        tried.append(candidate)
        try:
            df = fetch_history_by_source(
                ticker=ticker,
                interval=interval,
                period=period,
                source=candidate,
                tf_name=tf_name,
            )
        except Exception:
            logger.exception(
                f"[DataService] خطا در {candidate} برای {ticker}/{tf_name}"
            )
            continue

        # ─── ۱. دیتا خالی ───
        if df is None or df.empty:
            logger.debug(f"[DataService] {candidate} دیتا نداد — بعدی")
            continue

        # ─── ۲. بازه‌ی اشتباه → رد کن ───
        if not interval_matches_tf(df, tf_name):
            detail = interval_mismatch_detail(df, tf_name)
            mismatched.append(candidate)
            logger.warning(
                f"[DataService] ⚠️ {candidate} کندل اشتباه داد ({detail}) "
                f"— صرافی بعدی"
            )
            continue

        # ─── ۳. موفق ───
        if use_cache:
            data_cache.set(cache_key, df, get_ttl(tf_name))
            clear_negative(cache_key)

        # ─── منبع **واقعی** دیتا (ممکن است با candidate فرق کند،
        #     چون زنجیره‌ی داخلی fallback هم هست) ───
        actual = get_data_source(df, candidate)
        if actual != source:
            logger.info(
                f"[DataService] {ticker}/{tf_name}: دیتا از «{actual}» "
                f"(درخواست کاربر: «{source}»)"
            )
        return df

    # ═══ همه‌ی صرافی‌ها امتحان شدند ═══
    if use_cache:
        # ─── اگر فقط مشکل «بازه‌ی اشتباه» بود → ساختاری ───
        # ─── اگر خطای شبکه بود → گذرا ───
        # ⚠️ TTL کوتاه است (۱۰ دقیقه / ۲ دقیقه) تا سیستم خودش را
        #    بازیابی کند — صرافی ممکن است برگردد یا TF اضافه شود.
        structural = bool(mismatched) or not is_valid_nobitex_symbol(ticker)
        ttl = NEGATIVE_TTL_STATIC if structural else NEGATIVE_TTL_TRANSIENT
        set_negative(cache_key, ttl=ttl, permanent=structural)
        logger.info(
            f"[DataService] دیتا نیامد: {ticker}/{tf_name} "
            f"(صرافی‌های امتحان‌شده: {tried}"
            + (f"، بازه‌ی نامنطبق: {mismatched}" if mismatched else "")
            + f") — کش منفی {'ساختاری' if structural else 'گذرا'} ({ttl}s)"
        )

    return None


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای
# ═══════════════════════════════════════════════════════════
def fetch_quote(ticker, source="nobitex"):
    """
    قیمت لحظه‌ای — **مستقل از هر صرافی**.

    ═══ قاعده (نسخه ۱.۷) ═══
    هرگز قیمت صرافی دیگر را با برچسب این صرافی برنگردان.
    اگر صرافی این بازار را ندارد → ``None``.

    چرا: صفحه‌ی «مقایسه قیمت» باید اسپرد **واقعی** بین صرافی‌ها
    را نشان دهد. fallback بی‌صدا آن را بی‌معنی می‌کند و کاربر
    فکر می‌کند بازارها یکی هستند.

    🔴 باگ رفع‌شده: پیش‌تر برای آبان‌تتر + جفت تتری، قیمت نوبیتکس
       با برچسب صرافی دیگر برگردانده می‌شد → دو ردیف یکسان.
    """
    cache_key = f"quote:{ticker}:{source}"
    cached = quote_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        result = fetch_quote_by_source(ticker, source)
    except Exception:
        logger.exception(f"[Quote] خطا در {ticker}/{source}")
        result = None

    if result:
        quote_cache.set(cache_key, result, 5)
    return result


def get_iran_prices():
    cache_key = "iran_prices"
    cached = data_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        result = fetch_iran_prices()
        data_cache.set(cache_key, result, 60)
        return result
    except Exception:
        logger.exception("[DataService] خطا در iran_prices")
        return {"prices": {}, "source": "None", "timestamp": ""}


def get_default_symbol(source):
    try:
        return get_default_symbol_for_source(source)
    except Exception:
        logger.exception(f"[DataService] default symbol برای {source}")
        return "BTC-USD"
