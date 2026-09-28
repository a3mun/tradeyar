"""
app.py
TradeYar — نسخه ۳۳.۰ (نهایی)
========================
- معماری رژیم‌محور (روند/گذار/رنج)
- دو پروفایل: جسورانه / محتاطانه
- سه منبع دیتا: جهانی / نوبیتکس / آبان‌تتر
- باکس تنظیمات یکپارچه
- چک‌لیست آکاردئونی
- جدول TF ریسپانسیو (شامل ۱ دقیقه)
- راستی‌آزمایی با لیست کشویی سیگنال‌ها
- جستجوی هوشمند + پایدار
- Order Book (عمق بازار)
- تم تاریک/روشن بازطراحی‌شده
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import json

import streamlit as st
import streamlit.components.v1 as components

from core.data_fetcher import (
    SYMBOLS, TIMEFRAMES,
    fetch_iran_prices, fetch_history, fetch_gold_silver_ratio,
    search_symbol,
)
from core.analyzer import (
    analyze_symbol, compute_fear_greed,
    build_checklist_weighted, build_analysis_paragraph,
)
from core.scanner import scan_markets
from core.market_lists import get_categories_with_tickers
from core.news import fetch_news
from core.calendar import fetch_calendar
from core.backtester import compute_stats, load_signal_log, record_signal, backtest_all
from core.utils import get_jalali_date, get_weekday_fa

from ui.styles import get_custom_css, get_theme
from ui.components import (
    render_header, render_top_ticker, render_unified_signal_card,
    render_tf_table, render_deep_analysis, render_fear_greed,
    render_calendar, render_news, render_backtest_stats, render_checklist,
    render_section_toggle, render_scanner, render_live_timer,
    render_profile_selector, render_source_selector,
    render_settings_section_title, render_settings_divider,
    render_order_book, render_recent_signals_list,
)


# ═══════════════════════════════════════════════════════════
# تنظیمات صفحه
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="TradeYar — ترید‌یار",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ═══════════════════════════════════════════════════════════
# session_state
# ═══════════════════════════════════════════════════════════
defaults = {
    "theme": "dark",
    "selected_symbol": "GC=F",
    "selected_tf": "۵ دقیقه",
    "risk_profile": "aggressive",
    "data_source": "global",
    "custom_symbol": "",
    "custom_symbols": [],
    "last_update": datetime.now().strftime("%H:%M"),
    "last_data_refresh": datetime.now().strftime("%H:%M:%S"),
    "scanner_last_update": "",
    "refresh_seconds": 0,
    "bt_done": False,
    "bt_time_filter": "all",
    "bt_confirm_reset": False,
    "show_calendar": False,
    "show_news": False,
    "show_scanner": True,
    "scanner_filter": "all",
    "scanner_category": "crypto",
    "scanner_tf": "۵ دقیقه",
    "scanner_key": "",
    "expanded_scanner": True,
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
            interval=st.session_state.refresh_seconds * 1000,
            key="auto_refresh",
        )
    except ImportError:
        pass


# ═══════════════════════════════════════════════════════════
# Cache — پایه
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def cached_history(ticker, interval, period, source="global"):
    """دریافت OHLCV بر اساس منبع انتخابی"""
    from core.data_fetcher import fetch_history_by_source
    return fetch_history_by_source(ticker, interval, period, source)


@st.cache_data(ttl=60, show_spinner=False)
def cached_prices():
    return fetch_iran_prices()


@st.cache_data(ttl=900, show_spinner=False)
def cached_news():
    return fetch_news(max_per_source=2, total_max=8)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_calendar():
    return fetch_calendar(hours_ahead=24, days_ahead=7)


@st.cache_data(ttl=600, show_spinner=False)
def cached_gsr():
    return fetch_gold_silver_ratio()


@st.cache_data(ttl=300, show_spinner=False)
def cached_scan_category(category: str, tf_index: int):
    return scan_markets(
        category=category,
        tf_index=tf_index,
        top_n=5,
        risk_profile="aggressive",
    )


@st.cache_data(ttl=300, show_spinner=False)
def cached_nobitex_search(query: str):
    try:
        from core.nobitex_fetcher import fetch_all_nobitex_symbols, NOBITEX_SYMBOLS
        all_syms = fetch_all_nobitex_symbols("usdt")
        reverse_map = {v: k for k, v in NOBITEX_SYMBOLS.items()}
        q_upper = query.upper()
        results = []
        for s in all_syms:
            if q_upper in s["symbol"] or q_upper in s["base"]:
                our_ticker = reverse_map.get(s["symbol"], f"{s['base']}-USD")
                results.append({
                    "ticker": our_ticker,
                    "name": f"{s['base']}/{s['quote']}",
                    "source": "nobitex",
                    "price": s["price"],
                    "change": s["change_24h"],
                })
        return results[:10]
    except Exception as e:
        print(f"[App] خطا در جستجوی نوبیتکس: {e}")
        return []


@st.cache_data(ttl=5, show_spinner=False)
def cached_ticker_data(source: str):
    """قیمت‌های تیکر (کش ۵ ثانیه)"""
    result = []

    ip = fetch_iran_prices()
    if ip.get("prices"):
        p = ip["prices"]
        result.extend([
            {"name": "طلای ۱۸", "emoji": "🥇", "price": p.get("geram18"), "change_pct": None, "unit": "تومان"},
            {"name": "سکه امامی", "emoji": "🪙", "price": p.get("sekee"), "change_pct": None, "unit": "تومان"},
            {"name": "دلار", "emoji": "💵", "price": p.get("dollar"), "change_pct": None, "unit": "تومان"},
            {"name": "انس جهانی", "emoji": "🌍", "price": p.get("ons"), "change_pct": None, "unit": "دلار"},
        ])

    if source == "nobitex":
        try:
            from core.nobitex_fetcher import (
                fetch_all_nobitex_symbols,
                filter_liquid_symbols,
            )
            all_syms = fetch_all_nobitex_symbols("usdt")
            top = filter_liquid_symbols(all_syms, min_volume=100000, max_count=8)

            emoji_map_crypto = {
                "BTC": "₿", "ETH": "Ξ", "SOL": "◎", "XRP": "✕",
                "DOGE": "🐕", "BNB": "🟡", "ADA": "🔵", "TON": "💎",
                "NEAR": "Ⓝ", "SUI": "💧", "AVAX": "🔺", "LINK": "🔗",
            }
            for s in top:
                base = s["base"]
                result.append({
                    "name": f"{base}/USDT",
                    "emoji": emoji_map_crypto.get(base, "💰"),
                    "price": s["price"],
                    "change_pct": s["change_24h"],
                    "unit": "دلار",
                })
        except Exception as e:
            print(f"[App] خطا در تیکر نوبیتکس: {e}")

    emoji_map_global = {"GC=F": "🥇", "SI=F": "🥈", "BTC-USD": "₿", "BZ=F": "🛢"}
    for tkr, name in SYMBOLS.items():
        try:
            d = fetch_history(tkr, "1h", "5d")
            if d is not None and len(d) > 0:
                lp = float(d["close"].iloc[-1])
                pp = float(d["close"].iloc[-2]) if len(d) > 1 else lp
                ch = ((lp - pp) / pp * 100) if pp > 0 else 0
                result.append({
                    "name": name, "emoji": emoji_map_global.get(tkr, "💰"),
                    "price": lp, "change_pct": ch, "unit": "دلار",
                })
        except Exception:
            continue

    return result


# ═══════════════════════════════════════════════════════════
# Cache — تحلیل
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def cached_analysis_v3(
    ticker: str,
    interval: str,
    period: str,
    tf_name: str,
    tfs_snapshot: str,
    risk_profile: str,
    source: str = "global",
):
    df = cached_history(ticker, interval, period, source)
    if df is None or df.empty:
        return None

    tfs_data = None
    if tfs_snapshot:
        try:
            tfs_data = json.loads(tfs_snapshot)
        except Exception:
            tfs_data = None

    return analyze_symbol(
        df,
        risk_profile=risk_profile,
        tf_name=tf_name,
        tfs_data=tfs_data,
    )


# ═══════════════════════════════════════════════════════════
# Snapshot
# ═══════════════════════════════════════════════════════════
def _make_tfs_snapshot(tfs_data: dict, exclude_tf: str = None) -> str:
    snapshot = {}
    if tfs_data:
        for tf, data in tfs_data.items():
            if tf == exclude_tf:
                continue
            if data:
                snapshot[tf] = {
                    "signal": data.get("signal", ""),
                    "confidence": data.get("confidence", 0),
                    "direction": data.get("direction", "neutral"),
                }
    return json.dumps(snapshot, sort_keys=True, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════
# تحلیل موازی
# ═══════════════════════════════════════════════════════════
def fetch_and_analyze_multi_tf(
    ticker: str,
    risk_profile: str,
    source: str = "global",
) -> dict:
    tfs_data = {}

    def _process_tf_first(iv, p, n):
        try:
            a = cached_analysis_v3(ticker, iv, p, n, "", risk_profile, source)
            if a:
                return (n, a)
        except Exception as e:
            print(f"[App] خطا در TF {n} (مرحله ۱): {e}")
        return (n, None)

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(_process_tf_first, iv, p, n)
            for iv, p, n in TIMEFRAMES
        ]
        for fut in as_completed(futures):
            try:
                n, a = fut.result()
                if a:
                    tfs_data[n] = a
            except Exception as e:
                print(f"[App] خطا در future (مرحله ۱): {e}")

    if not tfs_data:
        return {}

    tfs_data_v2 = {}

    def _process_tf_second(iv, p, n):
        try:
            snapshot = _make_tfs_snapshot(tfs_data, exclude_tf=n)
            a = cached_analysis_v3(ticker, iv, p, n, snapshot, risk_profile, source)
            if a:
                return (n, a)
            return (n, tfs_data.get(n))
        except Exception as e:
            print(f"[App] خطا در TF {n} (مرحله ۲): {e}")
            return (n, tfs_data.get(n))

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(_process_tf_second, iv, p, n)
            for iv, p, n in TIMEFRAMES
        ]
        for fut in as_completed(futures):
            try:
                n, a = fut.result()
                if a:
                    tfs_data_v2[n] = a
            except Exception as e:
                print(f"[App] خطا در future (مرحله ۲): {e}")

    return tfs_data_v2 if tfs_data_v2 else tfs_data


# ═══════════════════════════════════════════════════════════
# بازارها
# ═══════════════════════════════════════════════════════════
def get_markets_info() -> list:
    now = datetime.utcnow() + timedelta(hours=3, minutes=30)
    h, m, wd = now.hour, now.minute, now.weekday()
    tm = h * 60 + m

    is_weekend_global = wd in [5, 6]
    markets = []

    tokyo_open = (not is_weekend_global) and 210 <= tm < 720
    if is_weekend_global:
        markets.append({"name": "توکیو", "icon": "🇯🇵", "is_open": False, "next_event": "تعطیل آخر هفته"})
    else:
        markets.append({"name": "توکیو", "icon": "🇯🇵", "is_open": tokyo_open,
                        "next_event": "باز تا ۱۲:۰۰" if tokyo_open else "باز می‌شه ۰۳:۳۰"})

    london_open = (not is_weekend_global) and 690 <= tm < 1200
    if is_weekend_global:
        markets.append({"name": "لندن", "icon": "🇪🇺", "is_open": False, "next_event": "تعطیل آخر هفته"})
    else:
        markets.append({"name": "لندن", "icon": "🇪🇺", "is_open": london_open,
                        "next_event": "باز تا ۲۰:۰۰" if london_open else "باز می‌شه ۱۱:۳۰"})

    ny_open = (not is_weekend_global) and 990 <= tm < 1380
    if is_weekend_global:
        markets.append({"name": "نیویورک", "icon": "🇺🇸", "is_open": False, "next_event": "تعطیل آخر هفته"})
    else:
        markets.append({"name": "نیویورک", "icon": "🇺🇸", "is_open": ny_open,
                        "next_event": "باز تا ۲۳:۰۰" if ny_open else "باز می‌شه ۱۶:۳۰"})

    iran_days = [5, 6, 0, 1, 2]
    iran_open = (wd in iran_days) and 540 <= tm < 750
    if wd not in iran_days:
        markets.append({"name": "بورس تهران", "icon": "🇮🇷", "is_open": False, "next_event": "تعطیل (پنج‌شنبه/جمعه)"})
    else:
        markets.append({"name": "بورس تهران", "icon": "🇮🇷", "is_open": iran_open,
                        "next_event": "باز تا ۱۲:۳۰" if iran_open else "باز می‌شه ۹:۰۰"})

    gold_fund_open = (wd in iran_days) and 720 <= tm < 1080
    if wd not in iran_days:
        markets.append({"name": "صندوق طلا", "icon": "🇮🇷", "is_open": False, "next_event": "تعطیل (پنج‌شنبه/جمعه)"})
    else:
        markets.append({"name": "صندوق طلا", "icon": "🇮🇷", "is_open": gold_fund_open,
                        "next_event": "باز تا ۱۸:۰۰" if gold_fund_open else "باز می‌شه ۱۲:۰۰"})

    return markets


# ═══════════════════════════════════════════════════════════
# هدر
# ═══════════════════════════════════════════════════════════
jalali = get_jalali_date()
weekday = get_weekday_fa()
miladi = (datetime.utcnow() + timedelta(hours=3, minutes=30)).strftime("%Y-%m-%d")

t = get_theme(st.session_state.theme)

render_header(jalali, weekday, miladi)


# ═══════════════════════════════════════════════════════════
# Placeholder تیکر
# ═══════════════════════════════════════════════════════════
ticker_placeholder = st.empty()
with ticker_placeholder:
    st.markdown(
        f'<div style="background:{t["bg_card"]}; border:1px solid {t["border"]};'
        f' border-radius:10px; padding:20px; text-align:center;'
        f' color:{t["fg_muted"]}; direction:rtl;">'
        f'⏳ در حال دریافت قیمت‌ها...</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════
# ⚙️ تنظیمات
# ═══════════════════════════════════════════════════════════
with st.container(border=True):
    render_settings_section_title("🎯", "پروفایل تحلیل")
    render_profile_selector(st.session_state.risk_profile)

    render_settings_divider()

    render_settings_section_title("📡", "منبع دیتا")
    render_source_selector(st.session_state.data_source)

    render_settings_divider()

    render_settings_section_title("🔄", "کنترل به‌روزرسانی")

    ctrl_cols = st.columns([3, 1, 1.5])

    with ctrl_cols[0]:
        refresh_options = [
            ("🖐 دستی", 0),
            ("⚡ ۵ ثانیه", 5),
            ("⏱ ۱۰ ثانیه", 10),
            ("⏱ ۳۰ ثانیه", 30),
            ("⏱ ۱ دقیقه", 60),
            ("⏱ ۵ دقیقه", 300),
        ]

        current_idx = 0
        for i, (_, secs) in enumerate(refresh_options):
            if secs == st.session_state.refresh_seconds:
                current_idx = i
                break

        refresh_choice = st.radio(
            "حالت به‌روزرسانی خودکار",
            options=refresh_options,
            format_func=lambda x: x[0],
            index=current_idx,
            horizontal=True,
            label_visibility="collapsed",
            key="refresh_toggle",
        )

        if refresh_choice[1] != st.session_state.refresh_seconds:
            st.session_state.refresh_seconds = refresh_choice[1]
            st.session_state.last_update = datetime.now().strftime("%H:%M")
            st.session_state.last_data_refresh = datetime.now().strftime("%H:%M:%S")
            st.rerun()

    with ctrl_cols[1]:
        if st.button("🔄 بروزرسانی حالا", key="manual_refresh", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.session_state.last_data_refresh = datetime.now().strftime("%H:%M:%S")
            st.session_state.last_update = datetime.now().strftime("%H:%M")
            st.rerun()

    with ctrl_cols[2]:
        last_refresh = st.session_state.get("last_data_refresh", "")
        if last_refresh:
            render_live_timer(
                last_refresh,
                key="top_refresh",
                prefix="🕐 آخرین بروزرسانی:",
                font_size=11,
                color=t["cyan"],
            )

st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# جستجوی هوشمند
# ═══════════════════════════════════════════════════════════
st.markdown(
    f'<div style="font-size:13px; font-weight:700; color:{t["primary"]}; '
    f'margin-bottom:6px; padding-right:8px; border-right:3px solid {t["primary"]}; '
    f'direction:rtl; text-align:right;">🔍 جستجوی نماد</div>',
    unsafe_allow_html=True,
)

search_cols = st.columns([5, 1])
with search_cols[0]:
    search_query = st.text_input(
        "جستجو",
        placeholder="مثال: BTC، ETH، ZEC، PAXG، بیت‌کوین",
        label_visibility="collapsed",
        key="search_input",
    )
with search_cols[1]:
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    search_btn = st.button("🔍 جستجو", use_container_width=True, key="search_btn")

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

    nobitex_results = cached_nobitex_search(q_upper)
    suggestions.extend(nobitex_results)

    if suggestions:
        st.markdown(
            f'<div style="font-size:10px; color:{t["fg_muted"]}; '
            f'margin:4px 0; direction:rtl;">'
            f'📌 {len(suggestions)} نتیجه</div>',
            unsafe_allow_html=True,
        )

        for i, sug in enumerate(suggestions[:8]):
            cols = st.columns([4, 1])
            with cols[0]:
                source_icon = {
                    "global": "🌍",
                    "nobitex": "🟣",
                    "custom": "⭐",
                }.get(sug["source"], "•")

                price_str = ""
                change_str = ""
                if "price" in sug:
                    price_str = f' · <span style="color:{t["fg"]}; font-family:\'JetBrains Mono\'; direction:ltr;">${sug["price"]:,.4f}</span>'
                if "change" in sug:
                    c = t["green"] if sug["change"] > 0 else t["red"]
                    change_str = f' · <span style="color:{c}; font-family:\'JetBrains Mono\';">{sug["change"]:+.2f}%</span>'

                st.markdown(
                    f'<div style="padding:6px 10px; background:{t["bg_card"]}; '
                    f'border:1px solid {t["border"]}; border-radius:8px; '
                    f'direction:rtl; text-align:right; font-size:11px;">'
                    f'{source_icon} <b style="color:{t["primary"]};">{sug["ticker"]}</b> '
                    f'— <span style="color:{t["fg_muted"]};">{sug["name"]}</span>'
                    f'{price_str}{change_str}</div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                if st.button(
                    "➕",
                    key=f"add_sug_{i}_{sug['ticker']}",
                    use_container_width=True,
                ):
                    tkr = sug["ticker"]
                    if tkr not in st.session_state.custom_symbols and tkr not in SYMBOLS:
                        if len(st.session_state.custom_symbols) < 10:
                            st.session_state.custom_symbols.append(tkr)
                    st.session_state.selected_symbol = tkr
                    st.rerun()
    else:
        st.info(f"نتیجه‌ای برای «{q}» پیدا نشد")


# ═══════════════════════════════════════════════════════════
# انتخاب نماد
# ═══════════════════════════════════════════════════════════
st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

emoji_map = {"GC=F": "🥇", "SI=F": "🥈", "BTC-USD": "₿", "BZ=F": "🛢"}

sym_opts = dict(SYMBOLS)
for custom in st.session_state.custom_symbols:
    sym_opts[custom] = f"⭐ {custom}"

POPULAR = ["GC=F", "BTC-USD", "BZ=F", "SI=F"]
popular_syms = [(k, sym_opts[k]) for k in POPULAR if k in sym_opts]

if popular_syms:
    pop_cols = st.columns(len(popular_syms))
    for i, (tkr, name) in enumerate(popular_syms):
        with pop_cols[i]:
            short_name = name.replace("⭐ ", "")[:12]
            is_active = tkr == st.session_state.selected_symbol
            if st.button(
                f"{emoji_map.get(tkr, '📌')} {short_name}",
                key=f"sp_{tkr}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.selected_symbol = tkr
                st.rerun()

other_syms = [(k, v) for k, v in sym_opts.items() if k not in POPULAR]
if other_syms:
    other_list = list(other_syms)
    rows_of_syms = [other_list[i:i+7] for i in range(0, len(other_list), 7)]

    for row_syms in rows_of_syms:
        cols = st.columns(len(row_syms))
        for i, (tkr, name) in enumerate(row_syms):
            with cols[i]:
                short_name = name.replace("⭐ ", "")[:12]
                is_active = tkr == st.session_state.selected_symbol
                if st.button(
                    f"{emoji_map.get(tkr, '📌')} {short_name}",
                    key=f"so_{tkr}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.selected_symbol = tkr
                    st.rerun()

if st.session_state.custom_symbols:
    with st.expander("🗑 حذف نمادهای سفارشی", expanded=False):
        del_cols = st.columns(min(len(st.session_state.custom_symbols), 6))
        for i, tkr in enumerate(st.session_state.custom_symbols):
            with del_cols[i % 6]:
                if st.button(f"❌ {tkr[:10]}", key=f"del_{tkr}", use_container_width=True):
                    st.session_state.custom_symbols.remove(tkr)
                    if st.session_state.selected_symbol == tkr:
                        st.session_state.selected_symbol = "GC=F"
                    st.rerun()


# ═══════════════════════════════════════════════════════════
# تایم‌فریم
# ═══════════════════════════════════════════════════════════
selected_ticker = st.session_state.selected_symbol
sym_name = sym_opts.get(selected_ticker, selected_ticker)

tf_names = [tf[2] for tf in TIMEFRAMES]

tf_choice = st.selectbox(
    "⏱ تایم فریم تحلیل",
    options=tf_names,
    index=tf_names.index(st.session_state.selected_tf) if st.session_state.selected_tf in tf_names else 1,
    key="tf_select",
)
st.session_state.selected_tf = tf_choice

tf_interval, tf_period = "5m", "5d"
tf_index_current = 0
for i, (iv, p, n) in enumerate(TIMEFRAMES):
    if n == tf_choice:
        tf_interval, tf_period = iv, p
        tf_index_current = i
        break


# ═══════════════════════════════════════════════════════════
# تحلیل
# ═══════════════════════════════════════════════════════════
current_source = st.session_state.get("data_source", "global")

with st.spinner(f"⏳ تحلیل {sym_name}..."):
    df_main = cached_history(selected_ticker, tf_interval, tf_period, current_source)

    if df_main is None or df_main.empty:
        st.error(f"❌ داده‌ای برای {sym_name} یافت نشد (منبع: {current_source}).")
        st.info(
            "💡 **راه‌حل‌ها:**\n"
            "- اگه منبع «نوبیتکس» هست، مطمئن شو نماد کریپتو هست\n"
            "- اگه منبع «جهانی» هست، اتصال اینترنت رو چک کن\n"
            "- یه نماد دیگه امتحان کن"
        )
        st.stop()

    tfs_data = fetch_and_analyze_multi_tf(
        selected_ticker,
        st.session_state.risk_profile,
        current_source,
    )

    snapshot_main = _make_tfs_snapshot(tfs_data, exclude_tf=tf_choice)
    analysis = cached_analysis_v3(
        selected_ticker,
        tf_interval,
        tf_period,
        tf_choice,
        snapshot_main,
        st.session_state.risk_profile,
        current_source,
    )

    if not analysis:
        analysis = tfs_data.get(tf_choice)

    if not analysis:
        analysis = analyze_symbol(
            df_main,
            risk_profile=st.session_state.risk_profile,
            tf_name=tf_choice,
            tfs_data=tfs_data,
        )


# ثبت سیگنال
if analysis and analysis.get("signal") in ("LONG", "SHORT"):
    record_signal(
        selected_ticker, sym_name, analysis["signal"],
        analysis["price"], tf_choice, analysis.get("sl_tp"),
    )

if not st.session_state.bt_done:
    try:
        backtest_all()
    except Exception as e:
        print(f"[App] خطا در backtest: {e}")
    st.session_state.bt_done = True


# ═══════════════════════════════════════════════════════════
# کارت سیگنال
# ═══════════════════════════════════════════════════════════
render_unified_signal_card(
    analysis=analysis,
    sym_name=sym_name,
    tf_name=tf_choice,
    ticker=selected_ticker,
    last_update=st.session_state.get("last_data_refresh", ""),
    source=current_source,
)


# ═══════════════════════════════════════════════════════════
# Order Book (عمق بازار)
# ═══════════════════════════════════════════════════════════
if current_source in ("nobitex", "abantether") and "-USD" in selected_ticker:
    try:
        from core.nobitex_fetcher import (
            map_symbol_to_nobitex,
            fetch_nobitex_orderbook,
        )

        nobitex_sym = map_symbol_to_nobitex(selected_ticker)
        if nobitex_sym:
            ob = fetch_nobitex_orderbook(nobitex_sym)
            if ob:
                render_order_book(ob, sym_name=sym_name)
    except Exception as e:
        print(f"[App] خطا در Order Book: {e}")


# ═══════════════════════════════════════════════════════════
# تحلیل عمیق + جدول TF + چک‌لیست + Fear & Greed
# ═══════════════════════════════════════════════════════════
st.markdown("<hr style='border-color:#21262D; margin:14px 0;'>", unsafe_allow_html=True)
col_a, col_b = st.columns([1, 1])

with col_a:
    analysis_text = build_analysis_paragraph(
        selected_ticker, sym_name, tfs_data,
        gsr=cached_gsr(),
        risk_profile=st.session_state.risk_profile,
        tf_name=tf_choice,
    )
    render_deep_analysis(analysis_text, analysis, sym_name=sym_name)

with col_b:
    current_price = analysis.get("price", 0) if analysis else 0
    render_tf_table(tfs_data, sym_name, current_price)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:13px; font-weight:bold; color:{t["primary"]};'
        f' margin-bottom:8px; padding-right:8px; border-right:3px solid {t["primary"]};'
        f' direction:rtl; text-align:right;">📋 چک‌لیست گروهی</div>',
        unsafe_allow_html=True,
    )
    items, pct, final_text, final_color = build_checklist_weighted(tfs_data, main_tf=tf_choice)
    render_checklist(items, pct, final_text, final_color)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    fg_val = compute_fear_greed(df_main)
    render_fear_greed(fg_val)


# ═══════════════════════════════════════════════════════════
# اسکنر فرصت‌ها
# ═══════════════════════════════════════════════════════════
st.markdown("<hr style='border-color:#21262D; margin:14px 0;'>", unsafe_allow_html=True)

with st.expander("🎯 اسکنر فرصت‌ها — پیدا کردن نماد مستعد نوسان", expanded=True):

    st.markdown(
        f'<div style="font-size:11px; color:{t["fg_muted"]}; margin-bottom:8px; '
        f'direction:rtl; padding-right:8px; border-right:3px solid {t["primary"]};">'
        f'🎯 انتخاب بازار هدف:</div>',
        unsafe_allow_html=True,
    )

    categories = get_categories_with_tickers()
    cat_keys = list(categories.keys())

    if not cat_keys:
        st.warning("هیچ بازاری تعریف نشده.")
    else:
        if st.session_state.scanner_category not in cat_keys:
            st.session_state.scanner_category = cat_keys[0]

        n_cols = min(len(cat_keys), 6)
        cat_cols = st.columns(n_cols)

        for i, key in enumerate(cat_keys):
            cat = categories[key]
            short_name = cat["name"].split(" ", 1)[-1] if " " in cat["name"] else cat["name"]

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

        st.markdown(
            f'<div style="font-size:11px; color:{t["fg_muted"]}; margin:12px 0 8px 0; '
            f'direction:rtl; padding-right:8px; border-right:3px solid {t["primary"]};">'
            f'⚙️ تنظیمات اسکن:</div>',
            unsafe_allow_html=True,
        )

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
                "تایم‌فریم اسکن",
                options=tf_names,
                index=tf_names.index(st.session_state.scanner_tf) if st.session_state.scanner_tf in tf_names else 1,
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
                f'<div style="text-align:center; padding:6px; font-size:10px; '
                f'color:{t["fg_muted"]};">⏱ اسکن با: '
                f'<b style="color:{t["cyan"]};">{st.session_state.scanner_tf}</b></div>',
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
            scan_data = cached_scan_category(current_cat, scanner_tf_index)

        scan_key = f"{current_cat}_{scanner_tf_index}"

        if st.session_state.get("scanner_key", "") != scan_key:
            st.session_state.scanner_key = scan_key
            st.session_state.scanner_last_update = datetime.now().strftime("%H:%M:%S")

        if not st.session_state.get("scanner_last_update", ""):
            st.session_state.scanner_last_update = datetime.now().strftime("%H:%M:%S")

        selected_ticker_from_scan = render_scanner(
            scan_data=scan_data,
            filter_signal=st.session_state.scanner_filter,
            last_update=st.session_state.scanner_last_update,
        )

        if selected_ticker_from_scan:
            tkr = selected_ticker_from_scan
            if tkr in SYMBOLS:
                st.info(f"ℹ️ {tkr} از قبل توی نمادهای اصلیه.")
            elif tkr in st.session_state.custom_symbols:
                st.info(f"ℹ️ {tkr} از قبل توی نمادهای توئه.")
            elif len(st.session_state.custom_symbols) >= 10:
                st.warning("⚠️ حداکثر ۱۰ نماد سفارشی.")
            else:
                st.session_state.custom_symbols.append(tkr)
                st.session_state.selected_symbol = tkr
                st.success(f"✅ {tkr} اضافه شد و انتخاب شد!")
                st.rerun()


# ═══════════════════════════════════════════════════════════
# راستی‌آزمایی
# ═══════════════════════════════════════════════════════════
st.markdown("<hr style='border-color:#21262D; margin:14px 0;'>", unsafe_allow_html=True)
st.markdown(
    f'<div style="font-size:13px; font-weight:bold; color:{t["primary"]};'
    f' margin-bottom:8px; padding-right:8px; border-right:3px solid {t["primary"]};'
    f' direction:rtl; text-align:right;">✅ راستی‌آزمایی</div>',
    unsafe_allow_html=True,
)
log = load_signal_log()
stats = compute_stats(log)
render_backtest_stats(stats, logs=log)

if log:
    render_recent_signals_list(log)


# ═══════════════════════════════════════════════════════════
# تقویم + اخبار
# ═══════════════════════════════════════════════════════════
st.markdown("<hr style='border-color:#21262D; margin:14px 0;'>", unsafe_allow_html=True)

toggle_cols = st.columns([1, 1])

with toggle_cols[0]:
    show_cal = render_section_toggle(
        key="calendar",
        label_on="📅 نمایش تقویم اقتصادی",
        label_off="❌ بستن تقویم",
        icon_on="📅",
        icon_off="❌",
    )

with toggle_cols[1]:
    show_news_flag = render_section_toggle(
        key="news",
        label_on="📰 نمایش اخبار بازار",
        label_off="❌ بستن اخبار",
        icon_on="📰",
        icon_off="❌",
    )


if show_cal:
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    with st.spinner("دریافت تقویم اقتصادی..."):
        try:
            cal = cached_calendar()
        except Exception as e:
            print(f"[App] خطا در تقویم: {e}")
            cal = None

    if cal and cal.get("all"):
        render_calendar(cal)
        st.markdown(
            f'<div style="font-size:9px; color:{t["fg_dim"]};'
            f' text-align:center; margin-top:8px; direction:rtl;">'
            f'⚠️ داده‌های تقویم ممکنه تا ۲۴ ساعت تأخیر داشته باشه</div>',
            unsafe_allow_html=True,
        )
    else:
        st.warning("⚠️ تقویم اقتصادی در دسترس نیست.")

if show_news_flag:
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    with st.spinner("دریافت اخبار..."):
        try:
            news = cached_news()
        except Exception as e:
            print(f"[App] خطا در اخبار: {e}")
            news = []

    if news:
        render_news(news)
    else:
        st.warning("⚠️ اخبار در دسترس نیست.")


# ═══════════════════════════════════════════════════════════
# تیکر — مستقل از نماد انتخابی
# ═══════════════════════════════════════════════════════════
with ticker_placeholder:
    current_source_ticker = st.session_state.get("data_source", "global")
    gp = cached_ticker_data(current_source_ticker)
    markets_info = get_markets_info()
    render_top_ticker(gp, markets_info)


# ═══════════════════════════════════════════════════════════
# دکمه تم
# ═══════════════════════════════════════════════════════════
st.markdown("<hr style='border-color:#21262D; margin:14px 0 8px 0;'>", unsafe_allow_html=True)

last_row = st.columns([1, 3, 1])
with last_row[1]:
    theme_label = "☀️ حالت روشن" if st.session_state.theme == "dark" else "🌙 حالت تیره"
    if st.button(theme_label, key="theme_btn_bottom", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()


# ═══════════════════════════════════════════════════════════
# فوتر
# ═══════════════════════════════════════════════════════════
source_label_footer = {
    "global": "yfinance (جهانی)",
    "nobitex": "نوبیتکس",
    "abantether": "آبان‌تتر",
}.get(st.session_state.get("data_source", "global"), "—")

ip_footer = cached_prices()

st.markdown(
    f'<div style="text-align:center; padding:12px 0;'
    f' border-top:1px solid {t["border"]}; margin-top:8px;'
    f' color:{t["fg_dim"]}; font-size:9px; direction:rtl;">'
    f'منبع قیمت ایران: <b style="color:{t["cyan"]};">{ip_footer.get("source", "—")}</b>'
    f' | منبع تحلیل: <b style="color:{t["cyan"]};">{source_label_footer}</b>'
    f' | آخرین: <b style="color:{t["cyan"]};">{st.session_state.last_update}</b>'
    f'</div>',
    unsafe_allow_html=True,
)