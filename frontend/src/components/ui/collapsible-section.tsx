"use client";

/**
 * CollapsibleSection — بخش کشویی مدرن با Framer Motion
 * ============================================================
 * 🔴 فاز ۱۴.۹.۵:
 *   • children فقط وقتی open=True رندر می‌شن (lazy)
 *   • با keepMounted، بعد از اولین باز شدن state حفظ می‌شه
 *   • انیمیشن نرم با Framer Motion
 *   • ذخیره state در localStorage (بین reload ها پایدار)
 */

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface CollapsibleSectionProps {
  id: string;
  title: string;
  icon?: string;
  subtitle?: string;
  accentColor?: string;
  defaultOpen?: boolean;
  persist?: boolean;
  /** 🔴 اگه true، children بعد از اولین باز شدن unmount نمی‌شن */
  keepMounted?: boolean;
  className?: string;
  children: React.ReactNode;
}

const STORAGE_PREFIX = "collapsible:";

export function CollapsibleSection({
  id,
  title,
  icon,
  subtitle,
  accentColor = "#d6ad60",
  defaultOpen = false,
  persist = true,
  keepMounted = true,
  className,
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState<boolean>(defaultOpen);
  const [hasOpenedOnce, setHasOpenedOnce] = useState<boolean>(defaultOpen);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    if (!persist) return;
    try {
      const stored = localStorage.getItem(`${STORAGE_PREFIX}${id}`);
      if (stored !== null) {
        const wasOpen = stored === "1";
        setIsOpen(wasOpen);
        if (wasOpen) setHasOpenedOnce(true);
      }
    } catch {
      // silent
    }
  }, [id, persist]);

  const toggle = () => {
    const next = !isOpen;
    setIsOpen(next);
    if (next) setHasOpenedOnce(true);
    if (persist) {
      try {
        localStorage.setItem(`${STORAGE_PREFIX}${id}`, next ? "1" : "0");
      } catch {
        // silent
      }
    }
  };

  const shouldRenderChildren = hasOpenedOnce || isOpen || !keepMounted;

  return (
    <Card
      className={cn(
        "overflow-hidden border transition-colors duration-300",
        className
      )}
      style={{
        borderColor: isOpen ? `${accentColor}55` : undefined,
      }}
    >
      <CardHeader
        className="cursor-pointer select-none py-3 px-4 transition-colors hover:bg-muted/20"
        onClick={toggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggle();
          }
        }}
        aria-expanded={isOpen}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {icon && (
              <span
                className="text-lg shrink-0"
                style={{ filter: isOpen ? "none" : "grayscale(0.3)" }}
              >
                {icon}
              </span>
            )}
            <div className="min-w-0">
              <h3
                className="text-sm font-bold font-display truncate"
                style={{ color: isOpen ? accentColor : undefined }}
              >
                {title}
              </h3>
              {subtitle && (
                <p className="text-[10px] text-muted-foreground truncate">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          <motion.div
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="shrink-0 rounded-full p-1"
            style={{
              backgroundColor: isOpen ? `${accentColor}22` : "transparent",
            }}
          >
            <ChevronDown
              className="h-4 w-4 transition-colors"
              style={{ color: isOpen ? accentColor : undefined }}
            />
          </motion.div>
        </div>
      </CardHeader>

      {isMounted && shouldRenderChildren && (
        <motion.div
          key="content"
          initial={false}
          animate={{
            height: isOpen ? "auto" : 0,
            opacity: isOpen ? 1 : 0,
          }}
          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
          style={{ overflow: "hidden" }}
        >
          <CardContent className="px-4 pb-4 pt-1">{children}</CardContent>
        </motion.div>
      )}
    </Card>
  );
}