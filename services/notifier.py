"""
services/notifier.py
ارسال سیگنال به تلگرام و بله — فاز ۱۳ (نسخه نهایی)
"""

import logging
import requests
from api.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# ۱. تابع کمکی برای گرد کردن قیمت‌ها
# ═══════════════════════════════════════════════════════════
def _format_price(price: float) -> str:
    if price is None:
        return "0"
    if price > 1000:
        return f"{price:,.0f}"
    return f"{price:.3f}".rstrip("0").rstrip(".")


# ═══════════════════════════════════════════════════════════
# ۲. ساخت پیام برای تلگرام (با HTML)
# ═══════════════════════════════════════════════════════════
def _build_telegram_message(signal: dict) -> str:
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", 0)

    # آیکون و متن بر اساس جهت
    if direction == "long":
        status_icon = "🟢"
        status_text = "خرید (LONG)"
        market_icon = "📈"
        regime_text = "صعودی"
    elif direction == "short":
        status_icon = "🔴"
        status_text = "فروش (SHORT)"
        market_icon = "📉"
        regime_text = "نزولی"
    else:
        status_icon = "🟡"
        status_text = "خنثی"
        market_icon = "➖"
        regime_text = "خنثی"

    # سطح اطمینان
    if confidence >= 70:
        conf_text = "اطمینان قوی"
    elif confidence >= 50:
        conf_text = "اطمینان متوسط"
    else:
        conf_text = "اطمینان ضعیف"

    # بازار و ریسک
    market_type_fa = "فیوچرز" if signal.get("market_type") == "futures" else "اسپات"
    risk_fa = (
        "جسورانه 🚀" if signal.get("risk_profile") == "aggressive" else "محتاطانه 🛡️"
    )

    # صرافی
    source_map = {
        "nobitex": "نوبیتکس",
        "bitpin": "بیت‌پین",
        "wallex": "والکس",
        "tabdeal": "تبدیل",
    }
    source_fa = source_map.get(signal.get("source", ""), signal.get("source", ""))

    ticker_clean = signal.get("ticker", "").replace("-", "")

    # فرمت قیمت‌ها
    price_str = _format_price(signal.get("price", 0))
    tp_str = _format_price(signal.get("tp", 0))
    sl_str = _format_price(signal.get("sl", 0))
    rr_str = f"{signal.get('rr', 0):.2f}"

    # استفاده از تگ‌های HTML برای تلگرام
    msg = (
        f"📊 سیگنال جدید | Trademun\n\n"
        f"<blockquote>"
        f"💎 نماد: <b>{signal.get('ticker', '')}</b>\n"
        f"🏦 صرافی: {source_fa}\n"
        f"⏱️ تایم‌فریم: {signal.get('tf', '')}\n"
        f"⚙️ بازار: {market_type_fa} {market_icon} · {risk_fa}"
        f"</blockquote>\n\n"
        f"{status_icon} <b>{status_text}</b> · {conf_text} ({confidence}%)\n"
        f"📈 جهت بازار: {regime_text}\n\n"
        f"<blockquote>"
        f"💰 قیمت ورود: <code>{price_str}</code>\n"
        f"🎯 حد سود: <code>{tp_str}</code>\n"
        f"🛡️ حد ضرر: <code>{sl_str}</code>\n"
        f"⚖️ نسبت سود به ضرر: <b>{rr_str}</b>"
        f"</blockquote>\n\n"
        f"🌠 تحلیل بازارهای مالی با تریدمون\n\n"
        f"🔗 <a href='https://trademun.ir'>سایت: trademun.ir</a>\n"
        f"📢 <a href='https://t.me/trademun'>کانال: @trademun</a>\n\n"
        f"#تریدمون_نشه؟ #کریپتو #ترید #{ticker_clean}"
    )
    return msg


