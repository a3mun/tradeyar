# 🔍 کد ریویو کامل — Trademun

**تاریخ:** ۱۴۰۵ · **نسخه بررسی‌شده:** `api 6.0.0` / `core 8.5` / `contracts 1.3`
**روش:** خواندن کامل فایل‌های اولویت‌دار + تست‌های اجرایی روی `.venv` (تأیید تجربی، نه حدس)
**دسترسی:** فقط-خواندن — **هیچ فایلی در پروژه اصلاح نشد**

---

## 📊 خلاصه اجرایی

| شدت | تعداد | موضوعات غالب |
|---|---|---|
| 🔴 بالا | **۱۴** | Timezone، TF اشتباه در بیت‌پین/والکس، event-loop blocking، عدم احراز هویت، منطق بک‌تست |
| 🟡 متوسط | **۱۳** | کش، race condition، type safety، منطق اندیکاتور، UX |
| 🟢 پایین | **۱۰** | dead code، RTL/spacing، تمیزکاری |

**پاسخ کوتاه به سؤالات مشخص شما:**

| سؤال شما | پاسخ |
|---|---|
| Circular import؟ | ❌ **نه.** `import api.main` را اجرا کردم — سالم بالا می‌آید. ولی `services/ → api/` وابستگی **معماری معکوس** است (بخش ۱-۱). |
| `services/cache.py` بدون lock؟ | ✅ **بله، تأیید شد** — ولی در تست عملی ۸-تردی خطا نداد (GIL). شکست واقعی در `set/get` هم‌زمان با دیکشنری بزرگ (بخش ۲-۱). |
| APScheduler + manual trigger؟ | 🔴 **بله، تداخل واقعی** — نه `max_instances` نه `coalesce` (بخش ۲-۳). |
| SQLite + multiple connections؟ | 🔴 **بله** — بدون WAL/busy_timeout + job هم‌زمان (بخش ۲-۴). |
| Timezone؟ | 🔴 **بدترین بخش پروژه.** سه منبع مختلف سه tz مختلف می‌دهند. **تأیید تجربی** (بخش ۳-۱). |
| `TF_ATR_MULT` معقول است؟ | 🟡 **عددش معقول، جای اعمالش نه** (بخش ۷-۱). |
| `resolve_symbol_and_source` درست است؟ | 🟡 **کار می‌کند ولی ۵ جای دیگر همین منطق تکرار شده** (بخش ۷-۵). |
| `record_signal` جلوگیری از تکرار؟ | 🔴 **درست کار نمی‌کند** — `source` و `market_type` را در چک تکراری لحاظ نمی‌کند (بخش ۷-۴). |
| `as any` در فرانت؟ | ✅ **۱۰ مورد** — `as any` شش‌تا، `: any` چهارتا، `@ts-ignore` صفر (بخش ۵-۱). |

---

# ۱. معماری و ساختار

## 🟡 ۱-۱ [شدت: متوسط] [دسته: باگ/معماری] — وابستگی معکوس `services/ → api/`

**فایل:** `services/signal_recorder.py` خط ۱۱-۱۲ · `services/backtest_service.py` خط ۱۲-۱۳

```python
from api.database import engine     # ← services به api وابسته است
from api.models import SignalLog
```

**مشکل:** لایه سرویس به لایه API وابسته است. چرخه‌ی import **ایجاد نمی‌کند** (تأیید شد: `import api.main` سالم بالا می‌آید، چون `analyzer_service` این import را داخل تابع خط ۲۱۹ انجام می‌دهد)، اما:

- `services/` دیگر بدون `api/` قابل تست یا استفاده نیست → تست واحد غیرممکن
- اگر کسی `import services.analyzer_service` را به بالای `api/routers/analyze.py` منتقل کند و هم‌زمان `services/signal_recorder` را در سطح ماژول import کند، **چرخه‌ی واقعی** ساخته می‌شود
- `app.py` (Streamlit) که از `services/` استفاده نمی‌کند، مجبور است دو سیستم ثبت سیگنال موازی نگه دارد

**ریشه:** `engine` و `SignalLog` در لایه‌ای تعریف شده‌اند که مصرف‌کننده‌ی سرویس است، نه زیرساخت مشترک.

**راه‌حل:** انتقال زیرساخت به لایه‌ی مستقل (الگوی repository):

```python
# ─── core/db.py  (جدید) ───
"""زیرساخت دیتابیس — بدون وابستگی به لایه API"""
from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine

BASE_DIR = Path(__file__).resolve().parent.parent
DB_URL = f"sqlite:///{BASE_DIR / 'data' / 'trademun.db'}"

engine = create_engine(
    DB_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)

def init_db() -> None:
    from core import db_models  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
```

```python
# ─── services/signal_recorder.py (اصلاح‌شده) ───
from core.db import engine          # ← دیگر api نیست
from core.db_models import SignalLog
```

```python
# ─── api/database.py (بعد از اصلاح — فقط re-export) ───
from core.db import engine, init_db, get_session   # سازگاری با کد قدیمی
```

**تست:**
```bash
python -c "import services.analyzer_service; print('OK - no api dependency')"
python -c "import services.backtest_service; print('OK')"
# و مطمئن شو دیگر چرخه نمی‌خورد:
python -c "import api.routers.analyze; import api.main; print('OK')"
```

---

## 🟡 ۱-۲ [شدت: متوسط] [دسته: باگ] — مسیرهای نسبی به CWD وابسته‌اند

**فایل:** `core/market_lists.py` خط ۱۵ · `core/nobitex_auth.py` خط ۲۴

```python
TSETMC_CACHE = Path("data/tsetmc_symbols.json")        # ← نسبی به CWD
API_KEYS_FILE = Path("api-keys nobitex.txt")           # ← نسبی به CWD
```

در حالی که `api/config.py` خط ۱۴-۱۶ این کار را **درست** انجام می‌دهد:

```python
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
```

**مشکل:** اگر اپ از ریشه‌ی پروژه اجرا نشود (مثلاً `uvicorn api.main:app` از یک systemd service با `WorkingDirectory=/`، یا اجرای تست از `tests/`):

- `market_lists` به فایل کش TSETMC نمی‌رسد → **`iran_stocks` خالی یا کند** (هر بار ۵۴۰ نماد از API)
- `nobitex_auth` فایل کلید را پیدا نمی‌کند → **همیشه fallback به public API**، بدون هیچ خطای واضحی
- `Path("data/...")` حتی ممکن است در CWD اشتباه یک پوشه‌ی جدید بسازد

**راه‌حل:**

```python
# ─── core/paths.py (جدید) ───
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SECRETS_DIR = BASE_DIR / "secrets"
DATA_DIR.mkdir(exist_ok=True)
SECRETS_DIR.mkdir(exist_ok=True)

TSETMC_CACHE = DATA_DIR / "tsetmc_symbols.json"
NOBITEX_KEYS_FILE = SECRETS_DIR / "nobitex_api_keys.json"
```

```python
# core/market_lists.py
from core.paths import TSETMC_CACHE

# core/nobitex_auth.py
from core.paths import NOBITEX_KEYS_FILE
API_KEYS_FILE = NOBITEX_KEYS_FILE
```

**تست:**
```bash
cd C:\ && python -c "import sys; sys.path.insert(0,r'C:\Users\asemu\Desktop\TradeYar Asemun'); from core.market_lists import TSETMC_CACHE; print(TSETMC_CACHE, TSETMC_CACHE.exists())"
# باید True بدهد حتی وقتی CWD جای دیگری است
```

---

## 🔴 ۱-۳ [شدت: بالا] [دسته: باگ] — کد جدید در git نیست (ریسک از دست رفتن کار)

**تأیید شده:** `git ls-files` فقط **۳۶ فایل** برمی‌گرداند.

فایل‌های tracked: `app.py`, `core/*`, `ui/*`, `data/*.json`, `tools/*`, `requirements.txt`, `fonts/*`

**فایل‌هایی که در git نیستند:**
- کل `api/` (۱۰ فایل)
- کل `services/` (۶ فایل)
- کل `frontend/` (۴۰+ فایل)
- کل `tests/` (۳ فایل)

**مشکل:** تمام فاز ۶ (FastAPI + Next.js) — یعنی کار اصلی این روزهای شما — **هیچ نسخه‌ی پشتیبانی ندارد**. یک `git clean -fdx` یا خرابی دیسک = از دست رفتن کامل.

**ریشه:** `.gitignore` هیچ‌کدام از این‌ها را ignore نمی‌کند؛ فقط commit نشده‌اند. (`.env` و `.env.local` درست ignore شده‌اند ✅)

**راه‌حل:**

```gitignore
# ─── اضافه کن به .gitignore ───
# Secrets — هرگز commit نشود
*api-keys*
secrets/
*.key
*.pem

# Database و state محلی
data/*.db
data/*.db-journal
data/user_prefs.json
data/signals_log.json
data/custom_symbols.json

# Python
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
```

```bash
git add api/ services/ tests/ frontend/src frontend/package.json \
        frontend/tsconfig.json frontend/next.config.ts \
        frontend/postcss.config.mjs frontend/components.json \
        frontend/eslint.config.mjs frontend/.env.local.example
git commit -m "feat(phase6): FastAPI backend + Next.js frontend"
```

**تست:**
```bash
git ls-files | findstr /C:"api/" | find /c /v ""     # باید > 0 باشد
git status --porcelain                                # باید تمیز باشد
git check-ignore -v ".env"                            # باید ignore را نشان دهد
```

---

# ۲. Concurrency، Cache و دیتابیس

## 🟡 ۲-۱ [شدت: متوسط] [دسته: باگ] — `TTLCache` بدون lock

**فایل:** `services/cache.py` خط ۲۲-۴۹

```python
def set(self, key: str, value: Any, ttl: int) -> None:
    if len(self._store) >= self._max_size:
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if exp < now]  # ← iterate
        for k in expired:
            del self._store[k]                                              # ← mutate
        if len(self._store) >= self._max_size:
            oldest = min(self._store.items(), key=lambda x: x[1][1])        # ← min روی dict خالی → ValueError
            del self._store[oldest[0]]
    self._store[key] = (value, time.time() + ttl)
```

**مشکل:** سه mutated-state بدون هماهنگی:

1. اگر thread دیگری بین `min(...)` و `del` آیتم را پاک کند → `ValueError: min() arg is an empty sequence`
2. `get()` در خط ۲۷ (`del self._store[key]`) هم‌زمان با iteration خط ۳۵ → `RuntimeError: dictionary changed size during iteration`
3. `max_size` واقعاً رعایت نمی‌شود (بین `len()` و `del` پنجره‌ی مسابقه هست)

**آنچه تست کردم:** ۸ thread × ۴۰۰ عملیات روی `TTLCache(max_size=50)` → **صفر خطا**. دلیل: GIL عملیات دیکشنری را اتمیک نگه می‌دارد و dict کوچک resize نمی‌شود. **این باگ واقعی است ولی نادر** — در production با ۵۰۰+ کلید و بار سنگین (که resize رخ می‌دهد) ظاهر می‌شود. صادقانه بگویم: این را در تست بازتولید نکردم؛ ادعای نظری است نه مشاهده‌ی تجربی.

**راه‌حل:**

```python
"""
services/cache.py — نسخه thread-safe با LRU واقعی
"""
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """کش in-memory با TTL و LRU — thread-safe"""

    def __init__(self, max_size: int = 500):
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expiry = item
            if time.time() > expiry:
                del self._store[key]
                return None
            self._store.move_to_end(key)   # ← LRU
            return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            now = time.time()

            if len(self._store) >= self._max_size:
                # اول منقضی‌ها
                dead = [k for k, (_, exp) in self._store.items() if exp < now]
                for k in dead:
                    self._store.pop(k, None)

                # بعد LRU تا رسیدن به ظرفیت
                while len(self._store) >= self._max_size:
                    self._store.popitem(last=False)   # ← امن، اتمیک

            self._store[key] = (value, now + ttl)
            self._store.move_to_end(key)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict:
        """برای observability — چند تا منقضی مونده"""
        with self._lock:
            now = time.time()
            alive = sum(1 for _, exp in self._store.values() if exp >= now)
            return {
                "total": len(self._store),
                "alive": alive,
                "expired": len(self._store) - alive,
                "max_size": self._max_size,
            }
```

**تست:**
```python
# tests/test_cache.py
import threading
from services.cache import TTLCache

def test_ttl_cache_concurrent_resize():
    c = TTLCache(max_size=100)
    errors = []

    def worker(tid):
        try:
            for i in range(5000):
                c.set(f"k{(tid * 997 + i) % 300}", i, ttl=60)
                c.get(f"k{(tid * 31 + i) % 300}")
                if i % 500 == 0:
                    c.clear()
        except Exception as e:
            errors.append(f"thread {tid}: {e!r}")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(16)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert errors == [], f"race detected: {errors[:5]}"
    assert c.size() <= 100, f"capacity violated: {c.size()}"
```

---

## 🔴 ۲-۲ [شدت: بالا] [دسته: باگ/performance] — کش تحلیل با fingerprint **عملاً بی‌اثر است**

**فایل:** `services/cache.py` خط ۷۲-۹۱ · `services/analyzer_service.py` خط ۹۲-۱۰۲

```python
def make_fingerprint(df) -> str:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    raw = (
        f"{last.name}_{last['close']:.6f}_"      # ← close کندل در حال تشکیل!
        f"{prev.name}_{prev['close']:.6f}_{len(df)}"
    )
    return hashlib.md5(raw.encode()).hexdigest()[:12]
```

**مشکل:** `last['close']` قیمت کندل **در حال تشکیل** است و در هر ثانیه عوض می‌شود. یعنی:

- کاربر هر ۳۰ ثانیه روی «تحلیل» بزند → fingerprint هر بار جدید → **cache miss ۱۰۰٪**
- کل `compute_indicators` (~۲۰ اندیکاتور، EMA200، Ichimoku، CVD) هر بار از صفر اجرا می‌شود
- TTL تعریف‌شده در `TF_TTL` (۳۰ تا ۱۸۰۰ ثانیه) **هیچ‌وقت اعمال نمی‌شود** چون fingerprint زودتر invalidate می‌کند
- بدتر: `set(fp_key, fingerprint)` و `set(cache_key, output)` دو ورودی جدا با TTL جدا هستند — اگر `fp` منقضی شود ولی `cache_key` نه، **داده‌ی کهنه با منطق متناقض** برگردانده می‌شود

**ریشه:** fingerprint باید از **کندل بسته‌شده** ساخته شود نه کندل جاری. کندل جاری به تحلیل زنده تعلق دارد و نباید در cache key باشد.

**راه‌حل:**

```python
"""
services/cache.py — fingerprint پایدار بر اساس کندل بسته
"""
import hashlib
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ─── نقشه دقیقه‌بندی هر TF (ثانیه) برای تشخیص کندل باز ───
_TF_SECONDS = {
    "۱ دقیقه": 60,
    "۵ دقیقه": 300,
    "۱۵ دقیقه": 900,
    "۳۰ دقیقه": 1800,
    "۱ ساعت": 3600,
    "روزانه": 86400,
}


def _closed_candles(df: pd.DataFrame, tf_name: str) -> pd.DataFrame:
    """
    فقط کندل‌های بسته‌شده را برمی‌گرداند.

    کندل آخری که هنوز در حال تشکیل است حذف می‌شود، چون:
      1. OHLC آن ثابت نیست
      2. استفاده از آن = repainting (سیگنالی که بعداً عوض می‌شود)
    """
    if df is None or df.empty:
        return df

    tf_sec = _TF_SECONDS.get(tf_name)
    if not tf_sec:
        return df[:-1] if len(df) > 1 else df

    idx = df.index[-1]

    # نرمال‌سازی به UTC-naive برای مقایسه‌ی یکنواخت
    try:
        if hasattr(idx, "tzinfo") and idx.tzinfo is not None:
            idx = idx.tz_convert("UTC").tz_localize(None)
        else:
            idx = pd.Timestamp(idx)
    except Exception:
        return df[:-1] if len(df) > 1 else df

    now_utc = pd.Timestamp.utcnow().tz_localize(None)

    # اگر زمان شروع کندل + طول TF > الان → کندل هنوز باز است
    candle_end = idx + pd.Timedelta(seconds=tf_sec)
    if candle_end > now_utc:
        return df[:-1] if len(df) > 1 else df

    return df


def make_fingerprint(df: pd.DataFrame, tf_name: str = "۵ دقیقه") -> str:
    """
    هش پایدار از آخرین ۲ کندلِ بسته + طول سری.

    پایدار در طول یک کندل → کش واقعاً hit می‌شود.
    """
    try:
        closed = _closed_candles(df, tf_name)
        if closed is None or len(closed) < 2:
            return "empty"

        last = closed.iloc[-1]
        prev = closed.iloc[-2]
        raw = (
            f"{last.name}|{last['close']:.8f}|"
            f"{prev.name}|{prev['close']:.8f}|{len(closed)}"
        )
        return hashlib.md5(raw.encode()).hexdigest()[:12]
    except Exception as e:
        logger.warning(f"[Fingerprint] {e}")
        return "error"
```

```python
# ─── services/analyzer_service.py — اصلاح خط ۹۲ ───
fingerprint = make_fingerprint(df, tf_name) if use_cache else ""
```

**نکته‌ی مهم:** کندل جاری را باید همچنان به `analyze_symbol` بدهید (قیمت زنده لازم است)، فقط **fingerprint** را از کندل بسته بسازید.

**تست:**
```python
# tests/test_fingerprint.py
import pandas as pd
from services.cache import make_fingerprint

def _mk(times, closes):
    return pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes,
         "volume": [1] * len(closes)},
        index=pd.to_datetime(times, utc=True),
    )

def test_fingerprint_stable_within_candle():
    """دو فراخوانی در همان کندل باید یک هش بدهند"""
    base = pd.date_range("2026-01-01", periods=60, freq="5min", tz="UTC")

    df1 = _mk(base, list(range(60)))
    df2 = _mk(base, list(range(59)) + [999.0])   # ← close کندل جاری عوض شد

    assert make_fingerprint(df1, "۵ دقیقه") == make_fingerprint(df2, "۵ دقیقه")

def test_fingerprint_changes_on_new_closed_candle():
    base = pd.date_range("2026-01-01", periods=60, freq="5min", tz="UTC")
    df1 = _mk(base, list(range(60)))
    df2 = _mk(list(base) + [base[-1] + pd.Timedelta("5min")], list(range(61)))

    assert make_fingerprint(df1, "۵ دقیقه") != make_fingerprint(df2, "۵ دقیقه")
```

---

## 🔴 ۲-۳ [شدت: بالا] [دسته: باگ] — تداخل Scheduler و manual trigger

**فایل:** `api/scheduler.py` خط ۳۷-۴۳ · `api/routers/backtest.py` خط ۱۰۰-۱۰۴

```python
scheduler.add_job(
    check_pending_signals,
    "interval",
    minutes=settings.BACKTEST_INTERVAL_MINUTES,
    id="check_pending_signals",
    replace_existing=True,
)   # ← نه max_instances، نه coalesce، نه misfire_grace_time
```

**مشکل:** سه مسیر هم‌زمان روی همان ردیف‌های SQLite کار می‌کنند:

1. Scheduler هر ۳۰ دقیقه
2. `POST /backtest/run` (دستی از UI)
3. **`SignalHistory.tsx` خط ۱۰۷ — هر ۳۰ ثانیه از مرورگر هر کاربر!**

اگر job قبلی هنوز تمام نشده باشد (و `backtest_all` با ۲۰۰ سیگنال و fetch شبکه‌ای می‌تواند دقیقه‌ها طول بکشد)، APScheduler یک instance دیگر اجرا می‌کند → **write-write conflict** → `database is locked`.

بدتر: `check_pending_signals` یک `async def` است که `backtest_all()` را **sync** صدا می‌زند → **کل event loop قفل می‌شود** (جزئیات در ۲-۵).

**راه‌حل:**

```python
"""
api/scheduler.py — با قفل، threadpool و جداسازی
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api.config import settings
from services.backtest_service import backtest_all

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

# ─── قفل process-level: Scheduler و manual trigger هرگز هم‌زمان اجرا نشوند ───
_backtest_lock = asyncio.Lock()


async def check_pending_signals(trigger: str = "scheduler") -> dict:
    """بررسی سیگنال‌های در انتظار — از scheduler و manual مشترک"""
    if _backtest_lock.locked():
        logger.info(f"[Scheduler/{trigger}] اجرای قبلی هنوز تمام نشده — رد شد")
        return {"ok": False, "reason": "already_running", "checked": 0,
                "updated": 0, "expired": 0, "win": 0, "loss": 0}

    async with _backtest_lock:
        logger.info(f"[Scheduler/{trigger}] بررسی سیگنال‌های در انتظار...")
        try:
            # ─── sync/blocking → threadpool، نه event loop ───
            result = await asyncio.to_thread(backtest_all, 200)

            if result.get("updated", 0) > 0:
                logger.info(
                    f"[Scheduler/{trigger}] ✅ {result['updated']} به‌روز شد "
                    f"(win={result['win']}, loss={result['loss']}, "
                    f"expired={result['expired']})"
                )
            else:
                logger.info(f"[Scheduler/{trigger}] {result['checked']} بررسی شد، تغییری نبود")
            return {"ok": True, **result}
        except Exception as e:
            logger.exception(f"[Scheduler/{trigger}] خطا")
            return {"ok": False, "reason": str(e), "checked": 0,
                    "updated": 0, "expired": 0, "win": 0, "loss": 0}


def start_scheduler():
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] غیرفعال")
        return

    scheduler.add_job(
        check_pending_signals,
        IntervalTrigger(minutes=settings.BACKTEST_INTERVAL_MINUTES),
        id="check_pending_signals",
        replace_existing=True,
        max_instances=1,                 # ← حیاتی
        coalesce=True,                   # ← چند misfire = یک اجرا
        misfire_grace_time=120,
        kwargs={"trigger": "scheduler"},
    )
    scheduler.start()
    logger.info(f"[Scheduler] فعال — هر {settings.BACKTEST_INTERVAL_MINUTES} دقیقه")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Scheduler] متوقف شد")
```

```python
# ─── api/routers/backtest.py — خط ۱۰۰-۱۰۴ (اصلاح‌شده) ───
from api.scheduler import check_pending_signals

@router.post("/run")
async def backtest_run():
    """اجرای دستی راستی‌آزمایی — با همان قفل scheduler"""
    result = await check_pending_signals(trigger="manual")
    if not result.get("ok"):
        raise HTTPException(
            status_code=409,
            detail="راستی‌آزمایی در حال اجراست — چند لحظه بعد تلاش کن",
        )
    return result
```

```typescript
// ─── frontend/src/components/backtest/SignalHistory.tsx — خط ۱۰۷ را حذف کن ───
// ❌ حذف شود: await api.post("/backtest/run").catch(() => {});
// دلیل: این کار وظیفه‌ی scheduler است، نه هر مرورگر. با ۱۰ کاربر = ۱۰ اجرای موازی.
const fetchHistory = async () => {
  setLoading(true);
  try {
    const res = await api.get("/backtest/history", { params: { limit: 50, status } });
    setItems(res.data.items || []);
  } catch {
    setItems([]);
  } finally {
    setLoading(false);
  }
};
```

