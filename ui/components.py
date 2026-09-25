"""
ui/components.py
کامپوننت‌ها — نسخه ۲۱.۰ (نهایی)
هدر سه‌بخشی + ساعت زنده + Marquee پیوسته
"""

from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from ui.styles import get_theme


def _t() -> dict:
    return get_theme(st.session_state.get("theme", "dark"))


def _render(html: str) -> None:
    clean = "".join(line.strip() for line in html.split("\n"))
    st.markdown(clean, unsafe_allow_html=True)


def sparkline_svg(prices: list, color: str, width: int = 70, height: int = 26,
                  trend: str = "flat") -> str:
    """نمودار کوچیک با فلش جهت"""
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
# هدر یکپارچه سه بخشی
# ═══════════════════════════════════════════════════════════
def render_header(jalali: str, weekday: str, miladi: str) -> None:
    """
    هدر یکپارچه سه بخشی:
    - راست: لوگو TradeYar
    - وسط: ساعت زنده (با JavaScript)
    - چپ: تاریخ (۳ خط)
    """
    t = _t()

    # ─── بخش ۱: HTML ساختار هدر (سه بخش) ───
    header_html = f"""
    <div class="tradeyar-header">
        <!-- راست: لوگو -->
        <div class="header-left">
            <span style="font-size:32px; filter:drop-shadow(0 0 8px {t['primary']}); line-height:1;">🏆</span>
            <div>
                <div style="font-size:18px; font-weight:bold; color:{t['primary']}; line-height:1.2;">TradeYar</div>
                <div style="font-size:10px; color:{t['fg_muted']};">ترید‌یار ۲۰۲۶</div>
            </div>
        </div>

        <!-- وسط: ساعت زنده -->
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

        <!-- چپ: تاریخ -->
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

    # ─── بخش ۲: JavaScript برای ساعت (iframe نامرئی) ───
    clock_js = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
        #ty-clock-js {{
            position: fixed;
            top: 0;
            right: 0;
            font-family: Consolas, monospace;
            font-size: 22px;
            font-weight: bold;
            color: {t['cyan']};
            direction: ltr;
            letter-spacing: 1px;
            display: none;
        }}
    </style>
    </head>
    <body>
        <span id="ty-clock-js">--:--:--</span>
        <script>
        (function tick() {{
            var now = new Date();
            var utc = now.getTime() + (now.getTimezoneOffset() * 60000);
            var teh = new Date(utc + (3.5 * 3600000));
            var h = String(teh.getHours()).padStart(2, '0');
            var m = String(teh.getMinutes()).padStart(2, '0');
            var s = String(teh.getSeconds()).padStart(2, '0');
            var timeStr = h + ':' + m + ':' + s;

            // بروزرسانی عناصر در سند والد
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
# نوار بالایی — Marquee پیوسته
# ═══════════════════════════════════════════════════════════
def render_top_ticker(prices_data: list, markets_info: list) -> None:
    """
    نوار بالایی — ثابت راست‌چین.
    کاربر می‌تونه با ماوس/لمس اسکرول کنه.
    """
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

    # ─── محتوا بدون تکرار ───
    prices_html = "".join(render_price(p) for p in prices_data)
    markets_html = "".join(render_market(m) for m in markets_info)

    _render(f"""
    <div class="top-ticker">
        <!-- ردیف قیمت‌ها -->
        <div class="ticker-row-wrapper">
            <div class="ticker-track">{prices_html}</div>
        </div>
        <!-- ردیف بازارها -->
        <div class="ticker-row-wrapper" style="border-top:1px solid {t['border']}; margin-top:6px; padding-top:6px;">
            <div class="ticker-track">{markets_html}</div>
        </div>
    </div>
    """)
# ═══════════════════════════════════════════════════════════
# کارت سیگنال
# ═══════════════════════════════════════════════════════════
def render_main_signal(analysis: dict, sym_name: str, tf_name: str, tf_label: str = "") -> None:
    t = _t()

    if not analysis:
        _render(f'<div style="text-align:center; padding:20px; color:{t["fg_muted"]};">در حال محاسبه...</div>')
        return

    signal = analysis.get("signal", "خنثی")
    price = analysis.get("price", 0)
    confidence = analysis.get("confidence", 0)
    sl_tp = analysis.get("sl_tp")
    rr = analysis.get("rr")

    if "LONG" in signal:
        cls, icon, action = "long", "🟢", "مناسب برای خرید"
        short_advice = "قیمت احتمالاً بالا می‌ره. اگه ریسک‌پذیری، با حد ضرر وارد شو."
        decision_text = "تصمیم: بخر یا صبر کن"
        decision_color = t["green"]
    elif "SHORT" in signal:
        cls, icon, action = "short", "🔴", "مناسب برای فروش"
        short_advice = "قیمت احتمالاً پایین می‌ره. محتاط باش و حد ضرر بذار."
        decision_text = "تصمیم: بفروش یا صبر کن"
        decision_color = t["red"]
    else:
        cls, icon, action = "neutral", "⚪", "فعلاً نخر"
        short_advice = "بدون سیگنال واضح. صبر کن تا وضعیت روشن‌تر بشه."
        decision_text = "تصمیم: وارد نشو"
        decision_color = t["fg_muted"]

    if sl_tp:
        sl_str = f"${sl_tp.get('sl', 0):,.2f}" if price < 10000 else f"${sl_tp.get('sl', 0):,.0f}"
        tp_str = f"${sl_tp.get('tp', 0):,.2f}" if price < 10000 else f"${sl_tp.get('tp', 0):,.0f}"
        rr_str = f"{rr:.1f}" if rr else "—"
    else:
        sl_str = "بدون سیگنال"
        tp_str = "بدون سیگنال"
        rr_str = "—"

    price_str = f"${price:,.2f}" if price < 10000 else f"${price:,.0f}"

    _render(f"""
    <div class="signal-card {cls} fade-in">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <div style="font-size:10px; color:{t['fg_muted']};">سیگنال فعلی</div>
                <div style="font-size:18px; font-weight:bold; color:{t['fg']};">{sym_name}</div>
            </div>
            <div class="signal-badge {cls}">
                <div style="font-size:18px; line-height:1;">{icon}</div>
                <div style="font-size:13px; margin-top:2px;">{action}</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:9px; color:{t['fg_muted']};">اطمینان</div>
                <div style="font-size:22px; font-weight:bold; color:{t['primary']};">{confidence}%</div>
            </div>
        </div>

        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin-top:14px; padding-top:14px; border-top:1px solid {t['border']};">
            <div style="text-align:center;">
                <div style="font-size:9px; color:{t['fg_muted']};">ورود</div>
                <div style="font-family:Consolas; font-size:13px; color:{t['fg']}; direction:ltr; font-weight:bold;">{price_str}</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:9px; color:{t['fg_muted']};">حد ضرر</div>
                <div style="font-family:Consolas; font-size:12px; color:{t['red']}; direction:ltr;">{sl_str}</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:9px; color:{t['fg_muted']};">هدف سود</div>
                <div style="font-family:Consolas; font-size:12px; color:{t['green']}; direction:ltr;">{tp_str}</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:9px; color:{t['fg_muted']};">سود/ضرر</div>
                <div style="font-family:Consolas; font-size:13px; color:{t['cyan']};">{rr_str}</div>
            </div>
        </div>

        <div style="margin-top:14px; padding:12px 14px; background:{t['bg_mid']}; border-radius:8px; border-right:4px solid {decision_color}; direction:rtl; text-align:right;">
            <div style="font-size:12px; font-weight:bold; color:{decision_color}; margin-bottom:6px;">{decision_text}</div>
            <div style="font-size:11px; color:{t['fg']}; line-height:1.7;">{short_advice}</div>
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

        # جملات متنوع
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


def render_checklist(items: list, percentage: int, final_text: str, final_color: str) -> None:
    t = _t()
    st.progress(percentage / 100)
    _render(f'<div style="text-align:center; font-size:13px; font-weight:bold; color:{t.get(final_color, t["primary"])}; padding:10px; margin:10px 0; background:{t["bg_mid"]}; border-radius:8px; direction:rtl;">{final_text}</div>')
    for text, color_key, weight in items:
        _render(f'<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 12px; background:{t["bg_card"]}; border:1px solid {t["border"]}; border-radius:6px; margin-bottom:4px; font-size:12px; direction:rtl;"><span style="color:{t.get(color_key, t["fg"])};">{text}</span><span style="color:{t["fg_muted"]}; font-family:Consolas; font-size:10px;">({weight}%)</span></div>')