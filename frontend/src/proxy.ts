// frontend/src/proxy.ts
// 🔴 فاز ۱۷.۹۲ — جایگزین middleware.ts (Next.js 16)
// ⚠️ توجه: توکن احراز هویت در localStorage ذخیره می‌شود (نه کوکی)،
//    بنابراین proxy (که سمت سرور اجرا می‌شود) نمی‌تواند آن را بخواند.
//    محافظت واقعی مسیرها توسط کامپوننت‌های فرانت و بک‌اند (401) انجام می‌شود.
//    این فایل فقط نقش هدایت کاربر لاگین‌کرده از /login به /dashboard را دارد.
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const token = request.cookies.get('trademun_token')?.value;
  const { pathname } = request.nextUrl;

  // اگه کاربر لاگین بود و توی صفحه لاگین بود، بفرستش داشبورد
  if (pathname === '/login' && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

// ⚠️ در Next.js 16، تنظیم runtime در proxy.ts پشتیبانی نمی‌شود.
// فقط matcher مجاز است.
export const config = {
  matcher: ['/', '/dashboard/:path*', '/admin/:path*', '/login'],
};