"""
api/database.py
اتصال دیتابیس + session
"""

import logging

from sqlalchemy import create_engine
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


def migrate_db():
    """
    اضافه کردن ستون‌های جدید به جداول موجود.

    ⚠️ SQLite از ALTER TABLE ADD COLUMN پشتیبانی می‌کنه ولی
       SQLModel خودکار انجام نمی‌ده. اینجا دستی چک می‌کنیم.
    """
    if not is_sqlite:
        return

    from sqlalchemy import inspect, text

    try:
        inspector = inspect(engine)
        if "signallog" not in inspector.get_table_names():
            return

        existing_cols = {col["name"] for col in inspector.get_columns("signallog")}

        # ─── ستون‌های جدید (اگه نباشن اضافه می‌شن) ───
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
            # 🔴 فاز ۸.۲
            ("is_weak", "INTEGER DEFAULT 0"),
        ]

        with engine.connect() as conn:
            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE signallog ADD COLUMN {col_name} {col_type}"
                            )
                        )
                        logger.info(f"  + ستون {col_name} اضافه شد")
                    except Exception as e:
                        logger.debug(f"  - ستون {col_name}: {e}")
            conn.commit()

    except Exception as e:
        logger.warning(f"[Database] migration: {e}")
