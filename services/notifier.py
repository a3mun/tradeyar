"""
services/notifier.py
ارسال سیگنال به تلگرام و بله
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


# ═══════════════════════════════════════════════════════════
# ابزار کمکی
# ═══════════════════════════════════════════════════════════
def _fmt(num) -> str:
    """فرمت اعداد با کاما (خوانایی بهتر)."""
    if num is None or num == "—":
        return "—"
    try:
        return f"{int(float(num)):,}"
    except (ValueError, TypeError):
        return str(num)


# ═══════════════════════════════════════════════════════════
# ساخت متن سیگنال
# ═══════════════════════════════════════════════════════════
def _build_signal_message(data: dict, for_telegram: bool = False) -> str:
    """ساخت متن سیگنال با جمع‌بندی تحلیل."""

    ticker = data.get("ticker", "—")
    ticker_clean = ticker.replace("-", "")
    source = data.get("source", "—")
    signal = data.get("signal", "—")
    confidence = data.get("confidence", 0)
    price = _fmt(data.get("price"))
    tp = _fmt(data.get("tp"))
    sl = _fmt(data.get("sl"))
    rr_net = data.get("rr_net", "—")
    market = data.get("market_type", "spot")
    profile = data.get("risk_profile", "aggressive")
    tf = data.get("tf", "—")
    regime = data.get("regime", "range")
    consensus = data.get("consensus", "neutral")
    had_trap = data.get("had_trap", False)
    trap_type = data.get("trap_type")

    scenarios = data.get("scenarios", [])
    override_reason = data.get("override_reason", "")
    neutral_explain = data.get("neutral_explain", {})

    signal_upper = signal.upper()
    if "LONG" in signal_upper:
        signal_emoji, signal_fa = "🟢", "خرید (LONG)"
    elif "SHORT" in signal_upper:
        signal_emoji, signal_fa = "🔴", "فروش (SHORT)"
    else:
        signal_emoji, signal_fa = "⚪", "خنثی"

    market_fa = "اسپات 💵" if market == "spot" else "فیوچرز 📈"
    profile_fa = "جسورانه 🚀" if profile == "aggressive" else "محتاطانه 🛡"

    if regime == "trend":
        if "LONG" in signal_upper:
            regime_fa = "صعودی"
        elif "SHORT" in signal_upper:
            regime_fa = "نزولی"
        else:
            regime_fa = "جهت‌دار"
    elif regime == "range":
        regime_fa = "خنثی (رِنج)"
    else:
        regime_fa = "پرنوسان"

    consensus_fa = (
        "قوی" if consensus == "strong" else "متوسط" if consensus == "medium" else "ضعیف"
    )

    # ─── هشتگ‌های تصادفی (۳ تا) ───
    all_hashtags = [
        f"#{ticker_clean}",
        "#سیگنال",
        "#تحلیل_تکنیکال",
        "#کریپتو",
        "#Trademun",
        "#معامله_گری",
        f"#{source}",
        "#بیت‌کوین",
        "#آلت‌کوین",
        "#ترید",
        "#ارز_دیجیتال",
        "#فارکس",
        "#سرمایه_گذاری",
        "#بازار_مالی",
    ]
    hashtags = random.sample(all_hashtags, 3)

    # ─── جمع‌بندی ───
    conclusion = ""
    if override_reason:
        conclusion = f"⚠️ {override_reason}"
    elif neutral_explain and neutral_explain.get("short"):
        conclusion = f"💡 {neutral_explain['short']}"
    elif scenarios and len(scenarios) > 0:
        sc = scenarios[0]
        cond = sc.get("condition", "")
        act = sc.get("action", "")
        prob = int(sc.get("probability", 0.5) * 100)
        conclusion = f"📊 {cond} (احتمال {prob}%) → {act}"
    elif had_trap and trap_type:
        trap_labels = {
            "bull_trap": "تله صعودی",
            "bear_trap": "تله نزولی",
            "fake_breakout": "شکست جعلی",
            "exhaustion": "خستگی روند",
        }
        conclusion = f"🚨 هشدار: احتمال {trap_labels.get(trap_type, trap_type)}"

    # ─── هشدار تله ───
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
            trap_line = f"\n⚠️ **هشدار:** احتمال {trap_label}\n"

    # ─── جمع‌بندی ───
    if conclusion:
        if for_telegram:
            conclusion_line = f"\n💡 <b>جمع‌بندی:</b> {conclusion}\n"
        else:
            conclusion_line = f"\n💡 **جمع‌بندی:** {conclusion}\n"
    else:
        conclusion_line = ""

    if for_telegram:
        # ─── تلگرام (HTML) ───
        msg = (
            f"📊 <b>سیگنال جدید | Trademun</b>\n"
            f"━━━━━━━━━━━━\n"
            f"💎 <b>نماد:</b> <code>{ticker}</code>\n"
            f"🏦 <b>صرافی:</b> {source}\n"
            f"⏱ <b>تایم‌فریم:</b> {tf}\n"
            f"⚙️ <b>بازار:</b> {market_fa} · {profile_fa}\n"
            f"━━━━━━━━━━━━\n"
            f"{signal_emoji} <b>وضعیت:</b> {signal_fa} ({confidence}%)\n"
            f"💰 <b>قیمت ورود:</b> <code>{price}</code>\n"
            f"🎯 <b>حد سود (TP):</b> <code>{tp}</code>\n"
            f"🛡 <b>حد ضرر (SL):</b> <code>{sl}</code>\n"
            f"⚖️ <b>R:R خالص:</b> <code>{rr_net}</code>\n"
            f"{trap_line}"
            f"{conclusion_line}"
            f"━━━━━━━━━━━━\n"
            f"📈 <b>جهت بازار:</b> {regime_fa} · اجماع {consensus_fa}\n"
            f"🔗 <b>سایت:</b> trademun.ir\n"
            f"━━━━━━━━━━━━\n"
            f"{' '.join(hashtags)}\n"
            f"📢 @trademun"
        )
    else:
        # ─── بله (Markdown) ───
        msg = (
            f"📊 **سیگنال جدید | Trademun**\n"
            f"━━━━━━━━━━━━\n"
            f"💎 **نماد:** `{ticker}`\n"
            f"🏦 **صرافی:** {source}\n"
            f"⏱ **تایم‌فریم:** {tf}\n"
            f"⚙️ **بازار:** {market_fa} · {profile_fa}\n"
            f"━━━━━━━━━━━━\n"
            f"{signal_emoji} **وضعیت:** {signal_fa} ({confidence}%)\n"
            f"💰 **قیمت ورود:** `{price}`\n"
            f"🎯 **حد سود (TP):** `{tp}`\n"
            f"🛡 **حد ضرر (SL):** `{sl}`\n"
            f"⚖️ **R:R خالص:** `{rr_net}`\n"
            f"{trap_line}"
            f"{conclusion_line}"
            f"━━━━━━━━━━━━\n"
            f"📈 **جهت بازار:** {regime_fa} · اجماع {consensus_fa}\n"
            f"🔗 **سایت:** trademun.ir\n"
            f"━━━━━━━━━━━━\n"
            f"{' '.join(hashtags)}\n"
            f"📢 @trademun"
        )
    return msg


# ═══════════════════════════════════════════════════════════
# ارسال به بله و تلگرام
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
    try:
        requests.post(
            f"{TELEGRAM_API_BASE}/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },  # 🔴 اضافه شد
            timeout=30,
        )
        logger.info("[Telegram] ✅")
    except Exception as e:
        logger.warning(f"[Telegram] ❌ {e}")


# ═══════════════════════════════════════════════════════════
# تابع اصلی
# ═══════════════════════════════════════════════════════════
def notify_signal(data: dict) -> None:
    """ارسال سیگنال به بله و تلگرام."""
    try:
        _send_to_bale(_build_signal_message(data, for_telegram=False))
        _send_to_telegram(_build_signal_message(data, for_telegram=True))
    except Exception as e:
        logger.exception(f"[Notifier] خطا: {e}")
