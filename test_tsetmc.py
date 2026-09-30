"""
test_tsetmc.py
تست OHLCV بورس تهران
"""

from core.data_fetcher import fetch_history_by_source

for symbol in ["فولاد", "فملی", "خودرو", "شپنا", "وبملت"]:
    print(f"\n{symbol}:")
    try:
        df = fetch_history_by_source(symbol, "1d", "6mo", "tsetmc")
        if df is None:
            print("   ❌ df=None")
        elif df.empty:
            print("   ❌ خالی")
        else:
            print(f"   ✅ {len(df)} کندل")
            print(f"   آخرین: {df['close'].iloc[-1]:,.0f}")
            print(f"   بازه: {df.index[0].date()} → {df.index[-1].date()}")
    except Exception as e:
        print(f"   ❌ خطا: {e}")

print()
