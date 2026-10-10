/**
 * TypeScript types — هم‌راستا با Pydantic schemas (api/schemas.py)
 */

export type Source =
  | "nobitex"
  | "bitpin"
  | "wallex"
  | "tabdeal"
  | "tsetmc"
  // ─── 🔜 فاز ۷ (placeholder) ───
  | "ramzinex"
  | "toobit"
  | "bingx"
  | "bit24";

/** صرافی‌هایی که واقعاً کار می‌کنند */
export type ActiveSource =
  | "nobitex"
  | "bitpin"
  | "wallex"
  | "tabdeal"
  | "tsetmc";

/** صرافی‌های برنامه‌ریزی‌شده */
export type PlannedSource = "ramzinex" | "toobit" | "bingx" | "bit24";

export type MarketType = "spot" | "futures";
export type RiskProfile = "aggressive" | "conservative";

export type Timeframe =
  | "۱ دقیقه"
  | "۵ دقیقه"
  | "۱۵ دقیقه"
  | "۳۰ دقیقه"
  | "۱ ساعت"
  | "روزانه";

// ═══ Analyze ═══
export interface AnalyzeRequest {
  ticker: string;
  source: Source;
  timeframe: Timeframe;
  market_type: MarketType;
  risk_profile: RiskProfile;
  ticker_name?: string;
}

export interface AnalyzeResponse {
  ok: boolean;
  ticker: string;
  name: string;
  source: string;
  /**
   * صرافی‌ای که کاربر انتخاب کرده
   * (در پاسخ‌های قدیمی ممکن است نباشد)
   */
  source_requested?: string;
  /**
   * صرافی‌ای که دیتا **واقعاً** از آن آمده.
   * اگر با source_requested فرق کند، fallback زده شده.
   */
  source_used?: string;
  /** آیا fallback زده شده؟ */
  is_fallback?: boolean;
  timeframe: string;
  market_type: string;
  risk_profile: string;
  close_series?: number[];

  // ═══ تحلیل ═══
  price: number;
  signal: string;
  direction: "long" | "short" | "neutral";
  confidence: number;
  confidence_tier: string;
  consensus: string;
  regime: string;
  action_fa: string;
  explanation: string;

  // ═══ SL/TP ═══
  sl: number | null;
  tp: number | null;
  /** R:R خام (بدون کارمزد) — برای سازگاری */
  rr: number | null;
  atr: number;
  atr_mult_sl: number;
  atr_mult_tp: number;

  // ═══ کارمزد (نسخه ۱.۹) — R:R واقعی ═══
  /** R:R خام بدون کارمزد */
  rr_gross?: number | null;
  /** R:R **خالص** — بعد از کسر کارمزد رفت‌وبرگشتی */
  rr_net?: number | null;
  /** کارمزد رفت‌وبرگشتی صرافی به درصد (مثلاً ۰.۴) */
  fee_pct?: number | null;
  /** نسبت TP خام به کارمزد — زیر ۳ بی‌ارزش */
  fee_ratio?: number | null;
  /** حداقل حرکت لازم برای سربه‌سر (درصد) */
  breakeven_pct?: number | null;
  /** آیا این معامله بعد از هزینه ارزش دارد؟ (rr_net ≥ ۱.۰) */
  is_worthwhile?: boolean | null;
  /**
   * آیا این **تایم‌فریم** از نظر اقتصادی معامله‌پذیر است؟
   * (rr_net ≥ ۱.۳ — حاشیه‌ی امن)
   *
   * ⚠️ در TF کوتاه با کارمزد صرافی‌های ایرانی (۰.۴-۰.۶۵٪)
   *    اغلب `false` است. سیستم هشدار می‌دهد، سیگنال را پنهان
   *    نمی‌کند.
   */
  timeframe_viable?: boolean | null;
  /** آیا SL/TP برای پوشش هزینه بزرگ‌تر شد؟ */
  sl_tp_scaled?: boolean | null;
  /** ضریب بزرگ‌تر شدن SL/TP */
  scale_factor?: number | null;
  /** چرا SL/TP مقیاس‌دهی شد */
  scale_reason?: string | null;
  /** SL قبل از مقیاس‌دهی */
  original_sl?: number | null;
  /** TP قبل از مقیاس‌دهی */
  original_tp?: number | null;
  /** چند درصد از R:R را کارمزد خورده */
  rr_decay_pct?: number | null;
  /** تفکیک هزینه‌ی اجرا: کارمزد + اسپرد + اسلیپیج */
  execution_cost?: {
    fee_pct: number;
    spread_cost_pct: number;
    slippage_pct: number;
    total_pct: number;
  } | null;
  /** عمق بازار (نسخه ۱.۹) — فقط در مسیر غیر-کش */
  orderbook?: {
    imbalance: number;
    spread_pct: number;
    pressure_fa: string;
    best_bid: number;
    best_ask: number;
    wall?: { side: string; price: number; ratio: number } | null;
  } | null;

