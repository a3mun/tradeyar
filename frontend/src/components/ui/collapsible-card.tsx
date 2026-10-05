"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  title: ReactNode;
  badge?: ReactNode;
  subtitle?: string;
  children: ReactNode;
  /** در موبایل پیش‌فرض باز باشه؟ */
  defaultOpen?: boolean;
  /** دسکتاپ هم کشویی بمونه؟ (فقط WatchlistCard) */
  keepCollapsibleOnDesktop?: boolean;
  className?: string;
}

export function CollapsibleCard({
  title,
  badge,
  subtitle,
  children,
  defaultOpen = false,
  keepCollapsibleOnDesktop = false,
  className = "",
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const locked = !keepCollapsibleOnDesktop;

  return (
    <Card className={className}>
      <CardHeader className="p-0">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className={`flex w-full items-center justify-between gap-2 p-2.5 text-right transition-colors hover:bg-muted/30 ${
            locked ? "lg:pointer-events-none lg:hover:bg-transparent" : ""
          }`}
          aria-expanded={open}
          aria-disabled={locked}
        >
          <span className="flex min-w-0 flex-1 items-center gap-2">
            <CardTitle className="truncate text-xs">{title}</CardTitle>
            {badge}
            {subtitle && !open && (
              <span
                className={`truncate text-[9px] text-muted-foreground ${
                  locked ? "lg:hidden" : ""
                }`}
              >
                · {subtitle}
              </span>
            )}
          </span>
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${
              open ? "rotate-180" : ""
            } ${locked ? "lg:hidden" : ""}`}
          />
        </button>
      </CardHeader>

      <div
        className={`${open ? "block" : "hidden"} ${locked ? "lg:block" : ""}`}
      >
        <CardContent className="p-3 pt-0">{children}</CardContent>
      </div>
    </Card>
  );
}

export function CollapsibleSection({
  title,
  badge,
  children,
  defaultOpen = false,
}: {
  title: ReactNode;
  badge?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-border/50">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 p-2.5 text-right transition-colors hover:bg-muted/30"
        aria-expanded={open}
      >
        <span className="flex min-w-0 flex-1 items-center gap-2 text-[11px] font-medium">
          {title}
          {badge}
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      <div className={`${open ? "block" : "hidden"}`}>
        <div className="border-t border-border/40 p-2.5">{children}</div>
      </div>
    </div>
  );
}