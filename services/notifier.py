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

# ═══════════════════════════════════════════════════════════
# تنظیمات
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")

BALE_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHAT_ID = os.getenv("BALE_CHAT_ID", "")

PROXY_LIST_URL = (
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
)

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


def _get_proxies() -> list[str]:
    try:
        resp = requests.get(PROXY_LIST_URL, timeout=10)
        resp.raise_for_status()
        proxies = [line.strip() for line in resp.text.splitlines() if line.strip()]
        return proxies[:5]  # 🔴 فقط ۵ تا
    except Exception as e:
        logger.warning(f"[Proxy] خطا: {e}")
        return []


def _try_telegram_with_proxy(message: str) -> bool:
    proxies = _get_proxies()
    if not proxies:
        return False
    random.shuffle(proxies)

    url = f"{TELEGRAM_API_BASE}/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}

    for proxy in proxies:
        try:
            proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            resp = requests.post(
                url, data=payload, proxies=proxy_dict, timeout=3
            )  # 🔴 ۳ ثانیه
            if resp.status_code == 200:
                logger.info(f"[Telegram] ✅ (پروکسی {proxy})")
                return True
        except Exception:
            continue
    return False


# ═══════════════════════════════════════════════════════════
# ساخت متن سیگنال
# ═══════════════════════════════════════════════════════════
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
        status_line = f"{signal_emoji} *وضعیت:* {signal_fa} · اطمینان *{confidence_str}* ({confidence}%)"
    else:
        status_line = f"{signal_emoji} *وضعیت:* {signal_fa} ({confidence}%)"

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
            trap_line = f"\n⚠️ <b>هشدار:</b> احتمال {trap_label}\n"
        else:
            trap_line = f"\n⚠️ *هشدار:* احتمال {trap_label}\n"

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
            conclusion_line = f"\n💡 <b>جمع‌بندی:</b> {conclusion}\n"
        else:
            conclusion_line = f"\n💡 *جمع‌بندی:* {conclusion}\n"
    else:
        conclusion_line = ""

    if for_telegram:
        msg = (
            f"📊 <b>سیگنال جدید | Trademun</b>\n"
            f"\n"
            f"💎 <b>نماد:</b> <code>{ticker}</code>\n"
            f"🏦 <b>صرافی:</b> {source_fa}\n"
            f"⏱ <b>تایم‌فریم:</b> {tf}\n"
            f"⚙️ <b>بازار:</b> {market_fa} · {profile_fa}\n"
            f"\n"
            f"{status_line.replace('*', '<b>').replace('*', '</b>') if '*' in status_line else status_line}\n"
            f"💰 <b>قیمت ورود:</b> <code>{price}</code>\n"
            f"🎯 <b>حد سود (TP):</b> <code>{tp}</code>\n"
            f"🛡 <b>حد ضرر (SL):</b> <code>{sl}</code>\n"
            f"⚖️ <b>R:R خالص:</b> <code>{rr_net}</code>\n"
            f"{trap_line}"
            f"{conclusion_line}"
            f"\n"
            f"🔗 <b>سایت:</b> trademun.ir · 📢 <b>کانال:</b> @trademun\n"
            f"\n"
            f"{' '.join(hashtags)}"
        )
    else:
        msg = (
            f"📊 *سیگنال جدید | Trademun*\n"
            f"\n"
            f"💎 *نماد:* {ticker}\n"
            f"🏦 *صرافی:* {source_fa}\n"
            f"⏱ *تایم‌فریم:* {tf}\n"
            f"⚙️ *بازار:* {market_fa} · {profile_fa}\n"
            f"\n"
            f"{status_line}\n"
            f"💰 *قیمت ورود:* {price}\n"
            f"🎯 *حد سود (TP):* {tp}\n"
            f"🛡 *حد ضرر (SL):* {sl}\n"
            f"⚖️ *R:R خالص:* {rr_net}\n"
            f"{trap_line}"
            f"{conclusion_line}"
            f"\n"
            f"🔗 *سایت:* trademun.ir · 📢 *کانال:* @trademun\n"
            f"\n"
            f"{' '.join(hashtags)}\n"  # 🔴 خط خالی آخر
        )
    return msg


# ═══════════════════════════════════════════════════════════
# ارسال‌ها
# ═══════════════════════════════════════════════════════════
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

    if _try_telegram_with_proxy(message):
        return

    try:
        requests.post(
            f"{TELEGRAM_API_BASE}/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=3,  # 🔴 تایم‌اوت کوتاه (۳ ثانیه)
        )
        logger.info("[Telegram] ✅ (مستقیم)")
    except Exception as e:
        logger.warning(f"[Telegram] ❌ {e}")


# ═══════════════════════════════════════════════════════════
# تابع اصلی
# ═══════════════════════════════════════════════════════════
def notify_signal(data: dict) -> None:
    try:
        _send_to_bale(_build_signal_message(data, for_telegram=False))
        _send_to_telegram(_build_signal_message(data, for_telegram=True))
    except Exception as e:
        logger.exception(f"[Notifier] خطا: {e}")
