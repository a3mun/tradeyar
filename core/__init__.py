"""
core/__init__.py
بسته‌ی core پروژه Trademun
============================================================
همه‌ی توابع و کلاس‌های کلیدی اینجان و از هرجای پروژه
قابل import هستن:

    from core import analyze_symbol, DataSource, AppDefaults
"""

# ═══════════════════════════════════════════════════════════
# Contracts (Enum، Type، Constant)
# ═══════════════════════════════════════════════════════════
from .contracts import (
    DataSource,
    MarketType,
    RiskProfile,
    Signal,
    Direction,
    Regime,
    Consensus,
    SignalResult,
    AnalysisGroup,
    TIMEFRAMES,
    TF_NAMES,
    TF_SHORT,
    SIGNAL_TIMEOUT,
    POPULAR_SYMBOLS,
    CacheTTL,
    AppDefaults,
    SYMBOLS,
    SLTPDict,
    GroupResult,
    TickerItem,
    MarketInfo,
    LogEntry,
)

# ═══════════════════════════════════════════════════════════
# Utils
# ═══════════════════════════════════════════════════════════
from .utils import (
    IRAN_TZ,
    to_english_digits,
    to_persian_digits,
    parse_number,
    safe_num,
    format_price,
    format_change,
    get_iran_time,
    get_jalali_date,
    get_jalali_datetime,
    get_weekday_fa,
    get_iran_clock,
    time_ago,
    format_time_short,
    market_status,
    normalize_df_columns,
    extract_close_series,
)

# ═══════════════════════════════════════════════════════════
# نسخه
# ═══════════════════════════════════════════════════════════
__version__ = "40.0"
__brand__ = "Trademun"
