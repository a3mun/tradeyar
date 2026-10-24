"use client";

// ⚠️ AuthGuard موقتاً غیرفعال شده تا اینماد ثبت شود
export function AuthGuard({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}