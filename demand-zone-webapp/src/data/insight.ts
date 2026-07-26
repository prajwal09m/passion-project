// Static fixtures for the premium AI analysis page (/insight).
// Numbers are deterministic and intended to *look* like real model output,
// not to be quoted as such.

import { CHART_DATA, ZONES, DemandZone } from "./signals";

export type InsightTicker = {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  industry: string;
  price: number;
  change: number;
  changeAbs: number;
  open: number;
  high: number;
  low: number;
  prevClose: number;
  weekHigh52: number;
  weekLow52: number;
  volume: number;
  avgVolume: number;
  marketCap: number;     // in USD
  pe: number;
  eps: number;
  beta: number;
  dividendYield: number;
  description: string;
  marketStatus: "OPEN" | "PRE" | "POST" | "CLOSED";
};

export const INSIGHT_TICKERS: InsightTicker[] = [
  {
    symbol: "NVDA",
    name: "NVIDIA Corporation",
    exchange: "NASDAQ",
    sector: "Technology",
    industry: "Semiconductors",
    price: 924.79,
    change: 0.0143,
    changeAbs: 13.06,
    open: 911.73,
    high: 928.42,
    low: 909.50,
    prevClose: 911.73,
    weekHigh52: 974.00,
    weekLow52: 460.20,
    volume: 47_300_000,
    avgVolume: 51_200_000,
    marketCap: 2_280_000_000_000,
    pe: 73.4,
    eps: 12.60,
    beta: 1.65,
    dividendYield: 0.0003,
    description:
      "NVIDIA designs accelerated computing platforms, GPUs, and networking technologies used in gaming, professional visualization, data center, and automotive markets.",
    marketStatus: "OPEN",
  },
  {
    symbol: "AAPL",
    name: "Apple Inc.",
    exchange: "NASDAQ",
    sector: "Technology",
    industry: "Consumer Electronics",
    price: 218.36,
    change: 0.0091,
    changeAbs: 1.96,
    open: 216.40,
    high: 219.21,
    low: 215.85,
    prevClose: 216.40,
    weekHigh52: 237.49,
    weekLow52: 164.08,
    volume: 38_100_000,
    avgVolume: 56_400_000,
    marketCap: 3_320_000_000_000,
    pe: 33.1,
    eps: 6.59,
    beta: 1.25,
    dividendYield: 0.0047,
    description:
      "Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories. Services include App Store, iCloud, and Apple Music.",
    marketStatus: "OPEN",
  },
  {
    symbol: "TSLA",
    name: "Tesla, Inc.",
    exchange: "NASDAQ",
    sector: "Consumer Discretionary",
    industry: "Automobiles",
    price: 244.20,
    change: -0.0117,
    changeAbs: -2.90,
    open: 247.10,
    high: 248.50,
    low: 242.05,
    prevClose: 247.10,
    weekHigh52: 299.29,
    weekLow52: 138.80,
    volume: 89_300_000,
    avgVolume: 110_200_000,
    marketCap: 778_000_000_000,
    pe: 67.4,
    eps: 3.62,
    beta: 2.18,
    dividendYield: 0,
    description:
      "Tesla designs, manufactures, and sells electric vehicles, battery energy storage, and solar generation. Operates a global network of supercharger stations.",
    marketStatus: "OPEN",
  },
];

export type Timeframe = "1m" | "5m" | "15m" | "1H" | "4H" | "1D" | "1W";
export const TIMEFRAMES: Timeframe[] = ["1m", "5m", "15m", "1H", "4H", "1D", "1W"];

export type Recommendation = "BUY" | "SELL" | "HOLD";

export type TechnicalIndicator = {
  key: string;
  name: string;
  value: string;
  status: "bullish" | "bearish" | "neutral";
  score: number; // 0..100
  hint?: string;
};

