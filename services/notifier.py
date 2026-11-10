"""
services/notifier.py
ارسال سیگنال به تلگرام و بله — نسخه ۴.۱ (فاز ۱۵)
============================================================
🔴 تغییرات نسخه ۴.۱:
  • رفع باگ Dedup مشترک (حالا تلگرام و بله مستقل هستند)
  • اضافه شدن لاگ‌های دیباگ برای بله
"""

import json
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from api.config import settings

logger = logging.getLogger(__name__)
DISABLE_NOTIFY = getattr(settings, "DISABLE_NOTIFICATIONS", "false").lower() == "true"

TEHRAN_TZ = ZoneInfo("Asia/Tehran")


# ═══════════════════════════════════════════════════════════
# آستانه‌های پویا (بر اساس ماتریس ۵ سطح)
# ═══════════════════════════════════════════════════════════
def _get_min_confidence(strategy: str) -> int:
    return {"scalp": 30, "swing": 40, "position": 50}.get(strategy, 40)


def _get_strong_bypass(strategy: str) -> int:
    """آستانه‌ی Bypass (سیگنال قوی که از is_worthwhile عبور می‌کنه)"""
    return {"scalp": 60, "swing": 70, "position": 75}.get(strategy, 70)


# Cooldown پویا بر اساس تایم‌فریم (برای اسکالپ کوتاه‌تر)
_TF_COOLDOWN_SEC = {
    "۱ دقیقه": 60,  # ۱ دقیقه
    "۵ دقیقه": 180,  # ۳ دقیقه
    "۱۵ دقیقه": 300,  # ۵ دقیقه
    "۳۰ دقیقه": 600,  # ۱۰ دقیقه
    "۱ ساعت": 1200,  # ۲۰ دقیقه
    "روزانه": 3600,  # ۱ ساعت
}
_DEFAULT_COOLDOWN = 300

# 🔴 لیست‌های جداگانه برای هر کانال
_last_sent: dict[str, dict[str, float]] = {"telegram": {}, "bale": {}}


def _is_recent_duplicate(signal: dict, channel: str) -> bool:
    ticker = signal.get("ticker", "")
    tf = signal.get("tf", "")
    strategy = signal.get("strategy", "swing")
    key = f"{ticker}|{tf}|{strategy}"

    cooldown = _TF_COOLDOWN_SEC.get(tf, _DEFAULT_COOLDOWN)
    now = time.time()

    channel_dict = _last_sent.get(channel, {})
    if key in channel_dict and now - channel_dict[key] < cooldown:
        logger.info(
            f"[Notifier/{channel}] ⏭ تکراری: {ticker} {tf} {strategy} "
            f"(cooldown {cooldown}s)"
        )
        return True
    channel_dict[key] = now
    return False


