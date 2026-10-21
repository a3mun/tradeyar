"""
api/main.py
FastAPI app — نقطه ورود
============================================================
اجرا: uvicorn api.main:app --reload

🔴 فاز ۷: WebSocket در sub-app جدا mount می‌شود تا
   CORSMiddleware روی آن اثر نگذارد (رفع 403).

🔴 فاز ۱۰.۹.۱: Scheduler از lifespan به startup_event منتقل شد
   (چون lifespan توی داکر با uvicorn non-root اجرا نمی‌شه).
"""

import logging
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
# Lifespan (startup/shutdown) — فقط DB
# ═══════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── Startup ───
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} در حال شروع...")
    init_db()
    migrate_db()
    logger.info("✅ دیتابیس آماده")
    logger.info("✅ WebSocket manager آماده (/api/ws/live)")
    yield
    # ─── Shutdown ───
    logger.info("👋 خداحافظ")


# ═══════════════════════════════════════════════════════════
# 🔴 WebSocket sub-app — جدا از CORS
# ═══════════════════════════════════════════════════════════
ws_app = FastAPI()
ws_app.include_router(ws_router.router)


# ═══════════════════════════════════════════════════════════
# App اصلی — با CORS
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="دستیار هوشمند تحلیل و مانیتورینگ بازار — Trademun",
    lifespan=lifespan,
)


# ═══════════════════════════════════════════════════════════
# 🔴 Startup/Shutdown Events (برای Scheduler)
# ═══════════════════════════════════════════════════════════
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 اجرای startup_event...")
    try:
        start_scheduler()
        logger.info("✅ Scheduler از startup_event شروع شد.")
    except Exception as e:
        logger.error(f"❌ خطا در شروع Scheduler: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    try:
        stop_scheduler()
        logger.info("👋 Scheduler متوقف شد.")
    except Exception as e:
        logger.error(f"❌ خطا در توقف Scheduler: {e}")


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
# Routers — HTTP
# ═══════════════════════════════════════════════════════════
app.include_router(analyze.router)
app.include_router(symbols.router)
app.include_router(scan.router)
app.include_router(backtest.router)
app.include_router(orderbook.router)


# ═══════════════════════════════════════════════════════════
# 🔴 Mount WebSocket sub-app — خارج از CORS
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
        "phase": "فاز ۱۰.۹.۱ — Scheduler Fix",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"ok": True, "status": "healthy"}
