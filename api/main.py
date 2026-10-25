"""
api/main.py
FastAPI app — نقطه ورود
============================================================
🔴 فاز ۱۰.۹.۴: Scheduler به سرویس مستقل (scheduler_worker) منتقل شد.
"""

import logging

from api.routers import analyze, backtest, orderbook, scan, symbols
from api.routers import auth as auth_router
from api.routers import ws as ws_router

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import init_db, migrate_db
from api.routers import analyze, backtest, orderbook, scan, symbols
from api.routers import ws as ws_router
from api.routers import admin, subscription

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
app.include_router(auth_router.router)
app.include_router(subscription.router)
app.include_router(admin.router)  # در بخش include_router
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
        "phase": "فاز ۱۰.۹.۴ — Scheduler Worker",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"ok": True, "status": "healthy"}
