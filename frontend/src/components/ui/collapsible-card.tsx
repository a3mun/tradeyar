"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  title: ReactNode;
  badge?: ReactNode;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  keepCollapsibleOnDesktop?: boolean;
  /** 🔴 روی دسکتاپ (xl) همیشه باز — بدون قابلیت بستن */
  forceOpenOnDesktop?: boolean;
  pulse?: boolean;
  className?: string;
}

export function CollapsibleCard({
  title,
  badge,
  actions,
  children,
  defaultOpen = false,
  keepCollapsibleOnDesktop = false,
  forceOpenOnDesktop = false,
  pulse = false,
  className = "",
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const locked = !keepCollapsibleOnDesktop;
  // 🔴 روی دسکتاپ قفل (همیشه باز)
  const forceOpen = forceOpenOnDesktop && !locked;

  const chevronCls = open
    ? "rotate-180 border-primary bg-primary/20 text-primary"
    : pulse
      ? "border-orange-500/60 bg-orange-500/10 text-orange-500"
      : "border-primary/40 bg-primary/10 text-primary";

  const chevronStyle =
    !open && pulse
      ? { animation: "chevron-pulse 1.5s ease-in-out infinite" }
      : undefined;

  return (
    <Card className={className}>
      {pulse && (
        <style jsx global>{`
          @keyframes chevron-pulse {
            0%, 100% {
              box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.5);
            }
            50% {
              box-shadow: 0 0 0 6px rgba(249, 115, 22, 0);
            }
          }
        `}</style>
      )}

      <CardHeader className="p-0">
        <div className="flex w-full items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className={`flex min-w-0 flex-1 items-center justify-between gap-2 px-2.5 py-1 text-right transition-colors hover:bg-muted/30 ${
              locked || forceOpen
                ? "lg:pointer-events-none xl:pointer-events-none lg:hover:bg-transparent xl:hover:bg-transparent"
                : ""
            }`}
            aria-expanded={open}
            aria-disabled={locked || forceOpen}
          >
            <span className="flex min-w-0 flex-1 items-center gap-2">
              <CardTitle className="truncate text-[11px]">{title}</CardTitle>
              {badge}
            </span>

            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded border-2 transition-all duration-200 ${chevronCls} ${
                locked ? "lg:hidden" : ""
              } ${forceOpen ? "xl:hidden" : ""}`}
              style={chevronStyle}
              aria-hidden
            >
              <ChevronDown className="h-4 w-4" strokeWidth={2.5} />
            </span>
          </button>

          {actions && <div className="shrink-0 px-2">{actions}</div>}
        </div>
      </CardHeader>

      <div
        className={`${open ? "block" : "hidden"} ${locked ? "lg:block" : ""} ${
          forceOpen ? "xl:block" : ""
        }`}
      >
        <CardContent className="p-2 pt-0">{children}</CardContent>
      </div>
    </Card>
  );
}

export function CollapsibleSection({
  title,
  badge,
  children,
  defaultOpen = false,
  pulse = false,
}: {
  title: ReactNode;
  badge?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  pulse?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const chevronCls = open
    ? "rotate-180 border-primary bg-primary/20 text-primary"
    : pulse
      ? "border-orange-500/60 bg-orange-500/10 text-orange-500"
      : "border-primary/40 bg-primary/10 text-primary";

  const chevronStyle =
    !open && pulse
      ? { animation: "chevron-pulse 1.5s ease-in-out infinite" }
      : undefined;

  return (
    <div className="rounded-lg border border-border/50">
      {pulse && (
        <style jsx global>{`
          @keyframes chevron-pulse {
            0%, 100% {
              box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.5);
            }
            50% {
              box-shadow: 0 0 0 6px rgba(249, 115, 22, 0);
            }
          }
        `}</style>
      )}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-right transition-colors hover:bg-muted/30"
        aria-expanded={open}
      >
        <span className="flex min-w-0 flex-1 items-center gap-2 text-[11px] font-medium">
          {title}
          {badge}
        </span>
        <span
          className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-all ${chevronCls}`}
          style={chevronStyle}
          aria-hidden
        >
          <ChevronDown className="h-3 w-3" strokeWidth={2.5} />
        </span>
      </button>
      <div className={`${open ? "block" : "hidden"}`}>
        <div className="border-t border-border/40 p-2">{children}</div>
      </div>
    </div>
  );
}