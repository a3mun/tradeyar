"""
ui/styles.py
پالت رنگ + CSS — نسخه ۱۲.۰
فونت IRANYekanXVF + JetBrains Mono
راست‌چین سراسری + تم روشن بازطراحی‌شده
"""

from pathlib import Path

FONT_DIR = Path(__file__).parent.parent / "fonts"
FONT_DIR.mkdir(exist_ok=True)

B64_FILE = FONT_DIR / "IRANYekanXVF.b64.txt"


def _load_font_base64() -> str:
    try:
        if B64_FILE.exists():
            with open(B64_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"[Styles] خطا در خواندن فونت: {e}")
    return ""


_FONT_B64 = _load_font_base64()


THEME_DARK = {
    "name": "تاریک",
    "bg": "#0d1117",
    "bg_dark": "#010409",
    "bg_card": "#161b22",
    "bg_card_hover": "#1c2128",
    "bg_mid": "#21262d",
    "bg_input": "#0d1117",
    "border": "#30363d",
    "border_light": "#484f58",
    "border_glow": "rgba(88, 166, 255, 0.4)",
    "fg": "#e6edf3",
    "fg_muted": "#8b949e",
    "fg_dim": "#6e7681",
    "primary": "#f0b90b",
    "primary_dark": "#d29922",
    "primary_glow": "rgba(240, 185, 11, 0.15)",
    "cyan": "#58a6ff",
    "cyan_dark": "#388bfd",
    "cyan_glow": "rgba(88, 166, 255, 0.15)",
    "green": "#3fb950",
    "green_dark": "#2ea043",
    "green_glow": "rgba(63, 185, 80, 0.15)",
    "red": "#f85149",
    "red_dark": "#da3633",
    "red_glow": "rgba(248, 81, 73, 0.15)",
    "yellow": "#d29922",
    "orange": "#db6d28",
    "purple": "#bc8cff",
    "purple_glow": "rgba(188, 140, 255, 0.15)",
    "gold": "#f0b90b",
    "nobitex": "#a855f7",
    "abantether": "#3b82f6",
}


THEME_LIGHT = {
    "name": "روشن",
    "bg": "#f8fafc",
    "bg_dark": "#f1f5f9",
    "bg_card": "#ffffff",
    "bg_card_hover": "#f8fafc",
    "bg_mid": "#f1f5f9",
    "bg_input": "#ffffff",
    "border": "#cbd5e1",
    "border_light": "#94a3b8",
    "border_glow": "rgba(2, 132, 199, 0.3)",
    "fg": "#0f172a",
    "fg_muted": "#334155",
    "fg_dim": "#64748b",
    "primary": "#b45309",
    "primary_dark": "#92400e",
    "primary_glow": "rgba(180, 83, 9, 0.12)",
    "cyan": "#0369a1",
    "cyan_dark": "#075985",
    "cyan_glow": "rgba(3, 105, 161, 0.1)",
    "green": "#047857",
    "green_dark": "#065f46",
    "green_glow": "rgba(4, 120, 87, 0.1)",
    "red": "#b91c1c",
    "red_dark": "#991b1b",
    "red_glow": "rgba(185, 28, 28, 0.1)",
    "yellow": "#a16207",
    "orange": "#c2410c",
    "purple": "#6d28d9",
    "purple_glow": "rgba(109, 40, 217, 0.1)",
    "gold": "#b45309",
    "nobitex": "#7c3aed",
    "abantether": "#2563eb",
}


def get_theme(name: str = "dark") -> dict:
    return THEME_DARK if name == "dark" else THEME_LIGHT


