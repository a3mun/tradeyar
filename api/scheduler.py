"""
api/scheduler.py — راستی‌آزمایی و اسکن خودکار
============================================================
نسخه ۵.۰ · فاز ۱۰.۹.۳
🔴 تغییرات اساسی:
  • جایگزینی AsyncIOScheduler با BackgroundScheduler
    (رفع خطای no running event loop در داکر)
  • توابع async به sync تبدیل شدن
"""

import asyncio
import json
import logging
import threading
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api.config import settings
from services.backtest_service import backtest_all

logger = logging.getLogger(__name__)

# 🔴 Scheduler به صورت global تعریف می‌شه
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
# نمادهای هدف
# ═══════════════════════════════════════════════════════════
FIXED_SYMBOLS = [
    {"ticker": "BTC-USD", "name": "بیت‌کوین (USDT)", "source": "nobitex"},
    {"ticker": "ETH-USD", "name": "اتریوم (USDT)", "source": "nobitex"},
    {"ticker": "PAXG-USD", "name": "پکس گلد (USDT)", "source": "nobitex"},
    {"ticker": "BTC-IRT", "name": "بیت‌کوین (تومان)", "source": "nobitex"},
    {"ticker": "PAXG-IRT", "name": "پکس گلد (تومان)", "source": "nobitex"},
    {"ticker": "BTC-USDT", "name": "بیت‌کوین (USDT)", "source": "wallex"},
    {"ticker": "ETH-USDT", "name": "اتریوم (USDT)", "source": "wallex"},
    {"ticker": "BTC-TMN", "name": "بیت‌کوین (تومان)", "source": "wallex"},
    {"ticker": "PAXG-USDT", "name": "پکس گلد (USDT)", "source": "wallex"},
    {"ticker": "PAXG-TMN", "name": "پکس گلد (تومان)", "source": "wallex"},
    {"ticker": "BTC_USDT", "name": "بیت‌کوین (USDT)", "source": "bitpin"},
    {"ticker": "ETH_USDT", "name": "اتریوم (USDT)", "source": "bitpin"},
    {"ticker": "BTC_IRT", "name": "بیت‌کوین (تومان)", "source": "bitpin"},
    {"ticker": "PAXG_USDT", "name": "پکس گلد (USDT)", "source": "bitpin"},
    {"ticker": "PAXG_IRT", "name": "پکس گلد (تومان)", "source": "bitpin"},
]

SCAN_TIMEFRAMES = ["۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت"]
SCAN_MARKET_TYPE = "futures"
SCAN_RISK_PROFILE = "aggressive"
EXCHANGE_CYCLE = ["nobitex", "wallex", "bitpin"]
_scan_cycle_idx = 0


def _next_exchange() -> str:
    global _scan_cycle_idx
    exchange = EXCHANGE_CYCLE[_scan_cycle_idx % len(EXCHANGE_CYCLE)]
    _scan_cycle_idx += 1
    return exchange


def _load_watchlist_from_file() -> list[dict]:
    path = Path("/app/data/watchlist.json")
    if not path.exists():
        path = Path(__file__).resolve().parent.parent / "data" / "watchlist.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        result = []
        for item in data:
            ticker = item.get("ticker", "")
            if not ticker or not ticker[0].isascii():
                continue
            result.append(
                {
                    "ticker": ticker,
                    "source": item.get("source", "nobitex"),
                    "name": item.get("name", ticker),
                }
            )
        return result
    except Exception as e:
        logger.warning(f"[AutoScan] خطا watchlist: {e!r}")
        return []


# 🔴 توابع sync (نه async) برای BackgroundScheduler
def check_pending_signals(trigger: str = "scheduler") -> dict:
    if _backtest_lock.locked():
        logger.info(f"[Backtest/{trigger}] اجرای قبلی در جریان — رد شد")
        return dict(_EMPTY_RESULT)

    with _backtest_lock:
        logger.info(f"[Backtest/{trigger}] بررسی سیگنال‌ها...")
        try:
            result = backtest_all(max_checks=100)
            updated = result.get("updated", 0)
            if updated > 0:
                logger.info(f"[Backtest/{trigger}] ✅ {updated} به‌روز")
            else:
                logger.info(
                    f"[Backtest/{trigger}] {result.get('checked', 0)} بررسی، تغییری نبود"
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
            }


def auto_scan_and_record(trigger: str = "scheduler"):
    exchange = _next_exchange()
    logger.info(f"[AutoScan/{trigger}] شروع — صرافی: {exchange}")
    try:
        from services.analyzer_service import analyze

        exchange_fixed = [s for s in FIXED_SYMBOLS if s["source"] == exchange]
        exchange_watchlist = [
            w for w in _load_watchlist_from_file() if w["source"] == exchange
        ]
        if not exchange_fixed and not exchange_watchlist:
            return {"ok": True, "exchange": exchange, "recorded": 0, "skipped": True}

        seen = set()
        all_symbols = []
        for s in exchange_fixed + exchange_watchlist:
            key = f"{s['ticker']}|{s['source']}"
            if key not in seen:
                seen.add(key)
                all_symbols.append(s)

        total_recorded = 0
        total_errors = 0
        for sym in all_symbols:
            for tf_name in SCAN_TIMEFRAMES:
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
                # تاخیر بین درخواست‌ها
                import time

                time.sleep(0.5)
        logger.info(
            f"[AutoScan/{trigger}] ✅ {total_recorded} سیگنال از {len(all_symbols)} نماد"
        )
        return {
            "ok": True,
            "exchange": exchange,
            "recorded": total_recorded,
            "symbols_scanned": len(all_symbols),
            "errors": total_errors,
        }
    except Exception as e:
        logger.exception(f"[AutoScan/{trigger}] خطا")
        return {"ok": False, "error": str(e)}


def start_scheduler():
    """راه‌اندازی scheduler با BackgroundScheduler."""
    global scheduler
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] غیرفعال")
        return

    if scheduler is not None and scheduler.running:
        logger.debug("[Scheduler] از قبل اجراست")
        return

    # 🔴 ساخت BackgroundScheduler (نیازی به event loop نداره)
    scheduler = BackgroundScheduler(timezone="UTC")

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

    scheduler.start()
    logger.info("[Scheduler] ✅ راستی‌آزمایی هر ۵ دقیقه + اسکن هر ۶۰ دقیقه")


def stop_scheduler():
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Scheduler] متوقف شد")
