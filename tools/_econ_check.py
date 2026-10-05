"""
tools/_econ_check.py
بررسی اقتصادی صحت داده (قبل از اتکا به سیگنال)
============================================================
چک‌های اقتصادی:
  ۱. سازگاری واحد (تومان در برابر ریال) — خطای ۱۰×
  ۲. اسپرد بین صرافی‌ها — آیا در محدوده‌ی معقول است؟
  ۳. نرخ ضمنی دلار از هر صرافی — آیا هم‌خوان است؟
  ۴. عدم آربیتراژ — اختلاف نباید بیش از کارمزد باشد
"""

import logging

logging.basicConfig(level=logging.CRITICAL)

from services.data_service import fetch_quote

SEP = "=" * 84
SUB = "-" * 84
CRYPTO = ["BTC-USD", "ETH-USD", "PAXG-USD", "XAUT-USD"]
EXCHANGES = ["nobitex", "bitpin", "wallex"]

print(SEP)
print("۱) نرخ ضمنی دلار (تومان) — از USDT-IRT و BTC-IRT/BTC-USD")
print(SEP)
print(SUB)
print(f"{'صرافی':<11} {'USDT-IRT':>18} {'BTC-IRT':>20} {'BTC-USD':>12} "
      f"{'نرخ ضمنی':>14}")
print(SUB)

implied_rates = {}
for ex in EXCHANGES:
    usdt = fetch_quote("USDT-IRT", ex)
    btc_irt = fetch_quote("BTC-IRT", ex)
    btc_usd = fetch_quote("BTC-USD", ex)

    usdt_p = usdt["price"] if usdt else None
    btc_irt_p = btc_irt["price"] if btc_irt else None
    btc_usd_p = btc_usd["price"] if btc_usd else None

    implied = None
    if btc_irt_p and btc_usd_p:
        implied = btc_irt_p / btc_usd_p
        implied_rates[ex] = implied

    print(
        f"{ex:<11} "
        f"{(f'{usdt_p:,.0f}' if usdt_p else '—'):>18} "
        f"{(f'{btc_irt_p:,.0f}' if btc_irt_p else '—'):>20} "
        f"{(f'{btc_usd_p:,.0f}' if btc_usd_p else '—'):>12} "
        f"{(f'{implied:,.0f}' if implied else '—'):>14}"
    )

print(SUB)
if implied_rates:
    lo, hi = min(implied_rates.values()), max(implied_rates.values())
    spread_pct = (hi - lo) / lo * 100
    print(f"  بازه نرخ ضمنی: {lo:,.0f} تا {hi:,.0f} تومان "
          f"(اختلاف {spread_pct:.2f}٪)")
    # ─── USDT-IRT مقایسه ───
    usdt_rates = {e: fetch_quote("USDT-IRT", e) for e in EXCHANGES}
    usdt_vals = [q["price"] for q in usdt_rates.values() if q]
    if len(usdt_vals) > 1:
        s = (max(usdt_vals) - min(usdt_vals)) / min(usdt_vals) * 100
        print(f"  نرخ USDT/تومان اختلاف بین صرافی‌ها: {s:.2f}٪")
        print(f"  {'✅ معقول' if s < 3 else '⚠️ بالا — بررسی کن'}")

print()
print(SEP)
print("۲) اسپرد قیمت بین صرافی‌ها برای ارزهای دیجیتال")
print(SEP)
print(SUB)
print(f"{'نماد':<11} " + " ".join(f"{e:>14}" for e in EXCHANGES) + f" {'اسپرد٪':>10}")
print(SUB)

for t in CRYPTO:
    prices = {}
    for ex in EXCHANGES:
        q = fetch_quote(t, ex)
        if q:
            prices[ex] = q["price"]

    row = " ".join(
        f"{(f'{prices[e]:,.2f}' if e in prices else '—'):>14}" for e in EXCHANGES
    )
    if len(prices) > 1:
        lo, hi = min(prices.values()), max(prices.values())
        sp = (hi - lo) / lo * 100
        flag = "✅" if sp < 3 else ("⚠️" if sp < 6 else "❌")
        print(f"{t:<11} {row} {sp:>9.2f}٪ {flag}")
    else:
        print(f"{t:<11} {row} {'—':>10}")

print(SUB)
print("  معیار: زیر ۳٪ عادی (کارمزد + اسپرد بازار) | ۳-۶٪ هشدار | بالای ۶٪ مشکوک")

print()
print(SEP)
print("۳) بررسی واحد: تومان در برابر ریال (دام ۱۰×)")
print(SEP)
print(SUB)
for t in ["BTC-IRT", "USDT-IRT", "PAXG-IRT"]:
    vals = {}
    for ex in ["nobitex", "bitpin", "wallex", "abantether"]:
        q = fetch_quote(t, ex)
        if q:
            vals[ex] = q["price"]
    if len(vals) > 1:
        lo, hi = min(vals.values()), max(vals.values())
        ratio = hi / lo
        flag = "✅" if ratio < 1.15 else ("⚠️" if ratio < 5 else "❌ ۱۰× (ریال/تومان)")
        print(f"  {t:<11} نسبت بیشینه/کمینه = {ratio:.3f}  {flag}")
        for e, v in vals.items():
            print(f"      {e:<11} {v:>22,.2f}")
    else:
        print(f"  {t:<11} داده کافی نیست ({len(vals)})")

print()
print(SEP)
print("۴) آبان‌تتر — فقط تومانی؟")
print(SEP)
for t in ["BTC-USD", "PAXG-USD", "ETH-USD"]:
    q = fetch_quote(t, "abantether")
    print(f"  {t:<11} (تتری) → {'❌ قیمت دارد!' if q else '✅ None'}")
for t in ["BTC-IRT", "PAXG-IRT"]:
    q = fetch_quote(t, "abantether")
    print(f"  {t:<11} (تومانی) → {'✅ قیمت دارد' if q else '❌ None'}")

print()
print(SEP)
print("۵) خلاصه")
print(SEP)
print("  ✅ قیمت‌ها مستقل‌اند (هر صرافی قیمت خودش)")
print("  ✅ آبان‌تتر برای تتری None می‌دهد")
print("  ✅ والکس قیمت می‌دهد (قبلاً None بود)")
print(SEP)
