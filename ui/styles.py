"""
ui/styles.py
پالت رنگ + CSS
نسخه ۱۹.۰ — نهایی فاز ۳
هدر سه‌بخشی + Marquee پیوسته
"""

from pathlib import Path

FONT_DIR = Path(__file__).parent.parent / "fonts"
FONT_DIR.mkdir(exist_ok=True)


THEME_DARK = {
    "name": "تاریک",
    "bg": "#0D1117",
    "bg_dark": "#08090D",
    "bg_card": "#161B22",
    "bg_hover": "#1C2128",
    "bg_mid": "#12161C",
    "border": "#21262D",
    "border_light": "#30363D",
    "fg": "#F0F6FC",
    "fg_muted": "#B1BAC4",
    "fg_dim": "#7D8590",
    "primary": "#F59E0B",
    "primary_dark": "#D97706",
    "primary_glow": "rgba(245, 158, 11, 0.25)",
    "cyan": "#3FD9C6",
    "cyan_dark": "#14B8A6",
    "cyan_glow": "rgba(63, 217, 198, 0.2)",
    "green": "#4ADE80",
    "green_glow": "rgba(74, 222, 128, 0.2)",
    "red": "#F87171",
    "red_glow": "rgba(248, 113, 113, 0.2)",
    "yellow": "#FACC15",
    "orange": "#FB923C",
    "purple": "#C084FC",
    "gold": "#FFD700",
}


THEME_LIGHT = {
    "name": "روشن",
    "bg": "#E8EDF2",
    "bg_dark": "#DDE3EA",
    "bg_card": "#F5F7FA",
    "bg_hover": "#EDF1F6",
    "bg_mid": "#E2E8F0",
    "border": "#CBD5E1",
    "border_light": "#B8C4D4",
    "fg": "#0F172A",
    "fg_muted": "#475569",
    "fg_dim": "#64748B",
    "primary": "#D97706",
    "primary_dark": "#B45309",
    "primary_glow": "rgba(217, 119, 6, 0.2)",
    "cyan": "#0D9488",
    "cyan_dark": "#0F766E",
    "cyan_glow": "rgba(13, 148, 136, 0.2)",
    "green": "#16A34A",
    "green_glow": "rgba(22, 163, 74, 0.15)",
    "red": "#DC2626",
    "red_glow": "rgba(220, 38, 38, 0.15)",
    "yellow": "#CA8A04",
    "orange": "#EA580C",
    "purple": "#9333EA",
    "gold": "#CA8A04",
}


def get_theme(name: str = "dark") -> dict:
    return THEME_DARK if name == "dark" else THEME_LIGHT


