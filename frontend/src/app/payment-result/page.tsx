"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Clock, ArrowRight } from "lucide-react";

function PaymentResultContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status");
  const refId = searchParams.get("ref");

  const isSuccess = status === "success";

  return (
    <div className="min-h-screen bg-[#030712] text-white flex items-center justify-center p-4">
      <div className="max-w-md w-full rounded-2xl border border-white/10 bg-[#051118] p-6 text-center space-y-4">
        {isSuccess ? (
          <>
            <div className="mx-auto w-16 h-16 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
            <h1 className="text-xl font-bold text-green-400">پرداخت موفق</h1>
            <p className="text-sm text-gray-400 leading-relaxed">
              پرداخت شما با موفقیت تایید شد و اشتراک شما فعال شد.
            </p>
            {refId && (
              <p className="text-xs text-gray-500">
                شماره پیگیری: <span className="font-mono text-[#d6ad60]">{refId}</span>
              </p>
            )}
            <Link href="/dashboard">
              <Button className="w-full h-11 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#07111f] font-bold gap-2">
                رفتن به داشبورد <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </>
        ) : (
          <>
            <div className="mx-auto w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center">
              <XCircle className="h-8 w-8 text-red-500" />
            </div>
            <h1 className="text-xl font-bold text-red-400">پرداخت ناموفق</h1>
            <p className="text-sm text-gray-400 leading-relaxed">
              متأسفانه پرداخت شما تکمیل نشد. اگر مبلغی از حساب شما کسر شده، تا ۷۲ ساعت آینده به‌طور خودکار عودت داده می‌شود.
            </p>
            <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-3 text-xs text-orange-400">
              <p className="flex items-start gap-2">
                <Clock className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                در صورت عدم عودت، لطفاً تیکت ثبت کنید.
              </p>
            </div>
            <div className="flex justify-center">
            <Link href="/subscription" className="w-full">
                <Button className="w-full h-11 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#07111f] font-bold">
                تلاش مجدد
                </Button>
            </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function PaymentResultPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#030712] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#d6ad60]" /></div>}>
      <PaymentResultContent />
    </Suspense>
  );
}