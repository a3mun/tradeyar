"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { 
  Copy, CheckCircle2, Terminal, AlertTriangle, Settings, BookOpen, 
  RotateCcw, X, ShieldAlert, Download, Database, FileText, Server
} from "lucide-react";

const SERVER_IP = "185.128.139.24";
const PROJECT_DIR = "/opt/trademun";

// ─── دکمه کپی ───
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button 
      onClick={handleCopy} 
      className="absolute top-2 right-2 rounded-md bg-black/50 p-1.5 text-gray-400 hover:bg-black/80 hover:text-[#d6ad60] transition-colors"
      title="کپی"
    >
      {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

// ─── باکس کد ───
function CodeBox({ children, title }: { children: string; title?: string }) {
  return (
    <div className="relative">
      {title && <div className="text-[11px] font-bold text-gray-500 mb-1.5">{title}</div>}
      <div className="relative">
        <pre className="bg-black/40 border border-white/10 rounded-lg p-3 pl-10 text-[11px] text-green-400 whitespace-pre-wrap break-all leading-relaxed dir-ltr" dir="ltr">
          {children}
        </pre>
        <CopyButton text={children} />
      </div>
    </div>
  );
}

// ─── تب ۱: راهنمای بازیابی ───
function RestoreTab({ backups }: { backups: any[] }) {
  const [selectedBackup, setSelectedBackup] = useState("");
  const [isOnServer, setIsOnServer] = useState(false);

  const scpCommand = `scp "C:\\Users\\YourName\\Downloads\\${selectedBackup || "YOUR_BACKUP.sql.gz"}" root@${SERVER_IP}:${PROJECT_DIR}/data/backups/`;
  const sshCommand = `ssh root@${SERVER_IP}`;
  const restoreCommand = `cd ${PROJECT_DIR} && gunzip -c data/backups/${selectedBackup || "YOUR_BACKUP.sql.gz"} | docker compose exec -T postgres psql -U trademun -d trademun`;
  const restartCommand = `cd ${PROJECT_DIR} && docker compose restart api`;

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-3 text-xs text-yellow-400 leading-relaxed">
        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
        <span>
          بازیابی دیتابیس سرور فقط از طریق SSH امکان‌پذیر است. این کار برای امنیت و جلوگیری از خطاهای Connection Pool انجام می‌شود.
        </span>
      </div>

      <div>
        <label className="text-xs font-bold text-gray-400 mb-1.5 block">۱. انتخاب فایل بک‌آپ (برای ساخت دستورات):</label>
        <select
          value={selectedBackup}
          onChange={(e) => setSelectedBackup(e.target.value)}
          className="w-full h-10 rounded-lg bg-black/30 border border-white/10 text-sm px-3 text-white focus:border-[#d6ad60] outline-none"
        >
          <option value="">-- انتخاب کنید --</option>
          {backups.map((b) => (
            <option key={b.name} value={b.name}>{b.name}</option>
          ))}
        </select>
        {selectedBackup && (
          <p className="text-[10px] text-green-400 mt-1.5">✅ فایل انتخاب شده: {selectedBackup}</p>
        )}
      </div>

      {/* ⬅️ چک‌باکس: فایل از قبل روی سرور هست؟ */}
      <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-3">
        <input 
          type="checkbox" 
          id="is-on-server" 
          checked={isOnServer} 
          onChange={(e) => setIsOnServer(e.target.checked)}
          className="accent-[#d6ad60] h-4 w-4" 
        />
        <label htmlFor="is-on-server" className="text-xs text-gray-300 cursor-pointer select-none">
          فایل از قبل روی سرور است (نیازی به آپلود مجدد نیست)
        </label>
      </div>

      <div className="space-y-4">
        {/* مرحله scp فقط اگه فایل روی سرور نیست نشون داده بشه */}
        {!isOnServer && (
          <div>
            <div className="flex items-center gap-2 text-sm font-bold text-[#d6ad60] mb-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#d6ad60]/20 text-[10px]">۲</span> 
              آپلود فایل به سرور (PowerShell لوکال)
            </div>
            <CodeBox>{scpCommand}</CodeBox>
          </div>
        )}

        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-[#d6ad60] mb-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#d6ad60]/20 text-[10px]">{isOnServer ? "۲" : "۳"}</span> 
            اتصال به سرور (SSH)
          </div>
          <CodeBox>{sshCommand}</CodeBox>
        </div>

        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-[#d6ad60] mb-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#d6ad60]/20 text-[10px]">{isOnServer ? "۳" : "۴"}</span> 
            بازیابی دیتابیس
          </div>
          <CodeBox>{restoreCommand}</CodeBox>
        </div>

        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-[#d6ad60] mb-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#d6ad60]/20 text-[10px]">{isOnServer ? "۴" : "۵"}</span> 
            ری‌استارت API
          </div>
          <CodeBox>{restartCommand}</CodeBox>
        </div>
      </div>
    </div>
  );
}


// ─── تب ۲: تست SSH ───
function SSHTestsTab() {
  return (
    <div className="space-y-4 text-sm text-gray-300">
      <p className="text-xs text-gray-400 leading-relaxed">دستورات زیر برای تست سلامت سرور و دیتابیس از طریق SSH است.</p>
      
      <CodeBox title="تست سلامت API">{`curl -s http://127.0.0.1:8000/health`}</CodeBox>
      <CodeBox title="تست سلامت سایت">{`curl -sI https://trademun.ir | head -3`}</CodeBox>
      <CodeBox title="وضعیت کانتینرها">{`cd ${PROJECT_DIR} && docker compose ps`}</CodeBox>
      <CodeBox title="لاگ API (۳۰ خط آخر)">{`cd ${PROJECT_DIR} && docker compose logs api --tail 30`}</CodeBox>
      <CodeBox title="لاگ Scheduler">{`cd ${PROJECT_DIR} && docker compose logs scheduler --tail 30`}</CodeBox>
      <CodeBox title="تعداد کاربران">{`cd ${PROJECT_DIR} && docker compose exec -T postgres psql -U trademun -d trademun -c "SELECT COUNT(*) FROM users;"`}</CodeBox>
      <CodeBox title="تعداد سیگنال‌ها">{`cd ${PROJECT_DIR} && docker compose exec -T postgres psql -U trademun -d trademun -c "SELECT COUNT(*) FROM signals_log;"`}</CodeBox>
    </div>
  );
}

// ─── تب ۳: اضطراری ───
function EmergencyTab() {
  return (
    <div className="space-y-4 text-sm text-gray-300">
      <div className="flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-xs text-red-400 leading-relaxed">
        <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
        <span>قبل از هر کار اضطراری، از دیتابیس بک‌آپ بگیرید!</span>
      </div>

      <CodeBox title="بک‌آپ فوری از دیتابیس">{`cd ${PROJECT_DIR} && docker compose exec -T postgres pg_dump -U trademun trademun > data/backups/emergency_$(date +%Y%m%d_%H%M%S).sql`}</CodeBox>
      <CodeBox title="ری‌استارت کامل سرویس‌ها">{`cd ${PROJECT_DIR} && docker compose restart`}</CodeBox>
      <CodeBox title="ری‌استارت داکر">{`systemctl restart docker`}</CodeBox>
      <CodeBox title="چک فضای دیسک">{`df -h && docker system df`}</CodeBox>
      <CodeBox title="پاکسازی کش بیلد">{`docker builder prune -af && docker image prune -f`}</CodeBox>
      <CodeBox title="حالت تعمیرات (دستی)">{`touch ${PROJECT_DIR}/data/maintenance.flag`}</CodeBox>
      <CodeBox title="خروج از حالت تعمیرات (دستی)">{`rm -f ${PROJECT_DIR}/data/maintenance.flag`}</CodeBox>
    </div>
  );
}

// ─── تب ۴: بهینه‌سازی ───
function OptimizationTab() {
  return (
    <div className="space-y-4 text-sm text-gray-300">
      <p className="text-xs text-gray-400 leading-relaxed">دستورات بهینه‌سازی سرور و بیلد (کاهش زمان و مصرف منابع).</p>
      
      <CodeBox title="بیلد مجدد (بدون کش)">{`cd ${PROJECT_DIR} && docker compose build --no-cache api frontend`}</CodeBox>
      <CodeBox title="بیلد فقط API">{`cd ${PROJECT_DIR} && docker compose build api`}</CodeBox>
      <CodeBox title="بیلد فقط Frontend">{`cd ${PROJECT_DIR} && docker compose build frontend`}</CodeBox>
      <CodeBox title="چک مصرف RAM و Swap">{`free -h`}</CodeBox>
      <CodeBox title="چک فضای دیسک">{`df -h && docker system df`}</CodeBox>
      <CodeBox title="پاکسازی کش داکر">{`docker builder prune -af`}</CodeBox>
      <CodeBox title="حذف ایمیج‌های قدیمی">{`docker image prune -f`}</CodeBox>
      
      <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-3 text-xs text-green-400 leading-relaxed">
        ✅ <strong>نکته:</strong> بعد از هر بیلد موفق، کش داکر را پاک کنید تا فضای دیسک آزاد شود.
      </div>
    </div>
  );
}

// ─── تب ۵: راهنمای مدیر ───
function AdminGuideTab() {
  return (
    <div className="space-y-5 text-sm text-gray-300 leading-relaxed">
      <div className="rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/5 p-3 text-xs text-[#d6ad60]">
        📚 راهنمای کامل استفاده از پنل مدیریت تریدمون
      </div>

      <section>
        <h4 className="font-bold text-[#d6ad60] mb-1.5 flex items-center gap-1.5">
          <FileText className="h-4 w-4" /> ورود به پنل مدیر
        </h4>
        <p>با شماره‌ی <code className="bg-black/30 px-1.5 py-0.5 rounded text-xs" dir="ltr">09129630901</code> و کد پیامک، وارد سایت شوید. از منوی «حساب کاربری» روی «پنل مدیریت» کلیک کنید.</p>
      </section>

      <section>
        <h4 className="font-bold text-[#d6ad60] mb-1.5 flex items-center gap-1.5">
          <Server className="h-4 w-4" /> مدیریت کاربران
        </h4>
        <p>در تب «کاربران»: افزودن کاربر، تغییر پلن، تنظیم تاریخ انقضا، حذف کاربر (با تایید دو مرحله‌ای اگر تیکت داشته باشد).</p>
      </section>

      <section>
        <h4 className="font-bold text-[#d6ad60] mb-1.5 flex items-center gap-1.5">
          <FileText className="h-4 w-4" /> درخواست‌های پرداخت
        </h4>
        <p>در تب «در انتظار»: درخواست‌های کارت‌به‌کارت را تایید یا رد کنید. با تایید، اشتراک به صورت خودکار فعال می‌شود.</p>
      </section>

      <section>
        <h4 className="font-bold text-[#d6ad60] mb-1.5 flex items-center gap-1.5">
          <BookOpen className="h-4 w-4" /> تیکت‌ها
        </h4>
        <p>در تب «تیکت‌ها»: مشاهده و پاسخ به تیکت‌های کاربران. تیکت‌های خوانده‌نشده با بج طلایی مشخص می‌شوند.</p>
      </section>

      <section>
        <h4 className="font-bold text-[#d6ad60] mb-1.5 flex items-center gap-1.5">
          <ShieldAlert className="h-4 w-4" /> حالت تعمیرات
        </h4>
        <p>در تب «ابزارها»: با فعال‌سازی حالت تعمیرات، سایت را برای کاربران غیرفعال کنید (برای دیپلوی یا بازیابی). فقط ادمین‌ها می‌توانند وارد شوند.</p>
      </section>

      <section>
        <h4 className="font-bold text-[#d6ad60] mb-1.5 flex items-center gap-1.5">
          <Database className="h-4 w-4" /> بک‌آپ و بازیابی
        </h4>
        <p>در تب «ابزارها»: دکمه «بک‌آپ جدید» فایل فشرده دیتابیس را دانلود می‌کند. برای بازیابی، از تب «راهنمای بازیابی» استفاده کنید.</p>
      </section>

      <section>
        <h4 className="font-bold text-[#d6ad60] mb-1.5 flex items-center gap-1.5">
          <Download className="h-4 w-4" /> خروجی اکسل
        </h4>
        <p>در تب «کاربران»: دکمه «اکسل» تمام اطلاعات کاربران را به فایل `.xlsx` صادر می‌کند.</p>
      </section>

      <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-3 text-xs text-yellow-400 leading-relaxed">
        ⚠️ <strong>نکات امنیتی:</strong> هرگز پسورد یا توکن را در چت یا سایت به اشتراک نگذارید. قبل از هر بیلد بزرگ، حالت تعمیرات را فعال کنید.
      </div>
    </div>
  );
}

// ─── کامپوننت اصلی ───
export function RestoreGuide({ backups }: { backups: any[] }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"restore" | "ssh" | "emergency" | "optimization" | "guide">("restore");

  const tabs = [
    { id: "restore", label: "راهنمای بازیابی", icon: RotateCcw },
    { id: "ssh", label: "تست SSH", icon: Terminal },
    { id: "emergency", label: "اضطراری", icon: AlertTriangle },
    { id: "optimization", label: "بهینه‌سازی", icon: Settings },
    { id: "guide", label: "راهنمای مدیر", icon: BookOpen },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <Button 
        variant="outline" 
        onClick={() => setIsOpen(true)}
        className="gap-2 border-[#d6ad60]/30 text-[#d6ad60] hover:bg-[#d6ad60]/10"
      >
        <BookOpen className="h-4 w-4" /> راهنمای مدیر
      </Button>
      
      <DialogContent className="max-w-2xl max-h-[90vh] p-0 bg-[#0d1b2d] border-white/10 text-white gap-0 [&>button]:hidden">
        
        {/* هدر با دکمه بستن اختصاصی */}
        <DialogHeader className="flex flex-row items-center justify-between p-4 sm:p-5 border-b border-white/10 space-y-0">
          <DialogTitle className="text-[#d6ad60] flex items-center gap-2 text-base sm:text-lg">
            <BookOpen className="h-5 w-5" /> راهنمای جامع مدیر
          </DialogTitle>
          <button 
            onClick={() => setIsOpen(false)} 
            className="rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </DialogHeader>

        {/* تب‌ها */}
        <div className="flex flex-wrap gap-1 border-b border-white/10 p-3">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-colors ${
                activeTab === tab.id 
                  ? "bg-[#d6ad60] text-[#101827]" 
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <tab.icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* محتوای تب */}
        <div className="p-4 sm:p-5 overflow-y-auto max-h-[60vh]">
          {activeTab === "restore" && <RestoreTab backups={backups} />}
          {activeTab === "ssh" && <SSHTestsTab />}
          {activeTab === "emergency" && <EmergencyTab />}
          {activeTab === "optimization" && <OptimizationTab />}
          {activeTab === "guide" && <AdminGuideTab />}
        </div>
      </DialogContent>
    </Dialog>
  );
}