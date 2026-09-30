"""
ui/styles.py
پالت رنگ + CSS — نسخه ۱۶.۰ (فاز ۵)
============================================================
تغییرات نسخه ۱۶.۰:
  - THEME_LIGHT با رنگ‌های صریح‌تر (رفع مشکل دید)
  - FAB (Floating Action Button) برای برگشت به بالا
  - Skeleton Loader برای بارگذاری
  - تابع render_back_to_top_fab
  - رفع باگ header (دکمه sidebar)
  - بهبود کنتراست تم روشن
"""

from pathlib import Path
from typing import Optional

FONT_DIR = Path(__file__).parent.parent / "fonts"
FONT_DIR.mkdir(exist_ok=True)

B64_FILE = FONT_DIR / "IRANYekanXVF.b64.txt"
LOGO_B64_FILE = FONT_DIR / "logo.b64.txt"


# ═══════════════════════════════════════════════════════════
# بارگذاری فایل‌ها
# ═══════════════════════════════════════════════════════════
def _load_file_base64(path: Path) -> str:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"[Styles] خطا در خواندن {path}: {e}")
    return ""


_FONT_B64 = _load_file_base64(B64_FILE)
_LOGO_B64 = _load_file_base64(LOGO_B64_FILE)


def get_logo_base64() -> str:
    """دریافت لوگو Base64"""
    return _LOGO_B64


# ═══════════════════════════════════════════════════════════
# تم تاریک
# ═══════════════════════════════════════════════════════════
THEME_DARK = {
    "name": "تاریک",
    "bg": "#0A0E1A",
    "bg_dark": "#060912",
    "bg_card": "#131B2E",
    "bg_card_hover": "#1A2540",
    "bg_mid": "#1B2744",
    "bg_input": "#0F1628",
    "border": "#1F2D4D",
    "border_light": "#2F4270",
    "border_glow": "rgba(59, 130, 246, 0.4)",
    "fg": "#E8EEF9",
    "fg_muted": "#9AABCB",
    "fg_dim": "#6B7DA0",
    "primary": "#3B82F6",
    "primary_dark": "#2563EB",
    "primary_glow": "rgba(59, 130, 246, 0.25)",
    "cyan": "#22D3EE",
    "cyan_dark": "#0891B2",
    "cyan_glow": "rgba(34, 211, 238, 0.25)",
    "green": "#10B981",
    "green_dark": "#059669",
    "green_glow": "rgba(16, 185, 129, 0.25)",
    "red": "#EF4444",
    "red_dark": "#DC2626",
    "red_glow": "rgba(239, 68, 68, 0.25)",
    "yellow": "#EAB308",
    "orange": "#F97316",
    "purple": "#A855F7",
    "purple_glow": "rgba(168, 85, 247, 0.25)",
    "gold": "#F0B90B",
    "nobitex": "#A855F7",
    "abantether": "#3B82F6",
    "tsetmc": "#10B981",
}


# ═══════════════════════════════════════════════════════════
# تم روشن — نسخه بهبودیافته
# ═══════════════════════════════════════════════════════════
THEME_LIGHT = {
    "name": "روشن",
    "bg": "#F0F4F8",
    "bg_dark": "#E2E8F0",
    "bg_card": "#FFFFFF",
    "bg_card_hover": "#F7FAFC",
    "bg_mid": "#EBF1F8",
    "bg_input": "#FFFFFF",
    "border": "#CBD5E1",
    "border_light": "#94A3B8",
    "border_glow": "rgba(30, 64, 175, 0.2)",
    "fg": "#0F172A",
    "fg_muted": "#475569",
    "fg_dim": "#64748B",
    "primary": "#1E40AF",
    "primary_dark": "#1E3A8A",
    "primary_glow": "rgba(30, 64, 175, 0.2)",
    "cyan": "#0891B2",
    "cyan_dark": "#0E7490",
    "cyan_glow": "rgba(8, 145, 178, 0.15)",
    "green": "#059669",
    "green_dark": "#047857",
    "green_glow": "rgba(5, 150, 105, 0.15)",
    "red": "#DC2626",
    "red_dark": "#B91C1C",
    "red_glow": "rgba(220, 38, 38, 0.15)",
    "yellow": "#CA8A04",
    "orange": "#EA580C",
    "purple": "#7C3AED",
    "purple_glow": "rgba(124, 58, 237, 0.15)",
    "gold": "#B45309",
    "nobitex": "#7C3AED",
    "abantether": "#2563EB",
    "tsetmc": "#059669",
}


