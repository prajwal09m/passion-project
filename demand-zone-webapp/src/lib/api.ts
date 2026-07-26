/**
 * API client for the Demand Zone AI backend.
 * Supports both sync fetch and async progress-polling for on-demand analysis.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types (mirrors backend Pydantic models) ──────────────────────────

export type Recommendation = "BUY" | "SELL" | "HOLD";

export type IndicatorStatus = "bullish" | "bearish" | "neutral";

export interface IndicatorValue {
  value: number;
  status: IndicatorStatus;
  score: number;
}

export interface TechnicalIndicators {
  rsi: IndicatorValue;
  macd: IndicatorValue;
  adx: IndicatorValue;
  atr: IndicatorValue;
  vwap: IndicatorValue;
  ema20: IndicatorValue;
  ema50: IndicatorValue;
  ema200: IndicatorValue;
  volume: IndicatorValue;
  rvol: IndicatorValue;
  trend: IndicatorValue;
}

export interface ZoneInfo {
  side: "demand" | "supply";
  price: number;
  upper_bound: number;
  lower_bound: number;
  touches: number;
  age_days: number;
  strength: "High" | "Medium" | "Low";
  fresh: boolean;
  created_at: string;
  win_rate: number;
  avg_bounce_pct: number;
  avg_duration_days: number;
}

export interface FeatureImportance {
  name: string;
  contribution: number;
  description: string;
}

export interface ReasoningItem {
  text: string;
  weight: number;
}

export interface TradeSetup {
  entry: number;
  stop_loss: number;
  take_profit: number;
  risk_reward: number;
  position_pct: number;
  shares: number;
  capital: number;
  profit: number;
  loss: number;
  kelly_pct: number;
  risk_pct: number;
}

export interface OHLCVCandle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TickerInfo {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  industry: string;
  price: number;
  change: number;
  change_abs: number;
  open: number;
  high: number;
  low: number;
  prev_close: number;
  week_high_52: number;
  week_low_52: number;
  volume: number;
  avg_volume: number;
  market_cap: number;
  pe: number;
  eps: number;
  beta: number;
  dividend_yield: number;
  description: string;
  market_status: string;
}

export interface PredictResponse {
  symbol: string;
  ticker: TickerInfo;
  recommendation: Recommendation;
  confidence: number;
  expected_return: number;
  stop_loss_pct: number;
  holding_days: number;
  probability_target: number;
  probability_stop: number;
  entry: number;
  stop_loss_price: number;
  take_profit_price: number;
  zones: ZoneInfo[];
  technicals: TechnicalIndicators;
  feature_importance: FeatureImportance[];
  reasoning: ReasoningItem[];
  trade_setup: TradeSetup;
  model_name: string;
  model_metadata: Record<string, unknown>;
  candles: OHLCVCandle[];
  predicted_path: { time: string; value: number }[];
}

export interface TaskStatus {
  task_id: string;
  symbol: string;
  stage: string;
  progress: number;
  done: boolean;
  error?: string;
  result?: PredictResponse;
}

export type ProgressCallback = (stage: string, progress: number) => void;

// ─── API Functions ────────────────────────────────────────────────────

/**
 * Fetch a prediction for a ticker with progress polling.
 * The backend returns a task ID, then the client polls for progress.
 * On completion, the callback receives the full result.
 */
export async function fetchPredictionWithProgress(
  symbol: string,
  onProgress: ProgressCallback,
  signal?: AbortSignal,
): Promise<PredictResponse> {
  // 1. Start the async task
  const startRes = await fetch(`${API_BASE}/api/predict/async`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol }),
    signal,
  });

  if (!startRes.ok) {
    const err = await startRes.json().catch(() => ({ error: startRes.statusText }));
    throw new Error(err.error || `API error ${startRes.status}`);
  }

  const { task_id, cached } = await startRes.json();

  // If cached, fetch result immediately
  if (cached) {
    return fetchPrediction(symbol);
  }

  // 2. Poll for progress
  let lastStage = "";
  while (true) {
    if (signal?.aborted) throw new Error("Aborted");

    await sleep(400);

    const pollRes = await fetch(`${API_BASE}/api/predict/task/${task_id}`, { signal });
    if (!pollRes.ok) {
      throw new Error(`Polling failed: ${pollRes.status}`);
    }

    const status: TaskStatus = await pollRes.json();

    // Report progress
    if (status.stage !== lastStage) {
      lastStage = status.stage;
      onProgress(status.stage, status.progress);
    } else if (status.progress % 10 === 0) {
      onProgress(status.stage, status.progress);
    }

    // Done?
    if (status.done) {
      if (status.error) {
        throw new Error(status.error);
      }
      if (status.result) {
        return status.result;
      }
      throw new Error("Task completed but no result returned");
    }
  }
}

/**
 * Simple sync fetch (no progress tracking).
 */
export async function fetchPrediction(symbol: string): Promise<PredictResponse> {
  const res = await fetch(`${API_BASE}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `API error ${res.status}`);
  }

  return res.json();
}

/**
 * Check backend health.
 */
export async function checkHealth(): Promise<{ status: string; model_loaded: boolean; model_name: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
