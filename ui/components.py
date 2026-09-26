"""
ui/components.py
کامپوننت‌های رابط کاربری — نسخه ۴.۰ (اصلاح S/R + موبایل)
هدر + تیکر + کارت سیگنال + S/R + تحلیل + تقویم + اخبار
"""

from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from ui.styles import get_theme


# ═══════════════════════════════════════════════════════════
# ابزارهای کمکی
# ═══════════════════════════════════════════════════════════
def _t() -> dict:
    return get_theme(st.session_state.get("theme", "dark"))


def _render(html: str) -> None:
    clean = "".join(line.strip() for line in html.split("\n"))
    st.markdown(clean, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# اسپارک‌لاین SVG
# ═══════════════════════════════════════════════════════════
def sparkline_svg(prices: list, color: str, width: int = 70, height: int = 26,
                  trend: str = "flat") -> str:
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
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════
# هدر
# ═══════════════════════════════════════════════════════════
def render_header(jalali: str, weekday: str, miladi: str) -> None:
    t = _t()

    header_html = f"""
    <div class="tradeyar-header">
        <div class="header-left">
            <span style="font-size:32px; filter:drop-shadow(0 0 8px {t['primary']}); line-height:1;">🏆</span>
            <div>
                <div style="font-size:18px; font-weight:bold; color:{t['primary']}; line-height:1.2;">TradeYar</div>
                <div style="font-size:10px; color:{t['fg_muted']};">ترید‌یار ۲۰۲۶</div>
            </div>
        </div>

        <div class="header-center">
            <div style="font-size:11px; color:{t['fg_muted']}; margin-bottom:2px;">🕐</div>
            <div id="ty-clock-header" style="
                font-family:Consolas,monospace;
                font-size:22px;
                font-weight:bold;
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
                <div style="font-size:13px; color:{t['fg']}; font-weight:bold; line-height:1.4;">{jalali}</div>
                <div style="font-size:10px; color:{t['fg_muted']};">{weekday}</div>
                <div style="font-size:9px; color:{t['fg_dim']}; direction:ltr;">{miladi}</div>
            </div>
        </div>
    </div>
    """
    _render(header_html)

    clock_js = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
    </style>
    </head>
    <body>
        <script>
        (function tick() {{
            var now = new Date();
            var utc = now.getTime() + (now.getTimezoneOffset() * 60000);
            var teh = new Date(utc + (3.5 * 3600000));
            var h = String(teh.getHours()).padStart(2, '0');
            var m = String(teh.getMinutes()).padStart(2, '0');
            var s = String(teh.getSeconds()).padStart(2, '0');
            var timeStr = h + ':' + m + ':' + s;

            try {{
                var parentClock = window.parent.document.getElementById('ty-clock-header');
                if (parentClock) parentClock.textContent = timeStr;
            }} catch(e) {{}}

            setTimeout(tick, 1000);
        }})();
        </script>
    </body>
    </html>
    """
    components.html(clock_js, height=0)


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
            c = t["green"] if change > 0 else (t["red"] if change < 0 else t["fg_muted"])
            change_html = f'<span style="color:{c}; font-size:10px;">{arrow}{abs(change):.2f}%</span>'

        return (
            f'<div class="ticker-item">'
            f'<span style="font-size:13px;">{emoji}</span>'
            f'<span style="color:{t["fg_muted"]}; font-size:10px;">{name}:</span>'
            f'<span style="font-family:Consolas; color:{t["fg"]}; font-weight:bold; direction:ltr; font-size:11px;">{price_str}</span>'
            f'{change_html}'
            f'</div>'
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
            f'<span style="color:{color}; font-size:10px; font-weight:bold;">{name}</span>'
            f'<span style="color:{t["fg_muted"]}; font-size:9px;">{next_event}</span>'
            f'</div>'
        )

    prices_html = "".join(render_price(p) for p in prices_data)
    markets_html = "".join(render_market(m) for m in markets_info)

    _render(f"""
    <div class="top-ticker">
        <div class="ticker-row-wrapper">
            <div class="ticker-track">{prices_html}</div>
        </div>
        <div class="ticker-row-wrapper" style="border-top:1px solid {t['border']}; margin-top:6px; padding-top:6px;">
            <div class="ticker-track">{markets_html}</div>
        </div>
    </div>
    """)


# ═══════════════════════════════════════════════════════════
# S/R — ساخت HTML (نسخه بهبودیافته)
# ═══════════════════════════════════════════════════════════
def _build_sr_rows(analysis: dict, max_levels: int = 3) -> tuple:
    """
    ساخت HTML سطوح S/R با منطق درست:
    - مقاومت‌ها: قرمز، از دورترین به نزدیک‌ترین (نزولی به قیمت)
    - حمایت‌ها: سبز، از نزدیک‌ترین به دورترین (نزولی از قیمت)
    - برچسب‌ها: R-1 (نزدیک‌ترین) تا R-3 (دورترین)
    """
    t = _t()
    price = analysis.get("price", 0)
    pivots = analysis.get("pivots") or {}
    swings = analysis.get("swings") or {}

    if not price or price <= 0:
        empty = f'<div style="text-align:center; padding:8px; color:{t["fg_dim"]}; font-size:10px;">داده کافی نیست</div>'
        return empty, empty, empty

    # ─── جمع‌آوری سطوح ───
    resistances = []
    supports = []

    # Pivot Points
    for key, label in [("r3", "R3"), ("r2", "R2"), ("r1", "R1")]:
        v = pivots.get(key, 0)
        if v and v > price:
            resistances.append({"pivot_label": label, "price": v, "source": "pivot"})

    for key, label in [("s3", "S3"), ("s2", "S2"), ("s1", "S1")]:
        v = pivots.get(key, 0)
        if v and v < price:
            supports.append({"pivot_label": label, "price": v, "source": "pivot"})

    # Swing High/Low
    if swings.get("swing_highs"):
        for _, p in swings["swing_highs"]:
            if p > price:
                resistances.append({"pivot_label": "SW", "price": p, "source": "swing"})

    if swings.get("swing_lows"):
        for _, p in swings["swing_lows"]:
            if p < price:
                supports.append({"pivot_label": "SW", "price": p, "source": "swing"})

    # حذف تکراری (فاصله کمتر از ۰.۱٪)
    def dedupe(levels):
        result = []
        for lvl in levels:
            if not any(abs(lvl["price"] - r["price"]) / price < 0.001 for r in result):
                result.append(lvl)
        return result

    resistances = dedupe(resistances)
    supports = dedupe(supports)

    # ─── مرتب‌سازی ───
    # مقاومت‌ها: صعودی (دورترین → نزدیک‌ترین برای نمایش از بالا به پایین)
    # اینطور: بالا = دورترین، پایین = نزدیک‌ترین (کنار قیمت)
    resistances.sort(key=lambda x: -x["price"])

    # حمایت‌ها: نزولی (نزدیک‌ترین → دورترین)
    # اینطور: بالا = نزدیک‌ترین، پایین = دورترین
    supports.sort(key=lambda x: -x["price"])

    resistances = resistances[:max_levels]
    supports = supports[:max_levels]

    # ─── سطح قیمت ───
    price_str = f"${price:,.2f}" if price < 10000 else f"${price:,.0f}"
    price_row = (
        f'<div style="display:flex; justify-content:space-between; align-items:center; '
        f'padding:10px 12px; margin:8px 0; '
        f'background:linear-gradient(90deg, {t["primary_glow"]}, transparent); '
        f'border:2px solid {t["primary"]}; border-radius:8px; direction:rtl;">'
        f'<div style="display:flex; align-items:center; gap:6px;">'
        f'<span style="font-size:14px;">💎</span>'
        f'<span style="font-size:12px; color:{t["fg"]}; font-weight:bold;">قیمت فعلی</span>'
        f'</div>'
        f'<span style="font-size:14px; color:{t["primary"]}; font-family:Consolas; '
        f'font-weight:bold; direction:ltr;">{price_str}</span>'
        f'</div>'
    )

    # ─── ساخت ردیف ───
    def level_row(level, order_num, is_resistance):
        """
        order_num: شماره ترتیب (۱ = نزدیک‌ترین به قیمت)
        """
        lvl_price = level["price"]
        dist_pct = (lvl_price - price) / price * 100
        abs_dist = abs(dist_pct)

        # رنگ اصلی
        base_color = t["red"] if is_resistance else t["green"]

        # شدت بر اساس فاصله
        if abs_dist < 0.5:
            opacity = 1.0
            border_width = 4
            bg_tint = f"rgba({248 if is_resistance else 74},{113 if is_resistance else 222},{113 if is_resistance else 128},0.10)"
            weight = "bold"
        elif abs_dist < 1.5:
            opacity = 0.85
            border_width = 3
            bg_tint = t["bg_mid"]
            weight = "bold"
        else:
            opacity = 0.65
            border_width = 2
            bg_tint = t["bg_mid"]
            weight = "normal"

        # ─── برچسب: R-1/S-1 + آیکون منبع ───
        prefix = "R" if is_resistance else "S"
        display_label = f"{prefix}-{order_num}"

        # آیکون منبع
        if level["source"] == "pivot":
            src_icon = "📌"
            src_text = "P"
            src_color = t["cyan"]
        else:
            src_icon = "🔄"
            src_text = "W"
            src_color = t["purple"]

        price_str = f"${lvl_price:,.2f}" if lvl_price < 10000 else f"${lvl_price:,.0f}"
        sign = "▲" if dist_pct > 0 else "▼"

        return (
            f'<div style="display:flex; justify-content:space-between; align-items:center; '
            f'padding:8px 10px; margin:3px 0; background:{bg_tint}; border-radius:6px; '
            f'border-right:{border_width}px solid {base_color}; opacity:{opacity}; direction:rtl;">'
            f'<div style="display:flex; align-items:center; gap:6px;">'
            f'<span style="font-size:10px;">{src_icon}</span>'
            f'<span style="font-size:11px; color:{base_color}; font-family:Consolas; font-weight:bold; min-width:34px;">{display_label}</span>'
            f'<span style="font-size:9px; color:{src_color}; font-family:Consolas; opacity:0.8; min-width:14px;">{src_text}</span>'
            f'<span style="font-size:11px; color:{base_color}; font-family:Consolas; font-weight:{weight};">{price_str}</span>'
            f'</div>'
            f'<span style="font-size:9px; color:{base_color}; direction:ltr;">{sign} {abs_dist:.2f}%</span>'
            f'</div>'
        )

    # ─── مقاومت‌ها: از بالا (دورترین) به پایین (نزدیک‌ترین) ───
    # شماره‌گذاری: R-3 بالا، R-2 وسط، R-1 پایین (نزدیک قیمت)
    res_rows = ""
    if resistances:
        total = len(resistances)
        for i, lvl in enumerate(resistances):
            # i=0: دورترین → order = total
            # i=total-1: نزدیک‌ترین → order = 1
            order_num = total - i
            res_rows += level_row(lvl, order_num, True)
    else:
        res_rows = f'<div style="text-align:center; padding:6px; color:{t["fg_dim"]}; font-size:9px;">مقاومتی بالای قیمت نیست</div>'

    # ─── حمایت‌ها: از بالا (نزدیک‌ترین) به پایین (دورترین) ───
    # شماره‌گذاری: S-1 بالا (نزدیک قیمت)، S-3 پایین
    sup_rows = ""
    if supports:
        for i, lvl in enumerate(supports):
            order_num = i + 1  # 1, 2, 3
            sup_rows += level_row(lvl, order_num, False)
    else:
        sup_rows = f'<div style="text-align:center; padding:6px; color:{t["fg_dim"]}; font-size:9px;">حمایتی زیر قیمت نیست</div>'

    return res_rows, price_row, sup_rows


# ═══════════════════════════════════════════════════════════
# کارت یکپارچه سیگنال + S/R
# ═══════════════════════════════════════════════════════════
def render_unified_signal_card(
    analysis: dict,
    sym_name: str,
    tf_name: str,
    ticker: str = "",
) -> None:
    t = _t()

    if not analysis:
        _render(
            f'<div style="text-align:center; padding:30px; '
            f'background:{t["bg_card"]}; border:1px solid {t["border"]}; '
            f'border-radius:12px; color:{t["fg_muted"]}; direction:rtl;">'
            f'در حال محاسبه تحلیل...</div>'
        )
        return

    signal = analysis.get("signal", "خنثی")
    price = analysis.get("price", 0)
    confidence = analysis.get("confidence", 0)
    sl_tp = analysis.get("sl_tp")
    rr = analysis.get("rr")

    # ─── تعیین رنگ و متن ───
    if "LONG" in signal:
        icon = "🟢"
        action = "مناسب برای خرید"
        signal_color = t["green"]
        signal_border = t["green"]
        decision_text = "تصمیم: بخر یا صبر کن"
        decision_color = t["green"]
        if confidence >= 70:
            advice = "قیمت احتمالاً بالا می‌ره. با حد ضرر و ۱-۳٪ سرمایه وارد شو."
        elif confidence >= 50:
            advice = "نشانه‌های صعودی ضعیفه. با احتیاط و سرمایه کم وارد شو."
        else:
            advice = "سیگنال صعودی ضعیفه. بهتره صبر کنی تا شرایط قوی‌تر بشه."
    elif "SHORT" in signal:
        icon = "🔴"
        action = "مناسب برای فروش"
        signal_color = t["red"]
        signal_border = t["red"]
        decision_text = "تصمیم: بفروش یا صبر کن"
        decision_color = t["red"]
        if confidence >= 70:
            advice = "قیمت احتمالاً پایین می‌ره. محتاط باش و حد ضرر بذار."
        elif confidence >= 50:
            advice = "فشار فروش ضعیفه. با احتیاط و سرمایه کم وارد شو."
        else:
            advice = "سیگنال نزولی ضعیفه. صبر کن تا وضعیت واضح‌تر بشه."
    else:
        icon = "⚪"
        action = "فعلاً نخر"
        signal_color = t["fg_muted"]
        signal_border = t["border_light"]
        decision_text = "تصمیم: وارد نشو"
        decision_color = t["fg_muted"]
        advice = "بدون سیگنال واضح. صبر کن تا بازار تصمیم بگیره."

    # ─── فرمت قیمت‌ها ───
    def _fmt_price(p):
        if not p or p <= 0:
            return "—"
        return f"${p:,.2f}" if p < 10000 else f"${p:,.0f}"

    price_str = _fmt_price(price)

    # ─── SL/TP ───
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

        if signal == "خنثی":
            sl_tp_note = (
                f'<div style="font-size:10px; color:{t["fg_muted"]}; margin-top:6px; '
                f'text-align:center; padding:6px; background:{t["bg_mid"]}; '
                f'border-radius:6px; direction:rtl;">'
                f'⚪ بازار خنثی — حد ضرر و هدف فعلاً تعریف نشده'
                f'</div>'
            )
        else:
            sl_tp_note = (
                f'<div style="font-size:10px; color:{t["yellow"]}; margin-top:6px; '
                f'text-align:center; padding:6px; background:rgba(250,204,21,0.08); '
                f'border-radius:6px; border-right:3px solid {t["yellow"]}; direction:rtl;">'
                f'⚠️ سیگنال ضعیف — منتظر سیگنال قوی‌تر باش'
                f'</div>'
            )

    # ─── S/R ───
    res_rows, price_row, sup_rows = _build_sr_rows(analysis, max_levels=3)

    # ─── بج سیگنال ───
    badge_bg = f'{signal_color}22' if signal != "خنثی" else 'rgba(139,148,158,0.15)'

    # ─── ضعیف ───
    weak_suffix = ""
    signal_main = signal
    if " ضعیف" in signal:
        signal_main = signal.replace(" ضعیف", "")
        weak_suffix = f'<div style="font-size:9px; color:{t["fg_muted"]}; margin-top:2px;">(ضعیف)</div>'

    ticker_html = f'<span style="font-size:11px; color:{t["fg_muted"]}; margin-right:6px;">({ticker})</span>' if ticker else ""

    # ═══════════════════════════════════════════════════════════
    # HTML نهایی — با بهبود کارت سیگنال و موبایل
    # ═══════════════════════════════════════════════════════════
    html = f"""
    <style>
        .ty-unified-card {{
            background:linear-gradient(135deg, {t['bg_card']} 0%, {t['bg_mid']} 100%);
            border:2px solid {signal_border};
            border-radius:14px;
            padding:18px 22px;
            margin-bottom:14px;
            box-shadow:0 6px 24px {signal_color}22;
            direction:rtl;
        }}
        .ty-unified-grid {{
            display:grid; grid-template-columns:1.2fr 1fr; gap:18px; align-items:start;
        }}
        .ty-sr-box {{
            background:{t['bg_mid']};
            border-radius:10px;
            padding:12px;
            border:1px solid {t['border']};
        }}
        .ty-signal-box {{
            background:{t['bg_mid']};
            border-radius:10px;
            padding:14px;
            border:1px solid {t['border']};
        }}

        /* موبایل */
        @media (max-width: 768px) {{
            .ty-unified-card {{
                padding:12px 14px;
            }}
            .ty-unified-grid {{
                grid-template-columns:1fr !important;
                gap:12px;
            }}
            .ty-sr-box, .ty-signal-box {{
                padding:10px;
            }}
            .ty-sr-header-sub {{
                display:none !important;
            }}
        }}
    </style>

    <div class="ty-unified-card">
        <!-- هدر مشترک -->
        <div style="
            display:flex; justify-content:space-between; align-items:center;
            padding-bottom:12px; margin-bottom:14px;
            border-bottom:1px solid {t['border']};
            flex-wrap:wrap; gap:10px;
        ">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:24px; filter:drop-shadow(0 0 6px {signal_color});">{icon}</span>
                <div>
                    <div style="font-size:15px; font-weight:bold; color:{t['fg']};">
                        تحلیل {sym_name} {ticker_html}
                    </div>
                    <div style="font-size:11px; color:{t['cyan']}; margin-top:2px; font-weight:bold;">
                        ⏱ تایم‌فریم: {tf_name}
                    </div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:20px;">
                <div style="text-align:center;">
                    <div style="font-size:9px; color:{t['fg_muted']};">قیمت فعلی</div>
                    <div style="font-family:Consolas; font-size:18px; color:{t['primary']}; font-weight:bold; direction:ltr;">{price_str}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:9px; color:{t['fg_muted']};">اطمینان</div>
                    <div style="font-family:Consolas; font-size:18px; color:{t['primary']}; font-weight:bold;">{confidence}%</div>
                </div>
            </div>
        </div>

        <!-- دو ستون -->
        <div class="ty-unified-grid">

            <!-- ستون راست: سیگنال -->
            <div class="ty-signal-box">
                <!-- بج سیگنال -->
                <div style="
                    display:flex; justify-content:space-between; align-items:center;
                    padding:12px 16px; margin-bottom:14px;
                    background:{badge_bg};
                    border:2px solid {signal_color};
                    border-radius:10px;
                ">
                    <div>
                        <div style="font-size:9px; color:{t['fg_muted']}; margin-bottom:2px;">سیگنال</div>
                        <div style="font-family:Consolas; font-size:20px; color:{signal_color}; font-weight:bold; letter-spacing:1px;">
                            {signal_main}
                        </div>
                        {weak_suffix}
                    </div>
                    <div style="text-align:left;">
                        <div style="font-size:11px; color:{signal_color}; font-weight:bold;">{action}</div>
                    </div>
                </div>

                <!-- جدول مقادیر -->
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:14px;">
                    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:8px; padding:10px; text-align:center; border-right:3px solid {t['primary']};">
                        <div style="font-size:9px; color:{t['fg_muted']}; margin-bottom:4px;">💰 ورود</div>
                        <div style="font-family:Consolas; font-size:13px; color:{t['fg']}; font-weight:bold; direction:ltr;">{price_str}</div>
                    </div>
                    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:8px; padding:10px; text-align:center; border-right:3px solid {sl_color};">
                        <div style="font-size:9px; color:{t['fg_muted']}; margin-bottom:4px;">🛑 حد ضرر</div>
                        <div style="font-family:Consolas; font-size:13px; color:{sl_color}; font-weight:bold; direction:ltr;">{sl_str}</div>
                    </div>
                    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:8px; padding:10px; text-align:center; border-right:3px solid {tp_color};">
                        <div style="font-size:9px; color:{t['fg_muted']}; margin-bottom:4px;">🎯 هدف</div>
                        <div style="font-family:Consolas; font-size:13px; color:{tp_color}; font-weight:bold; direction:ltr;">{tp_str}</div>
                    </div>
                    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:8px; padding:10px; text-align:center; border-right:3px solid {t['cyan']};">
                        <div style="font-size:9px; color:{t['fg_muted']}; margin-bottom:4px;">⚖️ سود/ضرر</div>
                        <div style="font-family:Consolas; font-size:13px; color:{t['cyan']}; font-weight:bold;">{rr_str}</div>
                    </div>
                </div>

                {sl_tp_note}

                <!-- باکس تصمیم -->
                <div style="
                    padding:12px 14px;
                    background:{t['bg_card']};
                    border:1px solid {t['border']};
                    border-radius:8px;
                    border-right:4px solid {decision_color};
                    margin-top:14px;
                ">
                    <div style="font-size:12px; font-weight:bold; color:{decision_color}; margin-bottom:6px;">{decision_text}</div>
                    <div style="font-size:11px; color:{t['fg']}; line-height:1.7;">{advice}</div>
                </div>
            </div>

            <!-- ستون چپ: S/R -->
            <div class="ty-sr-box">
                <div style="
                    display:flex; justify-content:space-between; align-items:center;
                    margin-bottom:10px; padding-bottom:8px;
                    border-bottom:1px solid {t['border']};
                ">
                    <div style="font-size:12px; font-weight:bold; color:{t['primary']};">🎯 سطوح حمایت و مقاومت</div>
                    <div class="ty-sr-header-sub" style="font-size:9px; color:{t['fg_muted']};">📌 Pivot · 🔄 Swing</div>
                </div>
                <div>
                    <div style="font-size:9px; color:{t['red']}; margin-bottom:4px; font-weight:bold;">🔴 مقاومت‌ها</div>
                    {res_rows}
                    {price_row}
                    <div style="font-size:9px; color:{t['green']}; margin-top:6px; margin-bottom:4px; font-weight:bold;">🟢 حمایت‌ها</div>
                    {sup_rows}
                </div>
            </div>
        </div>
    </div>
    """

    _render(html)


# ═══════════════════════════════════════════════════════════
# نسخه مستقل S/R
# ═══════════════════════════════════════════════════════════
def render_sr_levels(analysis: dict, max_levels: int = 3) -> None:
    t = _t()
    if not analysis:
        return

    res_rows, price_row, sup_rows = _build_sr_rows(analysis, max_levels)

    _render(f"""
    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:14px; direction:rtl;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid {t['border']};">
            <div style="font-size:13px; font-weight:bold; color:{t['primary']};">🎯 سطوح حمایت و مقاومت</div>
            <div style="font-size:9px; color:{t['fg_muted']};">📌 Pivot · 🔄 Swing</div>
        </div>
        <div>
            <div style="font-size:10px; color:{t['red']}; margin-bottom:6px; font-weight:bold;">🔴 مقاومت‌ها</div>
            {res_rows}
            {price_row}
            <div style="font-size:10px; color:{t['green']}; margin-top:6px; margin-bottom:6px; font-weight:bold;">🟢 حمایت‌ها</div>
            {sup_rows}
        </div>
    </div>
    """)


# ═══════════════════════════════════════════════════════════
# جدول TF
# ═══════════════════════════════════════════════════════════
def render_tf_table(tfs_data: dict, sym_name: str, current_price: float) -> None:
    t = _t()
    if not tfs_data:
        return

    tf_order = ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"]
    tf_short = {
        "۵ دقیقه": "5m",
        "۱۵ دقیقه": "15m",
        "۳۰ دقیقه": "30m",
        "۱ ساعت": "1h",
        "روزانه": "1D",
    }

    price_str = f"${current_price:,.2f}" if current_price < 10000 else f"${current_price:,.0f}"

    _render(f'<div style="font-size:13px; font-weight:bold; color:{t["primary"]}; margin:16px 0 8px 0; padding-right:8px; border-right:3px solid {t["primary"]}; direction:rtl; text-align:right;">📊 تحلیل {sym_name} — قیمت فعلی: {price_str}</div>')

    rows = ""
    cards = ""

    for tf in tf_order:
        if tf not in tfs_data:
            continue
        a = tfs_data[tf]
        signal = a.get("signal", "—")
        confidence = a.get("confidence", 0)
        close_series = a.get("close_series", [])
        rsi = a.get("rsi", 50)
        adx = a.get("adx", 20)

        if "LONG" in signal:
            sig_text = "LONG"
            sig_color = t["green"]
            trend = "up"
        elif "SHORT" in signal:
            sig_text = "SHORT"
            sig_color = t["red"]
            trend = "down"
        else:
            sig_text = "خنثی"
            sig_color = t["fg_muted"]
            trend = "flat"

        if "LONG" in signal and confidence >= 70:
            expl_main = "🟢 فرصت خوبی برای خرید"
            expl_sub = "احتمال صعود قویه، با حد ضرر وارد شو"
        elif "LONG" in signal and confidence >= 50:
            expl_main = "🟢 خرید محتاطانه"
            expl_sub = "قیمت احتمالاً بالا می‌ره، کم وارد شو"
        elif "LONG" in signal:
            expl_main = "🟢 نشانه‌های صعود"
            expl_sub = "صبر کن، سیگنال ضعیفه"
        elif "SHORT" in signal and confidence >= 70:
            expl_main = "🔴 فرصت خوبی برای فروش"
            expl_sub = "احتمال نزول قویه، با حد ضرر وارد شو"
        elif "SHORT" in signal and confidence >= 50:
            expl_main = "🔴 فروش محتاطانه"
            expl_sub = "قیمت احتمالاً پایین می‌ره، کم وارد شو"
        elif "SHORT" in signal:
            expl_main = "🔴 نشانه‌های نزول"
            expl_sub = "صبر کن، سیگنال ضعیفه"
        else:
            if adx < 20:
                expl_main = "⚪ بازار رنج"
                expl_sub = "بدون روند واضح، صبر کن"
            elif rsi > 70:
                expl_main = "⚪ اشباع خرید"
                expl_sub = "احتمال اصلاح، وارد نشو"
            elif rsi < 30:
                expl_main = "⚪ اشباع فروش"
                expl_sub = "منتظر برگشت باش"
            else:
                expl_main = "⚪ بدون سیگنال"
                expl_sub = "وضعیت بازار نامشخصه"

        spark_color = t["green"] if "LONG" in signal else (t["red"] if "SHORT" in signal else t["fg_muted"])
        spark = sparkline_svg(close_series, spark_color, 65, 24, trend)

        rows += (
            f'<tr>'
            f'<td style="font-weight:bold; color:{t["primary"]}; text-align:right; font-family:Consolas;">{tf_short.get(tf, tf)}</td>'
            f'<td style="text-align:center;">{spark}</td>'
            f'<td style="text-align:center; color:{sig_color}; font-weight:bold; font-size:12px; font-family:Consolas;">{sig_text}</td>'
            f'<td style="font-size:11px; color:{t["fg"]}; text-align:right; line-height:1.6;">{expl_main}<br><span style="font-size:9px; color:{t["fg_muted"]};">{expl_sub}</span></td>'
            f'<td style="text-align:center; font-family:Consolas; color:{t["primary"]}; font-size:11px;">{confidence}%</td>'
            f'</tr>'
        )

        cards += (
            f'<div class="tf-card">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">'
            f'<div style="font-size:14px; font-weight:bold; color:{t["primary"]}; font-family:Consolas;">{tf_short.get(tf, tf)}</div>'
            f'<div style="font-size:12px; color:{sig_color}; font-weight:bold; font-family:Consolas;">{sig_text}</div>'
            f'<div style="text-align:center;">{spark}</div>'
            f'<div style="font-family:Consolas; font-size:11px; color:{t["primary"]};">{confidence}%</div>'
            f'</div>'
            f'<div style="font-size:11px; color:{t["fg"]}; text-align:right; margin-bottom:4px;">{expl_main}</div>'
            f'<div style="font-size:10px; color:{t["fg_muted"]}; text-align:right;">{expl_sub}</div>'
            f'</div>'
        )

    _render(f"""
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
    <div>{cards}</div>
    """)


# ═══════════════════════════════════════════════════════════
# تحلیل عمیق
# ═══════════════════════════════════════════════════════════
def render_deep_analysis(analysis_text: str, analysis_data: dict) -> None:
    t = _t()

    signal = analysis_data.get("signal", "خنثی") if analysis_data else "خنثی"
    confidence = analysis_data.get("confidence", 0) if analysis_data else 0

    if "LONG" in signal:
        final_decision = "🟢 پیشنهاد خرید"
        final_color = t["green"]
        decision_line = "با احتیاط وارد شو و حتماً حد ضرر بذار"
    elif "SHORT" in signal:
        final_decision = "🔴 پیشنهاد فروش"
        final_color = t["red"]
        decision_line = "محتاط باش، نوسان بالاست"
    else:
        final_decision = "⚪ صبر کن"
        final_color = t["fg_muted"]
        decision_line = "بدون سیگنال واضح — منتظر بمان"

    if "LONG" in signal and confidence > 70:
        low_risk_color = t["green"]
        low_risk_text = "✅ می‌تونی با احتیاط وارد شی — ۱٪ سرمایه"
    elif "LONG" in signal and confidence > 50:
        low_risk_color = t["yellow"]
        low_risk_text = "⚠️ صبر کن تا سیگنال قوی‌تر بشه"
    elif "SHORT" in signal and confidence > 70:
        low_risk_color = t["red"]
        low_risk_text = "⚠️ فروش پر‌ریسکه — بهتره صبر کنی"
    elif "SHORT" in signal:
        low_risk_color = t["red"]
        low_risk_text = "❌ فعلاً وارد نشو"
    else:
        low_risk_color = t["fg_muted"]
        low_risk_text = "⏸ صبر کن — بازار بی‌جهته"

    if "LONG" in signal:
        high_risk_color = t["green"]
        high_risk_text = "🚀 فرصت خرید — با حد ضرر و ۳-۵٪ سرمایه"
    elif "SHORT" in signal:
        high_risk_color = t["red"]
        high_risk_text = "🎯 فرصت فروش — با حد ضرر و ۳-۵٪ سرمایه"
    else:
        high_risk_color = t["yellow"]
        high_risk_text = "⏳ می‌تونی نوسان‌گیری کنی ولی محتاط باش"

    text_html = analysis_text.replace("\n", "<br>")
    text_html = text_html.replace("◈", f'<span style="color:{t["primary"]}; font-weight:bold;">◈</span>')
    text_html = text_html.replace("─" * 30, f'<span style="color:{t["border"]};">{"─" * 30}</span>')

    _render(f"""
    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:18px; direction:rtl; text-align:right;">
        <div style="background:{t['bg_mid']}; border-right:4px solid {final_color}; border-radius:8px; padding:12px 16px; margin-bottom:16px;">
            <div style="font-size:15px; font-weight:bold; color:{final_color}; margin-bottom:4px;">{final_decision}</div>
            <div style="font-size:11px; color:{t['fg']};">{decision_line}</div>
        </div>
        <div style="font-size:14px; font-weight:bold; color:{t['primary']}; margin-bottom:12px; padding-right:8px; border-right:3px solid {t['primary']};">
            📝 تحلیل عمیق
        </div>
        <div style="font-size:12px; line-height:2.2; color:{t['fg']}; direction:rtl; text-align:right; margin-bottom:16px;">
            {text_html}
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:14px; padding-top:14px; border-top:1px solid {t['border']};">
            <div style="background:{t['bg_mid']}; border-radius:8px; padding:12px; border-right:3px solid {low_risk_color};">
                <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:6px;">🛡 برای افراد کم‌ریسک</div>
                <div style="font-size:11px; color:{low_risk_color}; line-height:1.7; font-weight:bold;">{low_risk_text}</div>
            </div>
            <div style="background:{t['bg_mid']}; border-radius:8px; padding:12px; border-right:3px solid {high_risk_color};">
                <div style="font-size:10px; color:{t['fg_muted']}; margin-bottom:6px;">⚡ برای افراد پر‌ریسک</div>
                <div style="font-size:11px; color:{high_risk_color}; line-height:1.7; font-weight:bold;">{high_risk_text}</div>
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
        label, c, adv, icon = "طمع شدید", t["red"], "احتمال اصلاح بالاست، مراقب باش", "🔥"
    elif value >= 65:
        label, c, adv, icon = "طمع", t["orange"], "با احتیاط خرید کن", "😊"
    elif value >= 45:
        label, c, adv, icon = "خنثی", t["yellow"], "بازار متعادل، صبر کن", "😐"
    elif value >= 25:
        label, c, adv, icon = "ترس", t["green"], "فرصت خرید محتمل", "😟"
    else:
        label, c, adv, icon = "ترس شدید", t["green"], "فرصت قوی خرید", "😱"

    bar_width = int(value)

    _render(f"""
    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:16px; direction:rtl; text-align:right;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div style="font-size:12px; font-weight:bold; color:{t['fg']};">🌡 شاخص ترس و طمع</div>
            <div style="font-size:9px; color:{t['fg_muted']};">Fear & Greed</div>
        </div>
        <div style="display:flex; align-items:center; gap:14px;">
            <div style="text-align:center; min-width:80px;">
                <div style="font-size:32px; font-weight:bold; color:{c};">{value:.0f}</div>
                <div style="font-size:11px; color:{c}; font-weight:bold;">{icon} {label}</div>
            </div>
            <div style="flex:1;">
                <div style="background:{t['bg_mid']}; height:8px; border-radius:4px; overflow:hidden; margin-bottom:8px;">
                    <div style="background:linear-gradient(90deg, {t['green']}, {t['yellow']}, {t['red']}); height:100%; width:{bar_width}%; border-radius:4px;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:8px; color:{t['fg_dim']}; margin-bottom:8px; direction:rtl;">
                    <span>ترس شدید</span>
                    <span>خنثی</span>
                    <span>طمع شدید</span>
                </div>
                <div style="font-size:11px; color:{c}; font-weight:bold; margin-bottom:4px;">💡 {adv}</div>
                <div style="font-size:9px; color:{t['fg_muted']}; line-height:1.6;">
                    یعنی الان {value:.0f} از ۱۰۰ — {label}. {adv}.
                </div>
            </div>
        </div>
    </div>
    """)


# ═══════════════════════════════════════════════════════════
# تقویم
# ═══════════════════════════════════════════════════════════
def render_calendar(calendar_data: dict) -> None:
    t = _t()
    critical = calendar_data.get("critical", [])
    weekly = calendar_data.get("weekly", [])

    _render(f'<div style="font-size:13px; font-weight:bold; color:{t["primary"]}; margin:0 0 8px 0; padding-right:8px; border-right:3px solid {t["primary"]}; direction:rtl; text-align:right;">⚠️ رویدادهای مهم</div>')

    if critical:
        for ev in critical[:3]:
            date_str = ev["date"].strftime("%m-%d") if ev.get("date") else "?"
            _render(f"""
            <div style="background:rgba(248,113,113,0.08); border-right:3px solid {t['red']}; border-radius:8px; padding:12px; margin-bottom:8px; direction:rtl; text-align:right;">
                <div style="font-size:12px; color:{t['red']}; font-weight:bold; margin-bottom:8px;">
                    🔴 {date_str} • {ev['time']} | {ev['flag']} {ev['title_fa']}
                </div>
                {_impact_html(ev.get("market_impact", {}), t)}
            </div>
            """)
    else:
        _render(f'<div style="background:rgba(74,222,128,0.08); border-right:3px solid {t["green"]}; border-radius:6px; padding:10px 12px; color:{t["green"]}; font-size:11px; direction:rtl; text-align:right;">✅ رویداد بحرانی توی ۲۴ ساعت آینده نیست — بازار آرومه</div>')

    if weekly:
        _render(f'<div style="font-size:10px; color:{t["fg_muted"]}; margin:10px 0 6px 0; direction:rtl; text-align:right;">📅 هفته پیش‌رو ({len(weekly)} رویداد)</div>')
        items = ""
        for ev in weekly[:8]:
            date_str = ev["date"].strftime("%m-%d") if ev.get("date") else "?"
            icon = "🔴" if ev.get("impact") == "high" else "🟠"
            items += (
                f'<div style="background:{t["bg_mid"]}; border:1px solid {t["border"]}; border-radius:6px; padding:10px 12px; margin-bottom:6px; direction:rtl; text-align:right;">'
                f'<div style="font-size:11px; color:{t["fg"]}; font-weight:bold; margin-bottom:8px;">'
                f'{icon} {date_str} • {ev["time"]} | {ev["flag"]} {ev["title_fa"][:50]}</div>'
                f'{_impact_html(ev.get("market_impact", {}), t)}'
                f'</div>'
            )
        _render(f'<div style="max-height:400px; overflow-y:auto;">{items}</div>')


def _impact_html(impact: dict, t: dict) -> str:
    if not impact or not isinstance(impact, dict):
        return ""

    high_data = impact.get("high", {})
    low_data = impact.get("low", {})

    if not high_data and not low_data:
        return ""

    labels = {"gold": ("🥇", "طلا"), "dollar": ("💵", "دلار"),
              "crypto": ("₿", "کریپتو"), "oil": ("🛢", "نفت")}

    def render_row(data, prefix):
        items = []
        for key in ["gold", "dollar", "crypto", "oil"]:
            info = data.get(key)
            if not info:
                continue
            emoji, name = labels[key]
            color = t["green"] if info.get("dir") == "up" else (
                t["red"] if info.get("dir") == "down" else t["fg_muted"]
            )
            items.append(
                f'<span style="display:inline-block; padding:3px 10px; '
                f'background:{t["bg_card"]}; border-radius:6px; margin:2px; '
                f'font-size:10px; color:{color}; border:1px solid {color};">'
                f'{emoji} {name} {info.get("icon", "")} {info.get("label", "")}</span>'
            )
        return f'<div style="margin-bottom:6px; direction:rtl; text-align:right;">{prefix} {" ".join(items)}</div>'

    result = ""
    if high_data:
        result += render_row(
            high_data,
            f'<span style="font-size:10px; color:{t["green"]}; font-weight:bold;">⬆️ اگه بالاتر از انتظار بیاد:</span>'
        )
    if low_data:
        result += render_row(
            low_data,
            f'<span style="font-size:10px; color:{t["red"]}; font-weight:bold;">⬇️ اگه پایین‌تر از انتظار بیاد:</span>'
        )

    gold_high = high_data.get("gold", {})
    gold_low = low_data.get("gold", {})

    advice = ""
    if gold_high.get("dir") == "up" and gold_low.get("dir") == "down":
        advice = "💡 بالاتر از انتظار → طلا صعودی | پایین‌تر → طلا نزولی"
    elif gold_high.get("dir") == "down" and gold_low.get("dir") == "up":
        advice = "💡 بالاتر از انتظار → طلا نزولی | پایین‌تر → طلا صعودی"

    if advice:
        result += (
            f'<div style="margin-top:8px; padding:8px 12px; '
            f'background:rgba(245, 158, 11, 0.08); border-radius:6px; '
            f'border-right:3px solid {t["primary"]}; font-size:10px; '
            f'color:{t["primary"]}; font-weight:bold; direction:rtl; text-align:right; line-height:1.7;">'
            f'{advice}</div>'
        )

    return f'<div style="line-height:1.9;">{result}</div>'


# ═══════════════════════════════════════════════════════════
# اخبار
# ═══════════════════════════════════════════════════════════
def render_news(news_items: list) -> None:
    t = _t()
    _render(f'<div style="font-size:13px; font-weight:bold; color:{t["primary"]}; margin:0 0 8px 0; padding-right:8px; border-right:3px solid {t["primary"]}; direction:rtl; text-align:right;">📰 اخبار بازار</div>')
    if not news_items:
        _render(f'<div style="color:{t["fg_muted"]}; font-size:10px; direction:rtl; text-align:right;">در حال دریافت...</div>')
        return
    for item in news_items[:6]:
        source = item.get("source", "?")
        category = item.get("category", "")
        title = item.get("title", "")
        link = item.get("link", "")
        title_html = f'<a href="{link}" target="_blank" style="color:{t["fg"]}; text-decoration:none; font-size:11px; line-height:1.6;">{title}</a>' if link else f'<span style="font-size:11px; color:{t["fg"]};">{title}</span>'
        _render(f'<div style="background:{t["bg_card"]}; border:1px solid {t["border"]}; border-radius:6px; padding:8px 11px; margin-bottom:4px; direction:rtl; text-align:right;"><div style="font-size:9px; color:{t["cyan"]}; margin-bottom:3px;">[{source}] {category}</div><div>{title_html}</div></div>')


# ═══════════════════════════════════════════════════════════
# راستی‌آزمایی
# ═══════════════════════════════════════════════════════════
def render_backtest_stats(stats: dict, logs: list = None) -> None:
    t = _t()
    total = stats.get("total", 0)

    if total == 0:
        _render(f'<div style="color:{t["fg_muted"]}; font-size:11px; padding:16px; text-align:center; background:{t["bg_card"]}; border:1px dashed {t["border"]}; border-radius:8px; direction:rtl;">هنوز سیگنالی ثبت نشده.<br><span style="font-size:9px; color:{t["fg_dim"]};">به‌محض ثبت، خودکار راستی‌آزمایی می‌شود</span></div>')
        return

    win = stats.get("win", 0)
    loss = stats.get("loss", 0)
    pending = stats.get("pending", 0)
    wr = stats.get("win_rate", 0)
    pf = stats.get("profit_factor", 0)
    wr_c = t["green"] if wr >= 60 else (t["yellow"] if wr >= 40 else t["red"])
    pf_c = t["green"] if pf >= 1.5 else (t["yellow"] if pf >= 1.0 else t["red"])

    _render(f"""
    <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:14px; direction:rtl; text-align:right;">
        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; text-align:center;">
            <div><div style="font-size:9px; color:{t['fg_muted']};">کل</div><div style="font-family:Consolas; font-size:18px; color:{t['fg']}; font-weight:bold;">{total}</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">✅ برد</div><div style="font-family:Consolas; font-size:18px; color:{t['green']}; font-weight:bold;">{win}</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">❌ باخت</div><div style="font-family:Consolas; font-size:18px; color:{t['red']}; font-weight:bold;">{loss}</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">⏳ انتظار</div><div style="font-family:Consolas; font-size:18px; color:{t['yellow']}; font-weight:bold;">{pending}</div></div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; text-align:center; margin-top:12px; padding-top:12px; border-top:1px solid {t['border']};">
            <div><div style="font-size:9px; color:{t['fg_muted']};">نرخ برد</div><div style="font-family:Consolas; font-size:20px; color:{wr_c}; font-weight:bold;">{wr:.0f}%</div></div>
            <div><div style="font-size:9px; color:{t['fg_muted']};">Profit Factor</div><div style="font-family:Consolas; font-size:20px; color:{pf_c}; font-weight:bold;">{pf:.2f}</div></div>
        </div>
    </div>
    """)

    if logs:
        recent = logs[-10:] if len(logs) > 10 else logs
        recent = list(reversed(recent))

        _render(f'<div style="font-size:12px; font-weight:bold; color:{t["primary"]}; margin:14px 0 8px 0; direction:rtl; text-align:right;">📋 آخرین سیگنال‌های ثبت‌شده</div>')

        items = ""
        for entry in recent:
            try:
                sig_time = datetime.fromisoformat(entry["time"]).strftime("%m-%d %H:%M")
            except Exception:
                sig_time = "?"

            signal = entry.get("signal", "—")
            tf = entry.get("tf", "?")
            name = entry.get("name", "?")
            price = entry.get("price", 0)
            result = entry.get("result")

            if result is True:
                icon, c = "✅", t["green"]
            elif result is False:
                icon, c = "❌", t["red"]
            elif result == "neutral":
                icon, c = "➖", t["fg_muted"]
            else:
                icon, c = "⏳", t["yellow"]

            sig_icon = "🟢" if "LONG" in signal else ("🔴" if "SHORT" in signal else "⚪")
            short_name = name[:8] if len(name) > 8 else name

            items += (
                f'<div style="background:{t["bg_mid"]}; border:1px solid {t["border"]}; border-radius:6px; padding:8px 12px; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center; direction:rtl;">'
                f'<div style="display:flex; gap:8px; align-items:center;">'
                f'<span style="font-size:14px;">{icon}</span>'
                f'<span style="font-size:11px; color:{c}; font-weight:bold;">{sig_icon} {signal}</span>'
                f'<span style="font-size:11px; color:{t["fg"]};">{short_name}</span>'
                f'<span style="font-size:10px; color:{t["fg_muted"]};">{tf}</span>'
                f'</div>'
                f'<div style="text-align:left; direction:ltr;">'
                f'<span style="font-family:Consolas; font-size:11px; color:{t["fg"]};">${price:,.0f}</span>'
                f'<span style="font-size:9px; color:{t["fg_muted"]}; margin-left:8px;">{sig_time}</span>'
                f'</div>'
                f'</div>'
            )

        _render(f'<div style="max-height:300px; overflow-y:auto;">{items}</div>')


# ═══════════════════════════════════════════════════════════
# چک‌لیست
# ═══════════════════════════════════════════════════════════
def render_checklist(items: list, percentage: int, final_text: str, final_color: str) -> None:
    t = _t()
    st.progress(percentage / 100)
    _render(f'<div style="text-align:center; font-size:13px; font-weight:bold; color:{t.get(final_color, t["primary"])}; padding:10px; margin:10px 0; background:{t["bg_mid"]}; border-radius:8px; direction:rtl;">{final_text}</div>')
    for text, color_key, weight in items:
        _render(f'<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 12px; background:{t["bg_card"]}; border:1px solid {t["border"]}; border-radius:6px; margin-bottom:4px; font-size:12px; direction:rtl;"><span style="color:{t.get(color_key, t["fg"])};">{text}</span><span style="color:{t["fg_muted"]}; font-family:Consolas; font-size:10px;">({weight}%)</span></div>')


# ═══════════════════════════════════════════════════════════
# دکمه تاگل
# ═══════════════════════════════════════════════════════════
def render_section_toggle(
    key: str,
    label_on: str,
    label_off: str,
    icon_on: str = "📂",
    icon_off: str = "❌",
) -> bool:
    state_key = f"show_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    is_on = st.session_state[state_key]

    if is_on:
        label = f"{icon_off} {label_off}"
        btn_type = "primary"
    else:
        label = f"{icon_on} {label_on}"
        btn_type = "secondary"

    if st.button(
        label,
        key=f"btn_{key}",
        use_container_width=True,
        type=btn_type,
    ):
        st.session_state[state_key] = not is_on
        st.rerun()

    return st.session_state[state_key]

# ═══════════════════════════════════════════════════════════
# اسکنر فرصت‌ها — نسخه بازارمحور
# ═══════════════════════════════════════════════════════════
def render_scanner(
    scan_data: dict,
    filter_signal: str = "all",
    on_add_callback=None,
) -> None:
    """
    نمایش اسکنر فرصت‌ها با پشتیبانی از دکمه افزودن.

    Args:
        scan_data: dict از scan_markets()
        filter_signal: "all" | "long" | "short"
        on_add_callback: تابع callback برای افزودن نماد (ticker, name)
    """
    t = _t()

    top = scan_data.get("top", [])
    all_results = scan_data.get("all", [])
    timeframe = scan_data.get("timeframe", "")
    total_scanned = scan_data.get("total_scanned", 0)
    total_success = scan_data.get("total_success", 0)
    category_name = scan_data.get("category_name", "")
    category_icon = scan_data.get("category_icon", "📊")
    empty_message = scan_data.get("empty_message")

    # اگه بازار خالیه (مثل سهام ایران)
    if empty_message:
        _render(f"""
        <div style="background:{t['bg_card']}; border:1px dashed {t['border']}; border-radius:12px; padding:20px; text-align:center; color:{t['fg_muted']}; direction:rtl;">
            <div style="font-size:14px; margin-bottom:8px;">{category_icon} {category_name}</div>
            <div style="font-size:11px;">{empty_message}</div>
        </div>
        """)
        return

    if not all_results:
        _render(f"""
        <div style="background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:12px; padding:20px; text-align:center; color:{t['fg_muted']}; direction:rtl;">
            ⚠️ اسکنر نتونست هیچ نمادی از <b>{category_name}</b> رو تحلیل کنه.<br>
            <span style="font-size:10px;">داده‌ها در دسترس نیستن. بعداً امتحان کن.</span>
        </div>
        """)
        return

    # ─── فیلتر ───
    def passes_filter(item):
        sig = item.get("signal", "")
        if filter_signal == "long":
            return "LONG" in sig
        elif filter_signal == "short":
            return "SHORT" in sig
        return True

    filtered = [x for x in all_results if passes_filter(x)]
    filtered_top = filtered[0] if filtered else None

    # ─── هدر ───
    _render(f"""
    <div style="
        background:linear-gradient(135deg, {t['bg_card']}, {t['bg_mid']});
        border:1px solid {t['border']};
        border-radius:12px;
        padding:16px 20px;
        margin-bottom:14px;
        direction:rtl;
    ">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:22px;">🎯</span>
                <div>
                    <div style="font-size:15px; font-weight:bold; color:{t['primary']};">اسکنر فرصت‌ها — {category_icon} {category_name}</div>
                    <div style="font-size:10px; color:{t['fg_muted']}; margin-top:2px;">
                        تایم‌فریم: <b style="color:{t['cyan']};">{timeframe}</b> · 
                        {total_success}/{total_scanned} نماد اسکن شد
                    </div>
                </div>
            </div>
        </div>
    """)

    # ─── کارت Hero ───
    if filtered_top:
        item = filtered_top
        signal = item.get("signal", "خنثی")
        score = item.get("score", 0)
        confidence = item.get("confidence", 0)
        name = item.get("name", "")
        ticker = item.get("ticker", "")
        price = item.get("price", 0)
        rr = item.get("rr")

        if "LONG" in signal:
            color = t["green"]
            icon = "🟢"
            direction = "صعودی"
        elif "SHORT" in signal:
            color = t["red"]
            icon = "🔴"
            direction = "نزولی"
        else:
            color = t["fg_muted"]
            icon = "⚪"
            direction = "خنثی"

        if score >= 70:
            score_color = t["green"]
        elif score >= 50:
            score_color = t["yellow"]
        else:
            score_color = t["orange"]

        price_str = f"${price:,.2f}" if price < 10000 else f"${price:,.0f}"
        rr_str = f"{rr:.1f}" if rr else "—"

        # دکمه افزودن (فقط اگه callback داشته باشیم)
        add_btn_html = ""
        if on_add_callback:
            add_btn_html = (
                f'<div style="text-align:center;">'
                f'<span style="font-size:9px; color:{t["fg_muted"]};">افزودن به نمادها</span>'
                f'</div>'
            )

        _render(f"""
        <div style="
            background:{color}11;
            border:2px solid {color};
            border-radius:10px;
            padding:14px 16px;
            margin-bottom:14px;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:28px;">🥇</span>
                    <div>
                        <div style="font-size:9px; color:{t['fg_muted']};">بهترین فرصت این بازار</div>
                        <div style="font-size:16px; font-weight:bold; color:{t['fg']}; margin-top:2px;">
                            {name} <span style="font-size:11px; color:{t['fg_muted']};">({ticker})</span>
                        </div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:14px;">
                    <div style="text-align:center;">
                        <div style="font-size:9px; color:{t['fg_muted']};">سیگنال</div>
                        <div style="font-family:Consolas; font-size:14px; color:{color}; font-weight:bold;">{icon} {signal}</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:9px; color:{t['fg_muted']};">امتیاز</div>
                        <div style="font-family:Consolas; font-size:16px; color:{score_color}; font-weight:bold;">{score:.0f}</div>
                    </div>
                </div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px;">
                <div style="background:{t['bg_card']}; border-radius:6px; padding:8px; text-align:center;">
                    <div style="font-size:9px; color:{t['fg_muted']};">قیمت</div>
                    <div style="font-family:Consolas; font-size:12px; color:{t['fg']}; font-weight:bold; direction:ltr;">{price_str}</div>
                </div>
                <div style="background:{t['bg_card']}; border-radius:6px; padding:8px; text-align:center;">
                    <div style="font-size:9px; color:{t['fg_muted']};">اطمینان</div>
                    <div style="font-family:Consolas; font-size:12px; color:{t['primary']}; font-weight:bold;">{confidence}%</div>
                </div>
                <div style="background:{t['bg_card']}; border-radius:6px; padding:8px; text-align:center;">
                    <div style="font-size:9px; color:{t['fg_muted']};">R:R</div>
                    <div style="font-family:Consolas; font-size:12px; color:{t['cyan']}; font-weight:bold;">{rr_str}</div>
                </div>
            </div>
        </div>
        """)

    # ─── جدول ───
    if filtered:
        rows = ""
        for idx, item in enumerate(filtered[:10], 1):
            signal = item.get("signal", "خنثی")
            score = item.get("score", 0)
            name = item.get("name", "")
            ticker = item.get("ticker", "")
            price = item.get("price", 0)

            if "LONG" in signal:
                sig_color = t["green"]
                sig_icon = "🟢"
                sig_text = "LONG"
            elif "SHORT" in signal:
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

            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"{idx}."

            price_str = f"${price:,.2f}" if price < 10000 else f"${price:,.0f}"

            rows += (
                f'<tr>'
                f'<td style="text-align:center; font-size:14px; padding:8px;">{medal}</td>'
                f'<td style="text-align:right; font-size:12px; color:{t["fg"]}; font-weight:bold; padding:8px;">'
                f'{name} <span style="font-size:9px; color:{t["fg_muted"]};">({ticker})</span></td>'
                f'<td style="text-align:center; font-family:Consolas; font-size:11px; color:{sig_color}; font-weight:bold; padding:8px;">'
                f'{sig_icon} {sig_text}</td>'
                f'<td style="text-align:center; font-family:Consolas; font-size:11px; color:{t["fg"]}; direction:ltr; padding:8px;">{price_str}</td>'
                f'<td style="text-align:center; font-family:Consolas; font-size:12px; color:{score_color}; font-weight:bold; padding:8px;">{score:.0f}</td>'
                f'</tr>'
            )

        _render(f"""
        <table style="width:100%; border-collapse:separate; border-spacing:0; background:{t['bg_card']}; border-radius:10px; overflow:hidden; border:1px solid {t['border']}; direction:rtl; margin-bottom:8px;">
            <thead>
                <tr style="background:{t['bg_mid']};">
                    <th style="width:40px; padding:8px; font-size:10px; color:{t['fg_muted']}; text-align:center;">#</th>
                    <th style="padding:8px; font-size:10px; color:{t['fg_muted']}; text-align:right;">نماد</th>
                    <th style="width:90px; padding:8px; font-size:10px; color:{t['fg_muted']}; text-align:center;">سیگنال</th>
                    <th style="width:100px; padding:8px; font-size:10px; color:{t['fg_muted']}; text-align:center;">قیمت</th>
                    <th style="width:70px; padding:8px; font-size:10px; color:{t['fg_muted']}; text-align:center;">امتیاز</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """)

    _render("</div>")