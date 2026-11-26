
"use client";

import { useEffect, useMemo, useState } from "react";
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
  TrendingUp as ChartIcon,
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

type StoredValues = {
  market: Market;
  direction: Direction;
  capital: number;
  riskPercent: number;
  entry: number;
  stop: number;
  target: number;
  leverage: number;
  contractSize: number;
  quantityStep: number;
  entryFee: number;
  exitFee: number;
  sellTax: number;
  extraCost: number;
};

const STORAGE_KEY = "compact-position-calculator-v1";

const DEFAULT_VALUES: StoredValues = {
  market: "crypto_spot",
  direction: "long",
  capital: 1000,
  riskPercent: 1,
  entry: 100,
  stop: 95,
  target: 110,
  leverage: 1,
  contractSize: 1,
  quantityStep: 0.001,
  entryFee: 0.1,
  exitFee: 0.1,
  sellTax: 0,
  extraCost: 0,
};

const GOLD = "#e7c477";
const GOLD_LIGHT = "#fff0bd";
const GOLD_DARK = "#b88a3b";
const CARD = "#051118";
const BACKGROUND = "#030712";

const goldGradient =
  "linear-gradient(110deg, #b88a3b 0%, #e7c477 48%, #fff0bd 100%)";

function formatNumber(value: number, digits = 2) {
  if (!Number.isFinite(value)) return "—";

  return new Intl.NumberFormat("fa-IR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(value);
}

function normalizeNumber(value: string): number {
  const normalized = value
    .replace(/[۰-۹]/g, (d) =>
      String("۰۱۲۳۴۵۶۷۸۹".indexOf(d))
    )
    .replace(/[٠-٩]/g, (d) =>
      String("٠١٢٣٤٥٦٧٨٩".indexOf(d))
    )
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
    <label className="block min-w-0">
      <span className="mb-1 block text-[10px] font-medium text-zinc-400">
        {label}
      </span>

      <div
        className={[
          "flex h-8 items-center gap-1 rounded-md border px-2 transition",
          "bg-[#051118]",
          focused
            ? "border-[#e7c477]/60 ring-1 ring-[#e7c477]/15"
            : "border-white/[0.07]",
          disabled ? "opacity-40" : "",
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
          className="w-full min-w-0 bg-transparent text-xs font-semibold text-zinc-100 outline-none placeholder:text-zinc-700"
          dir="ltr"
          aria-label={label}
          data-step={step}
        />

        {suffix && (
          <span className="shrink-0 text-[9px] text-zinc-500">
            {suffix}
          </span>
        )}
      </div>
    </label>
  );
}

function SectionTitle({
  icon: Icon,
  title,
}: {
  icon: React.ElementType;
  title: string;
}) {
  return (
    <div className="mb-2 flex items-center gap-1.5">
      <div
        className="flex h-6 w-6 items-center justify-center rounded-md"
        style={{
          background: "rgba(231,196,119,0.09)",
        }}
      >
        <Icon size={13} style={{ color: GOLD }} />
      </div>

      <h3 className="text-[11px] font-bold text-zinc-200">
        {title}
      </h3>
    </div>
  );
}

function ResultItem({
  label,
  value,
  hint,
  accent = "text-zinc-100",
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: string;
}) {
  return (
    <div className="min-w-0 rounded-md border border-white/[0.055] bg-[#051118] px-2 py-1.5">
      <div className="text-[9px] text-zinc-500">
        {label}
      </div>

      <div
        className={`mt-1 break-words text-xs font-bold tabular-nums ${accent}`}
        dir="ltr"
      >
        {value}
      </div>

      {hint && (
        <div className="mt-1 text-[9px] leading-3 text-zinc-500">
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

  const [entryFee, setEntryFee] = useState(0.1);
  const [exitFee, setExitFee] = useState(0.1);
  const [sellTax, setSellTax] = useState(0);
  const [extraCost, setExtraCost] = useState(0);

  const [hydrated, setHydrated] = useState(false);

  // بارگذاری مقادیر ذخیره‌شده
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);

      if (saved) {
        const data = JSON.parse(saved) as Partial<StoredValues>;

        const validNumber = (
          value: unknown,
          fallback: number
        ) =>
          typeof value === "number" && Number.isFinite(value)
            ? value
            : fallback;

        if (
          data.market === "stock" ||
          data.market === "crypto_spot" ||
          data.market === "crypto_futures" ||
          data.market === "gold"
        ) {
          setMarket(data.market);
        }

        if (data.direction === "long" || data.direction === "short") {
          setDirection(data.direction);
        }

        setCapital(validNumber(data.capital, DEFAULT_VALUES.capital));
        setRiskPercent(validNumber(data.riskPercent, DEFAULT_VALUES.riskPercent));
        setEntry(validNumber(data.entry, DEFAULT_VALUES.entry));
        setStop(validNumber(data.stop, DEFAULT_VALUES.stop));
        setTarget(validNumber(data.target, DEFAULT_VALUES.target));
        setLeverage(validNumber(data.leverage, DEFAULT_VALUES.leverage));
        setContractSize(validNumber(data.contractSize, DEFAULT_VALUES.contractSize));
        setQuantityStep(validNumber(data.quantityStep, DEFAULT_VALUES.quantityStep));
        setEntryFee(validNumber(data.entryFee, DEFAULT_VALUES.entryFee));
        setExitFee(validNumber(data.exitFee, DEFAULT_VALUES.exitFee));
        setSellTax(validNumber(data.sellTax, DEFAULT_VALUES.sellTax));
        setExtraCost(validNumber(data.extraCost, DEFAULT_VALUES.extraCost));
      }
    } catch {
      // استفاده از مقادیر پیش‌فرض
    }

    setHydrated(true);
  }, []);

  // ذخیره خودکار تغییرات
  useEffect(() => {
    if (!hydrated) return;

    const values: StoredValues = {
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
    };

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(values));
    } catch {
      // محاسبه بدون ذخیره‌سازی هم ادامه پیدا می‌کند.
    }
  }, [
    hydrated,
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
  ]);

  const isStock = market === "stock";

  const isSpot =
    market === "stock" || market === "crypto_spot";

  const isFutures = market === "crypto_futures";

  const isLeveraged =
    market === "crypto_futures" || market === "gold";

  const marketName: Record<Market, string> = {
    stock: "بورس ایران",
    crypto_spot: "کریپتو اسپات",
    crypto_futures: "کریپتو فیوچرز",
    gold: "طلای جهانی",
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
      return invalid(
        "مقادیر سرمایه، قیمت‌ها و اندازه قرارداد باید معتبر و مثبت باشند."
      );
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

    const riskBasedQuantity = riskBudget / lossPerUnit;

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

    const margin = isLeveraged
      ? notional / leverage
      : notional;

    const capitalRequired = isLeveraged
      ? quantity * capitalPerUnit
      : notional +
        quantity * entryNotionalPerUnit * entryFeeRate;

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
    isStock,
  ]);

  const reset = () => {
    setMarket(DEFAULT_VALUES.market);
    setDirection(DEFAULT_VALUES.direction);
    setCapital(DEFAULT_VALUES.capital);
    setRiskPercent(DEFAULT_VALUES.riskPercent);
    setEntry(DEFAULT_VALUES.entry);
    setStop(DEFAULT_VALUES.stop);
    setTarget(DEFAULT_VALUES.target);
    setLeverage(DEFAULT_VALUES.leverage);
    setContractSize(DEFAULT_VALUES.contractSize);
    setQuantityStep(DEFAULT_VALUES.quantityStep);
    setEntryFee(DEFAULT_VALUES.entryFee);
    setExitFee(DEFAULT_VALUES.exitFee);
    setSellTax(DEFAULT_VALUES.sellTax);
    setExtraCost(DEFAULT_VALUES.extraCost);
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
      className="relative mx-auto w-full max-w-2xl overflow-hidden rounded-xl border border-[#b88a3b]/20 p-2.5 text-zinc-100 shadow-2xl sm:rounded-2xl sm:p-3.5"
      style={{ background: BACKGROUND }}
    >
      {/* Header */}
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[#e7c477]/20"
            style={{ background: "rgba(231,196,119,0.09)" }}
          >
            <Calculator size={16} style={{ color: GOLD }} />
          </div>

          <div className="min-w-0">
            <h3 className="text-xs font-bold text-white sm:text-sm">
              ماشین‌حساب سود و ضرر
            </h3>
            <p className="mt-0.5 text-[9px] text-zinc-500">
              محاسبه حجم معامله و مدیریت ریسک
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={reset}
          className="flex h-8 shrink-0 items-center gap-1 rounded-md border border-white/[0.08] bg-[#051118] px-2 text-[10px] text-zinc-400 transition hover:border-[#e7c477]/40 hover:text-[#e7c477]"
        >
          <RotateCcw size={12} />
          بازنشانی
        </button>
      </div>

      {/* Market */}
      <section className="mb-3">
        <div className="mb-1.5 text-[10px] font-medium text-zinc-400">
          بازار معاملاتی
        </div>

        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
          {marketOptions.map((item) => {
            const active = market === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => updateMarket(item.id)}
                className={[
                  "min-h-8 rounded-md border px-2 py-1.5 text-[10px] font-semibold transition sm:text-[11px]",
                  active
                    ? "border-[#e7c477]/45 text-[#fff0bd]"
                    : "border-white/[0.06] bg-[#051118] text-zinc-400 hover:border-[#e7c477]/25 hover:text-zinc-200",
                ].join(" ")}
                style={active ? {
                  background: "linear-gradient(110deg, rgba(184,138,59,0.18), rgba(231,196,119,0.08))",
                } : undefined}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </section>

      {/* Direction */}
      <section className="mb-3">
        <div className="mb-1.5 text-[10px] font-medium text-zinc-400">
          جهت معامله
        </div>

        <div className="grid grid-cols-2 gap-1.5">
          <button
            type="button"
            onClick={() => setDirection("long")}
            className={[
              "flex h-8 items-center justify-center gap-1.5 rounded-md border text-[11px] font-bold transition",
              direction === "long"
                ? "border-emerald-500/30 bg-emerald-500/[0.08] text-emerald-300"
                : "border-white/[0.06] bg-[#051118] text-zinc-500 hover:text-zinc-200",
            ].join(" ")}
          >
            <TrendingUp size={13} />
            خرید / لانگ
          </button>

          <button
            type="button"
            disabled={isSpot}
            onClick={() => setDirection("short")}
            className={[
              "flex h-8 items-center justify-center gap-1.5 rounded-md border text-[11px] font-bold transition disabled:cursor-not-allowed disabled:opacity-30",
              direction === "short"
                ? "border-rose-500/30 bg-rose-500/[0.08] text-rose-300"
                : "border-white/[0.06] bg-[#051118] text-zinc-500 hover:text-zinc-200",
            ].join(" ")}
          >
            <TrendingDown size={13} />
            فروش / شورت
          </button>
        </div>

        {isSpot && (
          <p className="mt-1 text-[9px] text-zinc-600">
            در بازار اسپات فقط موقعیت خرید قابل محاسبه است.
          </p>
        )}
      </section>

      <div className="mb-3 h-px bg-white/[0.06]" />

      {/* Capital and Risk */}
      <section className="mb-3">
        <SectionTitle icon={Wallet} title="سرمایه و مدیریت ریسک" />

        <div className="grid grid-cols-2 gap-x-2 gap-y-2 sm:grid-cols-3">
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
          />
        </div>

        <p className="mt-1.5 text-[9px] leading-4 text-zinc-600">
          ضریب قرارداد را مطابق مشخصات نماد وارد کن. اگر هر واحد سفارش برابر یک واحد دارایی است، مقدار ۱ مناسب است.
        </p>
      </section>

      <div className="mb-3 h-px bg-white/[0.06]" />

      {/* Prices */}
      <section className="mb-3">
        <SectionTitle icon={Target} title="قیمت‌های معامله" />

        <div className="grid grid-cols-2 gap-x-2 gap-y-2 sm:grid-cols-3">
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
      </section>

      <div className="mb-3 h-px bg-white/[0.06]" />

      {/* Fees */}
      <section className="mb-3">
        <SectionTitle icon={Percent} title="کارمزد و هزینه‌ها" />

        <div className="grid grid-cols-2 gap-x-2 gap-y-2 sm:grid-cols-3">
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
          />
        </div>

        <p className="mt-1.5 text-[9px] leading-4 text-zinc-600">
          نرخ‌ها درصدی هستند؛ مثلاً ۰٫۱ یعنی ۰٫۱ درصد. هزینه اضافه در فیوچرز برای تخمین اسلیپیج و فاندینگ است.
        </p>
      </section>

      {/* Results */}
      <section
        className="mt-3 rounded-lg border border-[#b88a3b]/25 p-2.5"
        style={{
          background: "linear-gradient(145deg, #051118 0%, #030712 100%)",
        }}
      >
        <div className="mb-2 flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <div
              className="flex h-6 w-6 items-center justify-center rounded-md"
              style={{ background: "rgba(231,196,119,0.1)" }}
            >
              <ChartIcon size={13} style={{ color: GOLD }} />
            </div>

            <h3 className="text-xs font-bold text-zinc-100">
              نتیجه محاسبه
            </h3>
          </div>

          <span className="rounded-md border border-[#b88a3b]/20 bg-[#051118] px-2 py-1 text-[9px] text-[#e7c477]">
            {marketName[market]}
          </span>
        </div>

        {!calculation.valid ? (
          <div className="rounded-md border border-amber-500/20 bg-amber-500/[0.05] p-2.5 text-center">
            <Info
              size={16}
              className="mx-auto mb-1 text-amber-400"
            />
            <p className="text-[10px] leading-5 text-amber-200">
              {calculation.error}
            </p>
          </div>
        ) : (
          <>
            {/* Main quantity */}
            <div
              className="mb-2 rounded-lg border border-[#e7c477]/25 p-2.5 text-center"
              style={{
                background: "linear-gradient(110deg, rgba(184,138,59,0.13), rgba(231,196,119,0.045), rgba(255,240,189,0.08))",
              }}
            >
              <div className="text-[10px] text-zinc-400">
                حجم پیشنهادی معامله
              </div>

              <div
                className="mt-1 break-all bg-clip-text text-2xl font-black tracking-tight text-transparent sm:text-3xl"
                style={{
                  backgroundImage: goldGradient,
                  WebkitBackgroundClip: "text",
                }}
                dir="ltr"
              >
                {formatNumber(calculation.quantity, 8)}
              </div>

              <div className="mt-1 text-[9px] text-zinc-500">
                حجم نهایی بر اساس محدودیت ریسک و سرمایه
              </div>
            </div>

            {/* Result grid */}
            <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
              <ResultItem
                label="مبلغ ریسک مجاز"
                value={formatNumber(calculation.riskBudget)}
                accent="text-[#e7c477]"
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
              />

              <ResultItem
                label={isLeveraged ? "مارجین تخمینی" : "سرمایه لازم برای ورود"}
                value={formatNumber(
                  isLeveraged
                    ? calculation.margin
                    : calculation.capitalRequired
                )}
                accent="text-[#e7c477]"
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

            {/* Limit status */}
            <div className="mt-2 rounded-md border border-white/[0.06] bg-[#051118] p-2">
              <div className="mb-1.5 text-[10px] font-semibold text-zinc-300">
                محدودیت اعمال‌شده روی حجم
              </div>

              <div className="flex flex-wrap gap-1.5">
                <span
                  className={[
                    "rounded-md px-2 py-1 text-[9px]",
                    calculation.riskLimited
                      ? "bg-[#e7c477]/[0.10] text-[#e7c477]"
                      : "bg-white/[0.04] text-zinc-500",
                  ].join(" ")}
                >
                  {calculation.riskLimited
                    ? "حجم بر اساس سقف ریسک تعیین شد"
                    : "سقف ریسک محدودکننده نبود"}
                </span>

                <span
                  className={[
                    "rounded-md px-2 py-1 text-[9px]",
                    calculation.capitalLimited
                      ? "bg-amber-500/[0.08] text-amber-300"
                      : "bg-white/[0.04] text-zinc-500",
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
      </section>

      {/* Disclaimer */}
      <div className="mt-2 flex gap-2 rounded-md border border-white/[0.05] bg-[#051118] p-2">
        <Info
          size={13}
          className="mt-0.5 shrink-0 text-zinc-500"
        />

        <p className="text-[9px] leading-4 text-zinc-600">
          نتایج تخمینی هستند و بر اساس قیمت‌ها، ضریب قرارداد، کارمزدها و هزینه‌های واردشده محاسبه می‌شوند. لغزش قیمت، گپ بازار، نقدشوندگی، تغییر کارمزد، فاندینگ واقعی و قوانین مارجین می‌توانند نتیجه واقعی را تغییر دهند. این ابزار قیمت لیکوییدشدن را محاسبه نمی‌کند و جایگزین بررسی مشخصات قرارداد و قوانین کارگزار نیست.
        </p>
      </div>

      <div className="mt-2 flex items-center justify-center gap-1 text-[9px] text-zinc-600">
        <ShieldCheck size={11} style={{ color: GOLD_DARK }} />
        <span>
          مقادیر ورودی به‌صورت خودکار در مرورگر ذخیره می‌شوند
        </span>
      </div>
    </div>
  );
}
