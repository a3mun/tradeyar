"""
services/data_service.py
لایه دیتا — با کش، single-flight و کش منفی تفکیک‌شده
============================================================
نسخه ۱.۷ — اعتبارسنجی OHLCV (Data Validation) اضافه شد.

🔴 تغییرات نسخه ۱.۷:
  • تابع `_validate_ohlcv` برای حذف کندل‌های تکراری، OHLC اشتباه و مرتب‌سازی زمانی.
  • اعتبارسنجی **قبل از** ذخیره در کش انجام می‌شود تا `single-flight` سالم بماند.
"""

import logging
import pandas as pd

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
# 🔴 فاز ۱۰.۸ — اعتبارسنجی OHLCV
# ═══════════════════════════════════════════════════════════
def _validate_ohlcv(df: pd.DataFrame, tf_name: str, source: str) -> pd.DataFrame | None:
    """
    اعتبارسنجی دیتای OHLCV — جلوگیری از ورود دیتای خراب به موتور تحلیل.
    """
    if df is None or df.empty:
        return None

    original_len = len(df)

    # ─── ۱. حذف کندل‌های تکراری ───
    df = df[~df.index.duplicated(keep="last")]

    # ─── ۲. حذف OHLC اشتباه (فقط اگه ستون‌ها موجود باشن) ───
    required_cols = {"high", "low", "open", "close"}
    if required_cols.issubset(df.columns):
        invalid_mask = (
            (df["high"] < df["low"])
            | (df["high"] < df["open"])
            | (df["high"] < df["close"])
            | (df["low"] > df["open"])
            | (df["low"] > df["close"])
        )
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            logger.warning(
                f"[DataService] {source} {tf_name}: {invalid_count} کندل OHLC نامعتبر — حذف شد"
            )
            df = df[~invalid_mask]
    else:
        logger.debug(
            f"[DataService] {source} {tf_name}: ستون‌های OHLC کامل نیستن — اعتبارسنجی OHLC رد شد"
        )

    # ─── ۳. مرتب‌سازی زمانی ───
    if not df.index.is_monotonic_increasing:
        logger.warning(
            f"[DataService] {source} {tf_name}: ترتیب زمانی به هم ریخته — مرتب شد"
        )
        df = df.sort_index()

    # ─── ۴. حذف کندل‌های با حجم صفر یا منفی (فقط اگه ستون volume موجود باشه) ───
    if "volume" in df.columns:
        df = df[df["volume"] > 0]

    if len(df) < original_len:
        logger.info(
            f"[DataService] {source} {tf_name}: {original_len - len(df)} کندل نامعتبر حذف شد (باقیمانده: {len(df)})"
        )

    # 🔴 فاز ۱۰.۸ — اگه دیتا خیلی کم بود، به تحلیل‌گر واگذار کن (نه اینکه None برگردونی)
    # چون تست‌های single-flight از دیتافریم‌های کوچک استفاده می‌کنن.
    if df.empty:
        logger.warning(f"[DataService] {source} {tf_name}: دیتا خالی است")
        return None

    return df


# ═══════════════════════════════════════════════════════════
# زنجیره‌ی fallback
# ═══════════════════════════════════════════════════════════
_FALLBACK_ORDER = ["nobitex", "bitpin", "wallex"]


def _resolve_source_for_tf(source: str, tf_name: str) -> str:
    """
    اگر منبع انتخابی کاربر **قطعاً** این TF را نداشته باشد،
    اولین منبع جایگزین که دارد برگردانده می‌شود.
    """
    # ─── تبدیل OHLCV ندارد → نوبیتکس ───
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

        # ─── ۳. اعتبارسنجی دیتا (🔴 فاز ۱۰.۸) ───
        df = _validate_ohlcv(df, tf_name, candidate)
        if df is None:
            logger.warning(
                f"[DataService] ⚠️ {candidate} دیتای نامعتبر داد — صرافی بعدی"
            )
            continue

        # ─── ۴. موفق (ذخیره در کش) ───
        if use_cache:
            data_cache.set(cache_key, df, get_ttl(tf_name))
            clear_negative(cache_key)

        # ─── منبع **واقعی** دیتا ───
        actual = get_data_source(df, candidate)
        if actual != source:
            logger.info(
                f"[DataService] {ticker}/{tf_name}: دیتا از «{actual}» "
                f"(درخواست کاربر: «{source}»)"
            )
        return df

    # ═══ همه‌ی صرافی‌ها امتحان شدند ═══
    if use_cache:
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
