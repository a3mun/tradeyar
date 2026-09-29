"""
debug_test.py
تست مستقیم توابع — ببینیم کجا fail می‌شه
"""

import sys
from datetime import datetime

print("=" * 70)
print(f"شروع تست — {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)
print()

# ═══════════════════════════════════════════════════════════
# ۱. تست imports
# ═══════════════════════════════════════════════════════════
print("【۱】تست importها...")
try:
    from core.contracts import TIMEFRAMES, SYMBOLS

    print(f"   ✅ contracts — {len(TIMEFRAMES)} TF، {len(SYMBOLS)} نماد")
except Exception as e:
    print(f"   ❌ contracts: {e}")
    sys.exit(1)

try:
    from core.sources import detect_source_for_ticker, is_symbol_available_in_source

    print(f"   ✅ sources")
except Exception as e:
    print(f"   ❌ sources: {e}")
    sys.exit(1)

try:
    from core.data_fetcher import fetch_history_by_source

    print(f"   ✅ data_fetcher")
except Exception as e:
    print(f"   ❌ data_fetcher: {e}")
    sys.exit(1)

try:
    from core.analyzer import analyze_symbol

    print(f"   ✅ analyzer")
except Exception as e:
    print(f"   ❌ analyzer: {e}")
    sys.exit(1)
print()

# ═══════════════════════════════════════════════════════════
# ۲. تست detect_source_for_ticker
# ═══════════════════════════════════════════════════════════
print("【۲】تست detect_source_for_ticker:")
for t in ["BTC-USD", "ETH-USD", "GC=F", "USDT-IRT", "PAXG-USD", "XAUT-USD"]:
    try:
        src = detect_source_for_ticker(t)
        avail = is_symbol_available_in_source(t, src)
        print(f"   {t:15} → منبع: {src:10} سازگار: {avail}")
    except Exception as e:
        print(f"   {t:15} → ❌ خطا: {e}")
print()

# ═══════════════════════════════════════════════════════════
# ۳. تست fetch_history_by_source برای BTC-USD از nobitex
# ═══════════════════════════════════════════════════════════
print("【۳】تست fetch_history_by_source('BTC-USD', '5m', '5d', 'nobitex'):")
try:
    df = fetch_history_by_source("BTC-USD", "5m", "5d", "nobitex")
    if df is None:
        print(f"   ❌ None برگشت — یعنی fetch کار نکرد")
    elif df.empty:
        print(f"   ❌ خالی برگشت")
    else:
        print(f"   ✅ {len(df)} کندل دریافت شد")
        print(f"   آخرین قیمت: ${df['close'].iloc[-1]:,.2f}")
        print(f"   بازه: {df.index[0]} → {df.index[-1]}")
except Exception as e:
    print(f"   ❌ خطا: {e}")
    import traceback

    traceback.print_exc()
print()

# ═══════════════════════════════════════════════════════════
# ۴. تست برای همه TFها
# ═══════════════════════════════════════════════════════════
print("【۴】تست همه TFها برای BTC-USD از nobitex:")
for iv, p, n in TIMEFRAMES:
    try:
        df = fetch_history_by_source("BTC-USD", iv, p, "nobitex")
        if df is None:
            print(f"   {n:12} ({iv:4}/{p:5}) → ❌ None")
        elif len(df) < 50:
            print(f"   {n:12} ({iv:4}/{p:5}) → ⚠️ فقط {len(df)} کندل (حداقل ۵۰ لازمه)")
        else:
            print(f"   {n:12} ({iv:4}/{p:5}) → ✅ {len(df)} کندل")
    except Exception as e:
        print(f"   {n:12} → ❌ خطا: {e}")
print()

# ═══════════════════════════════════════════════════════════
# ۵. تست fetch_nobitex_for_ticker مستقیم
# ═══════════════════════════════════════════════════════════
print("【۵】تست مستقیم nobitex_fetcher:")
try:
    from core.nobitex_fetcher import (
        fetch_nobitex_for_ticker,
        map_symbol_to_nobitex,
        is_in_nobitex,
    )

    print(f"   map_symbol_to_nobitex('BTC-USD'): {map_symbol_to_nobitex('BTC-USD')}")
    print(f"   is_in_nobitex('BTC-USD'): {is_in_nobitex('BTC-USD')}")

    df = fetch_nobitex_for_ticker("BTC-USD", "5m", "5d")
    if df is None:
        print(f"   ❌ fetch_nobitex_for_ticker برگشت None")
    elif df.empty:
        print(f"   ❌ خالی")
    else:
        print(f"   ✅ {len(df)} کندل")
        print(f"   آخرین: ${df['close'].iloc[-1]:,.2f}")
except Exception as e:
    print(f"   ❌ خطا: {e}")
    import traceback

    traceback.print_exc()
print()

# ═══════════════════════════════════════════════════════════
# ۶. تست analyze_symbol مستقیم
# ═══════════════════════════════════════════════════════════
print("【۶】تست analyze_symbol مستقیم:")
try:
    df = fetch_history_by_source("BTC-USD", "5m", "5d", "nobitex")
    if df is not None and not df.empty:
        print(f"   کندل ورودی: {len(df)}")
        result = analyze_symbol(
            df,
            risk_profile="aggressive",
            tf_name="۵ دقیقه",
            tfs_data=None,
            market_type="futures",
        )
        if result:
            print(f"   ✅ تحلیل موفق")
            print(f"   سیگنال: {result.get('signal')}")
            print(f"   اطمینان: {result.get('confidence')}%")
            print(f"   رژیم: {result.get('regime')}")
        else:
            print(f"   ❌ analyze_symbol برگشت None")
            if len(df) < 50:
                print(f"   ⚠️ چون فقط {len(df)} کندل داره")
    else:
        print(f"   ❌ df خالیه — نمی‌تونیم تحلیل کنیم")
except Exception as e:
    print(f"   ❌ خطا: {e}")
    import traceback

    traceback.print_exc()
print()

# ═══════════════════════════════════════════════════════════
# ۷. تست global برای طلا
# ═══════════════════════════════════════════════════════════
print("【۷】تست global برای GC=F:")
try:
    df = fetch_history_by_source("GC=F", "5m", "5d", "global")
    if df is None:
        print(f"   ❌ None")
    elif df.empty:
        print(f"   ❌ خالی")
    else:
        print(f"   ✅ {len(df)} کندل")
        result = analyze_symbol(
            df,
            risk_profile="aggressive",
            tf_name="۵ دقیقه",
            tfs_data=None,
            market_type="futures",
        )
        if result:
            print(f"   تحلیل: {result.get('signal')} ({result.get('confidence')}%)")
        else:
            print(f"   ❌ تحلیل None")
except Exception as e:
    print(f"   ❌ خطا: {e}")
print()

print("=" * 70)
print("پایان تست")
print("=" * 70)
