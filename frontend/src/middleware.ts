import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('trademun_token')?.value;
  const { pathname } = request.nextUrl;

  // مسیرهایی که نیاز به لاگین دارند
  const protectedPaths = ['/', '/dashboard', '/admin'];
  const isProtected = protectedPaths.includes(pathname) || pathname.startsWith('/dashboard') || pathname.startsWith('/admin');

  // اگه مسیر محافظت شده بود و توکن نبود، بفرست لاگین
  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // اگه کاربر لاگین بود و توی صفحه لاگین بود، بفرستش داشبورد
  if (pathname === '/login' && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/', '/dashboard/:path*', '/admin/:path*', '/login'],
};