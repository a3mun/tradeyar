"""
api/scheduler_worker.py
سرویس مستقل Scheduler (جدا از FastAPI)
============================================================
اجرا: python -m api.scheduler_worker
"""

import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api.scheduler import check_pending_signals, auto_scan_and_record

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info(
        "🚀 Scheduler worker starting | PID=%s | UID=%s", os.getpid(), os.getuid()
    )
    scheduler = BlockingScheduler(timezone="UTC")

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

    scheduler.add_job(
        auto_scan_and_record,
        IntervalTrigger(minutes=60),
        id="auto_scan_and_record",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        kwargs={"trigger": "scheduler"},
    )

    logger.info("✅ Registered jobs: %s", [j.id for j in scheduler.get_jobs()])
    logger.info("⏰ Scheduler worker is running. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Scheduler worker stopping")
        raise


if __name__ == "__main__":
    main()