**تست:**
```python
# tests/test_scheduler_lock.py
import asyncio
from api.scheduler import check_pending_signals

async def test_no_overlap():
    """دو اجرای هم‌زمان → یکی رد می‌شود"""
    r1, r2 = await asyncio.gather(
        check_pending_signals("t1"),
        check_pending_signals("t2"),
    )
    outcomes = sorted([r1.get("ok"), r2.get("ok")])
    assert outcomes == [False, True], f"expected one rejection, got {outcomes}"

asyncio.run(test_no_overlap())
```

---

## 🔴 ۲-۴ [شدت: بالا] [دسته: باگ] — SQLite بدون WAL، busy_timeout و pool_pre_ping

**فایل:** `api/database.py` خط ۱۳-۱۹

```python
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    ),
)
```

**مشکل:** چهار تنظیم حیاتی غایب است:

| غایب | نتیجه |
|---|---|
| `PRAGMA journal_mode=WAL` | نویسنده، خواننده‌ها را قفل می‌کند → `database is locked` |
| `PRAGMA busy_timeout` | به‌جای صبر، فوراً خطا می‌دهد |
| `pool_pre_ping=True` | اتصال مرده (بعد از idle طولانی روی Postgres/Render) → `OperationalError` |
| `pool_size` / `max_overflow` | پیش‌فرض ۵+۱۰؛ برای Scheduler + چند کاربر کافی نیست |

اضافه: `echo=settings.DEBUG` با `DEBUG=True` در `.env` یعنی **هر query لاگ می‌شود** — در job ۳۰ دقیقه‌ای روی ۲۰۰ ردیف، هزاران خط لاگ.

**راه‌حل:**

```python
"""
api/database.py — SQLite/Postgres با تنظیمات production
"""
import logging

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from api.config import settings

logger = logging.getLogger(__name__)

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,                       # ← همیشه False؛ لاگ را logging کنترل کند
        connect_args={
            "check_same_thread": False,
            "timeout": 30,                # ← busy_timeout در سطح درایور
        },
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        """WAL + تنظیمات عملکردی — یک‌بار در هر اتصال"""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=30000")     # ۳۰ ثانیه
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
else:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,                # ← Render/Neon اتصال idle را می‌کشد
    )


def init_db() -> None:
    from api import models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    logger.info(f"✅ دیتابیس آماده ({'sqlite' if IS_SQLITE else 'postgres'})")


def get_session():
    with Session(engine) as session:
        yield session
```

**تست:**
```python
# tests/test_db_pragmas.py
from sqlalchemy import text
from api.database import engine

def test_wal_enabled():
    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert mode.lower() == "wal", f"WAL off: {mode}"
        timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()
        assert timeout >= 30000

def test_concurrent_writes():
    """۲۰ نوشتن هم‌زمان نباید locked بدهد"""
    import threading
    from sqlmodel import Session
    from api.models import SignalLog

    errors = []
    def writer(i):
        try:
            with Session(engine) as s:
                s.add(SignalLog(ticker=f"T{i}", signal="LONG", price=1.0, tf="۵ دقیقه"))
                s.commit()
        except Exception as e:
            errors.append(repr(e))

    ts = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert not errors, f"locked: {errors[:3]}"
```

---

## 🔴 ۲-۵ [شدت: بالا] [دسته: performance] — `async def` که event loop را قفل می‌کند

**فایل‌ها:**
- `api/routers/analyze.py` خط ۴۲، ۶۷، ۹۶، ۱۳۶، ۱۵۴
- `api/routers/scan.py` خط ۲۷
- `api/routers/backtest.py` خط ۲۵، ۴۱، ۱۰۱، ۱۱۱
- `api/scheduler.py` خط ۱۶

```python
@router.post("", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest):
    result = analyze(...)      # ← sync: requests.get + pandas + SQLite داخل event loop!
```

**مشکل:** همه‌ی endpointها `async def` هستند اما بدنه‌ی آن‌ها **کاملاً sync و blocking** است:

- `analyze()` → `fetch_ohlcv` → `requests.get(timeout=20)` → **I/O بلاک‌کننده**
- `pandas_ta` روی ۲۰۰ کندل → **CPU بلاک‌کننده**
- `record_signal()` → `session.commit()` → **I/O بلاک‌کننده**

**اثر واقعی:** تا وقتی یک کاربر `POST /analyze` می‌زند، **هیچ درخواست دیگری** — حتی `GET /health` — پاسخ نمی‌گیرد. سناریوی بد:

- `POST /scan` با `limit=15` روی `tickers[:45]`، هر نماد تا ۶ fetch → تا **۲۷۰ درخواست شبکه‌ای سریال** → چند دقیقه event loop کاملاً قفل
- Uvicorn با یک worker → کل سرویس برای همه‌ی کاربران down می‌شود
- Load balancer/healthcheck → اپ را unhealthy می‌بیند و restart می‌کند

**راه‌حل — دو گزینه (اولی برای الان، دومی برای آینده):**

```python
# ═══ گزینه ۱: سریع — اجرای sync در threadpool ═══
# ─── api/routers/analyze.py ───
from fastapi.concurrency import run_in_threadpool

@router.post("", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest):
    result = await run_in_threadpool(
        analyze,
        ticker=req.ticker,
        source=req.source,
        tf_name=req.timeframe,
        market_type=req.market_type,
        risk_profile=req.risk_profile,
        ticker_name=req.ticker_name or req.ticker,
        include_extras=True,
    )
    if result is None:
        raise HTTPException(404, detail=f"تحلیل برای {req.ticker} امکان‌پذیر نبود — دیتا کافی نیست")
    return AnalyzeResponse(**result)
```

```python
# ─── api/routers/scan.py — موازی به‌جای سریال ───
import asyncio
from fastapi.concurrency import run_in_threadpool

@router.post("", response_model=ScanResponse)
async def scan_endpoint(req: ScanRequest):
    cat_data = MARKET_CATEGORIES.get(req.category)
    if not cat_data:
        raise HTTPException(404, detail=f"دسته {req.category} پیدا نشد")

    tickers = cat_data.get("tickers", [])
    if not tickers:
        raise HTTPException(404, detail=f"دسته {req.category} خالی است")

    source = "tsetmc" if req.category == "iran_stocks" else cat_data.get("source", "nobitex")

    # ─── نرمال‌سازی ورودی ───
    parsed = []
    for item in tickers:
        if isinstance(item, tuple):
            t, n = item[0], (item[1] if len(item) > 1 else item[0])
        elif isinstance(item, dict):
            t, n = item.get("ticker", ""), item.get("name", "")
            n = n or t
        else:
            t = n = str(item)
        if t:
            parsed.append((t, n))

    # ─── هم‌زمانی محدود: ۶ تا هم‌زمان ───
    sem = asyncio.Semaphore(6)

    async def _one(ticker: str, name: str):
        async with sem:
            return await run_in_threadpool(
                analyze,
                ticker=ticker, source=source, tf_name=req.timeframe,
                market_type=req.market_type, risk_profile=req.risk_profile,
                ticker_name=name, include_extras=False,
            )

    # ─── هر نماد مستقل، خطا بقیه را نمی‌خواباند ───
    raw = await asyncio.gather(
        *(_one(t, n) for t, n in parsed[: req.limit * 3]),
        return_exceptions=True,
    )

    results = []
    for (ticker, name), r in zip(parsed[: req.limit * 3], raw):
        if isinstance(r, Exception):
            logger.warning(f"[Scan] خطا در {ticker}: {r}")
            continue
        if r and r.get("direction") != "neutral":
            results.append(ScanItem(
                ticker=ticker, name=name, price=r["price"],
                signal=r["signal"], confidence=r["confidence"],
                direction=r["direction"],
            ))
        if len(results) >= req.limit:
            break

    results.sort(key=lambda x: -x.confidence)
    return ScanResponse(
        category=req.category, timeframe=req.timeframe,
        total=len(results), items=results,
    )
```

```python
# ─── api/routers/backtest.py — history هم threadpool ───
from fastapi.concurrency import run_in_threadpool

@router.get("", response_model=BacktestResponse)
async def backtest_stats(tf: str = "", source: str = "", time_filter: str = "all"):
    stats = await run_in_threadpool(compute_stats, tf, source, time_filter)
    return BacktestResponse(stats=BacktestStats(**stats), items=[])
```

**تست:**
```python
# tests/test_no_event_loop_blocking.py
import asyncio, time
import httpx
from api.main import app

async def test_health_responds_during_analyze():
    """
    /health باید فوراً جواب بدهد حتی وقتی /scan در حال اجراست.
    قبل از اصلاح: /health منتظر می‌ماند.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        scan_task = asyncio.create_task(
            c.post("/scan", json={"category": "crypto", "limit": 5}, timeout=120)
        )
        await asyncio.sleep(0.5)

        t0 = time.perf_counter()
        r = await c.get("/health", timeout=5)
        elapsed = time.perf_counter() - t0

        assert r.status_code == 200
        assert elapsed < 1.0, f"health took {elapsed:.2f}s — event loop blocked!"

        scan_task.cancel()
```

---

# ۳. Timezone — بدترین بخش پروژه

## 🔴 ۳-۱ [شدت: بالا] [دسته: باگ] — سه منبع، سه timezone متفاوت

**فایل‌ها و خطوط دقیق:**

| منبع | فایل:خط | کد | وضعیت index |
|---|---|---|---|
| **نوبیتکس** | `core/nobitex_fetcher.py:542` | `pd.to_datetime(ts, unit="s", utc=True)` | ✅ **tz-aware UTC** |
| **بیت‌پین** | `core/bitpin_fetcher.py:125` | `pd.to_datetime(df["ts"], unit="s")` | ❌ **naive به وقت محلی (تهران)** |
| **والکس** | `core/wallex_fetcher.py:125` | `pd.to_datetime(data["t"], unit="s")` | ❌ **naive به وقت محلی (تهران)** |
| **TSETMC** | `core/tsetmc_fetcher.py:213` | `pd.to_datetime(..., format="%Y%m%d")` | ❌ **naive، تاریخ تقویمی بدون ساعت** |

**تأیید تجربی** (`services/backtest_service.py:60-65`):

```python
entry_naive = _strip_tz(entry_ts)          # ← UTC-naive
if hasattr(df.index, "tz") and df.index.tz is not None:
    df = df[df.index.tz_localize(None) >= entry_naive]
else:
    df = df[df.index >= entry_naive]       # ← مقایسه UTC با تهران!
```

خروجی واقعی تست من:

```
nobitex(UTC-aware)   -> kept 3 of 5 | first index: 2026-01-01 00:10:00+00:00   ✅ درست
bitpin(naive-local)  -> kept 5 of 5 | first index: 2026-01-01 03:30:00         ❌ فیلتر بی‌اثر
entry_naive = 2026-01-01 00:10:00
```

**اثر:** برای بیت‌پین و والکس و TSETMC، فیلتر «کندل‌های بعد از ثبت سیگنال» **تقریباً هیچ‌وقت کار نمی‌کند** — به‌اندازه‌ی ۳:۳۰ ساعت به آینده شیفت خورده. یعنی `_check_one` روی **کندل‌هایی داوری می‌کند که قبل از ثبت سیگنال بسته شده‌اند**. تمام win/loss/win-rate بیت‌پین و والکس **بی‌اعتبار** است.

همین باگ در `core/backtester.py` خط ۸۶، ۱۵۷، ۲۵۶، ۵۱۶ (`datetime.now()` naive محلی) هم هست.

**راه‌حل — نرمال‌سازی اجباری در یک نقطه:**

```python
# ─── core/tz.py (جدید) ───
"""مدیریت متمرکز timezone — تنها منبع حقیقت"""
from datetime import datetime, timezone, timedelta

import pandas as pd

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))
UTC = timezone.utc


def ensure_utc_index(df: pd.DataFrame, *, assume_tz: str = "Asia/Tehran") -> pd.DataFrame:
    """
    index را به UTC-aware نرمال می‌کند.

    قواعد:
      - اگر tz-aware است → به UTC تبدیل
      - اگر naive است → با assume_tz محلی‌سازی، بعد به UTC

    ⚠️ assume_tz برای داده‌های صرافی ایرانی «Asia/Tehran» است،
       چون API آن‌ها timestamp را به وقت محلی می‌دهد.
    """
    if df is None or df.empty:
        return df

    idx = df.index

    if isinstance(idx, pd.DatetimeIndex):
        if idx.tz is not None:
            df.index = idx.tz_convert("UTC")
        else:
            df.index = idx.tz_localize(assume_tz, ambiguous="NaT",
                                       nonexistent="NaT").tz_convert("UTC")
        return df

    # index غیر datetime → تبدیل
    df.index = pd.to_datetime(df.index, errors="coerce", utc=True)
    return df[~df.index.isna()]


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_utc_naive(dt: datetime) -> datetime:
    """برای مقایسه با index نرمال‌شده‌ی UTC-naive"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).replace(tzinfo=None)
```

```python
# ─── core/bitpin_fetcher.py — خط ۱۲۳-۱۴۱ (اصلاح‌شده) ───
from core.tz import ensure_utc_index

    try:
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["ts"], unit="s", utc=True)   # ← utc=True
        df.set_index("time", inplace=True)

        for col in ["open", "close", "low", "high", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["open", "high", "low", "close", "volume"]].copy()
        df = df.dropna()
        df = df[~df.index.duplicated(keep="last")]     # ← اضافه شد
        df = df.sort_index()
        df = ensure_utc_index(df)                       # ← تضمین نهایی

        if len(df) < 20:
            return None
        return df
    except Exception as e:
        logger.warning(f"[Bitpin] parse {ticker}: {e}")
        return None
```

```python
# ─── core/wallex_fetcher.py — خط ۱۲۲-۱۴۲ (اصلاح‌شده) ───
from core.tz import ensure_utc_index

    try:
        df = pd.DataFrame({
            "time": pd.to_datetime(data["t"], unit="s", utc=True),   # ← utc=True
            "open": data["o"], "high": data["h"], "low": data["l"],
            "close": data["c"], "volume": data["v"],
        })
        df.set_index("time", inplace=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna()
        df = df[~df.index.duplicated(keep="last")]
        df = df.sort_index()
        df = ensure_utc_index(df)
        if len(df) < 20:
            return None
        return df
    except Exception as e:
        logger.warning(f"[Wallex] parse {ticker}: {e}")
        return None
```

```python
# ─── core/tsetmc_fetcher.py — خط ۲۱۲-۲۲۶ (اصلاح‌شده) ───
from core.tz import ensure_utc_index

        df["date"] = pd.to_datetime(
            df["date"].astype(str), format="%Y%m%d", errors="coerce"
        )
        df = df.dropna(subset=["date"])
        df = df.set_index("date")
        df = df.sort_index()
        df = df[(df["close"] > 0) & (df["high"] > 0) & (df["low"] > 0)]
        # ─── تاریخ تقویمی TSETMC → نیمه‌شب تهران → UTC-aware ───
        df = ensure_utc_index(df, assume_tz="Asia/Tehran")
        df = df.tail(days)
        return df
```

```python
# ─── services/backtest_service.py — خط ۲۴-۲۸ و ۵۹-۶۷ (اصلاح‌شده) ───
from core.tz import to_utc_naive


def _check_one(log: SignalLog) -> str | None:
    if log.result is not None:
        return None
    if not log.sl or not log.tp or not log.price:
        return None

    timeout = SIGNAL_TIMEOUT.get(log.tf, timedelta(hours=2))

    # ─── همه‌چیز در UTC-naive ───
    now_naive = to_utc_naive(_utcnow())
    entry_naive = to_utc_naive(log.timestamp)

    if now_naive > entry_naive + timeout:
        log.expired = True
        log.result = "expired"
        log.result_time = _utcnow()
        return "expired"

    try:
        df = fetch_ohlcv(log.ticker, log.tf, log.source, use_cache=True)
    except Exception as e:
        logger.debug(f"[Backtest] {log.ticker}: {e}")
        return None

    if df is None or df.empty:
        return None

    # ─── index از قبل UTC-aware است (core.tz تضمین می‌کند) ───
    if df.index.tz is not None:
        df = df[df.index.tz_convert("UTC").tz_localize(None) >= entry_naive]
    else:
        logger.warning(
            f"[Backtest] index بدون tz برای {log.ticker}/{log.source} — "
            f"نرمال‌سازی اجباری"
        )
        df = df[df.index >= entry_naive]

    if df.empty:
        return None
    # ... ادامه منطق
```

**تست:**
```python
# tests/test_tz_normalization.py
import pandas as pd
import pytest
from core.tz import ensure_utc_index, to_utc_naive
from datetime import datetime, timezone


def test_naive_local_becomes_utc():
    df = pd.DataFrame(
        {"close": [1.0]},
        index=pd.to_datetime(["2026-01-01 03:30:00"]),   # به وقت تهران
    )
    out = ensure_utc_index(df, assume_tz="Asia/Tehran")
    assert out.index.tz is not None
    assert out.index[0] == pd.Timestamp("2026-01-01 00:00:00", tz="UTC")


def test_aware_utc_unchanged():
    df = pd.DataFrame({"close": [1.0]},
                      index=pd.to_datetime(["2026-01-01T00:00:00Z"]))
    out = ensure_utc_index(df)
    assert out.index[0] == pd.Timestamp("2026-01-01 00:00:00", tz="UTC")


def test_backtest_filter_matches_for_all_sources():
    """همان کندل → همان فیلتر، مستقل از منبع"""
    entry = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)
    entry_naive = to_utc_naive(entry)

    # سه نمایش مختلف از همان لحظات
    nobitex = pd.DataFrame({"h": range(5)},
        index=pd.date_range("2026-01-01 00:00", periods=5, freq="5min", tz="UTC"))
    bitpin = pd.DataFrame({"h": range(5)},
        index=pd.date_range("2026-01-01 03:30", periods=5, freq="5min"))  # تهران

    for name, raw in (("nobitex", nobitex), ("bitpin", bitpin)):
        df = ensure_utc_index(raw)
        kept = df[df.index.tz_convert("UTC").tz_localize(None) >= entry_naive]
        assert len(kept) == 3, f"{name}: expected 3, got {len(kept)}"
```

---

## 🔴 ۳-۲ [شدت: بالا] [دسته: باگ] — `datetime.utcnow()` در schema + naive در utils

**فایل:** `api/schemas.py` خط ۹۵

```python
timestamp: datetime = Field(default_factory=datetime.utcnow)   # ← deprecated + naive
```

**فایل:** `core/utils.py` خط ۲۶۹-۲۷۳

```python
now = datetime.now()              # ← naive محلی (تهران)
if dt.tzinfo is not None:
    dt = dt.replace(tzinfo=None)  # ← UTC را naive می‌کند، بدون تبدیل!
delta = now - dt                  # ← UTC-naive منهای تهران-naive = ۳:۳۰ خطا
```

**مشکل سه‌گانه:**

1. `datetime.utcnow()` در Python 3.12+ deprecated است و **naive** برمی‌گرداند → `isoformat()` بدون `Z` می‌دهد → `new Date(iso)` در مرورگر آن را **به وقت محلی کاربر** پارس می‌کند، نه UTC. (subagent تأیید کرد: `new Date("2026-02-14T10:00:00")` → `06:30Z` روی این ماشین)
2. `time_ago` و `format_time_short`/`format_datetime_short` (خط ۲۹۲-۳۲۱) همه UTC را به‌عنوان زمان محلی نمایش می‌دهند
3. `api/routers/backtest.py` خط ۷۴ و ۸۸ هم `r.timestamp.isoformat()` می‌دهد → اگر SQLite رشته را بدون tz برگرداند، مشکل بالا رخ می‌دهد

**راه‌حل:**

```python
# ─── api/schemas.py خط ۹۵ ───
from datetime import datetime, timezone

def _utcnow_aware() -> datetime:
    """UTC با timezone — isoformat آن با +00:00 تمام می‌شود، پس مرورگر درست پارس می‌کند"""
    return datetime.now(timezone.utc)

class AnalyzeResponse(BaseModel):
    ...
    timestamp: datetime = Field(default_factory=_utcnow_aware)
```

```python
# ─── core/utils.py خط ۲۵۱-۳۲۱ (اصلاح کامل) ───
from datetime import datetime, timezone, timedelta

UTC = timezone.utc


def _as_utc(dt_input) -> datetime | None:
    """
    هر ورودی را به UTC-aware تبدیل می‌کند.

    ⚠️ naive را «UTC» فرض می‌کنیم، چون همه‌ی timestampهای بک‌اند UTC-naive هستند
       (SQLite tz را ذخیره نمی‌کند).
    """
    try:
        if isinstance(dt_input, str):
            dt = datetime.fromisoformat(dt_input.replace("Z", "+00:00"))
        elif isinstance(dt_input, datetime):
            dt = dt_input
        elif isinstance(dt_input, (int, float)):
            dt = datetime.fromtimestamp(dt_input, tz=UTC)
        else:
            return None
    except Exception:
        return None

    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def time_ago(dt_input) -> str:
    """متن «چند دقیقه پیش» — با فرض UTC-naive برای ورودی بدون tz"""
    dt = _as_utc(dt_input)
    if dt is None:
        return "—"

    secs = (datetime.now(UTC) - dt).total_seconds()

    if secs < 0:
        return "الان"          # ← ساعت سیستم عقب است
    if secs < 5:
        return "همین الان"
    if secs < 60:
        return f"{int(secs)} ثانیه پیش"
    if secs < 3600:
        return f"{int(secs / 60)} دقیقه پیش"
    if secs < 86400:
        return f"{int(secs / 3600)} ساعت پیش"
    return f"{int(secs / 86400)} روز پیش"


def format_time_short(dt_input) -> str:
    """HH:MM:SS به وقت **ایران**"""
    dt = _as_utc(dt_input)
    if dt is None:
        return "—"
    return dt.astimezone(IRAN_TZ).strftime("%H:%M:%S")


def format_datetime_short(dt_input) -> str:
    """MM-DD HH:MM به وقت **ایران**"""
    dt = _as_utc(dt_input)
    if dt is None:
        return "—"
    return dt.astimezone(IRAN_TZ).strftime("%m-%d %H:%M")
```

```typescript
// ─── frontend/src/lib/date.ts (جدید) ───
/**
 * پارس امن ISO — اگر tz ندارد، UTC فرض کن (بک‌اند UTC-naive می‌فرستد)
 */
export function parseUtc(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  // بک‌اند ممکن است بدون Z/+00:00 بفرستد
  const hasTz = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  const d = new Date(hasTz ? iso : `${iso}Z`);
  return Number.isFinite(d.getTime()) ? d : null;
}

export function toJalali(iso: string): string {
  const d = parseUtc(iso);
  if (!d) return "—";
  try {
    return new Intl.DateTimeFormat("fa-IR", {
      year: "2-digit", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    }).format(d);
  } catch {
    return "—";
  }
}

const TF_TIMEOUT_MIN: Record<string, number> = {
  "۱ دقیقه": 30, "۵ دقیقه": 120, "۱۵ دقیقه": 360,
  "۳۰ دقیقه": 720, "۱ ساعت": 2880, "روزانه": 10080,
};

export function timeLeftMin(iso: string, tf: string, result: string | null): number {
  if (result) return -1;
  const d = parseUtc(iso);
  if (!d) return -1;
  const timeoutMin = TF_TIMEOUT_MIN[tf] ?? 120;
  const diff = d.getTime() + timeoutMin * 60_000 - Date.now();
  return Math.floor(diff / 60_000);
}
```