export const TECHNICAL_INDICATORS: TechnicalIndicator[] = [
  { key: "rsi",       name: "RSI (14)",       value: "62.4",  status: "bullish",  score: 78, hint: "Recovering from oversold" },
  { key: "macd",      name: "MACD",           value: "+4.21", status: "bullish",  score: 82, hint: "Histogram expanding" },
  { key: "adx",       name: "ADX (14)",       value: "31.7",  status: "bullish",  score: 71, hint: "Strong trending regime" },
  { key: "atr",       name: "ATR (14)",       value: "12.4",  status: "neutral",  score: 55, hint: "Below-average volatility" },
  { key: "vwap",      name: "VWAP",           value: "$918.4",status: "bullish",  score: 76, hint: "Price above session VWAP" },
  { key: "ema20",     name: "EMA 20",         value: "$911.2",status: "bullish",  score: 80, hint: "Price above rising EMA" },
  { key: "ema50",     name: "EMA 50",         value: "$895.7",status: "bullish",  score: 74, hint: "Slope turning positive" },
  { key: "ema200",    name: "EMA 200",        value: "$752.3",status: "bullish",  score: 88, hint: "Strong long-term trend" },
  { key: "volume",    name: "Volume",         value: "47.3M", status: "neutral",  score: 60, hint: "Below 20-day average" },
  { key: "rvol",      name: "Relative Volume",value: "0.92x", status: "neutral",  score: 58, hint: "In-line with typical activity" },
  { key: "trend",     name: "Trend Score",    value: "91",    status: "bullish",  score: 91, hint: "Composite 0–100" },
];

export type FeatureContribution = {
  key: string;
  name: string;
  contribution: number; // 0..1
  description: string;
};

export const FEATURE_CONTRIBUTIONS: FeatureContribution[] = [
  { key: "demand_zone_strength",   name: "Demand Zone Strength",    contribution: 0.94, description: "Composite of base/width/freshness." },
  { key: "relative_volume",        name: "Relative Volume",         contribution: 0.84, description: "Current vs 20-day average." },
  { key: "trend_score",            name: "Trend Score",             contribution: 0.79, description: "EMA + ADX composite." },
  { key: "ema_alignment",          name: "EMA Alignment",           contribution: 0.72, description: "20/50/200 stacked bullish." },
  { key: "atr",                    name: "ATR",                     contribution: 0.61, description: "Volatility-adjusted range." },
  { key: "rsi",                    name: "RSI",                     contribution: 0.48, description: "14-period RSI slope." },
  { key: "macd",                   name: "MACD",                    contribution: 0.42, description: "Histogram momentum." },
  { key: "support_strength",       name: "Support Strength",        contribution: 0.36, description: "Historical touch density." },
  { key: "volume_delta",           name: "Volume Delta",            contribution: 0.31, description: "Buy vs sell pressure." },
  { key: "spread",                 name: "Spread",                  contribution: 0.24, description: "Effective bid/ask cost." },
];

export type ReasoningReason = {
  text: string;
  weight: number; // 0..1
};

export const AI_REASONS: ReasoningReason[] = [
  { text: "Strong demand zone with multiple rejections",  weight: 0.94 },
  { text: "Relative volume 2.8× the 20-day average",       weight: 0.86 },
  { text: "Bullish EMA alignment (20 > 50 > 200)",         weight: 0.81 },
  { text: "Positive MACD momentum and rising histogram",   weight: 0.74 },
  { text: "RSI recovering from oversold and curling up",   weight: 0.68 },
  { text: "Trend strength composite 91/100",               weight: 0.62 },
  { text: "Institutional accumulation detected (dark pool)", weight: 0.55 },
  { text: "Volatility regime below sector average",        weight: 0.41 },
];

export type NewsItem = {
  id: string;
  source: string;
  age: string;
  headline: string;
  sentiment: "bullish" | "neutral" | "bearish";
  score: number; // -1..1
  summary: string;
};

