"""
api/main.py
FastAPI app — نقطه ورود
============================================================
🔴 فاز ۱۰.۹.۲: Scheduler توی Thread جداگانه با Event Loop مستقل
   اجرا می‌شه (چون lifespan/startup_event توی داکر کار نمی‌کنن).
"""

import atexit
import asyncio
import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import init_db, migrate_db
from api.routers import analyze, backtest, orderbook, scan, symbols
from api.routers import ws as ws_router
from api.scheduler import start_scheduler, stop_scheduler

# ═══════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Lifespan (فقط DB)
# ═══════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} در حال شروع...")
    init_db()
    migrate_db()
    logger.info("✅ دیتابیس آماده")
    yield
    logger.info("👋 خداحافظ")


# ═══════════════════════════════════════════════════════════
# 🔴 Scheduler Thread (جداگانه با Event Loop مستقل)
# ═══════════════════════════════════════════════════════════
_scheduler_started = False
_scheduler_thread = None


def _run_scheduler_thread():
    """اجرای Scheduler توی thread جداگانه با event loop مستقل."""
    global _scheduler_started
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        start_scheduler()  # 🔴 scheduler داخل این تابع ساخته می‌شه
        _scheduler_started = True
        logger.info("✅ Scheduler از Thread جداگانه شروع شد.")
        while _scheduler_started:
            loop.run_until_complete(asyncio.sleep(60))
    except Exception as e:
        logger.error(f"❌ خطا در Scheduler Thread: {e}")
    finally:
        try:
            loop.close()
        except Exception:
            pass


def _start_scheduler_in_thread():
    """شروع Scheduler توی thread جداگانه."""
    global _scheduler_thread
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return
    _scheduler_thread = threading.Thread(
        target=_run_scheduler_thread,
        daemon=True,
        name="apscheduler-thread",
    )
    _scheduler_thread.start()
    logger.info("🧵 Thread مخصوص Scheduler ساخته شد.")


def _stop_scheduler_safely():
    """توقف امن Scheduler."""
    global _scheduler_started
    _scheduler_started = False
    try:
        stop_scheduler()
    except Exception as e:
        logger.warning(f"[Scheduler] خطا در توقف: {e}")


# ثبت توقف در خروج برنامه
atexit.register(_stop_scheduler_safely)


# ═══════════════════════════════════════════════════════════
# WebSocket sub-app
# ═══════════════════════════════════════════════════════════
ws_app = FastAPI()
ws_app.include_router(ws_router.router)


# ═══════════════════════════════════════════════════════════
# App اصلی
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="دستیار هوشمند تحلیل و مانیتورینگ بازار — Trademun",
    lifespan=lifespan,
)


# ═══════════════════════════════════════════════════════════
# 🔴 شروع Scheduler در Thread جداگانه (بلافاصله)
# ═══════════════════════════════════════════════════════════
_start_scheduler_in_thread()


# ═══════════════════════════════════════════════════════════
# CORS
# ═══════════════════════════════════════════════════════════
_cors_origins = list(settings.CORS_ORIGINS) if settings.CORS_ORIGINS else []
for _dev in ("http://localhost:3000", "http://127.0.0.1:3000"):
    if _dev not in _cors_origins:
        _cors_origins.append(_dev)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# Routers
# ═══════════════════════════════════════════════════════════
app.include_router(analyze.router)
app.include_router(symbols.router)
app.include_router(scan.router)
app.include_router(backtest.router)
app.include_router(orderbook.router)


# ═══════════════════════════════════════════════════════════
# Mount WebSocket
# ═══════════════════════════════════════════════════════════
app.mount("/api", ws_app)


# ═══════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════
@app.get("/", tags=["Health"])
async def root():
    return {
        "ok": True,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "phase": "فاز ۱۰.۹.۲ — Scheduler Fix (Thread)",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"ok": True, "status": "healthy"}
