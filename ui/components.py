"""
ui/components.py
کامپوننت‌های رابط کاربری — نسخه ۱۷.۱ (فاز ۵.۵)
============================================================
تغییرات نسخه ۱۷.۱:
  - رفع باگ تشخیص تومان/دلار: از ticker به جای heuristic قیمت
  - _build_sr_rows پارامتر ticker می‌گیره
  - render_tf_table پارامتر ticker می‌گیره
  - sl_tp_note با neutral_explain (short + long + hint)
  - جعبه تله‌ها (_render_traps_box)
  - جعبه سناریوها (_render_scenarios_box)
"""

from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from core.contracts import (
    AnalysisGroup,
    Consensus,
    MarketType,
    Regime,
    Signal as SigEnum,
    SignalResult,
)
from core.sources import get_source_info
from ui.styles import get_theme


# ═══════════════════════════════════════════════════════════
# ابزار پایه
# ═══════════════════════════════════════════════════════════
def _t() -> dict:
    return get_theme(st.session_state.get("theme", "dark"))


def _render(html: str) -> None:
    clean = "".join(line.strip() for line in html.split("\n"))
    st.markdown(clean, unsafe_allow_html=True)


def _safe_num(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _is_iranian_ticker(ticker: str) -> bool:
    """تشخیص نمادهای تومانی/ریالی از روی ticker"""
    if not ticker:
        return False
    upper = ticker.upper()
    return "IRT" in upper or "RLS" in upper or upper == "USDT-IRT"


# ═══════════════════════════════════════════════════════════
# Sparkline
# ═══════════════════════════════════════════════════════════
def sparkline_svg(
    prices: list, color: str, width: int = 70, height: int = 26, trend: str = "flat"
) -> str:
    if not prices or len(prices) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    try:
        prices = [float(p) for p in prices if p is not None]
    except (ValueError, TypeError):
        return f'<svg width="{width}" height="{height}"></svg>'
    if len(prices) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'

    mn, mx = min(prices), max(prices)
    if mx == mn:
        mx = mn + 1
    n = len(prices)
    pts = []
    for i, p in enumerate(prices):
        x = int(i * width / (n - 1))
        y = int(height - ((p - mn) / (mx - mn)) * (height - 4) - 2)
        pts.append(f"{x},{y}")

    arrow = "▲" if trend == "up" else ("▼" if trend == "down" else "●")

    return (
        f'<div style="display:inline-flex; align-items:center; gap:4px;">'
        f'<span style="color:{color}; font-size:11px; font-weight:bold;">{arrow}</span>'
        f'<svg width="{width}" height="{height}" style="display:inline-block; vertical-align:middle;">'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        f"</div>"
    )


# ═══════════════════════════════════════════════════════════
# هدر رنگی بخش
# ═══════════════════════════════════════════════════════════
def render_section_header(
    icon: str,
    title: str,
    subtitle: str = "",
    color: str = "primary",
    anchor_id: str = "",
) -> None:
    t = _t()
    color_map = {
        "primary": t["primary"],
        "green": t["green"],
        "orange": t["orange"],
        "cyan": t["cyan"],
        "red": t["red"],
        "purple": t["purple"],
    }
    c = color_map.get(color, t["primary"])

    anchor_html = (
        f'<div id="{anchor_id}" style="scroll-margin-top:20px;"></div>'
        if anchor_id
        else ""
    )

    subtitle_html = (
        f'<div style="font-size:11px; color:{t["fg_muted"]}; margin-top:5px; '
        f'direction:rtl; text-align:right;">{subtitle}</div>'
        if subtitle
        else ""
    )

    st.markdown(
        f"""
        {anchor_html}
        <div style="
            display:flex; align-items:center; gap:14px;
            padding:16px 22px; margin:22px 0 14px 0;
            background:linear-gradient(135deg, {c}20, {c}08);
            border:2px solid {c}66;
            border-right:6px solid {c};
            border-radius:14px;
            direction:rtl;
            box-shadow:0 4px 16px {c}15;
        ">
            <span style="font-size:30px; filter:drop-shadow(0 0 8px {c}88);">{icon}</span>
            <div style="text-align:right;">
                <div style="font-size:18px; font-weight:700; color:{c}; letter-spacing:0.3px;">
                    {title}
                </div>
                {subtitle_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════
# هدر اصلی
# ═══════════════════════════════════════════════════════════
def render_header(jalali: str, weekday: str, miladi: str) -> None:
    t = _t()

    try:
        from ui.styles import get_logo_base64

        logo_b64 = get_logo_base64()
        if logo_b64:
            logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="header-logo" alt="AsemunYar" />'
        else:
            logo_html = '<span style="font-size:36px;">🏆</span>'
    except Exception:
        logo_html = '<span style="font-size:36px;">🏆</span>'

    header_html = f"""
    <style>
        @media (max-width: 900px) {{
            .header-brand {{ display: none !important; }}
            .header-logo {{ width: 42px !important; height: 42px !important; }}
        }}
    </style>
    <div class="asemunyar-header">
        <div class="header-left">
            {logo_html}
            <div class="header-brand">
                <div class="header-brand-fa">آسمون‌یار</div>
                <div class="header-brand-en">AsemunYar</div>
            </div>
        </div>

        <div class="header-center">
            <div style="font-size:11px; color:{t['fg_muted']}; margin-bottom:2px;">🕐 ساعت ایران</div>
            <div id="ty-clock-header" style="
                font-family:'JetBrains Mono', monospace;
                font-size:22px;
                font-weight:700;
                color:{t['cyan']};
                direction:ltr;
                letter-spacing:1px;
                line-height:1.2;
            ">--:--:--</div>
            <div style="display:flex; align-items:center; justify-content:center; gap:4px; margin-top:2px;">
                <span class="live-dot"></span>
                <span style="font-size:9px; color:{t['fg_muted']};">داده زنده</span>
            </div>
        </div>

        <div class="header-right">
            <div style="text-align:center;">
                <div style="font-size:9px; color:{t['fg_muted']};">📅 تاریخ</div>
                <div style="font-size:13px; color:{t['fg']}; font-weight:700; line-height:1.4;">{jalali}</div>
                <div style="font-size:10px; color:{t['fg_muted']};">{weekday}</div>
                <div style="font-size:9px; color:{t['fg_dim']}; direction:ltr;">{miladi}</div>
            </div>
        </div>
    </div>
    """
    _render(header_html)

    clock_js = """
    <!DOCTYPE html><html><head><style>body { margin: 0; padding: 0; background: transparent; overflow: hidden; }</style></head>
    <body><script>
    (function tick() {
        var now = new Date();
        var utc = now.getTime() + (now.getTimezoneOffset() * 60000);
        var teh = new Date(utc + (3.5 * 3600000));
        var h = String(teh.getHours()).padStart(2, '0');
        var m = String(teh.getMinutes()).padStart(2, '0');
        var s = String(teh.getSeconds()).padStart(2, '0');
        var timeStr = h + ':' + m + ':' + s;
        try {
            var parentClock = window.parent.document.getElementById('ty-clock-header');
            if (parentClock) parentClock.textContent = timeStr;
        } catch(e) {}
        setTimeout(tick, 1000);
    })();
    </script></body></html>
    """
    components.html(clock_js, height=0)


# ═══════════════════════════════════════════════════════════
# پنل تنظیمات
# ═══════════════════════════════════════════════════════════
def render_settings_panel_open_button() -> None:
    t = _t()

    state_key = "settings_open"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    is_open = st.session_state[state_key]

    cols = st.columns([6, 1])
    with cols[1]:
        label = "❌ بستن" if is_open else "⚙️ تنظیمات"
        btn_type = "primary" if is_open else "secondary"
        if st.button(
            label,
            key="settings_toggle_btn",
            use_container_width=True,
            type=btn_type,
        ):
            st.session_state[state_key] = not is_open
            st.rerun()


def render_settings_panel() -> None:
    t = _t()

    if not st.session_state.get("settings_open", False):
        return

    with st.container(border=True):
        st.markdown(
            f'<div style="text-align:center; padding:8px 0 16px 0; direction:rtl;">'
            f'<div style="font-size:16px; font-weight:700; color:{t["primary"]};">⚙️ تنظیمات اپ</div>'
            f'<div style="font-size:11px; color:{t["fg_muted"]}; margin-top:4px;">'
            f"پروفایل · بازار · منبع · بروزرسانی</div></div>",
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            render_settings_section_title("🎯", "پروفایل تحلیل")
            render_profile_selector(st.session_state.risk_profile)

            render_settings_divider()

            render_settings_section_title("📊", "نوع بازار")
            render_market_type_selector(st.session_state.get("market_type", "futures"))

        with col2:
            render_settings_section_title("📡", "منبع دیتا")
            render_source_selector(st.session_state.data_source)

        render_settings_divider()

        render_settings_section_title("🔄", "کنترل بروزرسانی")

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
            "حالت",
            options=refresh_options,
            format_func=lambda x: x[0],
            index=current_idx,
            horizontal=True,
            label_visibility="collapsed",
            key="refresh_toggle_panel",
        )

        if refresh_choice[1] != st.session_state.refresh_seconds:
            st.session_state.refresh_seconds = refresh_choice[1]
            st.session_state.last_update = datetime.now().strftime("%H:%M")
            st.session_state.last_data_refresh = datetime.now().strftime("%H:%M:%S")
            st.rerun()

        btn_cols = st.columns([1, 1, 1])
        with btn_cols[0]:
            if st.button(
                "🔄 بروزرسانی حالا",
                key="panel_refresh",
                use_container_width=True,
                type="primary",
            ):
                st.cache_data.clear()
                st.session_state.last_data_refresh = datetime.now().strftime("%H:%M:%S")
                st.session_state.last_update = datetime.now().strftime("%H:%M")
                st.rerun()
        with btn_cols[1]:
            theme_label = "☀️ روشن" if st.session_state.theme == "dark" else "🌙 تیره"
            if st.button(theme_label, key="panel_theme", use_container_width=True):
                st.session_state.theme = (
                    "light" if st.session_state.theme == "dark" else "dark"
                )
                st.rerun()
        with btn_cols[2]:
            last_refresh = st.session_state.get("last_data_refresh", "")
            if last_refresh:
                render_live_timer(
                    last_refresh,
                    key="panel_refresh_timer",
                    prefix="🕐",
                    font_size=11,
                )


# ═══════════════════════════════════════════════════════════
# تیکر
# ═══════════════════════════════════════════════════════════
def render_top_ticker(prices_data: list, markets_info: list) -> None:
    t = _t()

    def render_price(item):
        name = item.get("name", "—")
        emoji = item.get("emoji", "💰")
        price = item.get("price")
        change = item.get("change_pct")
        unit = item.get("unit", "دلار")

        if price is None:
            price_str = "—"
        elif unit == "دلار":
            price_str = f"${price:,.2f}" if price < 10000 else f"${price:,.0f}"
        else:
            price_str = f"{price:,.0f}"

        change_html = ""
        if change is not None:
            arrow = "▲" if change > 0 else ("▼" if change < 0 else "")
            c = (
                t["green"]
                if change > 0
                else (t["red"] if change < 0 else t["fg_muted"])
            )
            change_html = (
                f'<span style="color:{c}; font-size:10px; '
                f"font-family:'JetBrains Mono'; direction:ltr;\">"
                f"{arrow}{abs(change):.2f}%</span>"
            )

        return (
            f'<div class="ticker-item">'
            f'<span style="font-size:13px;">{emoji}</span>'
            f'<span style="color:{t["fg_muted"]}; font-size:10px;">{name}:</span>'
            f'<span style="font-family:\'JetBrains Mono\'; color:{t["fg"]}; '
            f'font-weight:600; direction:ltr; font-size:11px;">{price_str}</span>'
            f"{change_html}"
            f"</div>"
        )

    def render_market(mk):
        name = mk.get("name", "")
        icon = mk.get("icon", "🌍")
        is_open = mk.get("is_open", False)
        next_event = mk.get("next_event", "")
        color = t["green"] if is_open else t["fg_muted"]

        return (
            f'<div class="ticker-item">'
            f'<span style="font-size:12px;">{icon}</span>'
            f'<span style="color:{color}; font-size:10px; font-weight:600;">{name}</span>'
            f'<span style="color:{t["fg_muted"]}; font-size:9px;">{next_event}</span>'
            f"</div>"
        )

    prices_html = "".join(render_price(p) for p in prices_data)
    markets_html = "".join(render_market(m) for m in markets_info)

    _render(f"""
    <div class="top-ticker">
        <div class="ticker-row-wrapper">
            <div class="ticker-track">{prices_html}</div>
        </div>
        <div class="ticker-row-wrapper" style="border-top:1px solid {t['border']}; margin-top:4px; padding-top:4px;">
            <div class="ticker-track">{markets_html}</div>
        </div>
    </div>
    """)


# ═══════════════════════════════════════════════════════════
# تنظیمات — توابع کمکی
# ═══════════════════════════════════════════════════════════
def render_settings_section_title(icon: str, title: str) -> None:
    t = _t()
    _render(
        f'<div style="font-size:12px; font-weight:700; color:{t["fg"]}; '
        f"margin:8px 0 10px 0; direction:rtl; text-align:right; "
        f'display:flex; align-items:center; gap:6px;">'
        f"<span>{icon}</span><span>{title}</span></div>"
    )


def render_settings_divider() -> None:
    t = _t()
    _render(
        f'<div style="height:1px; background:{t["border"]}; '
        f'margin:16px 0; opacity:0.6;"></div>'
    )


def render_profile_selector(current_profile: str) -> None:
    is_aggressive = current_profile == "aggressive"
    is_conservative = current_profile == "conservative"

    col_a, col_b = st.columns(2)

    with col_a:
        label_a = "🚀 جسورانه" + (" ✓" if is_aggressive else "")
        if st.button(
            label_a,
            key="profile_btn_aggressive",
            use_container_width=True,
            type="primary" if is_aggressive else "secondary",
        ):
            if not is_aggressive:
                st.session_state.risk_profile = "aggressive"
                st.session_state.last_data_refresh = datetime.now().strftime("%H:%M:%S")
                st.rerun()

    with col_b:
        label_b = "🛡 محتاطانه" + (" ✓" if is_conservative else "")
        if st.button(
            label_b,
            key="profile_btn_conservative",
            use_container_width=True,
            type="primary" if is_conservative else "secondary",
        ):
            if not is_conservative:
                st.session_state.risk_profile = "conservative"
                st.session_state.last_data_refresh = datetime.now().strftime("%H:%M:%S")
                st.rerun()


def render_source_selector(current_source: str) -> None:
    t = _t()

    sources = [
        {
            "key": "global",
            "icon": "🌍",
            "label": "جهانی",
            "desc": "yfinance",
            "color": t["cyan"],
        },
        {
            "key": "nobitex",
            "icon": "🟣",
            "label": "نوبیتکس",
            "desc": "کریپتو تتری",
            "color": t["nobitex"],
        },
        {
            "key": "abantether",
            "icon": "🔵",
            "label": "آبان‌تتر",
            "desc": "لحظه‌ای کریپتو",
            "color": t["abantether"],
        },
        {
            "key": "tsetmc",
            "icon": "🇮🇷",
            "label": "بورس تهران",
            "desc": "TSETMC",
            "color": t["tsetmc"],
        },
    ]

    cols = st.columns(2)
    for i, src in enumerate(sources):
        with cols[i % 2]:
            is_active = src["key"] == current_source
            label = f"{src['icon']} {src['label']}"
            if is_active:
                label += " ✓"

            if st.button(
                label,
                key=f"src_btn_{src['key']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active:
                    st.session_state.data_source = src["key"]
                    st.session_state.manual_source_override = True
                    st.session_state.last_data_refresh = datetime.now().strftime(
                        "%H:%M:%S"
                    )
                    st.rerun()

            _render(
                f'<div style="font-size:9px; color:{src["color"]}; '
                f"text-align:center; margin-top:2px; margin-bottom:8px; "
                f'direction:rtl; opacity:0.85;">{src["desc"]}</div>'
            )


def render_source_badge(source: str) -> str:
    info = get_source_info(source)
    return (
        f'<span style="display:inline-flex; align-items:center; gap:4px; '
        f'padding:4px 12px; background:{info["color"]}18; '
        f'border:1px solid {info["color"]}66; border-radius:8px; '
        f'font-size:11px; color:{info["color"]}; font-weight:700;">'
        f'{info["icon"]} {info["full_name"]}</span>'
    )


def render_market_type_selector(current_type: str) -> None:
    market_types = [
        {"key": "spot", "icon": "💵", "label": "اسپات"},
        {"key": "futures", "icon": "📈", "label": "فیوچرز"},
    ]

    cols = st.columns(2)
    for i, mt in enumerate(market_types):
        with cols[i]:
            is_active = mt["key"] == current_type
            label = f"{mt['icon']} {mt['label']}"
            if is_active:
                label += " ✓"

            if st.button(
                label,
                key=f"mt_btn_{mt['key']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active:
                    st.session_state.market_type = mt["key"]
                    st.session_state.last_data_refresh = datetime.now().strftime(
                        "%H:%M:%S"
                    )
                    st.rerun()


# ═══════════════════════════════════════════════════════════
# S/R — با تشخیص تومان/دلار از ticker
# ═══════════════════════════════════════════════════════════
def _build_sr_rows(analysis: dict, max_levels: int = 3, ticker: str = "") -> tuple:
    t = _t()
    price = analysis.get("price", 0)
    pivots = analysis.get("pivots") or {}
    swings = analysis.get("swings") or {}

    if not price or price <= 0:
        empty = (
            f'<div style="text-align:center; padding:8px; '
            f'color:{t["fg_dim"]}; font-size:10px;">داده کافی نیست</div>'
        )
        return empty, empty, empty

    # ═══ تشخیص تومانی از روی ticker ═══
    is_iranian = _is_iranian_ticker(ticker)

    resistances = []
    supports = []

    for key, label in [("r3", "R3"), ("r2", "R2"), ("r1", "R1")]:
        v = pivots.get(key, 0)
        if v and v > price:
            resistances.append({"pivot_label": label, "price": v, "source": "pivot"})

    for key, label in [("s3", "S3"), ("s2", "S2"), ("s1", "S1")]:
        v = pivots.get(key, 0)
        if v and v < price:
            supports.append({"pivot_label": label, "price": v, "source": "pivot"})

    if swings.get("swing_highs"):
        for _, p in swings["swing_highs"]:
            if p > price:
                resistances.append({"pivot_label": "SW", "price": p, "source": "swing"})

    if swings.get("swing_lows"):
        for _, p in swings["swing_lows"]:
            if p < price:
                supports.append({"pivot_label": "SW", "price": p, "source": "swing"})

    def dedupe(levels):
        result = []
        for lvl in levels:
            if not any(abs(lvl["price"] - r["price"]) / price < 0.001 for r in result):
                result.append(lvl)
        return result

    resistances = dedupe(resistances)
    supports = dedupe(supports)

    resistances.sort(key=lambda x: -x["price"])
    supports.sort(key=lambda x: -x["price"])

    resistances = resistances[:max_levels]
    supports = supports[:max_levels]

    # ═══ فرمت قیمت ═══
    if is_iranian:
        price_str = f"{price:,.0f} تومان"
    else:
        price_str = f"${price:,.2f}" if price < 10000 else f"${price:,.0f}"

    price_row = (
        f'<div style="display:flex; justify-content:space-between; align-items:center; '
        f"padding:10px 12px; margin:8px 0; "
        f'background:linear-gradient(90deg, {t["primary_glow"]}, transparent); '
        f'border:2px solid {t["primary"]}; border-radius:10px; direction:rtl;">'
        f'<div style="display:flex; align-items:center; gap:6px;">'
        f'<span style="font-size:14px;">💎</span>'
        f'<span style="font-size:12px; color:{t["fg"]}; font-weight:700;">قیمت فعلی</span>'
        f"</div>"
        f'<span style="font-size:14px; color:{t["primary"]}; '
        f"font-family:'JetBrains Mono'; font-weight:700; direction:rtl;\">{price_str}</span>"
        f"</div>"
    )

    def level_row(level, order_num, is_resistance):
        lvl_price = level["price"]
        dist_pct = (lvl_price - price) / price * 100
        abs_dist = abs(dist_pct)

        base_color = t["red"] if is_resistance else t["green"]

        if abs_dist < 0.5:
            opacity = 1.0
            border_width = 4
            bg_tint = (
                f"rgba({248 if is_resistance else 63},"
                f"{81 if is_resistance else 185},"
                f"{73 if is_resistance else 80},0.12)"
            )
            weight = "700"
        elif abs_dist < 1.5:
            opacity = 0.85
            border_width = 3
            bg_tint = t["bg_mid"]
            weight = "600"
        else:
            opacity = 0.65
            border_width = 2
            bg_tint = t["bg_mid"]
            weight = "500"

        prefix = "R" if is_resistance else "S"
        display_label = f"{prefix}-{order_num}"

        if level["source"] == "pivot":
            src_icon = "📌"
            src_text = "P"
            src_color = t["cyan"]
        else:
            src_icon = "🔄"
            src_text = "W"
            src_color = t["purple"]

        # ═══ فرمت قیمت level ═══
        if is_iranian:
            price_str = f"{lvl_price:,.0f} تومان"
        else:
            price_str = (
                f"${lvl_price:,.2f}" if lvl_price < 10000 else f"${lvl_price:,.0f}"
            )
        sign = "▲" if dist_pct > 0 else "▼"

        return (
            f'<div style="display:flex; justify-content:space-between; align-items:center; '
            f"padding:9px 12px; margin:4px 0; background:{bg_tint}; border-radius:8px; "
            f'border-right:{border_width}px solid {base_color}; opacity:{opacity}; direction:rtl;">'
            f'<div style="display:flex; align-items:center; gap:6px;">'
            f'<span style="font-size:10px;">{src_icon}</span>'
            f'<span style="font-size:11px; color:{base_color}; '
            f"font-family:'JetBrains Mono'; font-weight:700; min-width:34px;\">{display_label}</span>"
            f'<span style="font-size:9px; color:{src_color}; '
            f"font-family:'JetBrains Mono'; opacity:0.8; min-width:14px;\">{src_text}</span>"
            f'<span style="font-size:12px; color:{base_color}; '
            f"font-family:'JetBrains Mono'; font-weight:{weight};\">{price_str}</span>"
            f"</div>"
            f'<span style="font-size:10px; color:{base_color}; direction:ltr; '
            f"font-family:'JetBrains Mono';\">{sign} {abs_dist:.2f}%</span>"
            f"</div>"
        )

    res_rows = ""
    if resistances:
        total = len(resistances)
        for i, lvl in enumerate(resistances):
            order_num = total - i
            res_rows += level_row(lvl, order_num, True)
    else:
        res_rows = (
            f'<div style="text-align:center; padding:8px; '
            f'color:{t["fg_dim"]}; font-size:10px;">مقاومتی بالای قیمت نیست</div>'
        )

    sup_rows = ""
    if supports:
        for i, lvl in enumerate(supports):
            order_num = i + 1
            sup_rows += level_row(lvl, order_num, False)
    else:
        sup_rows = (
            f'<div style="text-align:center; padding:8px; '
            f'color:{t["fg_dim"]}; font-size:10px;">حمایتی زیر قیمت نیست</div>'
        )

    return res_rows, price_row, sup_rows


# ═══════════════════════════════════════════════════════════
# رژیم + رأی‌گیری
# ═══════════════════════════════════════════════════════════
def _build_regime_badge(analysis: dict) -> str:
    t = _t()
    regime = analysis.get("regime", "range")
    adx = analysis.get("adx", 0)
    risk_profile = analysis.get("risk_profile", "aggressive")

    regime_icon, regime_fa = Regime.display_fa(regime)

    if regime == "trend":
        regime_color = t["green"]
    elif regime == "transitional":
        regime_color = t["yellow"]
    else:
        regime_color = t["cyan"]

    profile_fa = "🚀 جسورانه" if risk_profile == "aggressive" else "🛡 محتاطانه"
    profile_color = t["orange"] if risk_profile == "aggressive" else t["green"]

    return f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding:10px 14px; background:{t['bg_mid']}; border-radius:10px; direction:rtl; gap:10px; flex-wrap:wrap;">
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:16px;">{regime_icon}</span>
            <div style="text-align:right;">
                <div style="font-size:11px; color:{t['fg_muted']};">حالت بازار</div>
                <div style="font-size:13px; color:{regime_color}; font-weight:700;">{regime_fa} · ADX={adx:.0f}</div>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:11px; color:{t['fg_muted']};">پروفایل:</span>
            <span style="font-size:12px; color:{profile_color}; font-weight:700; padding:4px 10px; background:{profile_color}15; border:1px solid {profile_color}55; border-radius:8px;">{profile_fa}</span>
        </div>
    </div>
    """


def _build_voting_bar(analysis: dict) -> str:
    t = _t()
    groups = analysis.get("groups", {})
    votes_long = analysis.get("votes_long", 0)
    votes_short = analysis.get("votes_short", 0)
    votes_neutral = analysis.get("votes_neutral", 0)
    multi_tf_info = analysis.get("multi_tf_info", "")
    multi_tf_ok = analysis.get("multi_tf_ok", True)
    consensus = analysis.get("consensus", "neutral")
    divergence = analysis.get("divergence", {})

    if not groups:
        return ""

    group_chips = ""
    for g_key in AnalysisGroup.all():
        if g_key not in groups:
            continue
        g_icon, g_name, _ = AnalysisGroup.display_fa(g_key)
        g_vote = groups[g_key].get("vote", 0)
        g_strength = groups[g_key].get("strength_fa", "")

        if g_vote > 0:
            chip_color = t["green"]
            chip_icon = "🟢"
        elif g_vote < 0:
            chip_color = t["red"]
            chip_icon = "🔴"
        else:
            chip_color = t["fg_muted"]
            chip_icon = "⚪"

        strength_html = ""
        if g_strength and g_strength != "بی‌جهت":
            strength_html = (
                f'<span style="color:{chip_color}; font-size:9px; opacity:0.75;">'
                f"· {g_strength}</span>"
            )

        group_chips += (
            f'<div style="display:inline-flex; align-items:center; gap:5px; '
            f"padding:5px 10px; margin:3px; "
            f"background:{chip_color}15; "
            f"border:1px solid {chip_color}55; "
            f'border-radius:8px; font-size:10px; direction:rtl;">'
            f"<span>{chip_icon}</span>"
            f'<span style="color:{chip_color}; font-weight:600;">{g_name}</span>'
            f"{strength_html}"
            f"</div>"
        )

    consensus_text = Consensus.display_fa(consensus)
    consensus_color = {
        "strong": t["green"],
        "normal": t["green"],
        "weak": t["yellow"],
        "neutral": t["fg_muted"],
    }.get(consensus, t["fg_muted"])

    multi_tf_html = ""
    if multi_tf_info and multi_tf_info != "بدون بررسی":
        multi_tf_color = t["green"] if multi_tf_ok else t["yellow"]
        multi_tf_icon = "✅" if multi_tf_ok else "⚠️"
        multi_tf_html = (
            f'<div style="display:flex; align-items:center; gap:6px; font-size:10px; '
            f"color:{multi_tf_color}; background:{multi_tf_color}10; padding:6px 10px; "
            f"border-radius:8px; border-right:3px solid {multi_tf_color}; direction:rtl; "
            f'margin-top:8px;">{multi_tf_icon} {multi_tf_info}</div>'
        )

    divergence_html = ""
    if divergence.get("has_divergence"):
        divergence_html = (
            f'<div style="display:flex; align-items:center; gap:6px; font-size:10px; '
            f'color:{t["red"]}; background:rgba(239,68,68,0.1); padding:8px 10px; '
            f'border-radius:8px; border-right:3px solid {t["red"]}; direction:rtl; '
            f'margin-top:8px; font-weight:600; line-height:1.6;">'
            f'{divergence.get("reason", "")}</div>'
        )

    return f"""
    <div style="margin-top:14px; padding-top:14px; border-top:1px solid {t['border']};">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:6px;">
            <div style="font-size:11px; color:{t['fg_muted']}; font-weight:600;">🗳 رأی‌گیری ۵ گروهی</div>
            <div style="font-size:10px;">
                <span style="color:{consensus_color}; font-weight:600;">{consensus_text}</span>
            </div>
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:2px; margin-bottom:10px;">
            {group_chips}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 10px; background:{t['bg_mid']}; border-radius:8px; margin-bottom:6px;">
            <div style="display:flex; align-items:center; gap:10px; font-size:11px; direction:rtl;">
                <span style="color:{t['green']}; font-weight:600;">{votes_long} صعودی ↑</span>
                <span style="color:{t['fg_muted']};">{votes_neutral} خنثی ●</span>
                <span style="color:{t['red']}; font-weight:600;">{votes_short} نزولی ↓</span>
            </div>
        </div>
        {multi_tf_html}
        {divergence_html}
    </div>
    """


# ═══════════════════════════════════════════════════════════
# جعبه تله‌ها
# ═══════════════════════════════════════════════════════════
def _render_traps_box(analysis: dict) -> str:
    t = _t()

    traps = analysis.get("traps", {})
    if not traps:
        return ""

    active_traps = {k: v for k, v in traps.items() if v.get("active")}
    if not active_traps:
        return ""

    sorted_traps = sorted(
        active_traps.items(),
        key=lambda x: -x[1].get("severity", 0),
    )

    trap_names = {
        "bull_trap": ("🚨", "تله صعودی"),
        "bear_trap": ("🚨", "تله نزولی"),
        "fake_breakout": ("⚠️", "شکست جعلی"),
        "exhaustion": ("😮‍💨", "خستگی روند"),
    }

    rows = ""
    for trap_key, trap_info in sorted_traps:
        icon, name = trap_names.get(trap_key, ("⚠️", trap_key))
        severity = trap_info.get("severity", 5)
        reason = trap_info.get("reason", "")

        if severity >= 8:
            bg = f"{t['red']}20"
            border = t["red"]
            text_color = t["red"]
        elif severity >= 6:
            bg = f"{t['orange']}20"
            border = t["orange"]
            text_color = t["orange"]
        else:
            bg = f"{t['yellow']}20"
            border = t["yellow"]
            text_color = t["yellow"]

        rows += (
            f'<div style="background:{bg}; '
            f"border-right:3px solid {border}; "
            f"border-radius:8px; padding:10px 12px; margin-bottom:6px; "
            f'direction:rtl; text-align:right;">'
            f'<div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">'
            f'<span style="font-size:14px;">{icon}</span>'
            f'<span style="color:{text_color}; font-weight:700; font-size:12px;">{name}</span>'
            f'<span style="font-size:9px; color:{text_color}; opacity:0.7;">'
            f"(شدت {severity}/10)</span>"
            f"</div>"
            f'<div style="font-size:10px; color:{t["fg"]}; line-height:1.7;">'
            f"{reason}</div>"
            f"</div>"
        )

    return (
        f'<div style="margin-top:14px; padding-top:12px; '
        f'border-top:1px dashed {t["red"]}55;">'
        f'<div style="font-size:11px; color:{t["red"]}; font-weight:700; '
        f'margin-bottom:8px;">🚨 هشدار تله‌های معاملاتی</div>'
        f"{rows}"
        f"</div>"
    )


# ═══════════════════════════════════════════════════════════
# جعبه سناریوها
# ═══════════════════════════════════════════════════════════
def _render_scenarios_box(analysis: dict) -> str:
    t = _t()

    scenarios = analysis.get("scenarios", [])
    if not scenarios:
        return ""

    rows = ""
    for sc in scenarios:
        color = sc.get("color", "yellow")
        color_hex = {
            "green": t["green"],
            "red": t["red"],
            "yellow": t["yellow"],
        }.get(color, t["yellow"])

        icon = sc.get("icon", "•")
        condition = sc.get("condition", "")
        action = sc.get("action", "")
        prob = sc.get("probability", 0.5)
        prob_pct = int(prob * 100)

        rows += (
            f'<div style="background:{t["bg_card"]}; '
            f'border:1px solid {t["border"]}; '
            f"border-right:3px solid {color_hex}; "
            f"border-radius:8px; padding:10px 12px; margin-bottom:6px; "
            f'direction:rtl; text-align:right;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; '
            f'margin-bottom:5px;">'
            f'<span style="font-size:11px; color:{color_hex}; font-weight:700;">'
            f"{icon} {condition}</span>"
            f'<span style="font-size:9px; color:{t["fg_muted"]}; '
            f'background:{color_hex}15; padding:2px 6px; border-radius:4px;">'
            f"{prob_pct}%</span>"
            f"</div>"
            f'<div style="font-size:10px; color:{t["fg"]}; line-height:1.6;">'
            f"← {action}</div>"
            f"</div>"
        )

    return (
        f'<div style="margin-top:14px; padding-top:12px; '
        f'border-top:1px solid {t["border"]};">'
        f'<div style="font-size:11px; color:{t["primary"]}; font-weight:700; '
        f'margin-bottom:8px;">🎯 سناریوهای احتمالی</div>'
        f"{rows}"
        f"</div>"
    )


# ═══════════════════════════════════════════════════════════
# کارت سیگنال
# ═══════════════════════════════════════════════════════════
def render_unified_signal_card(
    analysis: dict,
    sym_name: str,
    tf_name: str,
    ticker: str = "",
    last_update: str = "",
    source: str = "global",
    market_type: str = "spot",
    live_price: float = None,
    show_scenarios: bool = True,
) -> None:
    t = _t()

    if not analysis:
        _render(
            f'<div style="text-align:center; padding:30px; '
            f'background:{t["bg_card"]}; border:1px solid {t["border"]}; '
            f'border-radius:12px; color:{t["fg_muted"]}; direction:rtl;">'
            f"در حال محاسبه تحلیل...</div>"
        )
        return

    signal = analysis.get("signal", "خنثی")
    price = analysis.get("price", 0)
    confidence = analysis.get("confidence", 0)
    sl_tp = analysis.get("sl_tp")
    rr = analysis.get("rr")

    # ═══ تشخیص تومانی ═══
    is_iranian = _is_iranian_ticker(ticker) or analysis.get("is_iranian", False)

    display_price = live_price if live_price and live_price > 0 else price

    if SigEnum.is_long(signal):
        icon = "🟢"
        signal_color = t["green"]
        signal_border = t["green"]
    elif SigEnum.is_short(signal):
        icon = "🔴"
        signal_color = t["red"]
        signal_border = t["red"]
    else:
        icon = "⚪"
        signal_color = t["fg_muted"]
        signal_border = t["border_light"]

    def _fmt_price(p):
        if not p or p <= 0:
            return "—"
        if is_iranian:
            return f"{p:,.0f} تومان"
        return f"${p:,.2f}" if p < 10000 else f"${p:,.0f}"

    price_str = _fmt_price(display_price)

    if sl_tp:
        sl_str = _fmt_price(sl_tp.get("sl"))
        tp_str = _fmt_price(sl_tp.get("tp"))
        rr_str = f"{rr:.1f}" if rr else "—"
        sl_color = t["red"]
        tp_color = t["green"]
        sl_tp_note = ""
    else:
        sl_str = "—"
        tp_str = "—"
        rr_str = "—"
        sl_color = t["fg_dim"]
        tp_color = t["fg_dim"]

        neutral_explain = analysis.get("neutral_explain", {})
        ne_short = neutral_explain.get("short") or analysis.get("explanation", "")
        ne_long = neutral_explain.get("long", "")
        ne_hint = neutral_explain.get("hint")

        hint_html = ""
        if ne_hint:
            hint_html = (
                f'<div style="margin-top:10px; padding:8px 10px; '
                f'background:{t["cyan"]}15; border-right:3px solid {t["cyan"]}; '
                f'border-radius:6px; font-size:10px; color:{t["cyan"]}; '
                f'direction:rtl; text-align:right; line-height:1.7; font-weight:600;">'
                f"{ne_hint}</div>"
            )

        long_html = ""
        if ne_long:
            long_html = (
                f'<div style="margin-top:6px; font-size:10px; color:{t["fg_muted"]}; '
                f'direction:rtl; text-align:right; line-height:1.8;">'
                f"{ne_long}</div>"
            )

        sl_tp_note = (
            f'<div style="font-size:11px; color:{t["fg_muted"]}; margin-top:10px; '
            f'padding:14px; background:{t["bg_mid"]}; '
            f'border-radius:8px; direction:rtl; line-height:1.9;">'
            f'<div style="font-weight:700; color:{t["fg"]}; margin-bottom:6px; '
            f'font-size:12px;">⚪ {ne_short}</div>'
            f"{long_html}"
            f"{hint_html}"
            f"</div>"
        )

    res_rows, price_row, sup_rows = _build_sr_rows(
        analysis, max_levels=3, ticker=ticker
    )
    voting_bar = _build_voting_bar(analysis)
    regime_badge = _build_regime_badge(analysis)

    badge_bg = f"{signal_color}22" if signal != "خنثی" else "rgba(139,148,158,0.15)"

    weak_suffix = ""
    signal_main = signal
    if " ضعیف" in signal:
        signal_main = signal.replace(" ضعیف", "")
        weak_suffix = f'<div style="font-size:9px; color:{t["fg_muted"]}; margin-top:2px;">(ضعیف)</div>'

    ticker_html = (
        f'<span style="font-size:11px; color:{t["fg_muted"]}; margin-right:6px;">({ticker})</span>'
        if ticker
        else ""
    )

    update_html = ""
    if last_update:
        update_html = (
            f'<span style="font-size:10px; color:{t["fg_muted"]};">🕐 </span>'
            f"<span style=\"font-family:'JetBrains Mono'; font-size:10px; "
            f'color:{t["cyan"]}; font-weight:600;">{last_update}</span>'
        )

    live_indicator = ""
    if live_price and live_price > 0:
        live_indicator = (
            f'<span class="live-pulse-dot" style="margin-right:6px;"></span>'
        )

    source_badge_html = render_source_badge(source)

    if market_type == "futures":
        leverage = analysis.get("leverage") or 3
        market_badge = (
            f'<span style="display:inline-flex; align-items:center; gap:5px; '
            f'padding:5px 14px; background:{t["orange"]}25; '
            f'border:1.5px solid {t["orange"]}88; border-radius:9px; '
            f'font-size:11px; color:{t["orange"]}; font-weight:700;">'
            f"📈 فیوچرز · {leverage}x</span>"
        )
    else:
        market_badge = (
            f'<span style="display:inline-flex; align-items:center; gap:5px; '
            f'padding:5px 14px; background:{t["green"]}25; '
            f'border:1.5px solid {t["green"]}88; border-radius:9px; '
            f'font-size:11px; color:{t["green"]}; font-weight:700;">'
            f"💵 اسپات</span>"
        )

    action_fa = analysis.get("action_fa", "")

    traps_html = _render_traps_box(analysis)
    scenarios_html = _render_scenarios_box(analysis) if show_scenarios else ""

    html = f"""
    <style>
        .ty-unified-card {{
            background:{t['bg_card']};
            border:2px solid {signal_border};
            border-radius:14px;
            padding:16px 20px;
            margin-bottom:16px;
            box-shadow:0 4px 20px {signal_color}22, 0 2px 8px rgba(0,0,0,0.2);
            direction:rtl;
            text-align:right;
        }}
        .ty-unified-grid {{
            display:grid;
            grid-template-columns:1.2fr 1fr;
            gap:16px;
            align-items:start;
            direction:rtl;
        }}
        .ty-sr-box {{
            background:{t['bg_mid']};
            border-radius:12px;
            padding:14px;
            border:1px solid {t['border']};
            direction:rtl;
            text-align:right;
        }}
        .ty-signal-box {{
            background:{t['bg_mid']};
            border-radius:12px;
            padding:14px;
            border:1px solid {t['border']};
            direction:rtl;
            text-align:right;
        }}

        @media (max-width: 768px) {{
            .ty-unified-card {{ padding:12px 14px; }}
            .ty-unified-grid {{
                grid-template-columns:1fr !important;
                gap:12px;
            }}
            .ty-sr-box, .ty-signal-box {{ padding:12px; }}
            .ty-sr-header-sub {{ display:none !important; }}
        }}
    </style>

    <div class="ty-unified-card">
        <div style="
            display:flex; justify-content:space-between; align-items:center;
            padding-bottom:10px; margin-bottom:12px;
            border-bottom:1px solid {t['border']};
            flex-wrap:wrap; gap:8px;
            direction:rtl;
        ">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:24px; filter:drop-shadow(0 0 8px {signal_color});">{icon}</span>
                <div style="text-align:right;">
                    <div style="font-size:15px; font-weight:700; color:{t['fg']}; display:flex; align-items:center; gap:6px;">
                        {live_indicator}
                        <span>تحلیل {sym_name}</span>
                        <span style="font-size:10px; color:{t['fg_muted']};">{ticker_html}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px; margin-top:3px; font-size:10px; color:{t['fg_muted']};">
                        <span>⏱ {tf_name}</span>
                        <span>·</span>
                        {update_html}
                    </div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:18px;">
                <div style="text-align:center;">
                    <div style="font-size:9px; color:{t['fg_muted']}; margin-bottom:2px;">قیمت</div>
                    <div style="font-family:'JetBrains Mono'; font-size:16px; color:{t['primary']}; font-weight:700; direction:rtl;">{price_str}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:9px; color:{t['fg_muted']}; margin-bottom:2px;">اطمینان</div>
                    <div style="font-family:'JetBrains Mono'; font-size:16px; color:{t['primary']}; font-weight:700;">{confidence}%</div>
                </div>
            </div>
        </div>

        <div style="display:flex; justify-content:flex-start; align-items:center; gap:8px; margin-bottom:12px; flex-wrap:wrap;">
            {source_badge_html}
            {market_badge}
        </div>

        <div class="ty-unified-grid">
            <div class="ty-signal-box">
                {regime_badge}

                <div style="
                    display:flex; justify-content:space-between; align-items:center;
                    padding:14px 18px; margin-bottom:14px;
                    background:{badge_bg};
                    border:2px solid {signal_color};
                    border-radius:12px;
                ">
                    <div style="text-align:right;">
                        <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:3px;">سیگنال</div>
                        <div style="font-family:'JetBrains Mono'; font-size:22px; color:{signal_color}; font-weight:700; letter-spacing:1px;">
                            {signal_main}
                        </div>
                        {weak_suffix}
                    </div>
                    <div style="text-align:left;">
                        <div style="font-size:12px; color:{signal_color}; font-weight:600;">{action_fa}</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px; direction:rtl;">
                    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:10px; padding:12px; text-align:center; border-right:3px solid {t['primary']};">
                        <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:5px;">💰 ورود</div>
                        <div style="font-family:'JetBrains Mono'; font-size:13px; color:{t['fg']}; font-weight:700; direction:rtl;">{price_str}</div>
                    </div>
                    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:10px; padding:12px; text-align:center; border-right:3px solid {sl_color};">
                        <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:5px;">🛑 حد ضرر</div>
                        <div style="font-family:'JetBrains Mono'; font-size:13px; color:{sl_color}; font-weight:700; direction:rtl;">{sl_str}</div>
                    </div>
                    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:10px; padding:12px; text-align:center; border-right:3px solid {tp_color};">
                        <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:5px;">🎯 هدف</div>
                        <div style="font-family:'JetBrains Mono'; font-size:13px; color:{tp_color}; font-weight:700; direction:rtl;">{tp_str}</div>
                    </div>
                    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:10px; padding:12px; text-align:center; border-right:3px solid {t['cyan']};">
                        <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:5px;">⚖️ سود/ضرر</div>
                        <div style="font-family:'JetBrains Mono'; font-size:13px; color:{t['cyan']}; font-weight:700;">{rr_str}</div>
                    </div>
                </div>

                {sl_tp_note}
                {voting_bar}
                {traps_html}
                {scenarios_html}
            </div>

            <div class="ty-sr-box">
                <div style="
                    display:flex; justify-content:space-between; align-items:center;
                    margin-bottom:12px; padding-bottom:10px;
                    border-bottom:1px solid {t['border']};
                ">
                    <div style="font-size:13px; font-weight:700; color:{t['primary']};">🎯 سطوح حمایت و مقاومت</div>
                    <div class="ty-sr-header-sub" style="font-size:10px; color:{t['fg_muted']};">📌 Pivot · 🔄 Swing</div>
                </div>
                <div>
                    <div style="font-size:10px; color:{t['red']}; margin-bottom:6px; font-weight:700;">🔴 مقاومت‌ها</div>
                    {res_rows}
                    {price_row}
                    <div style="font-size:10px; color:{t['green']}; margin-top:8px; margin-bottom:6px; font-weight:700;">🟢 حمایت‌ها</div>
                    {sup_rows}
                </div>
            </div>
        </div>
    </div>
    """
    _render(html)


# ═══════════════════════════════════════════════════════════
# جدول TF
# ═══════════════════════════════════════════════════════════
def render_tf_table(
    tfs_data: dict,
    sym_name: str,
    current_price: float,
    ticker: str = "",
) -> str | None:
    t = _t()
    if not tfs_data:
        return None

    from core.contracts import TF_NAMES, TF_SHORT

    is_iranian = _is_iranian_ticker(ticker)

    tf_order = TF_NAMES
    if is_iranian:
        price_str = f"{current_price:,.0f} تومان"
    else:
        price_str = (
            f"${current_price:,.2f}"
            if current_price < 10000
            else f"${current_price:,.0f}"
        )

    _render(
        f'<div style="font-size:13px; font-weight:700; color:{t["primary"]}; '
        f"margin:0 0 10px 0; padding-right:10px; border-right:3px solid {t['primary']}; "
        f'direction:rtl; text-align:right;">📊 جدول تحلیل — قیمت فعلی: {price_str}</div>'
    )

    rows = ""
    cards = ""

    for tf in tf_order:
        if tf not in tfs_data:
            continue
        a = tfs_data[tf]
        signal = a.get("signal", "—")
        confidence = a.get("confidence", 0)
        close_series = a.get("close_series", [])
        regime = a.get("regime", "range")

        if SigEnum.is_long(signal):
            sig_text = "LONG"
            sig_color = t["green"]
            trend = "up"
        elif SigEnum.is_short(signal):
            sig_text = "SHORT"
            sig_color = t["red"]
            trend = "down"
        else:
            sig_text = "خنثی"
            sig_color = t["fg_muted"]
            trend = "flat"

        regime_fa = {
            "trend": "جهت‌دار",
            "transitional": "در حال‌تغییر",
            "range": "بی‌جهت",
        }.get(regime, regime)

        # توضیح فارسی
        traps = a.get("traps", {})
        active_traps = [k for k, v in traps.items() if v.get("active")]

        if active_traps:
            trap_names_fa = {
                "bull_trap": "تله صعودی",
                "bear_trap": "تله نزولی",
                "fake_breakout": "شکست جعلی",
                "exhaustion": "خستگی روند",
            }
            trap_fa = trap_names_fa.get(active_traps[0], "هشدار")
            expl_main = f"🚨 {trap_fa}"
            expl_sub = "احتمال تله — احتیاط"
        elif SigEnum.is_long(signal) and confidence >= 70:
            expl_main = "فرصت خرید قوی"
            expl_sub = "احتمال صعود بالاست"
        elif SigEnum.is_long(signal) and confidence >= 50:
            expl_main = "فرصت خرید"
            expl_sub = "با حد ضرر وارد شو"
        elif SigEnum.is_long(signal):
            expl_main = "نشانه‌های صعود ضعیف"
            expl_sub = "با احتیاط و حجم کم"
        elif SigEnum.is_short(signal) and confidence >= 70:
            expl_main = "فرصت فروش قوی"
            expl_sub = "احتمال نزول بالاست"
        elif SigEnum.is_short(signal) and confidence >= 50:
            expl_main = "فرصت فروش"
            expl_sub = "با حد ضرر وارد شو"
        elif SigEnum.is_short(signal):
            expl_main = "نشانه‌های نزول ضعیف"
            expl_sub = "با احتیاط و حجم کم"
        else:
            if regime == "range":
                expl_main = "بازار رنج"
                expl_sub = "بدون روند — صبر کن"
            elif regime == "trend":
                expl_main = "بدون سیگنال معتبر"
                expl_sub = "روند هست ولی گروه‌ها هم‌جهت نیستن"
            else:
                expl_main = "بدون سیگنال"
                expl_sub = "منتظر تأیید باش"

        spark_color = (
            t["green"]
            if SigEnum.is_long(signal)
            else (t["red"] if SigEnum.is_short(signal) else t["fg_muted"])
        )
        spark = sparkline_svg(close_series, spark_color, 65, 24, trend)

        rows += (
            f"<tr>"
            f'<td style="font-weight:700; color:{t["primary"]}; text-align:right; '
            f"font-family:'JetBrains Mono'; font-size:12px;\">{TF_SHORT.get(tf, tf)}</td>"
            f'<td style="text-align:center;">{spark}</td>'
            f'<td style="text-align:center; color:{sig_color}; font-weight:700; '
            f"font-size:12px; font-family:'JetBrains Mono';\">{sig_text}</td>"
            f'<td style="font-size:11px; color:{t["fg"]}; text-align:right; line-height:1.6;">'
            f'{expl_main}<br><span style="font-size:9px; color:{t["fg_muted"]};">{expl_sub} · حالت {regime_fa}</span></td>'
            f"<td style=\"text-align:center; font-family:'JetBrains Mono'; "
            f'color:{t["primary"]}; font-size:12px; font-weight:600;">{confidence}%</td>'
            f"</tr>"
        )

        cards += (
            f'<div class="ty-tf-card">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
            f'<div style="font-size:14px; font-weight:700; color:{t["primary"]}; '
            f"font-family:'JetBrains Mono';\">{TF_SHORT.get(tf, tf)}</div>"
            f'<div style="font-size:12px; color:{sig_color}; font-weight:700; '
            f"font-family:'JetBrains Mono';\">{sig_text}</div>"
            f"</div>"
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
            f"<div>{spark}</div>"
            f"<div style=\"font-family:'JetBrains Mono'; font-size:13px; "
            f'color:{t["primary"]}; font-weight:600;">{confidence}%</div>'
            f"</div>"
            f'<div style="font-size:11px; color:{t["fg"]}; text-align:right; margin-bottom:4px;">{expl_main}</div>'
            f'<div style="font-size:9px; color:{t["fg_muted"]}; text-align:right;">'
            f"{expl_sub} · حالت {regime_fa}</div>"
            f"</div>"
        )

    _render(f"""
    <style>
        .ty-tf-desktop {{ display: block; }}
        .ty-tf-mobile {{ display: none; }}
        .ty-tf-card {{
            background:{t['bg_card']};
            border:1px solid {t['border']};
            border-right:3px solid {t['primary']};
            border-radius:10px;
            padding:12px 14px;
            margin-bottom:8px;
            direction:rtl;
            text-align:right;
        }}
        @media (max-width: 768px) {{
            .ty-tf-desktop {{ display: none !important; }}
            .ty-tf-mobile {{ display: block !important; }}
        }}
    </style>
    <div class="ty-tf-desktop">
        <table class="tf-table" style="direction:rtl;">
            <thead>
                <tr>
                    <th style="width:60px; text-align:right;">تایم</th>
                    <th style="width:90px; text-align:center;">نمودار</th>
                    <th style="width:80px; text-align:center;">سیگنال</th>
                    <th style="text-align:right;">تحلیل</th>
                    <th style="width:80px; text-align:center;">اطمینان</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    <div class="ty-tf-mobile">{cards}</div>
    """)

    return None


# ═══════════════════════════════════════════════════════════
# تحلیل عمیق
# ═══════════════════════════════════════════════════════════
def render_deep_analysis(
    analysis_text: str, analysis_data: dict, sym_name: str = ""
) -> None:
    t = _t()

    signal = analysis_data.get("signal", "خنثی") if analysis_data else "خنثی"
    confidence = analysis_data.get("confidence", 0) if analysis_data else 0

    if SigEnum.is_long(signal):
        final_decision = "🟢 پیشنهاد خرید"
        final_color = t["green"]
        decision_line = "با احتیاط وارد شو و حتماً حد ضرر بذار"
    elif SigEnum.is_short(signal):
        final_decision = "🔴 پیشنهاد فروش"
        final_color = t["red"]
        decision_line = "محتاط باش، نوسان بالاست"
    else:
        final_decision = "⚪ صبر کن"
        final_color = t["fg_muted"]
        decision_line = "بدون سیگنال واضح — منتظر بمان"

    if SigEnum.is_long(signal) and confidence > 70:
        low_risk_color = t["green"]
        low_risk_text = "✅ می‌تونی با احتیاط وارد شی — ۱٪ سرمایه"
    elif SigEnum.is_long(signal) and confidence > 50:
        low_risk_color = t["yellow"]
        low_risk_text = "⚠️ صبر کن تا سیگنال قوی‌تر بشه"
    elif SigEnum.is_short(signal) and confidence > 70:
        low_risk_color = t["red"]
        low_risk_text = "⚠️ فروش پر‌ریسکه — بهتره صبر کنی"
    elif SigEnum.is_short(signal):
        low_risk_color = t["red"]
        low_risk_text = "❌ فعلاً وارد نشو"
    else:
        low_risk_color = t["fg_muted"]
        low_risk_text = "⏸ صبر کن — بازار بی‌جهته"

    if SigEnum.is_long(signal):
        high_risk_color = t["green"]
        high_risk_text = "🚀 فرصت خرید — با حد ضرر و ۳-۵٪ سرمایه"
    elif SigEnum.is_short(signal):
        high_risk_color = t["red"]
        high_risk_text = "🎯 فرصت فروش — با حد ضرر و ۳-۵٪ سرمایه"
    else:
        high_risk_color = t["yellow"]
        high_risk_text = "⏳ می‌تونی نوسان‌گیری کنی ولی محتاط باش"

    text_html = analysis_text.replace("\n", "<br>")
    text_html = text_html.replace(
        "◈", f'<span style="color:{t["primary"]}; font-weight:700;">◈</span>'
    )
    text_html = text_html.replace(
        "─" * 30, f'<span style="color:{t["border"]};">{"─" * 30}</span>'
    )

    title_html = f"تحلیل عمیق {sym_name}" if sym_name else "تحلیل عمیق"

    _render(f"""
    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:18px; direction:rtl; text-align:right; box-shadow:0 2px 8px rgba(0,0,0,0.2);">
        <div style="background:{t['bg_mid']}; border-right:4px solid {final_color}; border-radius:10px; padding:14px 18px; margin-bottom:16px; text-align:right;">
            <div style="font-size:15px; font-weight:700; color:{final_color}; margin-bottom:5px;">{final_decision}</div>
            <div style="font-size:11px; color:{t['fg']};">{decision_line}</div>
        </div>
        <div style="font-size:14px; font-weight:700; color:{t['primary']}; margin-bottom:14px; padding-right:10px; border-right:3px solid {t['primary']};">
            📝 {title_html}
        </div>
        <div style="font-size:12px; line-height:2.2; color:{t['fg']}; direction:rtl; text-align:right; margin-bottom:16px;">
            {text_html}
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:14px; padding-top:14px; border-top:1px solid {t['border']}; direction:rtl;">
            <div style="background:{t['bg_mid']}; border-radius:10px; padding:12px; border-right:3px solid {low_risk_color}; text-align:right;">
                <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:6px;">🛡 برای افراد کم‌ریسک</div>
                <div style="font-size:11px; color:{low_risk_color}; line-height:1.7; font-weight:600;">{low_risk_text}</div>
            </div>
            <div style="background:{t['bg_mid']}; border-radius:10px; padding:12px; border-right:3px solid {high_risk_color}; text-align:right;">
                <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:6px;">⚡ برای افراد پر‌ریسک</div>
                <div style="font-size:11px; color:{high_risk_color}; line-height:1.7; font-weight:600;">{high_risk_text}</div>
            </div>
        </div>
    </div>
    """)


# ═══════════════════════════════════════════════════════════
# Fear & Greed
# ═══════════════════════════════════════════════════════════
def render_fear_greed(value: float) -> None:
    t = _t()

    if value >= 80:
        label, c, adv, icon = "طمع شدید", t["red"], "احتمال اصلاح بالاست", "🔥"
    elif value >= 65:
        label, c, adv, icon = "طمع", t["orange"], "با احتیاط خرید کن", "😊"
    elif value >= 45:
        label, c, adv, icon = "خنثی", t["yellow"], "بازار متعادل", "😐"
    elif value >= 25:
        label, c, adv, icon = "ترس", t["green"], "فرصت خرید محتمل", "😟"
    else:
        label, c, adv, icon = "ترس شدید", t["green"], "فرصت قوی خرید", "😱"

    bar_width = int(value)

    _render(f"""
    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:16px; direction:rtl; text-align:right; box-shadow:0 2px 8px rgba(0,0,0,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div style="font-size:12px; font-weight:700; color:{t['fg']};">🌡 شاخص ترس و طمع</div>
            <div style="font-size:9px; color:{t['fg_muted']};">Fear & Greed</div>
        </div>
        <div style="display:flex; align-items:center; gap:14px;">
            <div style="text-align:center; min-width:80px;">
                <div style="font-size:32px; font-weight:700; color:{c}; font-family:'JetBrains Mono';">{value:.0f}</div>
                <div style="font-size:11px; color:{c}; font-weight:600;">{icon} {label}</div>
            </div>
            <div style="flex:1;">
                <div style="background:{t['bg_mid']}; height:8px; border-radius:4px; overflow:hidden; margin-bottom:8px;">
                    <div style="background:linear-gradient(90deg, {t['green']}, {t['yellow']}, {t['red']}); height:100%; width:{bar_width}%; border-radius:4px;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:8px; color:{t['fg_dim']}; margin-bottom:8px; direction:rtl;">
                    <span>ترس شدید</span><span>خنثی</span><span>طمع شدید</span>
                </div>
                <div style="font-size:11px; color:{c}; font-weight:600; margin-bottom:4px;">💡 {adv}</div>
            </div>
        </div>
    </div>
    """)


# ═══════════════════════════════════════════════════════════
# راستی‌آزمایی
# ═══════════════════════════════════════════════════════════
def render_backtest_stats(stats: dict, logs: list = None) -> None:
    t = _t()

    if "bt_time_filter" not in st.session_state:
        st.session_state.bt_time_filter = "all"

    st.markdown(
        f'<div style="font-size:11px; color:{t["fg_muted"]}; margin-bottom:6px; '
        f'direction:rtl; text-align:right;">📅 فیلتر زمانی:</div>',
        unsafe_allow_html=True,
    )

    time_filter_cols = st.columns([1, 1, 1])
    with time_filter_cols[0]:
        if st.button(
            "📅 ۷ روز",
            key="bt_filter_7d",
            use_container_width=True,
            type="primary" if st.session_state.bt_time_filter == "7d" else "secondary",
        ):
            st.session_state.bt_time_filter = "7d"
            st.rerun()
    with time_filter_cols[1]:
        if st.button(
            "📅 ۳۰ روز",
            key="bt_filter_30d",
            use_container_width=True,
            type="primary" if st.session_state.bt_time_filter == "30d" else "secondary",
        ):
            st.session_state.bt_time_filter = "30d"
            st.rerun()
    with time_filter_cols[2]:
        if st.button(
            "📅 همه",
            key="bt_filter_all",
            use_container_width=True,
            type="primary" if st.session_state.bt_time_filter == "all" else "secondary",
        ):
            st.session_state.bt_time_filter = "all"
            st.rerun()

    total = stats.get("total", 0)

    if total == 0:
        _render(
            f'<div style="color:{t["fg_muted"]}; font-size:11px; padding:20px; '
            f'text-align:center; background:{t["bg_card"]}; border:1px dashed {t["border"]}; '
            f'border-radius:10px; direction:rtl; margin-top:10px;">'
            f"هنوز سیگنالی ثبت نشده.<br>"
            f'<span style="font-size:9px; color:{t["fg_dim"]};">به‌محض ثبت، خودکار راستی‌آزمایی می‌شود</span></div>'
        )
        return

    win = stats.get("win", 0)
    loss = stats.get("loss", 0)
    pending = stats.get("pending", 0)
    expired = stats.get("expired", 0)
    wr = stats.get("win_rate", 0)
    pf = stats.get("profit_factor", 0)
    wr_c = t["green"] if wr >= 60 else (t["yellow"] if wr >= 40 else t["red"])
    pf_c = t["green"] if pf >= 1.5 else (t["yellow"] if pf >= 1.0 else t["red"])

    _render(f"""
    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:16px; direction:rtl; text-align:right; box-shadow:0 2px 8px rgba(0,0,0,0.2); margin-top:10px;">
        <div style="display:grid; grid-template-columns:repeat(5, 1fr); gap:8px; text-align:center;">
            <div><div style="font-size:9px; color:{t['fg_muted']};">کل</div>
                <div style="font-family:'JetBrains Mono'; font-size:18px; color:{t['fg']}; font-weight:700;">{total}</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">✅ برد</div>
                <div style="font-family:'JetBrains Mono'; font-size:18px; color:{t['green']}; font-weight:700;">{win}</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">❌ باخت</div>
                <div style="font-family:'JetBrains Mono'; font-size:18px; color:{t['red']}; font-weight:700;">{loss}</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">⏳ انتظار</div>
                <div style="font-family:'JetBrains Mono'; font-size:18px; color:{t['yellow']}; font-weight:700;">{pending}</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">⏰ منقضی</div>
                <div style="font-family:'JetBrains Mono'; font-size:18px; color:{t['fg_muted']}; font-weight:700;">{expired}</div></div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; text-align:center; margin-top:12px; padding-top:12px; border-top:1px solid {t['border']};">
            <div><div style="font-size:9px; color:{t['fg_muted']};">نرخ برد</div>
                <div style="font-family:'JetBrains Mono'; font-size:20px; color:{wr_c}; font-weight:700;">{wr:.0f}%</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">Profit Factor</div>
                <div style="font-family:'JetBrains Mono'; font-size:20px; color:{pf_c}; font-weight:700;">{pf:.2f}</div></div>
        </div>
    </div>
    """)

    action_cols = st.columns([1, 1, 1])
    with action_cols[0]:
        if st.button("🔄 بررسی مجدد", key="bt_recheck", use_container_width=True):
            try:
                from core.backtester import backtest_all

                result = backtest_all()
                if result.get("updated", 0) > 0:
                    st.success(f"✅ {result['updated']} سیگنال بررسی شد")
                else:
                    st.info("ℹ️ همه سیگنال‌ها در انتظار هستن")
                st.rerun()
            except Exception as e:
                st.error(f"خطا: {e}")

    with action_cols[1]:
        if logs:
            import json

            logs_json = json.dumps(logs, ensure_ascii=False, indent=2, default=str)
            st.download_button(
                "📥 دانلود JSON",
                data=logs_json,
                file_name=f"tradeyar_signals_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True,
                key="bt_export",
            )
        else:
            st.button(
                "📥 دانلود JSON",
                disabled=True,
                use_container_width=True,
                key="bt_export_disabled",
            )

    with action_cols[2]:
        if st.button(
            "🗑 ریست لاگ", key="bt_reset", use_container_width=True, type="secondary"
        ):
            st.session_state.bt_confirm_reset = True

    if st.session_state.get("bt_confirm_reset", False):
        st.warning("⚠️ همه سیگنال‌ها پاک می‌شن. مطمئنی؟")
        confirm_cols = st.columns([1, 1])
        with confirm_cols[0]:
            if st.button(
                "✅ بله، پاک کن",
                key="bt_confirm_yes",
                use_container_width=True,
                type="primary",
            ):
                try:
                    from core.backtester import reset_signal_log

                    reset_signal_log()
                    st.session_state.bt_confirm_reset = False
                    st.cache_data.clear()
                    st.success("✅ لاگ پاک شد")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطا در ریست: {e}")
                    st.session_state.bt_confirm_reset = False
        with confirm_cols[1]:
            if st.button("❌ لغو", key="bt_confirm_no", use_container_width=True):
                st.session_state.bt_confirm_reset = False
                st.rerun()


# ═══════════════════════════════════════════════════════════
# لیست سیگنال‌ها
# ═══════════════════════════════════════════════════════════
def render_recent_signals_list(logs: list) -> None:
    t = _t()

    if not logs:
        return

    from core.backtester import filter_logs

    with st.expander(f"📋 لیست سیگنال‌های ثبت‌شده ({len(logs)} مورد)", expanded=False):
        sorted_logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)

        st.markdown(
            f'<div style="font-size:10px; color:{t["fg_muted"]}; margin:6px 0; '
            f'direction:rtl; text-align:right;">🔎 فیلترها:</div>',
            unsafe_allow_html=True,
        )

        filter_cols = st.columns(4)
        with filter_cols[0]:
            st.markdown(
                f'<div style="font-size:10px; color:{t["fg_muted"]}; margin-bottom:4px; '
                f'direction:rtl;">بازار</div>',
                unsafe_allow_html=True,
            )
            market_filter = st.selectbox(
                "بازار",
                ["همه", "اسپات", "فیوچرز"],
                key="log_market_filter",
                label_visibility="collapsed",
            )
        with filter_cols[1]:
            st.markdown(
                f'<div style="font-size:10px; color:{t["fg_muted"]}; margin-bottom:4px; '
                f'direction:rtl;">سیگنال</div>',
                unsafe_allow_html=True,
            )
            signal_filter = st.selectbox(
                "سیگنال",
                ["همه", "LONG", "SHORT"],
                key="log_signal_filter",
                label_visibility="collapsed",
            )
        with filter_cols[2]:
            st.markdown(
                f'<div style="font-size:10px; color:{t["fg_muted"]}; margin-bottom:4px; '
                f'direction:rtl;">وضعیت</div>',
                unsafe_allow_html=True,
            )
            status_filter = st.selectbox(
                "وضعیت",
                ["همه", "در انتظار", "برد", "باخت", "منقضی"],
                key="log_status_filter",
                label_visibility="collapsed",
            )
        with filter_cols[3]:
            st.markdown(
                f'<div style="font-size:10px; color:{t["fg_muted"]}; margin-bottom:4px; '
                f'direction:rtl;">زمان</div>',
                unsafe_allow_html=True,
            )
            time_filter = st.selectbox(
                "زمان",
                ["همه", "۷ روز", "۳۰ روز"],
                key="log_time_filter",
                label_visibility="collapsed",
            )

        market_map = {"همه": "all", "اسپات": "spot", "فیوچرز": "futures"}
        signal_map = {"همه": "all", "LONG": "long", "SHORT": "short"}
        status_map = {
            "همه": "all",
            "در انتظار": "pending",
            "برد": "win",
            "باخت": "loss",
            "منقضی": "expired",
        }
        time_map = {"همه": "all", "۷ روز": "7d", "۳۰ روز": "30d"}

        filtered = filter_logs(
            sorted_logs,
            market_filter=market_map.get(market_filter, "all"),
            signal_filter=signal_map.get(signal_filter, "all"),
            status_filter=status_map.get(status_filter, "all"),
            time_filter=time_map.get(time_filter, "all"),
        )

        if not filtered:
            st.info("هیچ سیگنالی با این فیلترها پیدا نشد.")
            return

        for entry in filtered[:50]:
            _render_log_entry(entry, t)


def _render_log_entry(entry: dict, t: dict) -> None:
    sig = entry.get("signal", "—")
    ticker = entry.get("ticker", "—")
    name = entry.get("name", ticker)
    tf = entry.get("tf", "—")
    price = _safe_num(entry.get("price"))
    result = entry.get("result")
    ts = entry.get("timestamp", "")
    market_type = entry.get("market_type", "spot")
    source = entry.get("source", "—")
    result_time = entry.get("result_time", "")
    exit_price = entry.get("exit_price")

    is_iranian = _is_iranian_ticker(ticker)

    if SigEnum.is_long(sig):
        sig_color = t["green"]
        sig_icon = "🟢"
    elif SigEnum.is_short(sig):
        sig_color = t["red"]
        sig_icon = "🔴"
    else:
        sig_color = t["fg_muted"]
        sig_icon = "⚪"

    if result is True:
        result_icon, result_text, result_color = "✅", "برد", t["green"]
    elif result is False:
        result_icon, result_text, result_color = "❌", "باخت", t["red"]
    elif result == "expired":
        result_icon, result_text, result_color = "⏰", "منقضی", t["fg_muted"]
    else:
        result_icon, result_text, result_color = "⏳", "در انتظار", t["yellow"]

    market_badge = "📈 فیوچرز" if market_type == "futures" else "💵 اسپات"
    market_color = t["orange"] if market_type == "futures" else t["green"]

    src_info = get_source_info(source)
    src_badge = f"{src_info['icon']} {src_info['full_name']}"

    try:
        dt = datetime.fromisoformat(ts)
        ts_str = dt.strftime("%m-%d %H:%M")
    except Exception:
        ts_str = ts[:16] if ts else "—"

    result_time_str = ""
    if result_time:
        try:
            rdt = datetime.fromisoformat(result_time)
            result_time_str = rdt.strftime("%m-%d %H:%M")
        except Exception:
            result_time_str = result_time[:16]

    # فرمت قیمت
    if is_iranian:
        price_str = f"{price:,.0f} تومان"
        exit_str = f"→ {_safe_num(exit_price):,.0f} تومان" if exit_price else ""
    else:
        price_str = f"${price:,.2f}"
        exit_str = f"→ ${_safe_num(exit_price):,.2f}" if exit_price else ""

    _render(
        f'<div style="background:{t["bg_card"]}; border:1px solid {t["border"]}; '
        f"border-right:3px solid {sig_color}; "
        f"border-radius:10px; padding:12px; margin-bottom:8px; "
        f'direction:rtl; text-align:right;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
        f'<span style="font-size:12px; color:{sig_color}; font-weight:700;">{sig_icon} {sig}</span>'
        f'<span style="font-size:11px; color:{result_color}; font-weight:600;">{result_icon} {result_text}</span>'
        f"</div>"
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:6px;">'
        f'<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">'
        f'<b style="color:{t["primary"]}; font-size:12px;">{name}</b>'
        f'<span style="font-size:9px; color:{t["fg_muted"]}; direction:ltr;">{ticker}</span>'
        f'<span style="font-size:9px; color:{market_color}; padding:2px 6px; background:{market_color}15; border-radius:6px;">{market_badge}</span>'
        f'<span style="font-size:9px; color:{t["fg_muted"]};">{src_badge}</span>'
        f"</div>"
        f'<span style="font-size:10px; color:{t["cyan"]}; padding:2px 6px; background:{t["cyan"]}15; border-radius:6px;">{tf}</span>'
        f"</div>"
        f'<div style="display:flex; justify-content:space-between; font-size:10px; color:{t["fg_muted"]};">'
        f"<span style=\"font-family:'JetBrains Mono'; direction:rtl;\">💰 {price_str} {exit_str}</span>"
        f"<span>🕐 ثبت: {ts_str}</span>"
        f"</div>"
        f'{f"<div style=\'font-size:9px; color:{result_color}; margin-top:4px; text-align:left; direction:ltr;\'>✅ تأیید: {result_time_str}</div>" if result_time_str else ""}'
        f"</div>"
    )


# ═══════════════════════════════════════════════════════════
# اسکنر
# ═══════════════════════════════════════════════════════════
def render_scanner(
    scan_data: dict, filter_signal: str = "all", last_update: str = ""
) -> str | None:
    t = _t()

    all_results = scan_data.get("all", [])
    total_scanned = scan_data.get("total_scanned", 0)
    total_success = scan_data.get("total_success", 0)
    category_name = scan_data.get("category_name", "")
    category_icon = scan_data.get("category_icon", "📊")
    empty_message = scan_data.get("empty_message")
    source_label = scan_data.get("source_label", "")

    if empty_message:
        st.info(f"{category_icon} {category_name} — {empty_message}")
        return None

    if not all_results:
        st.warning(f"⚠️ اسکنر نتونست هیچ نمادی از {category_name} رو تحلیل کنه.")
        return None

    def passes_filter(item):
        sig = item.get("signal", "")
        if filter_signal == "long":
            return SigEnum.is_long(sig)
        elif filter_signal == "short":
            return SigEnum.is_short(sig)
        return True

    filtered = [x for x in all_results if passes_filter(x)]

    source_html = ""
    if source_label:
        source_html = (
            f'<div style="font-size:9px; color:{t["cyan"]}; margin-top:3px;">'
            f"📡 منبع: {source_label}</div>"
        )

    _render(f"""
    <div style="background:{t['bg_card']};
                border:1px solid {t['border']}; border-radius:12px;
                padding:14px 18px; margin-bottom:8px; direction:rtl; text-align:right;
                box-shadow:0 2px 8px rgba(0,0,0,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:22px;">🎯</span>
                <div style="text-align:right;">
                    <div style="font-size:14px; font-weight:700; color:{t['primary']};">
                        {category_icon} {category_name}
                    </div>
                    <div style="font-size:10px; color:{t['fg_muted']}; margin-top:3px;">
                        {total_success}/{total_scanned} نماد اسکن شد
                    </div>
                    {source_html}
                </div>
            </div>
        </div>
    </div>
    """)

    if last_update:
        timer_cols = st.columns([1, 4])
        with timer_cols[0]:
            render_live_timer(
                last_update,
                key=f"scanner_{category_name}",
                prefix="🕐 آخرین اسکن:",
                font_size=11,
                color=t["cyan"],
            )

    selected_ticker = None

    for idx, item in enumerate(filtered[:10], 1):
        signal = item.get("signal", "خنثی")
        score = item.get("score", 0)
        name = item.get("name", "")
        ticker = item.get("ticker", "")
        price = item.get("price", 0)
        confidence = item.get("confidence", 0)
        rr = item.get("rr")

        is_iranian = _is_iranian_ticker(ticker)

        if SigEnum.is_long(signal):
            sig_color = t["green"]
            sig_icon = "🟢"
            sig_text = "LONG"
        elif SigEnum.is_short(signal):
            sig_color = t["red"]
            sig_icon = "🔴"
            sig_text = "SHORT"
        else:
            sig_color = t["fg_muted"]
            sig_icon = "⚪"
            sig_text = "خنثی"

        if score >= 70:
            score_color = t["green"]
        elif score >= 50:
            score_color = t["yellow"]
        else:
            score_color = t["orange"]

        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")

        if is_iranian:
            price_str = f"{price:,.0f} تومان"
        else:
            price_str = f"${price:,.2f}" if price < 10000 else f"${price:,.0f}"

        rr_str = f"{rr:.1f}" if rr else "—"

        row_cols = st.columns([1, 10])

        with row_cols[0]:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button(
                "➕",
                key=f"add_scan_{ticker}_{idx}",
                use_container_width=True,
                help=f"افزودن {name}",
            ):
                selected_ticker = ticker

        with row_cols[1]:
            _render(f"""
            <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:10px; padding:12px 14px; margin-bottom:6px; direction:rtl; box-shadow:0 1px 4px rgba(0,0,0,0.15);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:18px;">{medal}</span>
                        <div style="text-align:right;">
                            <div style="font-size:13px; font-weight:700; color:{t['fg']};">{name}</div>
                            <div style="font-size:9px; color:{t['fg_muted']}; direction:ltr;">{ticker}</div>
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:14px;">
                        <div style="text-align:center;">
                            <div style="font-size:8px; color:{t['fg_muted']};">سیگنال</div>
                            <div style="font-family:'JetBrains Mono'; font-size:11px; color:{sig_color}; font-weight:700;">{sig_icon} {sig_text}</div>
                        </div>
                        <div style="text-align:center;">
                            <div style="font-size:8px; color:{t['fg_muted']};">امتیاز</div>
                            <div style="font-family:'JetBrains Mono'; font-size:13px; color:{score_color}; font-weight:700;">{score:.0f}</div>
                        </div>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px;">
                    <div style="background:{t['bg_mid']}; border-radius:6px; padding:5px; text-align:center;">
                        <div style="font-size:8px; color:{t['fg_muted']};">قیمت</div>
                        <div style="font-family:'JetBrains Mono'; font-size:10px; color:{t['fg']}; font-weight:600; direction:rtl;">{price_str}</div>
                    </div>
                    <div style="background:{t['bg_mid']}; border-radius:6px; padding:5px; text-align:center;">
                        <div style="font-size:8px; color:{t['fg_muted']};">اطمینان</div>
                        <div style="font-family:'JetBrains Mono'; font-size:10px; color:{t['primary']}; font-weight:600;">{confidence}%</div>
                    </div>
                    <div style="background:{t['bg_mid']}; border-radius:6px; padding:5px; text-align:center;">
                        <div style="font-size:8px; color:{t['fg_muted']};">R:R</div>
                        <div style="font-family:'JetBrains Mono'; font-size:10px; color:{t['cyan']}; font-weight:600;">{rr_str}</div>
                    </div>
                </div>
            </div>
            """)

    return selected_ticker


# ═══════════════════════════════════════════════════════════
# چک‌لیست
# ═══════════════════════════════════════════════════════════
def render_checklist(
    items: list, percentage: int, final_text: str, final_color: str
) -> None:
    t = _t()

    st.progress(percentage / 100)

    color_map = {
        "green": t["green"],
        "red": t["red"],
        "yellow": t["yellow"],
        "orange": t.get("orange", "#F97316"),
    }
    final_color_hex = color_map.get(final_color, t["primary"])

    _render(
        f'<div style="background:{t["bg_card"]}; border:1px solid {t["border"]}; '
        f"border-radius:12px; padding:14px; margin:10px 0; direction:rtl; "
        f'box-shadow:0 2px 8px rgba(0,0,0,0.2);">'
        f'<div style="text-align:center; font-size:13px; font-weight:700; '
        f"color:{final_color_hex}; padding:12px; "
        f'background:{t["bg_mid"]}; border-radius:10px; '
        f'border-right:3px solid {final_color_hex};">{final_text}</div>'
        f"</div>"
    )

    if not items:
        return

    GROUP_ORDER = [
        "multi_tf",
        "divergence",
        "momentum",
        "trend",
        "volatility",
        "volume",
        "structure",
        "sl_tp",
    ]

    sorted_items = sorted(
        items,
        key=lambda x: (
            GROUP_ORDER.index(x.get("group", ""))
            if x.get("group") in GROUP_ORDER
            else 999
        ),
    )

    for item in sorted_items:
        label = item.get("label", "")
        detail = item.get("detail", "")
        score = item.get("score", 0.0)
        weight = item.get("weight", 0)
        color_key = item.get("color", "yellow")
        reasons = item.get("reasons", [])
        vote = item.get("vote", None)

        c = color_map.get(color_key, t["fg"])

        if vote is None:
            status_icon = "•"
        elif vote > 0:
            status_icon = "🟢"
        elif vote < 0:
            status_icon = "🔴"
        else:
            status_icon = "⚪"

        title = f"{status_icon} {label}  ·  {score:+.2f}  ({weight}%)"

        with st.expander(title, expanded=False):
            if detail:
                _render(
                    f'<div style="color:{t["fg_dim"]}; font-size:10px; '
                    f'margin-bottom:10px; direction:rtl; line-height:1.7;">{detail}</div>'
                )

            if reasons:
                for r in reasons:
                    _render(
                        f'<div style="color:{t["fg_muted"]}; font-size:11px; '
                        f"padding:8px 10px; margin-bottom:5px; "
                        f'background:{t["bg_mid"]}; border-radius:6px; '
                        f"border-right:2px solid {c}; direction:rtl; "
                        f'text-align:right; line-height:1.6;">◦ {r}</div>'
                    )
            else:
                _render(
                    f'<div style="color:{t["fg_dim"]}; font-size:10px; '
                    f'text-align:center; padding:10px; direction:rtl;">'
                    f"دلیلی ثبت نشده</div>"
                )


# ═══════════════════════════════════════════════════════════
# Order Book
# ═══════════════════════════════════════════════════════════
def render_order_book(
    orderbook_data: dict, sym_name: str = "", ticker: str = ""
) -> None:
    t = _t()

    if not orderbook_data:
        return

    is_iranian = _is_iranian_ticker(ticker)

    spread_pct = orderbook_data.get("spread_pct", 0)
    bids = orderbook_data.get("bids", [])[:5]
    asks = orderbook_data.get("asks", [])[:5]

    if not bids or not asks:
        return

    def _get_vol(item):
        try:
            return float(item[1])
        except (IndexError, ValueError, TypeError):
            return 0.0

    total_bid_vol = sum(_get_vol(b) for b in bids)
    total_ask_vol = sum(_get_vol(a) for a in asks)

    if total_bid_vol + total_ask_vol > 0:
        buy_pressure = (total_bid_vol / (total_bid_vol + total_ask_vol)) * 100
        sell_pressure = 100 - buy_pressure
    else:
        buy_pressure = sell_pressure = 50

    buy_color = t["green"] if buy_pressure > sell_pressure else t["red"]

    def _fmt(price):
        try:
            p = float(price)
            if is_iranian:
                return f"{p:,.0f}"
            return f"${p:,.4f}" if p < 1000 else f"${p:,.2f}"
        except (TypeError, ValueError):
            return "—"

    ask_rows = ""
    for a in reversed(asks):
        try:
            price = float(a[0])
            vol = float(a[1])
            ask_rows += (
                f'<div style="display:flex; justify-content:space-between; '
                f"padding:4px 10px; font-size:10px; direction:rtl; "
                f'font-family:\'JetBrains Mono\'; color:{t["red"]}; '
                f'border-bottom:1px solid {t["border"]}20;">'
                f"<span>{_fmt(price)}</span><span>{vol:.4f}</span></div>"
            )
        except (IndexError, ValueError, TypeError):
            continue

    bid_rows = ""
    for b in bids:
        try:
            price = float(b[0])
            vol = float(b[1])
            bid_rows += (
                f'<div style="display:flex; justify-content:space-between; '
                f"padding:4px 10px; font-size:10px; direction:rtl; "
                f'font-family:\'JetBrains Mono\'; color:{t["green"]}; '
                f'border-bottom:1px solid {t["border"]}20;">'
                f"<span>{_fmt(price)}</span><span>{vol:.4f}</span></div>"
            )
        except (IndexError, ValueError, TypeError):
            continue

    _render(f"""
    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:14px; direction:rtl; margin-top:12px; box-shadow:0 2px 8px rgba(0,0,0,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid {t['border']};">
            <div style="font-size:13px; font-weight:700; color:{t['primary']}; padding-right:8px; border-right:3px solid {t['primary']};">
                📊 عمق بازار {sym_name}
            </div>
            <div style="font-size:10px; color:{t['fg_muted']};">
                Spread: <b style="color:{t['cyan']}; font-family:'JetBrains Mono';">{spread_pct:.4f}%</b>
            </div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; direction:rtl;">
            <div>
                <div style="font-size:10px; color:{t['red']}; font-weight:700; margin-bottom:6px; text-align:center;">🔴 فروش (Asks)</div>
                <div style="background:{t['bg_mid']}; border-radius:8px; padding:4px 0; overflow:hidden;">{ask_rows}</div>
            </div>
            <div>
                <div style="font-size:10px; color:{t['green']}; font-weight:700; margin-bottom:6px; text-align:center;">🟢 خرید (Bids)</div>
                <div style="background:{t['bg_mid']}; border-radius:8px; padding:4px 0; overflow:hidden;">{bid_rows}</div>
            </div>
        </div>

        <div style="margin-top:14px; padding-top:12px; border-top:1px solid {t['border']};">
            <div style="display:flex; justify-content:space-between; font-size:10px; color:{t['fg_muted']}; margin-bottom:6px;">
                <span>فشار خرید: <b style="color:{t['green']}; font-family:'JetBrains Mono';">{buy_pressure:.1f}%</b></span>
                <span>فشار فروش: <b style="color:{t['red']}; font-family:'JetBrains Mono';">{sell_pressure:.1f}%</b></span>
            </div>
            <div style="background:{t['bg_mid']}; height:10px; border-radius:5px; overflow:hidden; display:flex;">
                <div style="background:{t['green']}; height:100%; width:{buy_pressure}%;"></div>
                <div style="background:{t['red']}; height:100%; width:{sell_pressure}%;"></div>
            </div>
            <div style="font-size:10px; color:{buy_color}; font-weight:700; text-align:center; margin-top:6px;">
                {"🟢 فشار خرید بیشتره — احتمال صعود" if buy_pressure > sell_pressure else "🔴 فشار فروش بیشتره — احتمال نزول"}
            </div>
        </div>
    </div>
    """)


# ═══════════════════════════════════════════════════════════
# تایمر زنده
# ═══════════════════════════════════════════════════════════
def render_live_timer(
    timestamp_str: str,
    key: str = "timer",
    prefix: str = "🕐",
    font_size: int = 11,
    color: str = None,
) -> None:
    t = _t()

    if not timestamp_str:
        _render(
            f'<span style="font-size:{font_size}px; color:{t["fg_muted"]};">—</span>'
        )
        return

    try:
        if len(timestamp_str) <= 8 and ":" in timestamp_str:
            today = datetime.now().strftime("%Y-%m-%d")
            dt = datetime.strptime(f"{today} {timestamp_str}", "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.fromisoformat(timestamp_str)
        iso_str = dt.isoformat()
    except Exception:
        iso_str = timestamp_str

    timer_color = color if color else t["cyan"]

    timer_html = f"""
    <!DOCTYPE html><html><head><style>
        body {{ margin: 0; padding: 0; background: transparent; overflow: hidden;
            font-family: 'IRANYekanX', 'Tahoma', sans-serif; direction: rtl; }}
        #ty-live-timer {{ display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }}
        #ty-live-timer .prefix {{ font-size: {font_size - 1}px; color: {t['fg_muted']}; }}
        #ty-live-timer .time {{ font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: {font_size}px; color: {timer_color}; font-weight: 600; direction: ltr; }}
    </style></head>
    <body>
        <span id="ty-live-timer">
            <span class="prefix">{prefix}</span>
            <span class="time" id="ty-timer-text">—</span>
        </span>
        <script>
        (function liveTimer() {{
            var startISO = "{iso_str}";
            function updateTimer() {{
                try {{
                    var now = new Date();
                    var start = new Date(startISO);
                    var deltaSec = Math.floor((now - start) / 1000);
                    var text;
                    if (deltaSec < 0) text = "الان";
                    else if (deltaSec < 5) text = "همین الان";
                    else if (deltaSec < 60) text = deltaSec + " ثانیه پیش";
                    else if (deltaSec < 3600) text = Math.floor(deltaSec / 60) + " دقیقه پیش";
                    else if (deltaSec < 86400) text = Math.floor(deltaSec / 3600) + " ساعت پیش";
                    else text = Math.floor(deltaSec / 86400) + " روز پیش";
                    var el = document.getElementById('ty-timer-text');
                    if (el) el.textContent = text;
                }} catch(e) {{}}
                setTimeout(updateTimer, 1000);
            }}
            updateTimer();
        }})();
        </script>
    </body></html>
    """
    components.html(timer_html, height=font_size + 14)


# ═══════════════════════════════════════════════════════════
# Exports
# ═══════════════════════════════════════════════════════════
__all__ = [
    "sparkline_svg",
    "render_section_header",
    "render_header",
    "render_settings_panel_open_button",
    "render_settings_panel",
    "render_top_ticker",
    "render_settings_section_title",
    "render_settings_divider",
    "render_profile_selector",
    "render_source_selector",
    "render_source_badge",
    "render_market_type_selector",
    "render_unified_signal_card",
    "render_tf_table",
    "render_deep_analysis",
    "render_fear_greed",
    "render_backtest_stats",
    "render_recent_signals_list",
    "render_scanner",
    "render_checklist",
    "render_order_book",
    "render_live_timer",
]
