"""
services/cache.py
کش in-memory با TTL — برای دیتا و تحلیل
============================================================
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple, Optional

import pandas as pd

logger = logging.getLogger(__name__)

UTC = timezone.utc


class TTLCache:
    """کش ساده in-memory با TTL"""

    def __init__(self, max_size: int = 500):
        self._store: dict[str, tuple[Any, float]] = {}
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        # ─── حذف قدیمی‌ها اگه پر شد ───
        if len(self._store) >= self._max_size:
            now = time.time()
            expired = [k for k, (_, exp) in self._store.items() if exp < now]
            for k in expired:
                del self._store[k]
            # اگه هنوز پر، قدیمی‌ترین رو پاک کن
            if len(self._store) >= self._max_size:
                oldest = min(self._store.items(), key=lambda x: x[1][1])
                del self._store[oldest[0]]

        self._store[key] = (value, time.time() + ttl)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


# ═══════════════════════════════════════════════════════════
# TTL بر اساس TF (ثانیه)
# ═══════════════════════════════════════════════════════════
TF_TTL = {
    "۱ دقیقه": 30,
    "۵ دقیقه": 120,
    "۱۵ دقیقه": 300,
    "۳۰ دقیقه": 600,
    "۱ ساعت": 900,
    "روزانه": 1800,
}


def get_ttl(tf_name: str) -> int:
    return TF_TTL.get(tf_name, 120)


# ═══════════════════════════════════════════════════════════
# Fingerprint بر اساس آخرین کندلِ **بسته**
# ═══════════════════════════════════════════════════════════
# باگ ۸ (نسخه ۱.۵)
# ------------------------------------------------------------
# پیش از این، fingerprint از ``df.iloc[-1]`` ساخته می‌شد — یعنی
# کندلی که **هنوز در حال تشکیل است**. Close آن کندل هر ثانیه
# عوض می‌شود، پس هش هر بار متفاوت بود و کش **هیچ‌وقت hit
# نمی‌شد**:
#
#     کاربر هر ۳۰ ثانیه «تحلیل» می‌زند
#       → fingerprint جدید
#       → cache miss
#       → ~۲۰ اندیکاتور از صفر محاسبه می‌شود (EMA200، Ichimoku، CVD)
#
# و TTL تعریف‌شده در ``TF_TTL`` عملاً بی‌اثر بود.
#
# حالا:
#   • fingerprint از آخرین کندل **بسته** ساخته می‌شود
#   • در طول یک کندل پایدار است → کش واقعاً کار می‌کند
#   • با بسته شدن کندل جدید عوض می‌شود → تحلیل تازه

# ─── طول هر TF به ثانیه (برای تشخیص کندل باز) ───
TF_SECONDS: dict[str, int] = {
    "۱ دقیقه": 60,
    "۵ دقیقه": 300,
    "۱۵ دقیقه": 900,
    "۳۰ دقیقه": 1800,
    "۱ ساعت": 3600,
    "روزانه": 86400,
}
_DEFAULT_TF_SECONDS = 300


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _unwrap_index(idx) -> Optional[datetime]:
    """
    ایندکس کندل را به datetime **UTC-aware** تبدیل می‌کند.

    ورودی ممکن است aware یا naive باشد؛ naive را UTC فرض می‌کنیم
    (قرارداد ``core.tz``).
    """
    try:
        ts = pd.Timestamp(idx)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts.tz_convert("UTC").to_pydatetime()
    except Exception:
        return None


def is_candle_closed(
    candle_time: datetime,
    tf_name: str,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """
    آیا این کندل بسته شده است؟

    یک کندل با زمان شروع ``t`` و طول ``L`` در ``t + L`` بسته می‌شود.

    Args:
        candle_time: زمان شروع کندل (aware یا naive-UTC)
        tf_name: نام فارسی تایم‌فریم
        now: زمان مرجع — برای تست قابل تزریق است
    """
    tf_sec = TF_SECONDS.get(tf_name, _DEFAULT_TF_SECONDS)
    current = now or _utc_now()

    if candle_time.tzinfo is None:
        candle_time = candle_time.replace(tzinfo=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    return candle_time + timedelta(seconds=tf_sec) <= current


def closed_candles(
    df: pd.DataFrame,
    tf_name: str,
    *,
    now: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    فقط کندل‌های **بسته‌شده** را برمی‌گرداند.

    کندل آخری که هنوز در حال تشکیل است حذف می‌شود، چون:
      ۱. OHLC آن ثابت نیست → cache key ناپایدار
      ۲. استفاده از آن = repainting (سیگنالی که بعداً عوض می‌شود)

    Args:
        df: دیتافریم OHLCV
        tf_name: نام فارسی تایم‌فریم
        now: زمان مرجع — برای تست

    Returns:
        دیتافریم بدون کندل باز.
        • ورودی ``None`` → ``None``
        • دیتافریم خالی → دیتافریم خالی
        • اگر همه‌ی کندل‌ها باز باشند → دیتافریم خالی
    """
    if df is None:
        return None
    if df.empty:
        return df

    close_times = [_unwrap_index(i) for i in df.index]

    # ─── اگر هیچ ایندکسی قابل تبدیل نبود، فقط آخرین را حذف کن ───
    if all(t is None for t in close_times):
        return df.iloc[:-1] if len(df) > 1 else df.iloc[0:0]

    keep = [
        i
        for i, t in enumerate(close_times)
        if t is not None and is_candle_closed(t, tf_name, now=now)
    ]

    if not keep:
        return df.iloc[0:0]

    return df.iloc[keep]


