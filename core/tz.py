"""
core/tz.py
مدیریت متمرکز timezone — تنها منبع حقیقت پروژه
============================================================
مشکلی که این ماژول حل می‌کند:

    پیش از این، هر fetcher ایندکس را متفاوت می‌ساخت:
      • nobitex_fetcher  → tz-aware UTC        (pd.to_datetime(..., utc=True))
      • bitpin_fetcher   → tz-NAIVE وقت محلی   (pd.to_datetime(...))
      • wallex_fetcher   → tz-NAIVE وقت محلی   (pd.to_datetime(...))
      • tsetmc_fetcher   → tz-NAIVE تاریخ تقویمی

    و backtest_service ایندکس را با یک datetime «UTC-naive» مقایسه می‌کرد.
    برای منابع naive، این مقایسه ۳:۳۰ ساعت شیفت می‌خورد و فیلتر
    «کندل‌های بعد از ثبت سیگنال» بی‌اثر می‌شد.

قرارداد این ماژول:
    ── هر DataFrame ای که از لایه داده بیرون می‌آید باید
       ایندکسش **UTC-aware** باشد. ──

تشخیص تجربی (۲۰۲۶-۱۰-۰۳):
    Bitpin   ts=1791030600 → 12:30Z (کندل ۱ ساعته) ✓ UTC
    Wallex   ts=1791032400 → 13:00Z               ✓ UTC
    یعنی epoch هر دو صرافی UTC است.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ─── ثابت‌های timezone ───
UTC = timezone.utc
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))
TEHRAN = "Asia/Tehran"


# ═══════════════════════════════════════════════════════════
# نرمال‌سازی ایندکس
# ═══════════════════════════════════════════════════════════
def ensure_utc_index(
    df: Optional[pd.DataFrame],
    *,
    assume_tz: Optional[str] = None,
    copy: bool = False,
) -> Optional[pd.DataFrame]:
    """
    ایندکس DataFrame را به UTC-aware نرمال می‌کند.

    Args:
        df: دیتافریم OHLCV (یا هر دیتافریمی با ایندکس زمانی)
        assume_tz:
            - ``None`` (پیش‌فرض): ایندکس naive را **UTC** فرض می‌کند.
              این حالت برای بیت‌پین/والکس درست است، چون epoch آن‌ها UTC است.
            - ``"Asia/Tehran"`` و مانند آن: naive را به آن timezone
              نسبت می‌دهد و بعد به UTC تبدیل می‌کند. برای تاریخ تقویمی
              TSETMC (نیمه‌شب تهران) لازم است.
        copy: اگر True، کپی می‌گیرد و دیتافریم اصلی را دست نمی‌زند.

    Returns:
        همان دیتافریم با ایندکس UTC-aware (in-place مگر copy=True).
        ورودی None/خالی بدون تغییر برمی‌گردد.

    Raises:
        هیچ استثنایی پرتاب نمی‌کند — در صورت شکست، دیتافریم اصلی
        برگردانده می‌شود و هشدار لاگ می‌شود.
    """
    if df is None or df.empty:
        return df

    try:
        if copy:
            df = df.copy()

        idx = df.index

        # ─── حالت ۱: ایندکس از قبل DatetimeIndex است ───
        if isinstance(idx, pd.DatetimeIndex):
            if idx.tz is not None:
                # tz-aware → فقط به UTC تبدیل کن
                df.index = idx.tz_convert("UTC")
            elif assume_tz:
                # naive + timezone مشخص → محلی‌سازی، بعد UTC
                localized = idx.tz_localize(
                    assume_tz, ambiguous="NaT", nonexistent="NaT"
                )
                df.index = localized.tz_convert("UTC")
            else:
                # naive + بدون timezone → UTC فرض کن
                df.index = idx.tz_localize("UTC")
            return df

        # ─── حالت ۲: ایندکس رشته/عدد است → تبدیل اجباری ───
        converted = pd.to_datetime(idx, errors="coerce", utc=True)
        mask = ~pd.isna(converted)
        if not mask.all():
            logger.warning(
                f"[tz] {int((~mask).sum())} ایندکس نامعتبر حذف شد"
            )
            df = df[mask]
            converted = converted[mask]
        df.index = converted
        return df

    except Exception as e:
        logger.error(f"[tz] ensure_utc_index شکست خورد: {e!r} — دیتافریم بدون تغییر")
        return df


def is_utc_aware(df: Optional[pd.DataFrame]) -> bool:
    """آیا ایندکس دیتافریم UTC-aware است؟"""
    if df is None or df.empty:
        return False
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        return False
    if idx.tz is None:
        return False
    return str(idx.tz) in ("UTC", "utc")


# ═══════════════════════════════════════════════════════════
# تبدیل datetime
# ═══════════════════════════════════════════════════════════
def utc_now() -> datetime:
    """زمان فعلی UTC با timezone — جانشین datetime.utcnow()"""
    return datetime.now(UTC)


def to_utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """
    datetime را به **UTC-naive** تبدیل می‌کند.

    کاربرد: مقایسه با ایندکس pandas که با ``tz_localize(None)``
    از UTC-aware ساخته شده.

    ⚠️ datetime بدون tz را **UTC** فرض می‌کند (نه وقت محلی)،
       چون تمام timestampهای دیتابیس و مدل‌ها UTC هستند.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def to_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    datetime را به **UTC-aware** تبدیل می‌کند.

    کاربرد: سریالization برای فرانت، تا ``isoformat()`` با ``+00:00``
    تمام شود و ``new Date(iso)`` در مرورگر درست پارس کند.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_iran(dt: Optional[datetime]) -> Optional[datetime]:
    """datetime را به وقت ایران تبدیل می‌کند (برای نمایش)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IRAN_TZ)


def iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """
    رشته‌ی ISO **با timezone** — برای پاسخ‌های API.

    مثال: ``"2026-10-03T12:30:00+00:00"`` — این را
    ``new Date(...)`` در مرورگر درست پارس می‌کند، برخلاف
    ``"2026-10-03T12:30:00"`` که به وقت محلی کاربر تفسیر می‌شود.
    """
    if dt is None:
        return None
    return to_utc_aware(dt).isoformat()


# ═══════════════════════════════════════════════════════════
# مقایسه‌ی امن با ایندکس
# ═══════════════════════════════════════════════════════════
def filter_from(df: pd.DataFrame, since: datetime) -> pd.DataFrame:
    """
    کندل‌های «از یک لحظه به بعد» را برمی‌گرداند — مستقل از tz ایندکس.

    این تابع جای مقایسه‌ی دستی و پرخطای
    ``df[df.index.tz_localize(None) >= entry_naive]`` را می‌گیرد.

    Args:
        df: دیتافریم با ایندکس UTC-aware (خروجی ensure_utc_index)
        since: لحظه‌ی شروع (aware یا naive-به‌معنی-UTC)

    Returns:
        دیتافریم فیلترشده؛ در صورت شکست، df بدون تغییر.
    """
    if df is None or df.empty:
        return df

    cutoff = to_utc_aware(since)  # naive → UTC فرض می‌شود

    try:
        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
            return df[df.index >= cutoff]

        # ─── ایندکس naive → نرمال‌سازی کن، بعد فیلتر ───
        logger.warning("[tz] filter_from روی ایندکس naive — نرمال‌سازی اجباری")
        normalized = ensure_utc_index(df, copy=True)
        return normalized[normalized.index >= cutoff]

    except Exception as e:
        logger.error(f"[tz] filter_from شکست خورد: {e!r} — دیتافریم بدون فیلتر")
        return df


# ═══════════════════════════════════════════════════════════
# تست دستی
# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════
# اعتبارسنجی بازه‌ی کندل
# ═══════════════════════════════════════════════════════════
# ⚠️ چرا لازم است (نسخه ۱.۶):
#
# برخی صرافی‌ها وقتی resolution درخواستی را «نزدیک» می‌بینند،
# بی‌سروصدا کندل **ریزتری** برمی‌گردانند:
#
#     والکس + res=15  →  ۲۸۷۱۷ کندل ۱ دقیقه‌ای (!)
#
# این خطرناک‌ترین نوع باگ است: ATR و SL/TP روی کندل ۱ دقیقه
# محاسبه می‌شود ولی به کاربر «۱۵ دقیقه» نشان داده می‌شود.
# تحلیل کاملاً بی‌اعتبار می‌شود و کاربر نمی‌فهمد.
#
# راه‌حل: بازه‌ی غالب کندل‌های برگشتی را اندازه بگیر و اگر با
# TF درخواستی نمی‌خواند، دیتا را **رد کن** تا زنجیره‌ی fallback
# به صرافی‌ای برود که کندل درست می‌دهد.

# ─── طول هر TF به ثانیه ───
TF_SECONDS: dict[str, int] = {
    "۱ دقیقه": 60,
    "۵ دقیقه": 300,
    "۱۵ دقیقه": 900,
    "۳۰ دقیقه": 1800,
    "۱ ساعت": 3600,
    "روزانه": 86400,
}

# ─── تلورانس مجاز (٪) ───
# کندل‌های واقعی همه‌جا کارمزد تعطیلی و شکاف دارند، پس
# بازه‌ی غالب می‌تواند ±۵٪ بچرخد (مثلاً ۵ دقیقه در بازار آرام
# گاهی ۳۰۱-۳۰۲ ثانیه است). ولی ۶۰ در برابر ۹۰۰ = ۹۳٪ خطا.
_TF_TOLERANCE_PCT = 10.0


def dominant_interval_seconds(df: Optional[pd.DataFrame]) -> Optional[int]:
    """
    بازه‌ی **غالب** بین کندل‌ها را به ثانیه برمی‌گرداند.

    چرا «غالب» و نه «میانگین»: بازار تعطیلات و شکاف دارد؛
    یک شکاف ۳ روزه میانگین را نابود می‌کند ولی مد تأثیر نمی‌گیرد.

    Returns:
        ثانیه، یا ``None`` اگر قابل محاسبه نباشد.
    """
    if df is None or df.empty or len(df) < 3:
        return None

    try:
        idx = df.index
        if not isinstance(idx, pd.DatetimeIndex):
            return None

        idx = idx.sort_values()
        deltas = idx.to_series().diff().dropna().dt.total_seconds()
        deltas = deltas[deltas > 0]
        if deltas.empty:
            return None

        # ─── مد (غالب‌ترین بازه) ───
        rounded = deltas.round().astype(int)
        return int(rounded.mode().iloc[0])

    except Exception as e:
        logger.debug(f"[tz] dominant_interval: {e}")
        return None


def interval_matches_tf(
    df: Optional[pd.DataFrame],
    tf_name: str,
    *,
    tolerance_pct: float = _TF_TOLERANCE_PCT,
) -> bool:
    """
    آیا بازه‌ی کندل‌های برگشتی با TF درخواستی می‌خواند؟

    Args:
        df: دیتافریم OHLCV
        tf_name: نام فارسی تایم‌فریم
        tolerance_pct: تلورانس مجاز به درصد

    Returns:
        True اگر بخواند **یا** اگر قابل اندازه‌گیری نباشد
        (fail-open: با دیتای کم نمی‌خواهیم بی‌دلیل رد کنیم).
    """
    expected = TF_SECONDS.get(tf_name)
    if expected is None:
        return True  # ─── TF ناشناخته: قضاوت نکن ───

    actual = dominant_interval_seconds(df)
    if actual is None:
        return True  # ─── دیتای کافی برای قضاوت نیست ───

    deviation = abs(actual - expected) / expected * 100
    return deviation <= tolerance_pct


def interval_mismatch_detail(
    df: Optional[pd.DataFrame], tf_name: str
) -> str:
    """توضیح خوانا برای لاگ وقتی بازه نمی‌خواند"""
    expected = TF_SECONDS.get(tf_name, 0)
    actual = dominant_interval_seconds(df)
    return f"TF درخواستی «{tf_name}» ({expected}s) ولی کندل‌ها {actual}s هستند"


if __name__ == "__main__":
    print("=" * 62)
    print("تست core/tz.py")
    print("=" * 62)

    # ─── ۱. naive → UTC ───
    raw = pd.DataFrame(
        {"close": [1.0, 2.0]},
        index=pd.to_datetime(["2026-01-01 12:00:00", "2026-01-01 12:05:00"]),
    )
    out = ensure_utc_index(raw)
    print("۱) naive→UTC :", out.index[0], "| tz:", out.index.tz)

    # ─── ۲. aware UTC بدون تغییر ───
    raw2 = pd.DataFrame(
        {"close": [1.0]}, index=pd.to_datetime(["2026-01-01T12:00:00Z"])
    )
    out2 = ensure_utc_index(raw2)
    print("۲) aware→UTC :", out2.index[0])

    # ─── ۳. Tehran → UTC ───
    raw3 = pd.DataFrame(
        {"close": [1.0]}, index=pd.to_datetime(["2026-01-01 03:30:00"])
    )
    out3 = ensure_utc_index(raw3, assume_tz=TEHRAN)
    print("۳) Tehran→UTC:", out3.index[0], "(باید 00:00Z باشد)")

    # ─── ۴. filter_from ───
    df = pd.DataFrame(
        {"close": range(5)},
        index=pd.date_range("2026-01-01 00:00", periods=5, freq="5min", tz="UTC"),
    )
    entry = datetime(2026, 1, 1, 0, 10, tzinfo=UTC)
    print("۴) filter_from:", len(filter_from(df, entry)), "از", len(df), "(باید ۳ باشد)")

    # ─── ۵. کمکی‌ها ───
    print("۵) iso_utc    :", iso_utc(datetime(2026, 1, 1, 0, 0)))
    print("   to_iran    :", to_iran(datetime(2026, 1, 1, 0, 0)).strftime("%H:%M"))
    print()
    print("[OK] تست کامل شد.")
