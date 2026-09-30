"""
app.py
Trademun (تریدمون) — نسخه ۴۵.۰
============================================================
تغییرات نسخه ۴۵.۰:
  - سازگاری با analyzer 8.5 (ticker param)
  - render_tf_table با ticker
  - render_order_book با ticker
  - build_ai_export بازنویسی‌شده (داده خام، اعداد ۲ رقم)
  - پیش‌فرض نوبیتکس + BTC-USD
  - دکمه کپی AI با JS
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core.contracts import (
    AppDefaults,
    CacheTTL,
    POPULAR_SYMBOLS,
    SYMBOLS,
    TIMEFRAMES,
    TF_NAMES,
    MarketType,
)
from core.sources import (
    get_default_symbol_for_source,
    get_source_info,
    detect_source_for_ticker,
    is_symbol_available_in_source,
)
from core.data_fetcher import (
    fetch_iran_prices,
    fetch_history_by_source,
    fetch_gold_silver_ratio,
    search_symbol,
)
from core.analyzer import (
    analyze_symbol,
    compute_fear_greed,
    build_checklist_weighted,
    build_analysis_paragraph,
)
from core.scanner import scan_markets
from core.market_lists import get_categories_with_tickers, fetch_tsetmc_all_symbols
from core.backtester import (
    compute_stats,
    load_signal_log,
    record_signal,
    backtest_all,
)
from core.utils import get_jalali_date, get_weekday_fa, get_miladi_date

from ui.styles import get_custom_css, get_theme, render_back_to_top_fab
from ui.components import (
    render_header,
    render_top_ticker,
    render_unified_signal_card,
    render_tf_table,
    render_deep_analysis,
    render_fear_greed,
    render_backtest_stats,
    render_checklist,
    render_scanner,
    render_live_timer,
    render_profile_selector,
    render_source_selector,
    render_settings_section_title,
    render_settings_divider,
    render_order_book,
    render_recent_signals_list,
    render_market_type_selector,
    render_section_header,
    render_settings_panel,
    render_settings_panel_open_button,
    render_help_panel,
    render_help_panel_open_button,
)

# ═══════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Trademun — تریدمون",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ═══════════════════════════════════════════════════════════
# Custom symbols persistence
# ═══════════════════════════════════════════════════════════
CUSTOM_SYMBOLS_FILE = Path("data/custom_symbols.json")

PREFERENCES_FILE = Path("data/user_prefs.json")


def load_preferences() -> dict:
    """بارگذاری تنظیمات کاربر"""
    if not PREFERENCES_FILE.exists():
        return {}
    try:
        with open(PREFERENCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_preferences(prefs: dict) -> None:
    """ذخیره تنظیمات کاربر"""
    try:
        PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[App] خطا در ذخیره preferences: {e}")


def load_custom_symbols() -> list:
    if not CUSTOM_SYMBOLS_FILE.exists():
        return []
    try:
        with open(CUSTOM_SYMBOLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_custom_symbols(symbols: list) -> None:
    try:
        CUSTOM_SYMBOLS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CUSTOM_SYMBOLS_FILE, "w", encoding="utf-8") as f:
            json.dump(symbols, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[App] خطا در ذخیره custom_symbols: {e}")


# ═══════════════════════════════════════════════════════════
# session_state
# ═══════════════════════════════════════════════════════════
# ═══ بارگذاری تنظیمات ذخیره‌شده ═══
_saved_prefs = load_preferences()

# ═══ تنظیمات پیش‌فرض (اولویت: saved > AppDefaults) ═══
defaults = {
    "theme": _saved_prefs.get("theme", AppDefaults.THEME),
    "selected_symbol": _saved_prefs.get("selected_symbol", AppDefaults.SYMBOL),
    "selected_tf": _saved_prefs.get("selected_tf", AppDefaults.TIMEFRAME),
    "risk_profile": _saved_prefs.get("risk_profile", AppDefaults.RISK_PROFILE),
    "market_type": _saved_prefs.get("market_type", AppDefaults.MARKET_TYPE),
    "data_source": _saved_prefs.get("data_source", AppDefaults.DATA_SOURCE),
    "custom_symbols": load_custom_symbols(),
    "last_update": datetime.now().strftime("%H:%M"),
    "last_data_refresh": datetime.now().strftime("%H:%M:%S"),
    "scanner_last_update": "",
    "refresh_seconds": _saved_prefs.get("refresh_seconds", AppDefaults.REFRESH_SECONDS),
    "bt_time_filter": "all",
    "bt_confirm_reset": False,
    "scanner_filter": "all",
    "scanner_category": "crypto",
    "scanner_tf": "۵ دقیقه",
    "scanner_key": "",
    "settings_open": False,
    "bt_last_check": 0,
    "bt_last_auto_update": "",
    "bt_last_auto_result": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ═══ ذخیره خودکار تنظیمات حیاتی ═══
def _persist_prefs():
    """ذخیره تنظیمات کاربر در فایل"""
    save_preferences(
        {
            "theme": st.session_state.get("theme", "dark"),
            "selected_symbol": st.session_state.get("selected_symbol", ""),
            "selected_tf": st.session_state.get("selected_tf", ""),
            "risk_profile": st.session_state.get("risk_profile", "aggressive"),
            "market_type": st.session_state.get("market_type", "futures"),
            "data_source": st.session_state.get("data_source", "nobitex"),
            "refresh_seconds": st.session_state.get("refresh_seconds", 60),
        }
    )


# ═══════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════
st.markdown(get_custom_css(st.session_state.theme), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# Auto-refresh
# ═══════════════════════════════════════════════════════════
if st.session_state.refresh_seconds > 0:
    try:
        from streamlit_autorefresh import st_autorefresh

        st_autorefresh(
            interval=st.session_state.refresh_seconds * 1000, key="auto_refresh"
        )
    except ImportError:
        pass


# ═══════════════════════════════════════════════════════════
# Cache
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=CacheTTL.ANALYSIS, show_spinner=False)
def cached_history(ticker: str, interval: str, period: str, source: str):
    return fetch_history_by_source(ticker, interval, period, source)


@st.cache_data(ttl=60, show_spinner=False)
def cached_prices():
    return fetch_iran_prices()


@st.cache_data(ttl=CacheTTL.ANALYSIS, show_spinner=False)
def cached_gsr():
    return fetch_gold_silver_ratio()


@st.cache_data(ttl=CacheTTL.SCAN, show_spinner=False)
def cached_scan(category: str, tf_index: int, market_type: str):
    return scan_markets(
        category=category,
        tf_index=tf_index,
        top_n=5,
        risk_profile="aggressive",
        market_type=market_type,
    )


@st.cache_data(ttl=CacheTTL.LIVE_PRICE, show_spinner=False)
def cached_live_price(ticker: str, source: str):
    try:
        from core.nobitex_fetcher import fetch_nobitex_stats_for_ticker

        if source in ("nobitex", "abantether"):
            stats = fetch_nobitex_stats_for_ticker(ticker)
            if stats:
                return stats.get("price")
    except Exception:
        pass
    return None


@st.cache_data(ttl=CacheTTL.TICKER, show_spinner=False)
def cached_ticker_data(source: str):
    result = []

    ip = fetch_iran_prices()
    if ip.get("prices"):
        p = ip["prices"]
        result.extend(
            [
                {
                    "name": "طلای ۱۸",
                    "emoji": "🥇",
                    "price": p.get("geram18"),
                    "change_pct": None,
                    "unit": "تومان",
                },
                {
                    "name": "سکه امامی",
                    "emoji": "🪙",
                    "price": p.get("sekee"),
                    "change_pct": None,
                    "unit": "تومان",
                },
                {
                    "name": "دلار",
                    "emoji": "💵",
                    "price": p.get("dollar"),
                    "change_pct": None,
                    "unit": "تومان",
                },
                {
                    "name": "انس جهانی",
                    "emoji": "🌍",
                    "price": p.get("ons"),
                    "change_pct": None,
                    "unit": "دلار",
                },
            ]
        )

    try:
        from core.nobitex_fetcher import fetch_nobitex_stats

        usdt_stats = fetch_nobitex_stats("usdt", "rls")
        if usdt_stats and usdt_stats.get("price"):
            result.insert(
                0,
                {
                    "name": "تتر/تومان",
                    "emoji": "💵",
                    "price": usdt_stats["price"],
                    "change_pct": usdt_stats.get("change_24h"),
                    "unit": "تومان",
                },
            )
    except Exception:
        pass

    if source == "nobitex":
        try:
            from core.nobitex_fetcher import (
                fetch_all_nobitex_symbols,
                filter_liquid_symbols,
            )

            all_syms = fetch_all_nobitex_symbols("usdt")
            top = filter_liquid_symbols(all_syms, min_volume=100000, max_count=8)
            emoji_map = {
                "BTC": "₿",
                "ETH": "Ξ",
                "SOL": "◎",
                "XRP": "✕",
                "DOGE": "🐕",
                "BNB": "🟡",
                "ADA": "🔵",
                "TON": "💎",
                "NEAR": "Ⓝ",
                "SUI": "💧",
                "AVAX": "🔺",
                "LINK": "🔗",
            }
            for s in top:
                base = s["base"]
                result.append(
                    {
                        "name": f"{base}/USDT",
                        "emoji": emoji_map.get(base, "💰"),
                        "price": s["price"],
                        "change_pct": s.get("change_24h"),
                        "unit": "دلار",
                    }
                )
        except Exception:
            pass

    emoji_map_global = {"GC=F": "🥇", "SI=F": "🥈", "BTC-USD": "₿", "BZ=F": "🛢"}
    for tkr in ["GC=F", "SI=F", "BZ=F"]:
        try:
            d = fetch_history_by_source(tkr, "1h", "5d", "global")
            if d is not None and len(d) > 0:
                lp = float(d["close"].iloc[-1])
                pp = float(d["close"].iloc[-2]) if len(d) > 1 else lp
                ch = ((lp - pp) / pp * 100) if pp > 0 else 0
                result.append(
                    {
                        "name": SYMBOLS.get(tkr, tkr),
                        "emoji": emoji_map_global.get(tkr, "💰"),
                        "price": lp,
                        "change_pct": ch,
                        "unit": "دلار",
                    }
                )
        except Exception:
            continue

    return result


def get_markets_info() -> list:
    """..."""
    now_iran = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
    h, m, wd = now_iran.hour, now_iran.minute, now_iran.weekday()
    tm = h * 60 + m

    # ═══ تعطیلات ═══
    is_weekend_global = wd in [5, 6]  # شنبه/یکشنبه — بازار جهانی تعطیل

    def fmt(minutes_total: int) -> str:
        """تبدیل دقیقه به HH:MM"""
        hh = (minutes_total // 60) % 24
        mm = minutes_total % 60
        return f"{hh:02d}:{mm:02d}"

    def calc_market(open_min: int, close_min: int, is_weekend: bool) -> dict:
        """محاسبه وضعیت بازار و زمان بعدی"""
        is_open = (not is_weekend) and (open_min <= tm < close_min)
        if is_weekend:
            return {
                "is_open": False,
                "status_text": "تعطیل",
                "next_event_type": "",
                "next_event_time": "",
            }

        if is_open:
            # زمان بسته شدن
            remaining = close_min - tm
            hh = remaining // 60
            mm = remaining % 60
            if hh > 0:
                status_text = f"باز (تا {hh}h {mm}m)"
            else:
                status_text = f"باز (تا {mm}m)"
            return {
                "is_open": True,
                "status_text": "باز",
                "next_event_type": "بسته",
                "next_event_time": fmt(close_min),
            }
        else:
            # زمان باز شدن (اگه الان قبل از بازه) یا فردا
            if tm < open_min:
                next_open = open_min
            else:
                next_open = open_min  # فردا

            # متن باز شدن
            if tm < open_min:
                remaining = open_min - tm
                hh = remaining // 60
                mm = remaining % 60
                if hh > 0:
                    status_text = f"بسته ({hh}h {mm}m تا باز شدن)"
                else:
                    status_text = f"بسته ({mm}m تا باز شدن)"
            else:
                status_text = "بسته"

            return {
                "is_open": False,
                "status_text": "بسته",
                "next_event_type": "باز",
                "next_event_time": fmt(next_open),
            }

    markets = []

    # ─── توکیو: ۰۳:۳۰ - ۱۲:۰۰ ───
    tokyo = calc_market(
        open_min=3 * 60 + 30,
        close_min=12 * 60,
        is_weekend=is_weekend_global,
    )
    markets.append(
        {
            "name": "توکیو",
            "icon": "🇯🇵",
            **tokyo,
        }
    )

    # ─── لندن: ۱۱:۳۰ - ۲۰:۰۰ ───
    london = calc_market(
        open_min=11 * 60 + 30,
        close_min=20 * 60,
        is_weekend=is_weekend_global,
    )
    markets.append(
        {
            "name": "لندن",
            "icon": "🇪🇺",
            **london,
        }
    )

    # ─── نیویورک: ۱۶:۳۰ - ۲۳:۰۰ ───
    ny = calc_market(
        open_min=16 * 60 + 30,
        close_min=23 * 60,
        is_weekend=is_weekend_global,
    )
    markets.append(
        {
            "name": "نیویورک",
            "icon": "🇺🇸",
            **ny,
        }
    )

    # ─── بورس تهران: شنبه-چهارشنبه ۰۹:۰۰ - ۱۲:۳۰ ───
    # wd: دوشنبه=0، سه=1، چهار=2، پنج=3، جمعه=4، شنبه=5، یک=6
    iran_days = [5, 6, 0, 1, 2]  # شنبه تا چهارشنبه
    iran_open = (wd in iran_days) and (9 * 60 <= tm < 12 * 60 + 30)

    if wd not in iran_days:
        iran_status = {
            "is_open": False,
            "status_text": "تعطیل",
            "next_event_type": "",
            "next_event_time": "",
        }
    elif iran_open:
        iran_status = {
            "is_open": True,
            "status_text": "باز",
            "next_event_type": "بسته",
            "next_event_time": "12:30",
        }
    else:
        if tm < 9 * 60:
            remaining = 9 * 60 - tm
            hh = remaining // 60
            mm = remaining % 60
            if hh > 0:
                status_text = f"بسته ({hh}h {mm}m تا باز شدن)"
            else:
                status_text = f"بسته ({mm}m تا باز شدن)"
            iran_status = {
                "is_open": False,
                "status_text": "بسته",
                "next_event_type": "باز",
                "next_event_time": "09:00",
            }
        else:
            iran_status = {
                "is_open": False,
                "status_text": "بسته",
                "next_event_type": "",
                "next_event_time": "",
            }

    markets.append(
        {
            "name": "بورس تهران",
            "icon": "🇮🇷",
            **iran_status,
        }
    )

    return markets


def _is_iranian_ticker(ticker: str) -> bool:
    """تشخیص نمادهای تومانی/ریالی"""
    if not ticker:
        return False
    upper = ticker.upper()
    return "IRT" in upper or "RLS" in upper or upper == "USDT-IRT"


def _normalize_fa(text: str) -> str:
    """نرمال‌سازی متن فارسی — حذف فاصله/نیم‌فاصله/ی/ک عربی"""
    if not text:
        return ""
    return (
        text.strip()
        .replace("‌", "")  # نیم‌فاصله
        .replace(" ", "")  # فاصله
        .replace("ي", "ی")  # ی عربی
        .replace("ك", "ک")  # ک عربی
        .lower()
    )


def build_ai_export(
    ticker: str, name: str, tf_name: str, analysis: dict, tfs_data: dict
) -> str:
    """
    خروجی برای AI — داده خام کامل
    شامل: اندیکاتورها، سطوح، TFها، گروه‌ها، تله‌ها، سناریوها
    """
    if not analysis:
        return ""

    lines = []

    # ═══════════════════════════════════════════════════════════
    # هدر
    # ═══════════════════════════════════════════════════════════
    lines.append(f"# داده خام {name} ({ticker})")
    lines.append(f"## تایم‌فریم: {tf_name}")
    lines.append("")
    lines.append(f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # خلاصه
    # ═══════════════════════════════════════════════════════════
    regime_raw = analysis.get("regime", "range")
    regime_fa = {
        "trend": "بازار جهت‌دار",
        "transitional": "بازار در حال‌تغییر",
        "range": "بازار بی‌جهت",
    }.get(regime_raw, regime_raw)

    lines.append("## خلاصه")
    lines.append(f"- سیگنال: {analysis.get('signal', '—')}")
    lines.append(f"- اطمینان: {analysis.get('confidence', 0):.0f}%")
    lines.append(f"- بازار: {regime_fa} (ADX={analysis.get('adx', 0):.2f})")
    lines.append(f"- قیمت: {analysis.get('price', 0):.2f}")
    lines.append(f"- جهت پیشنهادی: {analysis.get('direction', 'neutral')}")
    lines.append(f"- اجماع: {analysis.get('consensus', 'neutral')}")
    lines.append(
        f"- آرا: {analysis.get('votes_long', 0)} صعودی / "
        f"{analysis.get('votes_neutral', 0)} خنثی / "
        f"{analysis.get('votes_short', 0)} نزولی"
    )

    # ═══ تأیید چند TF ═══
    multi_tf = analysis.get("multi_tf_info", "")
    if multi_tf and multi_tf != "بدون بررسی":
        lines.append(f"- تأیید TF: {multi_tf}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # اندیکاتورها
    # ═══════════════════════════════════════════════════════════
    lines.append("## اندیکاتورها (TF فعلی)")
    indicators = [
        ("RSI", analysis.get("rsi")),
        ("Stoch K", analysis.get("stoch_k")),
        ("Stoch D", analysis.get("stoch_d")),
        ("Williams %R", analysis.get("willr")),
        ("MACD Hist", analysis.get("macd_hist")),
        ("EMA200", analysis.get("ema200")),
        ("BB Upper", analysis.get("bb_upper")),
        ("BB Lower", analysis.get("bb_lower")),
        ("ATR", analysis.get("atr")),
        ("ADX", analysis.get("adx")),
    ]
    for label, val in indicators:
        if val is None:
            continue
        try:
            lines.append(f"- {label}: {float(val):.2f}")
        except (TypeError, ValueError):
            lines.append(f"- {label}: {val}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # سطوح کلیدی
    # ═══════════════════════════════════════════════════════════
    lines.append("## سطوح کلیدی")
    r = analysis.get("resistance", 0) or 0
    s = analysis.get("support", 0) or 0
    if r > 0:
        lines.append(f"- مقاومت نزدیک: {r:.2f}")
    if s > 0:
        lines.append(f"- حمایت نزدیک: {s:.2f}")

    pivots = analysis.get("pivots", {}) or {}
    if pivots:
        values = [
            pivots.get(k, 0) for k in ["r3", "r2", "r1", "pivot", "s1", "s2", "s3"]
        ]
        values = [v for v in values if v]
        is_flat = len(values) >= 2 and (max(values) - min(values)) < 1e-6

        if is_flat:
            lines.append("- Pivot Points: (نامعتبر — کندل تخت)")
        else:
            lines.append("- Pivot Points:")
            for k, label in [
                ("r3", "R3"),
                ("r2", "R2"),
                ("r1", "R1"),
                ("pivot", "Pivot"),
                ("s1", "S1"),
                ("s2", "S2"),
                ("s3", "S3"),
            ]:
                v = pivots.get(k)
                if v:
                    lines.append(f"  - {label}: {float(v):.2f}")

    fib = analysis.get("fibonacci", {}) or {}
    if fib and fib.get("levels"):
        lines.append("- Fibonacci:")
        for ratio, val in fib["levels"].items():
            lines.append(f"  - {ratio}: {float(val):.2f}")

    swings = analysis.get("swings", {}) or {}
    if swings:
        if swings.get("nearest_resistance"):
            lines.append(f"- Swing Resistance: {swings['nearest_resistance']:.2f}")
        if swings.get("nearest_support"):
            lines.append(f"- Swing Support: {swings['nearest_support']:.2f}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # SL/TP
    # ═══════════════════════════════════════════════════════════
    sl_tp = analysis.get("sl_tp")
    if sl_tp:
        lines.append("## حد ضرر و هدف")
        lines.append(f"- حد ضرر: {sl_tp.get('sl', 0):.2f}")
        lines.append(f"- هدف: {sl_tp.get('tp', 0):.2f}")
        lines.append(f"- نوع: {sl_tp.get('type', '—')}")
        rr = analysis.get("rr")
        if rr:
            lines.append(f"- R:R: {rr:.2f}")
        lines.append("")

    # ═══════════════════════════════════════════════════════════
    # TFها
    # ═══════════════════════════════════════════════════════════
    lines.append("## تحلیل همه TFها")
    for tf in TF_NAMES:
        if tf in tfs_data:
            a = tfs_data[tf]
            sig = a.get("signal", "—")
            conf = a.get("confidence", 0)
            reg = a.get("regime", "—")
            reg_fa = {
                "trend": "جهت‌دار",
                "transitional": "در حال‌تغییر",
                "range": "بی‌جهت",
            }.get(reg, reg)
            adx = a.get("adx", 0)
            lines.append(f"- {tf}: {sig} · {conf:.0f}% · {reg_fa} · ADX={adx:.2f}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # گروه‌های تحلیل
    # ═══════════════════════════════════════════════════════════
    lines.append("## دلایل گروه‌های تحلیل (TF فعلی)")
    groups = analysis.get("groups", {}) or {}
    for g_key, g_data in groups.items():
        g_names = {
            "momentum": "مومنتوم",
            "trend": "روند",
            "volatility": "نوسان",
            "volume": "حجم",
            "structure": "ساختار",
        }
        g_name = g_names.get(g_key, g_key)
        vote = g_data.get("vote", 0)
        score = g_data.get("score", 0.0)
        strength = g_data.get("strength_fa", "")
        lines.append(f"### {g_name}")
        lines.append(f"- رای: {vote} · امتیاز: {score:.2f} · قدرت: {strength}")
        for reason in g_data.get("reasons", []):
            lines.append(f"  - {reason}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # واگرایی
    # ═══════════════════════════════════════════════════════════
    divergence = analysis.get("divergence", {}) or {}
    if divergence.get("has_divergence"):
        lines.append("## واگرایی")
        lines.append(f"- {divergence.get('reason', '')}")
        lines.append("")

    # ═══════════════════════════════════════════════════════════
    # تله‌ها
    # ═══════════════════════════════════════════════════════════
    traps = analysis.get("traps", {}) or {}
    active_traps = [k for k, v in traps.items() if v.get("active")]
    if active_traps:
        lines.append("## هشدار تله‌ها")
        trap_names = {
            "bull_trap": "تله صعودی",
            "bear_trap": "تله نزولی",
            "fake_breakout": "شکست جعلی",
            "exhaustion": "خستگی روند",
        }
        for trap_key in active_traps:
            t_info = traps[trap_key]
            lines.append(
                f"- {trap_names.get(trap_key, trap_key)} "
                f"(شدت {t_info.get('severity', 0)}/10)"
            )
            lines.append(f"  {t_info.get('reason', '')}")
        lines.append("")

    # ═══════════════════════════════════════════════════════════
    # سناریوها
    # ═══════════════════════════════════════════════════════════
    scenarios = analysis.get("scenarios", []) or []
    if scenarios:
        lines.append("## سناریوها")
        for sc in scenarios:
            prob = int(sc.get("probability", 0.5) * 100)
            lines.append(f"- ({prob}%) {sc.get('condition', '')}")
            lines.append(f"  → {sc.get('action', '')}")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# هدر
# ═══════════════════════════════════════════════════════════
t = get_theme(st.session_state.theme)
render_header(get_jalali_date(), get_weekday_fa(), get_miladi_date())

# ═══ یک ردیف: تنظیمات + راهنما کنار هم ═══
_btn_cols = st.columns([5, 1, 1])
with _btn_cols[1]:
    render_settings_panel_open_button()
with _btn_cols[2]:
    render_help_panel_open_button()

render_settings_panel()
render_help_panel()

# ═══ تیکر ساعت‌های بازار ═══
markets_info = get_markets_info()
render_top_ticker([], markets_info)

# ═══════════════════════════════════════════════════════════
# جستجو
# ═══════════════════════════════════════════════════════════
st.markdown(
    f'<div style="font-size:14px; font-weight:700; color:{t["primary"]}; '
    f'margin-bottom:6px; padding-right:8px; border-right:3px solid {t["primary"]}; '
    f'direction:rtl; text-align:right;">🔍 جستجوی نماد</div>',
    unsafe_allow_html=True,
)

search_cols = st.columns([5, 1])
with search_cols[0]:
    search_query = st.text_input(
        "جستجو",
        placeholder="مثال: BTC، TSLA، فولاد، PAXG",
        label_visibility="collapsed",
        key="search_input",
    )
with search_cols[1]:
    st.button("🔍", use_container_width=True, key="search_btn")

if search_query and len(search_query.strip()) >= 2:
    q = search_query.strip()
    q_upper = q.upper()
    suggestions = []

    # ═══ جستجوی هوشمند فارسی + انگلیسی ═══
    q_norm = _normalize_fa(q)

    for tkr, name in SYMBOLS.items():
        tkr_upper = tkr.upper()
        name_norm = _normalize_fa(name)

        # انطباق انگلیسی
        if q_upper in tkr_upper:
            src = detect_source_for_ticker(tkr)
            suggestions.append({"ticker": tkr, "name": name, "source": src})
            continue

        # انطباق فارسی (نرمال‌شده)
        if q_norm and q_norm in name_norm:
            src = detect_source_for_ticker(tkr)
            suggestions.append({"ticker": tkr, "name": name, "source": src})
            continue

    for tkr in st.session_state.custom_symbols:
        if q_upper in tkr.upper():
            suggestions.append({"ticker": tkr, "name": tkr, "source": "custom"})

    # ═══ نوبیتکس: USDT + RLS ═══
    try:
        from core.nobitex_fetcher import (
            fetch_all_nobitex_symbols,
            map_nobitex_to_symbol,
        )

        existing_tickers = {s["ticker"] for s in suggestions}

        # USDT pairs
        all_usdt = fetch_all_nobitex_symbols("usdt")
        for s in all_usdt[:200]:
            if q_upper in s["symbol"] or q_upper in s["base"]:
                our_ticker = map_nobitex_to_symbol(s["symbol"])
                if our_ticker and our_ticker not in existing_tickers:
                    suggestions.append(
                        {
                            "ticker": our_ticker,
                            "name": f"{s['base']}/USDT",
                            "source": "nobitex",
                            "price": s["price"],
                            "change": s.get("change_24h", 0),
                        }
                    )
                    existing_tickers.add(our_ticker)

        # RLS pairs (تومانی)
        all_rls = fetch_all_nobitex_symbols("rls")
        for s in all_rls[:100]:
            if q_upper in s["symbol"] or q_upper in s["base"]:
                our_ticker = map_nobitex_to_symbol(s["symbol"])
                if our_ticker and our_ticker not in existing_tickers:
                    suggestions.append(
                        {
                            "ticker": our_ticker,
                            "name": f"{s['base']}/تومان",
                            "source": "nobitex",
                            "price": s["price"],
                            "change": s.get("change_24h", 0),
                        }
                    )
                    existing_tickers.add(our_ticker)
    except Exception:
        pass

    # ═══ جستجو در NOBITEX_SYMBOLS (دیکشنری کامل — برای نمادهای نوبیتکس که در API نیستن) ═══
    try:
        from core.nobitex_fetcher import NOBITEX_SYMBOLS

        existing_tickers = {s["ticker"] for s in suggestions}
        for ticker, nobitex_sym in NOBITEX_SYMBOLS.items():
            if ticker in existing_tickers:
                continue
            # انطباق در ticker یا nobitex_sym یا base
            tkr_upper = ticker.upper()
            nob_upper = nobitex_sym.upper()
            if q_upper in tkr_upper or q_upper in nob_upper:
                # تعیین نام نمایشی
                if ticker.endswith("-IRT"):
                    display = ticker.replace("-IRT", "/تومان")
                elif ticker.endswith("-USD"):
                    display = ticker.replace("-USD", "/USDT")
                else:
                    display = ticker

                suggestions.append(
                    {
                        "ticker": ticker,
                        "name": display,
                        "source": "nobitex",
                    }
                )
                existing_tickers.add(ticker)
    except Exception:
        pass

    # ═══ بورس تهران: static + cache ═══
    try:
        from core.market_lists import get_iran_stock_symbols, get_iran_stock_map

        existing_tickers = {s["ticker"] for s in suggestions}
        static_syms = get_iran_stock_symbols()
        static_map = get_iran_stock_map()

        for sym in static_syms:
            if sym in existing_tickers:
                continue
            if q in sym or q_upper in sym.upper():
                name_fa = static_map.get(sym, sym)
                suggestions.append(
                    {
                        "ticker": sym,
                        "name": f"{sym} — {name_fa}",
                        "source": "tsetmc",
                    }
                )
                existing_tickers.add(sym)
    except Exception:
        pass

    # ═══ اگه کمتر از ۵ نتیجه، از cache TSETMC بگیر ═══
    if len(suggestions) < 5:
        try:
            existing_tickers = {s["ticker"] for s in suggestions}
            tsetmc_syms = fetch_tsetmc_all_symbols()
            for sym in tsetmc_syms:
                if sym in existing_tickers:
                    continue
                if q in sym or q_upper in sym.upper():
                    suggestions.append({"ticker": sym, "name": sym, "source": "tsetmc"})
                    existing_tickers.add(sym)
        except Exception:
            pass

    if len(suggestions) < 5 and q_upper.isascii():
        try:
            yf_result = search_symbol(q_upper)
            if yf_result and not any(s["ticker"] == yf_result for s in suggestions):
                suggestions.append(
                    {"ticker": yf_result, "name": yf_result, "source": "global"}
                )
        except Exception:
            pass

    seen = set()
    unique = []
    for sug in suggestions:
        if sug["ticker"] not in seen:
            seen.add(sug["ticker"])
            unique.append(sug)
    suggestions = unique

    if suggestions:
        st.markdown(
            f'<div style="font-size:10px; color:{t["fg_muted"]}; margin:4px 0; direction:rtl;">'
            f"📌 {len(suggestions)} نتیجه</div>",
            unsafe_allow_html=True,
        )
        for i, sug in enumerate(suggestions[:8]):
            cols = st.columns([4, 1])
            with cols[0]:
                # ═══ منبع خودکار ═══
                auto_source = detect_source_for_ticker(sug["ticker"])
                source_info = {
                    "global": ("🌍", "جهانی", t["cyan"]),
                    "nobitex": ("🟣", "نوبیتکس", t["nobitex"]),
                    "abantether": ("🔵", "آبان‌تتر", t["abantether"]),
                    "tsetmc": ("🇮🇷", "بورس تهران", t["tsetmc"]),
                    "custom": ("⭐", "سفارشی", t["fg_muted"]),
                }.get(auto_source, ("•", "—", t["fg_muted"]))

                source_icon, source_name, source_color = source_info

                # ═══ قیمت (اگه هست) ═══
                price_str = ""
                if "price" in sug and sug.get("price"):
                    is_ir = _is_iranian_ticker(sug["ticker"])
                    if is_ir:
                        price_str = (
                            f' · <span style="color:{t["fg"]}; '
                            f"font-family:'JetBrains Mono';\">"
                            f'{sug["price"]:,.0f} تومان</span>'
                        )
                    else:
                        price_str = (
                            f' · <span style="color:{t["fg"]}; '
                            f"font-family:'JetBrains Mono';\">"
                            f'${sug["price"]:,.4f}</span>'
                        )

                # ═══ نمایش با بج منبع ═══
                st.markdown(
                    f'<div style="padding:8px 12px; background:{t["bg_card"]}; '
                    f'border:1px solid {t["border"]}; border-radius:8px; '
                    f"direction:rtl; text-align:right; font-size:11px; "
                    f'display:flex; justify-content:space-between; align-items:center; gap:8px;">'
                    f"<div>"
                    f'<b style="color:{t["primary"]};">{sug["ticker"]}</b> '
                    f'<span style="color:{t["fg_muted"]};">{sug["name"]}</span>'
                    f"{price_str}"
                    f"</div>"
                    f'<span style="font-size:9px; color:{source_color}; '
                    f"background:{source_color}15; padding:2px 8px; "
                    f'border-radius:6px; white-space:nowrap; font-weight:600;">'
                    f"{source_icon} {source_name}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with cols[1]:
                if st.button(
                    "📊 تحلیل",
                    key=f"add_sug_{i}_{sug['ticker']}",
                    use_container_width=True,
                    help=f"نمایش تحلیل {sug['ticker']}",
                ):
                    tkr = sug["ticker"]

                    # اضافه به لیست سفارشی (اگه نبود)
                    if (
                        tkr not in st.session_state.custom_symbols
                        and tkr not in SYMBOLS
                    ):
                        if (
                            len(st.session_state.custom_symbols)
                            < AppDefaults.MAX_CUSTOM_SYMBOLS
                        ):
                            st.session_state.custom_symbols.append(tkr)
                            save_custom_symbols(st.session_state.custom_symbols)

                    # ═══ انتخاب نماد (همیشه) ═══
                    st.session_state.selected_symbol = tkr
                    st.session_state.data_source = detect_source_for_ticker(tkr)
                    if detect_source_for_ticker(tkr) == "tsetmc":
                        st.session_state.market_type = "spot"
                        st.session_state.selected_tf = "روزانه"

                    st.rerun()

    else:
        st.info(f"نتیجه‌ای برای «{q}» پیدا نشد")


# ═══════════════════════════════════════════════════════════
# Popular symbols
# ═══════════════════════════════════════════════════════════
st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

sym_opts = dict(SYMBOLS)
if "USDT-IRT" not in sym_opts:
    sym_opts["USDT-IRT"] = "💵 تتر/تومان"
for custom in st.session_state.custom_symbols:
    sym_opts[custom] = f"⭐ {custom}"

POPULAR = [s[0] for s in POPULAR_SYMBOLS]
POPULAR_LABELS = {s[0]: s[1] for s in POPULAR_SYMBOLS}
popular_syms = [(k, sym_opts.get(k, POPULAR_LABELS.get(k, k))) for k in POPULAR]

if popular_syms:
    pop_cols = st.columns(len(popular_syms), gap="small")
    for i, (tkr, name) in enumerate(popular_syms):
        with pop_cols[i]:
            is_active = tkr == st.session_state.selected_symbol
            label = POPULAR_LABELS.get(tkr, name)
            if is_active:
                label += " ✓"
            if st.button(
                label,
                key=f"sp_{tkr}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.selected_symbol = tkr
                new_source = detect_source_for_ticker(tkr)
                st.session_state.data_source = new_source

                # ═══ market_type خودکار ═══
                if new_source == "tsetmc":
                    st.session_state.market_type = "spot"
                st.rerun()

other_syms = [(k, v) for k, v in sym_opts.items() if k not in POPULAR]
if other_syms:
    with st.expander("📋 همه نمادها", expanded=False):
        other_list = list(other_syms)
        rows_of_syms = [other_list[i : i + 7] for i in range(0, len(other_list), 7)]
        for row_syms in rows_of_syms:
            cols = st.columns(len(row_syms))
            for i, (tkr, name) in enumerate(row_syms):
                with cols[i]:
                    short_name = name.replace("⭐ ", "")[:14]
                    is_active = tkr == st.session_state.selected_symbol
                    if st.button(
                        f"{short_name}",
                        key=f"so_{tkr}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                    ):
                        st.session_state.selected_symbol = tkr
                        st.session_state.data_source = detect_source_for_ticker(tkr)
                        if detect_source_for_ticker(tkr) == "tsetmc":
                            st.session_state.market_type = "spot"
                            st.session_state.selected_tf = "روزانه"
                        st.rerun()

if st.session_state.custom_symbols:
    with st.expander("🗑 حذف نمادهای سفارشی", expanded=False):
        del_cols = st.columns(min(len(st.session_state.custom_symbols), 6))
        for i, tkr in enumerate(st.session_state.custom_symbols):
            with del_cols[i % 6]:
                if st.button(
                    f"❌ {tkr[:10]}", key=f"del_{tkr}", use_container_width=True
                ):
                    st.session_state.custom_symbols.remove(tkr)
                    save_custom_symbols(st.session_state.custom_symbols)
                    if st.session_state.selected_symbol == tkr:
                        st.session_state.selected_symbol = (
                            get_default_symbol_for_source(st.session_state.data_source)
                        )
                    st.rerun()


# ═══════════════════════════════════════════════════════════
# تایم‌فریم
# ═══════════════════════════════════════════════════════════
selected_ticker = st.session_state.selected_symbol
sym_name = sym_opts.get(selected_ticker, selected_ticker)

# ═══ TF — بدون key، پایدار ═══
if "selected_tf" not in st.session_state:
    st.session_state.selected_tf = AppDefaults.TIMEFRAME

_tf_index = (
    TF_NAMES.index(st.session_state.selected_tf)
    if st.session_state.selected_tf in TF_NAMES
    else 0
)

tf_choice = st.selectbox(
    "⏱ تایم فریم تحلیل",
    options=TF_NAMES,
    index=_tf_index,
)

if tf_choice != st.session_state.selected_tf:
    st.session_state.selected_tf = tf_choice
    st.rerun()

# ═══════════════════════════════════════════════════════════
# تحلیل
# ═══════════════════════════════════════════════════════════
current_source = st.session_state.get("data_source", "nobitex")
current_market_type = st.session_state.get("market_type", "futures")
risk_profile = st.session_state.get("risk_profile", "aggressive")

with st.spinner(f"⏳ تحلیل {sym_name}..."):

    def _analyze_one_tf(iv: str, p: str, n: str):
        try:
            df = cached_history(selected_ticker, iv, p, current_source)
            if df is None:
                print(f"[DEBUG] {n}: df None")
                return (n, None)
            if df.empty:
                print(f"[DEBUG] {n}: df empty")
                return (n, None)
            print(f"[DEBUG] {n}: {len(df)} کندل")
            a = analyze_symbol(
                df,
                risk_profile=risk_profile,
                tf_name=n,
                tfs_data=None,
                market_type=current_market_type,
                ticker=selected_ticker,
            )
            if a is None:
                print(f"[DEBUG] {n}: analyze returned None")
            else:
                print(f"[DEBUG] {n}: signal={a.get('signal')}")
            return (n, a)
        except Exception as e:
            import traceback

            print(f"[App] خطا در TF {n}: {e}")
            traceback.print_exc()
            return (n, None)

    tfs_data = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(_analyze_one_tf, iv, p, n) for iv, p, n in TIMEFRAMES
        ]
        for fut in as_completed(futures):
            try:
                n, a = fut.result()
                if a:
                    tfs_data[n] = a
            except Exception:
                pass

    analysis = tfs_data.get(tf_choice)

    if not analysis:
        for alt_tf in TF_NAMES:
            if alt_tf in tfs_data and tfs_data[alt_tf]:
                analysis = tfs_data[alt_tf]
                break

    if not analysis:
        st.error(f"❌ داده کافی برای {sym_name} در هیچ TF نیست.")
        if current_source == "global":
            st.warning(
                "**🔍 دلیل احتمالی:**\n\n"
                "Yahoo Finance از IP ایران در دسترس نیست.\n\n"
                "**✅ راه‌حل‌ها:**\n\n"
                "1. **VPN روشن کن**\n"
                "2. **از نمادهای کریپتو استفاده کن** — نوبیتکس\n"
                "3. **چند دقیقه صبر کن**"
            )
        else:
            st.info(
                "**💡 راه‌حل‌ها:**\n"
                "- یه نماد دیگه امتحان کن\n"
                "- منبع رو عوض کن\n"
                "- چند لحظه بعد دوباره امتحان کن"
            )
        st.stop()


# ═══════════════════════════════════════════════════════════
# ثبت سیگنال + بک‌تست خودکار
# ═══════════════════════════════════════════════════════════
if analysis and analysis.get("signal") in (
    "LONG",
    "SHORT",
    "LONG ضعیف",
    "SHORT ضعیف",
):
    record_signal(
        selected_ticker,
        sym_name,
        analysis["signal"],
        analysis["price"],
        tf_choice,
        analysis.get("sl_tp"),
        market_type=current_market_type,
        source=current_source,
    )

# ═══ بک‌تست: هر ۶۰ ثانیه، غیر-بلاکینگ ═══
import time as _time

now_ts = _time.time()
last_check = st.session_state.get("bt_last_check", 0)
if now_ts - last_check >= 60:
    # اول timestamp رو آپدیت کن تا دوباره اجرا نشه
    st.session_state["bt_last_check"] = now_ts

    # ═══ در background اجرا کن ═══
    try:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(backtest_all)
            result = future.result(timeout=5)  # حداکثر ۵ ثانیه صبر
            if result.get("updated", 0) > 0:
                st.session_state["bt_last_auto_update"] = datetime.now().strftime(
                    "%H:%M:%S"
                )
                st.session_state["bt_last_auto_result"] = result
    except TimeoutError:
        print("[App] backtest: timeout")
    except Exception as e:
        print(f"[App] backtest: {e}")

# ═══════════════════════════════════════════════════════════
# بخش ۱: تحلیل
# ═══════════════════════════════════════════════════════════
render_section_header(
    icon="📈",
    title="تحلیل بازار",
    subtitle=f"{sym_name} · {tf_choice} · {current_market_type}",
    color="primary",
    anchor_id="sec_analyze",
)

live_price = cached_live_price(selected_ticker, current_source)
render_unified_signal_card(
    analysis=analysis,
    sym_name=sym_name,
    tf_name=tf_choice,
    ticker=selected_ticker,
    last_update=st.session_state.get("last_data_refresh", ""),
    source=current_source,
    market_type=current_market_type,
    live_price=live_price,
)

if current_source in ("nobitex", "abantether") and "-USD" in selected_ticker:
    try:
        from core.nobitex_fetcher import map_symbol_to_nobitex, fetch_nobitex_orderbook

        nobitex_sym = map_symbol_to_nobitex(selected_ticker)
        if nobitex_sym:
            ob = fetch_nobitex_orderbook(nobitex_sym)
            if ob:
                render_order_book(ob, sym_name=sym_name, ticker=selected_ticker)
    except Exception:
        pass

st.markdown(
    f"<hr style='border-color:{t['border']}; margin:14px 0;'>", unsafe_allow_html=True
)
col_a, col_b = st.columns([1, 1])

with col_a:
    analysis_text = build_analysis_paragraph(
        selected_ticker,
        sym_name,
        tfs_data,
        gsr=cached_gsr(),
        risk_profile=risk_profile,
        tf_name=tf_choice,
    )
    render_deep_analysis(analysis_text, analysis, sym_name=sym_name)

    ai_export = build_ai_export(
        selected_ticker, sym_name, tf_choice, analysis, tfs_data
    )
    if ai_export:
        import html as _html

        escaped_js = (
            ai_export.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        )

        copy_button_html = f"""
        <div style="direction:rtl; text-align:center; margin-top:8px;">
            <button id="copy-ai-btn" style="
                background:#3B82F6;
                color:#fff;
                border:none;
                border-radius:10px;
                padding:10px 24px;
                font-family:IRANYekanX, Tahoma, sans-serif;
                font-size:13px;
                font-weight:700;
                cursor:pointer;
                width:100%;
                transition:all 0.2s;
                box-shadow:0 2px 8px rgba(59,130,246,0.3);
            ">📋 کپی داده‌ها برای AI</button>
            <div id="copy-ai-toast" style="
                display:none;
                margin-top:8px;
                padding:8px 12px;
                background:rgba(16,185,129,0.15);
                border:1px solid #10B981;
                border-radius:8px;
                color:#10B981;
                font-size:11px;
                font-weight:600;
            ">✅ داده‌ها در حافظه کپی شد</div>
        </div>
        <script>
        (function() {{
            const btn = document.getElementById('copy-ai-btn');
            const toast = document.getElementById('copy-ai-toast');
            const data = `{escaped_js}`;

            if (!btn) return;

            btn.addEventListener('click', function() {{
                navigator.clipboard.writeText(data).then(function() {{
                    toast.style.display = 'block';
                    btn.textContent = '✅ کپی شد';
                    btn.style.background = '#10B981';

                    setTimeout(function() {{
                        toast.style.display = 'none';
                        btn.textContent = '📋 کپی داده‌ها برای AI';
                        btn.style.background = '#3B82F6';
                    }}, 3000);
                }}).catch(function(err) {{
                    alert('خطا در کپی: ' + err);
                }});
            }});
        }})();
        </script>
        """

        components.html(copy_button_html, height=110)

with col_b:
    current_price = analysis.get("price", 0)
    render_tf_table(
        tfs_data,
        sym_name,
        current_price,
        ticker=selected_ticker,
    )

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    items, pct, final_text, final_color = build_checklist_weighted(
        tfs_data, main_tf=tf_choice
    )
    render_checklist(items, pct, final_text, final_color)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    df_for_fg = None
    for iv, p, n in TIMEFRAMES:
        if n == tf_choice:
            df_for_fg = cached_history(selected_ticker, iv, p, current_source)
            break
    if df_for_fg is not None:
        fg_val = compute_fear_greed(df_for_fg)
        render_fear_greed(fg_val)


# ═══════════════════════════════════════════════════════════
# بخش ۲: اسکنر
# ═══════════════════════════════════════════════════════════
render_section_header(
    icon="🎯",
    title="اسکنر فرصت‌ها",
    subtitle="پیدا کردن نمادهای مستعد نوسان",
    color="cyan",
    anchor_id="sec_scanner",
)

# ═══ جمع شدن اسکنر (پیش‌فرض بسته) ═══
if "scanner_open" not in st.session_state:
    st.session_state["scanner_open"] = False

_scan_cols = st.columns([4, 1])
with _scan_cols[1]:
    _scan_label = "❌ بستن" if st.session_state["scanner_open"] else "🔽 باز کردن"
    if st.button(
        _scan_label,
        key="scanner_toggle",
        use_container_width=True,
        type="primary" if st.session_state["scanner_open"] else "secondary",
    ):
        st.session_state["scanner_open"] = not st.session_state["scanner_open"]
        st.rerun()

if not st.session_state["scanner_open"]:
    st.info("💡 برای مشاهده فرصت‌ها، روی «🔽 باز کردن» کلیک کن.")
else:
    categories = get_categories_with_tickers()
    cat_keys = list(categories.keys())

    if cat_keys:
        # ═══ همه کد اسکنر اینجا (indented با ۸ فاصله) ═══

        if st.session_state.scanner_category not in cat_keys:
            st.session_state.scanner_category = cat_keys[0]

        n_cols = min(len(cat_keys), 6)
        cat_cols = st.columns(n_cols)
        for i, key in enumerate(cat_keys):
            cat = categories[key]
            short_name = (
                cat["name"].split(" ", 1)[-1] if " " in cat["name"] else cat["name"]
            )
            with cat_cols[i % n_cols]:
                is_active = st.session_state.scanner_category == key
                if st.button(
                    f"{cat['icon']} {short_name}",
                    key=f"cat_btn_{key}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.scanner_category = key
                    st.rerun()

        fc = st.columns([1.2, 1.2, 1, 1])
        with fc[0]:
            filt_opt = st.selectbox(
                "فیلتر",
                options=[("همه", "all"), ("LONG", "long"), ("SHORT", "short")],
                format_func=lambda x: x[0],
                index=0,
                key="scanner_filter_opt",
                label_visibility="collapsed",
            )
            st.session_state.scanner_filter = filt_opt[1]
        with fc[1]:
            scanner_tf = st.selectbox(
                "TF",
                options=TF_NAMES,
                index=(
                    TF_NAMES.index(st.session_state.scanner_tf)
                    if st.session_state.scanner_tf in TF_NAMES
                    else 1
                ),
                key="scanner_tf_select",
                label_visibility="collapsed",
            )
            st.session_state.scanner_tf = scanner_tf
        with fc[2]:
            if st.button("🔄 اسکن مجدد", key="rescan_btn", use_container_width=True):
                st.cache_data.clear()
                st.session_state.scanner_last_update = datetime.now().strftime(
                    "%H:%M:%S"
                )
                st.session_state.scanner_key = ""
                st.rerun()
        with fc[3]:
            st.markdown(
                f'<div style="text-align:center; padding:6px; font-size:10px; color:{t["fg_muted"]};">⏱ <b style="color:{t["cyan"]};">{st.session_state.scanner_tf}</b></div>',
                unsafe_allow_html=True,
            )

        scanner_tf_index = 0
        for i, (iv, p, n) in enumerate(TIMEFRAMES):
            if n == st.session_state.scanner_tf:
                scanner_tf_index = i
                break

        current_cat = st.session_state.scanner_category
        current_cat_name = categories[current_cat]["name"]

        with st.spinner(f"⏳ اسکن {current_cat_name}..."):
            scan_data = cached_scan(current_cat, scanner_tf_index, current_market_type)

        scan_key = f"{current_cat}_{scanner_tf_index}"
        if st.session_state.get("scanner_key", "") != scan_key:
            st.session_state.scanner_key = scan_key
            st.session_state.scanner_last_update = datetime.now().strftime("%H:%M:%S")
        if not st.session_state.get("scanner_last_update", ""):
            st.session_state.scanner_last_update = datetime.now().strftime("%H:%M:%S")

        selected_from_scan = render_scanner(
            scan_data=scan_data,
            filter_signal=st.session_state.scanner_filter,
            last_update=st.session_state.scanner_last_update,
        )

        if selected_from_scan:
            tkr = selected_from_scan
            if tkr not in st.session_state.custom_symbols and tkr not in SYMBOLS:
                if (
                    len(st.session_state.custom_symbols)
                    < AppDefaults.MAX_CUSTOM_SYMBOLS
                ):
                    st.session_state.custom_symbols.append(tkr)
                    save_custom_symbols(st.session_state.custom_symbols)
            st.session_state.selected_symbol = tkr
            st.session_state.data_source = detect_source_for_ticker(tkr)
            if detect_source_for_ticker(tkr) == "tsetmc":
                st.session_state.market_type = "spot"
                st.session_state.selected_tf = "روزانه"
            st.rerun()


# ═══════════════════════════════════════════════════════════
# بخش ۳: راستی‌آزمایی
# ═══════════════════════════════════════════════════════════
render_section_header(
    icon="✅",
    title="راستی‌آزمایی",
    subtitle="نتایج واقعی سیگنال‌های گذشته",
    color="green",
    anchor_id="sec_history",
)

log = load_signal_log()
stats = compute_stats(log)
render_backtest_stats(stats, logs=log)
if log:
    render_recent_signals_list(log)


# ═══════════════════════════════════════════════════════════
# FAB
# ═══════════════════════════════════════════════════════════
render_back_to_top_fab()


# ═══════════════════════════════════════════════════════════
# فوتر
# ═══════════════════════════════════════════════════════════
source_info = get_source_info(st.session_state.get("data_source", "nobitex"))
market_label = MarketType.display_fa(st.session_state.get("market_type", "futures"))

st.markdown(
    f'<div style="text-align:center; padding:12px 0;'
    f' border-top:1px solid {t["border"]}; margin-top:8px;'
    f' color:{t["fg_dim"]}; font-size:9px; direction:rtl;">'
    f"تریدمون © ۲۰۲۶"
    f' | منبع: <b style="color:{t["cyan"]};">{source_info["icon"]} {source_info["full_name"]}</b>'
    f' | بازار: <b style="color:{t["cyan"]};">{market_label}</b>'
    f' | آخرین: <b style="color:{t["cyan"]};">{st.session_state.last_update}</b>'
    f"</div>",
    unsafe_allow_html=True,
)

# ═══ ذخیره خودکار تنظیمات ═══
_persist_prefs()