**تست:**
```python
# tests/test_time_ago_tz.py
from datetime import datetime, timezone, timedelta
from core.utils import time_ago, format_time_short

def test_utc_naive_treated_as_utc():
    """5 دقیقه پیش به UTC → «5 دقیقه پیش» نه «3 ساعت پیش»"""
    five_min_ago_utc_naive = (
        datetime.now(timezone.utc) - timedelta(minutes=5)
    ).replace(tzinfo=None)
    assert time_ago(five_min_ago_utc_naive) == "5 دقیقه پیش"

def test_result_time_never_negative():
    """آینده → «الان» نه عدد منفی"""
    future = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(tzinfo=None)
    assert time_ago(future) == "الان"

def test_format_time_short_is_iran_tz():
    dt_utc = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert format_time_short(dt_utc) == "03:30:00"
```

---

# ۴. Error handling و امنیت

## 🔴 ۴-۱ [شدت: بالا] [دسته: امنیت] — هیچ endpoint احراز هویت ندارد + `DELETE /backtest/reset` باز است

**فایل:** `api/routers/backtest.py` خط ۱۱۰-۱۱۸ · `api/main.py` خط ۷۱-۷۵

```python
@router.delete("/reset")
async def backtest_reset(session: Session = Depends(get_session)):
    """حذف همه سیگنال‌ها"""
    rows = session.exec(select(SignalLog)).all()
    count = len(rows)
    for r in rows:
        session.delete(r)
    session.commit()
    return {"ok": True, "deleted": count}
```

**مشکل:** هیچ‌کدام از ۱۲ endpoint احراز هویت، authorization یا rate limit ندارند. `JWT_SECRET` در `api/config.py` خط ۶۳ تعریف شده و **هیچ‌جا استفاده نمی‌شود** (فاز ۷).

عواقب مشخص:
- `curl -X DELETE http://host:8000/backtest/reset` → **کل تاریخچه‌ی سیگنال‌ها و آمار win-rate نابود می‌شود** بدون هیچ تأییدی
- `POST /scan` با `limit=100` → ۱۰۰ نماد × تا ۶ fetch شبکه‌ای = **آمپلیفایر DoS** روی IP شما (صرافی‌ها ممکن است block کنند)
- CORS فقط `localhost:3000` را مجاز می‌کند ✅ ولی این جلوی `curl` را نمی‌گیرد

**راه‌حل:**

```python
# ─── api/deps.py (جدید) ───
"""احراز هویت و rate limiting"""
import logging
import time
from collections import defaultdict

from fastapi import Header, HTTPException, Request, status

from api.config import settings

logger = logging.getLogger(__name__)


# ═══ ۱. Admin token ساده (تا فاز ۷ که JWT کامل بیاید) ═══
async def require_admin(x_admin_token: str = Header(default="")):
    """عملیات مخرب فقط با توکن admin"""
    if not settings.ADMIN_TOKEN:
        logger.error("[Auth] ADMIN_TOKEN تنظیم نشده — عملیات admin مسدود شد")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_TOKEN روی سرور تنظیم نشده است",
        )
    if x_admin_token != settings.ADMIN_TOKEN:
        logger.warning("[Auth] تلاش ناموفق برای عملیات admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="دسترسی admin لازم است",
        )
    return True


# ═══ ۲. Rate limiter ساده (in-memory، کافی برای یک worker) ═══
_buckets: dict[str, list[float]] = defaultdict(list)


def rate_limit(key: str, limit: int, window_sec: int = 60):
    """
    محدودیت نرخ sliding-window.

    برای چند worker باید به Redis منتقل شود (فاز ۷).
    """
    now = time.time()
    bucket = _buckets[key]
    cutoff = now - window_sec
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)

    if len(bucket) >= limit:
        retry = int(bucket[0] + window_sec - now) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"تعداد درخواست زیاد است — {retry} ثانیه دیگر تلاش کن",
            headers={"Retry-After": str(retry)},
        )
    bucket.append(now)


async def client_ip(request: Request) -> str:
    """IP واقعی — با احتساب reverse proxy"""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

```python
# ─── api/routers/backtest.py (اصلاح‌شده) ───
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func
from api.deps import require_admin

