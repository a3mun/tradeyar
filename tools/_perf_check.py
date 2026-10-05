"""tools/_perf_check.py — تست عملکرد نهایی (طبق قوانین کاربر)"""

import logging
import statistics
import time

logging.basicConfig(level=logging.CRITICAL)

from services.analyzer_service import analyze, analyze_multi_tf
from services.cache import clear_all_negative, data_cache

SEP = "=" * 76
results = []


def bench(label, fn, budget):
    t0 = time.perf_counter()
    out = fn()
    el = time.perf_counter() - t0
    ok = el <= budget
    results.append((label, el, budget, ok))
    print(f"  {'✅' if ok else '❌'} {label:<46} {el:6.3f}s  (بودجه {budget}s)")
    return out


print(SEP)
print("تست عملکرد — طبق قوانین پروژه")
print(SEP)

# ─── گرم‌کردن ───
analyze("BTC-USD", "nobitex", "۵ دقیقه")

print("\n  ۱) analyze — cache hit (بودجه < ۱۰ms)")
df = None
for _ in range(3):
    _, df = None, analyze("BTC-USD", "nobitex", "۵ دقیقه")
bench(
    "analyze('BTC-USD','nobitex','۵ دقیقه')",
    lambda: analyze("BTC-USD", "nobitex", "۵ دقیقه"),
    0.010,
)

print("\n  ۲) analyze_multi_tf — کش گرم (بودجه < ۲s)")
bench(
    "analyze_multi_tf('BTC-USD','nobitex')",
    lambda: analyze_multi_tf("BTC-USD", "nobitex"),
    2.0,
)

print("\n  ۳) analyze_multi_tf — کش سرد (بودجه < ۱۰s)")
data_cache.clear()
clear_all_negative()
bench(
    "analyze_multi_tf کش سرد",
    lambda: analyze_multi_tf("BTC-USD", "nobitex"),
    10.0,
)

print("\n  ۴) /scan — کش گرم (بودجه < ۳s)")
from fastapi.testclient import TestClient

from api.deps import reset_rate_limits
from api.main import app

client = TestClient(app)
body = {
    "category": "crypto",
    "timeframe": "۵ دقیقه",
    "market_type": "futures",
    "risk_profile": "aggressive",
    "limit": 10,
}


def do_scan():
    reset_rate_limits()
    return client.post("/scan", json=body)


do_scan()  # ─── گرم‌کردن ───
bench("POST /scan limit=10 (کش گرم)", do_scan, 3.0)

print("\n  ۵) /scan — کش سرد (بودجه < ۳۰s)")
data_cache.clear()
clear_all_negative()
bench("POST /scan limit=10 (کش سرد)", do_scan, 30.0)

print("\n  ۶) /health (بودجه < ۱۰۰ms)")
lat = []
for _ in range(5):
    t0 = time.perf_counter()
    client.get("/health")
    lat.append(time.perf_counter() - t0)
best = min(lat)
ok = best < 0.1
results.append(("health", best, 0.1, ok))
print(f"  {'✅' if ok else '❌'} GET /health{'':<38} {best*1000:6.1f}ms (بودجه 100ms)")

# ═══════════════════════════════════════════════════════════
print()
print(SEP)
passed = sum(1 for _, _, _, ok in results if ok)
total = len(results)
print(f"  {passed}/{total} تست عملکردی پاس")
for label, el, budget, ok in results:
    print(f"    {'✅' if ok else '❌'} {label:<46} {el:7.3f}s / {budget}s")
print(SEP)
