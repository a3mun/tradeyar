"""
services/notifier.py
ارسال سیگنال به تلگرام و بله — نسخه ۲.۳
============================================================
🔴 تغییرات نسخه ۲.۳:
  • هماهنگی کامل با آستانه‌های جدید (شروع سیگنال از ۴۰٪)
  • به‌روزرسانی برچسب‌های اطمینان (ضعیف ۴۰-۵۵، معمولی ۵۵-۷۰، قوی ۷۰-۸۵، طلایی +۸۵)
  • بهبود نمایش R:R خالص در پیام
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from api.config import settings

logger = logging.getLogger(__name__)

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

# ═══════════════════════════════════════════════════════════
# 🔴 آستانه‌ها
# ═══════════════════════════════════════════════════════════
MIN_CONFIDENCE_TO_NOTIFY = 40
STRONG_CONFIDENCE_BYPASS = 70

# 🔴 TFهایی که به notify نمی‌رن (فقط UI)
TF_SKIP_FOR_NOTIFY = frozenset({"۱ دقیقه"})


def _should_skip(signal: dict, source_name: str) -> bool:
    """چرا نباید ارسال بشه؟ با لاگ دقیق."""
    ticker = signal.get("ticker", "?")
    tf = signal.get("tf", "?")

    # ═══ چک TF ═══
    if tf in TF_SKIP_FOR_NOTIFY:
        logger.debug(
            f"[Notifier/{source_name}] رد {ticker} {tf}: "
            f"TF در TF_SKIP_FOR_NOTIFY (ذاتاً R:R خالص پایین)"
        )
        return True

    # ═══ چک جهت ═══
    direction = signal.get("direction", "neutral")
    if direction not in ("long", "short"):
        logger.debug(
            f"[Notifier/{source_name}] رد {ticker} {tf}: direction={direction}"
        )
        return True

    # ═══ چک confidence ═══
    confidence = signal.get("confidence", 0)
    if confidence < MIN_CONFIDENCE_TO_NOTIFY:
        logger.debug(
            f"[Notifier/{source_name}] رد {ticker} {tf}: "
            f"confidence={confidence}% < {MIN_CONFIDENCE_TO_NOTIFY}%"
        )
        return True

    # 🔴 استثنا: سیگنال قوی (≥ 70%) حتی با is_worthwhile=False
    if confidence >= STRONG_CONFIDENCE_BYPASS:
        logger.info(
            f"[Notifier/{source_name}] ⚡ سیگنال قوی: {ticker} {tf} "
            f"conf={confidence}% (bypass is_worthwhile)"
        )
        return False

    # ═══ چک is_worthwhile ═══
    if signal.get("is_worthwhile") is False:
        logger.debug(
            f"[Notifier/{source_name}] رد {ticker} {tf}: "
            f"is_worthwhile=False (R:R پایین)"
        )
        return True

    return False


def _format_price(price: float) -> str:
    if price is None:
        return "0"
    if price > 1000:
        return f"{price:,.0f}"
    return f"{price:.3f}".rstrip("0").rstrip(".")


def _format_shamsi_date() -> str:
    """تاریخ و ساعت به وقت تهران — 1405/08/06 - 22:00:25"""
    try:
        now = datetime.now(TEHRAN_TZ)
        try:
            import jdatetime

            j = jdatetime.datetime.fromgregorian(datetime=now)
            date_str = f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
        except ImportError:
            date_str = now.strftime("%Y/%m/%d")
        time_str = now.strftime("%H:%M:%S")
        return f"{date_str} - {time_str}"
    except Exception:
        return ""


def _get_hashtags(signal: dict) -> str:
    """ساخت ۵ هشتگ داینامیک"""
    tags = ["#تریدمون_نشه"]

    ticker = (
        (signal.get("ticker") or "").replace("-", "").replace("_", "").replace("/", "")
    )
    ticker = "".join(c for c in ticker if c.isalnum())
    if ticker:
        tags.append(f"#{ticker}")

    source = signal.get("source", "")
    source_map = {
        "nobitex": "#نوبیتکس",
        "bitpin": "#بیت‌پین",
        "wallex": "#والکس",
        "tabdeal": "#تبدیل",
        "tsetmc": "#بورس",
    }
    if source in source_map:
        tags.append(source_map[source])

    market_type = signal.get("market_type", "")
    if market_type == "futures":
        tags.append("#فیوچرز")
    elif market_type == "spot":
        tags.append("#اسپات")

    tags.append("#کریپتو")

    return " ".join(tags[:5])


def _get_trap_status(signal: dict) -> str:
    traps = signal.get("traps") or {}
    for k, v in traps.items():
        if isinstance(v, dict) and v.get("active"):
            trap_names = {
                "bull_trap": "تله صعودی",
                "bear_trap": "تله نزولی",
                "fake_breakout": "شکست جعلی",
                "exhaustion": "خستگی روند",
            }
            return trap_names.get(k, k)
    return ""


def _confidence_label(confidence: int) -> tuple[str, str]:
    """برچسب سطح اطمینان — هماهنگ با قانون جدید (۴۰، ۵۵، ۷۰، ۸۵)"""
    if confidence >= 85:
        return ("💎", "اطمینان طلایی")
    elif confidence >= 70:
        return ("🔥", "اطمینان قوی")
    elif confidence >= 55:
        return ("✅", "اطمینان معمولی")
    elif confidence >= 40:
        return ("⚠️", "اطمینان ضعیف")
    else:
        return ("⚪", "بدون اطمینان")


def _build_message(signal: dict, is_telegram: bool = True) -> str:
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", 0)
    market_type = signal.get("market_type", "spot")
    risk_profile = signal.get("risk_profile", "aggressive")

    if direction == "long":
        icon = "🟢"
        dir_fa = "خرید"
    elif direction == "short":
        icon = "🔴"
        dir_fa = "فروش"
    else:
        icon = "🟡"
        dir_fa = "خنثی"

    conf_icon, conf_fa = _confidence_label(confidence)

    market_fa = "فیوچرز" if market_type == "futures" else "اسپات"
    risk_fa = "جسورانه" if risk_profile == "aggressive" else "محتاطانه"

    source = signal.get("source", "")
    source_map = {
        "nobitex": "🟣Nobitex",
        "bitpin": "🟢Bitpin",
        "wallex": "🔵Wallex",
        "tabdeal": "🟠Tabdeal",
        "tsetmc": "🇮🇷TSETMC",
    }
    source_fa = source_map.get(source, source)

    tf_short = {
        "۱ دقیقه": "1m",
        "۵ دقیقه": "5m",
        "۱۵ دقیقه": "15m",
        "۳۰ دقیقه": "30m",
        "۱ ساعت": "1h",
        "روزانه": "1d",
    }.get(signal.get("tf", ""), signal.get("tf", ""))

    # 🔴 R:R خالص (بعد از کارمزد+اسپرد)
    rr_val = signal.get("rr_net") or signal.get("rr", 0) or 0
    rr_str = f"{rr_val:.2f}"

    price_str = _format_price(signal.get("price", 0))
    tp_str = _format_price(signal.get("tp", 0))
    sl_str = _format_price(signal.get("sl", 0))

    trap_text = _get_trap_status(signal)
    trap_line = f" | ⚠️ {trap_text}" if trap_text else ""

    date_str = _format_shamsi_date()
    hashtags = _get_hashtags(signal)
    ticker = signal.get("ticker", "")

    golden_mark = "💎 " if confidence >= 85 else ""

    if is_telegram:
        header_line = f"     {golden_mark}{ticker} / <b>TF: {tf_short}</b>"
        direction_line = f"| <b>{dir_fa}</b> | {conf_icon} {conf_fa} ({confidence}%)"
        prices_block = (
            f"<blockquote>"
            f"💰 ورود: <code>{price_str}</code>\n"
            f"🎯 حد سود: <code>{tp_str}</code>\n"
            f"🛡️ حد ضرر: <code>{sl_str}</code>\n"
            f"ریسک به ریوارد (خالص): <b>{rr_str}</b>"
            f"</blockquote>"
        )
    else:
        header_line = f"     {golden_mark}{ticker} / TF: {tf_short}"
        direction_line = f"| {dir_fa} | {conf_icon} {conf_fa} ({confidence}%)"
        prices_block = (
            f"💰 ورود: {price_str}\n"
            f"🎯 حد سود: {tp_str}\n"
            f"🛡️ حد ضرر: {sl_str}\n"
            f"ریسک به ریوارد (خالص): {rr_str}"
        )

    msg = (
        f"━━━━━{icon}━━━━━\n"
        f"{header_line}\n\n"
        f"{direction_line}\n"
        f"| {market_fa} | {risk_fa} |{source_fa}{trap_line}\n\n"
        f"{prices_block}\n\n"
        f"━━━━━{icon}━━━━━\n"
        f"{date_str}\n\n\n"
        f"🌠 تحلیل بازارهای مالی با تریدمون\n"
        f"🔗 سایت: trademun.ir\n"
        f"📢 کانال: @trademun\n\n"
        f"{hashtags}"
    )
    return msg


def send_telegram(signal: dict) -> bool:
    if _should_skip(signal, "telegram"):
        return False

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    api_base = settings.TELEGRAM_API_BASE or "https://api.telegram.org"

    if not token or not chat_id:
        logger.warning(
            "[Notifier/telegram] TELEGRAM_BOT_TOKEN یا TELEGRAM_CHAT_ID خالی است"
        )
        return False

    msg = _build_message(signal, is_telegram=True)
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
            logger.info(
                f"[Notifier/telegram] ✅ {signal.get('ticker')} "
                f"{signal.get('tf')} {signal.get('confidence')}%"
            )
            return True
        logger.warning(
            f"[Notifier/telegram] ❌ status={resp.status_code} body={resp.text[:200]}"
        )
        return False
    except Exception as e:
        logger.warning(f"[Notifier/telegram] ❌ خطا: {e!r}")
        return False


def send_bale(signal: dict) -> bool:
    if _should_skip(signal, "bale"):
        return False

    token = settings.BALE_BOT_TOKEN
    chat_id = settings.BALE_CHAT_ID
    api_base = "https://tapi.bale.ai"

    if not token or not chat_id:
        logger.warning("[Notifier/bale] BALE_BOT_TOKEN یا BALE_CHAT_ID خالی است")
        return False

    msg = _build_message(signal, is_telegram=False)
    url = f"{api_base}/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": msg}

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            logger.info(
                f"[Notifier/bale] ✅ {signal.get('ticker')} "
                f"{signal.get('tf')} {signal.get('confidence')}%"
            )
            return True
        logger.warning(
            f"[Notifier/bale] ❌ status={resp.status_code} body={resp.text[:200]}"
        )
        return False
    except Exception as e:
        logger.warning(f"[Notifier/bale] ❌ خطا: {e!r}")
        return False


def notify_signal(signal: dict) -> None:
    """ارسال به هر دو کانال — با لاگ دقیق."""
    tg = send_telegram(signal)
    bale = send_bale(signal)
    if not tg and not bale:
        logger.info(
            f"[Notifier] هیچ‌کدام ارسال نشد: "
            f"{signal.get('ticker')} {signal.get('tf')} "
            f"conf={signal.get('confidence')}% "
            f"is_worthwhile={signal.get('is_worthwhile')} "
            f"direction={signal.get('direction')}"
        )