@router.delete("/reset")
async def backtest_reset(
    _: bool = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """حذف همه سیگنال‌ها — نیازمند توکن admin"""
    count = session.exec(select(func.count()).select_from(SignalLog)).one()
    session.exec(delete(SignalLog))      # ← یک query، نه N تا
    session.commit()
    logger.warning(f"[Backtest] ⚠️ RESET — {count} ردیف حذف شد")
    return {"ok": True, "deleted": int(count)}
```

```python
# ─── api/routers/scan.py — rate limit سنگین‌ترین endpoint ───
from api.deps import client_ip, rate_limit

@router.post("", response_model=ScanResponse)
async def scan_endpoint(req: ScanRequest, request: Request):
    rate_limit(f"scan:{await client_ip(request)}", limit=3, window_sec=60)
    ...
```

```python
# ─── api/config.py — اضافه کن ───
    # ─── Admin (تا فاز ۷) ───
    ADMIN_TOKEN: str = ""

    # ─── Rate limits ───
    RL_ANALYZE_PER_MIN: int = 30
    RL_SCAN_PER_MIN: int = 3
    RL_QUOTE_PER_MIN: int = 120
```

```env
# ─── .env.example — اضافه کن ───
# توکن ادمین برای عملیات مخرب (reset). با `openssl rand -hex 32` بساز.
ADMIN_TOKEN=
```

**تست:**
```python
# tests/test_auth.py
import httpx
from api.main import app
from api.config import settings

async def test_reset_requires_admin_token():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        # بدون توکن → 403 یا 503
        r = await c.delete("/backtest/reset")
        assert r.status_code in (403, 503)

        # با توکن درست
        settings.ADMIN_TOKEN = "test-token"
        r = await c.delete("/backtest/reset", headers={"x-admin-token": "test-token"})
        assert r.status_code == 200

async def test_scan_rate_limited():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        codes = []
        for _ in range(5):
            r = await c.post("/scan", json={"category": "crypto", "limit": 1})
            codes.append(r.status_code)
        assert 429 in codes, codes
```

---

## 🔴 ۴-۲ [شدت: بالا] [دسته: امنیت] — فایل کلید API بدون gitignore + `JWT_SECRET` پیش‌فرض

**فایل:** `core/nobitex_auth.py` خط ۲۴ · `.gitignore` (کل فایل) · `api/config.py` خط ۶۳

```python
API_KEYS_FILE = Path("api-keys nobitex.txt")     # ← الگوی ignore وجود ندارد
```

```python
JWT_SECRET: str = "change-me-in-production"      # ← پیش‌فرض ناامن در کد
```

**مشکل:**
- `.gitignore` فقط `.env*` را ignore می‌کند. `git add .` → `api-keys nobitex.txt` **کامیت می‌شود**
- پروژه یک remote عمومی دارد (`github.com/a3mun/tradeyar` طبق `PROJECT_STATUS.md` خط ۱۲۹)
- `nobitex_auth` مقدار `settings.NOBITEX_API_KEY` را **کاملاً نادیده می‌گیرد** → دو منبع حقیقت برای یک secret
- `JWT_SECRET` پیش‌فرض commit شده است؛ اگر کسی فاز ۷ را با پیش‌فرض deploy کند، می‌توان توکن جعل کرد

**راه‌حل:**

```gitignore
# ─── Secrets — هرگز کامیت نشود ───
.env
.env.local
.env*.local
*api-keys*
api-keys*.txt
secrets/
*.key
*.pem
*.p12
```

```python
# ─── core/nobitex_auth.py — یک منبع حقیقت: settings ───
"""اتصال به API اختصاصی نوبیتکس

اولویت منابع کلید:
  1. متغیرهای محیطی (NOBITEX_API_KEY / NOBITEX_SECRET_KEY) ← production
  2. فایل secrets/nobitex_api_keys.json                     ← dev
اگر هیچ‌کدام نبود، fallback به public API.
"""

import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Optional

import requests

from api.config import settings
from core.paths import SECRETS_DIR

logger = logging.getLogger(__name__)

NOBITEX_BASE = "https://apiv2.nobitex.ir"
API_KEYS_FILE = SECRETS_DIR / "nobitex_api_keys.json"
TIMEOUT = 15

_keys_cache: Optional[dict] = None
_keys_lock = threading.Lock()


def load_api_keys() -> Optional[dict]:
    """بارگذاری کلیدها — env اول، بعد فایل"""
    global _keys_cache
    with _keys_lock:
        if _keys_cache is not None:
            return _keys_cache

        # ─── ۱. متغیر محیطی ───
        if settings.NOBITEX_API_KEY and settings.NOBITEX_SECRET_KEY:
            _keys_cache = {
                "api_key": settings.NOBITEX_API_KEY,
                "secret": settings.NOBITEX_SECRET_KEY,
            }
            logger.info("[NobitexAuth] کلید از environment بارگذاری شد")
            return _keys_cache

        # ─── ۲. فایل ───
        try:
            if API_KEYS_FILE.exists():
                with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                api_key = data.get("apiKey", "").strip()
                secret = data.get("secretKey", "").strip()
                if api_key and secret:
                    _keys_cache = {"api_key": api_key, "secret": secret}
                    logger.info(f"[NobitexAuth] کلید از {API_KEYS_FILE.name} بارگذاری شد")
                    return _keys_cache
        except Exception:
            logger.exception("[NobitexAuth] خطا در خواندن فایل کلید")

        logger.debug("[NobitexAuth] کلیدی تنظیم نشده — public API")
        return None
```

```python
# ─── api/config.py — اضافه و اعتبارسنجی ───
from pydantic import field_validator

class Settings(BaseSettings):
    ...
    NOBITEX_API_KEY: str = ""
    NOBITEX_SECRET_KEY: str = ""        # ← اضافه شد
    ADMIN_TOKEN: str = ""
    JWT_SECRET: str = ""

    @field_validator("JWT_SECRET")
    @classmethod
    def _check_jwt_secret(cls, v: str, info) -> str:
        """هرگز با پیش‌فرض ناامن در production اجرا نشو"""
        debug = info.data.get("DEBUG", True)
        if not debug and (not v or v == "change-me-in-production" or len(v) < 32):
            raise ValueError(
                "JWT_SECRET در production باید تنظیم و حداقل ۳۲ کاراکتر باشد. "
                "با `openssl rand -hex 32` بساز."
            )
        return v or "dev-only-not-for-production"
```

```powershell
# ─── پاک‌سازی اگر قبلاً کامیت شده ───
git rm --cached "api-keys nobitex.txt"
# ─── چرخش کلید در پنل نوبیتکس (کلید قدیمی را باطل کن) ───
```

**تست:**
```bash
git check-ignore -v "api-keys nobitex.txt"        # باید ignore را نشان دهد
git ls-files | findstr "api-keys"                 # باید خالی باشد
```

---

## 🟡 ۴-۳ [شدت: متوسط] [دسته: باگ] — `backtest_all` با یک خطا **کل batch** را از دست می‌دهد

**فایل:** `services/backtest_service.py` خط ۱۱۴-۱۳۹

```python
try:
    with Session(engine) as session:
        logs = session.exec(stmt).all()
        for log in logs:
            result["checked"] += 1
            outcome = _check_one(log)     # ← خطا اینجا کل تابع را می‌کشد
            if outcome:
                ...
                session.add(log)
        session.commit()                   # ← هرگز اجرا نمی‌شود
except Exception as e:
    logger.error(f"[Backtest] خطا: {e}")   # ← همه‌ی نتایج از دست رفت
```

**مشکل:** اگر یک سیگنال (مثلاً از میان ۲۰۰) خطای غیرمنتظره بدهد:

- **هیچ‌کدام** از نتایج آن اجرا commit نمی‌شود → کار تمام‌شده هدر می‌رود
- در اجرای بعدی، همان سیگنال مشکل‌دار دوباره خطا می‌دهد → **بن‌بست دائمی**: هیچ‌وقت پیشرفت نمی‌کند
- خطا فقط لاگ می‌شود؛ هیچ `job status` یا metric وجود ندارد

**راه‌حل:**

```python
"""
services/backtest_service.py — مقاوم در برابر خطا
"""
import logging
from datetime import timedelta

from sqlmodel import Session, select

from api.database import engine
from api.models import SignalLog

logger = logging.getLogger(__name__)


def backtest_all(max_checks: int = 200) -> dict:
    """
    بررسی سیگنال‌های در انتظار.

    هر سیگنال مستقل پردازش می‌شود؛ خطای یکی بقیه را متوقف نمی‌کند.
    نتایج به‌صورت دوره‌ای commit می‌شوند تا کار انجام‌شده از دست نرود.
    """
    result = {
        "checked": 0, "updated": 0, "expired": 0,
        "win": 0, "loss": 0, "errors": 0,
    }

    # ─── مرحله ۱: فقط شناسه‌ها را بگیر (session کوتاه) ───
    try:
        with Session(engine) as session:
            stmt = (
                select(SignalLog.id)
                .where(SignalLog.result.is_(None))
                .order_by(SignalLog.timestamp.asc())
                .limit(max_checks)
            )
            ids = list(session.exec(stmt).all())
    except Exception:
        logger.exception("[Backtest] خطا در خواندن لیست سیگنال‌ها")
        return result

    COMMIT_EVERY = 25

    for batch_start in range(0, len(ids), COMMIT_EVERY):
        batch = ids[batch_start : batch_start + COMMIT_EVERY]
        pending_writes = []

        try:
            with Session(engine) as session:
                for log_id in batch:
                    log = session.get(SignalLog, log_id)
                    if log is None or log.result is not None:
                        continue

                    result["checked"] += 1
                    try:
                        outcome = _check_one(log)
                    except Exception:
                        # ─── یک سیگنال خراب بقیه را نمی‌خواباند ───
                        logger.exception(
                            f"[Backtest] خطا در سیگنال {log_id} "
                            f"({log.ticker}/{log.tf}) — رد شد"
                        )
                        result["errors"] += 1
                        continue

                    if outcome:
                        pending_writes.append((log, outcome))

                # ─── مرحله ۳: نوشتن batch ───
                for log, outcome in pending_writes:
                    session.add(log)
                    result["updated"] += 1
                    if outcome == "expired":
                        result["expired"] += 1
                    elif outcome == "win":
                        result["win"] += 1
                    elif outcome == "loss":
                        result["loss"] += 1

                session.commit()
        except Exception:
            logger.exception(f"[Backtest] خطا در batch {batch_start} — ادامه می‌دهیم")
            result["errors"] += len(batch)

    if result["errors"]:
        logger.warning(f"[Backtest] {result['errors']} سیگنال با خطا رد شد")
    return result
```

**تست:**
```python
# tests/test_backtest_resilience.py
from unittest.mock import patch
from sqlmodel import Session
from api.database import engine
from api.models import SignalLog
import services.backtest_service as bs


def test_one_bad_signal_does_not_kill_batch():
    """سیگنال سوم خطا می‌دهد → ۴ تای دیگر باید ثبت شوند"""
    with Session(engine) as s:
        for i in range(5):
            s.add(SignalLog(ticker=f"T{i}", signal="LONG", price=100.0,
                            sl=95.0, tp=110.0, tf="۵ دقیقه"))
        s.commit()

    call = {"n": 0}

    def flaky(log):
        call["n"] += 1
        if call["n"] == 3:
            raise RuntimeError("boom")
        return "win"

    with patch.object(bs, "_check_one", side_effect=flaky):
        r = bs.backtest_all()

    assert r["checked"] == 5
    assert r["errors"] == 1
    assert r["win"] == 4, f"expected 4 wins committed, got {r}"
```

---

## 🟡 ۴-۴ [شدت: متوسط] [دسته: باگ] — `except: pass` های بی‌صدا در fetcherها

**فایل‌ها و خطوط:**

| فایل | خط | مشکل |
|---|---|---|
| `core/bitpin_fetcher.py` | ۱۷۹، ۲۱۰ | `except Exception: return None` — بدون log |
| `core/wallex_fetcher.py` | ۱۸۲، ۲۱۷ | همان |
| `core/nobitex_auth.py` | ۱۸۴ | همان |
| `core/data_fetcher.py` | ۲۱۹-۲۲۰ | `except Exception: pass` — **fallback والکس بی‌صدا می‌میرد** |
| `services/backtest_service.py` | ۶۶-۶۷ | `except Exception: pass` — فیلتر کندل شکست می‌خورد بی‌صدا |
| `api/routers/symbols.py` | ۱۱۰-۱۱۱، ۱۲۴-۱۲۵ | جستجوی TSETMC/نوبیتکس بی‌صدا خالی می‌شود |
| `core/analyzer.py` | ۱۸۷، ۲۰۸، ۲۱۷، ۲۴۸، ۲۵۵، ۲۶۱، ۵۷۰ | اندیکاتورها بی‌صدا صفر می‌شوند |

**مشکل:** وقتی Supertrend یا Keltner شکست بخورد، `df["supertrend_dir"] = 1` می‌شود — یعنی **همیشه صعودی**. تحلیل شما بدون هیچ نشانه‌ای به سمت LONG منحرف می‌شود. کاربر فکر می‌کند اندیکاتور صعودی است، در واقع محاسبه شکست خورده.

**راه‌حل — الگوی «degrade با اعلان»:**

```python
# ─── core/analyzer.py خط ۱۷۹-۲۱۸ (اصلاح) ───
import logging
logger = logging.getLogger(__name__)

STALE_INDICATORS: list[str] = []      # ← per-call، در analyze_symbol ریست شود


def _try_indicator(name: str, fn, default):
    """
    اندیکاتور را با ثبت خطا اجرا می‌کند.

    در صورت شکست، default برمی‌گرداند و نام را در STALE_INDICATORS ثبت می‌کند
    تا در خروجی تحلیل به کاربر هشدار داده شود.
    """
    try:
        return fn()
    except Exception as e:
        STALE_INDICATORS.append(name)
        logger.warning(f"[Analyzer] اندیکاتور {name} شکست خورد: {e!r} — مقدار پیش‌فرض")
        return default


# جای except Exception: pass های بی‌صدا:
        st = _try_indicator(
            "supertrend",
            lambda: ta.supertrend(df["high"], df["low"], df["close"],
                                  length=10, multiplier=3.0),
            None,
        )
        if st is not None and st.shape[1] > 1:
            df["supertrend_dir"] = st.iloc[:, 1]
        else:
            df["supertrend_dir"] = np.nan    # ← NaN، نه 1 (صعودی دروغین)
```

```python
# ─── core/analyzer.py — در analyze_symbol، پس از محاسبه‌ی groups ───
        if STALE_INDICATORS:
            traps["degraded_indicators"] = {
                "active": True,
                "reason": (
                    f"⚠️ {len(STALE_INDICATORS)} اندیکاتور محاسبه نشد: "
                    f"{', '.join(STALE_INDICATORS)} — نتیجه با احتیاط"
                ),
                "severity": 5,
            }
```

**تست:**
```python
# tests/test_indicator_degradation.py
from unittest.mock import patch
import numpy as np
import pandas as pd
from core import analyzer


def _df(n=200):
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    return pd.DataFrame({
        "open": close, "high": close + 0.5, "low": close - 0.5,
        "close": close, "volume": rng.integers(100, 1000, n).astype(float),
    }, index=pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC"))


def test_broken_supertrend_is_reported_not_silently_bullish():
    analyzer.STALE_INDICATORS.clear()
    with patch("pandas_ta_classic.supertrend", side_effect=RuntimeError("api changed")):
        res = analyzer.analyze_symbol(_df(), tf_name="۵ دقیقه", ticker="BTC-USD")

    details = res["groups"]["trend"]["details"]
    assert not (details["supertrend_dir"] > 0), "نباید صعودی دروغین باشد"
    assert res["traps"]["degraded_indicators"]["active"] is True
```

---

# ۵. Type Safety و قرارداد API

## 🟡 ۵-۱ [شدت: متوسط] [دسته: types] — ۱۰ کست ناامن در فرانت + 🔴 فیلدهای تله هرگز نمی‌رسند

**شمارش دقیق (grep تأیید‌شده):**

| نوع | تعداد | محل |
|---|---|---|
| `as any` | ۶ | `Scanner.tsx:243`، `SymbolSelector.tsx:103`، `SymbolSelector.tsx:130`، `TFTable.tsx:94` |
| `: any` | ۴ | `DeepAnalysis.tsx:126`، `BacktestStats.tsx:34,36,39` |
| `@ts-ignore` / `@ts-expect-error` / `@ts-nocheck` | **۰** | — |

**ریشه‌ی مشترک:** `useAppStore.ts` خط ۶ و ۱۹ — `source: string` به‌جای `Source`:

```typescript
interface AppState {
  source: Source;                 // ✅ type درست
  ...
}
interface WatchlistItem {
  source: string;                 // ❌ string خام
}
```

به‌خاطر همین سوراخ، `Scanner.tsx:243` مجبور به `as any` می‌شود.

### 🔴 مشکل جدی‌تر: قابلیت «تشخیص تله» کاملاً مرده است

**فایل:** `api/routers/backtest.py` خط ۷۱-۹۳ — فیلدهای `had_trap` و `trap_type` در پاسخ نیستند، در حالی که:

- `api/models.py:52-53` هر دو را تعریف کرده
- `services/signal_recorder.py:99-100` هر دو را ذخیره می‌کند
- `SignalHistory.tsx:33` و `BacktestStats.tsx:34,39` آن‌ها را می‌خوانند

**نتیجه:** بج تله هرگز نمایش داده نمی‌شود و پنل «دقت هشدار تله‌ها» هرگز ظاهر نمی‌شود.

**راه‌حل:**

```python
# ─── api/routers/backtest.py خط ۶۸-۹۴ (اصلاح‌شده) ───
from datetime import timezone

def _iso_utc(dt):
    """datetime → ISO با tz مشخص (برای پارس درست در مرورگر)"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

    return {
        "ok": True,
        "total": len(rows),
        "items": [
            {
                "id": r.id,
                "timestamp": _iso_utc(r.timestamp),
                "ticker": r.ticker,
                "name": r.name,
                "source": r.source,
                "signal": r.signal,
                "direction": r.direction,
                "confidence": r.confidence,
                "consensus": r.consensus,          # ← اضافه
                "regime": r.regime,                # ← اضافه
                "price": r.price,
                "sl": r.sl,
                "tp": r.tp,
                "rr": r.rr,
                "sl_tp_type": r.sl_tp_type,        # ← اضافه
                "tf": r.tf,
                "market_type": r.market_type,
                "risk_profile": r.risk_profile,    # ← اضافه
                "result": r.result,
                "result_time": _iso_utc(r.result_time),
                "exit_price": r.exit_price,
                "expired": r.expired,
                "had_trap": r.had_trap,            # ✅ حیاتی
                "trap_type": r.trap_type,          # ✅ حیاتی
            }
            for r in rows
        ],
    }
```

```typescript
// ─── frontend/src/store/useAppStore.ts (اصلاح‌شده) ───
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { MarketType, RiskProfile, Source, Timeframe } from "@/lib/types";

interface WatchlistItem {
  ticker: string;
  name: string;
  source: Source;                 // ✅ نه string
}

interface AppState {
  source: Source;
  ticker: string;
  tickerName: string;
  timeframe: Timeframe;
  marketType: MarketType;
  riskProfile: RiskProfile;
  refreshSeconds: number;
  watchlist: WatchlistItem[];
  _hasHydrated: boolean;
  setHasHydrated: (v: boolean) => void;
  // ... بقیه setters با Source به‌جای string
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...DEFAULTS,
      setHasHydrated: (v) => set({ _hasHydrated: v }),
      addToWatchlist: (ticker, name, source: Source) => {
        const current = get().watchlist;
        if (current.some((w) => w.ticker === ticker)) return;
        if (current.length >= 20) return;
        set({ watchlist: [...current, { ticker, name, source }] });
      },
      // ...
    }),
    {
      name: "trademun-store",
      version: 4,
      storage: createJSONStorage(() => localStorage),
      // ─── جلوگیری از hydration mismatch در SSR ───
      skipHydration: true,
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      // ─── مهاجرت نسخه‌ها ───
      migrate: (persisted: unknown, version: number) => {
        const s = (persisted ?? {}) as Record<string, unknown>;
        if (version < 4) {
          // نسخه ۳ source را string نگه می‌داشت
          s.source = (s.source as string) || "nobitex";
          s.watchlist = ((s.watchlist as WatchlistItem[]) || []).map((w) => ({
            ...w,
            source: (w.source as Source) || "nobitex",
          }));
        }
        return s as Partial<AppState>;
      },
      partialize: (state) => ({
        source: state.source,
        ticker: state.ticker,
        tickerName: state.tickerName,
        timeframe: state.timeframe,
        marketType: state.marketType,
        riskProfile: state.riskProfile,
        refreshSeconds: state.refreshSeconds,
        watchlist: state.watchlist,
      }),
    }
  )
);
```

```typescript
// ─── frontend/src/components/scan/Scanner.tsx خط ۲۴۳ ───
// ❌ قبل:  setSource(scanSource as any);
setSource(scanSource);                       // ✅ حالا type-safe است

// ─── SymbolSelector.tsx خط ۱۰۳ و ۱۳۰ ───
selectSymbol(item.ticker, item.name, finalSource);   // ✅ بدون as any
```

**تست:**
```bash
cd frontend
npx tsc --noEmit                    # باید صفر خطا بدهد
npx eslint src --max-warnings 0
```

---

## 🟡 ۵-۲ [شدت: متوسط] [دسته: باگ] — `AnalyzeResponse` کلیدهای تکراری + فیلدهای حذف‌شده

**فایل:** `services/analyzer_service.py` خط ۱۴۳-۱۴۸

```python
"atr": float(result.get("atr", 0.0)),              # ← خط ۱۴۳
"atr_mult_sl": float(sl_tp.get("effective_sl_mult", 1.0)),
"atr_mult_tp": float(sl_tp.get("effective_tp_mult", 1.5)),
"atr": result.get("atr", 0.0),                     # ← خط ۱۴۶: بازنویسی!
"atr_mult_sl": sl_tp.get("effective_sl_mult", 1.0),  # ← بازنویسی!
"atr_mult_tp": sl_tp.get("effective_tp_mult", 1.5),  # ← بازنویسی!
```

**مشکل:** کلیدهای تکراری در dict literal → پایتون آخرین را نگه می‌دارد → تبدیل `float()` **بی‌اثر** می‌شود. اگر `result["atr"]` نباشد، مقدار `0.0` جای `float(...)` را می‌گیرد. بدتر: اگر `atr` مقدار `None` داشته باشد، `AnalyzeResponse` با `atr: float` **خطای validation** می‌دهد → 500 به کاربر.

**فیلدهای حذف‌شده:** `close_series` در `analyzer_service.py:169` پر می‌شود ولی در `api/schemas.py` `AnalyzeResponse` **تعریف نشده** → Pydantic آن را در `response_model` **حذف می‌کند**. فرانت `types.ts:40` آن را `close_series?: number[]` (اختیاری) اعلام کرده — پس نه خطا می‌دهد نه کار می‌کند.

**راه‌حل:**

```python
# ─── services/analyzer_service.py خط ۱۴۳-۱۴۸ (اصلاح‌شده) ───
def _f(val, default: float = 0.0) -> float:
    """تبدیل امن به float — None و NaN را مدیریت می‌کند"""
    try:
        if val is None:
            return default
        out = float(val)
        return out if out == out else default    # NaN check
    except (TypeError, ValueError):
        return default


output = {
    "ok": True,
    "ticker": ticker,
    "name": ticker_name or ticker,
    "source": source,
    "timeframe": tf_name,
    "market_type": market_type,
    "risk_profile": risk_profile,
    "price": _f(result.get("price")),
    "signal": result.get("signal", "خنثی"),
    "direction": result.get("direction", "neutral"),
    "confidence": int(_f(result.get("confidence"))),
    "confidence_tier": result.get("confidence_tier", "neutral"),
    "consensus": result.get("consensus", "neutral"),
    "regime": result.get("regime", "range"),
    "action_fa": result.get("action_fa", ""),
    "explanation": result.get("explanation", ""),
    "sl": _f(sl_tp.get("sl")) or None,
    "tp": _f(sl_tp.get("tp")) or None,
    "rr": _f(result.get("rr")) or None,
    # ─── یک‌بار، درست ───
    "atr": _f(result.get("atr")),
    "atr_mult_sl": _f(sl_tp.get("effective_sl_mult"), 1.0),
    "atr_mult_tp": _f(sl_tp.get("effective_tp_mult"), 1.5),
    # ─── سطوح ───
    "support": _f(result.get("support")),
    "resistance": _f(result.get("resistance")),
    # ... بقیه بدون تغییر
}
```

```python
# ─── api/schemas.py — اضافه کردن فیلدهای واقعاً ارسالی ───
from pydantic import ConfigDict

class AnalyzeResponse(BaseModel):
    ...
    # ─── داده‌ی نمودار ───
    close_series: list[float] = Field(default_factory=list)   # ← اضافه شد

    # ─── اطمینان از serializer درست ───
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )
```

**تست:**
```python
# tests/test_analyzer_service_schema.py
import pytest
from api.schemas import AnalyzeResponse
from services.analyzer_service import analyze


def test_response_never_has_none_floats():
    """هیچ فیلد float نباید None باشد → 500 ندهد"""
    r = analyze("BTC-USD", source="nobitex", tf_name="۵ دقیقه")
    if r is None:
        pytest.skip("دیتای شبکه در دسترس نیست")

    resp = AnalyzeResponse(**r)          # نباید exception بدهد
    assert resp.atr >= 0
    assert isinstance(resp.atr, float)
    assert resp.atr_mult_sl >= 0
    assert resp.timestamp.tzinfo is not None, "timestamp باید tz-aware باشد"


def test_close_series_survives_response_model():
    """close_series باید در پاسخ نهایی بماند"""
    r = analyze("BTC-USD", source="nobitex", tf_name="۵ دقیقه")
    if r is None:
        pytest.skip("no network")
    resp = AnalyzeResponse(**r)
    assert len(resp.close_series) > 0, "close_series حذف شده — schema ناقص است"
```

---

# ۶. Frontend

## 🔴 ۶-۱ [شدت: بالا] [دسته: باگ] — `SignalCard` SL/TP را دوباره از قیمت زنده حساب می‌کند

**فایل:** `frontend/src/components/signal/SignalCard.tsx` خط ۱۵۳-۱۷۷

```typescript
const displayPrice = livePrice ?? data.price ?? 0;

const atr = data.atr ?? 0;
const multSl = data.atr_mult_sl ?? 1.0;
const multTp = data.atr_mult_tp ?? 1.5;

const liveSl = dirLong ? displayPrice - atr * multSl : ...
const liveTp = dirLong ? displayPrice + atr * multTp : ...
```

**مشکل:** بک‌اند در همان پاسخ `sl` و `tp` قطعی را فرستاده (`analyzer_service.py:140-141` → از `result["sl_tp"]`). فرانت آن‌ها را **دور می‌ریزد** و با آخرین قیمت زنده (هر ۵ ثانیه) و ATR **قدیمی** دوباره حساب می‌کند. نتیجه:

- SL نمایش‌داده‌شده با SL ثبت‌شده در `SignalLog` **یکی نیست** → بک‌تست و UI ضد هم حرف می‌زنند
- با هر ۵ ثانیه تیک قیمت، SL/TP کاربر **جابه‌جا می‌شود** → سفارش قابل ثبت نیست
- «R:R» نمایشی همیشه برابر `multTp / multSl` است (ثابت ۱.۶۷)، چون هر دو ضریب در ATR ضرب می‌شوند و ATR حذف می‌شود → **اطلاعات بی‌معنی**

**راه‌حل:**

```typescript
// ─── frontend/src/components/signal/SignalCard.tsx خط ۱۵۳-۱۷۷ (اصلاح‌شده) ───
  // ─── SL/TP از خود تحلیل، نه محاسبه‌ی مجدد ───
  // دلیل: بک‌تست روی همین اعداد داوری می‌کند؛ UI باید همان را نشان دهد.
  const entryPrice = data.price ?? 0;
  const sl = data.sl;
  const tp = data.tp;
  const rr = data.rr;

  const displayPrice = livePrice ?? entryPrice;
  const displayChange = livePrice != null ? liveChange : null;

  // ─── فاصله‌ی قیمت فعلی تا SL/TP (نمایشی، نه تصمیم‌گیری) ───
  const distToSl =
    sl != null && displayPrice > 0
      ? ((displayPrice - sl) / displayPrice) * 100
      : null;
  const distToTp =
    tp != null && displayPrice > 0
      ? ((tp - displayPrice) / displayPrice) * 100
      : null;
```

```tsx
{/* ─── کارت SL/TP — خط ۲۶۸-۲۹۸ (اصلاح‌شده) ─── */}
{sl != null && tp != null && (
  <div className="grid grid-cols-3 gap-1.5">
    <div className="rounded-md border border-red-500/20 bg-red-500/5 px-2 py-2 text-center">
      <div className="flex items-center justify-center gap-1 text-[9px] text-muted-foreground">
        <Shield className="h-2.5 w-2.5" />
        حد ضرر
      </div>
      <p className="num mt-0.5 text-xs font-bold text-red-500">
        {formatNumber(sl)}
      </p>
      {distToSl != null && (
        <p className="num text-[9px] text-muted-foreground">
          {distToSl >= 0 ? "−" : "+"}{Math.abs(distToSl).toFixed(2)}%
        </p>
      )}
    </div>

    <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-2 py-2 text-center">
      <div className="flex items-center justify-center gap-1 text-[9px] text-muted-foreground">
        <Percent className="h-2.5 w-2.5" />
        R:R
      </div>
      <p className="num mt-0.5 text-xs font-bold text-blue-500">
        {rr != null ? rr.toFixed(1) : "—"}
      </p>
    </div>

    <div className="rounded-md border border-green-500/20 bg-green-500/5 px-2 py-2 text-center">
      <div className="flex items-center justify-center gap-1 text-[9px] text-muted-foreground">
        <Target className="h-2.5 w-2.5" />
        هدف
      </div>
      <p className="num mt-0.5 text-xs font-bold text-green-500">
        {formatNumber(tp)}
      </p>
      {distToTp != null && (
        <p className="num text-[9px] text-muted-foreground">
          {distToTp >= 0 ? "+" : "−"}{Math.abs(distToTp).toFixed(2)}%
        </p>
      )}
    </div>
  </div>
)}

{/* ─── برچسب ورود ─── */}
<p className="text-[10px] text-muted-foreground text-center">
  ورود تحلیل: <span className="num">{formatNumber(entryPrice)}</span>
  {livePrice != null && Math.abs(livePrice - entryPrice) > entryPrice * 0.001 && (
    <span className="mr-2">
      · قیمت فعلی: <span className="num">{formatNumber(livePrice)}</span>
    </span>
  )}
</p>
```

```typescript
// ─── خط ۲۳۴ — نمایش change ───
{displayChange != null && displayChange !== 0 && (
  <p className={`num text-[10px] ${displayChange > 0 ? "text-green-500" : "text-red-500"}`}>
    {displayChange > 0 ? "▲" : "▼"} {Math.abs(displayChange).toFixed(2)}%
  </p>
)}
```

**تست:**
```typescript
// frontend/src/components/signal/__tests__/SignalCard.test.tsx
test("SL/TP از پاسخ سرور نمایش داده می‌شود، نه محاسبه‌ی مجدد", async () => {
  mockApi.post.mockResolvedValue({
    data: {
      ...baseAnalysis,
      price: 100, sl: 95, tp: 110, rr: 2.0,
      atr: 3, atr_mult_sl: 1.5, atr_mult_tp: 3.0,
    },
  });
  mockApi.get.mockResolvedValue({ data: { price: 130, change_pct: 1 } });

  render(<SignalCard />);

  // قیمت زنده ۱۳۰ است، ولی SL باید همان ۹۵ سرور باشد
  expect(await screen.findByText("95")).toBeInTheDocument();
  expect(await screen.findByText("110")).toBeInTheDocument();
  expect(await screen.findByText("2.0")).toBeInTheDocument();
  // محاسبه‌ی غلط قبلی می‌داد: 130 - 3*1.5 = 125.5
  expect(screen.queryByText("125.5")).not.toBeInTheDocument();
});
```

---

## 🔴 ۶-۲ [شدت: بالا] [دسته: باگ] — `SymbolSelector` نماد انتخابی کاربر را خودسر عوض می‌کند

**فایل:** `frontend/src/components/signal/SymbolSelector.tsx` خط ۹۷-۱۲۲

```typescript
const handleSelect = (item: SymbolItem) => {
  const isIranianStock = !item.ticker[0]?.match(/[A-Za-z]/);
  const finalSource = isIranianStock ? "tsetmc" : source;   // ← منبع خود item دور ریخته می‌شود
  selectSymbol(item.ticker, item.name, finalSource as any);
  ...
};

// ═══ تغییر صرافی به TSETMC → نماد کریپتو رو پاک کن ═══
useEffect(() => {
  if (source === "tsetmc" && /^[A-Z]/.test(ticker)) {
    setTicker("فولاد", "فولاد مبارکه");        // ← 🔴 نماد کاربر را بی‌صدا عوض می‌کند!
  }
  if (["nobitex", "bitpin", "wallex", "abantether"].includes(source) && !/^[A-Z]/.test(ticker)) {
    setTicker("BTC-USD", "بیت‌کوین (USDT)");   // ← 🔴 همان
  }
}, [source, ticker, setTicker]);
```

**سناریوی قطعی باگ:** کاربر در حالت `source = "tsetmc"` روی چیپ «بیت‌کوین (USDT)» کلیک می‌کند:

1. `handleSelect` → `finalSource = "tsetmc"` (چون BTC انگلیسی است، `isIranianStock = false` → `finalSource = source = "tsetmc"`)
2. استور می‌شود `{ticker: "BTC-USD", source: "tsetmc"}`
3. `useEffect` خط ۱۱۲ شرط `/^[A-Z]/.test("BTC-USD")` را **درست** می‌بیند
4. `setTicker("فولاد", "فولاد مبارکه")` → **کاربر بیت‌کوین خواست، فولاد گرفت**

بدون هیچ پیامی. کاربر مبتدی فکر می‌کند تحلیل بیت‌کوین است.

**راه‌حل:**

```typescript
// ─── frontend/src/components/signal/SymbolSelector.tsx (اصلاح‌شده) ───
import type { Source, SymbolItem } from "@/lib/types";

const CRYPTO_SOURCES: Source[] = ["nobitex", "bitpin", "wallex", "abantether"];

function isIranianTicker(ticker: string): boolean {
  return !!ticker && !/^[A-Za-z0-9]/.test(ticker);
}

function handleSelect(item: SymbolItem) {
  // ─── منبع خود آیتم ملاک است، نه منبع فعلی استور ───
  // بک‌اند در /symbols/search و /symbols/popular برای هر آیتم source می‌فرستد
  const itemSource = item.source as Source | undefined;
  const finalSource: Source =
    itemSource && (itemSource === "tsetmc" || CRYPTO_SOURCES.includes(itemSource))
      ? itemSource
      : isIranianTicker(item.ticker)
        ? "tsetmc"
        : "nobitex";

  selectSymbol(item.ticker, item.name, finalSource);
  setQuery("");
  setResults([]);
  setShowDropdown(false);
}

// ═══ 🔴 این useEffect کاملاً حذف شود ═══
// دلیل: ناسازگاری source/ticker یک انتخاب معتبر کاربر است. بک‌اند خودش در
// core/sources.py:resolve_symbol_and_source تصمیم درست را می‌گیرد و
// services/analyzer_service.py:84 منبع را به tsetmc اصلاح می‌کند.
// هر خودترمیمی در فرانت = دزدیدن کنترل از کاربر.
```

```typescript
// ─── خط ۱۲۴-۱۳۴ — handleManualSubmit هم همان اصلاح ───
const handleManualSubmit = () => {
  const q = query.trim();
  if (!q) return;
  const isStock = isIranianTicker(q);
  const tk = isStock ? q : q.toUpperCase();
  const finalSource: Source = isStock ? "tsetmc" : source;

  selectSymbol(tk, tk, finalSource);
  setQuery("");
  setResults([]);
  setShowDropdown(false);
};
```

**تست:**
```typescript
test("انتخاب BTC در حالت tsetmc نماد را عوض نمی‌کند", async () => {
  useAppStore.setState({ source: "tsetmc", ticker: "فولاد" });
  render(<SymbolSelector />);

  await userEvent.click(await screen.findByText("بیت‌کوین (USDT)"));

  const s = useAppStore.getState();
  expect(s.ticker).toBe("BTC-USD");
  expect(s.source).toBe("tsetmc");   // کاربر خودش tsetmc را انتخاب کرده بود
  // 🔴 قبل از اصلاح: ticker تبدیل به "فولاد" می‌شد
});
```

---

## 🔴 ۶-۳ [شدت: بالا] [دسته: باگ] — هیچ AbortController نیست → نمایش داده‌ی نماد اشتباه

**فایل‌ها:** `SignalCard.tsx:42-56` و `96-120` · `DeepAnalysis.tsx:41-64` · `TFTable.tsx:66-91` · `FearGreed.tsx:16-27` · `SymbolSelector.tsx:58-85`

```typescript
useEffect(() => {
  if (!ticker) return;
  setLoading(true);
  api.post("/analyze", { ticker, source, ... })   // ← بدون signal
    .then((res) => setData(res.data))
    .catch((err) => { ... });
}, [ticker, tickerName, source, timeframe, marketType, riskProfile]);
```

**مشکل:** کاربر سریع BTC → ETH → SOL کلیک می‌کند. سه درخواست موازی می‌روند. اگر پاسخ BTC **دیرتر** برسد (که می‌رسد — تحلیل BTC اولین بار است و ۸ ثانیه طول می‌کشد)، `setData(res.data)` داده‌ی BTC را روی state فعلی SOL می‌نویسد.

نتیجه: **کارت SOL با قیمت، سیگنال و SL/TP بیت‌کوین.** برای یک دستیار معاملاتی این فاجعه است.

اضافه: بعد از unmount (کاربر تب را عوض می‌کند)، `setData` روی کامپوننت مرده اجرا می‌شود.

**راه‌حل — هوک مشترک:**

```typescript
// ─── frontend/src/hooks/useApiQuery.ts (جدید) ───
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios, { AxiosError, type AxiosRequestConfig } from "axios";
import { api } from "@/lib/api";

interface QueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * درخواست API با محافظت کامل:
 *   - AbortController (لغو درخواست قدیمی → پایان race condition)
 *   - نادیده‌گرفتن پاسخ پس از unmount
 *   - error state واقعی
 */
export function useApiQuery<T>(
  config: AxiosRequestConfig | null,
  deps: unknown[]
): QueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!config) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    const ac = new AbortController();
    setLoading(true);
    setError(null);

    api
      .request<T>({ ...config, signal: ac.signal })
      .then((res) => {
        if (mountedRef.current) setData(res.data);
      })
      .catch((err: AxiosError<{ detail?: string }>) => {
        if (axios.isCancel(err) || err.code === "ERR_CANCELED") return;  // ← لغو، خطا نیست
        if (!mountedRef.current) return;
        setData(null);
        setError(humanError(err));
      })
      .finally(() => {
        if (mountedRef.current) setLoading(false);
      });

    return () => ac.abort();     // ← حیاتی
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const refetch = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, refetch };
}


/**
 * ترجمه‌ی خطای فنی به پیام فارسی برای کاربر مبتدی
 */
export function humanError(err: unknown): string {
  const e = err as AxiosError<{ detail?: string }>;

  if (!e?.response) {
    if (e?.code === "ECONNABORTED") return "سرور دیر جواب داد — دوباره تلاش کن";
    return "اتصال به سرور برقرار نشد — اینترنت و بک‌اند را چک کن";
  }

  const { status, data } = e.response;
  const detail = data?.detail;

  if (typeof detail === "string" && detail.trim()) return detail;

  switch (status) {
    case 404: return "داده‌ای برای این نماد در دسترس نیست";
    case 422: return "تنظیمات نامعتبر است — نماد یا تایم‌فریم را چک کن";
    case 429: return "درخواست‌ها زیاد شد — چند لحظه صبر کن";
    case 500:
    case 502:
    case 503: return "سرور دچار مشکل شد — لطفاً بعداً تلاش کن";
    default:  return `خطای غیرمنتظره (${status})`;
  }
}
```

```typescript
// ─── frontend/src/components/signal/SignalCard.tsx — خط ۹۶-۱۲۰ (اصلاح‌شده) ───
import { useApiQuery } from "@/hooks/useApiQuery";

const { data, loading, error, refetch } = useApiQuery<AnalyzeResponse>(
  ticker
    ? {
        method: "post",
        url: "/analyze",
        data: { ticker, source, timeframe, market_type: marketType,
                risk_profile: riskProfile, ticker_name: tickerName },
      }
    : null,
  [ticker, tickerName, source, timeframe, marketType, riskProfile]
);
```

```typescript
// ─── frontend/src/components/signal/SignalCard.tsx — useLiveQuote (خط ۳۸-۵۹) ───
function useLiveQuote(ticker: string, source: string, enabled: boolean, intervalMs = 5000) {
  const [price, setPrice] = useState<number | null>(null);
  const [change, setChange] = useState(0);

  useEffect(() => {
    if (!enabled || !ticker || intervalMs <= 0) return;

    let cancelled = false;
    let inflight: AbortController | null = null;

    const tick = async () => {
      // ─── تب مخفی = توقف polling (صرفه‌جویی باتری/ترافیک) ───
      if (document.hidden) return;

      inflight?.abort();
      inflight = new AbortController();
      try {
        const res = await api.get("/analyze/quote", {
          params: { ticker, source },
          signal: inflight.signal,
        });
        if (!cancelled) {
          setPrice(res.data.price ?? null);
          setChange(res.data.change_pct ?? 0);
        }
      } catch {
        // ─── quote خراب مهم نیست؛ قیمت قبلی بماند ───
      }
    };

    tick();
    const id = setInterval(tick, intervalMs);
    const onVisible = () => { if (!document.hidden) tick(); };

    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      clearInterval(id);
      inflight?.abort();
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [ticker, source, enabled, intervalMs]);

  return { price, change };
}
```

**تست:**
```typescript
test("پاسخ دیررس نماد قبلی روی نماد جدید نوشته نمی‌شود", async () => {
  const { rerender } = render(<SignalCard />);

  const slowBtc = deferred<any>();
  mockApi.post.mockImplementation((url, body) =>
    body.ticker === "BTC-USD" ? slowBtc.promise : Promise.resolve({ data: ethData })
  );

  useAppStore.setState({ ticker: "BTC-USD" });
  rerender(<SignalCard />);

  useAppStore.setState({ ticker: "ETH-USD" });   // کاربر سریع عوض کرد
  rerender(<SignalCard />);
  await screen.findByText(ethData.name);

  slowBtc.resolve({ data: btcData });            // پاسخ کند BTC می‌رسد
  await new Promise((r) => setTimeout(r, 50));

  expect(screen.getByText(ethData.name)).toBeInTheDocument();
  expect(screen.queryByText(btcData.name)).not.toBeInTheDocument();
});
```

---

## 🔴 ۶-۴ [شدت: بالا] [دسته: باگ] — تنظیم `refreshSeconds` (شامل «خاموش») بی‌اثر است

**فایل:** `frontend/src/store/useAppStore.ts:18,58,80` · `SettingsPanel.tsx:44-49,217-234`

**مشکل (تأیید با grep):** `refreshSeconds` فقط ۴ ارجاع دارد — همه در استور و پنل تنظیمات. **هیچ کامپوننتی آن را نمی‌خواند.** همه‌ی intervalها هاردکد هستند:

| کامپوننت | خط | interval |
|---|---|---|
| `SignalCard.tsx` | ۵۴ | ۵ ثانیه (quote) |
| `PriceComparison.tsx` | ۵۷ | ۱۰ ثانیه |
| `Marquee.tsx` | — | ۶۰ ثانیه |
| `SignalHistory.tsx` | ۱۲۷ | ۳۰ ثانیه |

و **تحلیل سیگنال هیچ‌وقت خودکار refresh نمی‌شود** (فقط با تغییر تنظیمات).

**راه‌حل:**

```typescript
// ─── frontend/src/hooks/usePolling.ts (جدید) ───
"use client";

import { useEffect, useRef } from "react";

/**
 * polling با احترام به «خاموش»:
 *   seconds <= 0  → غیرفعال
 *   تب مخفی      → متوقف
 *   درخواست قبلی → لغو
 */
export function usePolling(
  fn: (signal: AbortSignal) => Promise<void> | void,
  seconds: number,
  deps: unknown[] = []
) {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!seconds || seconds <= 0) return;   // ← «خاموش»

    let inflight: AbortController | null = null;
    const intervalMs = seconds * 1000;

    const tick = async () => {
      if (document.hidden) return;          // ← تب مخفی
      inflight?.abort();
      inflight = new AbortController();
      try {
        await fnRef.current(inflight.signal);
      } catch {
        /* خطا در فراخوانی مدیریت می‌شود */
      }
    };

    tick();
    const id = setInterval(tick, intervalMs);
    const onVisible = () => { if (!document.hidden) tick(); };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      clearInterval(id);
      inflight?.abort();
      document.removeEventListener("visibilitychange", onVisible);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seconds, ...deps]);
}
```

```typescript
// ─── SignalCard.tsx — وصل کردن تنظیم کاربر ───
const refreshSeconds = useAppStore((s) => s.refreshSeconds);

// quote هر ۵ ثانیه (مستقل از تنظیم — سبک است)
const { price: livePrice, change: liveChange } = useLiveQuote(ticker, source, !!ticker, 5000);

// تحلیل با تنظیم کاربر
const { data, loading, error, refetch } = useApiQuery<AnalyzeResponse>(/* ... */);
usePolling(() => { refetch(); }, refreshSeconds, [ticker, source, timeframe]);
```

```typescript
// ─── SettingsPanel.tsx — گزینه‌ی «خاموش» ───
const REFRESH_OPTIONS = [
  { value: 0,   label: "خاموش" },
  { value: 30,  label: "۳۰ ثانیه" },
  { value: 60,  label: "۱ دقیقه" },
  { value: 300, label: "۵ دقیقه" },
];
```

**تست:**
```typescript
test("refreshSeconds=0 هیچ درخواست دوره‌ای نمی‌فرستد", async () => {
  jest.useFakeTimers();
  useAppStore.setState({ refreshSeconds: 0 });
  render(<SignalCard />);

  const after = mockApi.post.mock.calls.length;
  jest.advanceTimersByTime(10 * 60_000);
  await jest.runOnlyPendingTimersAsync();

  expect(mockApi.post.mock.calls.length).toBe(after);
});
```

---

## 🔴 ۶-۵ [شدت: بالا] [دسته: UX] — خطاهای API در production کاملاً بی‌صدا

**فایل:** `frontend/src/lib/api.ts` خط ۱۷-۲۵

```typescript
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (process.env.NODE_ENV === "development") {
      console.error("[API]", err.config?.url, err.message);   // ← در production هیچ!
    }
    return Promise.reject(err);
  }
);
```

**مشکل:** با خاموش بودن بک‌اند:

- `TFTable` → «دیتا نیست» (به‌نظر کاربر: بازار داده ندارد)
- `FearGreed` → کارت ناپدید می‌شود
- `SignalHistory` → `items=[]` → خط ۱۵۰ `return null` → **کل کارت ناپدید**
- `PriceComparison` → فقط `—`
- `Scanner` → «فرصتی با این فیلتر پیدا نشد»

کاربر مبتدی **نمی‌فهمد مشکل فنی است** و فکر می‌کند بازار آرام است.

**راه‌حل:**

```tsx
// ─── frontend/src/components/ui/ErrorState.tsx (جدید) ───
"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center"
    >
      <AlertTriangle className="h-6 w-6 text-destructive" />
      <div>
        <p className="text-sm font-bold text-destructive">ارتباط برقرار نشد</p>
        <p className="mt-1 text-xs text-muted-foreground">{message}</p>
      </div>
      {onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          تلاش مجدد
        </Button>
      )}
    </div>
  );
}
```

```tsx
// ─── SignalCard.tsx — تفکیک Empty از Error ───
if (error) return <ErrorState message={error} onRetry={refetch} />;
if (loading && !data) return <SignalCardSkeleton />;
if (!data) return <EmptyState message="داده‌ای برای این نماد نیست" />;
```

```tsx
// ─── SignalHistory.tsx خط ۱۵۰ (اصلاح) ───
// ❌ قبل: if (!loading && items.length === 0) return null;   ← کارت را قورت می‌دهد
if (error) {
  return (
    <Card>
      <CardContent className="pt-4">
        <ErrorState message={error} onRetry={fetchHistory} />
      </CardContent>
    </Card>
  );
}
```

```typescript
// ─── frontend/src/lib/api.ts (اصلاح‌شده) ───
import axios, { AxiosError, type AxiosResponse } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// ─── در production، fallback بی‌صدا به localhost = شکست خاموش ───
if (!API_URL) {
  if (process.env.NODE_ENV === "production") {
    throw new Error(
      "NEXT_PUBLIC_API_URL تنظیم نشده است. " +
      "در بیلد production این متغیر اجباری است."
    );
  }
  console.warn("[API] NEXT_PUBLIC_API_URL نیست — استفاده از http://localhost:8000");
}

export const api = axios.create({
  baseURL: API_URL || "http://localhost:8000",
  timeout: 60000,          // ← ۳۰s برای اولین تحلیل کم بود
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (res: AxiosResponse) => res,
  (err: AxiosError) => {
    // ─── خطای شبکه/سرور را همیشه لاگ کن (نه فقط dev) ───
    const url = err.config?.url ?? "?";
    if (!err.response) {
      console.error(`[API] شبکه قطع است → ${url}: ${err.message}`);
    } else if (err.response.status >= 500) {
      console.error(`[API] خطای سرور ${err.response.status} → ${url}`);
    }
    return Promise.reject(err);
  }
);
```

**تست:**
```typescript
test("با قطع بک‌اند، پیام «ارتباط برقرار نشد» نمایش داده می‌شود نه «داده‌ای نیست»", async () => {
  mockApi.post.mockRejectedValue({ request: {}, message: "Network Error" });
  render(<SignalCard />);

  expect(await screen.findByRole("alert")).toHaveTextContent("ارتباط برقرار نشد");
  expect(screen.queryByText("داده‌ای نیست")).not.toBeInTheDocument();
});
```

---

## 🟡 ۶-۶ [شدت: متوسط] [دسته: performance] — ۴ درخواست `/analyze` موازی در هر تغییر تنظیم

**فایل‌ها:** `page.tsx:20,45-47` · `SignalCard.tsx:96-120` · `DeepAnalysis.tsx:41-64` (دو درخواست!)

**مشکل:** با هر تغییر نماد/تایم‌فریم:

1. `SignalCard` → `POST /analyze` (با `include_extras=True`)
2. `DeepAnalysis` → `GET /analyze/deep` → **دوباره `analyze_multi_tf` روی ۶ تایم‌فریم**
3. `DeepAnalysis` → `POST /analyze` **دوباره** (فقط برای `ai_export`)
4. `useSignalData` (page) → `POST /analyze`

یعنی همان پاسخ چهار بار تولید می‌شود. چون `/analyze` **خودش** `deep_analysis`، `checklist` و `ai_export` را در پاسخ دارد (`analyzer_service.py:176,189,202`)، درخواست‌های ۲ و ۳ **کاملاً زائد** هستند.

**راه‌حل — Context مشترک:**

```tsx
// ─── frontend/src/context/AnalysisContext.tsx (جدید) ───
"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useAppStore } from "@/store/useAppStore";
import type { AnalyzeResponse } from "@/lib/types";

interface Ctx {
  data: AnalyzeResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

const AnalysisCtx = createContext<Ctx | null>(null);

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const { ticker, tickerName, source, timeframe, marketType, riskProfile } =
    useAppStore();

  const { data, loading, error, refetch } = useApiQuery<AnalyzeResponse>(
    ticker
      ? {
          method: "post",
          url: "/analyze",
          data: {
            ticker, source, timeframe, ticker_name: tickerName,
            market_type: marketType, risk_profile: riskProfile,
          },
        }
      : null,
    [ticker, tickerName, source, timeframe, marketType, riskProfile]
  );

  return (
    <AnalysisCtx.Provider value={{ data, loading, error, refetch }}>
      {children}
    </AnalysisCtx.Provider>
  );
}

export function useAnalysis() {
  const ctx = useContext(AnalysisCtx);
  if (!ctx) throw new Error("useAnalysis باید داخل AnalysisProvider باشد");
  return ctx;
}
```

```tsx
// ─── DeepAnalysis.tsx — حذف دو fetch، استفاده از context ───
export function DeepAnalysis() {
  const { data, loading } = useAnalysis();

  // ✅ deep_analysis و ai_export از همان پاسخ /analyze می‌آیند
  const text = data?.deep_analysis ?? "";
  const aiExport = data?.ai_export ?? "";

  // ❌ حذف کامل: useEffect با GET /analyze/deep
  // ❌ حذف کامل: useEffect با POST /analyze
}
```

```tsx
// ─── app/page.tsx — wrap کردن ───
<AnalysisProvider>
  <SignalCard />
  <DeepAnalysis />
  <TFTable />
  <Checklist />
</AnalysisProvider>
```

**تست:**
```typescript
test("تغییر نماد فقط یک درخواست /analyze می‌فرستد", async () => {
  render(
    <AnalysisProvider>
      <SignalCard /><DeepAnalysis />
    </AnalysisProvider>
  );
  useAppStore.setState({ ticker: "ETH-USD" });
  await waitFor(() => expect(mockApi.post).toHaveBeenCalled());
  await new Promise((r) => setTimeout(r, 100));

  const analyzeCalls = mockApi.post.mock.calls.filter(([u]) => u === "/analyze");
  expect(analyzeCalls).toHaveLength(1);     // قبل از اصلاح: ۳
});
```

---

## 🟡 ۶-۷ [شدت: متوسط] [دسته: امنیت/UX] — کلید DeepSeek در localStorage و درخواست مستقیم از مرورگر

**فایل:** `frontend/src/components/signal/DeepAnalysis.tsx` خط ۳۶، ۷۸، ۹۲-۱۳۴

```typescript
const saved = localStorage.getItem("deepseek_api_key") || "";   // ← خط ۳۶

const res = await fetch("https://api.deepseek.com/chat/completions", {
  headers: { Authorization: `Bearer ${key}` },                   // ← کلید در مرورگر
  ...
});
localStorage.setItem("deepseek_api_key", apiKey);               // ← خط ۱۳۴
```

**مشکل:**
- **کلید API در localStorage** → هر XSS (یا هر dependency آلوده) آن را می‌دزدد
- کلید در DevTools قابل دیدن است
- درخواست مستقیم مرورگر به `api.deepseek.com` → وابسته به CORS آن‌ها
- **هیچ راهی برای پاک کردن کلید نیست**
- خطای 401 خام (`HTTP 401`) به کاربر فارسی نشان داده می‌شود

**راه‌حل — کوتاه‌مدت:**

```tsx
// ─── DeepAnalysis.tsx (اصلاح امنیتی حداقلی) ───
const KEY_STORAGE = "deepseek_api_key";

const handleClearKey = () => {
  localStorage.removeItem(KEY_STORAGE);
  sessionStorage.removeItem(KEY_STORAGE);
  setApiKey("");
  setShowKeyInput(true);
  setAiError("");
};

const handleSaveKey = () => {
  const k = apiKey.trim();
  if (!k.startsWith("sk-")) {
    setAiError("کلید باید با sk- شروع شود");
    return;
  }
  localStorage.setItem(KEY_STORAGE, k);
  setShowKeyInput(false);
  setAiError("");
  setApiKey(k);
};

// ─── پیام خطای انسانی ───
} catch (e) {
  const msg = (e as Error)?.message ?? "";
  if (msg.includes("401")) {
    setAiError("کلید DeepSeek نامعتبر است — کلید را دوباره وارد کن");
  } else if (msg.includes("402") || msg.includes("insufficient")) {
    setAiError("اعتبار حساب DeepSeek تمام شده است");
  } else if (msg.includes("429")) {
    setAiError("درخواست‌ها زیاد شد — چند لحظه صبر کن");
  } else {
    setAiError(msg || "خطا در ارتباط با AI");
  }
}
```

```tsx
{/* ─── دکمه‌ی پاک کردن کلید ─── */}
<Button size="sm" variant="ghost" onClick={handleClearKey} className="text-destructive">
  <Trash2 className="h-3.5 w-3.5" />
  پاک کردن کلید
</Button>

{/* ─── هشدار به کاربر ─── */}
<p className="text-[10px] text-muted-foreground">
  ⚠️ کلید در همین مرورگر ذخیره می‌شود. فقط روی دستگاه شخصی خودت استفاده کن.
</p>
```

**راه‌حل — بلندمدت (توصیه‌ی جدی):** پروکسی سمت سرور:

```python
# ─── api/routers/ai.py (جدید) ───
"""
پروکسی DeepSeek — کلید هرگز به مرورگر نمی‌رسد.
"""
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request

from api.deps import client_ip, rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


@router.post("/analyze")
async def ai_analyze(payload: dict, request: Request):
    rate_limit(f"ai:{await client_ip(request)}", limit=10, window_sec=3600)

    # ─── کلید از سرور، نه از کلاینت ───
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        raise HTTPException(503, detail="سرویس AI روی سرور تنظیم نشده است")

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json=payload,
        )

    if r.status_code == 401:
        raise HTTPException(502, detail="کلید DeepSeek سرور نامعتبر است")
    if r.status_code == 429:
        raise HTTPException(429, detail="سرویس AI شلوغ است — بعداً تلاش کن")
    if r.status_code != 200:
        logger.error(f"[AI] DeepSeek {r.status_code}: {r.text[:200]}")
        raise HTTPException(502, detail="سرویس AI پاسخ نداد")

    return r.json()
```

---

## 🟡 ۶-۸ [شدت: متوسط] [دسته: performance] — `BacktestStats` حلقه‌ی fetch بی‌پایان

**فایل:** `frontend/src/components/backtest/BacktestStats.tsx` خط ۲۹-۴۶

```typescript
useEffect(() => {
  api.get("/backtest/history", { params: { limit: 500 } })
    .then((res) => { setTrapStats(computeTrapStats(res.data.items)); });
  // وابستگی به data که خودش ست می‌کند
}, [data]);
```

**مشکل:** افکت به `data` وابسته است و `data` را خودش ست می‌کند → **حلقه‌ی fetch**. هر بار ۵۰۰ ردیف. و در دو مسیر `return` بدون `setTrapStats(null)`، عدد قدیمی روی صفحه می‌ماند.

**راه‌حل:**

```typescript
// ─── BacktestStats.tsx (اصلاح‌شده) ───
const { data, loading, error, refetch } = useApiQuery<HistoryResponse>(
  { method: "get", url: "/backtest/history", params: { limit: 500 } },
  []                                       // ← وابستگی خالی: یک‌بار
);

const trapStats = useMemo(
  () => (data?.items ? computeTrapStats(data.items) : null),
  [data]
);

if (error) return <ErrorState message={error} onRetry={refetch} />;
if (!trapStats) return null;
```

**تست:**
```typescript
test("BacktestStats بر اثر تغییر state خودش دوباره fetch نمی‌کند", async () => {
  render(<BacktestStats />);
  await waitFor(() => expect(mockApi.get).toHaveBeenCalledTimes(1));
  await new Promise((r) => setTimeout(r, 300));
  expect(mockApi.get).toHaveBeenCalledTimes(1);     // قبل از اصلاح: > 1
});
```

---

## 🟡 ۶-۹ [شدت: متوسط] [دسته: UX] — تایم‌اوت نمایشی سیگنال‌ها غلط + `parseUtc`

**فایل:** `SignalHistory.tsx` خط ۶۰-۸۷

```typescript
function timeLeftMin(iso: string, tf: string, result: string | null): number {
  if (result) return -1;
  try {
    const start = new Date(iso).getTime();        // ← "2026-02-14T10:00:00" → 06:30Z
    ...
    return Math.floor(diff / 60000);
  } catch {
    return -1;                                     // ← new Date("bogus") استثنا نمی‌دهد!
  }
}
```

**مشکل دوتایی:**
1. بک‌اند `isoformat()` بدون `Z` می‌دهد (چون `datetime.utcnow()` naive است) → `new Date()` آن را **به وقت محلی کاربر** پارس می‌کند → شمارش معکوس ۳:۳۰ ساعت غلط
2. `new Date("bogus").getTime()` مقدار `NaN` می‌دهد، **استثنا نمی‌دهد** → `try/catch` بی‌اثر است → `NaN` به `formatTimeLeft` می‌رسد

**راه‌حل:** (کامل در بخش ۳-۲ — `frontend/src/lib/date.ts`) — همان `parseUtc` با `Number.isFinite` guard.

**تست:**
```typescript
test("timestamp بدون Z به‌عنوان UTC پارس می‌شود", () => {
  const d = parseUtc("2026-01-01T00:00:00");
  expect(d?.toISOString()).toBe("2026-01-01T00:00:00.000Z");
});

test("timestamp نامعتبر → null، نه NaN", () => {
  expect(parseUtc("bogus")).toBeNull();
  expect(timeLeftMin("bogus", "۵ دقیقه", null)).toBe(-1);
});
```

---

## 🟡 ۶-۱۰ [شدت: متوسط] [دسته: باگ] — `Scanner` پروفایل ریسک کاربر را نادیده می‌گیرد

**فایل:** `frontend/src/components/scan/Scanner.tsx` خط ۴۸-۷۴

```typescript
api.post("/scan", {
  category,
  timeframe,
  market_type: marketType,
  risk_profile: "aggressive",     // ← 🔴 هاردکد — انتخاب کاربر نادیده
  limit: 15,
})
```

**مشکل:** تنظیم `riskProfile` کاربر دور ریخته می‌شود. اضافه: useState اولیه به `globalSource` وابسته است ولی همگام نمی‌شود. و `onClick` با `setTimeout 50ms` (خط ۲۴۴) یک hack برای ترتیب state است.

**راه‌حل:**

```typescript
// ─── Scanner.tsx (اصلاح‌شده) ───
export function Scanner() {
  const source = useAppStore((s) => s.source);
  const setSource = useAppStore((s) => s.setSource);
  const timeframe = useAppStore((s) => s.timeframe);
  const riskProfile = useAppStore((s) => s.riskProfile);   // ← وصل شد
  const addToWatchlist = useAppStore((s) => s.addToWatchlist);

  const [scanSource, setScanSource] = useState<Source>(source);

  // ─── همگام‌سازی با store ───
  useEffect(() => { setScanSource(source); }, [source]);

  const handleScan = () => {
    setLoading(true);
    setScannedTf(timeframe);
    setError(null);
    api.post("/scan", {
      category: CATEGORIES_BY_SOURCE[scanSource] ?? "crypto",
      timeframe,
      market_type: scanSource === "tsetmc" ? "spot" : "futures",
      risk_profile: riskProfile,           // ✅
      limit: 15,
    })
      .then((res) => setData(res.data))
      .catch((err) => { setData(null); setError(humanError(err)); })
      .finally(() => setLoading(false));
  };

  // ─── یک اکشن اتمیک، نه دو setState + setTimeout ───
  const handleSelectFromScan = (item: ScanItem) => {
    useAppStore.getState().selectSymbol(item.ticker, item.name, scanSource);
  };
```

**تست:**
```typescript
test("اسکنر پروفایل ریسک کاربر را می‌فرستد", async () => {
  useAppStore.setState({ riskProfile: "conservative" });
  render(<Scanner />);
  await userEvent.click(screen.getByText(/بررسی فرصت/));

  expect(mockApi.post).toHaveBeenCalledWith(
    "/scan",
    expect.objectContaining({ risk_profile: "conservative" })
  );
});
```

---

## 🟢 ۶-۱۱ [شدت: پایین] [دسته: UX] — Marquee: محاسبه‌ی زمان بازار غلط

**فایل:** `frontend/src/components/layout/Marquee.tsx` خط ۱۴-۲۸، ۵۷-۷۹

**مشکل:**
- آفست ثابت `+3:30` — ساعت‌های لندن/نیویورک/توکیو **به وقت محلی خودشان** نوشته شده‌اند و با وقت تهران مقایسه می‌شوند → «لندن تا ۲۰:۰۰» در واقع ۲۰:۰۰ تهران است
- `isIranWorkday` با `getUTCDay()` و لیست هاردکد تعطیلات رسمی ایران را نمی‌داند → «باز» نشان می‌دهد وقتی بازار تعطیل است

**راه‌حل:**

```typescript
// ─── frontend/src/lib/marketHours.ts (جدید) ───
/**
 * ساعات بازار با Intl API — بدون آفست دستی، DST خودکار.
 */
type Session = { open: [number, number]; close: [number, number] };

const SESSIONS: Record<string, { tz: string; session: Session; label: string }> = {
  tehran:  { tz: "Asia/Tehran",      session: { open: [9, 0],  close: [12, 30] }, label: "بورس تهران" },
  london:  { tz: "Europe/London",    session: { open: [8, 0],  close: [16, 30] }, label: "لندن" },
  newyork: { tz: "America/New_York", session: { open: [9, 30], close: [16, 0] },  label: "نیویورک" },
  tokyo:   { tz: "Asia/Tokyo",       session: { open: [9, 0],  close: [15, 0] },  label: "توکیو" },
};

function partsInTz(tz: string, now = new Date()) {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: tz, hour: "2-digit", minute: "2-digit",
    weekday: "short", hour12: false,
  });
  const parts = Object.fromEntries(
    fmt.formatToParts(now).map((p) => [p.type, p.value])
  );
  return {
    hour: Number(parts.hour),
    minute: Number(parts.minute),
    weekday: parts.weekday,
  };
}

export function marketState(key: keyof typeof SESSIONS, now = new Date()) {
  const { tz, session, label } = SESSIONS[key];
  const { hour, minute, weekday } = partsInTz(tz, now);

  const isWeekend = weekday === "Sat" || weekday === "Sun";
  const mins = hour * 60 + minute;
  const open = session.open[0] * 60 + session.open[1];
  const close = session.close[0] * 60 + session.close[1];

  const isOpen = !isWeekend && mins >= open && mins < close;
  return {
    isOpen,
    label,
    localTime: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`,
  };
}
```

---

## 🟢 ۶-۱۲ [شدت: پایین] [دسته: UX/دسترس‌پذیری]

**فایل‌ها و مشکلات:**

| فایل:خط | مشکل | راه‌حل |
|---|---|---|
| `SignalCard.tsx:234` | `displayChange !== 0` → تغییر صفر اصلاً نشان داده نمی‌شود | آستانه‌ی `< 0.005` را چاپ کن |
| `SymbolSelector.tsx:246` | `opacity-0 group-hover:opacity-100` → **روی موبایل واچ‌لیست غیرقابل‌استفاده** | `opacity-100 sm:opacity-0 sm:group-hover:opacity-100` |
| `SymbolSelector.tsx:177-191` | دکمه‌ی ستاره بدون `aria-label`/`aria-pressed` | `aria-label` + `aria-pressed={inWatchlist}` |
| `Footer.tsx:12` | `setTimeout` بدون cleanup | `const id = setTimeout(...); return () => clearTimeout(id)` |
| `Footer.tsx:10` | `localStorage.getItem` بدون try/catch → در private mode کل افکت می‌شکند | wrap در try/catch |
| `Footer.tsx:28-72` | مودال دیسکلیمر بدون `role="dialog"`/focus trap/Esc + کلیک پس‌زمینه = پذیرش | `role="dialog"` + `aria-modal` + Esc |
| `Header.tsx:32-36` | `<img>` بدون `width`/`height` → CLS | اضافه کردن ابعاد |
| `Header.tsx:46-56` | بج سبز «زنده» هاردکد، حتی وقتی بک‌اند خواب است | `GET /health` + رنگ واقعی |
| `Header.tsx:4` | import بی‌استفاده `Zap` | حذف |
| `TFTable.tsx:81` | `console.log` در production | حذف یا gate با NODE_ENV |
| همه‌جا | `%85` (عدد لاتین + ٪ فارسی) | helper `formatFaNumber` |
| `Marquee.tsx:143-145` | سه کپی DOM، بدون `prefers-reduced-motion` | `motion-reduce:animate-none` |
| `package.json` | وابستگی‌های بدون مصرف: `cn`, `next-pwa`, `framer-motion`, `recharts`, `lightweight-charts`, `date-fns-jalali`, `@base-ui/react` | حذف |
| `tsconfig.json` | `noUnusedLocals` ندارد → tsc این‌ها را نمی‌گیرد | `"noUnusedLocals": true, "noUnusedParameters": true` |
| `BacktestStats.tsx:86-97` | `URL.createObjectURL` بدون `revokeObjectURL` → نشت حافظه | `finally { URL.revokeObjectURL(url) }` |
| `BacktestStats.tsx:74,83` | `catch {}` خالی | حداقل `console.error` + پیام به کاربر |

**تست:**
```bash
cd frontend
npx tsc --noEmit                                  # با noUnusedLocals
npx eslint src --max-warnings 0
npx @axe-core/cli http://localhost:3000 --exit    # دسترس‌پذیری
```

---

# ۷. Logic Bugs

## 🟡 ۷-۱ [شدت: متوسط] [دسته: logic] — `TF_ATR_MULT` روی SL و TP **هر دو** ضرب می‌شود

**فایل:** `core/contracts.py` خط ۲۵۸-۲۷۰ · `core/analyzer.py` خط ۱۶۶۱-۱۶۹۱

```python
TF_ATR_MULT = {
    "۱ دقیقه": 1.8, "۵ دقیقه": 1.5, "۱۵ دقیقه": 1.3,
    "۳۰ دقیقه": 1.3, "۱ ساعت": 1.4, "روزانه": 1.8,
}
```

```python
tf_mult = get_tf_atr_mult(tf_name)
effective_sl_mult = profile["sl_mult"] * tf_mult
effective_tp_mult = profile["tp_mult"] * tf_mult      # ← همان ضریب
```

**تحلیل اقتصادی:**

- **R:R تغییر نمی‌کند:** `rr = (atr·tp_mult·k) / (atr·sl_mult·k) = tp_mult/sl_mult`. یعنی تمام کار «tf-محور کردن» فقط **فاصله مطلق** SL/TP را بزرگ می‌کند، نه نسبت را. دلیل ذکرشده در کامنت خط ۲۵۷ («SL/TP تنگ باعث باخت می‌شد») فقط وقتی درست است که با **اسلیپیج/کارمزد ثابت** کار کنید.
- **ریسک هر معامله ۲ تا ۴ برابر شد:** برای `aggressive_spot` (`sl_mult=1.2`) در «۱ دقیقه»: `1.2 × 1.8 = 2.16× ATR` — در مقابل ۱.۲× قبل. با مدیریت حجم ثابت، **drawdown هر ترید دو برابر** شد. اگر کاربر ۲٪ سرمایه‌اش را ریسک می‌کرد، الان باید ۱٪ بگذارد — ولی `RISK_PROFILES` هیچ‌جا مشاوره‌ی حجم را با ضریب جدید هماهنگ نکرده (خط ۳۲: «۲-۳٪ سرمایه» متن ثابت است).
- **مقادیر غیریکنوا:** `۱ دقیقه=1.8`، `۱۵ دقیقه=1.3`، `۳۰ دقیقه=1.3`، `۱ ساعت=1.4`، `روزانه=1.8` — یک V شکل است، نه یک رابطه‌ی یکنوا با TF. معنای اقتصادی روشنی ندارد.
- **`روزانه` و `۱ دقیقه` هم‌ضریب شدند** (هر دو ۱.۸) در حالی که ATR روزانه BTC می‌تواند ۳٪ قیمت باشد → SL روزانه = ۵.۴٪.

**راه‌حل — یکنوا + سقف ریسک:**

```python
# ─── core/contracts.py (اصلاح‌شده) ───
"""
ضریب ATR بر اساس TF.

اصلاح اقتصادی:
  1. TF کوچک نویز بیشتری دارد → ضریب بزرگ‌تر برای **هر دو** SL و TP
     (این درست بود) ولی باید **سقف ریسک** داشته باشد.
  2. باید یکنوا باشد: هر چه TF بزرگ‌تر، ضریب بزرگ‌تر
     (چون نوسان در واحد زمان جمع می‌شود ~ √t).
  3. باید با درصد سرمایه گره بخورد، نه فقط ATR.
"""

import math

_TF_MINUTES = {
    "۱ دقیقه": 1, "۵ دقیقه": 5, "۱۵ دقیقه": 15,
    "۳۰ دقیقه": 30, "۱ ساعت": 60, "روزانه": 1440,
}
_BASE_MINUTES = 5
_BASE_MULT = 1.5          # ضریب پایه برای ۵ دقیقه


def get_tf_atr_mult(tf_name: str) -> float:
    """
    ضریب ATR یکنوا بر اساس √(TF/5min) با سقف.

    rationale: نوسان با √t رشد می‌کند (random walk)؛
    ضریب بزرگ‌تر از آن = SL غیرضروری گشاد.
    """
    m = _TF_MINUTES.get(tf_name)
    if not m:
        return 1.0
    raw = _BASE_MULT * math.sqrt(m / _BASE_MINUTES)
    # ─── سقف ۳.۰: بالاتر از آن، SL یعنی رها کردن پوزیشن ───
    return round(min(raw, 3.0), 2)

# نتیجه:
#   ۱ دقیقه  → 1.5 × √(1/5)  = 0.67
#   ۵ دقیقه  → 1.50
#   ۱۵ دقیقه → 1.50 × √3     = 2.60
#   ۳۰ دقیقه → 1.50 × √6     = 3.00 (سقف)
#   ۱ ساعت   → 3.00 (سقف)
#   روزانه   → 3.00 (سقف)
```

```python
# ─── core/analyzer.py خط ۳۱-۶۵ — افزودن سقف ریسک به پروفایل‌ها ───
RISK_PROFILES = {
    "aggressive_spot": {
        "name": "جسور (اسپات)",
        "sl_mult": 1.2, "tp_mult": 2.5,
        "min_confidence": 30,
        "max_risk_pct": 2.0,        # ← حداکثر فاصله SL به درصد
        "capital_risk_pct": 2.0,    # ← چند درصد سرمایه ریسک شود
        "advice": "خرید در اسپات. حداکثر ۲٪ سرمایه ریسک کن.",
        "allow_short": False, "leverage": None,
    },
    "aggressive_futures": {
        "name": "جسور (فیوچرز)",
        "sl_mult": 1.5, "tp_mult": 3.0,
        "min_confidence": 40,
        "max_risk_pct": 1.5,
        "capital_risk_pct": 1.0,
        "advice": "فیوچرز با اهرم ۲-۳x. حداکثر ۱٪ سرمایه ریسک کن.",
        "allow_short": True, "leverage": 3,
    },
    # ...
}
```

```python
# ─── core/analyzer.py خط ۱۶۶۱-۱۶۹۱ (اصلاح‌شده) ───
        if atr > 0 and is_directional:
            tf_mult = get_tf_atr_mult(tf_name)
            sl_mult = profile["sl_mult"] * tf_mult
            tp_mult = profile["tp_mult"] * tf_mult

            # ─── سقف ریسک: SL بیشتر از max_risk_pct نباشد ───
            max_risk_pct = profile.get("max_risk_pct", 2.0)
            if price > 0 and (atr * sl_mult) / price * 100 > max_risk_pct:
                allowed_atr = price * max_risk_pct / 100
                sl_mult = allowed_atr / atr
                # ─── R:R را حفظ کن ───
                tp_mult = sl_mult * (profile["tp_mult"] / profile["sl_mult"])
                logger.info(
                    f"[Analyzer] SL به سقف ریسک {max_risk_pct}% محدود شد "
                    f"(قبل: {profile['sl_mult'] * tf_mult:.2f}× ATR)"
                )

            if SigEnum.is_long(signal):
                sl = price - atr * sl_mult
                tp = price + atr * tp_mult
                sl_tp = {
                    "sl": sl, "tp": tp, "type": "LONG",
                    "tf_mult": tf_mult,
                    "effective_sl_mult": sl_mult,
                    "effective_tp_mult": tp_mult,
                    "sl_pct": abs(price - sl) / price * 100,
                    "capital_risk_pct": profile.get("capital_risk_pct", 1.0),
                }
                rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else None
```

**تست:**
```python
# tests/test_tf_atr_mult.py
from core.contracts import get_tf_atr_mult, TF_NAMES

def test_tf_mult_is_monotonic():
    """ضریب باید با TF بزرگ‌تر زیاد شود (یکنوا)"""
    order = ["۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"]
    vals = [get_tf_atr_mult(tf) for tf in order]
    assert vals == sorted(vals), f"غیریکنوا: {dict(zip(order, vals))}"

def test_tf_mult_capped():
    for tf in TF_NAMES:
        assert get_tf_atr_mult(tf) <= 3.0

def test_sl_respects_max_risk_pct():
    """ATR بزرگ → SL نباید از سقف رد شود"""
    from core.analyzer import analyze_symbol, RISK_PROFILES
    res = analyze_symbol(_df_atr_pct(5.0), risk_profile="aggressive",
                         market_type="spot", tf_name="۱ دقیقه", ticker="BTC-USD")
    if res["sl_tp"]:
        pct = abs(res["price"] - res["sl_tp"]["sl"]) / res["price"] * 100
        assert pct <= RISK_PROFILES["aggressive_spot"]["max_risk_pct"] + 0.01
```

---

## 🟡 ۷-۲ [شدت: متوسط] [دسته: logic] — حجم در نبود داده «خنثی» نیست و RSI یک‌طرفه رأی می‌دهد

### الف) `vol_ratio` گمراه‌کننده

**فایل:** `core/analyzer.py` خط ۸۱۹-۸۲۶ · ۹۶۳ · ۹۸۵-۹۹۳

```python
"details": {
    "vol_ratio": (vol / vol_ma) if vol_ma > 0 else 0,   # ← صفر وقتی حجم نیست
}

# و در _detect_traps:
vol_ratio = v_details.get("vol_ratio", 1.0)
if adx > 35 and vol_ratio < 0.6 and abs(s_score) > 0.30:
    traps["fake_breakout"] = ... "حجم فقط 0.0x میانگین"  # ← پیام غیرواقعی
```

**مشکل:** وقتی volume وجود ندارد، `vol_ratio = 0` ذخیره می‌شود. در `_detect_traps` شرط `< 0.6` برقرار است → **«شکست جعلی» کاذب** با پیام «حجم فقط 0.0x میانگین». کاربر هشدار تله می‌گیرد که پایه‌ی داده‌ای ندارد.

**راه‌حل:**

```python
# ─── core/analyzer.py خط ۸۱۹-۸۲۶ ───
    vol_ratio = None
    if vol_ma > 0 and vol > 0:
        vol_ratio = vol / vol_ma

    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "obv": obv_last,
            "vol_ratio": vol_ratio,          # ← None یعنی «نامعلوم»
            "has_volume": has_volume,
            "cmf": cmf, "mfi": mfi,
            "cvd": safe_num(last.get("cvd")),
            "delta": safe_num(last.get("delta")),
        },
        "weight": 1.0,
    }
```

```python
# ─── core/analyzer.py خط ۹۶۳ (اصلاح‌شده) ───
    vol_ratio = v_details.get("vol_ratio")
    has_volume = v_details.get("has_volume", False)

    # ... و در شرط:
    if (
        adx > 35
        and has_volume                        # ← بدون داده، تشخیص تله نده
        and vol_ratio is not None
        and vol_ratio < 0.6
        and abs(s_score) > 0.30
    ):
```

### ب) RSI در روند، سیگنال معکوس می‌دهد

**فایل:** `core/analyzer.py` خط ۴۰۷-۴۱۸

```python
if rsi < 30:    signals.append((+1.0, 1.2))    # ← خرید
elif rsi > 70:  signals.append((-1.0, 1.2))    # ← فروش
```

**مشکل اقتصادی:** RSI یک اندیکاتور **mean-reversion** است. در روند قوی (که `classify_regime` هم تشخیص می‌دهد: `adx >= 25`)، RSI می‌تواند **هفته‌ها** بالای ۷۰ بماند. سیستم در هر کندل `-1.0` با وزن ۱.۲ (بالاترین وزن گروه مومنتوم) رأی نزولی می‌دهد — یعنی در یک روند صعودی قوی، مداوم SHORT پیشنهاد می‌کند.

این با `_regime_weights` هم تشدید می‌شود: در `trend` وزن momentum = ۱.۲.

**راه‌حل:**

```python
# ─── core/analyzer.py خط ۴۰۶-۴۲۰ (اصلاح‌شده) ───
    rsi = safe_num(last.get("rsi"), 50)

    # ─── RSI باید رژیم‌آگاه باشد ───
    # در روند: RSI بالا = قدرت روند (تأییدی)، نه اشباع
    # در رنج: RSI بالا = اشباع (بازگشتی)
    adx_now = safe_num(last.get("adx"), 20)
    trend_mode = adx_now >= 25

    if trend_mode:
        ema200 = safe_num(last.get("ema200"))
        up_trend = price > ema200 if ema200 > 0 else True

        if rsi > 60 and up_trend:
            signals.append((+0.6, 1.0))
            reasons.append(f"RSI={rsi:.0f} قوت روند صعودی (ADX={adx_now:.0f})")
        elif rsi < 40 and not up_trend:
            signals.append((-0.6, 1.0))
            reasons.append(f"RSI={rsi:.0f} قوت روند نزولی (ADX={adx_now:.0f})")
        elif rsi > 80:
            signals.append((-0.3, 0.6))
            reasons.append(f"RSI={rsi:.0f} اشباع خرید در روند — احتیاط")
        elif rsi < 20:
            signals.append((+0.3, 0.6))
            reasons.append(f"RSI={rsi:.0f} اشباع فروش در روند — احتیاط")
        else:
            signals.append((0.0, 0.5))
    else:
        # ─── رژیم رنج: رفتار بازگشتی (منطق قبلی) ───
        if rsi < 30:
            signals.append((+1.0, 1.2))
            reasons.append(f"RSI={rsi:.0f} اشباع فروش")
        elif rsi > 70:
            signals.append((-1.0, 1.2))
            reasons.append(f"RSI={rsi:.0f} اشباع خرید")
        elif rsi < 40:
            signals.append((+0.4, 0.8))
            reasons.append(f"RSI={rsi:.0f} نزدیک اشباع فروش")
        elif rsi > 60:
            signals.append((-0.4, 0.8))
            reasons.append(f"RSI={rsi:.0f} نزدیک اشباع خرید")
        else:
            signals.append((0.0, 0.5))
```

**تست:**
```python
# tests/test_rsi_regime_aware.py
def test_rsi_does_not_short_a_strong_uptrend():
    """
    ADX=40 (روند قوی) + RSI=75 + قیمت بالای EMA200
    → گروه مومنتوم نباید رأی نزولی بدهد
    """
    df = build_uptrend_df(adx=40, rsi=75)
    res = analyzer._analyze_momentum(df, _thresholds=(0.25, 0.30, 0.30))
    assert res["vote"] >= 0, f"در روند صعودی رأی نزولی داد: {res['reasons']}"


def test_rsi_still_mean_reverts_in_range():
    """ADX=15 (رنج) + RSI=75 → باید نزولی رأی بدهد"""
    df = build_range_df(adx=15, rsi=75)
    res = analyzer._analyze_momentum(df, _thresholds=(0.25, 0.30, 0.30))
    assert res["vote"] <= 0
```

---

## 🔴 ۷-۳ [شدت: بالا] [دسته: باگ] — `< 50 کندل` ورودی را می‌پذیرد و EMA200 بی‌اعتبار می‌شود

**فایل:** `core/analyzer.py` خط ۱۴۷-۱۴۸، ۱۴۹۱-۱۴۹۴، ۱۷۰ · `services/data_service.py` خط ۲۴-۳۱

```python
def compute_indicators(df):
    if df is None or df.empty or len(df) < 50:
        return df                    # ← بی‌صدا برمی‌گردد
```

```python
n_candles = len(df)
if n_candles < 50:
    return None                      # ← فقط ۵۰ کندل لازم می‌داند
```

اما `ema200 = ta.ema(df["close"], length=200)` **۲۰۰ کندل** لازم دارد.

**مشکل:** با ۵۰ تا ۱۹۹ کندل:

| منبع | تعداد کندل | EMA200 |
|---|---|---|
| `wallex` روزانه | `days=90` → ۹۰ | ❌ **EMA200 = NaN** |
| `tsetmc` | `days=200` → ۲۰۰ | ⚠️ فقط ۱ نقطه معتبر |
| `bitpin` «۵ دقیقه» با TF اشتباه | ۸۶۴ | ✅ |

با `ema200 = NaN`: `safe_num(last.get("ema200"))` → `0.0` → شرط `if ema200 > 0` در `_analyze_trend` خط ۵۰۷ **False** → **کل وزن ۱.۲ سیگنال EMA200 حذف می‌شود** بی‌صدا.

**راه‌حل:**

```python
# ─── core/analyzer.py خط ۱۴۶-۱۴۸ (اصلاح‌شده) ───
MIN_CANDLES = 60            # حداقل مطلق
PREFERRED_CANDLES = 250     # برای EMA200 معتبر

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if len(df) < MIN_CANDLES:
        logger.warning(
            f"[Analyzer] فقط {len(df)} کندل — حداقل {MIN_CANDLES} لازم است"
        )
        return df
    # ... ادامه
```

```python
# ─── core/analyzer.py خط ۱۴۹۱-۱۴۹۴ (اصلاح‌شده) ───
    n_candles = len(df)
    if n_candles < MIN_CANDLES:
        logger.info(f"[Analyzer] کندل کافی نیست: {n_candles} < {MIN_CANDLES}")
        return None

    # ─── هشدار صریح برای EMA200 ───
    degraded: list[str] = []
    if n_candles < PREFERRED_CANDLES:
        degraded.append("ema200")
        logger.info(
            f"[Analyzer] {n_candles} کندل < {PREFERRED_CANDLES} — "
            f"EMA200 و Ichimoku کامل نیستند"
        )
```

```python
# ─── core/analyzer.py — در خروجی analyze_symbol ───
        return {
            ...
            "degraded_indicators": degraded,     # ← فرانت باید نشان دهد
            "candles_used": n_candles,
            ...
        }
```

```python
# ─── services/data_service.py خط ۲۴-۳۱ (اصلاح‌شده) ───
# ─── period ها را بزرگ‌تر کن تا EMA200 معتبر باشد ───
TF_MAP = {
    "۱ دقیقه": ("1m", "2d"),      # بود: 1d
    "۵ دقیقه": ("5m", "10d"),     # بود: 5d
    "۱۵ دقیقه": ("15m", "20d"),   # بود: 5d
    "۳۰ دقیقه": ("30m", "1mo"),
    "۱ ساعت": ("1h", "6mo"),      # بود: 3mo
    "روزانه": ("1d", "2y"),       # بود: 6mo → ۵۰۰ کندل، EMA200 معتبر
}
```

```python
# ─── core/wallex_fetcher.py و core/bitpin_fetcher.py — PERIOD_MAP ───
PERIOD_MAP = {
    "۱ دقیقه": 2, "۵ دقیقه": 10, "۱۵ دقیقه": 20,
    "۳۰ دقیقه": 30, "۱ ساعت": 180, "روزانه": 730,   # ← ۲ سال
}
```

**تست:**
```python
# tests/test_min_candles.py
from core.analyzer import analyze_symbol, MIN_CANDLES, PREFERRED_CANDLES

def test_insufficient_candles_rejected():
    assert analyze_symbol(_df(MIN_CANDLES - 1), ticker="BTC-USD") is None

def test_degraded_flag_when_ema200_unavailable():
    res = analyze_symbol(_df(100), ticker="BTC-USD", tf_name="۵ دقیقه")
    assert "ema200" in res["degraded_indicators"]
    assert res["candles_used"] == 100

def test_no_degraded_flag_with_enough_candles():
    res = analyze_symbol(_df(PREFERRED_CANDLES + 50), ticker="BTC-USD", tf_name="۵ دقیقه")
    assert res["degraded_indicators"] == []

def test_fetcher_periods_cover_ema200():
    """هر TF باید حداقل PREFERRED_CANDLES کندل بدهد"""
    from services.data_service import TF_MAP
    minutes_per_candle = {"۱ دقیقه": 1, "۵ دقیقه": 5, "۱۵ دقیقه": 15,
                          "۳۰ دقیقه": 30, "۱ ساعت": 60, "روزانه": 1440}
    days = {"1d": 1, "2d": 2, "5d": 5, "10d": 10, "20d": 20,
            "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730}
    for tf, (_, period) in TF_MAP.items():
        n = days[period] * 1440 / minutes_per_candle[tf]
        assert n >= PREFERRED_CANDLES, f"{tf}: only {n:.0f} candles < {PREFERRED_CANDLES}"
```

---

## 🔴 ۷-۴ [شدت: بالا] [دسته: باگ] — `record_signal` منبع و نوع بازار را در چک تکراری لحاظ نمی‌کند

**فایل:** `services/signal_recorder.py` خط ۵۰-۶۳

```python
cutoff = _utcnow() - timedelta(hours=24)
stmt = (
    select(SignalLog)
    .where(SignalLog.ticker == ticker)
    .where(SignalLog.tf == tf_name)
    .where(SignalLog.signal == signal)
    .where(SignalLog.timestamp >= cutoff)
    .limit(1)
)   # ← source و market_type غایب!
```

**سناریوهای باگ:**

1. کاربر «نوبیتکس» را انتخاب می‌کند → `BTC-USD LONG` روی `۵ دقیقه` ثبت می‌شود
2. کاربر «بیت‌پین» را انتخاب می‌کند → همان سیگنال دیده می‌شود
3. `record_signal` می‌بیند `BTC-USD / ۵ دقیقه / LONG` قبلاً در ۲۴ ساعت هست → **return False**
4. **سیگنال بیت‌پین هرگز ثبت نمی‌شود** → آمار بک‌تست بیت‌پین همیشه خالی می‌ماند

همین برای `market_type`: سیگنال spot یک سیگنال futures را بلوکه می‌کند.

اضافه: **race condition** — بین `SELECT` و `INSERT` هیچ constraint یکتایی نیست. دو تحلیل هم‌زمان (فرانت ۴ درخواست موازی می‌فرستد! بخش ۶-۶) → **دو ردیف تکراری**.

**راه‌حل:**

```python
"""
services/signal_recorder.py — با کلید تکراری کامل + محافظت اتمیک
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from api.database import engine
from api.models import SignalLog
from core.contracts import Signal as SigEnum

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def record_signal(
    ticker: str,
    name: str,
    signal: str,
    price: float,
    tf_name: str,
    source: str = "nobitex",
    market_type: str = "futures",
    risk_profile: str = "aggressive",
    sl_tp: dict | None = None,
    direction: str = "neutral",
    confidence: int = 0,
    consensus: str = "neutral",
    regime: str = "range",
    rr: float | None = None,
    traps: dict | None = None,
) -> bool:
    """ثبت سیگنال. True اگر ثبت شد، False اگر تکراری/نامعتبر."""
    if not SigEnum.is_directional(signal):
        return False
    if not price or price <= 0:
        return False

    now = _utcnow()

    try:
        with Session(engine) as session:
            # ═══ ۱. چک تکراری با کلید کامل ═══
            cutoff = now - timedelta(hours=24)
            stmt = (
                select(SignalLog)
                .where(SignalLog.ticker == ticker)
                .where(SignalLog.tf == tf_name)
                .where(SignalLog.signal == signal)
                .where(SignalLog.source == source)             # ← اضافه شد
                .where(SignalLog.market_type == market_type)   # ← اضافه شد
                .where(SignalLog.risk_profile == risk_profile) # ← اضافه شد
                .where(SignalLog.timestamp >= cutoff)
                .limit(1)
            )
            if session.exec(stmt).first():
                logger.debug(
                    f"[Recorder] تکراری: {ticker} {tf_name} {signal} "
                    f"({source}/{market_type}/{risk_profile})"
                )
                return False

            # ═══ ۲. استخراج ═══
            sl = tp = sl_tp_type = None
            if sl_tp:
                sl = sl_tp.get("sl")
                tp = sl_tp.get("tp")
                sl_tp_type = sl_tp.get("type")

            active_trap = None
            if traps:
                for key, val in traps.items():
                    if isinstance(val, dict) and val.get("active"):
                        active_trap = key
                        break

            log = SignalLog(
                ticker=ticker, name=name, source=source, signal=signal,
                direction=direction, confidence=confidence, consensus=consensus,
                regime=regime, price=float(price),
                sl=float(sl) if sl else None,
                tp=float(tp) if tp else None,
                sl_tp_type=sl_tp_type,
                rr=float(rr) if rr else None,
                tf=tf_name, market_type=market_type, risk_profile=risk_profile,
                had_trap=bool(active_trap), trap_type=active_trap,
                timestamp=now,
            )
            session.add(log)
            session.commit()
            logger.info(
                f"[Recorder] ✅ ثبت: {ticker} {tf_name} {signal} "
                f"({source}, {confidence}%)"
            )
            return True

    except IntegrityError:
        # ═══ ۳. race: constraint یکتایی جلوی تکراری را گرفت ═══
        logger.debug(f"[Recorder] race تشخیص داده شد: {ticker} {tf_name} {signal}")
        return False
    except Exception:
        logger.exception(f"[Recorder] خطا در ثبت {ticker} {tf_name} {signal}")
        return False
```

```python
# ─── api/models.py — افزودن constraint یکتایی ───
from sqlalchemy import UniqueConstraint

class SignalLog(SQLModel, table=True):
    __tablename__ = "signals_log"
    __table_args__ = (
        # ─── جلوگیری از تکراری در سطح دیتابیس (لایه دوم دفاع) ───
        UniqueConstraint(
            "ticker", "tf", "signal", "source", "market_type", "risk_profile",
            "dedup_bucket",
            name="uq_signal_dedup",
        ),
    )
    # ... فیلدهای قبلی ...
    dedup_bucket: str = Field(default="", index=True)   # ← "20260115"
    exit_reason: Optional[str] = None   # "tp" | "sl" | "ambiguous_sl_first" | "expired"
```

**تست:**
```python
# tests/test_signal_recorder.py
from sqlmodel import Session, select
from api.database import engine
from api.models import SignalLog
from services.signal_recorder import record_signal


def _clean():
    with Session(engine) as s:
        for r in s.exec(select(SignalLog)).all():
            s.delete(r)
        s.commit()


def test_same_signal_different_source_is_recorded():
    """BTC-USD LONG روی نوبیتکس و بیت‌پین → هر دو ثبت شوند"""
    _clean()
    kw = dict(ticker="BTC-USD", name="BTC", signal="LONG", price=100.0,
              tf_name="۵ دقیقه", direction="long", confidence=70,
              sl_tp={"sl": 95, "tp": 110, "type": "LONG"})

    assert record_signal(source="nobitex", **kw) is True
    assert record_signal(source="bitpin", **kw) is True      # ← قبل از اصلاح: False
    assert record_signal(source="wallex", **kw) is True

    with Session(engine) as s:
        n = len(s.exec(select(SignalLog).where(SignalLog.ticker == "BTC-USD")).all())
    assert n == 3, f"expected 3 rows, got {n}"


def test_exact_duplicate_still_blocked():
    _clean()
    kw = dict(ticker="ETH-USD", name="ETH", signal="SHORT", price=50.0,
              tf_name="۱۵ دقیقه", source="nobitex", direction="short",
              confidence=60, sl_tp={"sl": 55, "tp": 40, "type": "SHORT"})

    assert record_signal(**kw) is True
    assert record_signal(**kw) is False       # ← تکراری واقعی


def test_market_type_distinguishes():
    _clean()
    kw = dict(ticker="SOL-USD", name="SOL", signal="LONG", price=10.0,
              tf_name="۵ دقیقه", source="nobitex", direction="long",
              sl_tp={"sl": 9, "tp": 12, "type": "LONG"})

    assert record_signal(market_type="spot", **kw) is True
    assert record_signal(market_type="futures", **kw) is True


def test_concurrent_records_no_duplicate():
    """۱۰ ثبت موازی همان سیگنال → فقط یکی"""
    import threading
    _clean()
    kw = dict(ticker="ADA-USD", name="ADA", signal="LONG", price=1.0,
              tf_name="۵ دقیقه", source="nobitex", direction="long",
              sl_tp={"sl": 0.9, "tp": 1.2, "type": "LONG"})

    threads = [threading.Thread(target=record_signal, kwargs=kw) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    with Session(engine) as s:
        n = len(s.exec(select(SignalLog).where(SignalLog.ticker == "ADA-USD")).all())
    assert n == 1, f"race: {n} rows created"
```

---

## 🔴 ۷-۵ [شدت: بالا] [دسته: باگ] — `tf_name` به بیت‌پین/والکس درست نمی‌رسد → **تایم‌فریم اشتباه تحلیل می‌شود**

**فایل‌ها:** `services/data_service.py:24-35,52,65-71` · `core/data_fetcher.py:194,207` · `core/bitpin_fetcher.py:63-83` · `core/wallex_fetcher.py:62-82` · `core/scanner.py:166` · `core/backtester.py:245,270`

```python
# data_service.py
TF_MAP = {"۵ دقیقه": ("5m", "5d")}
interval, period = get_tf_params(tf_name)      # interval = "5m"

df = fetch_history_by_source(
    ticker=final_ticker,
    interval=interval,        # ← "5m" (انگلیسی)
    period=period,
    source=final_source,
    tf_name=tf_name,          # ← "۵ دقیقه" (فارسی) ✅
)
```

```python
# data_fetcher.py خط ۱۹۴ — برای بیت‌پین فقط tf_name فرستاده می‌شود ✅
df = fetch_bitpin_candles(ticker, tf_name)
```

پس چرا باگ؟ چون `TF_MAP` **فارسی → انگلیسی** است و `fetch_bitpin_candles` **فارسی** می‌خواهد. در مسیر عادی درست است. **ولی:**

1. `core/scanner.py:166` — `fetch_history_by_source(symbol, interval, period, cat_source)` — **`tf_name` را اصلاً نمی‌فرستد!** → `tf_name=""` → `TF_MAP.get("", "5m")` → **همیشه ۵ دقیقه**، حتی وقتی «روزانه» خواسته شده
2. `core/backtester.py:245` — `interval, period = "1h", "3mo"` **هاردکد** → و خط ۲۷۰ بدون `tf_name` → بیت‌پین/والکس **همیشه ۵ دقیقه/۱۵ دقیقه** می‌دهند ولی به‌عنوان ۱ ساعت تحلیل می‌شوند
3. `core/data_fetcher.py:226` — برای abantether `if interval == "1m"` چک می‌کند که با `tf_name` ناسازگار است

**اثر:** بک‌تست و اسکنر بیت‌پین/والکس روی کندل‌های **اشتباه** کار می‌کنند. `SIGNAL_TIMEOUT` برای «۱ ساعت» ۲ روز است، ولی کندل‌های ۵ دقیقه تحویل داده شده → ارزیابی کاملاً بی‌معنی.

**نکته‌ی مهم از تست زنده:** `wallex_fetcher.py:64` — `"۵ دقیقه": "15"` یعنی والکس ۵ دقیقه ندارد و **همیشه** ۱۵ دقیقه می‌دهد، ولی برچسبش «۵ دقیقه» می‌ماند. ATR و SL/TP بر پایه‌ی کندل ۱۵ دقیقه محاسبه می‌شود و کاربر فکر می‌کند ۵ دقیقه است. همین برای `"۳۰ دقیقه": "60"`.

**راه‌حل — یک منبع حقیقت:**

```python
# ─── core/contracts.py — جدول واحد تایم‌فریم ───
from typing import NamedTuple


class TFSpec(NamedTuple):
    """مشخصات کامل یک تایم‌فریم — تنها منبع حقیقت"""
    name_fa: str          # "۵ دقیقه"
    udf_res: str          # نوبیتکس/والکس: "5"
    bitpin_res: str       # بیت‌پین: "5m"
    period_days: int      # چند روز دیتا لازم است
    timeout_min: int      # مهلت سیگنال
    atr_mult: float
    wallex_res: str       # ← جدا، چون والکس ۵ دقیقه ندارد
    wallex_substituted: bool


TIMEFRAME_SPECS: dict[str, TFSpec] = {
    "۱ دقیقه":  TFSpec("۱ دقیقه",  "1",   "1m",  2,    30,   0.67, "1",  False),
    "۵ دقیقه":  TFSpec("۵ دقیقه",  "5",   "5m",  10,   120,  1.50, "15", True),   # ← جانشین
    "۱۵ دقیقه": TFSpec("۱۵ دقیقه", "15",  "15m", 20,   360,  2.60, "15", False),
    "۳۰ دقیقه": TFSpec("۳۰ دقیقه", "30",  "30m", 30,   720,  3.00, "60", True),   # ← جانشین
    "۱ ساعت":   TFSpec("۱ ساعت",   "60",  "1h",  180,  2880, 3.00, "60", False),
    "روزانه":   TFSpec("روزانه",   "1D",  "1d",  730, 10080, 3.00, "1D", False),
}

TF_NAMES = list(TIMEFRAME_SPECS)


def get_tf_spec(tf_name: str) -> TFSpec:
    """با fallback امن — هرگز None برنگردان"""
    spec = TIMEFRAME_SPECS.get(tf_name)
    if spec is None:
        import logging
        logging.getLogger(__name__).warning(
            f"[Contracts] TF ناشناخته {tf_name!r} — پیش‌فرض ۵ دقیقه"
        )
        return TIMEFRAME_SPECS["۵ دقیقه"]
    return spec
```

```python
# ─── core/bitpin_fetcher.py (اصلاح‌شده) ───
from core.contracts import get_tf_spec


def fetch_bitpin_candles(ticker: str, tf_name: str = "۵ دقیقه") -> pd.DataFrame | None:
    """دریافت کندل‌های بیت‌پین — tf_name فارسی (اجباری)"""
    symbol = map_symbol_to_bitpin(ticker)
    if not symbol:
        return None

    if not tf_name:
        logger.error("[Bitpin] tf_name خالی — تایم‌فریم مشخص نیست")
        return None

    spec = get_tf_spec(tf_name)          # ← جدول واحد، با هشدار برای ناشناخته

    to_ts = int(datetime.now(timezone.utc).timestamp())
    from_ts = to_ts - spec.period_days * 86400

    params = {"symbol": symbol, "from": from_ts, "to": to_ts, "res": spec.bitpin_res}
    # ... ادامه
```

```python
# ─── core/wallex_fetcher.py (اصلاح‌شده + شفافیت) ───
from core.contracts import get_tf_spec


def fetch_wallex_candles(ticker: str, tf_name: str = "۵ دقیقه") -> pd.DataFrame | None:
    symbol = map_symbol_to_wallex(ticker)
    if not symbol:
        return None

    if not tf_name:
        logger.error("[Wallex] tf_name خالی")
        return None

    spec = get_tf_spec(tf_name)

    # ─── ⚠️ شفافیت: به کاربر بگو TF جایگزین شده ───
    if spec.wallex_substituted:
        logger.warning(
            f"[Wallex] {tf_name} پشتیبانی نمی‌شود → {spec.wallex_res} دقیقه. "
            f"ATR و SL/TP روی کندل جایگزین محاسبه می‌شود."
        )
    # ... ادامه با spec.wallex_res و spec.period_days
```

```python
# ─── core/scanner.py خط ۱۶۶ (اصلاح‌شده) ───
            df = fetch_history_by_source(
                symbol, interval, period, cat_source,
                tf_name=tf_name,          # ← ✅ حالا فرستاده می‌شود
            )
```

```python
# ─── core/data_fetcher.py — tf_name را اجباری کن ───
def fetch_history_by_source(
    ticker: str,
    interval: str,
    period: str,
    source: str = "nobitex",
    tf_name: str = "",
):
    if not ticker:
        return None

    if not tf_name:
        logger.error(
            f"[Fetcher] tf_name خالی برای {ticker}/{source} — "
            f"نمی‌توان تایم‌فریم درست را تعیین کرد"
        )
        return None             # ← به‌جای fallback بی‌صدا به 5m
```

**تست:**
```python
# tests/test_timeframe_plumbing.py
import pytest
from unittest.mock import patch
from core.contracts import TIMEFRAME_SPECS


@pytest.mark.parametrize("tf", list(TIMEFRAME_SPECS))
def test_bitpin_receives_correct_resolution(tf):
    """بیت‌پین باید resolution درست بگیرد، نه همیشه 5m"""
    from core.bitpin_fetcher import fetch_bitpin_candles

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status = lambda: None
        fetch_bitpin_candles("BTC-USD", tf)

        _, kwargs = mock_get.call_args
        expected = TIMEFRAME_SPECS[tf].bitpin_res
        assert kwargs["params"]["res"] == expected, \
            f"{tf} → {kwargs['params']['res']} (expected {expected})"


def test_scanner_passes_tf_name():
    """scanner نباید tf_name را جا بیندازد"""
    from core import scanner
    import inspect
    src = inspect.getsource(scanner.scan_markets)
    assert "tf_name=" in src


def test_empty_tf_name_is_rejected():
    from core.data_fetcher import fetch_history_by_source
    assert fetch_history_by_source("BTC-USD", "5m", "5d", "bitpin", tf_name="") is None
```

---

## 🟡 ۷-۶ [شدت: متوسط] [دسته: logic] — بک‌تست: برد خوش‌بینانه + معیارهای ناسازگار

### الف) در یک کندل که هم SL و هم TP لمس می‌شود → همیشه «برد»

**فایل:** `services/backtest_service.py` خط ۸۵-۱۰۶

```python
if SigEnum.is_long(log.signal):
    if high >= log.tp:                    # ← اول TP چک می‌شود
        log.result = "win"
        return "win"
    if low <= log.sl:                     # ← بعد SL
        log.result = "loss"
        return "loss"
```

**مشکل (تأیید تجربی):** روی کندل ۱ دقیقه BTC با ATR بالا، احتمال لمس هر دو سطح در یک کندل زیاد است. چون TP اول چک می‌شود، **همیشه برد** ثبت می‌شود. این یک **سوگیری سیستماتیک خوش‌بینانه** است.

تست من:
```
LONG: both touched in same candle -> recorded WIN (optimistic)
```

اضافه: بک‌تست **کارمزد و اسلیپیج** را حساب نمی‌کند. صرافی‌های ایرانی ۰.۱-۰.۵٪ کارمزد دارند → روی TP ۲.۵× ATR این می‌تواند ۲۰٪ از سود را بخورد.

### ب) `profit_factor` و `expectancy` در واحدهای مختلف

**فایل:** `services/backtest_service.py` خط ۱۸۵-۲۰۶

```python
gross_win = sum(abs(r.tp - r.price) / r.price for r in rows if r.result == "win")   # ← درصد قیمت
gross_loss = sum(abs(r.price - r.sl) / r.price for r in rows if r.result == "loss")
stats["profit_factor"] = gross_win / gross_loss

rrs = [r.rr for r in rows if r.rr]              # ← R-multiple
stats["avg_rr"] = sum(rrs) / len(rrs)
stats["expectancy"] = wr * stats["avg_rr"] - (1 - wr)    # ← R-multiple × احتمال
```

**مشکل:** `profit_factor` و `expectancy` دو **واحد مختلف** دارند:

- `profit_factor` = مجموع درصدهای سود / مجموع درصدهای ضرر → به اندازه‌ی SL/TP حساس است، نه به R:R
- `expectancy` = win_rate × avg_rr − (1 − win_rate) → به اندازه‌ی SL/TP **حساس نیست**

نتیجه: می‌توانید PF = ۴.۰ (به‌نظر عالی) و expectancy = ۰.۱ (به‌نظر بد) ببینید، بدون اینکه بدانید کدام را باور کنید. تست من:

```
profit_factor (price-% based, rr ignored) = 42.0
avg_rr = 8.0 | expectancy = 5.0 (inconsistent units)
```

اضافه: `avg_rr` **همه‌ی** سیگنال‌ها را میانگین می‌گیرد — حتی loss‌ها. ولی `rr` یک ویژگی **ex-ante** طرح است، نه نتیجه. باید `realized_r` محاسبه شود.

**راه‌حل:**

```python
"""
services/backtest_service.py — معیارهای استاندارد بر پایه R
"""
FEE_PCT = 0.2          # ۰.۲٪ رفت و برگشت (کارمزد صرافی ایرانی)
SLIPPAGE_PCT = 0.1     # ۰.۱٪ لغزش قیمت


def _check_one(log: SignalLog) -> str | None:
    # ... تا رسیدن به حلقه‌ی کندل‌ها

    for idx, row in df.iterrows():
        high = float(row.get("high", 0))
        low = float(row.get("low", 0))

        # ─── محافظت: کندل بدون دامنه ───
        if high <= 0 or low <= 0 or high < low:
            continue

        is_long = SigEnum.is_long(log.signal)
        hit_tp = (high >= log.tp) if is_long else (low <= log.tp)
        hit_sl = (low <= log.sl) if is_long else (high >= log.sl)

        if hit_tp and hit_sl:
            # ═══ محافظه‌کارانه: فرض کن SL اول لمس شده ═══
            # دلیل: ترتیب درون‌کندلی نامعلوم است؛ فرض بدبینانه
            # از آمار خوش‌بینانه جلوگیری می‌کند.
            log.result = "loss"
            log.result_time = _to_aware(idx)
            log.exit_price = log.sl
            log.exit_reason = "ambiguous_sl_first"
            return "loss"

        if hit_sl:
            log.result = "loss"
            log.result_time = _to_aware(idx)
            log.exit_price = log.sl
            log.exit_reason = "sl"
            return "loss"

        if hit_tp:
            log.result = "win"
            log.result_time = _to_aware(idx)
            log.exit_price = log.tp
            log.exit_reason = "tp"
            return "win"

    return None


def _to_aware(idx) -> datetime:
    """index را به datetime UTC-aware تبدیل کن"""
    ts = pd.Timestamp(idx)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime()
```

```python
# ─── services/backtest_service.py — compute_stats با معیارهای R ───
def compute_stats(tf: str = "", source: str = "", time_filter: str = "all") -> dict:
    """
    آمار بک‌تست — معیارهای استاندارد بر پایه R-multiple.

    تفاوت کلیدی با نسخه‌ی قبل:
      - expectancy و profit_factor هر دو بر R کار می‌کنند (نه درصد قیمت)
      - کارمزد و اسلیپیج کسر می‌شوند
      - max_drawdown هم محاسبه می‌شود
    """
    stats = {
        "total": 0, "wins": 0, "losses": 0, "pending": 0, "expired": 0,
        "win_rate": 0.0, "profit_factor": 0.0, "avg_rr": 0.0,
        "expectancy_r": 0.0,           # ← بر R
        "expectancy_pct": 0.0,         # ← بر درصد (خالص کارمزد)
        "net_return_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "avg_win_r": 0.0, "avg_loss_r": 0.0,
        "fee_applied": FEE_PCT,
    }

    try:
        with Session(engine) as session:
            stmt = select(SignalLog)
            if tf:
                stmt = stmt.where(SignalLog.tf == tf)
            if source:
                stmt = stmt.where(SignalLog.source == source)

            now = datetime.now(timezone.utc)
            if time_filter == "7d":
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=7))
            elif time_filter == "30d":
                stmt = stmt.where(SignalLog.timestamp >= now - timedelta(days=30))

            rows = session.exec(stmt).all()

            stats["total"] = len(rows)
            stats["wins"] = sum(1 for r in rows if r.result == "win")
            stats["losses"] = sum(1 for r in rows if r.result == "loss")
            stats["pending"] = sum(1 for r in rows if r.result is None and not r.expired)
            stats["expired"] = sum(1 for r in rows if r.expired)

            closed = stats["wins"] + stats["losses"]
            if closed == 0:
                return stats

            stats["win_rate"] = round(stats["wins"] / closed * 100, 2)

            # ═══ R-multiple محقق‌شده — بر پایه فاصله‌ی واقعی ورود→خروج ═══
            r_multiples: list[float] = []
            pct_returns: list[float] = []

            for r in rows:
                if r.result not in ("win", "loss"):
                    continue
                if not r.price or not r.sl or not r.tp:
                    continue

                risk = abs(r.price - r.sl)
                if risk <= 0:
                    continue

                exit_p = r.exit_price if r.exit_price else (r.tp if r.result == "win" else r.sl)
                reward = abs(exit_p - r.price)

                r_raw = reward / risk if r.result == "win" else -1.0

                # ─── کارمزد و اسلیپیج به R ───
                cost_r = (FEE_PCT + SLIPPAGE_PCT) / 100 * r.price / risk
                r_net = r_raw - cost_r

                pct = (reward / r.price * 100) * (1 if r.result == "win" else -1)
                pct_net = pct - FEE_PCT - SLIPPAGE_PCT

                r_multiples.append(r_net)
                pct_returns.append(pct_net)

            if r_multiples:
                wins_r = [x for x in r_multiples if x > 0]
                losses_r = [x for x in r_multiples if x <= 0]

                stats["avg_rr"] = round(sum(r_multiples) / len(r_multiples), 2)
                stats["avg_win_r"] = round(sum(wins_r) / len(wins_r), 2) if wins_r else 0.0
                stats["avg_loss_r"] = round(sum(losses_r) / len(losses_r), 2) if losses_r else 0.0

                gross_win_r = sum(wins_r)
                gross_loss_r = abs(sum(losses_r))

                if gross_loss_r > 0:
                    stats["profit_factor"] = round(gross_win_r / gross_loss_r, 2)
                elif gross_win_r > 0:
                    stats["profit_factor"] = 999.0

                stats["expectancy_r"] = round(sum(r_multiples) / len(r_multiples), 3)

            if pct_returns:
                stats["expectancy_pct"] = round(sum(pct_returns) / len(pct_returns), 3)
                stats["net_return_pct"] = round(sum(pct_returns), 2)

                # ─── max drawdown روی منحنی سرمایه ───
                equity = 1.0
                peak = 1.0
                max_dd = 0.0
                for p in pct_returns:
                    equity *= (1 + p / 100)
                    peak = max(peak, equity)
                    max_dd = max(max_dd, (peak - equity) / peak * 100)
                stats["max_drawdown_pct"] = round(max_dd, 2)

    except Exception:
        logger.exception("[Backtest] خطا در compute_stats")

    return stats
```

```python
# ─── api/schemas.py — BacktestStats را هم‌راستا کن ───
class BacktestStats(BaseModel):
    total: int = 0
    wins: int = 0
    losses: int = 0
    pending: int = 0
    expired: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_rr: float = 0.0
    expectancy_r: float = 0.0        # ← جدید
    expectancy_pct: float = 0.0      # ← جدید
    net_return_pct: float = 0.0      # ← جدید
    max_drawdown_pct: float = 0.0    # ← جدید
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    fee_applied: float = 0.0
```

**تست:**
```python
# tests/test_backtest_metrics.py
import pandas as pd
import services.backtest_service as bs
from api.models import SignalLog


def _candle(high, low, ts="2026-01-01T00:10:00Z"):
    return pd.DataFrame(
        {"open": [low], "high": [high], "low": [low], "close": [low], "volume": [1.0]},
        index=pd.to_datetime([ts]),
    )


def test_ambiguous_candle_is_loss_not_win(monkeypatch):
    """کندلی که هم SL هم TP را لمس می‌کند → محافظه‌کارانه loss"""
    log = SignalLog(
        ticker="BTC-USD", signal="LONG", direction="long",
        price=100.0, sl=95.0, tp=110.0, tf="۵ دقیقه", source="nobitex",
        timestamp=pd.Timestamp("2026-01-01T00:00:00Z").to_pydatetime(),
    )
    monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: _candle(111, 94))

    assert bs._check_one(log) == "loss"
    assert log.exit_reason == "ambiguous_sl_first"


