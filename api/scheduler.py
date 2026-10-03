"""
api/scheduler.py — با راستی‌آزمایی خودکار
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.config import settings
from services.backtest_service import backtest_all

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")


async def check_pending_signals():
    """بررسی سیگنال‌های در انتظار"""
    logger.info("[Scheduler] بررسی سیگنال‌های در انتظار...")
    try:
        result = backtest_all()
        if result.get("updated", 0) > 0:
            logger.info(
                f"[Scheduler] ✅ {result['updated']} به‌روز شد "
                f"(win={result['win']}, loss={result['loss']}, expired={result['expired']})"
            )
        else:
            logger.info(f"[Scheduler] {result['checked']} بررسی شد، هیچی عوض نشد")
    except Exception as e:
        logger.error(f"[Scheduler] خطا: {e}")


def start_scheduler():
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] غیرفعال")
        return

    scheduler.add_job(
        check_pending_signals,
        "interval",
        minutes=settings.BACKTEST_INTERVAL_MINUTES,
        id="check_pending_signals",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"[Scheduler] فعال — هر {settings.BACKTEST_INTERVAL_MINUTES} دقیقه")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] متوقف شد")
