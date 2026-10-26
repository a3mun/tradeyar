"use client";

import { useEffect, useState } from "react";
import { Heart, AlertTriangle, Shield, Globe, Send } from "lucide-react";

export function Footer() {
  const [showDisclaimer, setShowDisclaimer] = useState(false);

  useEffect(() => {
    const seen = localStorage.getItem("trademun_disclaimer_seen");
    if (!seen) {
      setTimeout(() => setShowDisclaimer(true), 1500);
    }
  }, []);

  const acceptDisclaimer = () => {
    localStorage.setItem("trademun_disclaimer_seen", "1");
    setShowDisclaimer(false);
  };

  const year = new Intl.DateTimeFormat("fa-IR", { year: "numeric" }).format(new Date());

  return (
    <>
      {showDisclaimer && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#07111f]/80 backdrop-blur-sm p-4" onClick={acceptDisclaimer}>
          <div className="max-w-md rounded-2xl border border-[#d6ad60]/30 bg-[#0d1b2d] p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-3">
              <div className="rounded-full bg-[#d6ad60]/15 p-2"><AlertTriangle className="h-5 w-5 text-[#d6ad60]" /></div>
              <h3 className="text-base font-bold text-white">توجه مهم</h3>
            </div>
            <div className="space-y-3 text-xs leading-relaxed text-gray-400">
              <p>📊 تحلیل‌ها و سیگنال‌های این اپ <strong className="text-white">صرفاً جنبه آموزشی</strong> دارن.</p>
              <p>🎯 تصمیم نهایی معامله، <strong className="text-white">با خودتونه</strong>.</p>
              <p>⚠️ <strong className="text-white">مسئولیت سود یا ضرر</strong> بر عهده‌ی شماست.</p>
              <p className="rounded-lg bg-white/5 p-3 text-[11px]">💡 این ابزار برای کمک به تحلیل شماست، نه جایگزین تصمیم شما. همیشه با مدیریت سرمایه و حد ضرر معامله کنید.</p>
            </div>
            <button onClick={acceptDisclaimer} className="mt-4 w-full rounded-lg bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-4 py-2.5 text-sm font-bold text-[#101827] transition-opacity hover:opacity-90">
              متوجه شدم
            </button>
          </div>
        </div>
      )}

      <footer className="mt-8 border-t border-[#d6ad60]/10 bg-[#07111f]/60">
        <div className="container mx-auto px-4 py-5 md:py-6">
          
          {/* موبایل */}
          <div className="flex flex-col items-center gap-4 text-center md:hidden">
            <img src="/icon-512.png" alt="Trademun" className="h-12 w-12 rounded-xl object-contain" />
            <div className="flex items-center gap-3 text-[11px]">
              <a href="https://trademun.ir" target="_blank" rel="noreferrer" className="flex items-center gap-1 text-gray-400 transition-colors hover:text-[#d6ad60]"><Globe className="h-3 w-3" /><span dir="ltr">trademun.ir</span></a>
              <span className="text-gray-600" aria-hidden="true">·</span>
              <a href="https://t.me/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-1 text-gray-400 transition-colors hover:text-[#d6ad60]"><Send className="h-3 w-3" /><span dir="ltr">t.me/trademun</span></a>
              <span className="text-gray-600" aria-hidden="true">·</span>
              <a href="https://ble.ir/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-1 text-gray-400 transition-colors hover:text-[#d6ad60]"><Send className="h-3 w-3" /><span dir="ltr">ble.ir/trademun</span></a>
            </div>
            <a referrerPolicy="origin" target="_blank" href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs" rel="noopener noreferrer" className="mt-2 block">
              <img referrerPolicy="origin" src="https://trustseal.enamad.ir/logo.aspx?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs" alt="نماد اعتماد الکترونیکی" className="h-24 w-auto mx-auto object-contain cursor-pointer" />
            </a>
            <p className="text-[10px] text-yellow-500/80 mt-2">⚠️ تحلیل‌ها صرفاً جنبه آموزشی دارن</p>
            <p className="flex items-center gap-1.5 text-[10px] text-gray-500"><span>© {year}</span><span aria-hidden="true">·</span><span>طراحی با</span><Heart className="h-3 w-3 fill-red-500 text-red-500" /><span>آسمون</span></p>
          </div>

          {/* دسکتاپ */}
          <div className="hidden md:block">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6 text-right">
              <div className="flex flex-row items-start gap-3">
                <img src="/icon-512.png" alt="Trademun" className="h-16 w-16 rounded-xl object-contain shrink-0" />
                <div className="flex-1 text-right">
                  <h3 className="text-lg font-bold text-white leading-none">تریدمون</h3>
                  <p className="text-[10px] text-[#d6ad60] mt-1">Trademun</p>
                  <div className="flex items-center gap-1.5 mt-2 justify-start">
                    <span className="rounded-md bg-[#d6ad60]/10 px-2 py-0.5 text-[9px] text-[#d6ad60]">v6.0</span>
                    <span className="text-[9px] text-gray-500">دستیار هوشمند بازار</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-bold mb-3 text-[#d6ad60]">اطلاعات</h4>
                <a href="https://trademun.ir" target="_blank" rel="noreferrer" className="flex items-center gap-2 text-[11px] text-gray-400 transition-colors hover:text-[#d6ad60] justify-start"><Globe className="h-3.5 w-3.5" /><span dir="ltr">trademun.ir</span></a>
                <a href="https://t.me/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-2 text-[11px] text-gray-400 transition-colors hover:text-[#d6ad60] justify-start"><Send className="h-3.5 w-3.5" /><span dir="ltr">t.me/trademun</span></a>
                <a href="https://ble.ir/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-2 text-[11px] text-gray-400 transition-colors hover:text-[#d6ad60] justify-start"><Send className="h-3.5 w-3.5" /><span dir="ltr">ble.ir/trademun</span></a>
                <p className="text-[10px] text-gray-500 pt-2">© {year} · همه حقوق محفوظ است</p>
              </div>

              <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-right">
                <div className="flex items-start gap-2">
                  <Shield className="h-4 w-4 shrink-0 mt-0.5 text-yellow-500" />
                  <div className="text-[10px] leading-relaxed text-yellow-500/90 text-right">
                    <strong className="block mb-1 text-yellow-500">⚠️ سلب مسئولیت</strong>
                    تحلیل‌ها صرفاً جنبه آموزشی دارن. مسئولیت سود یا ضرر بر عهده شماست.
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-center border-r border-[#d6ad60]/10 pr-4">
                <a referrerPolicy="origin" target="_blank" href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs" rel="noopener noreferrer" className="block transition-transform hover:scale-105">
                  <img referrerPolicy="origin" src="https://trustseal.enamad.ir/logo.aspx?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs" alt="نماد اعتماد الکترونیکی" className="h-28 w-auto object-contain cursor-pointer" />
                </a>
              </div>
            </div>

            <div className="border-t border-[#d6ad60]/10 pt-4">
              <div className="flex flex-row items-center justify-between gap-2 text-[11px] text-gray-400">
                <div className="flex items-center gap-1.5">
                  <span>طراحی و ساخت با</span>
                  <Heart className="h-3.5 w-3.5 fill-red-500 text-red-500 animate-pulse" />
                  <span>توسط</span>
                  <span className="font-bold text-[#d6ad60]">آسمون</span>
                </div>
                <p className="text-[10px] opacity-70">⚠️ معامله در بازارهای مالی ریسک بالایی داره</p>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}