def test_not_ambiguous_when_only_tp_hit(monkeypatch):
    log = SignalLog(
        ticker="BTC-USD", signal="LONG", direction="long",
        price=100.0, sl=95.0, tp=110.0, tf="۵ دقیقه", source="nobitex",
        timestamp=pd.Timestamp("2026-01-01T00:00:00Z").to_pydatetime(),
    )
    monkeypatch.setattr(bs, "fetch_ohlcv", lambda *a, **k: _candle(111, 99))

    assert bs._check_one(log) == "win"
    assert log.exit_reason == "tp"
```

---

## 🟡 ۷-۷ [شدت: متوسط] [دسته: باگ] — متن «حمایت» به‌جای «مقاومت» چاپ می‌شود

**فایل:** `core/analyzer.py` خط ۲۲۱۴-۲۲۲۱

```python
if s > 0 and price > 0:
    dist_s = abs(price - s) / price * 100
    if is_tsetmc:
        lines.append(f"🔴 **مقاومت:** {r:,.0f} ریال (فاصله: {dist_r:.2f}%)")   # ← 🔴 باید «حمایت» و s/dist_s باشد
    elif is_iranian:
        lines.append(f"🔴 **مقاومت:** {r:,.0f} تومان (فاصله: {dist_r:.2f}%)")   # ← 🔴 همان
    else:
        lines.append(f"🔴 **مقاومت:** {r:,.2f}$ (فاصله: {dist_r:.2f}%)")        # ← 🔴 همان
