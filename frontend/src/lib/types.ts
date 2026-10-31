/**
 * TypeScript types — هم‌راستا با Pydantic schemas (api/schemas.py)
 */

export type Source =
  | "nobitex"
  | "bitpin"
  | "wallex"
  | "tabdeal"
  | "tsetmc"
  | "ramzinex"
  | "toobit"
  | "bingx"
  | "bit24";

export type ActiveSource =
  | "nobitex"
  | "bitpin"
  | "wallex"
  | "tabdeal"
  | "tsetmc";

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
  source_requested?: string;
  source_used?: string;
  is_fallback?: boolean;
  timeframe: string;
  market_type: string;
  risk_profile: string;
  close_series?: number[];

  price: number;
  signal: string;
  direction: "long" | "short" | "neutral";
  confidence: number;
  confidence_tier: string;
  consensus: string;
  regime: string;
  session_label?: string;
  action_fa: string;
  explanation: string;

  sl: number | null;
  tp: number | null;
  rr: number | null;
  atr: number;
  atr_mult_sl: number;
  atr_mult_tp: number;

  rr_gross?: number | null;
  rr_net?: number | null;
  fee_pct?: number | null;
  fee_ratio?: number | null;
  breakeven_pct?: number | null;
  is_worthwhile?: boolean | null;
  timeframe_viable?: boolean | null;
  sl_tp_scaled?: boolean | null;
  scale_factor?: number | null;
  scale_reason?: string | null;
  original_sl?: number | null;
  original_tp?: number | null;
  rr_decay_pct?: number | null;
  execution_cost?: {
    fee_pct: number;
    spread_cost_pct: number;
    slippage_pct: number;
    total_pct: number;
  } | null;
  orderbook?: {
    imbalance: number;
    spread_pct: number;
    pressure_fa: string;
    best_bid: number;
    best_ask: number;
    wall?: { side: string; price: number; ratio: number } | null;
  } | null;

  support: number;
  resistance: number;
  pivots: Record<string, number>;
  swings: Record<string, unknown>;
  fibonacci: Record<string, unknown>;

  groups: Record<string, GroupData>;
  votes_long: number;
  votes_short: number;
  votes_neutral: number;

  reasons: string[];
  scenarios: Scenario[];
  traps: Record<string, TrapInfo>;
  traps_summary: Record<string, unknown>;
  divergence: { has_divergence: boolean; reason: string };
  multi_tf_info: string;
  multi_tf_ok: boolean;
  neutral_explain: { short?: string; long?: string; hint?: string };

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

// ═══ Quotes ═══
export interface QuoteResponse {
  ok: boolean;
  ticker: string;
  price: number;
  change_pct: number;
  source: string;
  available?: boolean;
}

// ═══ Sources ═══
export interface SourceInfo {
  value: Source;
  icon: string;
  label: string;
  full_name?: string;
  planned: boolean;
  active: boolean;
}

export interface SourcesResponse {
  ok: boolean;
  total: number;
  items: SourceInfo[];
  active_count: number;
  planned_count: number;
}

// ═══ Order Book ═══
export interface OrderBookLevel {
  price: number;
  quantity: number;
  orders?: number | null;
}

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
  imbalance?: number | null;
}

export interface OrderBookSummary {
  ok: boolean;
  ticker: string;
  source: string;
  imbalance: number;
  spread_pct: number;
  pressure_fa: string;
  has_bid_wall: boolean;
  has_ask_wall: boolean;
  wall?: OrderBookLevel & { side: string; ratio: number } | null;
  execution_cost?: {
    fee_pct: number;
    spread_cost_pct: number;
    slippage_pct: number;
    total_pct: number;
  };
}

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
  is_pre_breakout: boolean;
  is_pre_breakout_down: boolean; 
  pre_breakout_score: number;
  pre_breakout_bias: "up" | "down" | "neutral";
}

// ═══ Backtest ═══
export interface BacktestStats {
  total: number;
  pending: number;
  expired: number;
  
  // 🔴 فیلدهای جدید (فاز ۱۰.۱۰)
  tp_hits: number;
  sl_hits: number;
  timeout_wins: number;
  timeout_losses: number;
  timeout_flats: number;
  
  // معیارهای اصلی
  win_rate: number;
  direction_accuracy: number;
  
  // روند
  trend_correct: number;
  trend_wrong: number;
  trend_accuracy: number;
  
  // بقیه
  profit_factor: number;
  avg_rr: number;
  avg_rr_net: number;
  expectancy: number;
}

export interface BacktestResponse {
  ok: boolean;
  stats: BacktestStats;
  items: Record<string, unknown>[];
}

export interface SignalHistoryItem {
  id: number;
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
  rr: number | null;
  
  rr_gross?: number | null;
  rr_net?: number | null;
  fee_pct?: number | null;
  fee_ratio?: number | null;
  breakeven_pct?: number | null;
  is_worthwhile?: boolean | null;
  rr_decay_pct?: number | null;
  sl_tp_type: string | null;
  tf: string;
  market_type: string;
  risk_profile: string;
  result: "win" | "loss" | "expired" | null;
  result_time: string | null;
  exit_price: number | null;
  expired: boolean;
  
  expired_at_price?: number | null;
  expired_pnl_pct?: number | null;
  expired_bias?: "win" | "loss" | "flat" | null;
  
  had_trap: boolean;
  trap_type: string | null;
  trend_correct?: boolean | null;
  is_weak?: boolean;

  // 🔴 فیلدهای جدید (فاز ۱۰.۱۰)
  exit_reason?: "tp_hit" | "sl_hit" | "timeout" | null;
  trend_predicted_at_entry?: "bull" | "bear" | "flat" | null;
}

export interface BacktestHistoryResponse {
  ok: boolean;
  total: number;
  items: SignalHistoryItem[];
}

export interface BacktestRunResponse {
  ok: boolean;
  checked: number;
  updated: number;
  expired: number;
  win: number;
  loss: number;
  reason?: string;
}