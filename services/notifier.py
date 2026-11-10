"""
services/notifier.py
ارسال سیگنال به تلگرام و بله — نسخه ۳.۱ (فاز ۱۴.۹.۱۰)
============================================================
🔴 تغییرات نسخه ۳.۱:
  • رفع باگ TP Ladder تکراری (خارج از blockquote شد)
  • آستانه‌های پویا (اسکالپ ۲۵، بقیه ۴۰)
  • bypass پویا (اسکالپ ۵۰، سوئینگ ۷۰، پوزیشن ۷۵)
  • نمایش استراتژی
  • برچسب‌های ۷ سطح
  • هشتگ استراتژی
  • dedup ۵ دقیقه
  • TP Ladder بدون درصد
"""

import logging
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from api.config import settings

logger = logging.getLogger(__name__)
DISABLE_NOTIFY = getattr(settings, "DISABLE_NOTIFICATIONS", "false").lower() == "true"

TEHRAN_TZ = ZoneInfo("Asia/Tehran")


# ═══════════════════════════════════════════════════════════
# 🔴 آستانه‌های پویا
# ═══════════════════════════════════════════════════════════
def _get_min_confidence(strategy: str) -> int:
    if strategy == "scalp":
        return 25
    return 40


def _get_strong_bypass(strategy: str) -> int:
    if strategy == "scalp":
        return 50
    elif strategy == "position":
        return 75
    return 70


TF_SKIP_FOR_NOTIFY = frozenset({"۱ دقیقه"})

# Cooldown برای جلوگیری از تکرار
_last_sent: dict[str, float] = {}
COOLDOWN_SEC = 300  # ۵ دقیقه


def _is_recent_duplicate(signal: dict) -> bool:
    ticker = signal.get("ticker", "")
    tf = signal.get("tf", "")
    strategy = signal.get("strategy", "swing")
    key = f"{ticker}|{tf}|{strategy}"
    now = time.time()
    if key in _last_sent and now - _last_sent[key] < COOLDOWN_SEC:
        logger.debug(f"[Notifier] ⏭ تکرار {key} (cooldown)")
        return True
    _last_sent[key] = now
    return False


def _should_skip(signal: dict, source_name: str) -> bool:
    ticker = signal.get("ticker", "?")
    tf = signal.get("tf", "?")
    strategy = signal.get("strategy", "swing")

    if tf in TF_SKIP_FOR_NOTIFY:
        logger.debug(f"[Notifier/{source_name}] رد {ticker} {tf}: TF در skip-list")
        return True

    direction = signal.get("direction", "neutral")
    if direction not in ("long", "short"):
        logger.debug(
            f"[Notifier/{source_name}] رد {ticker} {tf}: direction={direction}"
        )
        return True

    min_conf = _get_min_confidence(strategy)
    confidence = signal.get("confidence", 0)
    if confidence < min_conf:
        logger.debug(
            f"[Notifier/{source_name}] رد {ticker} {tf}: "
            f"confidence={confidence}% < {min_conf}% (strategy={strategy})"
        )
        return True

    bypass = _get_strong_bypass(strategy)
    if confidence >= bypass:
        logger.info(
            f"[Notifier/{source_name}] ⚡ سیگنال قوی: {ticker} {tf} "
            f"conf={confidence}% (bypass, strategy={strategy})"
        )
        return False

    if signal.get("is_worthwhile") is False:
        if strategy == "scalp":
            logger.info(
                f"[Notifier/{source_name}] ✅ اسکالپ is_worthwhile=False: "
                f"{ticker} {tf} conf={confidence}%"
            )
            return False
        logger.debug(
            f"[Notifier/{source_name}] رد {ticker} {tf}: "
            f"is_worthwhile=False (strategy={strategy})"
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
        time_str = now.strftime("%H:%M:%S")
        return f"{date_str} - {time_str}"
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
    strategy_hashtag = {
        "scalp": "#اسکالپ",
        "swing": "#سوئینگ",
        "position": "#پوزیشن",
    }.get(strategy)
    if strategy_hashtag:
        tags.append(strategy_hashtag)

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
            trap_names = {
                "bull_trap": "تله صعودی",
                "bear_trap": "تله نزولی",
                "fake_breakout": "شکست جعلی",
                "exhaustion": "خستگی روند",
            }
            return trap_names.get(k, k)
    return ""


def _confidence_label(confidence: int, strategy: str = "swing") -> tuple[str, str]:
    min_conf = {"scalp": 30, "swing": 40, "position": 50}.get(strategy, 40)

    if confidence >= 85:
        return ("💎", "اطمینان طلایی")
    elif confidence >= 70:
        return ("🔥", "اطمینان قوی")
    elif confidence >= min_conf + 20:
        return ("✅", "اطمینان معمولی")
    elif confidence >= min_conf:
        return ("⚠️", "اطمینان ضعیف")
    else:
        return ("⚪", "بدون اطمینان")


def _build_message(signal: dict, is_telegram: bool = True) -> str:
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", 0)
    market_type = signal.get("market_type", "spot")
    risk_profile = signal.get("risk_profile", "aggressive")
    strategy = signal.get("strategy", "swing")

    if direction == "long":
        icon = "🟢"
        dir_fa = "خرید"
    elif direction == "short":
        icon = "🔴"
        dir_fa = "فروش"
    else:
        icon = "🟡"
        dir_fa = "خنثی"

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

    # 🔴 TP Ladder — بدون درصد
    tp_levels = signal.get("tp_levels") or {}
    tp_ladder = ""
    if tp_levels.get("tp1"):
        tp1_str = _format_price(tp_levels.get("tp1", 0))
        tp2_str = _format_price(tp_levels.get("tp2", 0))
        tp3_str = _format_price(tp_levels.get("tp3", 0))
        if is_telegram:
            tp_ladder = (
                f"\n\n📊 <b>خروج پله‌ای:</b>\n"
                f"• TP1: <code>{tp1_str}</code>\n"
                f"• TP2: <code>{tp2_str}</code>\n"
                f"• TP3: <code>{tp3_str}</code>"
            )
        else:
            tp_ladder = (
                f"\n\n📊 خروج پله‌ای:\n"
                f"• TP1: {tp1_str}\n"
                f"• TP2: {tp2_str}\n"
                f"• TP3: {tp3_str}"
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

    # 🔴 tp_ladder فقط یک بار (بیرون از blockquote)
    msg = (
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
    return msg


def send_telegram(signal: dict) -> bool:
    if DISABLE_NOTIFY:
        return False
    if _should_skip(signal, "telegram"):
        return False
    if _is_recent_duplicate(signal):
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
        return False
    if _should_skip(signal, "bale"):
        return False
    if _is_recent_duplicate(signal):
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
        logger.info(f"[Notify] ارسال غیرفعال است (DISABLE_NOTIFICATIONS=true)")
        return
    tg = send_telegram(signal)
    bale = send_bale(signal)
    if not tg and not bale:
        logger.info(
            f"[Notifier] هیچ‌کدام ارسال نشد: "
            f"{signal.get('ticker')} {signal.get('tf')} "
            f"strategy={signal.get('strategy')} "
            f"conf={signal.get('confidence')}% "
            f"is_worthwhile={signal.get('is_worthwhile')} "
            f"direction={signal.get('direction')}"
        )
