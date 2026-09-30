"""
extract_tsetmc.py
استخراج نمادهای بورس تهران از TSETMC API — نسخه ۲
"""

import json
import time
import urllib.parse
from pathlib import Path

import requests

TSETMC_API = "https://cdn.tsetmc.com/api"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_instrument_search(query: str) -> list:
    """جستجو در TSETMC — با encode دستی برای فارسی"""
    encoded_query = urllib.parse.quote(query, safe="")
    url = f"{TSETMC_API}/Instrument/GetInstrumentSearch/{encoded_query}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("instrumentSearch", []) or []
    except Exception as e:
        print(f"   ⚠️ {query}: {e}")
        return []


def _is_valid_stock_symbol(symbol: str) -> bool:
    """
    فیلتر نمادهای مفید:
    - حذف حق تقدم (به «ح» ختم می‌شن)
    - حذف اوراق (به عدد ختم می‌شن)
    - حذف نمادهای کوتاه (کمتر از ۲ حرف)
    """
    if not symbol:
        return False
    if len(symbol) < 2:
        return False
    if symbol.endswith("ح"):
        return False
    if symbol[-1].isdigit():
        return False
    return True


def main():
    print("=" * 70)
    print("استخراج نمادهای بورس تهران — نسخه ۲")
    print("=" * 70)
    print()

    # ═══ استراتژی: جستجوی حروف مختلف الفبا + پیشوندهای صندوق ═══
    queries = [
        # الفبای فارسی
        "آ",
        "ا",
        "ب",
        "پ",
        "ت",
        "ث",
        "ج",
        "چ",
        "ح",
        "خ",
        "د",
        "ذ",
        "ر",
        "ز",
        "ژ",
        "س",
        "ش",
        "ص",
        "ض",
        "ط",
        "ظ",
        "ع",
        "غ",
        "ف",
        "ق",
        "ک",
        "گ",
        "ل",
        "م",
        "ن",
        "و",
        "ه",
        "ی",
        # حروف انگلیسی
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
        # صندوق‌ها (پیشوندهای رایج)
        "زر",
        "طلا",
        "کالا",
        "سهامی",
        "مختلط",
        "اهرم",
    ]

    mapping = {}
    print(f"🔍 جستجو با {len(queries)} کوئری...\n")

    for i, q in enumerate(queries, 1):
        results = fetch_instrument_search(q)

        new_count = 0
        for inst in results:
            symbol = inst.get("lVal18AFC", "").strip()
            name = inst.get("lVal30", "").strip()
            isin = inst.get("isin", "")

            if not symbol or symbol in mapping:
                continue
            if not _is_valid_stock_symbol(symbol):
                continue

            mapping[symbol] = {
                "name_fa": name,
                "isin": isin,
            }
            new_count += 1

        print(
            f"   [{i:>2}/{len(queries)}] '{q}': {len(results):>3} خام → +{new_count:>3} (کل: {len(mapping)})"
        )
        time.sleep(0.6)

    print()
    print(f"✅ کل نمادهای معتبر: {len(mapping)}")
    print()

    # ═══ ذخیره ═══
    out_path = Path("data/tsetmc_symbols_full.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"💾 ذخیره شد: {out_path}")
    print()

    # ═══ نمونه ═══
    print("نمونه (۲۰ مورد اول):")
    for sym in list(mapping.keys())[:20]:
        print(f"  {sym} → {mapping[sym]['name_fa']}")
    print()


if __name__ == "__main__":
    main()
