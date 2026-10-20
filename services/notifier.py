"""
services/notifier.py
ارسال سیگنال به تلگرام (با پروکسی) و بله
============================================================
"""

import logging
import os
import random

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")

BALE_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHAT_ID = os.getenv("BALE_CHAT_ID", "")

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


def _fmt(num, for_telegram: bool = False) -> str:
    if num is None or num == "—" or num == 0:
        return "—"
    try:
        if for_telegram:
            return str(int(float(num)))  # 🔴 بدون کاما برای تلگرام
        return f"{int(float(num)):,}"  # 🔴 با کاما برای بله
    except (ValueError, TypeError):
        return str(num)


def _build_signal_message(data: dict, for_telegram: bool = False) -> str:
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
    price = _fmt(data.get("price"), for_telegram)
    tp = _fmt(data.get("tp"), for_telegram)
    sl = _fmt(data.get("sl"), for_telegram)
    rr_net = data.get("rr_net", "—")
    market = data.get("market_type", "spot")
    profile = data.get("risk_profile", "aggressive")
    tf = data.get("tf", "—")
    had_trap = data.get("had_trap", False)
    trap_type = data.get("trap_type")

    if "LONG" in signal.upper():
        regime_fa = "صعودی"
    elif "SHORT" in signal.upper():
        regime_fa = "نزولی"
    else:
        regime_fa = "خنثی"

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
    random_topics = random.sample(topic_hashtags, 2)
    hashtags = [
        "#تریدمون_نشه؟",  # 🔴 اول: ثابت + فارسی + راست‌چین
        f"#{ticker_fa}",
        f"#{source_fa}",
        *random_topics,
    ]

    trap_line = ""
    if had_trap and trap_type:
        trap_labels = {
            "bull_trap": "تله صعودی",
            "bear_trap": "تله نزولی",
            "fake_breakout": "شکست جعلی",
            "exhaustion": "خستگی روند",
        }
        trap_label = trap_labels.get(trap_type, trap_type)
        if for_telegram:
            trap_line = f"\n⚠️ <b>هشدار:</b> احتمال {trap_label}"
        else:
            trap_line = f"\n⚠️ *هشدار:* احتمال {trap_label}"

    scenarios = data.get("scenarios", [])
    override_reason = data.get("override_reason", "")
    conclusion = ""
    if override_reason:
        conclusion = f"⚠️ {override_reason}"
    elif scenarios and len(scenarios) > 0:
        sc = scenarios[0]
        conclusion = f"📊 {sc.get('condition', '')} (احتمال {int(sc.get('probability', 0.5) * 100)}%) → {sc.get('action', '')}"

    if conclusion:
        if for_telegram:
            conclusion_line = f"\n💡 <b>جمع‌بندی:</b> {conclusion}"
        else:
            conclusion_line = f"\n💡 *جمع‌بندی:* {conclusion}"
    else:
        conclusion_line = ""

    if for_telegram:
        status_line_html = f"{signal_emoji} <b>وضعیت:</b> {signal_fa} · اطمینان <b>{confidence_str}</b> ({confidence}%)"

        msg = (
            f"📊 <b>سیگنال جدید | Trademun</b>\n\n"
            f"💎 <b>نماد:</b> <code>{ticker}</code>\n"
            f"🏦 <b>صرافی:</b> {source_fa}\n"
            f"⏱ <b>تایم‌فریم:</b> {tf}\n"
            f"⚙️ <b>بازار:</b> {market_fa} · {profile_fa}\n\n"
            f"<blockquote>"
            f"{status_line_html}\n"
            f"💰 <b>قیمت ورود:</b> <code>{price}</code>\n"
            f"🎯 <b>حد سود (TP):</b> <code>{tp}</code>\n"
            f"🛡 <b>حد ضرر (SL):</b> <code>{sl}</code>"
            f"</blockquote>\n\n"
            f"⚖️ <b>نسبت سود به ضرر:</b> <code>{rr_net}</code>\n\n"
            f"📈 <b>جهت بازار:</b> {regime_fa}\n"
            f"{trap_line}\n"
            f"{conclusion_line}\n\n"
            f"🔗 <b>سایت:</b> trademun.ir\n"
            f"📢 <b>کانال:</b> @trademun\n\n"
            f"{' '.join(hashtags)}\n"
        )
    else:
        # ... (بخش بله دست‌نخورده بمونه) ...

        status_line_md = f"{signal_emoji} *وضعیت:* {signal_fa} · اطمینان *{confidence_str}* ({confidence}%)"

        msg = (
            f"📊 *سیگنال جدید | Trademun*\n\n"
            f"💎 *نماد:* {ticker}\n"
            f"🏦 *صرافی:* {source_fa}\n"
            f"⏱ *تایم‌فریم:* {tf}\n"
            f"⚙️ *بازار:* {market_fa} · {profile_fa}\n\n"
            f"{status_line_md}\n"
            f"💰 *قیمت ورود:* {price}\n"
            f"🎯 *حد سود (TP):* {tp}\n"
            f"🛡 *حد ضرر (SL):* {sl}\n"
            f"⚖️ *نسبت سود به ضرر:* {rr_net}\n\n"
            f"📈 *جهت بازار:* {regime_fa}\n"
            f"{trap_line}\n"
            f"{conclusion_line}\n\n"
            f"🔗 *سایت:* trademun.ir\n"
            f"📢 *کانال:* @trademun\n\n"
            f"{' '.join(hashtags)}\n"
        )
    return msg


def _send_to_bale(message: str) -> None:
    if not BALE_TOKEN or not BALE_CHAT_ID:
        return
    try:
        requests.post(
            f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendMessage",
            data={"chat_id": BALE_CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=30,
        )
        logger.info("[Bale] ✅")
    except Exception as e:
        logger.warning(f"[Bale] ❌ {e}")


def _send_to_telegram(message: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        resp = requests.post(
            f"{TELEGRAM_API_BASE}/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("[Telegram] ✅")
    except Exception as e:
        logger.warning(f"[Telegram] ❌ {e}")


def notify_signal(data: dict) -> None:
    try:
        _send_to_bale(_build_signal_message(data, for_telegram=False))
        _send_to_telegram(_build_signal_message(data, for_telegram=True))
    except Exception as e:
        logger.exception(f"[Notifier] خطا: {e}")
