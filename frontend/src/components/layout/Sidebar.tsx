"use client";

import { useState } from "react";
import { Settings as SettingsIcon } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { SettingsPanel } from "./SettingsPanel";

export function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* ═══ دسکتاپ: ستون ثابت ═══ */}
      <aside className="hidden lg:block lg:w-72 lg:shrink-0">
        <div className="sticky top-20 space-y-3">
          <SettingsPanel />
        </div>
      </aside>

      {/* ═══ موبایل: FAB ═══ */}
      <div className="lg:hidden">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger
            className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90"
            aria-label="تنظیمات"
          >
            <SettingsIcon className="h-5 w-5" />
          </SheetTrigger>
          <SheetContent side="right" className="w-80 overflow-y-auto">
            <div className="mt-6">
              <SettingsPanel />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}