"""
api/scheduler.py — راستی‌آزمایی و اسکن خودکار
============================================================
نسخه ۶.۳ · فاز ۱۰.۹.۶
🔴 تغییرات نهایی:
  • ۱۰ نماد در هر ۳ صرافی (نوبیتکس، بیت‌پین، والکس)
  • تایم‌فریم‌ها: نوبیتکس/بیت‌پین کامل، والکس فقط ۱ ساعت و روزانه
  • اسکن هر ۱۵ دقیقه (چرخشی)
  • راستی‌آزمایی هر ۳ دقیقه
  • misfire_grace_time=600 برای جلوگیری از نادیده گرفتن Job
"""

import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api.config import settings
from services.backtest_service import backtest_all

logger = logging.getLogger(__name__)

scheduler: BackgroundScheduler | None = None
_backtest_lock = threading.Lock()

_EMPTY_RESULT = {
    "ok": False,
    "reason": "already_running",
    "checked": 0,
    "updated": 0,
    "expired": 0,
    "win": 0,
    "loss": 0,
}


# ═══════════════════════════════════════════════════════════
# نمادهای ثابت (۱۰ نماد در هر ۳ صرافی)
# ═══════════════════════════════════════════════════════════
FIXED_SYMBOLS = [
    # ─── nobitex ───
    {"ticker": "BTC-IRT", "name": "بیت‌کوین (تومان)", "source": "nobitex"},
    {"ticker": "BTC-USD", "name": "بیت‌کوین (USDT)", "source": "nobitex"},
    {"ticker": "XAUT-IRT", "name": "تتر گلد (تومان)", "source": "nobitex"},
    {"ticker": "PAXG-USD", "name": "پکس گلد (USDT)", "source": "nobitex"},
    {"ticker": "PAXG-IRT", "name": "پکس گلد (تومان)", "source": "nobitex"},
    {"ticker": "SOL-USD", "name": "سولانا", "source": "nobitex"},
    {"ticker": "XRP-USD", "name": "ریپل", "source": "nobitex"},
    {"ticker": "DOGE-USD", "name": "دوج‌کوین", "source": "nobitex"},
    {"ticker": "ETH-USD", "name": "اتریوم", "source": "nobitex"},
    # ─── bitpin ───
    {"ticker": "BTC_IRT", "name": "بیت‌کوین (تومان)", "source": "bitpin"},
    {"ticker": "BTC_USDT", "name": "بیت‌کوین (USDT)", "source": "bitpin"},
    {"ticker": "PAXG_IRT", "name": "پکس گلد (تومان)", "source": "bitpin"},
    {"ticker": "PAXG_USDT", "name": "پکس گلد (USDT)", "source": "bitpin"},
    {"ticker": "SOL_USDT", "name": "سولانا", "source": "bitpin"},
    {"ticker": "XRP_USDT", "name": "ریپل", "source": "bitpin"},
    {"ticker": "DOGE_USDT", "name": "دوج‌کوین", "source": "bitpin"},
    {"ticker": "ETH_USDT", "name": "اتریوم", "source": "bitpin"},
    # ─── wallex ───
    {"ticker": "BTC-TMN", "name": "بیت‌کوین (تومان)", "source": "wallex"},
    {"ticker": "BTC-USDT", "name": "بیت‌کوین (USDT)", "source": "wallex"},
    {"ticker": "PAXG-TMN", "name": "پکس گلد (تومان)", "source": "wallex"},
    {"ticker": "PAXG-USDT", "name": "پکس گلد (USDT)", "source": "wallex"},
    {"ticker": "SOL-USDT", "name": "سولانا", "source": "wallex"},
    {"ticker": "XRP-USDT", "name": "ریپل", "source": "wallex"},
    {"ticker": "DOGE-USDT", "name": "دوج‌کوین", "source": "wallex"},
    {"ticker": "ETH-USDT", "name": "اتریوم", "source": "wallex"},
]

# 🔴 تایم‌فریم‌های مخصوص هر صرافی
TIMEFRAMES_BY_SOURCE = {
    "nobitex": ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"],
    "bitpin": ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"],
    "wallex": ["۱ ساعت", "روزانه"],  # فقط ۱ ساعت و روزانه
}

SCAN_MARKET_TYPE = "futures"
SCAN_RISK_PROFILE = "aggressive"
EXCHANGE_CYCLE = ["nobitex", "wallex", "bitpin"]
_scan_cycle_idx = 0


