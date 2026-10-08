"""
api/scheduler.py — راستی‌آزمایی خودکار
============================================================
باگ ۶ (نسخه ۱.۵):
  ۱. ``check_pending_signals`` یک ``async def`` بود که ``backtest_all``
     را **sync** صدا می‌زد. یعنی هر اجرای ۳۰ دقیقه‌ای، event loop را
     برای دقیقه‌ها قفل می‌کرد. حالا ``asyncio.to_thread``.
  ۲. قفل process-level اضافه شد: Scheduler و اجرای دستی
     (``POST /backtest/run``) هرگز هم‌زمان روی همان ردیف‌های
     SQLite کار نمی‌کنند.
  ۳. ``max_instances=1`` و ``coalesce=True`` تا APScheduler خودش
     هم instance دوم نسازد.
"""

import asyncio
import logging

import asyncio
from services.analyzer_service import analyze
from core.market_lists import get_top_symbols_by_volume

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api.config import settings
from services.backtest_service import backtest_all

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

# ─── قفل مشترک: Scheduler و manual trigger ───
_backtest_lock = asyncio.Lock()

_EMPTY_RESULT = {
    "ok": False,
    "reason": "already_running",
    "checked": 0,
    "updated": 0,
    "expired": 0,
    "win": 0,
    "loss": 0,
}


async def check_pending_signals(trigger: str = "scheduler") -> dict:
    """
    بررسی سیگنال‌های در انتظار.

    از دو مسیر صدا زده می‌شود:
      • APScheduler (هر ``BACKTEST_INTERVAL_MINUTES``)
      • ``POST /backtest/run`` (اجرای دستی کاربر)

    Args:
        trigger: برچسب مسیر فراخوانی، برای لاگ.

    Returns:
        dict با ``ok`` و شمارنده‌ها. اگر اجرای قبلی در جریان باشد،
        ``ok=False`` و ``reason="already_running"``.
    """
    # ─── اگر اجرای قبلی تمام نشده، رد کن (نه اینکه صف شود) ───
    if _backtest_lock.locked():
        logger.info(f"[Backtest/{trigger}] اجرای قبلی در جریان است — رد شد")
        return dict(_EMPTY_RESULT)

    async with _backtest_lock:
        logger.info(f"[Backtest/{trigger}] بررسی سیگنال‌های در انتظار...")
        try:
            # ─── sync + طولانی → thread جدا، نه event loop ───
            result = await asyncio.to_thread(backtest_all, 200)

            updated = result.get("updated", 0)
            if updated > 0:
                logger.info(
                    f"[Backtest/{trigger}] ✅ {updated} به‌روز شد "
                    f"(win={result.get('win', 0)}, "
                    f"loss={result.get('loss', 0)}, "
                    f"expired={result.get('expired', 0)}, "
                    f"errors={result.get('errors', 0)})"
                )
            else:
                logger.info(
                    f"[Backtest/{trigger}] {result.get('checked', 0)} بررسی شد، "
                    f"تغییری نبود"
                )
            return {"ok": True, **result}

        except Exception as e:
            logger.exception(f"[Backtest/{trigger}] خطای غیرمنتظره")
            return {
                "ok": False,
                "reason": str(e),
                "checked": 0,
                "updated": 0,
                "expired": 0,
                "win": 0,
                "loss": 0,
            }


def start_scheduler():
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] غیرفعال")
        return

    if scheduler.running:
        logger.debug("[Scheduler] از قبل در حال اجراست")
        return

    scheduler.add_job(
        check_pending_signals,
        IntervalTrigger(minutes=settings.BACKTEST_INTERVAL_MINUTES),
        id="check_pending_signals",
        replace_existing=True,
        # ─── حیاتی: بدون این‌ها APScheduler instance موازی می‌سازد ───
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
        kwargs={"trigger": "scheduler"},
    )
    scheduler.start()
    logger.info(f"[Scheduler] فعال — هر {settings.BACKTEST_INTERVAL_MINUTES} دقیقه")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Scheduler] متوقف شد")


async def auto_scan_and_record(trigger: str = "scheduler"):
    """
    اسکن خودکار + ثبت سیگنال‌ها — نسخه ۱.۰
    ============================================================
    هدف: حتی وقتی کاربر نیست، سیگنال‌ها ثبت بشن تا راستی‌آزمایی
    پر بشه.

    ⚠️ فقط نمادهای Top 50 هر صرافی رو اسکن می‌کنه.
    ⚠️ با skip_record=False → سیگنال‌ها ثبت می‌شن.
    """
    logger.info(f"[AutoScan/{trigger}] شروع اسکن خودکار...")

    try:
        from services.analyzer_service import analyze
        from core.market_lists import get_top_symbols_by_volume

        sources = ["nobitex", "bitpin", "wallex"]
        timeframes = ["۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت"]  # ← TF بالا (بهتر)
        risk_profiles = ["aggressive", "conservative"]

        total_recorded = 0

        for source in sources:
            # ─── Top 20 نماد پرحجم ───
            symbols = get_top_symbols_by_volume(source, limit=20)

            for ticker, name in symbols[:20]:
                for tf in timeframes:
                    for risk in risk_profiles:
                        try:
                            r = await asyncio.to_thread(
                                analyze,
                                ticker=ticker,
                                source=source,
                                tf_name=tf,
                                market_type="futures",
                                risk_profile=risk,
                                ticker_name=name,
                                include_extras=False,
                                skip_record=False,  # ← ثبت کن
                            )
                            if r and r.get("signal") != "خنثی":
                                total_recorded += 1
                        except Exception as e:
                            logger.debug(f"[AutoScan] {ticker}/{tf}: {e}")

        logger.info(f"[AutoScan/{trigger}] ✅ {total_recorded} سیگنال ثبت شد")
        return {"ok": True, "recorded": total_recorded}

    except Exception as e:
        logger.exception(f"[AutoScan/{trigger}] خطا")
        return {"ok": False, "error": str(e)}


def start_scheduler():
    if not settings.SCHEDULER_ENABLED:
        return

    if scheduler.running:
        return

    # ─── راستی‌آزمایی سیگنال‌ها (هر ۳۰ دقیقه) ───
    scheduler.add_job(
        check_pending_signals,
        IntervalTrigger(minutes=settings.BACKTEST_INTERVAL_MINUTES),
        id="check_pending_signals",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
        kwargs={"trigger": "scheduler"},
    )

    # ═══ 🔴 اسکن خودکار (هر ۱ ساعت) ═══
    scheduler.add_job(
        auto_scan_and_record,
        IntervalTrigger(minutes=60),  # ← هر ۱ ساعت
        id="auto_scan_and_record",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        kwargs={"trigger": "scheduler"},
    )

    scheduler.start()
    logger.info(
        f"[Scheduler] فعال — راستی‌آزمایی هر {settings.BACKTEST_INTERVAL_MINUTES} دقیقه + "
        f"اسکن خودکار هر ۶۰ دقیقه"
    )
