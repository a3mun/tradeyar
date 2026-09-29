"""
tools/logo_to_base64.py
تبدیل لوگو به Base64 — برای inline کردن در HTML
"""

import base64
from pathlib import Path


def main():
    logo_path = Path(__file__).parent.parent / "fonts" / "logo.png"
    output_path = Path(__file__).parent.parent / "fonts" / "logo.b64.txt"

    if not logo_path.exists():
        print(f"❌ لوگو پیدا نشد: {logo_path}")
        print("💡 لطفاً لوگو رو در پوشه fonts/ با اسم logo.png بذار")
        return

    with open(logo_path, "rb") as f:
        logo_bytes = f.read()

    b64 = base64.b64encode(logo_bytes).decode("utf-8")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(b64)

    print(f"✅ لوگو تبدیل شد")
    print(f"   حجم: {len(logo_bytes):,} بایت")
    print(f"   Base64: {len(b64):,} کاراکتر")
    print(f"   مسیر: {output_path}")


if __name__ == "__main__":
    main()