def _should_skip(signal: dict, channel: str) -> bool:
    """شرط‌های رد کردن سیگنال"""
    ticker = signal.get("ticker", "?")
    tf = signal.get("tf", "?")
    strategy = signal.get("strategy", "swing")
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", 0)

    # ۱. فقط جهت‌دار
    if direction not in ("long", "short"):
        logger.debug(f"[Notifier/{channel}] ⏭ {ticker} {tf}: جهت {direction} خنثی")
        return True

    # ۲. حداقل اطمینان
    min_conf = _get_min_confidence(strategy)
    if confidence < min_conf:
        logger.debug(
            f"[Notifier/{channel}] ⏭ {ticker} {tf}: "
            f"conf={confidence}% < min={min_conf}% ({strategy})"
        )
        return True

    # ۳. Bypass برای سیگنال‌های قوی
    if confidence >= _get_strong_bypass(strategy):
        logger.info(
            f"[Notifier/{channel}] ⚡ قوی (bypass): {ticker} {tf} conf={confidence}%"
        )
        return False

    # ۴. R:R برای اسکالپ و سوئینگ نادیده گرفته میشه
    if strategy in ("scalp", "swing"):
        return False

    # ۵. R:R برای پوزیشن چک میشه
    if signal.get("is_worthwhile") is False:
        logger.debug(
            f"[Notifier/{channel}] ⏭ {ticker} {tf}: is_worthwhile=False ({strategy})"
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
    try:
        now = datetime.now(TEHRAN_TZ)
        try:
            import jdatetime

            j = jdatetime.datetime.fromgregorian(datetime=now)
            date_str = f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
        except ImportError:
            date_str = now.strftime("%Y/%m/%d")
        return f"{date_str} - {now.strftime('%H:%M:%S')}"
    except Exception:
        return ""


def _get_strategy_label(strategy: str) -> tuple[str, str]:
    return {
        "scalp": ("⚡", "اسکالپ"),
        "swing": ("🌊", "سوئینگ"),
        "position": ("🏛", "پوزیشن"),
    }.get(strategy, ("🌊", "سوئینگ"))


def _get_hashtags(signal: dict) -> str:
    tags = ["#تریدمون_نشه"]
    ticker = (
        (signal.get("ticker") or "").replace("-", "").replace("_", "").replace("/", "")
    )
    ticker = "".join(c for c in ticker if c.isalnum())
    if ticker:
        tags.append(f"#{ticker}")
    strategy = signal.get("strategy", "swing")
    strategy_tag = {"scalp": "#اسکالپ", "swing": "#سوئینگ", "position": "#پوزیشن"}.get(
        strategy
    )
    if strategy_tag:
        tags.append(strategy_tag)
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
    return " ".join(tags[:5])


def _get_trap_status(signal: dict) -> str:
    traps = signal.get("traps") or {}
    for k, v in traps.items():
        if isinstance(v, dict) and v.get("active"):
            return {
                "bull_trap": "تله صعودی",
                "bear_trap": "تله نزولی",
                "fake_breakout": "شکست جعلی",
                "exhaustion": "خستگی روند",
            }.get(k, k)
    return ""


def _confidence_label(confidence: int, strategy: str) -> tuple[str, str]:
    min_conf = _get_min_confidence(strategy)
    if confidence >= 85:
        return ("💎", "اطمینان طلایی")
    elif confidence >= 70:
        return ("🔥", "اطمینان قوی")
    elif confidence >= min_conf + 20:
        return ("✅", "اطمینان معمولی")
    elif confidence >= min_conf:
        return ("⚠️", "اطمینان ضعیف")
    return ("⚪", "بدون اطمینان")


def _build_message(signal: dict, is_telegram: bool = True) -> str:
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", 0)
    market_type = signal.get("market_type", "spot")
    risk_profile = signal.get("risk_profile", "aggressive")
    strategy = signal.get("strategy", "swing")

    icon = "🟢" if direction == "long" else ("🔴" if direction == "short" else "🟡")
    dir_fa = (
        "خرید" if direction == "long" else ("فروش" if direction == "short" else "خنثی")
    )
    conf_icon, conf_fa = _confidence_label(confidence, strategy)
    strategy_icon, strategy_fa = _get_strategy_label(strategy)
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

    rr_val = signal.get("rr_net") or signal.get("rr", 0) or 0
    rr_str = f"{rr_val:.2f}"
    price_str = _format_price(signal.get("price", 0))
    tp_str = _format_price(signal.get("tp", 0))
    sl_str = _format_price(signal.get("sl", 0))

    # TP Ladder
    tp_levels = signal.get("tp_levels") or {}
    if not tp_levels and signal.get("tp_levels_json"):
        try:
            tp_levels = json.loads(signal["tp_levels_json"])
        except Exception:
            tp_levels = {}

    tp_ladder = ""
    if tp_levels.get("tp1"):
        tp1_s = _format_price(tp_levels.get("tp1", 0))
        tp2_s = _format_price(tp_levels.get("tp2", 0))
        tp3_s = _format_price(tp_levels.get("tp3", 0))
        if is_telegram:
            tp_ladder = (
                f"\n\n📊 <b>خروج پله‌ای:</b>\n"
                f"• TP1: <code>{tp1_s}</code>\n"
                f"• TP2: <code>{tp2_s}</code>\n"
                f"• TP3: <code>{tp3_s}</code>"
            )
        else:
            tp_ladder = (
                f"\n\n📊 خروج پله‌ای:\n"
                f"• TP1: {tp1_s}\n"
                f"• TP2: {tp2_s}\n"
                f"• TP3: {tp3_s}"
            )

    trap_text = _get_trap_status(signal)
    trap_line = f" | ⚠️ {trap_text}" if trap_text else ""

    date_str = _format_shamsi_date()
    hashtags = _get_hashtags(signal)
    ticker = signal.get("ticker", "")
    golden_mark = "💎 " if confidence >= 85 else ""

    if is_telegram:
        header_line = f"     {golden_mark}{ticker} / <b>TF: {tf_short}</b>"
        direction_line = f"| <b>{dir_fa}</b> | {conf_icon} {conf_fa} ({confidence}%)"
        strategy_line = (
            f"{strategy_icon} <b>{strategy_fa}</b> | {market_fa} | {risk_fa}"
        )
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
        strategy_line = f"{strategy_icon} {strategy_fa} | {market_fa} | {risk_fa}"
        prices_block = (
            f"💰 ورود: {price_str}\n"
            f"🎯 حد سود: {tp_str}\n"
            f"🛡️ حد ضرر: {sl_str}\n"
            f"ریسک به ریوارد (خالص): {rr_str}"
        )

    return (
        f"━━━━━{icon}━━━━━\n"
        f"{header_line}\n\n"
        f"{direction_line}\n"
        f"{strategy_line}{source_fa}{trap_line}\n\n"
        f"{prices_block}"
        f"{tp_ladder}\n\n"
        f"━━━━━{icon}━━━━━\n"
        f"{date_str}\n\n\n"
        f"🌠 تحلیل بازارهای مالی با تریدمون\n"
        f"🔗 سایت: trademun.ir\n"
        f"📢 کانال: @trademun\n\n"
        f"{hashtags}"
    )


def send_telegram(signal: dict) -> bool:
    if DISABLE_NOTIFY:
        logger.debug("[Notifier/telegram] غیرفعال (DISABLE_NOTIFICATIONS=true)")
        return False
    logger.info(
        f"[Notifier/telegram] 🔍 چک: {signal.get('ticker')} {signal.get('tf')} "
        f"strategy={signal.get('strategy')} conf={signal.get('confidence')}%"
    )
    if _should_skip(signal, "telegram"):
        return False
    if _is_recent_duplicate(signal, "telegram"):
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
                f"{signal.get('tf')} {signal.get('strategy')} {signal.get('confidence')}%"
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
    if DISABLE_NOTIFY:
        logger.debug("[Notifier/bale] غیرفعال (DISABLE_NOTIFICATIONS=true)")
        return False
    logger.info(
        f"[Notifier/bale] 🔍 چک: {signal.get('ticker')} {signal.get('tf')} "
        f"strategy={signal.get('strategy')} conf={signal.get('confidence')}%"
    )
    if _should_skip(signal, "bale"):
        return False
    if _is_recent_duplicate(signal, "bale"):
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
        # لاگ دقیق برای دیباگ بله
        logger.warning(
            f"[DEBUG/bale] URL={url} | Status={resp.status_code} | Response={resp.text[:500]}"
        )

        if resp.status_code == 200:
            logger.info(
                f"[Notifier/bale] ✅ {signal.get('ticker')} "
                f"{signal.get('tf')} {signal.get('strategy')} {signal.get('confidence')}%"
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
    if DISABLE_NOTIFY:
        logger.info("[Notify] ارسال غیرفعال است (DISABLE_NOTIFICATIONS=true)")
        return

    tg = send_telegram(signal)
    # 🔴 استفاده از کپی برای جلوگیری از دستکاری همزمان
    bale = send_bale(dict(signal))
    if not tg and not bale:
        logger.info(
            f"[Notifier] هیچ‌کدام ارسال نشد: "
            f"{signal.get('ticker')} {signal.get('tf')} "
            f"strategy={signal.get('strategy')} conf={signal.get('confidence')}%"
        )
