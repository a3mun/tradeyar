"""
api/main.py
FastAPI app — نقطه ورود
============================================================
اجرا: uvicorn api.main:app --reload

🔴 فاز ۷: WebSocket در sub-app جدا mount می‌شود تا
   CORSMiddleware روی آن اثر نگذارد (رفع 403).
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
# Lifespan (startup/shutdown)
# ═══════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── Startup ───
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} در حال شروع...")
    init_db()
    migrate_db()
    logger.info("✅ دیتابیس آماده")
    start_scheduler()
    logger.info("✅ WebSocket manager آماده (/api/ws/live)")
    yield
    # ─── Shutdown ───
    stop_scheduler()
    logger.info("👋 خداحافظ")


# ═══════════════════════════════════════════════════════════
# 🔴 WebSocket sub-app — جدا از CORS
# ═══════════════════════════════════════════════════════════
# چرا: CORSMiddleware در Starlette کل app رو wrap می‌کنه،
# حتی اگه include_router قبلش باشه. تنها راه واقعی، جدا کردن
# WS در یه app مستقل با mount در path مشخصه.
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
# CORS
# ═══════════════════════════════════════════════════════════
# ⚠️ WebSocket خودش CORS جدا داره و این تنظیم روش اثر نداره.
# برای تست محلی، localhost:3000 و 127.0.0.1:3000 هر دو مجازن.
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
# مسیر نهایی: /api/ws/live
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
        "phase": "فاز ۷ — WebSocket زنده",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"ok": True, "status": "healthy"}
