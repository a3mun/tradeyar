"use client";

import { SettingsPanel } from "./SettingsPanel";

export function Sidebar() {
  return (
    <>
      {/* ═══ دسکتاپ: ستون ثابت ═══ */}
      <aside className="hidden lg:block lg:w-72 lg:shrink-0">
        <div className="sticky top-20 space-y-3">
          <SettingsPanel />
        </div>
      </aside>

      {/* 🔴 فاز ۱۰.۲ — FAB موبایل حذف شد (BottomNav جاش رو گرفت) */}
    </>
  );
}