```

**مشکل:** بلوک `support` دقیقاً کپی بلوک `resistance` است. کاربر در تحلیل عمیق **دو بار «مقاومت»** به یک قیمت می‌بیند و **هیچ‌وقت حمایت** نمی‌بیند. برای تصمیم‌گیری معاملاتی، حمایت مهم‌ترین سطح است. آیکن هم باید 🟢 باشد نه 🔴.

**راه‌حل:**

```python
# ─── core/analyzer.py خط ۲۲۱۴-۲۲۲۱ (اصلاح‌شده) ───
        if s > 0 and price > 0:
            dist_s = abs(price - s) / price * 100
            if is_tsetmc:
                lines.append(f"🟢 **حمایت:** {s:,.0f} ریال (فاصله: {dist_s:.2f}%)")
            elif is_iranian:
                lines.append(f"🟢 **حمایت:** {s:,.0f} تومان (فاصله: {dist_s:.2f}%)")
            else:
                lines.append(f"🟢 **حمایت:** {s:,.2f}$ (فاصله: {dist_s:.2f}%)")
```

**تست:**
```python
# tests/test_paragraph_support.py
from core.analyzer import build_analysis_paragraph

def test_support_is_labelled_support():
    tfs = {"۵ دقیقه": {
        "signal": "خنثی", "price": 100.0, "support": 95.0, "resistance": 110.0,
        "regime": "range", "confidence": 0, "groups": {}, "traps": {},
        "neutral_explain": {}, "scenarios": [], "market_type": "spot",
        "candle: ": None,
    }}
    text = build_analysis_paragraph("BTC-USD", "BTC", tfs, tf_name="۵ دقیقه")
    assert "حمایت" in text, "بلوک حمایت هرگز چاپ نمی‌شود"
    assert "95" in text
    assert text.count("مقاومت") == 1, "مقاومت دو بار چاپ شده"
