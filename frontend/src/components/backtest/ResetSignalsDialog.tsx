"use client";

/**
 * ResetSignalsDialog — ساده‌شده (نسخه ۲.۰)
 * ============================================================
 * ═══ تغییرات نسخه ۲.۰ ═══
 *   • حذف مرحله‌ی دوگانه (RESET + کلید ادمین)
 *   • فقط یک رمز ساده: `38800`
 *   • چرا: کاربر (محمدمهدی) خودش ادمین است.
 *     رمز ساده کافیه که کاربر عادی ناخواسته ریست نکنه.
 *
 * ⚠️ توجه: این حفاظت «ظاهری» است، نه امنیتی.
 *    اگر اپ روی اینترنت عمومی میره، باید کلید ادمین سرور
 *    فعال باشه (`ADMIN_API_KEY` در .env). ولی رمز فرانت
 *    برای تجربه‌ی کاربری سریع کافیه.
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

// ═══ رمز ریست ═══
const RESET_PASSCODE = "38800";

// ═══ کلید ادمین سرور (اختیاری) ═══
// ─── اگه توی .env سرور ADMIN_API_KEY تنظیم شده، باید این هم ست بشه ───
// ─── اگه تنظیم نشده باشه، backend ریست رو بدون کلید قبول می‌کنه ───
const ADMIN_API_KEY_STORAGE = "trademun_admin_api_key";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (deleted: number) => void;
}

function readStoredAdminKey(): string {
  try {
    return localStorage.getItem(ADMIN_API_KEY_STORAGE) || "";
  } catch {
    return "";
  }
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

  const passOk = passcode.trim() === RESET_PASSCODE;

  const handleReset = async () => {
    if (!passOk) {
      setError("رمز اشتباه است");
      return;
    }

    setBusy(true);
    setError("");
    try {
      // ─── هدر ادمین (اگه توی localStorage بود) ───
      const adminKey = readStoredAdminKey();
      const headers: Record<string, string> = {};
      if (adminKey) headers["X-API-Key"] = adminKey;

      const res = await api.delete("/backtest/reset", { headers });
      onSuccess(res.data?.deleted ?? 0);
      onClose();
    } catch (e: unknown) {
      const err = e as {
        response?: { status?: number; data?: { detail?: string } };
      };
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      if (status === 403) {
        setError(
          "سرور کلید ادمین می‌خواد — با مدیر تماس بگیر (ADMIN_API_KEY تنظیم شده)"
        );
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
            رمز ریست
          </label>
          <Input
            id="reset-passcode"
            type="password"
            dir="ltr"
            autoComplete="off"
            inputMode="numeric"
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
            placeholder="•••••"
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