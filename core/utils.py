"""
core/utils.py
توابع کمکی — تاریخ، فرمت، اعداد، بازار، تایمر
"""

from datetime import datetime, timezone, timedelta

import pandas as pd


# ═══════════════════════════════════════════════════════════
# منطقه زمانی ایران
# ═══════════════════════════════════════════════════════════
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))


# ═══════════════════════════════════════════════════════════
# اعداد فارسی/عربی → انگلیسی
# ═══════════════════════════════════════════════════════════
FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
EN_DIGITS = "0123456789"


def to_english_digits(text: str) -> str:
    if not text:
        return text
    for fa, en in zip(FA_DIGITS, EN_DIGITS):
        text = text.replace(fa, en)
    for ar, en in zip(AR_DIGITS, EN_DIGITS):
        text = text.replace(ar, en)
    return text


def to_persian_digits(text: str) -> str:
    if not text:
        return text
    for en, fa in zip(EN_DIGITS, FA_DIGITS):
        text = text.replace(en, fa)
    return text


# ═══════════════════════════════════════════════════════════
# پارس امن اعداد
# ═══════════════════════════════════════════════════════════
def parse_number(text) -> float | None:
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
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def format_price(price, unit: str = "تومان") -> str:
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

    if price >= 1_000_000_000:
        return f"{price / 1_000_000_000:,.2f}B"
    elif price >= 1_000_000:
        return f"{price / 1_000_000:,.1f}M"
    elif price >= 1_000:
        return f"{price:,.0f}"
    else:
        return f"{price:,.2f}"


def format_change(value: float, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except (TypeError, ValueError):
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


# ═══════════════════════════════════════════════════════════
# تاریخ و زمان
# ═══════════════════════════════════════════════════════════
def get_iran_time() -> datetime:
    return datetime.now(IRAN_TZ)


def get_jalali_date() -> str:
    try:
        import jdatetime
        return jdatetime.datetime.now().strftime("%Y/%m/%d")
    except ImportError:
        return datetime.now().strftime("%Y-%m-%d")


def get_jalali_datetime() -> str:
    try:
        import jdatetime
        return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    except ImportError:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_weekday_fa() -> str:
    try:
        import jdatetime
        wd = jdatetime.datetime.now().weekday()
        days = ["شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه",
                "چهارشنبه", "پنج‌شنبه", "جمعه"]
        return days[wd]
    except ImportError:
        days = {
            0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه",
            3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یک‌شنبه",
        }
        return days[datetime.now().weekday()]


def get_iran_clock() -> str:
    return get_iran_time().strftime("%H:%M:%S")


# ═══════════════════════════════════════════════════════════
# زمان نسبی (چند دقیقه پیش)
# ═══════════════════════════════════════════════════════════
def time_ago(dt_input) -> str:
    """
    تبدیل یه timestamp به متن «چند دقیقه پیش».
    """
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


# ═══════════════════════════════════════════════════════════
# وضعیت بازار
# ═══════════════════════════════════════════════════════════
def market_status() -> tuple[str, str]:
    now = get_iran_time()
    wd = now.weekday()
    h = now.hour

    if wd in (4, 5):
        return "تعطیل", "gray"

    if 11 <= h < 17:
        return "لندن", "green"
    elif 17 <= h < 21:
        return "لندن + نیویورک", "green"
    elif 21 <= h or h < 2:
        return "نیویورک", "yellow"
    else:
        return "آسیا", "gray"


# ═══════════════════════════════════════════════════════════
# توابع کمکی pandas
# ═══════════════════════════════════════════════════════════
def normalize_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    return df


def extract_close_series(df: pd.DataFrame):
    if df is None or df.empty:
        return None
    try:
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.squeeze()
        return close.dropna()
    except (KeyError, AttributeError):
        return None


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 50)
    print("تست core/utils.py")
    print("=" * 50)
    print()

    print("1) اعداد فارسی به انگلیسی:")
    print(f"   {to_english_digits('۱۲۳۴۵۶۷۸۹۰')}")
    print()

    print("2) پارس اعداد:")
    for t in ["۲۴,۱۰۰,۰۰۰", "$4,267.45", "۳.۵", "abc", None, 1234.5]:
        print(f"   parse_number({t!r}) = {parse_number(t)}")
    print()

    print("3) فرمت قیمت:")
    for p in [4267.45, 24_100_000, 104_300_000, 4_500_000_000]:
        print(f"   {p:>15,.2f}  ->  تومان: {format_price(p, 'تومان'):>12}  |  دلار: {format_price(p, 'دلار')}")
    print()

    print("4) تاریخ و ساعت:")
    print(f"   شمسی: {get_jalali_date()}")
    print(f"   کامل: {get_jalali_datetime()}")
    print(f"   روز:  {get_weekday_fa()}")
    print(f"   ساعت: {get_iran_clock()}")
    print()

    print("5) زمان نسبی:")
    from datetime import datetime, timedelta
    now = datetime.now()
    for delta in [timedelta(seconds=10), timedelta(minutes=3), timedelta(hours=2)]:
        print(f"   {delta} پیش: {time_ago(now - delta)}")
    print()

    print("[OK] همه تست‌ها اجرا شد.")