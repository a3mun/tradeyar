"use client";

export function EnamadLogo() {
  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <a
        referrerPolicy="origin"
        target="_blank"
        href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
        rel="noopener noreferrer"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          referrerPolicy="origin"
          src="https://trustseal.enamad.ir/logo.aspx?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
          alt="نماد اعتماد الکترونیکی"
          className="h-32 w-auto cursor-pointer object-contain"
        />
      </a>
      <span className="text-[10px] text-muted-foreground">نماد اعتماد الکترونیکی</span>
    </div>
  );
}