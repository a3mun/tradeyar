"""
extract_tsetmc.py
استخراج نمادهای بورس تهران از TSETMC API
"""

import json
import time
import requests
from pathlib import Path

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
    """جستجو در TSETMC — endpoint که قبلاً کار کرده"""
    url = f"{TSETMC_API}/Instrument/GetInstrumentSearch/{query}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("instrumentSearch", []) or []
    except Exception as e:
        print(f"   ⚠️ {query}: {e}")
        return []


def main():
    print("=" * 70)
    print("استخراج نمادهای بورس تهران")
    print("=" * 70)
    print()

    # ═══ استراتژی: جستجوی حروف مختلف الفبا + اعداد ═══
    # این روش نمادهای بیشتری رو پیدا می‌کنه
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
        time.sleep(0.5)  # ← delay بین کوئری‌ها
        new_count = 0
        for inst in results:
            symbol = inst.get("lVal18AFC", "").strip()
            name = inst.get("lVal30", "").strip()
            isin = inst.get("isin", "")

        if symbol and symbol not in mapping:
            # ═══ حجم معاملات (برای رتبه‌بندی) ═══
            qtot = inst.get("qTotTran5J") or 0  # حجم معاملات
            try:
                qtot = float(qtot)
            except (TypeError, ValueError):
                qtot = 0

            mapping[symbol] = {
                "name_fa": name,
                "isin": isin,
                "volume": qtot,
            }
            new_count += 1

        if new_count > 0:
            print(
                f"   [{i:>2}/{len(queries)}] '{q}': +{new_count} (کل: {len(mapping)})"
            )

    print()
    print(f"✅ کل نمادها: {len(mapping)}")
    print()

    if not mapping:
        print("❌ هیچ نمادی پیدا نشد — احتمالاً TSETMC در دسترس نیست")
        return

    # ═══ ادغام با فایل موجود ═══
    out_path = Path("data/tsetmc_symbols_full.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if out_path.exists():
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f) or {}
            if not isinstance(existing, dict):
                existing = {}
        except Exception:
            existing = {}

    # ادغام: mapping جدید بر existing غلبه می‌کنه
    merged = {**existing, **mapping}

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"💾 ذخیره شد: {out_path}")
    print(f"   جدید: {len(mapping)} نماد")
    print(f"   قبلی: {len(existing)} نماد")
    print(f"   ادغام‌شده: {len(merged)} نماد")
    print()

    # نمونه
    print("نمونه (۲۰ مورد اول):")
    for sym in list(mapping.keys())[:20]:
        print(f"  {sym} → {mapping[sym]['name_fa']}")
    print()


if __name__ == "__main__":
    main()