export const NEWS: NewsItem[] = [
  {
    id: "n1",
    source: "Bloomberg",
    age: "12m",
    headline: "NVIDIA's data-center revenue seen topping $30B in next quarter",
    sentiment: "bullish",
    score: 0.82,
    summary: "Sell-side upgrades cite sustained order growth from hyperscaler customers.",
  },
  {
    id: "n2",
    source: "Reuters",
    age: "1h",
    headline: "Chip-equipment makers sign long-term supply agreements with NVDA",
    sentiment: "bullish",
    score: 0.71,
    summary: "Industry sources confirm multi-year commitments as Blackwell ramps.",
  },
  {
    id: "n3",
    source: "WSJ",
    age: "3h",
    headline: "Analyst maintains Hold, flags near-term valuation as stretched",
    sentiment: "neutral",
    score: 0.05,
    summary: "Mixed view on risk/reward after the recent 32% rally.",
  },
  {
    id: "n4",
    source: "FT",
    age: "6h",
    headline: "China reportedly steps back from issuing new antitrust probe",
    sentiment: "bullish",
    score: 0.62,
    summary: "Trade tensions cooling; analysts reduce geopolitical risk discount.",
  },
  {
    id: "n5",
    source: "CNBC",
    age: "1d",
    headline: "Options flow shows heavy call activity at $1,000 strike",
    sentiment: "bullish",
    score: 0.58,
    summary: "Unusual volume in far-OTM calls suggests institutional bullish bets.",
  },
  {
    id: "n6",
    source: "MarketWatch",
    age: "2d",
    headline: "Short interest ticks up to 1.4% of float",
    sentiment: "bearish",
    score: -0.31,
    summary: "Modest rise; well below historical average for the name.",
  },
];

export type RiskMetric = {
  key: string;
  name: string;
  value: number; // 0..1 (higher = more)
  tone: "pos" | "neg" | "neutral";
  detail: string;
};

export const RISK_METRICS: RiskMetric[] = [
  { key: "vol",   name: "Volatility",  value: 0.42, tone: "neutral", detail: "Annualized 38.2%" },
  { key: "dd",    name: "Drawdown",   value: 0.28, tone: "pos",     detail: "Max 12.4% (90d)" },
  { key: "liq",   name: "Liquidity",  value: 0.18, tone: "neg",     detail: "Top 5% of names" },
  { key: "spread",name: "Spread",     value: 0.12, tone: "pos",     detail: "Avg 1.2 bps" },
  { key: "sector",name: "Sector Risk",value: 0.55, tone: "neutral", detail: "Tech beta 1.25" },
  { key: "overall",name:"Overall",    value: 0.31, tone: "pos",     detail: "Composite risk score" },
];

export type SupplyZone = {
  startIdx: number;
  endIdx: number;
  topPrice: number;
  bottomPrice: number;
  strength: "High" | "Medium" | "Low";
  fresh: boolean;
  touches: number;
  createdAt: string;
  winRate: number; // 0..1
  avgBounce: number; // e.g. 0.034
  avgDuration: number; // days
};

export const SUPPLY_ZONES: Record<string, SupplyZone[]> = {
  NVDA: [
    { startIdx: 60,  endIdx: 145, topPrice: 982.50, bottomPrice: 952.10, strength: "High",   fresh: true,  touches: 3, createdAt: "2026-04-12", winRate: 0.68, avgBounce: 0.042, avgDuration: 14 },
    { startIdx: 95,  endIdx: 165, topPrice: 1014.10, bottomPrice: 988.50, strength: "Medium", fresh: false, touches: 2, createdAt: "2026-05-08", winRate: 0.54, avgBounce: 0.031, avgDuration: 11 },
  ],
};

export const ENRICHED_DEMAND_ZONES: Record<
  string,
  Array<DemandZone & { createdAt: string; winRate: number; avgBounce: number; avgDuration: number }>
> = {
  NVDA: (ZONES.NVDA ?? []).map((z, i) => ({
    ...z,
    createdAt: i === 0 ? "2026-05-21" : "2026-02-08",
    winRate: i === 0 ? 0.74 : 0.51,
    avgBounce: i === 0 ? 0.058 : 0.029,
    avgDuration: i === 0 ? 17 : 9,
  })),
  AAPL: (ZONES.AAPL ?? []).map((z, i) => ({
    ...z,
    createdAt: i === 0 ? "2026-05-04" : "2026-01-22",
    winRate: i === 0 ? 0.69 : 0.48,
    avgBounce: i === 0 ? 0.04 : 0.022,
    avgDuration: i === 0 ? 14 : 8,
  })),
  TSLA: (ZONES.TSLA ?? []).map((z, i) => ({
    ...z,
    createdAt: "2026-04-19",
    winRate: 0.61,
    avgBounce: 0.039,
    avgDuration: 12,
  })),
};

