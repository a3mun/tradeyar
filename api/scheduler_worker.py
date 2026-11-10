"""
api/scheduler_worker.py
سرویس مستقل Scheduler (جدا از FastAPI) — نسخه ۸.۰ · فاز ۱۵
============================================================
🔴 تغییرات فاز ۱۵ (کم‌فشار + دقیق):
  • چرخه ترکیبی: اسکالپ ۱ ساعته، سوئینگ ۲ ساعته، پوزیشن ۴ ساعته.
  • راستی‌آزمایی هر ۵ دقیقه (فقط برای سیگنال‌های تایم‌آوت شده).
  • بدون همزمانی اسکن‌ها.
"""

import logging
import os
import gzip
import shutil
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# ایمپورت‌های پایه
from api.config import settings
from api.scheduler import check_pending_signals
from services.analyzer_service import analyze

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# لیست نمادها
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


def is_irt(ticker: str) -> bool:
    """تشخیص اینکه آیا نماد تومانی است یا خیر"""
    upper = ticker.upper()
    return "-IRT" in upper or "-TMN" in upper or "_IRT" in upper


# ═══════════════════════════════════════════════════════════
# تسک‌های اسکن
# ═══════════════════════════════════════════════════════════


def run_scalp_scan():
    """اسکن اسکالپ — هر ۱ ساعت"""
    logger.info("[Scan:Scalp] شروع...")
    symbols = [
        s
        for s in FIXED_SYMBOLS
        if s["source"] in ("nobitex", "bitpin") and not is_irt(s["ticker"])
    ]
    tfs = ["۱ دقیقه", "۵ دقیقه"]

    count = 0
    for sym in symbols:
        for tf in tfs:
            try:
                analyze(
                    ticker=sym["ticker"],
                    source=sym["source"],
                    tf_name=tf,
                    market_type="futures",
                    risk_profile="aggressive",
                    strategy="scalp",
                    ticker_name=sym["name"],
                    skip_record=False,
                )
                count += 1
            except Exception as e:
                logger.debug(f"[Scan:Scalp] {sym['ticker']} {tf}: {e!r}")
    logger.info(f"[Scan:Scalp] ✅ {count} تحلیل انجام شد.")


def run_swing_scan():
    """اسکن سوئینگ — هر ۲ ساعت"""
    logger.info("[Scan:Swing] شروع...")
    symbols = [s for s in FIXED_SYMBOLS if s["source"] in ("nobitex", "bitpin")]
    aggressive_tfs = ["۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه"]
    conservative_tfs = ["۱ ساعت", "روزانه"]

    count = 0
    for sym in symbols:
        for tf in aggressive_tfs:
            try:
                analyze(
                    ticker=sym["ticker"],
                    source=sym["source"],
                    tf_name=tf,
                    market_type="futures",
                    risk_profile="aggressive",
                    strategy="swing",
                    ticker_name=sym["name"],
                    skip_record=False,
                )
                count += 1
            except Exception as e:
                logger.debug(f"[Scan:Swing:agg] {sym['ticker']} {tf}: {e!r}")
        for tf in conservative_tfs:
            try:
                analyze(
                    ticker=sym["ticker"],
                    source=sym["source"],
                    tf_name=tf,
                    market_type="futures",
                    risk_profile="conservative",
                    strategy="swing",
                    ticker_name=sym["name"],
                    skip_record=False,
                )
                count += 1
            except Exception as e:
                logger.debug(f"[Scan:Swing:cons] {sym['ticker']} {tf}: {e!r}")
    logger.info(f"[Scan:Swing] ✅ {count} تحلیل انجام شد.")


def run_position_scan():
    """اسکن پوزیشن — هر ۴ ساعت"""
    logger.info("[Scan:Position] شروع...")
    symbols = [
        s for s in FIXED_SYMBOLS if s["source"] in ("nobitex", "bitpin", "wallex")
    ]
    tfs = ["۱ ساعت", "روزانه"]

    count = 0
    for sym in symbols:
        for tf in tfs:
            try:
                analyze(
                    ticker=sym["ticker"],
                    source=sym["source"],
                    tf_name=tf,
                    market_type="futures",
                    risk_profile="conservative",
                    strategy="position",
                    ticker_name=sym["name"],
                    skip_record=False,
                )
                count += 1
            except Exception as e:
                logger.debug(f"[Scan:Position] {sym['ticker']} {tf}: {e!r}")
    logger.info(f"[Scan:Position] ✅ {count} تحلیل انجام شد.")


def auto_backup():
    """بک‌آپ خودکار هفتگی"""
    from api.database import engine, BASE_DIR

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

        gz_path = BASE_DIR / "data" / f"Trademun_Backup_{timestamp}.{ext}.gz"
        with open(raw_path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        if raw_path.exists():
            os.remove(raw_path)
        logger.info(f"[AutoBackup] ✅ بک‌آپ خودکار ساخته شد: {gz_path.name}")
    except Exception as e:
        logger.error(f"[AutoBackup] ❌ خطا: {e}")
        if raw_path and raw_path.exists():
            os.remove(raw_path)


def main():
    logger.info("🚀 Scheduler worker starting | PID=%s", os.getpid())
    scheduler = BlockingScheduler(timezone="UTC")

    # ═══════════════════════════════════════════════════════════
    # چرخه ترکیبی
    # ═══════════════════════════════════════════════════════════

    # ۱. اسکالپ (هر ۱ ساعت، دقیقه 0)
    scheduler.add_job(
        run_scalp_scan,
        CronTrigger(minute="0"),
        id="scan_scalp",
        max_instances=1,
        coalesce=True,
    )

    # ۲. سوئینگ (هر ۲ ساعت، دقیقه 15)
    scheduler.add_job(
        run_swing_scan,
        CronTrigger(minute="15", hour="*/2"),
        id="scan_swing",
        max_instances=1,
        coalesce=True,
    )

    # ۳. پوزیشن (هر ۴ ساعت، دقیقه 30)
    scheduler.add_job(
        run_position_scan,
        CronTrigger(minute="30", hour="*/4"),
        id="scan_position",
        max_instances=1,
        coalesce=True,
    )

    # ۴. راستی‌آزمایی (هر 5 دقیقه — فقط سیگنال‌های تایم‌آوت شده)
    scheduler.add_job(
        check_pending_signals,
        IntervalTrigger(minutes=5),
        id="backtest_check",
        max_instances=1,
        coalesce=True,
        kwargs={"trigger": "scheduler"},
    )

    # بک‌آپ خودکار هفتگی (شنبه‌ها ساعت ۳ بامداد)
    scheduler.add_job(
        auto_backup,
        CronTrigger(day_of_week="sat", hour=3, minute=0),
        id="auto_backup",
        max_instances=1,
        coalesce=True,
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
