"""
render_worker/notifier.py
نسخه مخصوص Render — فقط تلگرام، بدون پروکسی
============================================================
"""

import logging
import os
import random

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# تنظیمات (فقط تلگرام)
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")

# ═══════════════════════════════════════════════════════════
# دیکشنری نام فارسی
# ═══════════════════════════════════════════════════════════
TICKER_FA = {
    "BTC": "بیت‌کوین",
    "ETH": "اتریوم",
    "XAUT": "تتر_گلد",
    "PAXG": "پکس_گلد",
    "ENA": "انا",
    "USDT": "تتر",
    "SOL": "سولانا",
    "BNB": "بایننس_کوین",
    "XRP": "ریپل",
    "DOGE": "دوج_کوین",
    "ADA": "کاردانو",
    "TRX": "ترون",
    "DOT": "پولکادات",
    "LTC": "لایت_کوین",
    "AVAX": "آوالانچ",
    "LINK": "چین_لینک",
    "MATIC": "ماتیک",
    "UNI": "یونی‌سواپ",
    "ATOM": "کازموس",
    "TON": "تون_کوین",
    "SHIB": "شیبا_اینو",
    "PEPE": "پپه",
    "XAU": "طلا",
    "MAGIC": "مجیک",
}

SOURCE_FA = {
    "nobitex": "نوبیتکس",
    "bitpin": "بیت‌پین",
    "wallex": "والکس",
    "tabdeal": "تبدیل",
    "tsetmc": "بورس",
}


# ═══════════════════════════════════════════════════════════
# ابزار کمکی
# ═══════════════════════════════════════════════════════════
def _fmt(num) -> str:
    if num is None or num == "—" or num == 0:
        return "—"
    try:
        return f"{int(float(num)):,}"
    except (ValueError, TypeError):
        return str(num)


# ═══════════════════════════════════════════════════════════
# ساخت متن سیگنال (فقط برای تلگرام)
# ═══════════════════════════════════════════════════════════
def _build_signal_message(data: dict) -> str:
    ticker = data.get("ticker", "—")
    ticker_clean = ticker.replace("-", "")
    ticker_base = (
        ticker_clean.split("_")[0]
        if "_" in ticker_clean
        else ticker_clean.split("-")[0]
    )

    ticker_fa = TICKER_FA.get(ticker_base.upper(), ticker_base)
    source = data.get("source", "—")
    source_fa = SOURCE_FA.get(source.lower(), source)

    signal = data.get("signal", "—")
    confidence = data.get("confidence", 0)
    price = _fmt(data.get("price"))
    tp = _fmt(data.get("tp"))
    sl = _fmt(data.get("sl"))
    rr_net = data.get("rr_net", "—")
    market = data.get("market_type", "spot")
    profile = data.get("risk_profile", "aggressive")
    tf = data.get("tf", "—")
    had_trap = data.get("had_trap", False)
    trap_type = data.get("trap_type")

    if confidence >= 70:
        confidence_str = "قوی"
    elif confidence >= 50:
        confidence_str = "متوسط"
    else:
        confidence_str = "ضعیف"

    signal_upper = signal.upper()
    if "LONG" in signal_upper:
        signal_emoji, signal_fa = "🟢", "خرید (LONG)"
    elif "SHORT" in signal_upper:
        signal_emoji, signal_fa = "🔴", "فروش (SHORT)"
    else:
        signal_emoji, signal_fa = "⚪", "خنثی"

    market_fa = "اسپات 💵" if market == "spot" else "فیوچرز 📈"
    profile_fa = "جسورانه 🚀" if profile == "aggressive" else "محتاطانه 🛡"

    topic_hashtags = [
        "#کریپتو",
        "#سیگنال",
        "#تحلیل_تکنیکال",
        "#ترید",
        "#بازار_مالی",
        "#ارز_دیجیتال",
    ]
    hashtags = [
        f"#{ticker_fa}",
        f"#{source_fa}",
        random.choice(topic_hashtags),
        random.choice(topic_hashtags),
        "#تریدمون_نشه",
    ]

    if confidence >= 70:
        status_line = f"{signal_emoji} <b>وضعیت:</b> {signal_fa} · اطمینان <b>{confidence_str}</b> ({confidence}%)"
    else:
        status_line = f"{signal_emoji} <b>وضعیت:</b> {signal_fa} ({confidence}%)"

    trap_line = ""
    if had_trap and trap_type:
        trap_labels = {
            "bull_trap": "تله صعودی",
            "bear_trap": "تله نزولی",
            "fake_breakout": "شکست جعلی",
            "exhaustion": "خستگی روند",
        }
        trap_label = trap_labels.get(trap_type, trap_type)
        trap_line = f"\n⚠️ <b>هشدار:</b> احتمال {trap_label}\n"

    scenarios = data.get("scenarios", [])
    override_reason = data.get("override_reason", "")
    conclusion = ""
    if override_reason:
        conclusion = f"⚠️ {override_reason}"
    elif scenarios and len(scenarios) > 0:
        sc = scenarios[0]
        conclusion = f"📊 {sc.get('condition', '')} (احتمال {int(sc.get('probability', 0.5) * 100)}%) → {sc.get('action', '')}"

    if conclusion:
        conclusion_line = f"\n💡 <b>جمع‌بندی:</b> {conclusion}\n"
    else:
        conclusion_line = ""

    msg = (
        f"📊 <b>سیگنال جدید | Trademun</b>\n"
        f"\n"
        f"💎 <b>نماد:</b> <code>{ticker}</code>\n"
        f"🏦 <b>صرافی:</b> {source_fa}\n"
        f"⏱ <b>تایم‌فریم:</b> {tf}\n"
        f"⚙️ <b>بازار:</b> {market_fa} · {profile_fa}\n"
        f"\n"
        f"{status_line}\n"
        f"💰 <b>قیمت ورود:</b> <code>{price}</code>\n"
        f"🎯 <b>حد سود (TP):</b> <code>{tp}</code>\n"
        f"🛡 <b>حد ضرر (SL):</b> <code>{sl}</code>\n"
        f"⚖️ <b>R:R خالص:</b> <code>{rr_net}</code>\n"
        f"{trap_line}"
        f"{conclusion_line}"
        f"\n"
        f"🔗 <b>سایت:</b> trademun.ir · 📢 <b>کانال:</b> @trademun\n"
        f"\n"
        f"{' '.join(hashtags)}\n"
    )
    return msg


# ═══════════════════════════════════════════════════════════
# ارسال به تلگرام (مستقیم، بدون پروکسی)
# ═══════════════════════════════════════════════════════════
def notify_signal(data: dict) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("[Render] Telegram token/chat_id not set.")
        return

    try:
        message = _build_signal_message(data)
        url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}

        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        logger.info("[Render Telegram] ✅ Signal sent successfully.")
    except Exception as e:
        logger.error(f"[Render Telegram] ❌ Error: {e}")
