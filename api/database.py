"""
api/database.py
اتصال به دیتابیس — SQLModel + SQLite (dev) / Postgres (prod)
============================================================
نسخه ۱.۴:
  - ``migrate_db()`` برای اضافه کردن ستون‌های جدید به جداول موجود
    (چون ``create_all`` فقط جدول **جدید** می‌سازد، ستون اضافه نمی‌کند).
  - باگ ۴: ``ADMIN_API_KEY`` در config.
  - تنظیمات production: WAL، busy_timeout، pool_pre_ping.
"""

import logging

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from api.config import settings

logger = logging.getLogger(__name__)

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")

# ─── نام مستعار عمومی (برای ماژول‌های دیگر) ───
is_sqlite = IS_SQLITE

# ═══════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════
if IS_SQLITE:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )

    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        """WAL + busy_timeout — یک‌بار در هر اتصال"""
        cur = dbapi_conn.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.execute("PRAGMA foreign_keys=ON")
        finally:
            cur.close()

else:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )


# ═══════════════════════════════════════════════════════════
# ایجاد جداول
# ═══════════════════════════════════════════════════════════
def init_db() -> None:
    """ایجاد همه جداول — در startup صدا زده می‌شود"""
    from api import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    logger.info(f"✅ دیتابیس آماده ({'sqlite' if IS_SQLITE else 'postgres'})")


# ═══════════════════════════════════════════════════════════
# Migration سبک — برای پروژه‌ی بدون Alembic فعال
# ═══════════════════════════════════════════════════════════
# چرا لازم است: ``create_all`` فقط جدول‌های ناموجود را می‌سازد.
# اگر ستونی به مدل اضافه شود (مثل ``dedup_key`` در باگ ۵)،
# دیتابیس موجود آن را **نمی‌گیرد** و هر INSERT با
# ``no such column`` می‌شکند.
#
# ⚠️ این راه‌حل موقت است. برای production واقعی Alembic را
#    فعال کن (alembic init + autogenerate).
_MIGRATIONS: list[tuple[str, str, str]] = [
    # (جدول, ستون, DDL نوع)
    ("signals_log", "dedup_key", "VARCHAR"),
    # ─── فاز ۶.۵ placeholder ───
    ("signals_log", "orderbook_available", "BOOLEAN NOT NULL DEFAULT 0"),
]


def _column_exists(conn, table: str, column: str) -> bool:
    """آیا ستون در جدول وجود دارد؟"""
    insp = inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _index_exists(conn, table: str, index_name: str) -> bool:
    """آیا ایندکس وجود دارد؟"""
    insp = inspect(conn)
    if table not in insp.get_table_names():
        return False
    return any(i["name"] == index_name for i in insp.get_indexes(table))


def migrate_db() -> dict:
    """
    ستون‌ها و ایندکس‌های جدید را به جداول موجود اضافه می‌کند.

    Returns:
        خلاصه‌ی عملیات: ``{"applied": [...], "skipped": [...], "errors": [...]}``
    """
    summary: dict[str, list[str]] = {"applied": [], "skipped": [], "errors": []}

    with engine.begin() as conn:
        # ─── ۱. ستون‌ها ───
        for table, column, ddl_type in _MIGRATIONS:
            label = f"{table}.{column}"
            try:
                if _column_exists(conn, table, column):
                    summary["skipped"].append(label)
                    continue

                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
                )
                summary["applied"].append(label)
                logger.info(f"[Migrate] ✅ ستون اضافه شد: {label} {ddl_type}")

            except Exception as e:
                summary["errors"].append(f"{label}: {e}")
                logger.error(f"[Migrate] ❌ خطا در {label}: {e}")

        # ─── ۲. بازسازی dedup_key برای ردیف‌های قدیمی ───
        if _column_exists(conn, "signals_log", "dedup_key"):
            try:
                result = conn.execute(
                    text(
                        """
                        UPDATE signals_log
                        SET dedup_key = COALESCE(ticker, '') || '|' ||
                                        COALESCE(tf, '') || '|' ||
                                        COALESCE(signal, '') || '|' ||
                                        COALESCE(source, '') || '|' ||
                                        COALESCE(market_type, '') || '|' ||
                                        COALESCE(risk_profile, '') || '|' ||
                                        COALESCE(strftime('%Y%m%d', timestamp), '')
                        WHERE dedup_key IS NULL
                        """
                    )
                )
                if result.rowcount:
                    logger.info(
                        f"[Migrate] 🔄 dedup_key برای {result.rowcount} "
                        f"ردیف قدیمی پر شد"
                    )
            except Exception as e:
                # ─── برای Postgres دستور strftime وجود ندارد ───
                summary["errors"].append(f"backfill dedup_key: {e}")
                logger.warning(
                    f"[Migrate] پر کردن dedup_key رد شد (غیر-SQLite؟): {e}"
                )

        # ─── ۳. ایندکس یکتای dedup_key (لایه دوم دفاع باگ ۵) ───
        if _column_exists(conn, "signals_log", "dedup_key"):
            for idx_name, ddl in (
                (
                    "ix_signals_log_dedup_key",
                    "CREATE INDEX IF NOT EXISTS ix_signals_log_dedup_key "
                    "ON signals_log (dedup_key)",
                ),
                (
                    "uq_signals_log_dedup_key",
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_signals_log_dedup_key "
                    "ON signals_log (dedup_key)",
                ),
            ):
                try:
                    if _index_exists(conn, "signals_log", idx_name):
                        summary["skipped"].append(idx_name)
                        continue
                    conn.execute(text(ddl))
                    summary["applied"].append(idx_name)
                    logger.info(f"[Migrate] ✅ ایندکس ساخته شد: {idx_name}")
                except Exception as e:
                    summary["errors"].append(f"{idx_name}: {e}")
                    logger.error(f"[Migrate] ❌ خطا در {idx_name}: {e}")

    if summary["applied"]:
        logger.info(f"[Migrate] {len(summary['applied'])} تغییر اعمال شد")
    return summary


# ═══════════════════════════════════════════════════════════
# Dependency برای FastAPI
# ═══════════════════════════════════════════════════════════
def get_session():
    """Session dependency برای FastAPI"""
    with Session(engine) as session:
        yield session