def get_theme(name: str = "dark") -> dict:
    """دریافت تم بر اساس نام"""
    return THEME_DARK if name == "dark" else THEME_LIGHT


# ═══════════════════════════════════════════════════════════
# CSS کامل
# ═══════════════════════════════════════════════════════════
def get_custom_css(theme_name: str = "dark") -> str:
    """تولید CSS سراسری بر اساس تم"""
    t = get_theme(theme_name)
    is_light = theme_name == "light"
    card_shadow = (
        "0 1px 4px rgba(15, 23, 42, 0.08)"
        if is_light
        else "0 2px 10px rgba(0, 0, 0, 0.3)"
    )

    # ─── فونت ───
    if _FONT_B64:
        font_face = f"""
        @font-face {{
            font-family: 'IRANYekanX';
            src: url('data:font/woff2;base64,{_FONT_B64}') format('woff2-variations');
            font-weight: 100 900;
            font-style: normal;
            font-display: swap;
        }}
        """
    else:
        font_face = (
            "@import url('https://cdn.jsdelivr.net/gh/rastikerdar/"
            "vazirmatn@v33.003/Vazirmatn-font-face.css');"
        )

    return f"""
    <style>
    {font_face}
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    * {{
        box-sizing: border-box;
        font-family: 'IRANYekanX', 'Vazirmatn', 'Tahoma', system-ui, sans-serif;
    }}

    code, .mono, [style*="Consolas"], [style*="monospace"] {{
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    }}

    html, body, [class*="css"], .stApp {{
        direction: rtl !important;
        text-align: right !important;
        background-color: {t['bg']} !important;
        color: {t['fg']} !important;
        font-family: 'IRANYekanX', 'Vazirmatn', 'Tahoma', sans-serif !important;
    }}

    .main .block-container {{
        padding: 1rem 1.5rem !important;
        max-width: 100% !important;
    }}

    /* ═══ رفع باگ: فقط MainMenu و footer، نه header ═══ */
    #MainMenu {{
        visibility: hidden;
    }}
    footer {{
        visibility: hidden;
    }}
    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 0 !important;
    }}
    button[data-testid="baseButton-headerNoPadding"] {{
        visibility: visible !important;
        display: flex !important;
    }}

    div[data-testid="stMarkdownContainer"],
    div[data-testid="stMarkdownContainer"] > p,
    div[data-testid="stMarkdownContainer"] > div,
    div[data-testid="stMarkdownContainer"] > span,
    label,
    .stRadio > label,
    .stSelectbox > label,
    .stTextInput > label,
    h1, h2, h3, h4, h5, h6 {{
        direction: rtl !important;
        text-align: right !important;
    }}

    div[role="radiogroup"] {{
        direction: rtl !important;
        justify-content: flex-start !important;
    }}

    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] > div > div {{
        direction: rtl !important;
        text-align: right !important;
    }}

    /* ═══════════════════════════════════════════════════════
       انیمیشن‌ها
       ═══════════════════════════════════════════════════════ */
    @keyframes pulse-glow {{
        0%, 100% {{
            box-shadow: 0 0 0 0 {t['primary_glow']};
            transform: scale(1);
        }}
        50% {{
            box-shadow: 0 0 16px 6px {t['primary_glow']};
            transform: scale(1.01);
        }}
    }}

    @keyframes fade-in {{
        from {{ opacity: 0; transform: translateY(4px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes slide-up {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes live-pulse {{
        0% {{
            box-shadow: 0 0 0 0 {t['green']}CC;
            transform: scale(1);
            opacity: 1;
        }}
        70% {{
            box-shadow: 0 0 0 8px {t['green']}00;
            transform: scale(1.4);
            opacity: 0.6;
        }}
        100% {{
            box-shadow: 0 0 0 0 {t['green']}00;
            transform: scale(1);
            opacity: 1;
        }}
    }}

    .live-pulse-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: {t['green']};
        animation: live-pulse 2s infinite;
        vertical-align: middle;
    }}

    .live-pulse-dot.large {{
        width: 10px;
        height: 10px;
    }}

    /* ═══════════════════════════════════════════════════════
       هدر
       ═══════════════════════════════════════════════════════ */
    .trademun-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 14px;
        padding: 12px 20px;
        margin-bottom: 12px;
        gap: 12px;
        width: 100%;
        min-height: 70px;
        box-shadow: {card_shadow};
        animation: fade-in 0.3s ease;
    }}

    .header-left {{
        display: flex;
        align-items: center;
        gap: 10px;
        flex: 1 1 0;
        min-width: 0;
    }}

    .header-logo {{
        width: 60px;
        height: 60px;
        object-fit: contain;
        border-radius: 10px;
        filter: drop-shadow(0 0 6px {t['primary_glow']});
    }}

    .header-brand {{
        display: flex;
        flex-direction: column;
        gap: 2px;
    }}

    .header-brand-fa {{
        font-size: 17px;
        font-weight: 700;
        color: {t['fg']};
        line-height: 1.2;
    }}

    .header-brand-en {{
        font-size: 10px;
        color: {t['fg_muted']};
        direction: ltr;
        text-align: left;
    }}

    .header-center {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        flex: 1 1 0;
        min-width: 0;
    }}

    .header-right {{
        display: flex;
        align-items: center;
        justify-content: flex-end;
        flex: 1 1 0;
        min-width: 0;
    }}

    .live-dot {{
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: {t['green']};
        box-shadow: 0 0 8px {t['green']};
        animation: live-pulse 2s infinite;
    }}

    /* ═══════════════════════════════════════════════════════
       تیکر
       ═══════════════════════════════════════════════════════ */
    .top-ticker {{
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 6px 0;
        margin-bottom: 12px;
        overflow: hidden;
        box-shadow: {card_shadow};
    }}

    .ticker-row-wrapper {{
        display: flex;
        overflow-x: auto;
        overflow-y: hidden;
        width: 100%;
        direction: rtl;
        scroll-behavior: smooth;
    }}

    .ticker-row-wrapper::-webkit-scrollbar {{ height: 3px; }}
    .ticker-row-wrapper::-webkit-scrollbar-track {{ background: {t['bg_dark']}; }}
    .ticker-row-wrapper::-webkit-scrollbar-thumb {{
        background: {t['border_light']};
        border-radius: 2px;
    }}

    .ticker-track {{
        display: inline-flex;
        gap: 0;
        align-items: center;
        white-space: nowrap;
        flex-shrink: 0;
    }}

    .ticker-item {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        white-space: nowrap;
        padding: 4px 12px;
        font-size: 12px;
        flex-shrink: 0;
        font-family: 'IRANYekanX', 'Vazirmatn', sans-serif;
    }}

    /* ═══════════════════════════════════════════════════════
       دکمه‌ها
       ═══════════════════════════════════════════════════════ */
    .stButton > button {{
        background: {t['bg_card']};
        color: {t['fg']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 8px 14px;
        font-family: 'IRANYekanX', 'Vazirmatn', sans-serif;
        font-weight: 600;
        font-size: 12px;
        transition: all 0.2s ease;
        box-shadow: {card_shadow};
    }}

    .stButton > button:hover {{
        background: {t['bg_card_hover']};
        border-color: {t['primary']};
        transform: translateY(-1px);
        box-shadow: 0 4px 12px {t['primary_glow']};
    }}

    .stButton > button[kind="primary"] {{
        background: {t['primary']};
        color: #ffffff;
        border-color: {t['primary_dark']};
        font-weight: 700;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: {t['primary_dark']};
        box-shadow: 0 3px 10px {t['primary_glow']};
    }}

    /* ═══════════════════════════════════════════════════════
       ورودی‌ها
       ═══════════════════════════════════════════════════════ */
    .stSelectbox > div > div,
    .stTextInput > div > div {{
        background: {t['bg_input']} !important;
        border-color: {t['border']} !important;
        color: {t['fg']} !important;
        border-radius: 10px !important;
    }}

    .stTextInput input {{
        background: {t['bg_input']} !important;
        color: {t['fg']} !important;
        font-family: 'IRANYekanX', 'Vazirmatn', sans-serif !important;
        font-size: 13px !important;
    }}

    div[data-testid="InputInstructions"] {{
        display: none !important;
    }}

    /* ═══════════════════════════════════════════════════════
       Radio
       ═══════════════════════════════════════════════════════ */
    div[role="radiogroup"] {{
        display: flex !important;
        flex-direction: row !important;
        gap: 6px !important;
        flex-wrap: wrap !important;
    }}

    div[role="radiogroup"] > label {{
        background: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 10px !important;
        padding: 8px 14px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        margin: 0 !important;
        font-size: 12px !important;
        color: {t['fg']} !important;
    }}

    div[role="radiogroup"] > label:hover {{
        border-color: {t['primary']} !important;
    }}

    div[role="radiogroup"] > label:has(input:checked) {{
        background: {t['primary']} !important;
        color: #ffffff !important;
        border-color: {t['primary_dark']} !important;
        font-weight: 700 !important;
    }}

    div[role="radiogroup"] > label > div:first-child {{
        display: none !important;
    }}

    /* ═══════════════════════════════════════════════════════
       جدول TF
       ═══════════════════════════════════════════════════════ */
    .tf-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: {t['bg_card']};
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid {t['border']};
        font-size: 12px;
        direction: rtl;
        box-shadow: {card_shadow};
    }}

    .tf-table th {{
        background: {t['bg_mid']};
        color: {t['fg_muted']};
        padding: 10px 8px;
        text-align: right;
        font-weight: 600;
        border-bottom: 1px solid {t['border']};
        font-size: 11px;
    }}

    .tf-table td {{
        padding: 10px 8px;
        border-bottom: 1px solid {t['border']};
        color: {t['fg']};
        font-size: 12px;
        vertical-align: middle;
        text-align: right;
    }}

    .tf-table tr:last-child td {{ border-bottom: none; }}
    .tf-table tr:hover td {{ background: {t['bg_card_hover']}; }}

    /* ═══════════════════════════════════════════════════════
       Progress
       ═══════════════════════════════════════════════════════ */
    .stProgress > div > div > div {{
        background: linear-gradient(90deg, {t['cyan']}, {t['primary']});
        border-radius: 4px;
    }}

    /* ═══════════════════════════════════════════════════════
       Expander
       ═══════════════════════════════════════════════════════ */
    details {{
        background: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        overflow: hidden !important;
        transition: all 0.2s ease;
    }}

    details[open] {{
        animation: slide-up 0.3s ease;
    }}

    details > summary {{
        direction: rtl !important;
        text-align: right !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-direction: row-reverse !important;
        padding: 14px 18px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        color: {t['fg']} !important;
        cursor: pointer !important;
        background: transparent !important;
        border-radius: 12px !important;
        list-style: none !important;
        outline: none !important;
    }}

    details > summary::-webkit-details-marker {{
        display: none !important;
    }}

    details > summary:hover {{
        background: {t['bg_card_hover']} !important;
    }}

    details > summary > div,
    details > summary > span,
    details > summary > p {{
        direction: rtl !important;
        text-align: right !important;
        margin: 0 !important;
    }}

    details > summary svg {{
        margin: 0 !important;
        order: -1 !important;
        flex-shrink: 0 !important;
    }}

    details[open] > summary {{
        border-bottom: 1px solid {t['border']} !important;
        border-radius: 12px 12px 0 0 !important;
    }}

    details > div {{
        padding: 16px 18px !important;
    }}

    /* ═══════════════════════════════════════════════════════
       کارت‌ها
       ═══════════════════════════════════════════════════════ */
    .ty-unified-card {{
        padding: 14px 18px !important;
        animation: fade-in 0.3s ease;
    }}

    .ty-signal-box, .ty-sr-box {{
        padding: 12px !important;
    }}

    /* ═══════════════════════════════════════════════════════
       Scrollbar
       ═══════════════════════════════════════════════════════ */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {t['bg_dark']}; }}
    ::-webkit-scrollbar-thumb {{
        background: {t['border_light']};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {t['primary']};
    }}

    /* ═══════════════════════════════════════════════════════
       FAB — برگشت به بالا
       ═══════════════════════════════════════════════════════ */
    .fab-back-to-top {{
        position: fixed;
        bottom: 24px;
        left: 24px;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: {t['primary']};
        color: #ffffff !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        font-weight: 700;
        cursor: pointer;
        box-shadow: 0 4px 16px {t['primary_glow']}, 0 2px 8px rgba(0, 0, 0, 0.25);
        z-index: 9999;
        transition: all 0.2s ease;
        text-decoration: none !important;
        border: 2px solid {t['primary_dark']};
        line-height: 1;
    }}

    .fab-back-to-top:hover {{
        background: {t['primary_dark']};
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 6px 20px {t['primary_glow']}, 0 4px 12px rgba(0, 0, 0, 0.3);
        color: #ffffff !important;
    }}

    .fab-back-to-top:active {{
        transform: translateY(-1px) scale(1);
    }}

    /* ═══════════════════════════════════════════════════════
       Skeleton Loader
       ═══════════════════════════════════════════════════════ */
    @keyframes skeleton-pulse {{
        0%, 100% {{ opacity: 0.6; }}
        50% {{ opacity: 0.3; }}
    }}

    .skeleton-box {{
        background: linear-gradient(
            90deg,
            {t['bg_mid']} 0%,
            {t['bg_card_hover']} 50%,
            {t['bg_mid']} 100%
        );
        background-size: 200% 100%;
        animation: skeleton-pulse 1.5s ease-in-out infinite;
        border-radius: 8px;
    }}

    /* ═══════════════════════════════════════════════════════
       موبایل
       ═══════════════════════════════════════════════════════ */
    @media (max-width: 900px) {{
        .main .block-container {{ padding: 0.5rem 0.75rem !important; }}

        .trademun-header {{
            padding: 10px 14px;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .header-logo {{ width: 42px; height: 42px; }}
        .header-brand-fa {{ font-size: 14px !important; }}
        .header-brand-en {{ font-size: 8px !important; }}

        .header-right div > div {{ font-size: 9px !important; }}

        .tf-table {{ display: none !important; }}

        details > summary {{
            padding: 12px 14px !important;
            font-size: 13px !important;
        }}

        details > div {{
            padding: 12px 14px !important;
        }}

        .fab-back-to-top {{
            bottom: 16px;
            left: 16px;
            width: 44px;
            height: 44px;
            font-size: 20px;
        }}
    }}
    </style>
    """