  // ═══ سطوح ═══
  support: number;
  resistance: number;
  pivots: Record<string, number>;
  swings: Record<string, unknown>;
  fibonacci: Record<string, unknown>;

  // ═══ گروه‌ها ═══
  groups: Record<string, GroupData>;
  votes_long: number;
  votes_short: number;
  votes_neutral: number;

  // ═══ متادیتا ═══
  reasons: string[];
  scenarios: Scenario[];
  traps: Record<string, TrapInfo>;
  traps_summary: Record<string, unknown>;
  divergence: { has_divergence: boolean; reason: string };
  multi_tf_info: string;
  multi_tf_ok: boolean;
  neutral_explain: { short?: string; long?: string; hint?: string };

  // ═══ extras ═══
  deep_analysis: string;
  checklist: ChecklistData;
  ai_export: string;
  fingerprint: string;

  timestamp: string;
}

export interface GroupData {
  vote: number;
  score: number;
  weight: number;
  strength: string;
  strength_fa: string;
  reasons: string[];
}

export interface Scenario {
  condition: string;
  action: string;
  probability: number;
  color: string;
  type: string;
  icon: string;
}

export interface TrapInfo {
  active: boolean;
  reason: string;
  severity: number;
}

// ═══ Checklist ═══
export interface ChecklistItem {
  group: string;
  label: string;
  icon: string;
  detail: string;
  reasons?: string[];
  score: number;
  weight: number;
  color: "green" | "red" | "yellow";
  vote?: number;
}

export interface ChecklistData {
  items: ChecklistItem[];
  percentage: number;
  final: string;
  final_color: "green" | "red" | "yellow";
}

// ═══ Fear & Greed ═══
export interface FearGreedResponse {
  ok: boolean;
  ticker: string;
  value: number;
  label: string;
  color: "red" | "yellow" | "green";
  icon: string;
}

// ═══ Symbols ═══
export interface SymbolItem {
  ticker: string;
  name: string;
  source: string;
  emoji?: string;
}

export interface SymbolsResponse {
  ok: boolean;
  total: number;
  items: SymbolItem[];
}

// ═══ Quotes (مقایسه قیمت) ═══
export interface QuoteResponse {
  ok: boolean;
  ticker: string;
  price: number;
  change_pct: number;
  source: string;
  /**
   * آیا این صرافی واقعاً این بازار را دارد؟
   *
   * ─── false یعنی ───
   *   • آبان‌تتر + جفت تتری (بازار USDT ندارد)
   *   • یا نماد روی آن صرافی لیست نشده
   *
   * ⚠️ این **خطای شبکه نیست** — محدودیت ساختاری است.
   *    در UI باید «—» نمایش داده شود، نه پیام خطا.
   */
  available?: boolean;
}

// ═══ Sources (صرافی‌ها) ═══
export interface SourceInfo {
  /** کلید صرافی: nobitex | bitpin | ... | bingx */
  value: Source;
  icon: string;
  /** نام کوتاه فارسی */
  label: string;
  /** نام کامل (مثلاً «آبان‌تتر (فقط قیمت)») */
  full_name?: string;
  /** 🔜 هنوز پیاده‌سازی نشده (فاز ۷) */
  planned: boolean;
  /** ✅ fetcher دارد */
  active: boolean;
}

export interface SourcesResponse {
  ok: boolean;
  total: number;
  items: SourceInfo[];
  active_count: number;
  planned_count: number;
}

// ═══ Order Book — 🔜 فاز ۶.۵ (placeholder) ═══
/**
 * یک سطح قیمت در عمق بازار.
 *
 * ⚠️ فعلاً هیچ endpointی این را برنمی‌گرداند
 *    (`GET /orderbook/{ticker}` → 501).
 */
export interface OrderBookLevel {
  price: number;
  quantity: number;
  /** تعداد سفارش در این سطح (اختیاری) */
  orders?: number | null;
}

/**
 * عمق بازار — قرارداد فاز ۶.۵.
 *
 * ═══ کاربرد در تحلیل ═══
 *   • `imbalance`  → نسبت حجم bids به asks (۰..۱)
 *                    بالای ۰.۵ = فشار خرید
 *   • `spread_pct` → هزینه‌ی واقعی ورود و خروج
 *   • دیوار سفارش  → سطحی با حجم غیرعادی
 */
export interface OrderBook {
  ok: boolean;
  ticker: string;
  source: string;
  timestamp: string;

  bids: OrderBookLevel[];
  asks: OrderBookLevel[];

  best_bid?: number | null;
  best_ask?: number | null;
  spread?: number | null;
  spread_pct?: number | null;
  /** 0..1 — بالای ۰.۵ فشار خرید، زیر ۰.۵ فشار فروش */
  imbalance?: number | null;
}

/** خلاصه‌ی عمق بازار برای نمایش سبک */
export interface OrderBookSummary {
  ok: boolean;
  ticker: string;
  source: string;
  imbalance: number;
  spread_pct: number;
  /** «فشار خرید» / «فشار فروش» / «متعادل» */
  pressure_fa: string;
  has_bid_wall: boolean;
  has_ask_wall: boolean;
  wall?: OrderBookLevel & { side: string; ratio: number } | null;
  /** هزینه‌ی واقعی معامله: کارمزد + اسپرد + اسلیپیج */
  execution_cost?: {
    fee_pct: number;
    spread_cost_pct: number;
    slippage_pct: number;
    total_pct: number;
  };
}