# ═══════════════════════════════════════════════════════════
# ۳. ساخت پیام برای بله (بدون HTML)
# ═══════════════════════════════════════════════════════════
def _build_bale_message(signal: dict) -> str:
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", 0)

    # آیکون و متن بر اساس جهت
    if direction == "long":
        status_icon = "🟢"
        status_text = "خرید (LONG)"
        market_icon = "📈"
        regime_text = "صعودی"
    elif direction == "short":
        status_icon = "🔴"
        status_text = "فروش (SHORT)"
        market_icon = "📉"
        regime_text = "نزولی"
    else:
        status_icon = "🟡"
        status_text = "خنثی"
        market_icon = "➖"
        regime_text = "خنثی"

    # سطح اطمینان
    if confidence >= 70:
        conf_text = "اطمینان قوی"
    elif confidence >= 50:
        conf_text = "اطمینان متوسط"
    else:
        conf_text = "اطمینان ضعیف"

    # بازار و ریسک
    market_type_fa = "فیوچرز" if signal.get("market_type") == "futures" else "اسپات"
    risk_fa = (
        "جسورانه 🚀" if signal.get("risk_profile") == "aggressive" else "محتاطانه 🛡️"
    )

    # صرافی
    source_map = {
        "nobitex": "نوبیتکس",
        "bitpin": "بیت‌پین",
        "wallex": "والکس",
        "tabdeal": "تبدیل",
    }
    source_fa = source_map.get(signal.get("source", ""), signal.get("source", ""))

    ticker_clean = signal.get("ticker", "").replace("-", "")

    # فرمت قیمت‌ها
    price_str = _format_price(signal.get("price", 0))
    tp_str = _format_price(signal.get("tp", 0))
    sl_str = _format_price(signal.get("sl", 0))
    rr_str = f"{signal.get('rr', 0):.2f}"

    # بله از blockquote پشتیبانی نمی‌کنه، پس از خط جداکننده ساده استفاده می‌کنیم
    msg = (
        f"📊 سیگنال جدید | Trademun\n\n"
        f"💎 نماد: {signal.get('ticker', '')}\n"
        f"🏦 صرافی: {source_fa}\n"
        f"⏱️ تایم‌فریم: {signal.get('tf', '')}\n"
        f"⚙️ بازار: {market_type_fa} {market_icon} · {risk_fa}\n\n"
        f"{status_icon} {status_text} · {conf_text} ({confidence}%)\n"
        f"📈 جهت بازار: {regime_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 قیمت ورود: {price_str}\n"
        f"🎯 حد سود: {tp_str}\n"
        f"🛡️ حد ضرر: {sl_str}\n"
        f"⚖️ نسبت سود به ضرر: {rr_str}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🌠 تحلیل بازارهای مالی با تریدمون\n\n"
        f"🔗 سایت: trademun.ir\n"
        f"📢 کانال: @trademun\n\n"
        f"#تریدمون_نشه؟ #کریپتو #ترید #{ticker_clean}"
    )
    return msg


# ═══════════════════════════════════════════════════════════
# ۴. ارسال به تلگرام
# ═══════════════════════════════════════════════════════════
def send_telegram(signal: dict) -> bool:
    if signal.get("confidence", 0) < 55:
        logger.info(
            f"[Telegram] سیگنال {signal.get('ticker')} رد شد (اطمینان {signal.get('confidence')}%)"
        )
        return False

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    api_base = settings.TELEGRAM_API_BASE or "https://api.telegram.org"

    if not token or not chat_id:
        logger.warning("[Telegram] تنظیمات کامل نیست")
        return False

    msg = _build_telegram_message(signal)

    url = f"{api_base}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            logger.info(f"[Telegram] ✅ {signal.get('ticker')}")
            return True
        logger.warning(
            f"[Telegram] ❌ status={resp.status_code} body={resp.text[:200]}"
        )
        return False
    except Exception as e:
        logger.exception(f"[Telegram] خطا: {e}")
        return False


# ═══════════════════════════════════════════════════════════
# ۵. ارسال به بله
# ═══════════════════════════════════════════════════════════
def send_bale(signal: dict) -> bool:
    if signal.get("confidence", 0) < 55:
        logger.info(
            f"[Bale] سیگنال {signal.get('ticker')} رد شد (اطمینان {signal.get('confidence')}%)"
        )
        return False

    token = settings.BALE_BOT_TOKEN
    chat_id = settings.BALE_CHAT_ID
    api_base = "https://tapi.bale.ai"

    if not token or not chat_id:
        logger.warning("[Bale] تنظیمات کامل نیست")
        return False

    msg = _build_bale_message(signal)

    url = f"{api_base}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            logger.info(f"[Bale] ✅ {signal.get('ticker')}")
            return True
        logger.warning(f"[Bale] ❌ status={resp.status_code} body={resp.text[:200]}")
        return False
    except Exception as e:
        logger.exception(f"[Bale] خطا: {e}")
        return False


# ═══════════════════════════════════════════════════════════
# ۶. تابع اصلی (ارسال به هر دو)
# ═══════════════════════════════════════════════════════════
def notify_signal(signal: dict) -> None:
    """ارسال سیگنال به تلگرام و بله (فقط اطمینان > 55%)"""
    if signal.get("confidence", 0) < 55:
        logger.info(
            f"[Notify] سیگنال {signal.get('ticker')} رد شد (اطمینان {signal.get('confidence')}%)"
        )
        return

    send_telegram(signal)
    send_bale(signal)
