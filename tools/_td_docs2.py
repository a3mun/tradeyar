"""tools/_td_docs2.py — خواندن مستندات تبدیل"""

import json
import re

import requests

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/json,*/*",
}

print("=" * 78)
print("۱) endpointهای ذکرشده در مستندات")
print("=" * 78)

r = requests.get("https://docs.tabdeal.org/", headers=H, timeout=30)
t = r.text
print(f"  {len(t)} کاراکتر")

# ─── دنبال مسیرهای API ───
paths = set()
for p in [
    r'["\'](/r?/?api/[a-zA-Z0-9/_\-{}.:]*)["\']',
    r'["\'](/[a-z]+/v[0-9]/[a-zA-Z0-9/_\-{}]*)["\']',
    r'https://api[a-z0-9.\-]*\.tabdeal\.org/[a-zA-Z0-9/_\-{}]*',
]:
    for m in re.findall(p, t):
        paths.add(m)

print(f"\n  {len(paths)} مسیر پیدا شد:")
for p in sorted(paths):
    print(f"    {p}")

# ─── کلمات کلیدی مهم ───
print()
print("=" * 78)
print("۲) جستجوی OHLCV / Kline در متن مستندات")
print("=" * 78)
for kw in ["ohlcv", "kline", "candle", "history", "chart", "interval",
           "resolution", "granularity", "market/", "websocket", "subscribe"]:
    idxs = [m.start() for m in re.finditer(kw, t, re.I)][:3]
    for i in idxs:
        seg = t[max(0, i - 90) : i + 110].replace("\n", " ").replace("\r", "")
        seg = re.sub(r"\s+", " ", seg)
        print(f"  [{kw}] …{seg}…")

print()
print("=" * 78)
print("۳) تست مسیرهای api-web.tabdeal.org")
print("=" * 78)
BASE = "https://api-web.tabdeal.org"
CANDIDATES = [
    "/markets",
    "/api/v1/exchangeInfo",
    "/market/klines",
    "/markets/BTC_IRT",
    "/markets/BTCIRT",
    "/market/BTC_IRT",
    "/market/history/BTC_IRT",
    "/charts/BTC_IRT",
    "/chart/BTC_IRT",
    "/candles/BTC_IRT",
    "/ohlcv/BTC_IRT",
    "/klines/BTC_IRT",
    "/trades/BTC_IRT",
    "/orderbook/BTC_IRT",
    "/markets/BTC_IRT/klines",
    "/markets/BTC_IRT/candles",
    "/markets/BTC_IRT/history",
    "/markets/BTC_IRT/chart",
    "/spot/markets",
    "/spot/BTC_IRT",
    "/v1/klines",
    "/v1/markets",
]
for path in CANDIDATES:
    try:
        r = requests.get(f"{BASE}{path}", headers=H, timeout=12)
        if r.status_code != 404:
            print(f"  ⚠️ {r.status_code}  {path}")
            print(f"      {r.text[:180]}".replace("\n", " "))
    except Exception:
        pass
print("  (فقط غیر-۴۰۴)")

print()
print("=" * 78)
print("۴) ساختار /markets — چه فیلدهایی دارد؟")
print("=" * 78)
try:
    d = requests.get(f"{BASE}/markets", headers=H, timeout=20).json()
    markets = d.get("markets", [])
    print(f"  {len(markets)} بازار")
    if markets:
        print(f"  کلیدهای رکورد: {list(markets[0].keys())}")
        print()
        print("  نمونه:")
        print("  " + json.dumps(markets[0], ensure_ascii=False, indent=2)[:1200].replace("\n", "\n  "))
except Exception as e:
    print(f"  ❌ {e!r}")

print()
print("=" * 78)
