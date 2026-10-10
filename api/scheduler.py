"""
api/scheduler.py — راستی‌آزمایی و اسکن خودکار
============================================================
نسخه ۲.۰ · فاز ۱۰.۱
🔴 تغییرات:
  • merge دوتا start_scheduler (باگ قبلی: یکی overwrite می‌کرد)
  • jobs به‌صورت کامل ثبت می‌شن:
      - check_pending_signals (هر BACKTEST_INTERVAL_MINUTES)
      - auto_scan_and_record   (هر ۶۰ دقیقه)
  • به check_pending_signals فقط سیگنال‌های **قدیمی‌تر از ۵ دقیقه**
    (نه هر بار همه)
"""

import asyncio
import logging

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
    """
    if _backtest_lock.locked():
        logger.info(f"[Backtest/{trigger}] اجرای قبلی در جریان است — رد شد")
        return dict(_EMPTY_RESULT)

    async with _backtest_lock:
        logger.info(f"[Backtest/{trigger}] بررسی سیگنال‌های در انتظار...")
        try:
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


async def auto_scan_and_record(trigger: str = "scheduler"):
    """
    اسکن خودکار + ثبت سیگنال‌ها.

    ⚠️ فقط نمادهای Top 20 هر صرافی رو اسکن می‌کنه.
    """
    logger.info(f"[AutoScan/{trigger}] شروع اسکن خودکار...")

    try:
        from services.analyzer_service import analyze
        from core.market_lists import get_top_symbols_by_volume

        sources = ["nobitex", "bitpin", "wallex"]
        timeframes = ["۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت"]
        risk_profiles = ["aggressive", "conservative"]

        total_recorded = 0

        for source in sources:
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
                                skip_record=False,
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


# ═══════════════════════════════════════════════════════════
# 🔴 یک start_scheduler واحد — نه دو تا!
# ═══════════════════════════════════════════════════════════
def start_scheduler():
    """
    راه‌اندازی scheduler با **هر دو** job.

    ═══ ریشه‌ی باگ نسخه‌ی قبلی ═══
    فایل قبلی **دو تابع** start_scheduler داشت. دومی روی اولی
    overwrite می‌شد. نتیجه: job ``check_pending_signals``
    **هیچ‌وقت ثبت نمی‌شد** و راستی‌آزمایی خودکار کار نمی‌کرد
    (شاهد: ۷۱ pending مونده).

    ═══ نسخه ۱۰.۱ ═══
    یک تابع واحد که **هر دو** job رو ثبت می‌کنه.
    """
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] غیرفعال (SCHEDULER_ENABLED=false)")
        return

    if scheduler.running:
        logger.debug("[Scheduler] از قبل در حال اجراست")
        return

    # ═══ job ۱: راستی‌آزمایی سیگنال‌ها ═══
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

    # ═══ job ۲: اسکن خودکار ═══
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

    scheduler.start()
    logger.info(
        f"[Scheduler] ✅ فعال — راستی‌آزمایی هر "
        f"{settings.BACKTEST_INTERVAL_MINUTES} دقیقه + "
        f"اسکن خودکار هر ۶۰ دقیقه"
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Scheduler] متوقف شد")
