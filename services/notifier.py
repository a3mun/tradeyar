"""
services/notifier.py
ارسال سیگنال به تلگرام و بله — نسخه ۵.۲ (فاز ۱۶.۵)
============================================================
🔴 تغییرات نسخه ۵.۲:
  • فرمت جدید پیام (مطابق درخواست کاربر):
    - هدر: ticker بالا / اسم فارسی زیرش
    - خط جهت: «🟢خرید (Long)» جدا
    - خط اطمینان جدا
    - خط استراتژی/صرافی جدا (بدون چسبیدن)
    - قیمت‌ها بدون emoji
    - فوتر ساده: trademun.ir - @trademun
  • اضافه شدن #trademun به هشتگ‌ها
  • بقیه (فیلترها، آستانه‌ها، cooldown) دست‌نخورده
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
# آستانه‌های پویا (فاز ۱۶.۵ — نرم‌تر)
# ═══════════════════════════════════════════════════════════
def _get_min_confidence_telegram(strategy: str) -> int:
    return {"scalp": 40, "swing": 50, "position": 60}.get(strategy, 50)


def _get_strong_bypass(strategy: str) -> int:
    return {"scalp": 55, "swing": 65, "position": 70}.get(strategy, 65)


_TF_COOLDOWN_SEC = {
    "۱ دقیقه": 60,
    "۵ دقیقه": 180,
    "۱۵ دقیقه": 300,
    "۳۰ دقیقه": 600,
    "۱ ساعت": 1200,
    "روزانه": 3600,
}
_DEFAULT_COOLDOWN = 300

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
    ticker = signal.get("ticker", "?")
    tf = signal.get("tf", "?")
    strategy = signal.get("strategy", "swing")
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", 0)
    signal_text = signal.get("signal", "")

    if direction not in ("long", "short"):
        logger.debug(f"[Notifier/{channel}] ⏭ {ticker} {tf}: جهت {direction} خنثی")
        return True

    min_conf = _get_min_confidence_telegram(strategy)
    if confidence < min_conf:
        logger.debug(
            f"[Notifier/{channel}] ⏭ {ticker} {tf}: "
            f"اطمینان {confidence}% < {min_conf}% ({strategy})"
        )
        return True

    if "ضعیف" in signal_text and confidence < 45:
        logger.debug(
            f"[Notifier/{channel}] ⏭ {ticker} {tf}: "
            f"سیگنال ضعیف با اطمینان {confidence}% < 45%"
        )
        return True

    traps_summary = signal.get("traps_summary") or {}
    if traps_summary.get("has_high_risk"):
        max_sev = traps_summary.get("max_severity", 0)
        if confidence < 80:
            logger.info(
                f"[Notifier/{channel}] ⏭ {ticker} {tf}: "
                f"تله پرخطر (severity={max_sev}) + اطمینان {confidence}% < 80%"
            )
            return True

    if confidence >= _get_strong_bypass(strategy):
        logger.info(
            f"[Notifier/{channel}] ⚡ قوی (bypass): {ticker} {tf} conf={confidence}%"
        )
        return False

    if strategy in ("scalp", "swing"):
        return False

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


# 🔴 فاز ۱۶.۵ — ۱۰ هشتگ رندوم هفتگی
RANDOM_HASHTAGS = [
    "#سیگنال_فارکس",
    "#تحلیل_تکنیکال",
    "#معامله_گری",
    "#ترید_روزانه",
    "#بازار_مالی",
    "#ارز_دیجیتال",
    "#تحلیل_بازار",
    "#سرمایه_گذاری",
    "#تریدر_حرفه_ای",
    "#نوسان_گیری",
]


def _get_random_hashtag() -> str:
    """
    🔴 فاز ۱۶.۵ — انتخاب هشتگ رندوم بر اساس شماره هفته سال.
    یعنی هر هفته یک هشتگ ثابت از لیست ۱۰ تایی.
    """
    from datetime import datetime

    try:
        week_num = datetime.now().isocalendar()[1]  # 1-53
        idx = week_num % len(RANDOM_HASHTAGS)
        return RANDOM_HASHTAGS[idx]
    except Exception:
        return RANDOM_HASHTAGS[0]


# 🔴 فاز ۱۶.۵ — ۲۰ هشتگ رندوم روزانه
RANDOM_HASHTAGS = [
    "#سیگنال_فارکس",
    "#سیگنال_کریپتو",
    "#سیگنال_طلا",
    "#تحلیل_تکنیکال",
    "#تحلیل_بازار",
    "#مقایسه_صرافی",
    "#صرافی_ایرانی",
    "#نوبیتکس",
    "#بیت‌پین",
    "#والکس",
    "#طلا_و_دلار",
    "#انس_طلا",
    "#ارز_دیجیتال",
    "#بورس_ایران",
    "#معامله_گری",
    "#ترید_روزانه",
    "#سرمایه_گذاری",
    "#نوسان_گیری",
    "#تریدر_حرفه_ای",
    "#آموزش_ترید",
]


def _get_random_hashtags_daily(count: int = 4) -> list[str]:
    """انتخاب ۴ هشتگ تصادفی که در طول یک روز ثابت می‌مونن"""
    import random
    from datetime import datetime

    try:
        day_of_year = datetime.now().timetuple().tm_yday
        rng = random.Random(day_of_year)
        return rng.sample(RANDOM_HASHTAGS, min(count, len(RANDOM_HASHTAGS)))
    except Exception:
        return RANDOM_HASHTAGS[:count]


def _get_hashtags(signal: dict) -> str:
    """۵ هشتگ: #تریدمون + ۴ تای رندوم روزانه"""
    tags = ["#تریدمون"]
    daily = _get_random_hashtags_daily(4)
    for h in daily:
        if h not in tags:
            tags.append(h)
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
    min_conf = _get_min_confidence_telegram(strategy)
    if confidence >= 85:
        return ("💎", "اطمینان طلایی")
    elif confidence >= 70:
        return ("🔥", "اطمینان قوی")
    elif confidence >= min_conf + 15:
        return ("✅", "اطمینان معمولی")
    elif confidence >= min_conf:
        return ("⚠️", "اطمینان ضعیف")
    return ("⚪", "بدون اطمینان")


