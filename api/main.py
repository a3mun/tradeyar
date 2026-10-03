"""
api/main.py
FastAPI app — نقطه ورود
============================================================
اجرا: uvicorn api.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import init_db
from api.routers import analyze, backtest, scan, symbols
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
# Lifespan (startup/shutdown)
# ═══════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── Startup ───
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} در حال شروع...")
    init_db()
    logger.info("✅ دیتابیس آماده")
    start_scheduler()
    yield
    # ─── Shutdown ───
    stop_scheduler()
    logger.info("👋 خداحافظ")


# ═══════════════════════════════════════════════════════════
# App
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="دستیار هوشمند تحلیل و مانیتورینگ بازار — Trademun",
    lifespan=lifespan,
)


# ═══════════════════════════════════════════════════════════
# CORS
# ═══════════════════════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# Routers
# ═══════════════════════════════════════════════════════════
app.include_router(analyze.router)
# (analyze router قبلاً اضافه شده — quote توی همون فایل هست)
app.include_router(symbols.router)
app.include_router(scan.router)
app.include_router(backtest.router)


# ═══════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════
@app.get("/", tags=["Health"])
async def root():
    return {
        "ok": True,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "phase": "فاز ۶ — FastAPI Backend",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"ok": True, "status": "healthy"}
