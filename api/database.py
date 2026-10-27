"""
api/database.py
اتصال دیتابیس + session
"""

import logging

from sqlalchemy import create_engine, inspect, text
from sqlmodel import Session, SQLModel

from api.config import settings

logger = logging.getLogger(__name__)

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )


def get_session():
    """FastAPI dependency — session per request."""
    with Session(engine) as session:
        yield session


def init_db():
    """ایجاد جداول اگر وجود نداشته باشن."""
    from api.models import SignalLog  # noqa

    SQLModel.metadata.create_all(engine)
    logger.info(f"✅ دیتابیس آماده ({'sqlite' if is_sqlite else 'postgres'})")


def _add_missing_columns_sqlite(inspector, conn):
    """migration برای SQLite — ستون‌های جدید signallog."""
    if "signallog" not in inspector.get_table_names():
        return
    existing_cols = {col["name"] for col in inspector.get_columns("signallog")}
    new_columns = [
        ("rr_net", "REAL"),
        ("fee_pct", "REAL"),
        ("fee_ratio", "REAL"),
        ("breakeven_pct", "REAL"),
        ("is_worthwhile", "INTEGER"),
        ("timeframe_viable", "INTEGER"),
        ("rr_decay_pct", "REAL"),
        ("execution_cost_json", "TEXT"),
        ("orderbook_available", "INTEGER DEFAULT 0"),
        ("trade_side_irt", "INTEGER DEFAULT 0"),
        ("trend_correct", "INTEGER"),
        ("expired_at_price", "REAL"),
        ("expired_pnl_pct", "REAL"),
        ("expired_bias", "TEXT"),
        ("is_weak", "INTEGER DEFAULT 0"),
        ("exit_reason", "TEXT"),
        ("trend_predicted_at_entry", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            try:
                conn.execute(
                    text(f"ALTER TABLE signallog ADD COLUMN {col_name} {col_type}")
                )
                logger.info(f"  + ستون {col_name} اضافه شد")
            except Exception as e:
                logger.debug(f"  - ستون {col_name}: {e}")


def _add_missing_columns_postgres(inspector, conn):
    """
    migration برای PostgreSQL — همه‌ی ستون‌های اضافه‌شده در طول فازها.
    با IF NOT EXISTS امن هست.
    """
    existing_tables = set(inspector.get_table_names())

    # ─── signallog: ستون‌های فاز ۸.۲ به بعد ───
    if "signallog" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("signallog")}
        signallog_cols = [
            ("rr_net", "DOUBLE PRECISION"),
            ("fee_pct", "DOUBLE PRECISION"),
            ("fee_ratio", "DOUBLE PRECISION"),
            ("breakeven_pct", "DOUBLE PRECISION"),
            ("is_worthwhile", "BOOLEAN"),
            ("timeframe_viable", "BOOLEAN"),
            ("rr_decay_pct", "DOUBLE PRECISION"),
            ("execution_cost_json", "TEXT"),
            ("orderbook_available", "BOOLEAN DEFAULT FALSE"),
            ("trade_side_irt", "BOOLEAN DEFAULT FALSE"),
            ("trend_correct", "BOOLEAN"),
            ("expired_at_price", "DOUBLE PRECISION"),
            ("expired_pnl_pct", "DOUBLE PRECISION"),
            ("expired_bias", "VARCHAR"),
            ("is_weak", "BOOLEAN DEFAULT FALSE"),
            ("exit_reason", "VARCHAR"),
            ("trend_predicted_at_entry", "VARCHAR"),
        ]
        for col_name, col_type in signallog_cols:
            if col_name not in cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE signallog ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        )
                    )
                    logger.info(f"  + signallog.{col_name} اضافه شد")
                except Exception as e:
                    logger.warning(f"  - signallog.{col_name}: {e}")

    # ─── users: ستون‌های فاز ۱۱ ───
    if "users" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("users")}
        users_cols = [
            ("email", "VARCHAR"),
            ("hashed_password", "VARCHAR"),
        ]
        for col_name, col_type in users_cols:
            if col_name not in cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        )
                    )
                    logger.info(f"  + users.{col_name} اضافه شد")
                except Exception as e:
                    logger.warning(f"  - users.{col_name}: {e}")

    # ─── payment_requests: ستون‌های فاز ۱۱ ───
    if "payment_requests" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("payment_requests")}
        pay_cols = [
            ("full_name", "VARCHAR"),
            ("payment_time", "VARCHAR"),
        ]
        for col_name, col_type in pay_cols:
            if col_name not in cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        )
                    )
                    logger.info(f"  + payment_requests.{col_name} اضافه شد")
                except Exception as e:
                    logger.warning(f"  - payment_requests.{col_name}: {e}")


def migrate_db():
    """
    اضافه کردن ستون‌های جدید به جداول موجود.
    هم SQLite و هم PostgreSQL رو پشتیبانی می‌کنه.
    """
    try:
        inspector = inspect(engine)

        if is_sqlite:
            with engine.connect() as conn:
                _add_missing_columns_sqlite(inspector, conn)
                conn.commit()
            logger.info("✅ migration برای SQLite انجام شد")
        else:
            with engine.connect() as conn:
                _add_missing_columns_postgres(inspector, conn)
                conn.commit()
            logger.info("✅ migration برای PostgreSQL انجام شد")

    except Exception as e:
        logger.warning(f"[Database] migration: {e}")