```

---

## 🟡 ۷-۸ [شدت: متوسط] [دسته: باگ] — `print` به‌جای `logging` در ۱۰ نقطه‌ی مسیر تحلیل

**فایل:** `core/analyzer.py` خط ۲۷۳، ۱۴۸۸، ۱۴۹۳، ۱۴۹۹، ۱۷۷۰ · `core/tsetmc_fetcher.py` ۱۵۰، ۲۲۹ · `core/nobitex_auth.py` ۵۴، ۷۴، ۱۰۱ · `core/nobitex_fetcher.py` ۵۶۲

```python
def compute_indicators(df):
    try:
        ...
    except Exception as e:
        print(f"[Analyzer] compute_indicators: {e}")     # ← print
```

**مشکل:**

- `api/main.py` خط ۲۲-۲۵ `logging.basicConfig` را تنظیم می‌کند → `print` از آن **عبور نمی‌کند** → بدون timestamp، بدون level، غیرقابل فیلتر
- در `api/analyzer_service.py` خط ۱۱۴ خطا **با logging ثبت می‌شود** ولی `core/analyzer.py` خط ۱۷۷۰ هم `print` می‌زند → پیام دوبار، یکی بی‌ساختار
- در production خروجی `print` جایی نمی‌رود که قابل جستجو باشد

**راه‌حل:**

```python
# ─── core/analyzer.py ───
import logging