def make_fingerprint(
    df,
    tf_name: str = "۵ دقیقه",
    *,
    now: Optional[datetime] = None,
) -> str:
    """
    هش پایدار از آخرین ۲ کندلِ **بسته** + طول سری.

    Args:
        df: دیتافریم OHLCV با ایندکس زمانی
        tf_name: نام فارسی تایم‌فریم (تعیین‌کننده‌ی طول کندل)
        now: زمان مرجع — **برای تست** قابل تزریق است.
             پیش‌فرض ``datetime.now(UTC)``.

    Returns:
        هش ۱۲ کاراکتری، یا ``"empty"``/``"error"``.

    تضمین‌ها:
      • در طول یک کندل **پایدار** است → کش hit می‌شود
      • با بسته شدن کندل جدید **عوض** می‌شود → تحلیل تازه
      • تغییر close کندل باز روی آن **اثر ندارد**
    """
    try:
        if df is None or df.empty:
            return "empty"

        closed = closed_candles(df, tf_name, now=now)
        if closed is None or len(closed) < 2:
            # ─── دیتای کافی برای هش پایدار نیست ───
            return "empty"

        last = closed.iloc[-1]
        prev = closed.iloc[-2]

        # ─── timestamp کندل بسته + close آن ───
        try:
            last_ts = pd.Timestamp(closed.index[-1]).isoformat()
            prev_ts = pd.Timestamp(closed.index[-2]).isoformat()
        except Exception:
            last_ts, prev_ts = str(closed.index[-1]), str(closed.index[-2])

        raw = (
            f"{last_ts}|{float(last['close']):.8f}|"
            f"{prev_ts}|{float(prev['close']):.8f}|{len(closed)}"
        )
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    except Exception as e:
        logger.warning(f"[Fingerprint] {e}")
        return "error"


# ═══════════════════════════════════════════════════════════
# نخ‌های در حال ساخت (جلوگیری از thundering herd)
# ═══════════════════════════════════════════════════════════
# مسئله (باگ ۶): در `/scan` چند نماد **هم‌زمان** درخواست همان
# ticker/TF را می‌دهند. بدون این مکانیزم، همه هم‌زمان cache miss
# می‌خورند و N بار درخواست شبکه‌ای یکسان می‌فرستند.
#
# راه‌حل سبک (بدون وابستگی جدید): قفل per-key.
# thread اول شبکه را می‌زند، بقیه منتظر می‌مانند و از کش می‌خوانند.
_key_locks: dict[str, threading.Lock] = {}
_key_locks_guard = threading.Lock()

# ─── سقف تعداد قفل هم‌زمان (جلوگیری از رشد بی‌نهایت) ───
_MAX_KEY_LOCKS = 256


def key_lock(key: str) -> threading.Lock:
    """
    قفل مخصوص یک کلید کش — برای الگوی single-flight.

    مثال استفاده::

        with key_lock(cache_key):
            cached = data_cache.get(cache_key)
            if cached is not None:
                return cached
            value = expensive_fetch()
            data_cache.set(cache_key, value, ttl)
            return value
    """
    with _key_locks_guard:
        lock = _key_locks.get(key)
        if lock is None:
            if len(_key_locks) >= _MAX_KEY_LOCKS:
                # ─── پاک‌سازی قفل‌های آزاد ───
                for k in [k for k, l in _key_locks.items() if not l.locked()]:
                    del _key_locks[k]
                    if len(_key_locks) < _MAX_KEY_LOCKS:
                        break
            lock = threading.Lock()
            _key_locks[key] = lock
        return lock


