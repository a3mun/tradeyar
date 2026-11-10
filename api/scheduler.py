"""
api/scheduler.py — راستی‌آزمایی (نسخه ۷.۰ · فاز ۱۵)
============================================================
🔴 تغییرات:
  • فقط مسئول راستی‌آزمایی است (اسکن به scheduler_worker.py منتقل شد).
  • استفاده از only_due=True برای کاهش فشار (فقط سیگنال‌های تایم‌آوت‌شده).
  • حذف FIXED_SYMBOLS و توابع اسکن.
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
    "errors": 0,
    "skipped": 0,
}


def check_pending_signals(trigger: str = "scheduler") -> dict:
    """بررسی سیگنال‌های pending (فقط تایم‌آوت‌شده‌ها)."""
    if _backtest_lock.locked():
        logger.debug(f"[Backtest/{trigger}] اجرای قبلی در جریان — رد شد")
        return dict(_EMPTY_RESULT)

    with _backtest_lock:
        logger.debug(f"[Backtest/{trigger}] بررسی سیگنال‌ها...")
        try:
            # 🔴 فاز ۱۵: only_due=True برای بررسی فقط سیگنال‌های تایم‌آوت‌شده
            result = backtest_all(max_checks=300, only_due=True)
            updated = result.get("updated", 0)
            errors = result.get("errors", 0)
            skipped = result.get("skipped", 0)

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
                "errors": 0,
                "skipped": 0,
            }


def start_scheduler():
    """استارت اسکنر پس‌زمینه (فقط راستی‌آزمایی)"""
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
            IntervalTrigger(minutes=5),
            id="check_pending_signals",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=120,
            kwargs={"trigger": "scheduler"},
        )
    if not scheduler.running:
        scheduler.start()
        logger.info("[Scheduler] ✅ راستی‌آزمایی هر ۵ دقیقه (فقط تایم‌آوت‌شده‌ها)")


def stop_scheduler():
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Scheduler] متوقف شد")
