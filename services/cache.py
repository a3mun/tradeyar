"""
services/cache.py
کش in-memory با TTL — برای دیتا و تحلیل
============================================================
"""

import hashlib
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """کش ساده in-memory با TTL"""

    def __init__(self, max_size: int = 500):
        self._store: dict[str, tuple[Any, float]] = {}
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        # ─── حذف قدیمی‌ها اگه پر شد ───
        if len(self._store) >= self._max_size:
            now = time.time()
            expired = [k for k, (_, exp) in self._store.items() if exp < now]
            for k in expired:
                del self._store[k]
            # اگه هنوز پر، قدیمی‌ترین رو پاک کن
            if len(self._store) >= self._max_size:
                oldest = min(self._store.items(), key=lambda x: x[1][1])
                del self._store[oldest[0]]

        self._store[key] = (value, time.time() + ttl)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


# ═══════════════════════════════════════════════════════════
# TTL بر اساس TF (ثانیه)
# ═══════════════════════════════════════════════════════════
TF_TTL = {
    "۱ دقیقه": 30,
    "۵ دقیقه": 120,
    "۱۵ دقیقه": 300,
    "۳۰ دقیقه": 600,
    "۱ ساعت": 900,
    "روزانه": 1800,
}


def get_ttl(tf_name: str) -> int:
    return TF_TTL.get(tf_name, 120)


# ═══════════════════════════════════════════════════════════
# Fingerprint بر اساس آخرین کندل
# ═══════════════════════════════════════════════════════════
def make_fingerprint(df) -> str:
    """
    ساخت هش از آخرین ۲ کندل — برای تشخیص کندل جدید.
    اگه همون باشه، سیگنال کش شده استفاده می‌شه.
    """
    try:
        if df is None or len(df) < 2:
            return "empty"

        last = df.iloc[-1]
        prev = df.iloc[-2]

        raw = (
            f"{last.name}_{last['close']:.6f}_"
            f"{prev.name}_{prev['close']:.6f}_{len(df)}"
        )
        return hashlib.md5(raw.encode()).hexdigest()[:12]
    except Exception as e:
        logger.warning(f"[Fingerprint] {e}")
        return "error"


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════
data_cache = TTLCache(max_size=300)
analysis_cache = TTLCache(max_size=500)
quote_cache = TTLCache(max_size=200)
