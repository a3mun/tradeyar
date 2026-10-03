"""
setup_frontend.py
ساخت پروژه Next.js 14 + Tailwind + shadcn/ui + RTL
============================================================
اجرا: python setup_frontend.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"


def run(cmd: str, cwd: Path = None):
    """اجرای دستور shell با نمایش خروجی"""
    print(f"\n▶ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd or BASE_DIR,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print(f"❌ خطا در: {cmd}")
        sys.exit(1)


def check_node():
    """چک نصب Node.js با shutil.which"""
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")

    if not node_path or not npm_path:
        print("❌ Node.js نصب نیست یا در PATH نیست!")
        print("👉 PowerShell رو ببند و دوباره باز کن.")
        print(f"   node: {node_path}")
        print(f"   npm:  {npm_path}")
        sys.exit(1)

    # ─── نمایش نسخه ───
    node_ver = subprocess.run(
        "node --version", shell=True, capture_output=True, text=True
    ).stdout.strip()
    npm_ver = subprocess.run(
        "npm --version", shell=True, capture_output=True, text=True
    ).stdout.strip()

    print(f"✅ Node.js: {node_ver}")
    print(f"✅ npm:     {npm_ver}")


def main():
    print("=" * 60)
    print("ساخت پروژه Next.js 14 — Trademun Frontend")
    print("=" * 60)

    # ═══ چک Node ═══
    check_node()

    # ═══ ساخت پروژه Next.js ═══
    if FRONTEND_DIR.exists():
        print(f"\n📁 پوشه {FRONTEND_DIR.name} موجوده. حذف نمی‌کنم.")
        print("👉 اگه می‌خوای از صفر بسازی، دستی حذفش کن.")
        return

    run(
        "npx --yes create-next-app@latest frontend "
        "--typescript --tailwind --eslint --app "
        '--src-dir --import-alias "@/*" --use-npm --no-turbopack',
        cwd=BASE_DIR,
    )

    print("\n✅ پروژه Next.js ساخته شد!")

    # ═══ نصب پکیج‌های اضافی ═══
    packages = [
        "clsx tailwind-merge class-variance-authority lucide-react",
        "zustand",
        "recharts lightweight-charts",
        "framer-motion",
        "axios",
        "next-pwa",
        "date-fns-jalali",
    ]

    for pkg in packages:
        run(f"npm install {pkg}", cwd=FRONTEND_DIR)

    print("\n✅ همه پکیج‌ها نصب شدند!")

    # ═══ shadcn/ui ═══
    run(
        "npx --yes shadcn@latest init -d",
        cwd=FRONTEND_DIR,
    )

    components = [
        "button card badge tabs dialog dropdown-menu",
        "input select separator skeleton toast",
        "table tooltip switch slider",
    ]
    run(
        f"npx --yes shadcn@latest add {' '.join(components)}",
        cwd=FRONTEND_DIR,
    )

    print("\n✅ shadcn/ui نصب شد!")
    print("\n" + "=" * 60)
    print("🎯 قدم بعدی: منتظر پیام من برای ساختار فایل‌ها باش.")
    print("=" * 60)


if __name__ == "__main__":
    main()
