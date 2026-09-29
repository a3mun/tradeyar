"""
debug_now.py
تشخیص سریع مشکل yfinance و منابع
"""

import sys
from datetime import datetime

print("=" * 70)
print(f"تشخیص — {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)
print()

# ─── تست ۱: yfinance ───
print("【۱】تست yfinance (GC=F، 5d، 5m):")
try:
    import yfinance as yf

    df = yf.download(
        "GC=F",
        period="5d",
        interval="5m",
        progress=False,
        auto_adjust=True,
        threads=False,
    )
    if df is None:
        print("   ❌ df=None")
    elif df.empty:
        print("   ❌ df خالیه")
    else:
        print(f"   ✅ {len(df)} کندل")
        print(f"   آخرین: {float(df['Close'].iloc[-1]):,.2f}")
except Exception as e:
    print(f"   ❌ خطا: {type(e).__name__}: {e}")
print()

# ─── تست ۲: yfinance با interval کوتاه ───
print("【۲】تست yfinance (GC=F، 1mo، 1d):")
try:
    import yfinance as yf

    df = yf.download(
        "GC=F",
        period="1mo",
        interval="1d",
        progress=False,
        auto_adjust=True,
        threads=False,
    )
    if df is None or df.empty:
        print("   ❌ خالی یا None")
    else:
        print(f"   ✅ {len(df)} کندل")
except Exception as e:
    print(f"   ❌ خطا: {type(e).__name__}: {e}")
print()

# ─── تست ۳: شبکه (اتصال به یاهو) ───
print("【۳】تست اتصال به Yahoo Finance:")
try:
    import requests

    r = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=5d&interval=5m",
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        result = data.get("chart", {}).get("result", [])
        if result:
            timestamps = result[0].get("timestamp", [])
            print(f"   ✅ {len(timestamps)} timestamp")
        else:
            print("   ⚠️ result خالیه")
    else:
        print(f"   ❌ Status غیرمنتظره")
except Exception as e:
    print(f"   ❌ خطا: {type(e).__name__}: {e}")
print()

# ─── تست ۴: نوبیتکس ───
print("【۴】تست نوبیتکس:")
try:
    from core.nobitex_fetcher import fetch_nobitex_stats_for_ticker

    stats = fetch_nobitex_stats_for_ticker("BTC-USD")
    if stats:
        print(f"   ✅ BTC-USD: ${stats['price']:,.2f}")
    else:
        print("   ❌ خالی")
except Exception as e:
    print(f"   ❌ خطا: {type(e).__name__}: {e}")
print()

# ─── تست ۵: fetch_history_by_source ───
print("【۵】تست fetch_history_by_source:")
try:
    from core.data_fetcher import fetch_history_by_source

    # نوبیتکس
    df = fetch_history_by_source("BTC-USD", "5m", "5d", "nobitex")
    if df is not None and not df.empty:
        print(f"   BTC-USD (nobitex):  ✅ {len(df)} کندل")
    else:
        print(f"   BTC-USD (nobitex):  ❌ خالی")

    # global
    df = fetch_history_by_source("GC=F", "5m", "5d", "global")
    if df is not None and not df.empty:
        print(f"   GC=F (global):      ✅ {len(df)} کندل")
    else:
        print(f"   GC=F (global):      ❌ خالی")
except Exception as e:
    print(f"   ❌ خطا: {type(e).__name__}: {e}")
print()

print("=" * 70)
print("پایان")
print("=" * 70)
