"""
core/__init__.py
بسته‌ی core پروژه Trademun
============================================================
"""

# ═══ Contracts ═══
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
    TF_ATR_MULT,
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
    get_tf_atr_mult,
    get_adaptive_thresholds,
)

# ═══ Utils ═══
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
    get_miladi_date,
    time_ago,
    format_time_short,
    market_status,
    normalize_df_columns,
    extract_close_series,
)

# ═══ Analyzer ═══
from .analyzer import (
    analyze_symbol,
    compute_indicators,
    compute_fear_greed,
    build_checklist_weighted,
    build_analysis_paragraph,
    build_scenarios,
    classify_regime,
    RISK_PROFILES,
)

# ═══ Sources ═══
from .sources import (
    get_source_info,
    detect_source_for_ticker,
    is_symbol_available_in_source,
    resolve_source,
    resolve_symbol_and_source,
    get_default_symbol_for_source,
)

# ═══ نسخه ═══
__version__ = "45.0"
__brand__ = "Trademun"