def _build_message(signal: dict, is_telegram: bool = True) -> str:
    """🔴 فاز ۱۶.۵ — فرمت نهایی (قیمت‌ها + خروج پله‌ای توی blockquote)"""
    direction = signal.get("direction", "neutral")
    confidence = signal.get("confidence", 0)
    market_type = signal.get("market_type", "spot")
    risk_profile = signal.get("risk_profile", "aggressive")
    strategy = signal.get("strategy", "swing")

    # آیکون و متن جهت
    direction_icon = (
        "🟢" if direction == "long" else ("🔴" if direction == "short" else "🟡")
    )
    direction_fa = (
        "خرید" if direction == "long" else ("فروش" if direction == "short" else "خنثی")
    )
    direction_en = (
        "Long"
        if direction == "long"
        else ("Short" if direction == "short" else "Neutral")
    )

    # اطمینان
    conf_icon, conf_fa = _confidence_label(confidence, strategy)

    # استراتژی
    strategy_icon, strategy_fa = _get_strategy_label(strategy)
    market_fa = "فیوچرز" if market_type == "futures" else "اسپات"
    risk_fa = "جسورانه" if risk_profile == "aggressive" else "محتاطانه"

    # صرافی
    source = signal.get("source", "")
    source_map = {
        "nobitex": "🟣Nobitex",
        "bitpin": "🟢Bitpin",
        "wallex": "🔵Wallex",
        "tabdeal": "🟠Tabdeal",
        "tsetmc": "🇮🇷TSETMC",
        "forex": "🌍 فارکس",
    }
    source_fa = source_map.get(source, source)

    # TF کوتاه
    tf_short = {
        "۱ دقیقه": "1m",
        "۵ دقیقه": "5m",
        "۱۵ دقیقه": "15m",
        "۳۰ دقیقه": "30m",
        "۱ ساعت": "1h",
        "روزانه": "1d",
    }.get(signal.get("tf", ""), signal.get("tf", ""))

    # قیمت‌ها
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

    # تله
    trap_text = _get_trap_status(signal)
    trap_line = f"\n⚠️ {trap_text}" if trap_text else ""

    # تاریخ
    date_str = _format_shamsi_date()
    hashtags = _get_hashtags(signal)

    # ticker و name
    ticker = signal.get("ticker", "")
    name = signal.get("name", "")

    # ═══ ساخت هدر ═══
    golden_mark = "💎 " if confidence >= 85 else ""

    # ═══ ساخت blockquote (قیمت‌ها + خروج پله‌ای) ═══
    if is_telegram:
        # تلگرام: HTML داخل blockquote
        prices_body = (
            f"ورود: <code>{price_str}</code>\n"
            f"حد سود: <code>{tp_str}</code>\n"
            f"حد ضرر: <code>{sl_str}</code>\n"
            f"ریسک به ریوارد: <b>{rr_str}</b>"
        )
        if tp_ladder:
            # tp_ladder رو داخل blockquote قرار می‌دیم (بدون \n\n اضافی)
            tp_ladder_inner = tp_ladder.replace("\n\n📊 ", "\n\n📊 ")
            prices_block = f"<blockquote>{prices_body}{tp_ladder_inner}</blockquote>"
        else:
            prices_block = f"<blockquote>{prices_body}</blockquote>"
    else:
        # بله: HTML ساپورت نمی‌کنه، فقط متن
        prices_body = (
            f"ورود: {price_str}\n"
            f"حد سود: {tp_str}\n"
            f"حد ضرر: {sl_str}\n"
            f"ریسک به ریوارد: {rr_str}"
        )
        if tp_ladder:
            prices_block = f"{prices_body}{tp_ladder}"
        else:
            prices_block = prices_body

    # ═══ ساخت header ═══
    if is_telegram:
        header_line = f"     {golden_mark}<code>{ticker}</code> / <b>TF: {tf_short}</b>"
        if name and name.strip() != ticker.strip():
            header_line += f"\n{name}"
        direction_line = f" {direction_icon}<b>{direction_fa}</b> ({direction_en})"
        conf_line = f"{conf_icon} {conf_fa} ({confidence}%)"
        strategy_line = (
            f"{strategy_icon} <b>{strategy_fa}</b> | {market_fa} | {risk_fa}"
        )
    else:
        header_line = f"     {golden_mark}{ticker} / TF: {tf_short}"
        if name and name.strip() != ticker.strip():
            header_line += f"\n{name}"
        direction_line = f" {direction_icon}{direction_fa} ({direction_en})"
        conf_line = f"{conf_icon} {conf_fa} ({confidence}%)"
        strategy_line = f"{strategy_icon} {strategy_fa} | {market_fa} | {risk_fa}"

    # ═══ ساخت نهایی ═══
    return (
        f"━━━━━{direction_icon}━━━━━\n"
        f"{header_line}\n\n"
        f"{direction_line}\n"
        f"{conf_line}\n"
        f"{strategy_line}\n"
        f"{source_fa}"
        f"{trap_line}\n\n"
        f"{prices_block}\n\n"  # ← حالا کل block (قیمت + tp_ladder) داخل blockquote
        f"━━━━━{direction_icon}━━━━━\n"
        f"{date_str}\n\n\n"
        f"🌠 تحلیل بازارهای مالی با تریدمون\n"
        f"trademun.ir - @trademun\n\n"
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
    bale = send_bale(dict(signal))
    if not tg and not bale:
        logger.info(
            f"[Notifier] هیچ‌کدام ارسال نشد: "
            f"{signal.get('ticker')} {signal.get('tf')} "
            f"strategy={signal.get('strategy')} conf={signal.get('confidence')}%"
        )
