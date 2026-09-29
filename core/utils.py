"""
core/utils.py
توابع کمکی — تاریخ، فرمت، اعداد، بازار، تایمر
نسخه ۲.۰ (فاز ۵)
============================================================
بهبودها:
  - market_status دقیق‌تر (بر اساس UTC و روزهای ایران)
  - time_ago با پشتیبانی از tz
  - format_price با پشتیبانی از تومان/دلار/ریال
  - حذف وابستگی‌های تکراری
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd

# ═══════════════════════════════════════════════════════════
# منطقه زمانی ایران
# ═══════════════════════════════════════════════════════════
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))
UTC_TZ = timezone.utc


# ═══════════════════════════════════════════════════════════
# اعداد فارسی/عربی → انگلیسی
# ═══════════════════════════════════════════════════════════
FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
EN_DIGITS = "0123456789"


def to_english_digits(text: str) -> str:
    """تبدیل اعداد فارسی/عربی به انگلیسی"""
    if not text:
        return text
    for fa, en in zip(FA_DIGITS, EN_DIGITS):
        text = text.replace(fa, en)
    for ar, en in zip(AR_DIGITS, EN_DIGITS):
        text = text.replace(ar, en)
    return text


def to_persian_digits(text: str) -> str:
    """تبدیل اعداد انگلیسی به فارسی"""
    if not text:
        return text
    for en, fa in zip(EN_DIGITS, FA_DIGITS):
        text = text.replace(en, fa)
    return text


# ═══════════════════════════════════════════════════════════
# پارس امن اعداد
# ═══════════════════════════════════════════════════════════
def parse_number(text) -> Optional[float]:
    """
    پارس امن اعداد از متن.
    مثال: '۲۴,۱۰۰,۰۰۰' → 24100000.0
    """
    if text is None:
        return None
    if isinstance(text, (int, float)):
        try:
            if pd.isna(text):
                return None
            return float(text)
        except (TypeError, ValueError):
            return None

    text = to_english_digits(str(text))

    start_idx = -1
    for i, ch in enumerate(text):
        if ch.isdigit():
            start_idx = i
            break

    if start_idx == -1:
        return None

    cleaned = ""
    for ch in text[start_idx:]:
        if ch.isdigit() or ch in ".-":
            cleaned += ch
        elif ch == ",":
            continue
        else:
            break

    if not cleaned or cleaned in (".", "-", "-."):
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════
# فرمت امن اعداد
# ═══════════════════════════════════════════════════════════
def safe_num(val, default: float = 0.0) -> float:
    """تبدیل امن هر چیز به float"""
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def format_price(price, unit: str = "تومان") -> str:
    """
    فرمت قیمت با توجه به واحد.

    Args:
        price: مقدار قیمت
        unit: 'تومان' / 'دلار' / 'ریال'
    """
    if price is None:
        return "—"
    try:
        if pd.isna(price):
            return "—"
    except (TypeError, ValueError):
        return "—"

    try:
        price = float(price)
    except (TypeError, ValueError):
        return "—"

    if unit == "دلار":
        return f"${price:,.2f}"

    if unit == "ریال":
        if price >= 1_000_000_000:
            return f"{price / 1_000_000_000:,.2f}B"
        elif price >= 1_000_000:
            return f"{price / 1_000_000:,.1f}M"
        elif price >= 1_000:
            return f"{price:,.0f}"
        return f"{price:,.2f}"

    # تومان
    if price >= 1_000_000_000:
        return f"{price / 1_000_000_000:,.2f}B"
    elif price >= 1_000_000:
        return f"{price / 1_000_000:,.1f}M"
    elif price >= 1_000:
        return f"{price:,.0f}"
    else:
        return f"{price:,.2f}"


def format_change(value: float, decimals: int = 2) -> str:
    """فرمت تغییرات درصدی با علامت"""
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except (TypeError, ValueError):
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_big_number(value: float) -> str:
    """فرمت اعداد بزرگ — 1.2M, 350K, ..."""
    v = safe_num(value)
    if v >= 1_000_000_000:
        return f"{v / 1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return f"{v:.2f}"


# ═══════════════════════════════════════════════════════════
# تاریخ و زمان
# ═══════════════════════════════════════════════════════════
def get_iran_time() -> datetime:
    """زمان فعلی ایران (UTC+3:30)"""
    return datetime.now(IRAN_TZ)


def get_utc_time() -> datetime:
    """زمان فعلی UTC"""
    return datetime.now(UTC_TZ)


def get_jalali_date() -> str:
    """تاریخ شمسی"""
    try:
        import jdatetime

        return jdatetime.datetime.now().strftime("%Y/%m/%d")
    except ImportError:
        return datetime.now().strftime("%Y-%m-%d")


def get_jalali_datetime() -> str:
    """تاریخ و ساعت شمسی"""
    try:
        import jdatetime

        return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    except ImportError:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_weekday_fa() -> str:
    """نام روز هفته به فارسی"""
    try:
        import jdatetime

        wd = jdatetime.datetime.now().weekday()
        days = ["شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]
        return days[wd]
    except ImportError:
        days = {
            0: "دوشنبه",
            1: "سه‌شنبه",
            2: "چهارشنبه",
            3: "پنج‌شنبه",
            4: "جمعه",
            5: "شنبه",
            6: "یک‌شنبه",
        }
        return days[datetime.now().weekday()]


def get_iran_clock() -> str:
    """ساعت ایران به فرمت HH:MM:SS"""
    return get_iran_time().strftime("%H:%M:%S")


def get_miladi_date() -> str:
    """تاریخ میلادی"""
    return get_iran_time().strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════
# زمان نسبی
# ═══════════════════════════════════════════════════════════
def time_ago(dt_input) -> str:
    """تبدیل timestamp به متن «چند دقیقه پیش»"""
    if dt_input is None:
        return "—"

    try:
        if isinstance(dt_input, str):
            dt = datetime.fromisoformat(dt_input)
        elif isinstance(dt_input, datetime):
            dt = dt_input
        elif isinstance(dt_input, (int, float)):
            dt = datetime.fromtimestamp(dt_input)
        else:
            return "—"
    except Exception:
        return "—"

    try:
        now = datetime.now()
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        delta = now - dt
        secs = delta.total_seconds()

        if secs < 0:
            return "الان"
        elif secs < 5:
            return "همین الان"
        elif secs < 60:
            return f"{int(secs)} ثانیه پیش"
        elif secs < 3600:
            return f"{int(secs / 60)} دقیقه پیش"
        elif secs < 86400:
            return f"{int(secs / 3600)} ساعت پیش"
        else:
            return f"{int(secs / 86400)} روز پیش"
    except Exception:
        return "—"


def format_time_short(dt_input) -> str:
    """فرمت HH:MM:SS از timestamp"""
    if dt_input is None:
        return "—"
    try:
        if isinstance(dt_input, str):
            dt = datetime.fromisoformat(dt_input)
        elif isinstance(dt_input, datetime):
            dt = dt_input
        else:
            return "—"
        return dt.strftime("%H:%M:%S")
    except Exception:
        return "—"


def format_datetime_short(dt_input) -> str:
    """فرمت MM-DD HH:MM از timestamp"""
    if dt_input is None:
        return "—"
    try:
        if isinstance(dt_input, str):
            dt = datetime.fromisoformat(dt_input)
        elif isinstance(dt_input, datetime):
            dt = dt_input
        else:
            return "—"
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return "—"


# ═══════════════════════════════════════════════════════════
# وضعیت بازار
# ═══════════════════════════════════════════════════════════
def market_status() -> tuple[str, str]:
    """
    وضعیت فعلی بازار (لندن / نیویورک / آسیا / تعطیل).

    Returns:
        (نام بازار, رنگ)
    """
    now = get_iran_time()
    wd = now.weekday()  # 0=دوشنبه ... 6=یک‌شنبه
    h = now.hour

    # جمعه و شنبه: بازار جهانی تعطیل
    # weekday: دوشنبه=0, سه=1, چهار=2, پنج=3, جمعه=4, شنبه=5, یک=6
    if wd in (4, 5):  # جمعه و شنبه
        return "تعطیل", "gray"

    if 11 <= h < 17:
        return "لندن", "green"
    elif 17 <= h < 21:
        return "لندن + نیویورک", "green"
    elif 21 <= h or h < 2:
        return "نیویورک", "yellow"
    else:
        return "آسیا", "gray"


def is_iran_market_open() -> bool:
    """
    آیا بورس تهران باز است؟

    بورس تهران: شنبه تا چهارشنبه، ۹:۰۰ تا ۱۲:۳۰ (با احتساب پیش‌گشایش)
    """
    now = get_iran_time()
    wd = now.weekday()

    # شنبه=5, یک=6, دوشنبه=0, سه=1, چهار=2
    iran_days = (5, 6, 0, 1, 2)
    if wd not in iran_days:
        return False

    h, m = now.hour, now.minute
    tm = h * 60 + m

    return 9 * 60 <= tm < 12 * 60 + 30


def is_global_market_open() -> bool:
    """آیا بازار جهانی (فارکس/کالا) باز است؟"""
    now = get_iran_time()
    wd = now.weekday()
    # جمعه شب تا یک‌شنبه صبح تعطیل
    if wd == 4 and now.hour >= 23:
        return False
    if wd in (5,):
        return False
    if wd == 6 and now.hour < 2:
        return False
    return True


def is_crypto_market_open() -> bool:
    """بازار کریپتو ۲۴/۷ باز است"""
    return True


# ═══════════════════════════════════════════════════════════
# توابع کمکی pandas
# ═══════════════════════════════════════════════════════════
def normalize_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    """یکسان‌سازی نام ستون‌ها (حذف MultiIndex + lowercase)"""
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    return df


def extract_close_series(df: pd.DataFrame):
    """استخراج سری Close به صورت Series"""
    if df is None or df.empty:
        return None
    try:
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.squeeze()
        return close.dropna()
    except (KeyError, AttributeError):
        return None


def ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    """اطمینان از اینکه index از نوع datetime است"""
    if df is None or df.empty:
        return df
    try:
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df
    except Exception:
        return df


def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    پاک‌سازی OHLCV:
      - حذف ستون‌های غیرضروری
      - dropna
      - فیلتر کندل‌های معتبر (قیمت > 0)
    """
    if df is None or df.empty:
        return df

    df = normalize_df_columns(df)
    df = ensure_datetime_index(df)

    needed = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in needed):
        return None

    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].copy()

    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df[(df["close"] > 0) & (df["high"] > 0) & (df["low"] > 0)]

    return df


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("تست core/utils.py — نسخه ۲.۰")
    print("=" * 60)
    print()

    print("۱) اعداد فارسی:")
    print(f"   ۱۲۳۴۵ → {to_english_digits('۱۲۳۴۵')}")
    print(f"   1234 → {to_persian_digits('1234')}")
    print()

    print("۲) پارس اعداد:")
    for t in ["۲۴,۱۰۰,۰۰۰", "$4,267.45", "۳.۵", "abc", None, 1234.5]:
        print(f"   parse_number({t!r}) = {parse_number(t)}")
    print()

    print("۳) فرمت قیمت:")
    for p in [4267.45, 24_100_000, 104_300_000, 4_500_000_000]:
        print(
            f"   {p:>15,.2f} → تومان: {format_price(p, 'تومان'):>12} | "
            f"دلار: {format_price(p, 'دلار')} | ریال: {format_price(p, 'ریال')}"
        )
    print()

    print("۴) تاریخ و ساعت:")
    print(f"   شمسی: {get_jalali_date()}")
    print(f"   کامل: {get_jalali_datetime()}")
    print(f"   روز:  {get_weekday_fa()}")
    print(f"   ساعت: {get_iran_clock()}")
    print(f"   میلادی: {get_miladi_date()}")
    print()

    print("۵) وضعیت بازارها:")
    print(f"   جهانی: {market_status()}")
    print(f"   بورس تهران باز؟ {is_iran_market_open()}")
    print(f"   بازار جهانی باز؟ {is_global_market_open()}")
    print(f"   کریپتو باز؟ {is_crypto_market_open()}")
    print()

    print("۶) زمان نسبی:")
    now = datetime.now()
    for delta in [
        timedelta(seconds=10),
        timedelta(minutes=3),
        timedelta(hours=2),
    ]:
        print(f"   {delta} پیش: {time_ago(now - delta)}")
    print()

    print("۷) فرمت‌های تاریخی:")
    print(f"   time_short:      {format_time_short(now)}")
    print(f"   datetime_short:  {format_datetime_short(now)}")
    print()

    print("[OK] تست کامل شد.")