def get_custom_css(theme_name: str = "dark") -> str:
    t = get_theme(theme_name)

    return f"""
    <style>
    * {{ box-sizing: border-box; }}

    html, body, [class*="css"], .stApp {{
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Vazirmatn', 'Tahoma', sans-serif !important;
        background-color: {t['bg']} !important;
        color: {t['fg']} !important;
    }}

    .main .block-container {{
        padding: 0.5rem 0.75rem !important;
        max-width: 100% !important;
    }}

    #MainMenu, footer, header {{ visibility: hidden; }}

    div[data-testid="stMarkdownContainer"] pre,
    div[data-testid="stMarkdownContainer"] code {{
        background: transparent !important;
        color: inherit !important;
        padding: 0 !important;
    }}

    /* ═══════════════════════════════════════════════════════
       هدر یکپارچه — سه بخش
       ═══════════════════════════════════════════════════════ */
    .tradeyar-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, {t['bg_dark']} 0%, {t['bg_card']} 100%);
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 12px 24px;
        margin-bottom: 12px;
        gap: 16px;
        flex-wrap: nowrap;
        width: 100%;
        min-height: 80px;
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
        box-shadow: 0 0 6px {t['green']};
        margin-left: 4px;
        animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.3; }}
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(5px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .fade-in {{ animation: fadeIn 0.3s ease; }}

    /* ═══════════════════════════════════════════════════════
       نوار بالایی — ثابت راست‌چین با اسکرول دستی
       ═══════════════════════════════════════════════════════ */
    .top-ticker {{
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 8px 0;
        margin-bottom: 12px;
        overflow: hidden;
        width: 100%;
    }}

    .ticker-row-wrapper {{
        display: flex;
        overflow-x: auto;
        overflow-y: hidden;
        width: 100%;
        direction: rtl;
        scroll-behavior: smooth;
        -webkit-overflow-scrolling: touch;
    }}

    /* اسکرول‌بار نامرئی */
    .ticker-row-wrapper::-webkit-scrollbar {{
        height: 4px;
    }}
    .ticker-row-wrapper::-webkit-scrollbar-track {{
        background: {t['bg_dark']};
        border-radius: 2px;
    }}
    .ticker-row-wrapper::-webkit-scrollbar-thumb {{
        background: {t['primary']};
        border-radius: 2px;
    }}
    .ticker-row-wrapper::-webkit-scrollbar-thumb:hover {{
        background: {t['cyan']};
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

    /* ═══════════════════════════════════════════════════════
       کارت سیگنال
       ═══════════════════════════════════════════════════════ */
    .signal-card {{
        background: linear-gradient(135deg, {t['bg_card']} 0%, {t['bg_mid']} 100%);
        border: 2px solid {t['border']};
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 14px;
        transition: all 0.3s ease;
        width: 100%;
    }}

    .signal-card.long {{
        border-color: {t['green']};
        box-shadow: 0 6px 24px {t['green_glow']};
    }}

    .signal-card.short {{
        border-color: {t['red']};
        box-shadow: 0 6px 24px {t['red_glow']};
    }}

    .signal-badge {{
        display: inline-block;
        padding: 8px 20px;
        border-radius: 10px;
        font-weight: bold;
        text-align: center;
        font-size: 15px;
    }}

    .signal-badge.long {{
        background: {t['green_glow']};
        color: {t['green']};
        border: 2px solid {t['green']};
    }}

    .signal-badge.short {{
        background: {t['red_glow']};
        color: {t['red']};
        border: 2px solid {t['red']};
    }}

    .signal-badge.neutral {{
        background: rgba(139, 148, 158, 0.15);
        color: {t['fg_muted']};
        border: 2px solid {t['border_light']};
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
    }}

    .tf-table th {{
        background: {t['bg_mid']};
        color: {t['fg_muted']};
        padding: 9px 8px;
        text-align: right;
        font-weight: 500;
        border-bottom: 1px solid {t['border']};
        font-size: 11px;
    }}

    .tf-table td {{
        padding: 9px 8px;
        border-bottom: 1px solid {t['border']};
        color: {t['fg']};
        font-size: 12px;
        vertical-align: middle;
        text-align: right;
    }}

    .tf-table tr:last-child td {{ border-bottom: none; }}
    .tf-table tr:hover td {{ background: {t['bg_hover']}; }}

    .tf-card {{
        display: none;
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
    }}

    /* ═══════════════════════════════════════════════════════
       دکمه‌ها
       ═══════════════════════════════════════════════════════ */
    .stButton > button {{
        background: {t['bg_card']};
        color: {t['fg']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 6px 12px;
        font-family: 'Vazirmatn', 'Tahoma', sans-serif;
        font-weight: 500;
        font-size: 12px;
        transition: all 0.2s ease;
    }}

    .stButton > button:hover {{
        background: {t['cyan']};
        color: #000;
        border-color: {t['cyan']};
    }}

    .stButton > button[kind="primary"] {{
        background: {t['primary']};
        color: #000;
        border-color: {t['primary']};
        font-weight: bold;
    }}

    .stSelectbox > div > div {{
        background: {t['bg_card']} !important;
        border-color: {t['border']} !important;
        color: {t['fg']} !important;
        border-radius: 8px !important;
    }}

    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-track {{ background: {t['bg_dark']}; }}
    ::-webkit-scrollbar-thumb {{ background: {t['border_light']}; border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {t['cyan']}; }}

    /* ═══════════════════════════════════════════════════════
       موبایل
       ═══════════════════════════════════════════════════════ */
    @media (max-width: 900px) {{
        .main .block-container {{ padding: 0.35rem 0.5rem !important; }}
        .signal-card {{ padding: 12px; }}

        .tradeyar-header {{
            padding: 10px 14px;
            gap: 8px;
        }}

        .header-left span:first-child {{ font-size: 24px !important; }}
        .header-left div > div:first-child {{ font-size: 14px !important; }}
        .header-left div > div:last-child {{ font-size: 8px !important; }}

        .header-right div > div {{ font-size: 9px !important; }}

        .tf-table {{ display: none !important; }}
        .tf-card {{ display: block !important; }}
    }}
    </style>
    """