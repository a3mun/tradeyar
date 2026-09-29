"""
app.py
AsemunYar (آسمون‌یار) — نسخه ۴۴.۰ (STABLE — بدون باگ)
============================================================
نسخه ساده و قابل اعتماد.
- بدون URL state
- سوییچ خودکار ساده
- منبع قابل تغییر دستی
- جدول TF همه تایم‌فریم‌ها
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import json
from pathlib import Path

import streamlit as st

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
)

# ═══════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AsemunYar — آسمون‌یار",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ═══════════════════════════════════════════════════════════
# Custom symbols persistence
# ═══════════════════════════════════════════════════════════
CUSTOM_SYMBOLS_FILE = Path("data/custom_symbols.json")


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
# session_state — ساده
# ═══════════════════════════════════════════════════════════
defaults = {
    "theme": AppDefaults.THEME,
    "selected_symbol": AppDefaults.SYMBOL,  # GC=F
    "selected_tf": AppDefaults.TIMEFRAME,  # ۵ دقیقه
    "risk_profile": AppDefaults.RISK_PROFILE,  # aggressive
    "market_type": AppDefaults.MARKET_TYPE,  # futures
    "data_source": AppDefaults.DATA_SOURCE,  # global
    "custom_symbols": load_custom_symbols(),
    "last_update": datetime.now().strftime("%H:%M"),
    "last_data_refresh": datetime.now().strftime("%H:%M:%S"),
    "scanner_last_update": "",
    "refresh_seconds": AppDefaults.REFRESH_SECONDS,
    "bt_time_filter": "all",
    "bt_confirm_reset": False,
    "scanner_filter": "all",
    "scanner_category": "crypto",
    "scanner_tf": "۵ دقیقه",
    "scanner_key": "",
    "settings_open": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


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
# Cache — بدون @st.cache_data روی analyze_symbol
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
    now = datetime.utcnow() + timedelta(hours=3, minutes=30)
    h, m, wd = now.hour, now.minute, now.weekday()
    tm = h * 60 + m
    is_weekend_global = wd in [5, 6]
    markets = []
    tokyo_open = (not is_weekend_global) and 210 <= tm < 720
    markets.append(
        {
            "name": "توکیو",
            "icon": "🇯🇵",
            "is_open": tokyo_open,
            "next_event": (
                "تعطیل" if is_weekend_global else ("باز" if tokyo_open else "بسته")
            ),
        }
    )
    london_open = (not is_weekend_global) and 690 <= tm < 1200
    markets.append(
        {
            "name": "لندن",
            "icon": "🇪🇺",
            "is_open": london_open,
            "next_event": (
                "تعطیل" if is_weekend_global else ("باز" if london_open else "بسته")
            ),
        }
    )
    ny_open = (not is_weekend_global) and 990 <= tm < 1380
    markets.append(
        {
            "name": "نیویورک",
            "icon": "🇺🇸",
            "is_open": ny_open,
            "next_event": (
                "تعطیل" if is_weekend_global else ("باز" if ny_open else "بسته")
            ),
        }
    )
    iran_days = [5, 6, 0, 1, 2]
    iran_open = (wd in iran_days) and 540 <= tm < 750
    markets.append(
        {
            "name": "بورس تهران",
            "icon": "🇮🇷",
            "is_open": iran_open,
            "next_event": (
                "تعطیل" if wd not in iran_days else ("باز" if iran_open else "بسته")
            ),
        }
    )
    return markets


def build_ai_export(
    ticker: str, name: str, tf_name: str, analysis: dict, tfs_data: dict
) -> str:
    if not analysis:
        return ""
    lines = []
    lines.append(f"# تحلیل {name} ({ticker})")
    lines.append(f"## تایم‌فریم: {tf_name}")
    lines.append("")
    lines.append("## خلاصه")
    lines.append(f"- سیگنال: **{analysis.get('signal', '—')}**")
    lines.append(f"- اطمینان: **{analysis.get('confidence', 0)}%**")
    lines.append(
        f"- رژیم: **{analysis.get('regime', '—')}** (ADX={analysis.get('adx', 0):.0f})"
    )
    lines.append(f"- قیمت: **{analysis.get('price', 0):.4f}**")
    lines.append("")
    lines.append("## اندیکاتورها")
    for k, label in [
        ("rsi", "RSI"),
        ("stoch_k", "Stoch K"),
        ("stoch_d", "Stoch D"),
        ("willr", "Williams %R"),
        ("macd_hist", "MACD Hist"),
        ("ema200", "EMA200"),
        ("atr", "ATR"),
        ("adx", "ADX"),
    ]:
        lines.append(f"- {label}: {analysis.get(k, 0)}")
    lines.append("")
    lines.append("## TFها")
    for tf in TF_NAMES:
        if tf in tfs_data:
            a = tfs_data[tf]
            lines.append(
                f"- **{tf}**: {a.get('signal', '—')} ({a.get('confidence', 0)}%)"
            )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# هدر
# ═══════════════════════════════════════════════════════════
t = get_theme(st.session_state.theme)
render_header(get_jalali_date(), get_weekday_fa(), get_miladi_date())

render_settings_panel_open_button()
render_settings_panel()


# ═══════════════════════════════════════════════════════════
# Placeholder تیکر
# ═══════════════════════════════════════════════════════════
ticker_placeholder = st.empty()
with ticker_placeholder:
    st.markdown(
        f'<div style="background:{t["bg_card"]}; border:1px solid {t["border"]};'
        f" border-radius:10px; padding:20px; text-align:center;"
        f' color:{t["fg_muted"]}; direction:rtl;">'
        f"⏳ در حال دریافت قیمت‌ها...</div>",
        unsafe_allow_html=True,
    )


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

    for tkr, name in SYMBOLS.items():
        if q_upper in tkr.upper() or q in name:
            suggestions.append({"ticker": tkr, "name": name, "source": "global"})

    for tkr in st.session_state.custom_symbols:
        if q_upper in tkr.upper():
            suggestions.append({"ticker": tkr, "name": tkr, "source": "custom"})

    try:
        from core.nobitex_fetcher import (
            fetch_all_nobitex_symbols,
            map_nobitex_to_symbol,
        )

        all_nobitex = fetch_all_nobitex_symbols("usdt")
        for s in all_nobitex[:100]:
            if q_upper in s["symbol"] or q_upper in s["base"]:
                our_ticker = map_nobitex_to_symbol(s["symbol"])
                if our_ticker:
                    suggestions.append(
                        {
                            "ticker": our_ticker,
                            "name": f"{s['base']}/{s['quote']}",
                            "source": "nobitex",
                            "price": s["price"],
                            "change": s.get("change_24h", 0),
                        }
                    )
    except Exception:
        pass

    try:
        tsetmc_syms = fetch_tsetmc_all_symbols()
        for sym in tsetmc_syms:
            if q in sym or q_upper in sym.upper():
                suggestions.append({"ticker": sym, "name": sym, "source": "tsetmc"})
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
                source_icon = {
                    "global": "🌍",
                    "nobitex": "🟣",
                    "tsetmc": "🇮🇷",
                    "custom": "⭐",
                }.get(sug["source"], "•")
                price_str = ""
                if "price" in sug:
                    price_str = f' · <span style="color:{t["fg"]}; font-family:\'JetBrains Mono\';">${sug["price"]:,.4f}</span>'
                st.markdown(
                    f'<div style="padding:6px 10px; background:{t["bg_card"]}; '
                    f'border:1px solid {t["border"]}; border-radius:8px; '
                    f'direction:rtl; text-align:right; font-size:11px;">'
                    f'{source_icon} <b style="color:{t["primary"]};">{sug["ticker"]}</b> '
                    f'— <span style="color:{t["fg_muted"]};">{sug["name"]}</span>{price_str}</div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                if st.button(
                    "➕", key=f"add_sug_{i}_{sug['ticker']}", use_container_width=True
                ):
                    tkr = sug["ticker"]
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
                    st.session_state.selected_symbol = tkr
                    st.session_state.data_source = detect_source_for_ticker(tkr)
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
    pop_cols = st.columns(len(popular_syms))
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
                st.session_state.data_source = detect_source_for_ticker(tkr)
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

tf_choice = st.selectbox(
    "⏱ تایم فریم تحلیل",
    options=TF_NAMES,
    index=(
        TF_NAMES.index(st.session_state.selected_tf)
        if st.session_state.selected_tf in TF_NAMES
        else 0
    ),
    key="tf_select",
)
st.session_state.selected_tf = tf_choice


# ═══════════════════════════════════════════════════════════
# تحلیل — همه TFها
# ═══════════════════════════════════════════════════════════
current_source = st.session_state.get("data_source", "global")
current_market_type = st.session_state.get("market_type", "futures")
risk_profile = st.session_state.get("risk_profile", "aggressive")

with st.spinner(f"⏳ تحلیل {sym_name}..."):
    # ═══ تحلیل همه TFها موازی ═══
    def _analyze_one_tf(iv: str, p: str, n: str):
        try:
            df = cached_history(selected_ticker, iv, p, current_source)
            if df is None or df.empty:
                return (n, None)
            a = analyze_symbol(
                df,
                risk_profile=risk_profile,
                tf_name=n,
                tfs_data=None,
                market_type=current_market_type,
            )
            return (n, a)
        except Exception as e:
            print(f"[App] خطا در TF {n}: {e}")
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

    # ═══ تحلیل اصلی ═══
    analysis = tfs_data.get(tf_choice)

    if not analysis:
        for alt_tf in TF_NAMES:
            if alt_tf in tfs_data and tfs_data[alt_tf]:
                analysis = tfs_data[alt_tf]
                break

    # اگه هیچی نبود
    if not analysis:
        st.error(f"❌ داده کافی برای {sym_name} در هیچ TF نیست.")
        st.info(
            f"💡 **راه‌حل‌ها:**\n"
            f"- یه نماد دیگه امتحان کن\n"
            f"- منبع رو عوض کن\n"
            f"- چند لحظه بعد دوباره امتحان کن"
        )
        st.stop()


# ثبت سیگنال + backtest
if analysis and analysis.get("signal") in ("LONG", "SHORT", "LONG ضعیف", "SHORT ضعیف"):
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

try:
    backtest_all()
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
                render_order_book(ob, sym_name=sym_name)
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
        st.download_button(
            label="📋 دانلود خروجی برای AI",
            data=ai_export,
            file_name=f"asemunyar_{selected_ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True,
            key="ai_export_btn",
        )

with col_b:
    current_price = analysis.get("price", 0)
    selected_tf_from_table = render_tf_table(tfs_data, sym_name, current_price)
    if (
        selected_tf_from_table
        and selected_tf_from_table != st.session_state.selected_tf
    ):
        st.session_state.selected_tf = selected_tf_from_table
        st.rerun()

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    items, pct, final_text, final_color = build_checklist_weighted(
        tfs_data, main_tf=tf_choice
    )
    render_checklist(items, pct, final_text, final_color)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Fear & Greed
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

categories = get_categories_with_tickers()
cat_keys = list(categories.keys())

if cat_keys:
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
            st.session_state.scanner_last_update = datetime.now().strftime("%H:%M:%S")
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
            if len(st.session_state.custom_symbols) < AppDefaults.MAX_CUSTOM_SYMBOLS:
                st.session_state.custom_symbols.append(tkr)
                save_custom_symbols(st.session_state.custom_symbols)
        st.session_state.selected_symbol = tkr
        st.session_state.data_source = detect_source_for_ticker(tkr)
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
# تیکر
# ═══════════════════════════════════════════════════════════
with ticker_placeholder:
    gp = cached_ticker_data(st.session_state.get("data_source", "global"))
    markets_info = get_markets_info()
    render_top_ticker(gp, markets_info)


# ═══════════════════════════════════════════════════════════
# FAB
# ═══════════════════════════════════════════════════════════
render_back_to_top_fab()


# ═══════════════════════════════════════════════════════════
# فوتر
# ═══════════════════════════════════════════════════════════
source_info = get_source_info(st.session_state.get("data_source", "global"))
market_label = MarketType.display_fa(st.session_state.get("market_type", "futures"))

st.markdown(
    f'<div style="text-align:center; padding:12px 0;'
    f' border-top:1px solid {t["border"]}; margin-top:8px;'
    f' color:{t["fg_dim"]}; font-size:9px; direction:rtl;">'
    f"آسمون‌یار © ۲۰۲۶"
    f' | منبع: <b style="color:{t["cyan"]};">{source_info["icon"]} {source_info["full_name"]}</b>'
    f' | بازار: <b style="color:{t["cyan"]};">{market_label}</b>'
    f' | آخرین: <b style="color:{t["cyan"]};">{st.session_state.last_update}</b>'
    f"</div>",
    unsafe_allow_html=True,
)