def _next_exchange() -> str:
    global _scan_cycle_idx
    exchange = EXCHANGE_CYCLE[_scan_cycle_idx % len(EXCHANGE_CYCLE)]
    _scan_cycle_idx += 1
    return exchange


def check_pending_signals(trigger: str = "scheduler") -> dict:
    if _backtest_lock.locked():
        logger.info(f"[Backtest/{trigger}] اجرای قبلی در جریان — رد شد")
        return dict(_EMPTY_RESULT)
    with _backtest_lock:
        logger.info(f"[Backtest/{trigger}] بررسی سیگنال‌ها...")
        try:
            result = backtest_all(max_checks=300)
            updated = result.get("updated", 0)
            errors = result.get("errors", 0)
            skipped = result.get("skipped", 0)

            # 🔴 لاگ کامل شامل errors و skipped
            logger.info(
                f"[Backtest/{trigger}] ✅ updated={updated} | "
                f"errors={errors} | skipped={skipped} | "
                f"win={result.get('win', 0)} | loss={result.get('loss', 0)}"
            )
            return {"ok": True, **result}
        except Exception as e:
            logger.exception(f"[Backtest/{trigger}] خطا")
            return {
                "ok": False,
                "reason": str(e),
                "checked": 0,
                "updated": 0,
                "expired": 0,
                "win": 0,
                "loss": 0,
                "errors": 0,  # 🔴 اضافه شد
                "skipped": 0,  # 🔴 اضافه شد
            }


def auto_scan_and_record(trigger: str = "scheduler"):
    exchange = _next_exchange()
    logger.info(f"[AutoScan/{trigger}] شروع — صرافی: {exchange}")
    try:
        from services.analyzer_service import analyze

        exchange_fixed = [s for s in FIXED_SYMBOLS if s["source"] == exchange]
        if not exchange_fixed:
            return {"ok": True, "exchange": exchange, "recorded": 0, "skipped": True}

        timeframes = TIMEFRAMES_BY_SOURCE.get(
            exchange, ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"]
        )

        total_recorded = 0
        total_errors = 0
        for sym in exchange_fixed:
            for tf_name in timeframes:
                try:
                    r = analyze(
                        ticker=sym["ticker"],
                        source=sym["source"],
                        tf_name=tf_name,
                        market_type=SCAN_MARKET_TYPE,
                        risk_profile=SCAN_RISK_PROFILE,
                        ticker_name=sym["name"],
                        include_extras=False,
                        skip_record=False,
                    )
                    if r and r.get("signal") != "خنثی":
                        total_recorded += 1
                except Exception as e:
                    logger.debug(f"[AutoScan] {sym['ticker']} {tf_name}: {e!r}")
                    total_errors += 1
                import time

                time.sleep(0.5)
        logger.info(
            f"[AutoScan/{trigger}] ✅ {total_recorded} سیگنال از {len(exchange_fixed)} نماد × {len(timeframes)} TF (خطا: {total_errors})"
        )
        return {
            "ok": True,
            "exchange": exchange,
            "recorded": total_recorded,
            "symbols_scanned": len(exchange_fixed),
            "timeframes": timeframes,
            "errors": total_errors,
        }
    except Exception as e:
        logger.exception(f"[AutoScan/{trigger}] خطا")
        return {"ok": False, "error": str(e)}


def start_scheduler():
    global scheduler
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] غیرفعال")
        return
    if scheduler is not None and scheduler.running:
        logger.debug("[Scheduler] از قبل اجراست")
        return
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone="UTC")
    if not scheduler.get_jobs():
        scheduler.add_job(
            check_pending_signals,
            IntervalTrigger(minutes=3),
            id="check_pending_signals",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=120,
            kwargs={"trigger": "scheduler"},
        )
        scheduler.add_job(
            auto_scan_and_record,
            IntervalTrigger(minutes=15),
            id="auto_scan_and_record",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=600,  # 🔴 افزایش یافت
            kwargs={"trigger": "scheduler"},
        )
    if not scheduler.running:
        scheduler.start()
        logger.info("[Scheduler] ✅ راستی‌آزمایی هر ۳ دقیقه + اسکن هر ۱۵ دقیقه")


def stop_scheduler():
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Scheduler] متوقف شد")
