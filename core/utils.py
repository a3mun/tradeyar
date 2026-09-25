"""
core/utils.py
توابع کمکی — تاریخ، فرمت، اعداد، بازار
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
    """تبدیل ارقام فارسی و عربی به انگلیسی"""
    if not text:
        return text
    for fa, en in zip(FA_DIGITS, EN_DIGITS):
        text = text.replace(fa, en)
    for ar, en in zip(AR_DIGITS, EN_DIGITS):
        text = text.replace(ar, en)
    return text


def to_persian_digits(text: str) -> str:
    """تبدیل ارقام انگلیسی به فارسی"""
    if not text:
        return text
    for en, fa in zip(EN_DIGITS, FA_DIGITS):
        text = text.replace(en, fa)
    return text


# ═══════════════════════════════════════════════════════════
# پارس امن اعداد
# ═══════════════════════════════════════════════════════════
def parse_number(text) -> float | None:
    """
    استخراج عدد از متن (با کاما، ارقام فارسی و ...)
    
    مثال:
        parse_number("۲۴,۱۰۰,۰۰۰") → 24100000.0
        parse_number("$4,267.45") → 4267.45
        parse_number("...") → None
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

    # مرحله ۱: اولین رقم رو پیدا کن
    start_idx = -1
    for i, ch in enumerate(text):
        if ch.isdigit():
            start_idx = i
            break

    if start_idx == -1:
        return None

    # مرحله ۲: از اولین رقم تا جایی که عدد ادامه داره برو
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
    """تبدیل امن به float — اگه NaN/None بود، مقدار پیش‌فرض رو بده"""
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
    فرمت قیمت بر اساس واحد
    
    - دلار: با ۲ رقم اعشار و $ در ابتدا
    - تومان: با B/M/K در صورت بزرگ بودن
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

    if price >= 1_000_000_000:
        return f"{price / 1_000_000_000:,.2f}B"
    elif price >= 1_000_000:
        return f"{price / 1_000_000:,.1f}M"
    elif price >= 1_000:
        return f"{price:,.0f}"
    else:
        return f"{price:,.2f}"


def format_change(value: float, decimals: int = 2) -> str:
    """فرمت درصد تغییر با علامت + یا -"""
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
    """ساعت فعلی ایران"""
    return datetime.now(IRAN_TZ)


def get_jalali_date() -> str:
    """تاریخ شمسی به صورت YYYY/MM/DD"""
    try:
        import jdatetime
        return jdatetime.datetime.now().strftime("%Y/%m/%d")
    except ImportError:
        return datetime.now().strftime("%Y-%m-%d")


def get_jalali_datetime() -> str:
    """تاریخ و ساعت شمسی کامل"""
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
    """ساعت ایران به صورت HH:MM:SS"""
    return get_iran_time().strftime("%H:%M:%S")


# ═══════════════════════════════════════════════════════════
# وضعیت بازار
# ═══════════════════════════════════════════════════════════
def market_status() -> tuple[str, str]:
    """
    وضعیت بازار جهانی بر اساس ساعت ایران
    
    Returns:
        (نام بازار, کلید رنگ)
    """
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
# توابع کمکی برای pandas DataFrame
# ═══════════════════════════════════════════════════════════
def normalize_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    نرمال‌سازی ستون‌های DataFrame yfinance:
    - MultiIndex → تک سطح
    - حروف کوچک
    """
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    return df


def extract_close_series(df: pd.DataFrame):
    """استخراج سری close از دیتافریم yfinance به صورت امن"""
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
# تست سریع (اجرا کن: python -m core.utils)
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

    print("5) وضعیت بازار:")
    status, color = market_status()
    print(f"   {status}  (رنگ: {color})")
    print()

    print("[OK] همه تست‌ها اجرا شد.")