"""
api/database.py
اتصال به دیتابیس — SQLModel + SQLite (dev) / Postgres (prod)
============================================================
"""

from sqlmodel import SQLModel, Session, create_engine
from api.config import settings

# ═══════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    ),
)


# ═══════════════════════════════════════════════════════════
# ایجاد جداول
# ═══════════════════════════════════════════════════════════
def init_db() -> None:
    """ایجاد همه جداول — در startup صدا زده می‌شود"""
    # ⚠️ import models اینجا لازمه تا SQLModel متادیتا رو بشناسه
    from api import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


# ═══════════════════════════════════════════════════════════
# Dependency برای FastAPI
# ═══════════════════════════════════════════════════════════
def get_session():
    """Session dependency برای FastAPI"""
    with Session(engine) as session:
        yield session
