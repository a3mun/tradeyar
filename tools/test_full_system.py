"""
tools/test_full_system.py
تست کامل سیستم Trademun — قبل از Deploy
============================================================
نحوه اجرا:
    .\.venv\Scripts\python.exe tools\test_full_system.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── اضافه‌کردن ریشه به sys.path ───
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

BASE_URL = "http://localhost:8000"
TIMEOUT = 60


# ═══════════════════════════════════════════════════════════
# ابزارهای تست
# ═══════════════════════════════════════════════════════════
class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results: list[dict] = []

    def add(self, name: str, ok: bool, detail: str = "", duration_ms: int = 0):
        status = "✅" if ok else "❌"
        print(f"  {status} {name} ({duration_ms}ms){' — ' + detail if detail else ''}")
        self.results.append(
            {
                "name": name,
                "ok": ok,
                "detail": detail,
                "duration_ms": duration_ms,
            }
        )
        if ok:
            self.passed += 1
        else:
            self.failed += 1

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "═" * 60)
        print(f"📊 خلاصه: {self.passed}/{total} پاس")
        if self.failed > 0:
            print(f"❌ {self.failed} شکست:")
            for r in self.results:
                if not r["ok"]:
                    print(f"   - {r['name']}: {r['detail']}")
        print("═" * 60)
        return self.failed == 0


R = TestResult()


# ═══════════════════════════════════════════════════════════
# تست‌ها
# ═══════════════════════════════════════════════════════════
def test_health():
    print("\n🏥 Health Check")
    t0 = time.time()
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        R.add(
            "GET /health",
            r.status_code == 200,
            f"status={r.status_code}",
            int((time.time() - t0) * 1000),
        )
    except Exception as e:
        R.add("GET /health", False, str(e))


def test_analyze(ticker: str, source: str, tf: str):
    """تست /analyze برای یک نماد"""
    name = f"POST /analyze [{ticker}/{source}/{tf}]"
    t0 = time.time()
    try:
        r = httpx.post(
            f"{BASE_URL}/analyze",
            json={
                "ticker": ticker,
                "source": source,
                "timeframe": tf,
                "market_type": "futures" if source != "tsetmc" else "spot",
                "risk_profile": "aggressive",
                "ticker_name": ticker,
            },
            timeout=TIMEOUT,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add(name, False, f"HTTP {r.status_code}", dur)
            return None
        data = r.json()
        # ─── بررسی فیلدهای حیاتی ───
        required = ["price", "signal", "direction", "confidence", "regime"]
        missing = [f for f in required if f not in data]
        if missing:
            R.add(name, False, f"missing: {missing}", dur)
            return None
        R.add(
            name,
            True,
            f"signal={data['signal']} ({data['confidence']}%) · {dur}ms",
            dur,
        )
        return data
    except Exception as e:
        R.add(name, False, str(e), int((time.time() - t0) * 1000))
        return None


def test_analyze_multi(ticker: str, source: str):
    """تست /analyze/multi"""
    name = f"POST /analyze/multi [{ticker}]"
    t0 = time.time()
    try:
        r = httpx.post(
            f"{BASE_URL}/analyze/multi",
            json={
                "ticker": ticker,
                "source": source,
                "timeframe": "۵ دقیقه",
                "market_type": "futures" if source != "tsetmc" else "spot",
                "risk_profile": "aggressive",
                "ticker_name": ticker,
            },
            timeout=TIMEOUT,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add(name, False, f"HTTP {r.status_code}", dur)
            return None
        data = r.json()
        tfs = data.get("timeframes", {})
        R.add(name, True, f"{len(tfs)} TF · {dur}ms", dur)
        return data
    except Exception as e:
        R.add(name, False, str(e), int((time.time() - t0) * 1000))
        return None


def test_quote(ticker: str, source: str):
    """تست /analyze/quote"""
    name = f"GET /analyze/quote [{ticker}/{source}]"
    t0 = time.time()
    try:
        r = httpx.get(
            f"{BASE_URL}/analyze/quote",
            params={"ticker": ticker, "source": source},
            timeout=TIMEOUT,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add(name, False, f"HTTP {r.status_code}", dur)
            return None
        data = r.json()
        if not data.get("price"):
            R.add(name, False, "price=0", dur)
            return None
        R.add(name, True, f"price={data['price']} · {dur}ms", dur)
        return data
    except Exception as e:
        R.add(name, False, str(e), int((time.time() - t0) * 1000))
        return None


def test_orderbook(ticker: str, source: str):
    """تست /orderbook/{ticker}/summary"""
    name = f"GET /orderbook/{ticker}/summary"
    t0 = time.time()
    try:
        r = httpx.get(
            f"{BASE_URL}/orderbook/{ticker}/summary",
            params={"source": source},
            timeout=TIMEOUT,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add(name, False, f"HTTP {r.status_code}", dur)
            return None
        data = r.json()
        R.add(
            name,
            True,
            f"imbalance={data.get('imbalance')} · spread={data.get('spread_pct')}%",
            dur,
        )
        return data
    except Exception as e:
        R.add(name, False, str(e), int((time.time() - t0) * 1000))
        return None


def test_fear_greed(ticker: str, source: str):
    """تست /analyze/fear-greed"""
    name = f"GET /analyze/fear-greed [{ticker}]"
    t0 = time.time()
    try:
        r = httpx.get(
            f"{BASE_URL}/analyze/fear-greed",
            params={"ticker": ticker, "source": source},
            timeout=TIMEOUT,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add(name, False, f"HTTP {r.status_code}", dur)
            return None
        data = r.json()
        R.add(name, True, f"value={data.get('value')} · {dur}ms", dur)
        return data
    except Exception as e:
        R.add(name, False, str(e), int((time.time() - t0) * 1000))
        return None


def test_scan(source: str):
    """تست /scan"""
    name = f"POST /scan [{source}]"
    t0 = time.time()
    category = "iran_stocks" if source == "tsetmc" else "crypto"
    try:
        r = httpx.post(
            f"{BASE_URL}/scan",
            json={
                "source": source,
                "category": category,
                "timeframe": "۵ دقیقه",
                "market_type": "spot" if source == "tsetmc" else "futures",
                "risk_profile": "aggressive",
                "limit": 20,
            },
            timeout=120,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add(name, False, f"HTTP {r.status_code}", dur)
            return None
        data = r.json()
        total = data.get("total", 0)
        R.add(name, True, f"{total} نتیجه · {dur}ms", dur)
        return data
    except Exception as e:
        R.add(name, False, str(e), int((time.time() - t0) * 1000))
        return None


def test_record_signal(ticker: str, source: str, tf: str):
    """تست POST /backtest/record"""
    name = f"POST /backtest/record [{ticker}/{tf}]"
    t0 = time.time()
    try:
        r = httpx.post(
            f"{BASE_URL}/backtest/record",
            json={
                "ticker": ticker,
                "source": source,
                "timeframe": tf,
                "market_type": "futures" if source != "tsetmc" else "spot",
                "risk_profile": "aggressive",
                "ticker_name": ticker,
            },
            timeout=TIMEOUT,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add(name, False, f"HTTP {r.status_code}", dur)
            return None
        data = r.json()
        R.add(name, True, f"recorded={data.get('recorded')} · {dur}ms", dur)
        return data
    except Exception as e:
        R.add(name, False, str(e), int((time.time() - t0) * 1000))
        return None


def test_backtest_stats():
    """تست GET /backtest"""
    print("\n📊 راستی‌آزمایی")
    t0 = time.time()
    try:
        r = httpx.get(
            f"{BASE_URL}/backtest", params={"time_filter": "all"}, timeout=TIMEOUT
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add("GET /backtest", False, f"HTTP {r.status_code}", dur)
            return
        data = r.json()
        stats = data.get("stats", {})
        R.add(
            "GET /backtest",
            True,
            f"total={stats.get('total')} · win_rate={stats.get('win_rate')}%",
            dur,
        )
    except Exception as e:
        R.add("GET /backtest", False, str(e))


def test_backtest_history():
    """تست GET /backtest/history"""
    t0 = time.time()
    try:
        r = httpx.get(
            f"{BASE_URL}/backtest/history",
            params={"limit": 50},
            timeout=TIMEOUT,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add("GET /backtest/history", False, f"HTTP {r.status_code}", dur)
            return
        data = r.json()
        R.add(
            "GET /backtest/history",
            True,
            f"{data.get('total')} سیگنال",
            dur,
        )
    except Exception as e:
        R.add("GET /backtest/history", False, str(e))


def test_backtest_run():
    """تست POST /backtest/run"""
    t0 = time.time()
    try:
        r = httpx.post(f"{BASE_URL}/backtest/run", timeout=120)
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add("POST /backtest/run", False, f"HTTP {r.status_code}", dur)
            return
        data = r.json()
        R.add(
            "POST /backtest/run",
            True,
            f"checked={data.get('checked')} · updated={data.get('updated')}",
            dur,
        )
    except Exception as e:
        R.add("POST /backtest/run", False, str(e))


def test_by_tf():
    """تست GET /backtest/by-tf"""
    t0 = time.time()
    try:
        r = httpx.get(
            f"{BASE_URL}/backtest/by-tf",
            params={"time_filter": "all"},
            timeout=TIMEOUT,
        )
        dur = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            R.add("GET /backtest/by-tf", False, f"HTTP {r.status_code}", dur)
            return
        data = r.json()
        R.add(
            "GET /backtest/by-tf",
            True,
            f"{len(data.get('items', {}))} TF",
            dur,
        )
    except Exception as e:
        R.add("GET /backtest/by-tf", False, str(e))


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════
def main():
    print("═" * 60)
    print("🧪 تست کامل سیستم Trademun")
    print("═" * 60)

    # ─── Health ───
    test_health()

    # ─── BTC-USD / nobitex ───
    print("\n₿ نماد ۱: BTC-USD / nobitex")
    test_analyze("BTC-USD", "nobitex", "۵ دقیقه")
    test_analyze_multi("BTC-USD", "nobitex")
    test_quote("BTC-USD", "nobitex")
    test_orderbook("BTC-USD", "nobitex")
    test_fear_greed("BTC-USD", "nobitex")
    test_record_signal("BTC-USD", "nobitex", "۵ دقیقه")

    # ─── PAXG-IRT / nobitex ───
    print("\n🥇 نماد ۲: PAXG-IRT / nobitex")
    test_analyze("PAXG-IRT", "nobitex", "۱۵ دقیقه")
    test_analyze_multi("PAXG-IRT", "nobitex")
    test_quote("PAXG-IRT", "nobitex")
    test_orderbook("PAXG-IRT", "nobitex")
    test_record_signal("PAXG-IRT", "nobitex", "۱۵ دقیقه")

    # ─── فولاد / tsetmc ───
    print("\n🇮🇷 نماد ۳: فولاد / tsetmc")
    test_analyze("فولاد", "tsetmc", "روزانه")
    test_analyze_multi("فولاد", "tsetmc")
    test_quote("فولاد", "tsetmc")
    test_record_signal("فولاد", "tsetmc", "روزانه")

    # ─── Scanner ───
    print("\n🔍 اسکنر")
    test_scan("nobitex")

    # ─── Backtest ───
    test_backtest_stats()
    test_backtest_history()
    test_backtest_run()
    test_by_tf()

    # ─── خلاصه ───
    success = R.summary()

    # ─── گزارش JSON ───
    report_path = Path(__file__).parent / "test_report.json"
    report_path.write_text(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "passed": R.passed,
                "failed": R.failed,
                "total": R.passed + R.failed,
                "success": success,
                "results": R.results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n📄 گزارش: {report_path}")
    print(f"\n{'✅ همه‌ی تست‌ها پاس شد!' if success else '❌ بعضی تست‌ها شکست خورد'}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