# ═══════════════════════════════════════════════════════════
# FAB — برگشت به بالا
# ═══════════════════════════════════════════════════════════
def render_back_to_top_fab() -> None:
    """دکمه شناور برگشت به بالا"""
    try:
        import streamlit as st

        st.markdown(
            '<div id="top-anchor" style="position: absolute; top: 0; '
            'left: 0; width: 1px; height: 1px;"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<a href="#top-anchor" class="fab-back-to-top" '
            'title="برگشت به بالا" aria-label="برگشت به بالا">'
            "↑"
            "</a>",
            unsafe_allow_html=True,
        )
    except Exception as e:
        print(f"[Styles] خطا در render_back_to_top_fab: {e}")


# ═══════════════════════════════════════════════════════════
# Skeleton Helper
# ═══════════════════════════════════════════════════════════
def render_skeleton(
    height: int = 100,
    width: str = "100%",
    message: str = "⏳ در حال بارگذاری...",
) -> None:
    """نمایش Skeleton Loader"""
    try:
        import streamlit as st

        st.markdown(
            f'<div class="skeleton-box" style="height:{height}px; '
            f"width:{width}; display:flex; align-items:center; "
            f'justify-content:center; color:#6B7DA0; font-size:12px;">'
            f"{message}</div>",
            unsafe_allow_html=True,
        )
    except Exception as e:
        print(f"[Styles] خطا در render_skeleton: {e}")


