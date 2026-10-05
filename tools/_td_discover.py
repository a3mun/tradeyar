"""tools/_td_discover.py — کشف endpoint چارت تبدیل از خود سایت"""

import re
import time

import requests

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

print("=" * 78)
print("۱) صفحات تبدیل را بگیر و دنبال API بگرد")
print("=" * 78)

PAGES = [
    "https://tabdeal.org/",
    "https://tabdeal.org/spot/BTC_IRT",
    "https://tabdeal.org/trade/BTC_IRT",
    "https://tabdeal.org/markets",
    "https://tabdeal.org/fa/spot/BTC_IRT",
]

found_urls = set()
for url in PAGES:
    try:
        r = requests.get(url, headers=H, timeout=20, allow_redirects=True)
        print(f"\n  {r.status_code}  {url}  ({len(r.content)} bytes)")
        if r.status_code != 200:
            continue

        txt = r.text

        # ─── دنبال API URL ───
        pats = [
            r'https?://[a-zA-Z0-9.\-]*tabdeal[a-zA-Z0-9.\-/]*',
            r'["\'](/api/[a-zA-Z0-9/_\-{}]*)[("\'?]',
            r'(wss?://[a-zA-Z0-9.\-]*tabdeal[a-zA-Z0-9.\-/]*)',
            r'(/r/api/[a-zA-Z0-9/_\-]*)',
        ]
        for p in pats:
            for m in re.findall(p, txt):
                u = m if isinstance(m, str) else m[0]
                if u and len(u) < 200:
                    found_urls.add(u)

        # ─── دنبال کلمات کلیدی ───
        for kw in ["klines", "candle", "ohlcv", "history", "chart", "stream", "ws"]:
            if kw in txt.lower():
                idx = txt.lower().find(kw)
                ctx = txt[max(0, idx - 60) : idx + 80].replace("\n", " ")
                print(f"      🔍 «{kw}»: …{ctx}…")
    except Exception as e:
        print(f"  ❌ {url}: {e!r}")

print()
print("=" * 78)
print("۲) URLهای کشف‌شده")
print("=" * 78)
for u in sorted(found_urls):
    print(f"  {u}")

print()
print("=" * 78)
print("۳) کشف از فایل‌های JS")
print("=" * 78)
# ─── پیدا کردن اسکریپت‌ها ───
try:
    r = requests.get("https://tabdeal.org/", headers=H, timeout=20)
    scripts = re.findall(r'src="([^"]+\.js)"', r.text)
    print(f"  {len(scripts)} اسکریپت پیدا شد")
    for s in scripts[:6]:
        url = s if s.startswith("http") else f"https://tabdeal.org{s}"
        try:
            jr = requests.get(url, headers=H, timeout=25)
            for p in [
                r'["\'](/r/api/[a-zA-Z0-9/_\-]*)["\']',
                r'["\'](/api/v[0-9]/[a-zA-Z0-9/_\-]*)["\']',
                r'(wss?://[a-zA-Z0-9.\-]+/[a-zA-Z0-9/_\-]*)',
                r'["\']([a-z]+/[a-z]+/history)["\']',
                r'klines?|candles?|ohlcv|udf',
            ]:
                for m in set(re.findall(p, jr.text, re.I)):
                    print(f"    {url.split('/')[-1][:30]}: {m}")
        except Exception as e:
            print(f"    ❌ {url}: {e!r}")
except Exception as e:
    print(f"  ❌ {e!r}")

print()
print("=" * 78)
print("۴) WebSocket — تبدیل stream دارد؟")
print("=" * 78)
print("""
  مستندات شما: wss://api1.tabdeal.org/stream/
  ⚠️ برای کشف اینکه چارت REST دارد یا فقط WS، باید
     درخواست‌های شبکه مرورگر را دید (DevTools → Network).

  اگر تبدیل چارت را از WS می‌سازد، OHLCV در REST **نیست**
  و باید کندل‌ها را از stream بسازیم (پیچیده).
""")
print("=" * 78)
