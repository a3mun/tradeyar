"""تست سریع API لوکال — بدون دردسر Unicode"""

import json
import urllib.request

BASE = "http://localhost:8000"


def _post(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


print("=" * 60)
print("🔬 تست API لوکال")
print("=" * 60)

# ─── ۱. Health ───
print("\n[۱] Health Check:")
try:
    h = _get("/health")
    print(f"   {h}")
except Exception as e:
    print(f"   ❌ {e}")
    exit(1)

# ─── ۲. Analyze ───
print("\n[۲] Analyze BTC-USD (۱۵ دقیقه):")
try:
    a = _post(
        "/analyze",
        {
            "ticker": "BTC-USD",
            "source": "nobitex",
            "timeframe": "۱۵ دقیقه",
            "market_type": "futures",
            "risk_profile": "aggressive",
        },
    )
    print(f"   Signal: {a.get('signal')} · {a.get('confidence')}%")
    print(f"   Regime: {a.get('regime')}")
    print(f"   is_worthwhile: {a.get('is_worthwhile')}")
    print(f"   timeframe_viable: {a.get('timeframe_viable')}")
    print(f"   price: {a.get('price')}")

    deep = a.get("deep_analysis", "")
    print(f"\n   --- deep_analysis (اول ۱۰۰۰ کاراکتر) ---")
    print(f"   {deep[:1000]}")
    print(f"   ---")
    print(f"   طول کل: {len(deep)} کاراکتر")
    print(f"   شامل ▎: {'▎' in deep}")

except Exception as e:
    print(f"   ❌ {e}")

# ─── ۳. Scan pre_breakout ───
print("\n[۳] Scan — pre_breakout:")
try:
    s = _post(
        "/scan",
        {
            "source": "nobitex",
            "category": "crypto",
            "timeframe": "۱۵ دقیقه",
            "market_type": "futures",
            "risk_profile": "aggressive",
            "limit": 10,
            "scan_mode": "pre_breakout",
        },
    )
    print(f"   Total: {s.get('total')}")
    for item in s.get("items", [])[:5]:
        print(
            f"   • {item['ticker']} | {item['signal']} | "
            f"conf={item['confidence']}% | "
            f"pb={item.get('is_pre_breakout')} | "
            f"pb_down={item.get('is_pre_breakout_down')}"
        )
except Exception as e:
    print(f"   ❌ {e}")

# ─── ۴. Scan all ───
print("\n[۴] Scan — all:")
try:
    s = _post(
        "/scan",
        {
            "source": "nobitex",
            "category": "crypto",
            "timeframe": "۱۵ دقیقه",
            "market_type": "futures",
            "risk_profile": "aggressive",
            "limit": 10,
            "scan_mode": "all",
        },
    )
    print(f"   Total: {s.get('total')}")
    for item in s.get("items", [])[:3]:
        print(
            f"   • {item['ticker']} | {item['signal']} | " f"conf={item['confidence']}%"
        )
except Exception as e:
    print(f"   ❌ {e}")

# ─── ۵. Backtest ───
print("\n[۵] Backtest Stats:")
try:
    b = _get("/backtest")
    stats = b.get("stats", {})
    print(f"   Total: {stats.get('total')}")
    print(f"   Win rate: {stats.get('win_rate')}%")
    print(f"   Trend accuracy: {stats.get('trend_accuracy')}%")
    print(f"   Pending: {stats.get('pending')}")
except Exception as e:
    print(f"   ❌ {e}")

# ─── ۶. by-quality ───
print("\n[۶] Backtest by-quality:")
try:
    q = _get("/backtest/by-quality")
    items = q.get("items", {})
    for key in ["all", "strong", "normal", "weak"]:
        d = items.get(key, {})
        print(
            f"   {key:8} | total={d.get('total', 0):3} | "
            f"win_rate={d.get('win_rate', 0):5.1f}% | "
            f"trend_acc={d.get('trend_accuracy', 0):5.1f}%"
        )
except Exception as e:
    print(f"   ❌ {e}")

print("\n" + "=" * 60)
print("✅ تست کامل شد!")
