"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Settings, Clock, RefreshCw } from "lucide-react";

export default function MaintenancePage() {
  const router = useRouter();

  // ⬅️ هر ۱۰ ثانیه چک کن اگه تعمیرات تموم شد، برو صفحه اصلی
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiUrl}/admin/maintenance/public`);
        if (res.ok) {
          const data = await res.json();
          if (!data.is_maintenance) {
            router.replace("/");
          }
        }
      } catch {}
    };

    const interval = setInterval(checkStatus, 10000); // هر ۱۰ ثانیه
    return () => clearInterval(interval);
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#07111f] text-white p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md text-center space-y-6 rounded-3xl border border-[#d6ad60]/20 bg-[#0d1b2d] p-10 shadow-2xl"
      >
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-[#d6ad60]/10">
          <Settings className="h-10 w-10 text-[#d6ad60] animate-spin" style={{ animationDuration: "4s" }} />
        </div>
        <h1 className="text-2xl font-bold">سایت در حال به‌روزرسانی است</h1>
        <p className="text-sm text-gray-400 leading-relaxed">
          ما در حال انجام به‌روزرسانی‌های ضروری هستیم تا تجربه بهتری برای شما فراهم کنیم.
          <br />
          لطفاً چند دقیقه دیگر دوباره سر بزنید.
        </p>
        <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
          <Clock className="h-4 w-4" /> زمان تقریبی: چند دقیقه
        </div>
        
        {/* ⬅️ دکمه تلاش مجدد */}
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 rounded-lg bg-[#d6ad60]/10 px-4 py-2 text-sm font-bold text-[#d6ad60] hover:bg-[#d6ad60]/20 transition-colors"
        >
          <RefreshCw className="h-4 w-4" /> تلاش مجدد
        </button>
        
        <div className="border-t border-white/10 pt-4 text-xs text-[#d6ad60]">
          تریدمون — دستیار هوشمند بازار
        </div>
      </motion.div>
    </main>
  );
}