# ═══════════════════════════════════════════════════════════
# Exports
# ═══════════════════════════════════════════════════════════
__all__ = [
    "THEME_DARK",
    "THEME_LIGHT",
    "get_theme",
    "get_custom_css",
    "get_logo_base64",
    "render_back_to_top_fab",
    "render_skeleton",
]


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("تست ui/styles.py — نسخه ۱۶.۰")
    print("=" * 60)
    print()

    print("۱) تم تاریک:")
    for k in ["bg", "bg_card", "fg", "primary", "cyan", "green", "red"]:
        print(f"   {k:12} = {THEME_DARK[k]}")
    print()

    print("۲) تم روشن:")
    for k in ["bg", "bg_card", "fg", "primary", "cyan", "green", "red"]:
        print(f"   {k:12} = {THEME_LIGHT[k]}")
    print()

    print("۳) CSS تولید شد؟")
    css = get_custom_css("dark")
    print(f"   طول: {len(css)} کاراکتر")
    print(f"   شامل live-pulse: {'live-pulse' in css}")
    print(f"   شامل fab-back-to-top: {'fab-back-to-top' in css}")
    print(f"   شامل skeleton-pulse: {'skeleton-pulse' in css}")
    print()

    print("۴) CSS تم روشن:")
    css_light = get_custom_css("light")
    print(f"   طول: {len(css_light)}")
    print(f"   شامل #F0F4F8: {'#F0F4F8' in css_light}")
    print()

    print("۵) لوگو base64:")
    logo = get_logo_base64()
    print(f"   طول: {len(logo)} | موجود: {'✅' if logo else '❌'}")
    print()

    print("[OK] تست کامل شد.")
