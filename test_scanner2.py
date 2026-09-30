"""
test_scanner2.py
"""

from core.nobitex_fetcher import fetch_all_nobitex_symbols, filter_liquid_symbols

all_syms = fetch_all_nobitex_symbols("usdt")
print(f"کل نمادهای USDT: {len(all_syms)}")
print()

if all_syms:
    print("اول ۵ تا از all_syms:")
    for s in all_syms[:5]:
        print(f"  {s['symbol']}: volume_24h={s.get('volume_24h', 0):,.2f}")
    print()

# فیلتر با مقادیر مختلف
for mv in [100, 1000, 10000]:
    filtered = filter_liquid_symbols(
        all_syms, min_volume=mv, min_trades=0, max_count=200
    )
    print(f"min_volume={mv:>6}: {len(filtered)} نماد")
