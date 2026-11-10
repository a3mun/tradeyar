"""
api/database.py
اتصال دیتابیس + session
============================================================
نسخه ۳.۰ · فاز ۱۴.۷.۱
🔴 تغییرات:
  • + strategy, tp_levels_json, tp_hit_level, timeout_planned_min
  • migration idempotent برای SQLite و Postgres
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


# ═══ جدول refund_requests ═══
try:
    with engine.begin() as conn:
        if is_sqlite:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS refund_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    subscription_id INTEGER NOT NULL,
                    old_plan VARCHAR,
                    new_plan VARCHAR,
                    refund_amount INTEGER DEFAULT 0,
                    admin_note VARCHAR,
                    status VARCHAR DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    processed_by VARCHAR
                );
            """))
        else:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS refund_requests (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
                    old_plan VARCHAR,
                    new_plan VARCHAR,
                    refund_amount INTEGER DEFAULT 0,
                    admin_note VARCHAR,
                    status VARCHAR DEFAULT 'pending',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    processed_at TIMESTAMP WITH TIME ZONE,
                    processed_by VARCHAR
                );
            """))
    logger.info("[Migration] ✅ جدول refund_requests آماده است")
except Exception as e:
    logger.warning(f"[Migration] refund_requests: {e}")


def _add_missing_columns_sqlite(inspector, conn):
    """migration برای SQLite — ستون‌های جدید signallog."""
    if "signals_log" not in inspector.get_table_names():
        return
    existing_cols = {col["name"] for col in inspector.get_columns("signals_log")}
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
        ("winning_group", "TEXT"),
        # فاز B — Pump/Dump
        ("pump_score", "REAL"),
        ("dump_score", "REAL"),
        ("pump_warning", "TEXT"),
        ("pump_type", "TEXT"),
        # فاز B — Suggested Entry
        ("suggested_entry", "REAL"),
        ("suggested_entry_method", "TEXT"),
        ("suggested_entry_distance_pct", "REAL"),
        # 🔴 فاز ۱۴.۷.۱ — استراتژی و TP Ladder
        ("strategy", "VARCHAR DEFAULT 'swing'"),
        ("tp_levels_json", "TEXT"),
        ("tp_hit_level", "INTEGER"),
        ("timeout_planned_min", "INTEGER"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            try:
                conn.execute(
                    text(f"ALTER TABLE signals_log ADD COLUMN {col_name} {col_type}")
                )
                logger.info(f"  + ستون {col_name} اضافه شد")
            except Exception as e:
                logger.debug(f"  - ستون {col_name}: {e}")


def _add_missing_columns_postgres(inspector, conn):
    """migration برای PostgreSQL"""
    existing_tables = set(inspector.get_table_names())

    if "signals_log" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("signals_log")}
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
            ("winning_group", "VARCHAR"),
            # فاز B — Pump/Dump
            ("pump_score", "DOUBLE PRECISION"),
            ("dump_score", "DOUBLE PRECISION"),
            ("pump_warning", "VARCHAR"),
            ("pump_type", "VARCHAR"),
            # فاز B — Suggested Entry
            ("suggested_entry", "DOUBLE PRECISION"),
            ("suggested_entry_method", "VARCHAR"),
            ("suggested_entry_distance_pct", "DOUBLE PRECISION"),
            # 🔴 فاز ۱۴.۷.۱
            ("strategy", "VARCHAR DEFAULT 'swing'"),
            ("tp_levels_json", "TEXT"),
            ("tp_hit_level", "INTEGER"),
            ("timeout_planned_min", "INTEGER"),
        ]
        for col_name, col_type in signallog_cols:
            if col_name not in cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE signals_log ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        )
                    )
                except Exception:
                    pass

    if "users" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("users")}
        for col_name, col_type in [
            ("email", "VARCHAR"),
            ("hashed_password", "VARCHAR"),
        ]:
            if col_name not in cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        )
                    )
                except Exception:
                    pass

    if "payment_requests" in existing_tables:
        cols = {col["name"] for col in inspector.get_columns("payment_requests")}
        pay_cols = [
            ("full_name", "VARCHAR"),
            ("payment_time", "VARCHAR"),
            ("payment_method", "VARCHAR"),
        ]
        for col_name, col_type in pay_cols:
            if col_name not in cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE payment_requests ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        )
                    )
                except Exception:
                    pass


def migrate_db():
    """migration برای هر دو دیتابیس"""
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


# ═══ جدول extension_tokens ═══
try:
    with engine.begin() as conn:
        if is_sqlite:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS extension_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash VARCHAR NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
        else:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS extension_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    token_hash VARCHAR NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_extension_tokens_hash ON extension_tokens(token_hash);"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_extension_tokens_user ON extension_tokens(user_id);"
            )
        )
    logger.info("[Migration] ✅ جدول extension_tokens آماده است")
except Exception as e:
    logger.warning(f"[Migration] extension_tokens: {e}")

# ═══ جدول site_stats_override ═══
try:
    with engine.begin() as conn:
        if is_sqlite:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS site_stats_override (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key VARCHAR NOT NULL UNIQUE,
                    value REAL DEFAULT 0.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by VARCHAR
                );
            """))
        else:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS site_stats_override (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR NOT NULL UNIQUE,
                    value DOUBLE PRECISION DEFAULT 0.0,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_by VARCHAR
                );
            """))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_site_stats_key ON site_stats_override(key);"
            )
        )
    logger.info("[Migration] ✅ جدول site_stats_override آماده است")
except Exception as e:
    logger.warning(f"[Migration] site_stats_override: {e}")
