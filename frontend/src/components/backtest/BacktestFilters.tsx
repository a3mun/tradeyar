"use client";

/**
 * BacktestFilters — فیلترهای مشترک راستی‌آزمایی
 * ============================================================
 * نسخه ۱.۰ · فاز ۷.۵
 *
 * ═══ چرا کامپوننت جدا؟ ═══
 *   • BacktestStats و SignalHistory هر دو به این فیلترها نیاز
 *     دارن. نگه‌داشتن توی BacktestPanel → یه بار تعریف،
 *     همه استفاده می‌کنن.
 *
 * ═══ فیلترها ═══
 *   • صرافی:  همه | نوبیتکس | بیت‌پین | والکس | تبدیل | بورس
 *   • پروفایل: همه | 🚀 جسورانه | 🛡 محتاطانه
 *   • زمان:   همه | ۷ روز | ۳۰ روز
 */

interface Props {
  source: string;
  onSourceChange: (s: string) => void;
  profile: string;
  onProfileChange: (p: string) => void;
  time: string;
  onTimeChange: (t: string) => void;
}

const SOURCE_TABS = [
  { key: "", label: "همه" },
  { key: "nobitex", label: "نوبیتکس" },
  { key: "bitpin", label: "بیت‌پین" },
  { key: "wallex", label: "والکس" },
  { key: "tabdeal", label: "تبدیل" },
  { key: "tsetmc", label: "بورس" },
];

const PROFILE_TABS = [
  {
    key: "",
    label: "همه",
    activeCls: "border-primary bg-primary/10 text-primary",
  },
  {
    key: "aggressive",
    label: "🚀 جسورانه",
    activeCls: "border-orange-500 bg-orange-500/10 text-orange-400",
  },
  {
    key: "conservative",
    label: "🛡 محتاطانه",
    activeCls: "border-green-500 bg-green-500/10 text-green-500",
  },
];

const TIME_TABS = [
  { key: "all", label: "همه" },
  { key: "7d", label: "۷ روز" },
  { key: "30d", label: "۳۰ روز" },
];

function TabButton({
  active,
  onClick,
  children,
  activeCls = "border-primary bg-primary/10 text-primary",
  size = "normal",
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  activeCls?: string;
  size?: "normal" | "small";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md border transition-all ${
        size === "small" ? "px-1.5 py-1 text-[9px]" : "px-2 py-1.5 text-[10px]"
      } font-medium ${
        active
          ? activeCls
          : "border-border text-muted-foreground hover:bg-muted/50"
      }`}
    >
      {children}
    </button>
  );
}

export function BacktestFilters({
  source,
  onSourceChange,
  profile,
  onProfileChange,
  time,
  onTimeChange,
}: Props) {
  return (
    <div className="space-y-2.5">
      {/* ═══ صرافی ═══ */}
      <div>
        <p className="mb-1 text-[9px] text-muted-foreground">صرافی</p>
        <div className="grid grid-cols-3 gap-1 sm:grid-cols-6">
          {SOURCE_TABS.map((t) => (
            <TabButton
              key={t.key || "all"}
              active={source === t.key}
              onClick={() => onSourceChange(t.key)}
            >
              {t.label}
            </TabButton>
          ))}
        </div>
      </div>

      {/* ═══ پروفایل ریسک ═══ */}
      <div>
        <p className="mb-1 text-[9px] text-muted-foreground">پروفایل ریسک</p>
        <div className="grid grid-cols-3 gap-1">
          {PROFILE_TABS.map((t) => (
            <TabButton
              key={t.key || "all"}
              active={profile === t.key}
              onClick={() => onProfileChange(t.key)}
              activeCls={t.activeCls}
            >
              {t.label}
            </TabButton>
          ))}
        </div>
      </div>

      {/* ═══ بازه‌ی زمانی ═══ */}
      <div>
        <p className="mb-1 text-[9px] text-muted-foreground">بازه</p>
        <div className="grid grid-cols-3 gap-1">
          {TIME_TABS.map((t) => (
            <TabButton
              key={t.key}
              active={time === t.key}
              onClick={() => onTimeChange(t.key)}
            >
              {t.label}
            </TabButton>
          ))}
        </div>
      </div>
    </div>
  );
}