/** مقایسه‌ی عمق بازار بین صرافی‌ها */
export interface OrderBookCompareResponse {
  ok: boolean;
  ticker: string;
  total: number;
  items: {
    source: string;
    imbalance: number;
    spread_pct: number;
    pressure_fa: string;
    best_bid: number;
    best_ask: number;
  }[];
  /** │ null = داده کافی نبود · true = همه هم‌جهت · false = متناقض */
  sources_agree: boolean | null;
  spread_min_pct: number | null;
  spread_max_pct: number | null;
  imbalance_min: number | null;
  imbalance_max: number | null;
}

// ═══ Scan ═══
export interface ScanRequest {
  category:
    | "crypto"
    | "forex"
    | "us_stocks"
    | "commodities"
    | "indices"
    | "iran_stocks";
  timeframe: Timeframe;
  market_type: MarketType;
  risk_profile: RiskProfile;
  limit: number;
}

export interface ScanResponse {
  ok: boolean;
  category: string;
  timeframe: string;
  total: number;
  items: ScanItem[];
}

export interface ScanItem {
  ticker: string;
  name: string;
  price: number;
  signal: string;
  confidence: number;
  direction: string;
  // 🔴 فاز ۱۰.۳ — Pre-breakout
  is_pre_breakout: boolean;
  pre_breakout_score: number;
  pre_breakout_bias: "up" | "down" | "neutral";
}

// ═══ Backtest ═══
export interface BacktestStats {
  total: number;
  wins: number;
  losses: number;
  pending: number;
  expired: number;
  win_rate: number;
  profit_factor: number;
  avg_rr: number;
  avg_rr_net?: number;
  /** انتظار ریاضی بر پایه R (اگر بک‌اند بفرستد) */
  expectancy?: number;
  // ═══ پیش‌بینی روند (نسخه ۳.۰) ═══
  trend_correct?: number;
  trend_wrong?: number;
  trend_accuracy?: number;
  expired_win?: number;
  expired_loss?: number;
  expired_flat?: number;
}

export interface BacktestResponse {
  ok: boolean;
  stats: BacktestStats;
  items: Record<string, unknown>[];
}

/**
 * یک سیگنال در تاریخچه‌ی راستی‌آزمایی
 * ─── هم‌راستا با api/routers/backtest.py:backtest_history ───
 */
export interface SignalHistoryItem {
  id: number;
  /** ISO با timezone — مثلاً "2026-10-03T12:30:00+00:00" */
  timestamp: string;
  ticker: string;
  name: string;
  source: string;
  signal: string;
  direction: "long" | "short" | "neutral";
  confidence: number;
  consensus: string;
  regime: string;
  price: number;
  sl: number | null;
  tp: number | null;
  /** R:R خام (بدون کارمزد) */
  rr: number | null;
  // ═══ کارمزد (نسخه ۱.۹) — R:R واقعی ═══
  /** R:R خام بدون کارمزد */
  rr_gross?: number | null;
  /** R:R **خالص** — بعد از کسر کارمزد رفت‌وبرگشتی */
  rr_net?: number | null;
  /** کارمزد رفت‌وبرگشتی صرافی به درصد */
  fee_pct?: number | null;
  /** نسبت TP خام به کارمزد — زیر ۳ بی‌ارزش */
  fee_ratio?: number | null;
  /** حداقل حرکت لازم برای سربه‌سر */
  breakeven_pct?: number | null;
  /** آیا این معامله بعد از کارمزد ارزش دارد؟ */
  is_worthwhile?: boolean | null;
  /** چند درصد از R:R را کارمزد خورده */
  rr_decay_pct?: number | null;
  sl_tp_type: string | null;
  tf: string;
  market_type: string;
  risk_profile: string;
  result: "win" | "loss" | "expired" | null;
  result_time: string | null;
  exit_price: number | null;
  expired: boolean;
  // ─── بسته شدن با مهلت (نسخه ۲.۰) ───
  expired_at_price?: number | null;
  expired_pnl_pct?: number | null;
  expired_bias?: "win" | "loss" | "flat" | null;
  had_trap: boolean;
  trap_type: string | null;
  trend_correct?: boolean | null;
  /** 🔴 فاز ۸.۲ — سیگنال ضعیف (در آمار win rate حساب نمی‌شود) */
  is_weak?: boolean;
}

export interface BacktestHistoryResponse {
  ok: boolean;
  total: number;
  items: SignalHistoryItem[];
}

/** پاسخ POST /backtest/run */
export interface BacktestRunResponse {
  ok: boolean;
  checked: number;
  updated: number;
  expired: number;
  win: number;
  loss: number;
  /** اگر اجرای قبلی هنوز تمام نشده باشد */
  reason?: string;
}