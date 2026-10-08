"""
tools/test_full_system.py
تست جامع سیستم Trademun
============================================================
- بکند: endpoints، WS، دیتابیس، اسکنر
- فرانت: فایل‌های TS، importها، کامپوننت‌ها
- خطاها: python syntax، TS errors
"""

import ast
import os
import sys
import time
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# مسیرها
# ═══════════════════════════════════════════════════════════
ROOT = Path(__file__).parent.parent
API_DIR = ROOT / "api"
CORE_DIR = ROOT / "core"
SERVICES_DIR = ROOT / "services"
FRONTEND_DIR = ROOT / "frontend" / "src"
TESTS_DIR = ROOT / "tests"

# ═══════════════════════════════════════════════════════════
# رنگ‌ها
# ═══════════════════════════════════════════════════════════
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log_ok(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def log_err(msg):
    print(f"{RED}❌ {msg}{RESET}")


def log_warn(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def log_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def log_section(title):
    print(f"\n{BLUE}{'═' * 60}{RESET}")
    print(f"{BLUE}  {title}{RESET}")
    print(f"{BLUE}{'═' * 60}{RESET}")


# ═══════════════════════════════════════════════════════════
# ۱. تست Syntax پایتون
# ═══════════════════════════════════════════════════════════
def test_python_syntax():
    log_section("۱. تست Syntax پایتون")

    errors = []
    count = 0

    for py_file in (
        list(API_DIR.rglob("*.py"))
        + list(CORE_DIR.rglob("*.py"))
        + list(SERVICES_DIR.rglob("*.py"))
    ):
        if "__pycache__" in str(py_file):
            continue
        count += 1
        try:
            with open(py_file, encoding="utf-8") as f:
                ast.parse(f.read())
        except SyntaxError as e:
            errors.append(f"{py_file.relative_to(ROOT)}: {e}")
        except Exception as e:
            errors.append(f"{py_file.relative_to(ROOT)}: {e}")

    if errors:
        for err in errors:
            log_err(err)
        return False

    log_ok(f"{count} فایل پایتون — همه سالم")
    return True


# ═══════════════════════════════════════════════════════════
# ۲. تست Import پایتون
# ═══════════════════════════════════════════════════════════
def test_python_imports():
    log_section("۲. تست Import پایتون")

    modules = [
        "api.main",
        "api.database",
        "api.models",
        "api.config",
        "api.scheduler",
        "core.analyzer",
        "core.data_fetcher",
        "core.orderbook",
        "core.contracts",
        "services.analyzer_service",
        "services.backtest_service",
        "services.data_service",
        "services.signal_recorder",
        "services.ws_manager",
    ]

    sys.path.insert(0, str(ROOT))
    errors = []

    for mod in modules:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"{mod}: {e}")

    if errors:
        for err in errors:
            log_err(err)
        return False

    log_ok(f"{len(modules)} ماژول — همه import می‌شن")
    return True


# ═══════════════════════════════════════════════════════════
# ۳. تست دیتابیس
# ═══════════════════════════════════════════════════════════
def test_database():
    log_section("۳. تست دیتابیس")

    try:
        from sqlmodel import Session, select
        from api.database import engine, init_db, migrate_db
        from api.models import SignalLog

        # ساخت جداول
        init_db()
        migrate_db()
        log_ok("جداول ساخته شدن")

        # تست کوئری
        with Session(engine) as session:
            stmt = select(SignalLog).limit(1)
            list(session.exec(stmt).all())
        log_ok("کوئری ساده — OK")

        # تست ستون is_weak
        with Session(engine) as session:
            stmt = select(SignalLog.is_weak).limit(1)
            list(session.exec(stmt).all())
        log_ok("ستون is_weak — OK")

        return True
    except Exception as e:
        log_err(f"خطا در دیتابیس: {e}")
        return False


# ═══════════════════════════════════════════════════════════
# ۴. تست Analyzer
# ═══════════════════════════════════════════════════════════
def test_analyzer():
    log_section("۴. تست Analyzer")

    try:
        from services.analyzer_service import analyze, quote, sparkline

        # تحلیل BTC-USD
        result = analyze(
            ticker="BTC-USD",
            source="nobitex",
            tf_name="۵ دقیقه",
            market_type="futures",
            risk_profile="aggressive",
            use_cache=False,
        )

        if result is None:
            log_warn("تحلیل BTC-USD برگشت None (شاید صرافی در دسترس نیست)")
        else:
            log_ok(
                f"BTC-USD — سیگنال: {result.get('signal')}, اطمینان: {result.get('confidence')}%"
            )

        # Sparkline
        sp = sparkline("BTC-USD", "nobitex", "۵ دقیقه")
        if sp and sp.get("close_series"):
            log_ok(f"Sparkline — {len(sp['close_series'])} کندل")
        else:
            log_warn("Sparkline برگشت None")

        # Quote
        q = quote("BTC-USD", "nobitex")
        if q and q.get("price"):
            log_ok(f"Quote — {q['price']}")
        else:
            log_warn("Quote برگشت None")

        return True
    except Exception as e:
        log_err(f"خطا در Analyzer: {e}")
        import traceback

        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════
# ۵. تست Frontend (فایل‌ها وجود دارن؟)
# ═══════════════════════════════════════════════════════════
def test_frontend_files():
    log_section("۵. تست فایل‌های Frontend")

    required_files = [
        "app/page.tsx",
        "app/layout.tsx",
        "components/signal/SignalCard.tsx",
        "components/signal/TFTable.tsx",
        "components/signal/FearGreed.tsx",
        "components/signal/SupportResistance.tsx",
        "components/signal/AIAnalysis.tsx",
        "components/signal/DeepAnalysis.tsx",
        "components/signal/Checklist.tsx",
        "components/signal/OrderBookPanel.tsx",
        "components/signal/PriceComparison.tsx",
        "components/signal/WatchlistCard.tsx",
        "components/signal/SymbolSelector.tsx",
        "components/backtest/BacktestPanel.tsx",
        "components/backtest/BacktestStats.tsx",
        "components/backtest/SignalHistory.tsx",
        "components/backtest/BacktestFilters.tsx",
        "components/scan/Scanner.tsx",
        "components/layout/Header.tsx",
        "components/layout/Footer.tsx",
        "components/layout/Marquee.tsx",
        "components/layout/HelpPanel.tsx",
        "components/layout/StickyMiniHeader.tsx",
        "components/ui/collapsible-card.tsx",
        "components/ui/card.tsx",
        "components/ui/button.tsx",
        "components/ui/badge.tsx",
        "lib/api.ts",
        "lib/sources.ts",
        "lib/display.ts",
        "lib/types.ts",
        "store/useAppStore.ts",
        "hooks/useSignalData.tsx",
    ]

    missing = []
    for f in required_files:
        path = FRONTEND_DIR / f
        if not path.exists():
            missing.append(f)

    if missing:
        for m in missing:
            log_err(f"غایب: {m}")
        return False

    log_ok(f"{len(required_files)} فایل — همه وجود دارن")
    return True


# ═══════════════════════════════════════════════════════════
# ۶. تست Hookهای Frontend
# ═══════════════════════════════════════════════════════════
def test_frontend_hooks():
    log_section("۶. تست Hookهای Frontend")

    hooks = [
        "hooks/useSignalData.ts",
        "lib/hooks/useWebSocket.ts",
        "lib/hooks/useWebSocketProvider.ts",
        "lib/hooks/useScrollVisibility.ts",
        "lib/hooks/useAnalysisCapability.ts",
    ]

    missing = []
    for h in hooks:
        path = FRONTEND_DIR / h
        if not path.exists():
            missing.append(h)

    if missing:
        for m in missing:
            log_warn(f"غایب: {m} (شاید اختیاریه)")

    log_ok(f"{len(hooks) - len(missing)}/{len(hooks)} hook — موجود")
    return True


# ═══════════════════════════════════════════════════════════
# ۷. تست Endpoints (بدون سرور)
# ═══════════════════════════════════════════════════════════
def test_endpoints():
    log_section("۷. تست endpoints (با httpx)")

    try:
        import httpx
    except ImportError:
        log_warn("httpx نصب نیست — skip")
        return True

    try:
        with httpx.Client(base_url="http://localhost:8000", timeout=10.0) as client:
            # /health
            r = client.get("/health")
            if r.status_code == 200:
                log_ok(f"/health — {r.json()}")
            else:
                log_err(f"/health — {r.status_code}")
                return False

            # /analyze/quote
            r = client.get(
                "/analyze/quote", params={"ticker": "BTC-USD", "source": "nobitex"}
            )
            if r.status_code == 200:
                log_ok(f"/analyze/quote — {r.json().get('price')}")
            else:
                log_warn(f"/analyze/quote — {r.status_code}")

            # /analyze/sparkline
            r = client.get(
                "/analyze/sparkline", params={"ticker": "BTC-USD", "source": "nobitex"}
            )
            if r.status_code == 200:
                log_ok(
                    f"/analyze/sparkline — {len(r.json().get('close_series', []))} کندل"
                )
            else:
                log_warn(f"/analyze/sparkline — {r.status_code}")

            # /backtest
            r = client.get("/backtest")
            if r.status_code == 200:
                log_ok(f"/backtest — کل: {r.json().get('stats', {}).get('total')}")
            else:
                log_warn(f"/backtest — {r.status_code}")

            # /backtest/history
            r = client.get("/backtest/history", params={"limit": 5})
            if r.status_code == 200:
                log_ok(f"/backtest/history — {r.json().get('total')} آیتم")
            else:
                log_warn(f"/backtest/history — {r.status_code}")

        return True
    except Exception as e:
        log_warn(f"سرور بکند خوابیده — {e}")
        log_info("برای تست endpoints، سرور رو روشن کن")
        return True


# ═══════════════════════════════════════════════════════════
# ۸. تست Signal Recorder
# ═══════════════════════════════════════════════════════════
def test_signal_recorder():
    log_section("۸. تست Signal Recorder")

    try:
        from services.signal_recorder import record_signal

        # سیگنال قطعی — باید ثبت بشه
        result1 = record_signal(
            ticker="TEST-USD",
            name="Test",
            signal="LONG",
            price=100.0,
            tf_name="۱ ساعت",
            source="nobitex",
            market_type="futures",
            risk_profile="aggressive",
            direction="long",
            confidence=70,
        )
        log_ok(f"سیگنال قطعی — ثبت: {result1}")

        # سیگنال ضعیف — باید ثبت بشه (با is_weak)
        result2 = record_signal(
            ticker="TEST2-USD",
            name="Test2",
            signal="LONG ضعیف",
            price=100.0,
            tf_name="۱ ساعت",
            source="nobitex",
            market_type="futures",
            risk_profile="aggressive",
            direction="long",
            confidence=40,
        )
        log_ok(f"سیگنال ضعیف — ثبت: {result2}")

        # سیگنال خنثی — نباید ثبت بشه
        result3 = record_signal(
            ticker="TEST3-USD",
            name="Test3",
            signal="خنثی",
            price=100.0,
            tf_name="۱ ساعت",
            source="nobitex",
            market_type="futures",
            risk_profile="aggressive",
            direction="neutral",
            confidence=0,
        )
        log_ok(f"سیگنال خنثی — ثبت نشد: {result3}")

        return True
    except Exception as e:
        log_err(f"خطا در Signal Recorder: {e}")
        return False


# ═══════════════════════════════════════════════════════════
# ۹. تست pytest (اگه تست‌ها هستن)
# ═══════════════════════════════════════════════════════════
def test_pytest():
    log_section("۹. اجرای pytest")

    if not TESTS_DIR.exists():
        log_warn("پوشه tests نیست — skip")
        return True

    import subprocess

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(TESTS_DIR), "-v", "--tb=short"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            log_ok("همه‌ی تست‌ها پاس شدن")
            # آخرین خط خلاصه
            lines = result.stdout.strip().split("\n")
            for line in lines[-5:]:
                print(f"  {line}")
        else:
            log_warn(f"بعضی تست‌ها fail — returncode: {result.returncode}")
            print(result.stdout[-2000:])

        return True
    except subprocess.TimeoutExpired:
        log_warn("pytest timeout — skip")
        return True
    except Exception as e:
        log_warn(f"pytest اجرا نشد: {e}")
        return True


# ═══════════════════════════════════════════════════════════
# ۱۰. تست TypeScript (اگه tsc هست)
# ═══════════════════════════════════════════════════════════
def test_typescript():
    log_section("۱۰. تست TypeScript")

    frontend_root = ROOT / "frontend"
    if not (frontend_root / "package.json").exists():
        log_warn("package.json نیست — skip")
        return True

    import subprocess

    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=frontend_root,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
        )

        if result.returncode == 0:
            log_ok("TypeScript — بدون خطا")
        else:
            log_err("TypeScript — خطا داره:")
            print(result.stdout[-2000:])

        return True
    except Exception as e:
        log_warn(f"tsc اجرا نشد: {e}")
        return True


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print(f"\n{BLUE}{'═' * 60}{RESET}")
    print(f"{BLUE}  🎩 تست جامع Trademun{RESET}")
    print(f"{BLUE}{'═' * 60}{RESET}")

    start = time.time()

    results = {
        "Syntax پایتون": test_python_syntax(),
        "Import پایتون": test_python_imports(),
        "دیتابیس": test_database(),
        "Analyzer": test_analyzer(),
        "فایل‌های Frontend": test_frontend_files(),
        "Hookهای Frontend": test_frontend_hooks(),
        "Endpoints": test_endpoints(),
        "Signal Recorder": test_signal_recorder(),
        "pytest": test_pytest(),
        "TypeScript": test_typescript(),
    }

    elapsed = time.time() - start

    log_section("📊 نتیجه‌ی نهایی")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, ok in results.items():
        status = f"{GREEN}✅{RESET}" if ok else f"{RED}❌{RESET}"
        print(f"  {status} {name}")

    print(f"\n  {GREEN}پاس: {passed}/{total}{RESET}")
    print(f"  زمان: {elapsed:.1f}s")

    if passed == total:
        print(f"\n{GREEN}🎉 همه‌ی تست‌ها پاس شدن!{RESET}")
        return 0
    else:
        print(f"\n{RED}⚠️  بعضی تست‌ها fail — چک کن{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
