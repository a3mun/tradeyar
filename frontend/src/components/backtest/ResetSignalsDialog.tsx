"use client";

/**
 * ResetSignalsDialog (نسخه ۳.۰ — امن‌شده)
 * ============================================================
 * ═══ تغییرات نسخه ۳.۰ ═══
 *   • رمز ثابت داخل کد فرانت حذف شد (قبلاً در مخزن عمومی و بسته‌ی JS
 *     دیده می‌شد و همان کلید واقعی سرور بود).
 *   • مدیر کلید `ADMIN_API_KEY` سرور را خودش وارد می‌کند و همان به‌صورت
 *     هدر X-API-Key فرستاده می‌شود. بررسی نهایی فقط در بک‌اند انجام می‌شود.
 */

import { useState } from "react";
import { AlertTriangle, Loader2, Trash2, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (deleted: number) => void;
}

export function ResetSignalsDialog({ open, onOpenChange, onSuccess }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open && (
        <ResetDialogBody
          onClose={() => onOpenChange(false)}
          onSuccess={onSuccess}
        />
      )}
    </Dialog>
  );
}

function ResetDialogBody({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (deleted: number) => void;
}) {
  const [passcode, setPasscode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const passOk = passcode.trim().length >= 8;

const handleReset = async () => {
  if (!passOk) {
    setError("کلید ادمین را وارد کنید");
    return;
  }

  setBusy(true);
  setError("");
  try {
    // 🔴 استفاده از api (axios) به جای fetch خام
    const res = await api.delete("/backtest/reset", {
      headers: {
        "X-API-Key": passcode.trim(),
      },
    });

    const deleted = res.data?.deleted ?? 0;
    onSuccess(deleted);
    onClose();
  } catch (e: unknown) {
    const err = e as {
      response?: { status?: number; data?: { detail?: string } };
    };
    const status = err.response?.status;
    const detail = err.response?.data?.detail;

    if (status === 403) {
      setError("رمز ادمین اشتباه است");
    } else if (status === 401) {
      setError("هدر X-API-Key ارسال نشد");
    } else if (status === 503) {
      setError("عملیات مدیریتی روی سرور فعال نیست");
    } else if (!err.response) {
      setError("ارتباط با سرور برقرار نشد");
    } else {
      setError(detail || `خطای غیرمنتظره (${status ?? "?"})`);
    }
  } finally {
    setBusy(false);
  }
};
  
  return (
    <DialogContent className="sm:max-w-sm">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-4 w-4" />
          ریست کامل سیگنال‌ها
        </DialogTitle>
        <DialogDescription>
          این عملیات <strong>برگشت‌ناپذیر</strong> است. کل تاریخچه‌ی
          سیگنال‌ها و آمار نرخ برد پاک می‌شود.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-3">
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-2.5 text-[11px]">
          <p className="font-medium text-destructive mb-1">
            قبل از ادامه مطمئن شو:
          </p>
          <ul className="list-disc space-y-0.5 pr-4 text-muted-foreground">
            <li>اگه می‌خوای داده‌ها رو نگه داری، اول JSON رو دانلود کن</li>
            <li>آمار نرخ برد صفر می‌شه</li>
          </ul>
        </div>

        <div>
          <label
            htmlFor="reset-passcode"
            className="mb-1 flex items-center gap-1 text-xs font-medium"
          >
            <KeyRound className="h-3 w-3" />
            کلید ادمین سرور
          </label>
          <Input
            id="reset-passcode"
            type="password"
            dir="ltr"
            autoComplete="off"
            value={passcode}
            onChange={(e) => {
              setPasscode(e.target.value);
              setError("");
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && passOk && !busy) {
                handleReset();
              }
            }}
            placeholder="••••••••••••"
            className={
              passcode && !passOk ? "border-destructive/50" : ""
            }
            disabled={busy}
            autoFocus
          />
        </div>

        {error && (
          <p
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive"
          >
            ⚠️ {error}
          </p>
        )}

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={busy}>
            انصراف
          </Button>
          <Button
            variant="destructive"
            onClick={handleReset}
            disabled={busy || !passOk}
            className="bg-destructive"
          >
            {busy ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                در حال حذف...
              </>
            ) : (
              <>
                <Trash2 className="h-3.5 w-3.5" />
                حذف همه
              </>
            )}
          </Button>
        </DialogFooter>
      </div>
    </DialogContent>
  );
}