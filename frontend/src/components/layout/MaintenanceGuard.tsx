"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

export function MaintenanceGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const check = async () => {
      // ⬅️ مسیرهای مجاز (نباید چک بشن)
      if (
        pathname === "/maintenance" ||
        pathname.startsWith("/admin") ||
        pathname === "/login"
      ) {
        setIsChecking(false);
        return;
      }

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiUrl}/admin/maintenance/public`, { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          if (data.is_maintenance) {
            router.replace("/maintenance");
            return;
          }
        }
      } catch {}
      
      setIsChecking(false);
    };

    check();
  }, [pathname, router]);

  if (isChecking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-white">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#d6ad60]"></div>
      </div>
    );
  }

  return <>{children}</>;
}