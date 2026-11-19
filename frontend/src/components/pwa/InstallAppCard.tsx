"use client";

import { Download, CheckCircle2, Smartphone, Share } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePWAInstall } from "@/lib/hooks/usePWAInstall";

export function InstallAppCard() {
  const { canInstall, isInstalled, isIOS, isInstalling, triggerInstall } = usePWAInstall();

  // اگه نصب شده → پیام موفقیت
  if (isInstalled) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-green-500/20 bg-green-500/5 p-3">
        <div className="shrink-0 rounded-lg bg-green-500/15 p-2">
          <CheckCircle2 className="h-5 w-5 text-green-400" />
        </div>
        <div className="flex-1">
          <p className="text-xs font-bold text-green-400">اپلیکیشن نصب شده است</p>
          <p className="mt-0.5 text-[10px] text-gray-400">
            می‌تونی از صفحه‌ی خانه گوشی یا دسکتاپ بازش کنی.
          </p>
        </div>
      </div>
    );
  }

  // اگه iOS هست و نصب نشده → راهنمای دستی
  if (isIOS) {
    return (
      <div className="rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/5 p-3">
        <div className="flex items-start gap-3">
          <div className="shrink-0 rounded-lg bg-[#d6ad60]/15 p-2">
            <Smartphone className="h-5 w-5 text-[#d6ad60]" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-bold text-[#d6ad60]">نصب روی آیفون / آیپد</p>
            <ol className="mt-1.5 space-y-1 text-[10px] leading-relaxed text-gray-400">
              <li className="flex items-center gap-1.5">
                <span className="rounded-full bg-white/10 px-1.5 text-[9px] font-bold text-gray-300">۱</span>
                روی دکمه‌ی <Share className="inline h-3 w-3" /> (اشتراک‌گذاری) بزن
              </li>
              <li className="flex items-center gap-1.5">
                <span className="rounded-full bg-white/10 px-1.5 text-[9px] font-bold text-gray-300">۲</span>
                گزینه‌ی «افزودن به صفحه اصلی» رو انتخاب کن
              </li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  // اگه اندروید/کروم و می‌تونه نصب کنه → دکمه‌ی نصب
  if (canInstall) {
    return (
      <div className="rounded-xl border border-[#d6ad60]/20 bg-gradient-to-br from-[#14263e] to-[#0a1526] p-3">
        <div className="flex items-center gap-3">
          <div className="shrink-0 rounded-lg bg-[#d6ad60]/15 p-2">
            <Download className="h-5 w-5 text-[#d6ad60]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold text-white">نصب اپلیکیشن تریدمون</p>
            <p className="mt-0.5 text-[10px] text-gray-400">
              دسترسی سریع‌تر، بدون نیاز به باز کردن مرورگر.
            </p>
          </div>
          <Button
            onClick={triggerInstall}
            disabled={isInstalling}
            className="h-9 shrink-0 gap-1.5 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-3 text-[11px] font-bold text-[#07111f] hover:opacity-90"
          >
            {isInstalling ? "در حال نصب..." : "نصب"}
          </Button>
        </div>
      </div>
    );
  }

  // اگه هیچ‌کدوم (مثلاً دسکتاپ بدون پشتیبانی) → نشون نده
  return null;
}