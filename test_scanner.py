"""
test_scanner.py
تست اسکنر
"""

from core.scanner import _get_nobitex_symbols_for_scanner

syms = _get_nobitex_symbols_for_scanner()
print(f"تعداد نمادها: {len(syms)}")
print()
print("نمونه (اول ۱۰ تا):")
for s in syms[:10]:
    print(f"  {s}")