# ═══════════════════════════════════════════════════════════
# کش منفی — جلوگیری از تلاش مکرر برای دیتای ناموجود
# ═══════════════════════════════════════════════════════════
# ⚠️ این مهم‌ترین اصلاح کارایی `/scan` است.
#
# مسئله: نمادهایی مثل TON-USD و MATIC-USD روی نوبیتکس نیستند و
# API کد 400 می‌دهد. چون `fetch_ohlcv` فقط نتیجه‌ی **موفق** را کش
# می‌کرد، هر اسکن مجدداً کل زنجیره‌ی fallback را با retry و
# timeout برای هر نماد می‌زد → یک اسکن ۱۵ نمادی **۲۷۷ ثانیه**.
#
# حالا شکست هم به خاطر سپرده می‌شود.
_negative_cache = TTLCache(max_size=2000)

# ─── مدت به‌خاطرسپاری شکست (نسخه ۱.۷) ───
# ⚠️ تغییر مهم: پیش‌تر «قطعی» ۲۴ ساعت کش می‌شد. مشکل:
#    اگر صرافی لحظه‌ای مشکل داشت یا TF جدید اضافه می‌شد، آن
#    ترکیب یک روز کامل خاموش می‌ماند و کاربر «خالی» می‌دید.
#
# حالا هر دو کوتاه‌اند تا سیستم خودش را بازیابی کند. تفکیک
# حفظ شده چون خطای موقت (شبکه) باید حتی سریع‌تر فراموش شود.
NEGATIVE_TTL_STATIC = 600  # ۱۰ دقیقه — نماد/TF واقعاً وجود ندارد
NEGATIVE_TTL_TRANSIENT = 120  # ۲ دقیقه — خطای شبکه/timeout

# ─── نام‌های قدیمی (سازگاری عقب‌رو) ───
NEGATIVE_TTL_PERMANENT = NEGATIVE_TTL_STATIC
NEGATIVE_TTL_TEMPORARY = NEGATIVE_TTL_TRANSIENT
NEGATIVE_TTL = NEGATIVE_TTL_STATIC

# ─── کلیدهای «نامعتبر ساختاری» تا در لاگ تفکیک شوند ───
_permanent_negative: set[str] = set()
_permanent_lock = threading.Lock()


def get_negative(key: str) -> bool:
    """آیا اخیراً این دیتا شکست خورده؟"""
    return _negative_cache.get(key) is not None


def get_negative_ttl(key: str) -> int:
    """TTL باقی‌مانده‌ی کش منفی (برای پیام بهتر)"""
    item = _negative_cache._store.get(key)  # noqa: SLF001
    if not item:
        return 0
    remaining = int(item[1] - time.time())
    return max(0, remaining)


def set_negative(
    key: str,
    ttl: int = NEGATIVE_TTL_STATIC,
    *,
    permanent: bool = True,
) -> None:
    """
    ثبت شکست برای مدتی.

    Args:
        key: کلید کش — **باید شامل صرافی باشد** تا شکست یک صرافی
             صرافی دیگر را بلاک نکند.
        ttl: مدت به‌خاطرسپاری (ثانیه)
        permanent: True = خطای ساختاری (نماد/TF وجود ندارد)
                   False = خطای گذرا (شبکه، timeout، ۵xx)
    """
    _negative_cache.set(key, True, ttl)
    with _permanent_lock:
        if permanent:
            _permanent_negative.add(key)
        else:
            _permanent_negative.discard(key)


def is_permanent_failure(key: str) -> bool:
    """آیا این شکست «قطعی» بود (نه موقت)؟"""
    with _permanent_lock:
        return key in _permanent_negative


def clear_negative(key: str) -> None:
    """پاک کردن شکست (وقتی دیتا موفق شد)"""
    _negative_cache._store.pop(key, None)  # noqa: SLF001
    with _permanent_lock:
        _permanent_negative.discard(key)


def clear_all_negative() -> None:
    """پاک‌سازی کامل کش منفی — برای تست"""
    _negative_cache.clear()
    with _permanent_lock:
        _permanent_negative.clear()


def negative_cache_stats() -> dict:
    """آمار کش منفی — برای observability"""
    with _permanent_lock:
        permanent = len(_permanent_negative)
    total = _negative_cache.size()
    return {
        "total": total,
        "permanent": permanent,
        "temporary": total - permanent,
    }


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════
data_cache = TTLCache(max_size=300)
analysis_cache = TTLCache(max_size=500)
quote_cache = TTLCache(max_size=200)