def get_custom_css(theme_name: str = "dark") -> str:
    t = get_theme(theme_name)

    font_face = ""
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
        font_face = """
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
        """

    is_light = (theme_name == "light")
    
    # تفاوت‌های خاص تم روشن
    card_shadow = "0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)" if is_light else "0 2px 8px rgba(0,0,0,0.15)"
    card_shadow_hover = "0 4px 12px rgba(15, 23, 42, 0.12)" if is_light else "0 4px 12px rgba(0,0,0,0.25)"

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

    #MainMenu, footer, header {{
        visibility: hidden;
    }}

    div[data-testid="stMarkdownContainer"],
    div[data-testid="stMarkdownContainer"] > p,
    div[data-testid="stMarkdownContainer"] > div,
    div[data-testid="stMarkdownContainer"] > span,
    label,
    .stRadio > label,
    .stSelectbox > label,
    .stTextInput > label,
    .stTextArea > label,
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

    /* ═══ هدر ═══ */
    .tradeyar-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 14px;
        padding: 14px 24px;
        margin-bottom: 14px;
        gap: 16px;
        flex-wrap: nowrap;
        width: 100%;
        min-height: 80px;
        box-shadow: {card_shadow};
    }}

    .header-left {{
        display: flex;
        align-items: center;
        gap: 10px;
        flex: 1 1 0;
        min-width: 0;
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
        animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.4; }}
    }}

    /* ═══ تیکر ═══ */
    .top-ticker {{
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 8px 0;
        margin-bottom: 14px;
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

    .ticker-row-wrapper::-webkit-scrollbar {{ height: 4px; }}
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
        padding: 4px 14px;
        font-size: 12px;
        flex-shrink: 0;
    }}

    /* ═══ دکمه‌ها ═══ */
    .stButton > button {{
        background: {t['bg_card']};
        color: {t['fg']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 8px 14px;
        font-family: 'IRANYekanX', 'Vazirmatn', sans-serif;
        font-weight: 600;
        font-size: 12px;
        transition: all 0.15s ease;
        box-shadow: {card_shadow};
    }}

    .stButton > button:hover {{
        background: {t['bg_card_hover']};
        border-color: {t['primary']};
        transform: translateY(-1px);
        box-shadow: {card_shadow_hover};
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

    /* ═══ ورودی‌ها ═══ */
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

    /* حذف راهنمای مزاحم زیر ورودی */
    div[data-testid="InputInstructions"] {{
        display: none !important;
    }}

    /* ═══ Radio افقی ═══ */
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
        transition: all 0.15s ease !important;
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

    /* ═══ جدول TF ═══ */
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

    .tf-card {{
        display: none;
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
    }}

    /* ═══ Progress ═══ */
    .stProgress > div > div > div {{
        background: linear-gradient(90deg, {t['cyan']}, {t['primary']});
        border-radius: 4px;
    }}

    /* ═══ Expander ═══ */
    details {{
        background: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 12px !important;
        margin-bottom: 14px !important;
        overflow: hidden !important;
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

    details[open] {{
        padding: 0 !important;
    }}

    details > div {{
        padding: 16px 18px !important;
    }}

    /* ═══ کارت‌ها ═══ */
    .ty-unified-card {{
        padding: 14px 18px !important;
    }}

    .ty-signal-box, .ty-sr-box {{
        padding: 12px !important;
    }}

    /* ═══ Scrollbar ═══ */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {t['bg_dark']}; }}
    ::-webkit-scrollbar-thumb {{
        background: {t['border_light']};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {t['cyan']};
    }}

    /* ═══ موبایل ═══ */
    @media (max-width: 900px) {{
        .main .block-container {{ padding: 0.5rem 0.75rem !important; }}

        .tradeyar-header {{
            padding: 10px 14px;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .header-left span:first-child {{ font-size: 24px !important; }}
        .header-left div > div:first-child {{ font-size: 14px !important; }}
        .header-left div > div:last-child {{ font-size: 8px !important; }}

        .header-right div > div {{ font-size: 9px !important; }}

        .tf-table {{ display: none !important; }}
        .tf-card {{ display: block !important; }}

        details > summary {{
            padding: 12px 14px !important;
            font-size: 13px !important;
        }}

        details > div {{
            padding: 12px 14px !important;
        }}
    }}
    </style>
    """