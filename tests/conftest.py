"""
tests/conftest.py
تنظیمات مشترک تست‌های Trademun
============================================================
"""

import os
import sys
from pathlib import Path

import pytest

# ═══ ریشه‌ی پروژه در sys.path (برای import core/api/services) ═══
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ═══ scheduler در تست اجرا نشود ═══
os.environ.setdefault("SCHEDULER_ENABLED", "false")


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def anyio_backend():
    """اجرای تست‌های async با asyncio (نه trio)"""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    """
    اطمینان از وجود جداول.

    ⚠️ تست‌ها روی همان دیتابیس dev اجرا می‌شوند (data/trademun.db)،
       چون engine در زمان import در api.database ساخته می‌شود و
       تغییر DATABASE_URL بعد از آن بی‌اثر است. مسئولیت پاک‌سازی
       ردیف‌ها بر عهده‌ی fixture هر تست است.
    """
    from api.database import init_db

    init_db()
    yield


@pytest.fixture(autouse=True)
def _clean_pending_signals():
    """
    پاک‌سازی سیگنال‌های در انتظار قبل از هر تست.

    چرا لازم است: ``backtest_all`` **همه‌ی** سیگنال‌های در انتظار
    دیتابیس را برمی‌دارد، نه فقط آن‌هایی که تست ساخته. بدون این
    پاک‌سازی، باقی‌مانده‌ی تست‌های دیگر شمارنده‌ها را خراب می‌کند
    و تست‌ها غیرقابل‌اعتماد می‌شوند.

    ⚠️ فقط ردیف‌های ``result IS NULL`` (یعنی در انتظار) حذف
    می‌شوند — تاریخچه‌ی پردازش‌شده دست‌نخورده می‌ماند.
    """
    try:
        from sqlmodel import Session, select

        from api.database import engine
        from api.models import SignalLog

        with Session(engine) as s:
            pending = s.exec(
                select(SignalLog).where(SignalLog.result.is_(None))
            ).all()
            for row in pending:
                s.delete(row)
            s.commit()
    except Exception:
        # ─── اگر دیتابیس آماده نبود، از این fixture رد شو ───
        pass

    yield


# ═══════════════════════════════════════════════════════════
# Hooks
# ═══════════════════════════════════════════════════════════
def pytest_configure(config):
    """مارکرهای سفارشی"""
    config.addinivalue_line("markers", "live: تست با API واقعی صرافی")
    config.addinivalue_line("markers", "slow: تست کند")


def pytest_addoption(parser):
    """گزینه‌ی --live برای تست‌های شبکه‌ای"""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="اجرای تست‌هایی که به API واقعی صرافی وصل می‌شوند",
    )
