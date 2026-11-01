"""
api/scheduler_worker.py
سرویس مستقل Scheduler (جدا از FastAPI)
============================================================
اجرا: python -m api.scheduler_worker
"""

import logging
import os
import gzip
import shutil
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from api.scheduler import check_pending_signals, auto_scan_and_record

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def auto_backup():
    """بک‌آپ خودکار هفتگی"""
    from api.config import BASE_DIR
    from api.database import engine

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    is_sqlite_db = engine.url.drivername.startswith("sqlite")

    raw_path = None
    try:
        if is_sqlite_db:
            db_path = BASE_DIR / "data" / "trademun.db"
            raw_path = BASE_DIR / "data" / f"temp_auto_{timestamp}.db"
            shutil.copy2(db_path, raw_path)
            ext = "db"
        else:
            raw_path = BASE_DIR / "data" / f"temp_auto_{timestamp}.sql"
            user = engine.url.username
            dbname = engine.url.database
            cmd = f"pg_dump -U {user} {dbname} > {raw_path}"
            if os.system(cmd) != 0:
                raise Exception("pg_dump failed")
            ext = "sql"

        # فشرده‌سازی
        gz_path = BASE_DIR / "data" / f"Trademun_Backup_{timestamp}.{ext}.gz"
        with open(raw_path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # پاکسازی فایل خام
        if raw_path.exists():
            os.remove(raw_path)
        logger.info(f"[AutoBackup] ✅ بک‌آپ خودکار ساخته شد: {gz_path.name}")
    except Exception as e:
        logger.error(f"[AutoBackup] ❌ خطا: {e}")
        if raw_path and raw_path.exists():
            os.remove(raw_path)


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

    # ⬅️ بک‌آپ خودکار هفتگی (شنبه‌ها ساعت ۳ بامداد)
    scheduler.add_job(
        auto_backup,
        CronTrigger(day_of_week="sat", hour=3, minute=0),
        id="auto_backup",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
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
