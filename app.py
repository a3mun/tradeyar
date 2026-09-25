"""
app.py
TradeYar — نسخه ۱۸.۰ (نهایی فاز ۳)
هدر یکپارچه سه‌بخشی + Marquee پیوسته + حذف ساعت قدیمی
"""

from datetime import datetime, timedelta

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
from core.news import fetch_news
from core.calendar import fetch_calendar
from core.backtester import compute_stats, load_signal_log, record_signal, backtest_all
from core.utils import get_jalali_date, get_weekday_fa

from ui.styles import get_custom_css, get_theme
from ui.components import (
    render_header, render_top_ticker, render_main_signal,
    render_tf_table, render_deep_analysis, render_fear_greed,
    render_calendar, render_news, render_backtest_stats, render_checklist,
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
    "selected_tf": "۱ ساعت",
    "custom_symbol": "",
    "custom_symbols": [],
    "last_update": datetime.now().strftime("%H:%M"),
    "refresh_seconds": 0,
    "bt_done": False,
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
# Cache
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def cached_history(ticker, interval, period):
    return fetch_history(ticker, interval, period)


@st.cache_data(ttl=60, show_spinner=False)
def cached_prices():
    return fetch_iran_prices()


@st.cache_data(ttl=300, show_spinner=False)
def cached_news():
    return fetch_news(max_per_source=2, total_max=8)


@st.cache_data(ttl=600, show_spinner=False)
def cached_calendar():
    return fetch_calendar(hours_ahead=24, days_ahead=7)


@st.cache_data(ttl=600, show_spinner=False)
def cached_gsr():
    return fetch_gold_silver_ratio()


# ═══════════════════════════════════════════════════════════
# بازارها — با تعطیلات ایران و جهان
# ═══════════════════════════════════════════════════════════
def get_markets_info() -> list:
    now = datetime.utcnow() + timedelta(hours=3, minutes=30)
    h, m, wd = now.hour, now.minute, now.weekday()
    tm = h * 60 + m

    # پایتون: 0=دوشنبه, 1=سه‌شنبه, 2=چهارشنبه, 3=پنج‌شنبه, 4=جمعه, 5=شنبه, 6=یک‌شنبه
    is_weekend_global = wd in [5, 6]      # شنبه و یک‌شنبه — بازارهای جهانی
    is_weekend_iran = wd in [3, 4]         # پنج‌شنبه و جمعه — بازارهای ایران

    markets = []

    # ─── توکیو: ۰۳:۳۰ تا ۱۲:۰۰ ───
    tokyo_open = (not is_weekend_global) and 210 <= tm < 720
    if is_weekend_global:
        markets.append({
            "name": "توکیو", "icon": "🇯🇵", "is_open": False,
            "next_event": "تعطیل آخر هفته",
        })
    else:
        markets.append({
            "name": "توکیو", "icon": "🇯🇵", "is_open": tokyo_open,
            "next_event": "باز تا ۱۲:۰۰" if tokyo_open else "باز می‌شه ۰۳:۳۰",
        })

    # ─── لندن: ۱۱:۳۰ تا ۲۰:۰۰ ───
    london_open = (not is_weekend_global) and 690 <= tm < 1200
    if is_weekend_global:
        markets.append({
            "name": "لندن", "icon": "🇪🇺", "is_open": False,
            "next_event": "تعطیل آخر هفته",
        })
    else:
        markets.append({
            "name": "لندن", "icon": "🇪🇺", "is_open": london_open,
            "next_event": "باز تا ۲۰:۰۰" if london_open else "باز می‌شه ۱۱:۳۰",
        })

    # ─── نیویورک: ۱۶:۳۰ تا ۲۳:۰۰ ───
    ny_open = (not is_weekend_global) and 990 <= tm < 1380
    if is_weekend_global:
        markets.append({
            "name": "نیویورک", "icon": "🇺🇸", "is_open": False,
            "next_event": "تعطیل آخر هفته",
        })
    else:
        markets.append({
            "name": "نیویورک", "icon": "🇺🇸", "is_open": ny_open,
            "next_event": "باز تا ۲۳:۰۰" if ny_open else "باز می‌شه ۱۶:۳۰",
        })

    # ─── بورس تهران: شنبه تا چهارشنبه ۹:۰۰ تا ۱۲:۳۰ ───
    iran_days = [5, 6, 0, 1, 2]  # شنبه، یک‌شنبه، دوشنبه، سه‌شنبه، چهارشنبه
    iran_open = (wd in iran_days) and 540 <= tm < 750
    if wd not in iran_days:
        markets.append({
            "name": "بورس تهران", "icon": "🇮🇷", "is_open": False,
            "next_event": "تعطیل (پنج‌شنبه/جمعه)",
        })
    else:
        markets.append({
            "name": "بورس تهران", "icon": "🇮🇷", "is_open": iran_open,
            "next_event": "باز تا ۱۲:۳۰" if iran_open else "باز می‌شه ۹:۰۰",
        })

    # ─── صندوق طلا: ۱۲:۰۰ تا ۱۸:۰۰ ───
    gold_fund_open = (wd in iran_days) and 720 <= tm < 1080
    if wd not in iran_days:
        markets.append({
            "name": "صندوق طلا", "icon": "🇮🇷", "is_open": False,
            "next_event": "تعطیل (پنج‌شنبه/جمعه)",
        })
    else:
        markets.append({
            "name": "صندوق طلا", "icon": "🇮🇷", "is_open": gold_fund_open,
            "next_event": "باز تا ۱۸:۰۰" if gold_fund_open else "باز می‌شه ۱۲:۰۰",
        })

    return markets


# ═══════════════════════════════════════════════════════════
# هدر یکپارچه
# ═══════════════════════════════════════════════════════════
jalali = get_jalali_date()
weekday = get_weekday_fa()
miladi = (datetime.utcnow() + timedelta(hours=3, minutes=30)).strftime("%Y-%m-%d")

t = get_theme(st.session_state.theme)

render_header(jalali, weekday, miladi)


# ═══════════════════════════════════════════════════════════
# نوار بالایی (قیمت + بازارها) با Marquee پیوسته
# ═══════════════════════════════════════════════════════════
emoji_map = {"GC=F": "🥇", "SI=F": "🥈", "BTC-USD": "₿", "BZ=F": "🛢"}

# ─── ۱) اول قیمت‌های ایران ───
gp = []
ip = cached_prices()
if ip.get("prices"):
    p = ip["prices"]
    gp.extend([
        {"name": "طلای ۱۸", "emoji": "🥇", "price": p.get("geram18"), "change_pct": None, "unit": "تومان"},
        {"name": "سکه امامی", "emoji": "🪙", "price": p.get("sekee"), "change_pct": None, "unit": "تومان"},
        {"name": "دلار", "emoji": "💵", "price": p.get("dollar"), "change_pct": None, "unit": "تومان"},
        {"name": "انس جهانی", "emoji": "🌍", "price": p.get("ons"), "change_pct": None, "unit": "دلار"},
    ])

# ─── ۲) بعد نمادهای جهانی ───
for tkr, name in SYMBOLS.items():
    d = cached_history(tkr, "1h", "5d")
    if d is not None and len(d) > 0:
        lp = float(d["close"].iloc[-1])
        pp = float(d["close"].iloc[-2]) if len(d) > 1 else lp
        ch = ((lp - pp) / pp * 100) if pp > 0 else 0
        gp.append({
            "name": name, "emoji": emoji_map.get(tkr, "💰"),
            "price": lp, "change_pct": ch, "unit": "دلار",
        })

markets_info = get_markets_info()
render_top_ticker(gp, markets_info)

# ═══════════════════════════════════════════════════════════
# کنترل‌ها: به‌روزرسانی + جستجو
# ═══════════════════════════════════════════════════════════
ctrl = st.columns([2, 3])

with ctrl[0]:
    refresh_opt = st.selectbox(
        "به‌روزرسانی",
        options=[
            ("🔄 به‌روزرسانی دستی", 0),
            ("⏱ هر ۳۰ ثانیه خودکار", 30),
            ("⏱ هر ۱ دقیقه خودکار", 60),
            ("⏱ هر ۵ دقیقه خودکار", 300),
        ],
        format_func=lambda x: x[0],
        index=0,
        label_visibility="collapsed",
        key="refresh_select",
    )
    if refresh_opt[1] != st.session_state.refresh_seconds:
        st.session_state.refresh_seconds = refresh_opt[1]
        st.cache_data.clear()
        st.session_state.last_update = datetime.now().strftime("%H:%M")
        st.rerun()

with ctrl[1]:
    search = st.text_input(
        "جستجوی نماد (با اینتر تایید کنید)",
        placeholder="مثال: AAPL, EURUSD, BTC, TSLA",
        label_visibility="collapsed",
        key="search_input",
    )
    if search:
        last_search = st.session_state.get("_last_search", "")
        if search != last_search:
            st.session_state["_last_search"] = search
            s = search.strip()

            if len(st.session_state.custom_symbols) >= 6:
                st.warning("⚠️ حداکثر ۶ نماد سفارشی می‌تونی اضافه کنی")
            else:
                with st.spinner(f"جستجوی {s}..."):
                    found = search_symbol(s)
                    if found:
                        if found not in st.session_state.custom_symbols and found not in SYMBOLS:
                            st.session_state.custom_symbols.append(found)

                        st.session_state.custom_symbol = found
                        st.session_state.selected_symbol = found
                        st.success(f"✅ {found} اضافه شد")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ نماد «{s}» یافت نشد — لطفاً بررسی کنید")


# ═══════════════════════════════════════════════════════════
# انتخاب نماد
# ═══════════════════════════════════════════════════════════
st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

sym_opts = dict(SYMBOLS)
for custom in st.session_state.custom_symbols:
    sym_opts[custom] = f"⭐ {custom}"

syms_list = list(sym_opts.items())
rows_of_syms = [syms_list[i:i+5] for i in range(0, len(syms_list), 5)]

for row_syms in rows_of_syms:
    cols = st.columns(len(row_syms))
    for i, (tkr, name) in enumerate(row_syms):
        with cols[i]:
            if st.button(
                f"{emoji_map.get(tkr, '📌')} {name}",
                key=f"s_{tkr}",
                use_container_width=True,
                type="primary" if tkr == st.session_state.selected_symbol else "secondary",
            ):
                st.session_state.selected_symbol = tkr
                st.rerun()

            st.markdown(
                f'<div style="text-align:center; font-size:9px; color:{t["fg_dim"]}; margin-top:2px; direction:ltr;">{tkr}</div>',
                unsafe_allow_html=True,
            )

            if tkr in st.session_state.custom_symbols:
                if st.button("🗑 حذف", key=f"del_{tkr}", use_container_width=True):
                    st.session_state.custom_symbols.remove(tkr)
                    if st.session_state.selected_symbol == tkr:
                        st.session_state.selected_symbol = "GC=F"
                    st.rerun()


# ═══════════════════════════════════════════════════════════
# تحلیل نماد
# ═══════════════════════════════════════════════════════════
selected_ticker = st.session_state.selected_symbol
sym_name = sym_opts.get(selected_ticker, selected_ticker)

tf_names = [tf[2] for tf in TIMEFRAMES]
tf_choice = st.selectbox(
    "⏱ تایم فریم",
    options=tf_names,
    index=tf_names.index(st.session_state.selected_tf) if st.session_state.selected_tf in tf_names else 3,
    key="tf_select",
)
st.session_state.selected_tf = tf_choice

tf_interval, tf_period = "1h", "3mo"
for iv, p, n in TIMEFRAMES:
    if n == tf_choice:
        tf_interval, tf_period = iv, p
        break

with st.spinner(f"تحلیل {sym_name}..."):
    df_main = cached_history(selected_ticker, tf_interval, tf_period)

if df_main is None or df_main.empty:
    st.error(f"❌ داده‌ای برای {sym_name} یافت نشد.")
    st.stop()

analysis = analyze_symbol(df_main, "medium")

if analysis and analysis.get("signal") in ("LONG", "SHORT"):
    record_signal(
        selected_ticker, sym_name, analysis["signal"],
        analysis["price"], tf_choice, analysis.get("sl_tp"),
    )

if not st.session_state.bt_done:
    try:
        backtest_all()
    except Exception:
        pass
    st.session_state.bt_done = True


# ═══════════════════════════════════════════════════════════
# کارت سیگنال
# ═══════════════════════════════════════════════════════════
render_main_signal(analysis, sym_name, tf_choice)

st.markdown("<hr style='border-color:#21262D; margin:10px 0;'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# جدول TF
# ═══════════════════════════════════════════════════════════
with st.spinner("محاسبه تحلیل چند تایم‌فریمی..."):
    tfs_data = {}
    for iv, p, n in TIMEFRAMES:
        d = cached_history(selected_ticker, iv, p)
        if d is not None and not d.empty:
            a = analyze_symbol(d, "medium")
            if a:
                tfs_data[n] = a

current_price = analysis.get("price", 0) if analysis else 0
render_tf_table(tfs_data, sym_name, current_price)


# ═══════════════════════════════════════════════════════════
# Fear & Greed
# ═══════════════════════════════════════════════════════════
st.markdown("<hr style='border-color:#21262D; margin:10px 0;'>", unsafe_allow_html=True)
fg_val = compute_fear_greed(df_main)
render_fear_greed(fg_val)


# ═══════════════════════════════════════════════════════════
# تحلیل عمیق + چک‌لیست
# ═══════════════════════════════════════════════════════════
st.markdown("<hr style='border-color:#21262D; margin:14px 0;'>", unsafe_allow_html=True)
col_a, col_b = st.columns([1, 1])

with col_a:
    analysis_text = build_analysis_paragraph(
        selected_ticker, sym_name, tfs_data,
        gsr=cached_gsr(),
        risk_profile="medium",
        tf_name=tf_choice,
    )
    render_deep_analysis(analysis_text, analysis)

with col_b:
    st.markdown(
        f'<div style="font-size:13px; font-weight:bold; color:{t["primary"]};'
        f' margin-bottom:8px; padding-right:8px; border-right:3px solid {t["primary"]};'
        f' direction:rtl; text-align:right;">📋 چک‌لیست</div>',
        unsafe_allow_html=True,
    )
    items, pct, final_text, final_color = build_checklist_weighted(tfs_data)
    render_checklist(items, pct, final_text, final_color)


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


# ═══════════════════════════════════════════════════════════
# تقویم + اخبار
# ═══════════════════════════════════════════════════════════
st.markdown("<hr style='border-color:#21262D; margin:14px 0;'>", unsafe_allow_html=True)
c1, c2 = st.columns([1, 1])

with c1:
    with st.spinner("تقویم..."):
        cal = cached_calendar()
    if cal and cal.get("all"):
        render_calendar(cal)
        st.markdown(
            f'<div style="font-size:9px; color:{t["fg_dim"]};'
            f' text-align:center; margin-top:8px; direction:rtl;">'
            f'⚠️ داده‌های تقویم ممکنه تا ۲۴ ساعت تأخیر داشته باشه</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("تقویم در دسترس نیست.")

with c2:
    with st.spinner("اخبار..."):
        news = cached_news()
    render_news(news)


# ═══════════════════════════════════════════════════════════
# ردیف آخر: دکمه تم
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
st.markdown(
    f'<div style="text-align:center; padding:12px 0;'
    f' border-top:1px solid {t["border"]}; margin-top:8px;'
    f' color:{t["fg_dim"]}; font-size:9px; direction:rtl;">'
    f'منبع: <b style="color:{t["cyan"]};">{ip.get("source", "—")}</b>'
    f' | تحلیل: <b style="color:{t["cyan"]};">yfinance</b>'
    f' | آخرین: <b style="color:{t["cyan"]};">{st.session_state.last_update}</b>'
    f'</div>',
    unsafe_allow_html=True,
)