
"use client";

import { useMemo, useState } from "react";
import {
  Calculator,
  TrendingUp,
  TrendingDown,
  Wallet,
  ShieldCheck,
  Target,
  Percent,
  RotateCcw,
  Info,
} from "lucide-react";

type Market = "stock" | "crypto_spot" | "crypto_futures" | "gold";
type Direction = "long" | "short";

type Calculation = {
  valid: boolean;
  error: string;
  riskBudget: number;
  stopDistance: number;
  stopPercent: number;
  rawQuantity: number;
  quantity: number;
  notional: number;
  margin: number;
  capitalRequired: number;
  actualLoss: number;
  actualRiskPercent: number;
  grossProfit: number;
  netProfit: number;
  rewardRisk: number;
  riskLimited: boolean;
  capitalLimited: boolean;
};

const nf = new Intl.NumberFormat("fa-IR", {
  maximumFractionDigits: 8,
});

function formatNumber(value: number, digits = 2) {
  if (!Number.isFinite(value)) return "—";

  return new Intl.NumberFormat("fa-IR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(value);
}

function normalizeNumber(value: string): number {
  const normalized = value
    .replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String("٠١٢٣٤٥٦٧٨٩".indexOf(d)))
    .replace(/٫/g, ".")
    .replace(/[٬،]/g, "")
    .replace(/,/g, "")
    .replace(/\s/g, "")
    .trim();

  if (!normalized || normalized === "." || normalized === "-") {
    return 0;
  }

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function floorToStep(value: number, step: number) {
  if (value <= 0 || step <= 0) return 0;

  const decimals = Math.min(
    12,
    Math.max(0, (String(step).split(".")[1] || "").length)
  );

  const roundedDown =
    Math.floor((value + step * 1e-10) / step) * step;

  return Number(roundedDown.toFixed(decimals));
}

function NumericField({
  label,
  value,
  onChange,
  suffix,
  step = "any",
  min = 0,
  placeholder = "۰",
  disabled = false,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  suffix?: string;
  step?: string;
  min?: number;
  placeholder?: string;
  disabled?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  const [draft, setDraft] = useState("");

  return (
    <label className="block min-w-0 space-y-1.5">
      <span className="block text-xs text-slate-400">{label}</span>

      <div
        className={[
          "flex h-11 items-center gap-2 rounded-xl border bg-[#07131e] px-3 transition",
          focused
            ? "border-cyan-400/50 ring-2 ring-cyan-400/10"
            : "border-white/[0.08]",
          disabled ? "opacity-50" : "",
        ].join(" ")}
      >
        <input
          type="text"
          inputMode="decimal"
          disabled={disabled}
          value={focused ? draft : value === 0 ? "" : String(value)}
          placeholder={placeholder}
          onFocus={() => {
            setFocused(true);
            setDraft(value === 0 ? "" : String(value));
          }}
          onBlur={() => {
            setFocused(false);
            onChange(Math.max(min, normalizeNumber(draft)));
          }}
          onChange={(event) => {
            const next = event.target.value;
            setDraft(next);
            onChange(Math.max(min, normalizeNumber(next)));
          }}
          className="w-full min-w-0 bg-transparent text-sm font-semibold text-white outline-none placeholder:text-slate-600 disabled:cursor-not-allowed"
          dir="ltr"
          step={step}
        />

        {suffix && (
          <span className="shrink-0 text-[11px] text-slate-500">
            {suffix}
          </span>
        )}
      </div>
    </label>
  );
}

function ResultItem({
  label,
  value,
  hint,
  accent = "text-white",
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: string;
}) {
  return (
    <div className="min-w-0 rounded-xl border border-white/[0.07] bg-[#081722] p-3">
      <div className="text-[11px] text-slate-400">{label}</div>
      <div
        className={`mt-1 break-words text-base font-bold tabular-nums ${accent}`}
        dir="ltr"
      >
        {value}
      </div>
      {hint && (
        <div className="mt-1 text-[10px] leading-5 text-slate-500">
          {hint}
        </div>
      )}
    </div>
  );
}

export function PositionSizeCalculatorPlaceholder() {
  const [market, setMarket] = useState<Market>("crypto_spot");
  const [direction, setDirection] = useState<Direction>("long");

  const [capital, setCapital] = useState(1000);
  const [riskPercent, setRiskPercent] = useState(1);

  const [entry, setEntry] = useState(100);
  const [stop, setStop] = useState(95);
  const [target, setTarget] = useState(110);

  const [leverage, setLeverage] = useState(1);
  const [contractSize, setContractSize] = useState(1);
  const [quantityStep, setQuantityStep] = useState(0.001);

  // همه نرخ‌ها درصد هستند؛ مثلاً 0.1 یعنی 0.1 درصد
  const [entryFee, setEntryFee] = useState(0.1);
  const [exitFee, setExitFee] = useState(0.1);
  const [sellTax, setSellTax] = useState(0);
  const [extraCost, setExtraCost] = useState(0);

  const isStock = market === "stock";
  const isSpot =
    market === "stock" || market === "crypto_spot";
  const isFutures = market === "crypto_futures";

  // طلا می‌تواند نقدی یا اهرمی محاسبه شود.
  const isLeveraged =
    market === "crypto_futures" || market === "gold";

  const marketName: Record<Market, string> = {
    stock: "بورس ایران",
    crypto_spot: "کریپتو اسپات",
    crypto_futures: "کریپتو فیوچرز",
    gold: "طلای جهانی (XAUUSD)",
  };

  const updateMarket = (next: Market) => {
    setMarket(next);
    setDirection("long");
    setLeverage(1);
    setContractSize(1);
    setQuantityStep(next === "stock" ? 1 : 0.001);
    setSellTax(0);
    setExtraCost(0);
  };

  const calculation = useMemo<Calculation>(() => {
    const invalid = (error: string): Calculation => ({
      valid: false,
      error,
      riskBudget: 0,
      stopDistance: 0,
      stopPercent: 0,
      rawQuantity: 0,
      quantity: 0,
      notional: 0,
      margin: 0,
      capitalRequired: 0,
      actualLoss: 0,
      actualRiskPercent: 0,
      grossProfit: 0,
      netProfit: 0,
      rewardRisk: 0,
      riskLimited: false,
      capitalLimited: false,
    });

    if (
      capital <= 0 ||
      riskPercent <= 0 ||
      riskPercent > 100 ||
      entry <= 0 ||
      stop <= 0 ||
      target <= 0 ||
      contractSize <= 0 ||
      quantityStep <= 0
    ) {
      return invalid("مقادیر سرمایه، قیمت‌ها و اندازه قرارداد باید معتبر و مثبت باشند.");
    }

    if (
      entryFee < 0 ||
      exitFee < 0 ||
      sellTax < 0 ||
      extraCost < 0
    ) {
      return invalid("هزینه‌ها نمی‌توانند منفی باشند.");
    }

    if (isLeveraged && (leverage < 1 || leverage > 125)) {
      return invalid("اهرم باید بین ۱ تا ۱۲۵ باشد.");
    }

    if (isSpot && direction === "short") {
      return invalid("فروش استقراضی در این بازار پشتیبانی نمی‌شود.");
    }

    const correctStop =
      direction === "long" ? stop < entry : stop > entry;

    const correctTarget =
      direction === "long" ? target > entry : target < entry;

    if (!correctStop) {
      return invalid(
        direction === "long"
          ? "در معامله خرید، حد ضرر باید پایین‌تر از قیمت ورود باشد."
          : "در معامله فروش، حد ضرر باید بالاتر از قیمت ورود باشد."
      );
    }

    if (!correctTarget) {
      return invalid(
        direction === "long"
          ? "در معامله خرید، حد سود باید بالاتر از قیمت ورود باشد."
          : "در معامله فروش، حد سود باید پایین‌تر از قیمت ورود باشد."
      );
    }

    const riskBudget = capital * (riskPercent / 100);
    const multiplier = contractSize;

    const entryNotionalPerUnit = entry * multiplier;
    const stopNotionalPerUnit = stop * multiplier;
    const targetNotionalPerUnit = target * multiplier;

    const entryFeeRate = entryFee / 100;
    const exitFeeRate = exitFee / 100;
    const taxRate = isStock ? sellTax / 100 : 0;
    const extraCostRate = extraCost / 100;

    const stopDistance = Math.abs(entry - stop);
    const targetDistance = Math.abs(target - entry);

    const stopGrossPerUnit = stopDistance * multiplier;
    const targetGrossPerUnit = targetDistance * multiplier;

    const stopCostsPerUnit =
      entryNotionalPerUnit * entryFeeRate +
      stopNotionalPerUnit * (exitFeeRate + taxRate) +
      entryNotionalPerUnit * extraCostRate;

    const targetCostsPerUnit =
      entryNotionalPerUnit * entryFeeRate +
      targetNotionalPerUnit * (exitFeeRate + taxRate) +
      entryNotionalPerUnit * extraCostRate;

    const lossPerUnit =
      stopGrossPerUnit + stopCostsPerUnit;

    const netProfitPerUnit =
      targetGrossPerUnit - targetCostsPerUnit;

    if (lossPerUnit <= 0 || !Number.isFinite(lossPerUnit)) {
      return invalid("محاسبه زیان هر واحد معتبر نیست.");
    }

    // سقف حجم بر اساس ریسک انتخاب‌شده
    const riskBasedQuantity = riskBudget / lossPerUnit;

    // سقف حجم بر اساس سرمایه
    // در حالت اهرمی، هزینه‌های دو سمت نیز به‌صورت محافظه‌کارانه
    // در سرمایه موردنیاز منظور می‌شوند.
    const capitalPerUnit = isLeveraged
      ? entryNotionalPerUnit *
        (
          1 / leverage +
          entryFeeRate +
          exitFeeRate +
          taxRate +
          extraCostRate
        )
      : entryNotionalPerUnit * (1 + entryFeeRate);

    if (capitalPerUnit <= 0) {
      return invalid("محاسبه سرمایه موردنیاز معتبر نیست.");
    }

    const capitalBasedQuantity = capital / capitalPerUnit;

    const rawQuantity = Math.min(
      riskBasedQuantity,
      capitalBasedQuantity
    );

    const quantity = floorToStep(rawQuantity, quantityStep);

    if (quantity <= 0) {
      return {
        ...invalid(
          "با سرمایه و گام حجم انتخاب‌شده، حجم قابل معامله به حداقل مجاز نمی‌رسد."
        ),
        riskBudget,
        stopDistance,
        stopPercent: (stopDistance / entry) * 100,
        rawQuantity,
      };
    }

    const notional = quantity * entryNotionalPerUnit;
    const margin = isLeveraged ? notional / leverage : notional;

    const capitalRequired = isLeveraged
      ? quantity * capitalPerUnit
      : notional + quantity * entryNotionalPerUnit * entryFeeRate;

    const actualLoss = quantity * lossPerUnit;
    const grossProfit = quantity * targetGrossPerUnit;
    const netProfit = quantity * netProfitPerUnit;

    const actualRiskPercent =
      capital > 0 ? (actualLoss / capital) * 100 : 0;

    const rewardRisk =
      actualLoss > 0 ? netProfit / actualLoss : 0;

    return {
      valid: true,
      error: "",
      riskBudget,
      stopDistance,
      stopPercent: (stopDistance / entry) * 100,
      rawQuantity,
      quantity,
      notional,
      margin,
      capitalRequired,
      actualLoss,
      actualRiskPercent,
      grossProfit,
      netProfit,
      rewardRisk,
      riskLimited: riskBasedQuantity <= capitalBasedQuantity,
      capitalLimited: capitalBasedQuantity < riskBasedQuantity,
    };
  }, [
    market,
    direction,
    capital,
    riskPercent,
    entry,
    stop,
    target,
    leverage,
    contractSize,
    quantityStep,
    entryFee,
    exitFee,
    sellTax,
    extraCost,
    isLeveraged,
    isSpot,
  ]);

  const reset = () => {
    setMarket("crypto_spot");
    setDirection("long");
    setCapital(1000);
    setRiskPercent(1);
    setEntry(100);
    setStop(95);
    setTarget(110);
    setLeverage(1);
    setContractSize(1);
    setQuantityStep(0.001);
    setEntryFee(0.1);
    setExitFee(0.1);
    setSellTax(0);
    setExtraCost(0);
  };

  const marketOptions: {
    id: Market;
    label: string;
  }[] = [
    { id: "stock", label: "بورس ایران" },
    { id: "crypto_spot", label: "کریپتو اسپات" },
    { id: "crypto_futures", label: "فیوچرز" },
    { id: "gold", label: "طلای جهانی" },
  ];

  return (
    <div
      dir="rtl"
      className="relative overflow-hidden rounded-2xl border border-cyan-400/15 bg-gradient-to-br from-[#071722] via-[#06131e] to-[#08111d] p-3 sm:p-5"
    >
      <div className="pointer-events-none absolute -right-20 -top-20 h-48 w-48 rounded-full bg-cyan-400/[0.05] blur-3xl" />

      {/* Header */}
      <div className="relative mb-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-400/20 bg-cyan-400/10">
            <Calculator className="h-5 w-5 text-cyan-300" />
          </div>

          <div>
            <h3 className="text-sm font-bold text-white sm:text-base">
              ماشین‌حساب سود و ضرر
            </h3>
            <p className="mt-1 text-[10px] text-slate-500 sm:text-xs">
              محاسبه حجم معامله بر اساس ریسک و سرمایه
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={reset}
          className="flex h-9 shrink-0 items-center gap-1.5 rounded-lg border border-white/10 px-3 text-xs text-slate-400 transition hover:border-white/20 hover:bg-white/5 hover:text-white"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          بازنشانی
        </button>
      </div>

      {/* Market selector */}
      <div className="relative mb-4">
        <div className="mb-2 text-xs font-medium text-slate-400">
          بازار معاملاتی
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {marketOptions.map((item) => {
            const active = market === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => updateMarket(item.id)}
                className={[
                  "rounded-xl border px-2 py-3 text-xs font-semibold transition",
                  active
                    ? "border-cyan-400/40 bg-cyan-400/10 text-cyan-200 shadow-[0_0_18px_rgba(34,211,238,0.06)]"
                    : "border-white/[0.07] bg-[#091925] text-slate-400 hover:border-white/20 hover:text-white",
                ].join(" ")}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Direction */}
      <div className="mb-4">
        <div className="mb-2 text-xs font-medium text-slate-400">
          جهت معامله
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setDirection("long")}
            className={[
              "flex h-11 items-center justify-center gap-2 rounded-xl border text-sm font-bold transition",
              direction === "long"
                ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
                : "border-white/[0.07] bg-[#091925] text-slate-400 hover:text-white",
            ].join(" ")}
          >
            <TrendingUp className="h-4 w-4" />
            خرید / لانگ
          </button>

          <button
            type="button"
            disabled={isSpot}
            onClick={() => setDirection("short")}
            className={[
              "flex h-11 items-center justify-center gap-2 rounded-xl border text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-30",
              direction === "short"
                ? "border-rose-400/40 bg-rose-400/10 text-rose-300"
                : "border-white/[0.07] bg-[#091925] text-slate-400 hover:text-white",
            ].join(" ")}
          >
            <TrendingDown className="h-4 w-4" />
            فروش / شورت
          </button>
        </div>

        {isSpot && (
          <p className="mt-1.5 text-[10px] text-slate-500">
            در معاملات اسپات، فقط موقعیت خرید قابل محاسبه است.
          </p>
        )}
      </div>

      {/* Main inputs */}
      <div className="relative space-y-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Wallet className="h-4 w-4 text-cyan-300" />
            سرمایه و مدیریت ریسک
          </div>

          <div className="grid grid-cols-2 gap-3">
            <NumericField
              label="کل سرمایه"
              value={capital}
              onChange={setCapital}
              suffix="واحد حساب"
            />

            <NumericField
              label="ریسک هر معامله"
              value={riskPercent}
              onChange={setRiskPercent}
              suffix="%"
              min={0}
              step="0.1"
            />

            {isLeveraged && (
              <NumericField
                label="اهرم"
                value={leverage}
                onChange={setLeverage}
                suffix="X"
                min={1}
                step="1"
              />
            )}

            <NumericField
              label="ضریب اندازه قرارداد"
              value={contractSize}
              onChange={setContractSize}
              suffix="واحد"
              min={0}
            />
          </div>

          <p className="mt-2 text-[10px] leading-5 text-slate-500">
            ضریب قرارداد را مطابق مشخصات نماد یا قرارداد وارد کن. برای
            دارایی‌هایی که هر واحد سفارش برابر یک واحد دارایی است، مقدار ۱
            مناسب است.
          </p>
        </div>

        <div className="h-px bg-white/[0.06]" />

        {/* Prices */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Target className="h-4 w-4 text-cyan-300" />
            قیمت‌های معامله
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <NumericField
              label="قیمت ورود"
              value={entry}
              onChange={setEntry}
            />

            <NumericField
              label="حد ضرر"
              value={stop}
              onChange={setStop}
            />

            <NumericField
              label="حد سود"
              value={target}
              onChange={setTarget}
            />
          </div>
        </div>

        <div className="h-px bg-white/[0.06]" />

        {/* Fees */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Percent className="h-4 w-4 text-cyan-300" />
            کارمزد و هزینه‌ها
          </div>

          <div className="grid grid-cols-2 gap-3">
            <NumericField
              label="کارمزد ورود"
              value={entryFee}
              onChange={setEntryFee}
              suffix="%"
              step="0.001"
            />

            <NumericField
              label="کارمزد خروج"
              value={exitFee}
              onChange={setExitFee}
              suffix="%"
              step="0.001"
            />

            {isStock && (
              <NumericField
                label="مالیات فروش"
                value={sellTax}
                onChange={setSellTax}
                suffix="%"
                step="0.001"
              />
            )}

            {isFutures && (
              <NumericField
                label="هزینه تخمینی اضافه"
                value={extraCost}
                onChange={setExtraCost}
                suffix="%"
                step="0.001"
              />
            )}

            <NumericField
              label="گام مجاز حجم"
              value={quantityStep}
              onChange={setQuantityStep}
              min={0}
            />
          </div>

          <p className="mt-2 text-[10px] leading-5 text-slate-500">
            نرخ‌ها را دستی وارد کن؛ مثلاً ۰٫۱ یعنی ۰٫۱ درصد، نه ۱۰ درصد.
            هزینه اضافه در فیوچرز برای برآورد هزینه‌هایی مثل اسلیپیج و
            فاندینگ است و باید تخمینی وارد شود.
          </p>
        </div>
      </div>

      {/* Results */}
      <div className="relative mt-5 rounded-2xl border border-cyan-400/15 bg-[#06121c] p-3 sm:p-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-bold text-white">
            <ShieldCheck className="h-4 w-4 text-cyan-300" />
            نتیجه محاسبه
          </div>

          <span className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-2 py-1 text-[10px] text-slate-400">
            {marketName[market]}
          </span>
        </div>

        {!calculation.valid ? (
          <div className="rounded-xl border border-amber-400/20 bg-amber-400/[0.06] p-4 text-center">
            <Info className="mx-auto mb-2 h-5 w-5 text-amber-300" />
            <p className="text-xs leading-6 text-amber-200">
              {calculation.error}
            </p>
          </div>
        ) : (
          <>
            <div className="mb-3 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.06] p-4 text-center">
              <div className="text-xs text-slate-400">
                حجم پیشنهادی معامله
              </div>

              <div
                className="mt-2 break-all text-2xl font-black text-cyan-300 sm:text-3xl"
                dir="ltr"
              >
                {formatNumber(calculation.quantity, 8)}
              </div>

              <div className="mt-1 text-[10px] text-slate-500">
                حجم نهایی پس از اعمال محدودیت ریسک، سرمایه و گام مجاز
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <ResultItem
                label="مبلغ ریسک مجاز"
                value={formatNumber(calculation.riskBudget)}
                accent="text-amber-300"
              />

              <ResultItem
                label="زیان تخمینی تا حد ضرر"
                value={formatNumber(calculation.actualLoss)}
                accent="text-rose-300"
                hint={`${formatNumber(calculation.actualRiskPercent, 3)}٪ از سرمایه`}
              />

              <ResultItem
                label="ارزش کل پوزیشن"
                value={formatNumber(calculation.notional)}
                accent="text-white"
              />

              <ResultItem
                label={isLeveraged ? "مارجین تخمینی" : "سرمایه لازم برای ورود"}
                value={formatNumber(
                  isLeveraged
                    ? calculation.margin
                    : calculation.capitalRequired
                )}
                accent="text-cyan-300"
                hint={
                  isLeveraged
                    ? `با اهرم ${formatNumber(leverage, 2)}X`
                    : "با احتساب کارمزد ورود"
                }
              />

              <ResultItem
                label="سود ناخالص در حد سود"
                value={formatNumber(calculation.grossProfit)}
                accent="text-emerald-300"
              />

              <ResultItem
                label="سود خالص تخمینی"
                value={formatNumber(calculation.netProfit)}
                accent={
                  calculation.netProfit >= 0
                    ? "text-emerald-300"
                    : "text-rose-300"
                }
                hint="پس از کسر هزینه‌های واردشده"
              />

              <ResultItem
                label="فاصله حد ضرر"
                value={`${formatNumber(calculation.stopDistance)} (${formatNumber(calculation.stopPercent, 3)}٪)`}
              />

              <ResultItem
                label="نسبت سود خالص به زیان"
                value={
                  calculation.rewardRisk > 0
                    ? `${formatNumber(calculation.rewardRisk, 2)} : 1`
                    : "نامطلوب"
                }
                accent={
                  calculation.rewardRisk >= 1
                    ? "text-emerald-300"
                    : "text-amber-300"
                }
                hint="سود خالص تقسیم بر زیان تخمینی"
              />
            </div>

            <div className="mt-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <div className="mb-2 text-xs font-semibold text-slate-300">
                محدودیت اعمال‌شده روی حجم
              </div>

              <div className="flex flex-wrap gap-2 text-[10px]">
                <span
                  className={[
                    "rounded-lg px-2.5 py-1.5",
                    calculation.riskLimited
                      ? "bg-cyan-400/10 text-cyan-300"
                      : "bg-white/[0.05] text-slate-500",
                  ].join(" ")}
                >
                  {calculation.riskLimited
                    ? "حجم بر اساس سقف ریسک تعیین شد"
                    : "سقف ریسک محدودکننده نبود"}
                </span>

                <span
                  className={[
                    "rounded-lg px-2.5 py-1.5",
                    calculation.capitalLimited
                      ? "bg-amber-400/10 text-amber-300"
                      : "bg-white/[0.05] text-slate-500",
                  ].join(" ")}
                >
                  {calculation.capitalLimited
                    ? "حجم با سرمایه محدود شد"
                    : "سرمایه محدودکننده نبود"}
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Disclaimer */}
      <div className="relative mt-3 flex gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
        <p className="text-[10px] leading-6 text-slate-500">
          نتایج تخمینی هستند و بر اساس قیمت‌ها، ضریب قرارداد، کارمزدها و
          هزینه‌هایی که وارد کرده‌ای محاسبه می‌شوند. لغزش قیمت، گپ بازار،
          نقدشوندگی، تغییر نرخ کارمزد، فاندینگ واقعی و قوانین مارجین صرافی
          می‌توانند نتیجه واقعی را تغییر دهند. این ابزار قیمت لیکوییدشدن
          را محاسبه نمی‌کند و جایگزین بررسی مشخصات قرارداد و قوانین کارگزار
          نیست.
        </p>
      </div>
    </div>
  );
}