logger = logging.getLogger(__name__)

# ─── خط ۲۷۳ ───
    except Exception as e:
        logger.exception("[Analyzer] compute_indicators شکست خورد")

# ─── خط ۱۴۸۸-۱۴۹۹ ───
    if df is None or df.empty:
        logger.info("[Analyzer] دیتافریم خالی")
        return None

    n_candles = len(df)
    if n_candles < MIN_CANDLES:
        logger.info(f"[Analyzer] کندل ناکافی: {n_candles} < {MIN_CANDLES}")
        return None

# ─── خط ۱۷۶۹-۱۷۷۴ ───
    except Exception:
        logger.exception(f"[Analyzer] خطا در تحلیل {ticker} / {tf_name}")

# ─── core/tsetmc_fetcher.py، core/nobitex_auth.py، core/nobitex_fetcher.py ───
# همان جایگزینی print → logger
```

**تست:**
```python
# tests/test_no_print_in_core.py
import io, contextlib, inspect
from core import analyzer, tsetmc_fetcher, nobitex_auth, nobitex_fetcher


def test_no_bare_print_in_analysis_path():
    """مسیر تحلیل نباید print داشته باشد"""
    for mod in (analyzer, tsetmc_fetcher, nobitex_auth, nobitex_fetcher):
        src = inspect.getsource(mod)
        code_lines = [
            l for l in src.splitlines()
            if l.strip().startswith("print(") and not l.strip().startswith("#")
        ]
        assert not code_lines, f"{mod.__name__} هنوز print دارد: {code_lines[:3]}"
```

---

# ۸. نکات مثبت (که باید حفظ شوند)

اینها را در ریفکتور **نشکنید**:

| مورد | محل |
|---|---|
| ✅ **هیچ circular import واقعی نیست** — `import api.main` تست شد و سالم بالا می‌آید | کل پروژه |
| ✅ **RTL سراسری درست** — `dir="rtl"` + `lang="fa"` | `app/layout.tsx` |
| ✅ **`clearInterval` درست در همه‌ی تایمرهای دائم** | `SignalCard`, `PriceComparison`, `Marquee`, `SignalHistory` |
| ✅ **`rel="noreferrer"` روی همه‌ی لینک‌های خارجی** | `Footer.tsx` |
| ✅ **کلاس `num` با `tabular-nums`** برای قیمت — انتخاب عالی برای جدول اعداد | `globals.css` |
| ✅ **`normalize_df_columns` + `clean_ohlcv`** — لایه پاک‌سازی داده درست طراحی شده | `core/utils.py:395-454` |
| ✅ **`.env` و `.env.local` در `.gitignore`** | `.gitignore:12-15` |
| ✅ **CORS محدود (نه `*`)** با `allow_credentials=True` — ترکیب درست | `api/main.py:59-65` |
| ✅ **سوییچ منبع با پیام فارسی** در `resolve_symbol_and_source` | `core/sources.py:61,65,70-71` |
| ✅ **`dict | None` type hints درست** (Python 3.10+) | `services/*` |
| ✅ **نرمال‌سازی نیم‌فاصله در جستجوی نماد** — توجه دقیق به فارسی | `SymbolSelector.tsx:71` |
| ✅ **حذف کندل تکراری + فیلتر کندل صفر در نوبیتکس** | `nobitex_fetcher.py:546-548` |
| ✅ **ترتیب ستون‌های `pandas_ta_classic` همه درست** (`bb`, `kc`, `dc`, `adx`, `macd`, `stoch`, `supertrend`) — تست شد | `core/analyzer.py:156-220` |

---

# ۹. برنامه‌ی اجرایی — ۵ قدم اول به ترتیب اولویت

## 🥇 قدم ۱ (امروز، ۳۰ دقیقه) — کد را در git بگذار و secrets را ignore کن
**چرا اول:** اگر دیسک بمیرد یا `git clean -fdx` بزنی، **کل فاز ۶ از بین می‌رود**. هیچ ریفکتور دیگری مهم نیست تا این حل شود.
**بخش:** ۱-۳، ۴-۲

## 🥈 قدم ۲ (این هفته، ۲ ساعت) — Timezone را یک‌دست کن
**چرا دوم:** تمام آمار win/loss بیت‌پین/والکس/TSETMC **بی‌اعتبار** است. باگ در داده، نه نمایش. هر تصمیم معاملاتی بر این آمار اشتباه است.
**بخش:** ۳-۱، ۳-۲
**فایل ایجاد کن:** `core/tz.py`

## 🥉 قدم ۳ (این هفته، ۱ ساعت) — تایم‌فریم درست برسد به بیت‌پین/والکس
**چرا سوم:** کاربر «روزانه» انتخاب می‌کند، تحلیل روی کندل ۵ دقیقه انجام می‌شود. والکس هم ۵ دقیقه را بی‌صدا به ۱۵ دقیقه تبدیل می‌کند.
**بخش:** ۷-۵
**فایل ایجاد کن:** جدول `TIMEFRAME_SPECS` در `core/contracts.py`

## ۴️⃣ قدم ۴ (این هفته، ۱ ساعت) — `await run_in_threadpool` + قفل scheduler + WAL
**چرا چهارم:** با یک کاربر روی `/scan`، کل API برای همه down است. همچنین خطر `database is locked`.
**بخش:** ۲-۳، ۲-۴، ۲-۵

## ۵️⃣ قدم ۵ (هفته‌ی بعد، ۲ ساعت) — احراز هویت `DELETE /backtest/reset` + `record_signal` + SL/TP فرانت
**چرا پنجم:** یکی `curl` می‌زند، تاریخچه‌ی همه‌ی کاربران پاک می‌شود. و SL/TP نمایش‌داده‌شده با SL/TP ثبت‌شده در دیتابیس یکی نیست.
**بخش:** ۴-۱، ۷-۴، ۶-۱

---

# 📎 پیوست — جدول کامل فایل‌ها و خطوط

## باگ‌های بحرانی به ترتیب فایل

| فایل | خط | مشکل |
|---|---|---|
| `services/analyzer_service.py` | ۱۴۳-۱۴۸ | کلیدهای تکراری در dict → `float()` بی‌اثر |
| `services/analyzer_service.py` | ۱۶۹ | `close_series` در schema نیست → حذف می‌شود |
| `services/analyzer_service.py` | ۲۴۵-۲۵۰ | کش با `include_extras` ناهماهنگ |
| `services/backtest_service.py` | ۶۰-۶۷ | مقایسه UTC با Tehran-local |
| `services/backtest_service.py` | ۸۵-۱۰۶ | TP قبل از SL → برد خوش‌بینانه |
| `services/backtest_service.py` | ۱۱۴-۱۳۹ | یک خطا = کل batch از دست می‌رود |
| `services/backtest_service.py` | ۱۸۵-۲۰۶ | PF و expectancy در واحدهای مختلف |
| `services/signal_recorder.py` | ۵۰-۶۳ | `source`/`market_type` در چک تکراری غایب |
| `services/cache.py` | ۲۲-۴۹ | بدون lock، `min()` روی dict خالی |
| `services/cache.py` | ۷۲-۹۱ | fingerprint از کندل باز → کش بی‌اثر |
| `services/data_service.py` | ۲۴-۳۱ | period کوتاه → EMA200 = NaN |
| `core/analyzer.py` | ۴۰۷-۴۶۵ | RSI در روند، معکوس رأی می‌دهد |
| `core/analyzer.py` | ۸۱۹-۸۲۶، ۹۶۳ | `vol_ratio=0` → تله جعلی |
| `core/analyzer.py` | ۱۴۷-۱۴۸ | `< 50 کندل` بی‌صدا برمی‌گردد |
| `core/analyzer.py` | ۱۶۶۱-۱۶۹۱ | `TF_ATR_MULT` روی SL و TP هر دو |
| `core/analyzer.py` | ۲۲۱۴-۲۲۲۱ | **مقاومت به‌جای حمایت** چاپ می‌شود |
| `core/analyzer.py` | ۲۷۳، ۱۴۸۸، ۱۴۹۳، ۱۴۹۹، ۱۷۷۰ | `print` به‌جای `logging` |
| `core/contracts.py` | ۲۵۸-۲۷۰ | ضریب غیریکنوا، بدون سقف |
| `core/bitpin_fetcher.py` | ۱۲۵ | tz-naive محلی |
| `core/bitpin_fetcher.py` | ۸۲-۸۳ | `map_tf` با tf_name انگلیسی |
| `core/wallex_fetcher.py` | ۱۲۵ | tz-naive محلی |
| `core/wallex_fetcher.py` | ۶۲-۶۹ | «۵ دقیقه» → ۱۵ دقیقه بی‌صدا |
| `core/nobitex_auth.py` | ۲۴ | فایل کلید بدون gitignore |
| `core/market_lists.py` | ۱۵ | مسیر نسبی به CWD |
| `core/utils.py` | ۲۵۱-۳۲۱ | naive local در `time_ago` |
| `core/backtester.py` | ۸۶، ۱۵۷، ۲۵۶، ۵۱۶ | `datetime.now()` naive محلی |
| `core/scanner.py` | ۱۶۶ | `tf_name` فرستاده نمی‌شود |
| `api/database.py` | ۱۳-۱۹ | بدون WAL/busy_timeout/pool_pre_ping |
| `api/scheduler.py` | ۳۷-۴۳ | بدون `max_instances`/`coalesce` |
| `api/scheduler.py` | ۱۶-۲۹ | sync در event loop |
| `api/routers/backtest.py` | ۷۱-۹۳ | `had_trap`/`trap_type` غایب |
| `api/routers/backtest.py` | ۱۱۰-۱۱۸ | `DELETE /reset` بدون احراز هویت |
| `api/routers/analyze.py` | ۱۴-۲۵ | ایمپورت تکراری (`QuoteResponse` دو بار) |
| `api/routers/scan.py` | ۴۹-۸۷ | حلقه سریال در async |
| `api/schemas.py` | ۹۵ | `datetime.utcnow()` deprecated + naive |
| `frontend/src/components/signal/SignalCard.tsx` | ۱۵۳-۱۷۷ | SL/TP از قیمت زنده، نه از سرور |
| `frontend/src/components/signal/SymbolSelector.tsx` | ۱۱۰-۱۲۲ | نماد کاربر را عوض می‌کند |
| `frontend/src/components/backtest/SignalHistory.tsx` | ۱۰۷ | `POST /backtest/run` هر ۳۰s |
| `frontend/src/components/backtest/SignalHistory.tsx` | ۱۵۰ | کارت را با `return null` قورت می‌دهد |
| `frontend/src/components/backtest/BacktestStats.tsx` | ۲۹-۴۶ | حلقه‌ی fetch |
| `frontend/src/components/scan/Scanner.tsx` | ۶۸ | `risk_profile` هاردکد |
| `frontend/src/lib/api.ts` | ۱۷-۲۵ | خطای production بی‌صدا |
| `frontend/src/store/useAppStore.ts` | ۹، ۱۹ | `source: string` |

---

# 🔬 پیوست ب — تست‌هایی که اجرا کردم

```text
✅ python -c "import api.main"                        → API OK (no circular import)
✅ TTLCache 8 threads × 400 ops                       → errors: 0 (bug is theoretical at this scale)
✅ timezone filter comparison                          → بیت‌پین 5/5 کندل نگه داشت (باید 3/5 باشد)
✅ backtest same-candle SL+TP                         → recorded WIN (optimistic bias confirmed)
✅ profit_factor vs expectancy units                  → PF=42.0 vs expectancy=5.0 (inconsistent)
✅ pandas_ta column order: bb/kc/dc/adx/macd/stoch    → همه‌ی ایندکس‌ها درست (no bug)
✅ pandas_ta supertrend column order                  → iloc[:,1] = dir_ ✅ درست
```

**باگ‌هایی که در این ریویو پیدا نشد (خبر خوب):**
- ❌ Circular import — وجود ندارد
- ❌ ترتیب ستون‌های `pandas_ta_classic` — همه درست
- ❌ `ADX` و `supertrend_dir` ایندکس — درست
- ❌ CORS wildcard — وجود ندارد
- ❌ SQL injection — همه‌جا SQLModel/parameterized
- ❌ `eval`/`exec` — وجود ندارد

---

**پایان گزارش**
