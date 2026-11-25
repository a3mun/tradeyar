
"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle2,
  XCircle,
  Clock,
  ArrowLeft,
  RefreshCw,
  ShieldCheck,
  AlertCircle,
  Copy,
} from "lucide-react";

import { Button } from "@/components/ui/button";

function PaymentResultContent() {
  const searchParams = useSearchParams();

  const status = searchParams.get("status");
  const refId = searchParams.get("ref");

  const isSuccess = status === "success";
  const isFailed = status === "failed" || status === "error";
  const isUnknown = !isSuccess && !isFailed;

  const copyReference = () => {
    if (refId && navigator.clipboard) {
      navigator.clipboard.writeText(refId);
    }
  };

  return (
    <main
      dir="rtl"
      className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#030712] px-4 py-10 text-white"
    >
      {/* Background */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#d6ad60]/5 to-transparent" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#d6ad60]/5 blur-[100px]" />

      <div className="relative w-full max-w-md">
        <div className="rounded-3xl border border-white/10 bg-[#051118]/95 p-7 text-center shadow-2xl backdrop-blur-xl sm:p-9">

          {/* SUCCESS */}
          {isSuccess && (
            <>
              <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-green-500/20 bg-green-500/10">
                <CheckCircle2 className="h-10 w-10 text-green-400" />
              </div>

              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-green-500/20 bg-green-500/10 px-3 py-1.5 text-xs text-green-400">
                <ShieldCheck className="h-3.5 w-3.5" />
                پرداخت تأیید شده
              </div>

              <h1 className="text-2xl font-extrabold text-green-400">
                پرداخت موفق
              </h1>

              <p className="mt-4 text-sm leading-8 text-gray-400">
                پرداخت شما با موفقیت تأیید شده است. برای مشاهده وضعیت
                اشتراک و امکانات حساب کاربری خود وارد داشبورد شوید.
              </p>

              {refId && (
                <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="mb-2 text-xs text-gray-500">
                    شماره پیگیری پرداخت
                  </p>

                  <div className="flex items-center justify-center gap-2">
                    <span className="break-all font-mono text-sm font-bold tracking-wider text-[#d6ad60]">
                      {refId}
                    </span>

                    <button
                      type="button"
                      onClick={copyReference}
                      title="کپی شماره پیگیری"
                      className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}

              <Link href="/dashboard" className="mt-7 block">
                <Button className="h-12 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f] hover:opacity-90">
                  رفتن به داشبورد
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>

              <p className="mt-5 text-[11px] leading-6 text-gray-500">
                در صورت مشاهده‌نشدن اشتراک، لطفاً وضعیت حساب خود را
                در داشبورد بررسی کنید یا با پشتیبانی تماس بگیرید.
              </p>
            </>
          )}

          {/* FAILED */}
          {isFailed && (
            <>
              <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-red-500/20 bg-red-500/10">
                <XCircle className="h-10 w-10 text-red-400" />
              </div>

              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs text-red-400">
                <AlertCircle className="h-3.5 w-3.5" />
                پرداخت تأیید نشده
              </div>

              <h1 className="text-2xl font-extrabold text-red-400">
                پرداخت ناموفق
              </h1>

              <p className="mt-4 text-sm leading-8 text-gray-400">
                پرداخت شما تأیید نشده است. اگر مبلغی از حساب بانکی
                شما کسر شده، وضعیت تراکنش را از طریق بانک یا پشتیبانی
                درگاه پرداخت پیگیری کنید.
              </p>

              {refId && (
                <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="mb-2 text-xs text-gray-500">
                    شماره پیگیری
                  </p>

                  <span className="break-all font-mono text-sm text-[#d6ad60]">
                    {refId}
                  </span>
                </div>
              )}

              <div className="mt-6 rounded-xl border border-orange-500/20 bg-orange-500/5 p-4 text-right">
                <p className="flex items-start gap-2 text-xs leading-7 text-orange-300">
                  <Clock className="mt-1 h-4 w-4 shrink-0" />
                  در صورت کسر وجه و عدم بازگشت آن، با ارائه اطلاعات
                  تراکنش از طریق پشتیبانی پیگیری کنید.
                </p>
              </div>

              <Link href="/subscription" className="mt-7 block">
                <Button className="h-12 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f] hover:opacity-90">
                  <RefreshCw className="h-4 w-4" />
                  تلاش مجدد برای پرداخت
                </Button>
              </Link>

              <Link
                href="/dashboard/tickets"
                className="mt-4 inline-block text-xs text-gray-400 transition-colors hover:text-[#d6ad60]"
              >
                ارتباط با پشتیبانی
              </Link>
            </>
          )}

          {/* UNKNOWN */}
          {isUnknown && (
            <>
              <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-orange-500/20 bg-orange-500/10">
                <Clock className="h-10 w-10 text-orange-400" />
              </div>

              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-orange-500/20 bg-orange-500/10 px-3 py-1.5 text-xs text-orange-400">
                <AlertCircle className="h-3.5 w-3.5" />
                وضعیت نامشخص
              </div>

              <h1 className="text-2xl font-extrabold text-orange-400">
                نتیجه پرداخت مشخص نیست
              </h1>

              <p className="mt-4 text-sm leading-8 text-gray-400">
                اطلاعات کافی برای نمایش نتیجه پرداخت دریافت نشده است.
                لطفاً پیش از انجام پرداخت مجدد، وضعیت تراکنش و اشتراک
                خود را بررسی کنید تا از پرداخت تکراری جلوگیری شود.
              </p>

              <Link href="/dashboard" className="mt-7 block">
                <Button className="h-12 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f] hover:opacity-90">
                  بررسی حساب کاربری
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>

              <Link
                href="/contact"
                className="mt-4 inline-block text-xs text-gray-400 transition-colors hover:text-[#d6ad60]"
              >
                تماس با پشتیبانی
              </Link>
            </>
          )}

        </div>

        <p className="mt-6 text-center text-xs text-gray-600">
          تریدمون | ابزارهای هوشمند تحلیل بازار
        </p>
      </div>
    </main>
  );
}

function PaymentResultLoading() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#030712]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-12 w-12 animate-spin rounded-full border-2 border-[#d6ad60]/20 border-t-[#d6ad60]" />
        <p className="text-xs text-gray-400">
          در حال دریافت اطلاعات پرداخت...
        </p>
      </div>
    </main>
  );
}

export default function PaymentResultPage() {
  return (
    <Suspense fallback={<PaymentResultLoading />}>
      <PaymentResultContent />
    </Suspense>
  );
}
