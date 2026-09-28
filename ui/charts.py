"""
ui/charts.py
نمودارهای Plotly تعاملی
نسخه ۱.۰ — چند-مارکتی + RTL + تم تاریک/روشن
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.styles import get_theme


# ═══════════════════════════════════════════════════════════
# ابزار کمکی: دریافت تم فعلی
# ═══════════════════════════════════════════════════════════
def _get_current_theme() -> dict:
    """تم فعلی رو از session_state می‌خونه"""
    try:
        import streamlit as st
        theme_name = st.session_state.get("theme", "dark")
    except Exception:
        theme_name = "dark"
    return get_theme(theme_name)


# ═══════════════════════════════════════════════════════════
# تنظیمات عمومی Plotly
# ═══════════════════════════════════════════════════════════
def _apply_layout(fig: go.Figure, title: str = "", height: int = 700) -> None:
    """اعمال تنظیمات ظاهری مشترک"""
    t = _get_current_theme()

    fig.update_layout(
        title={
            "text": title,
            "font": {"size": 16, "color": t["fg"], "family": "Tahoma"},
            "x": 0.5,
            "xanchor": "center",
        },
        height=height,
        paper_bgcolor=t["bg_card"],
        plot_bgcolor=t["bg"],
        font={"color": t["fg"], "family": "Tahoma"},
        margin={"l": 50, "r": 30, "t": 60, "b": 40},
        hovermode="x unified",
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "bgcolor": t["bg_mid"],
            "bordercolor": t["border"],
            "borderwidth": 1,
            "font": {"color": t["fg"], "size": 11},
        },
    )

    # استایل محورها
    fig.update_xaxes(
        gridcolor=t["border"],
        linecolor=t["border"],
        showgrid=True,
        zeroline=False,
        tickfont={"color": t["fg_muted"], "size": 10},
    )
    fig.update_yaxes(
        gridcolor=t["border"],
        linecolor=t["border"],
        showgrid=True,
        zeroline=False,
        tickfont={"color": t["fg_muted"], "size": 10},
    )


# ═══════════════════════════════════════════════════════════
# ۱. چارت کندل استیک ساده
# ═══════════════════════════════════════════════════════════
def render_candlestick(
    df: pd.DataFrame,
    title: str = "",
    show_ema200: bool = True,
    show_vwap: bool = True,
    show_sl_tp: dict | None = None,
    show_sr: dict | None = None,
    n_candles: int = 200,
    height: int = 500,
) -> go.Figure:
    """
    ساخت نمودار کندل استیک با اندیکاتورها.
    
    Args:
        df: دیتافریم با ستون‌های open, high, low, close, volume
            و اختیاری: ema200, vwap
        title: عنوان چارت
        show_ema200: نمایش EMA200
        show_vwap: نمایش VWAP
        show_sl_tp: dict {"sl": 4272, "tp": 4297, "type": "LONG"}
        show_sr: dict {"support": 4270, "resistance": 4290}
        n_candles: تعداد کندل‌های نمایش
        height: ارتفاع چارت
    
    Returns:
        Figure plotly
    """
    t = _get_current_theme()

    # فقط N کندل آخر
    plot_df = df.tail(n_candles).copy()

    fig = go.Figure()

    # ─── کندل استیک ───
    fig.add_trace(
        go.Candlestick(
            x=plot_df.index,
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            name="قیمت",
            increasing=dict(line=dict(color=t["green"], width=1),
                            fillcolor=t["green"]),
            decreasing=dict(line=dict(color=t["red"], width=1),
                            fillcolor=t["red"]),
        )
    )

    # ─── EMA200 ───
    if show_ema200 and "ema200" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["ema200"],
                mode="lines",
                name="EMA200",
                line=dict(color=t["cyan"], width=1.5),
            )
        )

    # ─── VWAP ───
    if show_vwap and "vwap" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["vwap"],
                mode="lines",
                name="VWAP",
                line=dict(color=t["purple"], width=1.5, dash="dot"),
            )
        )

    # ─── سطوح حمایت/مقاومت ───
    if show_sr:
        support = show_sr.get("support")
        resistance = show_sr.get("resistance")
        if support and support > 0:
            fig.add_hline(
                y=support,
                line=dict(color=t["green"], width=1, dash="dash"),
                annotation_text=f"حمایت {support:,.0f}",
                annotation_position="right",
                annotation_font_color=t["green"],
            )
        if resistance and resistance > 0:
            fig.add_hline(
                y=resistance,
                line=dict(color=t["yellow"], width=1, dash="dash"),
                annotation_text=f"مقاومت {resistance:,.0f}",
                annotation_position="right",
                annotation_font_color=t["yellow"],
            )

    # ─── خطوط SL/TP ───
    if show_sl_tp:
        sl = show_sl_tp.get("sl")
        tp = show_sl_tp.get("tp")
        if sl and sl > 0:
            fig.add_hline(
                y=sl,
                line=dict(color=t["red"], width=2, dash="dot"),
                annotation_text=f"حد ضرر {sl:,.2f}",
                annotation_position="right",
                annotation_font_color=t["red"],
            )
        if tp and tp > 0:
            fig.add_hline(
                y=tp,
                line=dict(color=t["green"], width=2, dash="dot"),
                annotation_text=f"هدف {tp:,.2f}",
                annotation_position="right",
                annotation_font_color=t["green"],
            )

    _apply_layout(fig, title, height=height)
    fig.update_layout(xaxis_rangeslider_visible=False)

    return fig


# ═══════════════════════════════════════════════════════════
# ۲. چارت کامل سه‌طبقه (کندل + RSI + MACD)
# ═══════════════════════════════════════════════════════════
def render_full_chart(
    df: pd.DataFrame,
    title: str = "",
    show_sl_tp: dict | None = None,
    show_sr: dict | None = None,
    n_candles: int = 200,
    height: int = 850,
) -> go.Figure:
    """
    ساخت چارت سه‌طبقه: کندل + RSI + MACD.
    
    Args:
        df: دیتافریم با ستون‌های open, high, low, close, volume
            و اختیاری: ema200, vwap, rsi, macd_hist
        title: عنوان
        show_sl_tp: dict SL/TP
        show_sr: dict S/R
        n_candles: تعداد کندل
        height: ارتفاع کل
    
    Returns:
        Figure plotly
    """
    t = _get_current_theme()

    plot_df = df.tail(n_candles).copy()

    # چارت سه‌طبقه
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("قیمت", "RSI", "MACD"),
    )

    # ─── طبقه ۱: کندل استیک ───
    fig.add_trace(
        go.Candlestick(
            x=plot_df.index,
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            name="قیمت",
            increasing=dict(line=dict(color=t["green"], width=1),
                            fillcolor=t["green"]),
            decreasing=dict(line=dict(color=t["red"], width=1),
                            fillcolor=t["red"]),
        ),
        row=1, col=1,
    )

    # EMA200
    if "ema200" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["ema200"],
                mode="lines", name="EMA200",
                line=dict(color=t["cyan"], width=1.5),
            ),
            row=1, col=1,
        )

    # VWAP
    if "vwap" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["vwap"],
                mode="lines", name="VWAP",
                line=dict(color=t["purple"], width=1.5, dash="dot"),
            ),
            row=1, col=1,
        )

    # S/R
    if show_sr:
        if show_sr.get("support", 0) > 0:
            fig.add_hline(
                y=show_sr["support"], row=1, col=1,
                line=dict(color=t["green"], width=1, dash="dash"),
            )
        if show_sr.get("resistance", 0) > 0:
            fig.add_hline(
                y=show_sr["resistance"], row=1, col=1,
                line=dict(color=t["yellow"], width=1, dash="dash"),
            )

    # SL/TP
    if show_sl_tp:
        if show_sl_tp.get("sl", 0) > 0:
            fig.add_hline(
                y=show_sl_tp["sl"], row=1, col=1,
                line=dict(color=t["red"], width=2, dash="dot"),
                annotation_text=f"SL {show_sl_tp['sl']:,.2f}",
                annotation_position="right",
                annotation_font_color=t["red"],
            )
        if show_sl_tp.get("tp", 0) > 0:
            fig.add_hline(
                y=show_sl_tp["tp"], row=1, col=1,
                line=dict(color=t["green"], width=2, dash="dot"),
                annotation_text=f"TP {show_sl_tp['tp']:,.2f}",
                annotation_position="right",
                annotation_font_color=t["green"],
            )

    # ─── طبقه ۲: RSI ───
    if "rsi" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["rsi"],
                mode="lines", name="RSI",
                line=dict(color=t["primary"], width=1.5),
            ),
            row=2, col=1,
        )

        # خطوط 30/70
        fig.add_hline(
            y=70, row=2, col=1,
            line=dict(color=t["red"], width=1, dash="dash"),
            annotation_text="70", annotation_position="right",
            annotation_font_color=t["red"],
        )
        fig.add_hline(
            y=30, row=2, col=1,
            line=dict(color=t["green"], width=1, dash="dash"),
            annotation_text="30", annotation_position="right",
            annotation_font_color=t["green"],
        )

        fig.update_yaxes(range=[0, 100], row=2, col=1)

    # ─── طبقه ۳: MACD ───
    if "macd_hist" in plot_df.columns:
        colors = [
            t["green"] if v > 0 else t["red"]
            for v in plot_df["macd_hist"].fillna(0)
        ]

        fig.add_trace(
            go.Bar(
                x=plot_df.index, y=plot_df["macd_hist"],
                name="MACD Hist",
                marker_color=colors,
                opacity=0.7,
            ),
            row=3, col=1,
        )

    # تنظیمات کلی
    _apply_layout(fig, title, height=height)
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        showlegend=True,
    )

    # استایل عنوان‌های زیرنویس
    for annotation in fig.layout.annotations[:3]:
        annotation.font.color = t["fg_muted"]
        annotation.font.size = 12

    return fig


# ═══════════════════════════════════════════════════════════
# ۳. نمودار RSI تنها
# ═══════════════════════════════════════════════════════════
def render_rsi_chart(
    df: pd.DataFrame,
    title: str = "RSI",
    n_candles: int = 200,
    height: int = 250,
) -> go.Figure:
    """نمودار RSI تنها"""
    t = _get_current_theme()
    plot_df = df.tail(n_candles).copy()

    fig = go.Figure()
    if "rsi" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["rsi"],
                mode="lines", name="RSI",
                line=dict(color=t["primary"], width=2),
                fill="tozeroy",
                fillcolor=f"rgba(245, 158, 11, 0.1)",
            )
        )

    fig.add_hline(y=70, line=dict(color=t["red"], width=1, dash="dash"))
    fig.add_hline(y=30, line=dict(color=t["green"], width=1, dash="dash"))
    fig.update_yaxes(range=[0, 100])

    _apply_layout(fig, title, height=height)
    return fig


# ═══════════════════════════════════════════════════════════
# ۴. نمودار MACD تنها
# ═══════════════════════════════════════════════════════════
def render_macd_chart(
    df: pd.DataFrame,
    title: str = "MACD",
    n_candles: int = 200,
    height: int = 250,
) -> go.Figure:
    """نمودار MACD با هیستوگرام"""
    t = _get_current_theme()
    plot_df = df.tail(n_candles).copy()

    fig = go.Figure()
    if "macd_hist" in plot_df.columns:
        colors = [
            t["green"] if v > 0 else t["red"]
            for v in plot_df["macd_hist"].fillna(0)
        ]
        fig.add_trace(
            go.Bar(
                x=plot_df.index, y=plot_df["macd_hist"],
                name="MACD Hist", marker_color=colors, opacity=0.7,
            )
        )

    _apply_layout(fig, title, height=height)
    return fig


# ═══════════════════════════════════════════════════════════
# ۵. نمودار حجم
# ═══════════════════════════════════════════════════════════
def render_volume_chart(
    df: pd.DataFrame,
    title: str = "حجم معاملات",
    n_candles: int = 200,
    height: int = 200,
) -> go.Figure:
    """نمودار حجم معاملات"""
    t = _get_current_theme()
    plot_df = df.tail(n_candles).copy()

    if "volume" not in plot_df.columns:
        return go.Figure()

    # رنگ بر اساس کندل صعودی/نزولی
    colors = [
        t["green"] if c >= o else t["red"]
        for c, o in zip(plot_df["close"], plot_df["open"])
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=plot_df.index,
            y=plot_df["volume"],
            name="حجم",
            marker_color=colors,
            opacity=0.7,
        )
    )

    _apply_layout(fig, title, height=height)
    return fig


# ═══════════════════════════════════════════════════════════
# ۶. نمودار Sparkline (برای کارت‌های قیمت)
# ═══════════════════════════════════════════════════════════
def render_sparkline(
    prices: list,
    is_up: bool = True,
    height: int = 60,
) -> go.Figure:
    """
    نمودار Sparkline کوچک برای کارت‌ها.
    
    Args:
        prices: لیست قیمت‌ها
        is_up: صعودی یا نزولی (برای رنگ)
        height: ارتفاع
    """
    t = _get_current_theme()
    color = t["green"] if is_up else t["red"]
    fill_color = "rgba(34, 197, 94, 0.1)" if is_up else "rgba(239, 68, 68, 0.1)"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            y=prices,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=fill_color,
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    return fig

# ═══════════════════════════════════════════════════════════
# ۷. نشانگر Fear & Greed
# ═══════════════════════════════════════════════════════════
def render_fear_greed_gauge(
    value: float,
    height: int = 300,
) -> go.Figure:
    """
    نشانگر Fear & Greed به صورت Gauge.
    
    Args:
        value: مقدار 0-100
        height: ارتفاع
    """
    t = _get_current_theme()

    # رنگ بر اساس مقدار
    if value >= 75:
        color = t["red"]
        label = "طمع شدید"
    elif value >= 60:
        color = t["orange"]
        label = "طمع"
    elif value >= 40:
        color = t["yellow"]
        label = "خنثی"
    elif value >= 25:
        color = t["green"]
        label = "ترس"
    else:
        color = t["green"]
        label = "ترس شدید"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": f"شاخص ترس و طمع<br>{label}",
                   "font": {"size": 14, "color": t["fg"]}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": t["fg_muted"],
                },
                "bar": {"color": color, "thickness": 0.3},
                "bgcolor": t["bg_card"],
                "borderwidth": 2,
                "bordercolor": t["border"],
                "steps": [
                    {"range": [0, 25], "color": "rgba(34, 197, 94, 0.2)"},
                    {"range": [25, 45], "color": "rgba(234, 179, 8, 0.2)"},
                    {"range": [45, 55], "color": "rgba(139, 139, 149, 0.2)"},
                    {"range": [55, 75], "color": "rgba(249, 115, 22, 0.2)"},
                    {"range": [75, 100], "color": "rgba(239, 68, 68, 0.2)"},
                ],
                "threshold": {
                    "line": {"color": t["fg"], "width": 2},
                    "thickness": 0.75,
                    "value": value,
                },
            },
        )
    )

    fig.update_layout(
        height=height,
        paper_bgcolor=t["bg_card"],
        font={"color": t["fg"]},
        margin=dict(l=20, r=20, t=60, b=20),
    )

    return fig


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("تست ui/charts.py")
    print("=" * 60)
    print()

    print("توابع نمودار:")
    funcs = [
        ("render_candlestick", "کندل استیک ساده با EMA200/VWAP/SL-TP"),
        ("render_full_chart", "چارت سه‌طبقه (کندل + RSI + MACD)"),
        ("render_rsi_chart", "نمودار RSI تنها"),
        ("render_macd_chart", "نمودار MACD"),
        ("render_volume_chart", "نمودار حجم"),
        ("render_sparkline", "Sparkline برای کارت‌ها"),
        ("render_fear_greed_gauge", "نشانگر ترس و طمع"),
    ]

    for name, desc in funcs:
        print(f"  ✅ {name}() — {desc}")

    print()
    print("[OK] تست کامل شد — برای تست واقعی با داده yfinance استفاده شود.")
    print()
    print("نمونه:")
    print("  from core.data_fetcher import fetch_history")
    print("  from ui.charts import render_full_chart")
    print("  df = fetch_history('GC=F', '1h', '3mo')")
    print("  fig = render_full_chart(df, title='طلا — ۱ ساعت')")
    print("  fig.show()")