export const MODEL_INFO = {
  name: "LightGBM v8.2",
  family: "Gradient Boosted Decision Trees",
  dataset: "58,000 trades",
  features: 120,
  valAUC: 0.756,
  precision: 0.42,
  recall: 0.68,
  trainedAt: "Today, 04:00 UTC",
  inferenceMs: 35,
} as const;

export type TradeSetup = {
  entry: number;
  current: number;
  stop: number;
  target: number;
  riskReward: number;
  positionPct: number;
  shares: number;
  capital: number;
  profit: number;
  loss: number;
  kellyPct: number;
  riskPct: number;
};

export function buildTradeSetup(t: InsightTicker, recommendation: Recommendation): TradeSetup {
  const dir = recommendation === "SELL" ? -1 : 1;
  const entry = t.price;
  const stop = +(t.price * (1 - 0.05 * dir)).toFixed(2);
  const target = +(t.price * (1 + 0.15 * dir)).toFixed(2);
  const risk = Math.abs(entry - stop);
  const reward = Math.abs(target - entry);
  const capital = 100_000;
  const riskPct = 0.01;
  const positionDollar = capital * riskPct;
  const shares = Math.floor(positionDollar / risk);
  const profit = +(reward * shares).toFixed(2);
  const loss = +(risk * shares).toFixed(2);
  return {
    entry,
    current: t.price,
    stop,
    target,
    riskReward: +(reward / risk).toFixed(2),
    positionPct: 0.085,
    shares,
    capital: +(shares * entry).toFixed(2),
    profit,
    loss,
    kellyPct: 0.18,
    riskPct: 0.01,
  };
}

export function pickInsight(symbol: string): InsightTicker {
  return INSIGHT_TICKERS.find((t) => t.symbol === symbol) ?? INSIGHT_TICKERS[0]!;
}

export type InsightData = {
  ticker: InsightTicker;
  recommendation: Recommendation;
  confidence: number; // 0..1
  expectedReturn: number; // 0.15 etc.
  stopLoss: number;     // -0.05
  holdingDays: number;
  hitProbability: number;
  stopProbability: number;
  candles: ReturnType<typeof makeCandles>;
  demandZones: Array<DemandZone & { createdAt: string; winRate: number; avgBounce: number; avgDuration: number }>;
  supplyZones: SupplyZone[];
  predictedPath: { time: string; value: number }[];
};

export function makeCandles(symbol: string) {
  return CHART_DATA[symbol] ?? CHART_DATA.NVDA!;
}

export function buildInsight(symbol: string): InsightData {
  const ticker = pickInsight(symbol);
  const recommendation: Recommendation = "BUY";
  const confidence = 0.94;
  const candles = makeCandles(symbol);
  const demand = (ENRICHED_DEMAND_ZONES[symbol] ?? ENRICHED_DEMAND_ZONES.NVDA)!;
  const supply = (SUPPLY_ZONES[symbol] ?? SUPPLY_ZONES.NVDA)!;

  // Predicted future price path — projects 20 sessions forward from the
  // last close with a positive drift + light noise.
  const last = candles[candles.length - 1]!;
  const tomorrow = new Date(last.time);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const drift = 0.005;
  const path: { time: string; value: number }[] = [];
  let v = last.close;
  for (let i = 0; i < 20; i++) {
    v = v * (1 + drift + (Math.sin(i * 0.7) * 0.004));
    const d = new Date(tomorrow);
    d.setDate(tomorrow.getDate() + i);
    const dow = d.getDay();
    if (dow === 0 || dow === 6) continue;
    path.push({ time: d.toISOString().slice(0, 10), value: +v.toFixed(2) });
  }

  return {
    ticker,
    recommendation,
    confidence,
    expectedReturn: 0.15,
    stopLoss: -0.05,
    holdingDays: 20,
    hitProbability: 0.71,
    stopProbability: 0.18,
    candles,
    demandZones: demand,
    supplyZones: supply,
    predictedPath: path,
  };
}
