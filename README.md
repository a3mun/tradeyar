# Trademun — دستیار هوشمند معاملات

## 📊 وضعیت پروژه — فاز ۸ ✅

- ✅ فاز ۱-۶: زیرساخت + تحلیل ۵ گروهی
- ✅ فاز ۷: WebSocket (quote ۱s، orderbook ۳s، signal ۳۰s)
- ✅ فاز ۸: UI Polish + تفکیک سیگنال قطعی/ضعیف

## 🚀 فاز بعدی: Deploy (فاز ۹)

- Backend → Render/Fly.io
- DB → Neon/Supabase (Postgres)
- Frontend → Cloudflare Pages
- Domain → trademun.ir

## 🛠 استک

- Backend: FastAPI + SQLModel + APScheduler
- Frontend: Next.js 16 + shadcn/ui + Tailwind
- DB: SQLite (local) → Postgres (production)

## 🏢 صرافی‌ها

✅ نوبیتکس، بیت‌پین، والکس، تبدیل، TSETMC

## 🧪 تست

```bash
python tools/test_full_system.py