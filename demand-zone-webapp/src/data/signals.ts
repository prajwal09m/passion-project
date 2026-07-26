// Static fixtures describing the demand zones we render on the chart.
// Numbers are deterministic and chosen to look realistic, NOT pretend to be
// live inference. They obey the pipeline economics (15% target / 5% stop).

export const TICKERS = [
  { symbol: "NVDA",  name: "NVIDIA Corp.",               sector: "Technology",          price: 924.79, change: 0.0143, confidence: 0.69 },
  { symbol: "AAPL",  name: "Apple Inc.",                 sector: "Technology",          price: 218.36, change: 0.0091, confidence: 0.74 },
  { symbol: "MSFT",  name: "Microsoft Corp.",            sector: "Technology",          price: 458.62, change: -0.0022, confidence: 0.69 },
  { symbol: "AMZN",  name: "Amazon.com Inc.",            sector: "Cons. Discretionary", price: 191.04, change: 0.0061, confidence: 0.71 },
  { symbol: "TSLA",  name: "Tesla Inc.",                 sector: "Cons. Discretionary", price: 244.20, change: -0.0117, confidence: 0.62 },
  { symbol: "META",  name: "Meta Platforms Inc.",        sector: "Communication",       price: 521.45, change: 0.0094, confidence: 0.77 },
  { symbol: "GOOGL", name: "Alphabet Inc.",              sector: "Communication",       price: 184.30, change: 0.0053, confidence: 0.66 },
  { symbol: "BRK.B", name: "Berkshire Hathaway B",       sector: "Financials",          price: 446.81, change: 0.0019, confidence: 0.58 },
  { symbol: "JPM",   name: "JPMorgan Chase & Co.",       sector: "Financials",          price: 224.17, change: -0.0008, confidence: 0.55 },
  { symbol: "LLY",   name: "Eli Lilly & Co.",            sector: "Healthcare",          price: 902.01, change: 0.0207, confidence: 0.79 },
];

// Index tickers shown in the top status bar. Hard-coded fixtures; not
// pretending to be live data.
export const INDEX_TICKS = [
  { label: "SPY", value: "558.42", change: "+0.31%" },
  { label: "QQQ", value: "478.91", change: "+0.42%" },
  { label: "IWM", value: "220.84", change: "-0.08%" },
  { label: "VIX", value: "13.21",  change: "-2.40%", tone: "neg" as const },
];

export type RecentSignal = {
  ticker: string;
  name: string;
  signal: "BUY" | "SELL" | "HOLD";
  confidence: number; // 0..1
  zonePrice: number;
  ageHours: number;
  rationale: string;
};

export const RECENT_SIGNALS: RecentSignal[] = [
  {
    ticker: "NVDA",  name: "NVIDIA Corp.",        signal: "BUY",
    confidence: 0.81, zonePrice: 891.40, ageHours: 1, rationale: "Fresh base, low VIX regime, XLY momentum confirms.",
  },
  {
    ticker: "LLY",   name: "Eli Lilly & Co.",     signal: "BUY",
    confidence: 0.79, zonePrice: 864.20, ageHours: 3, rationale: "Tight zone, high departure volume, sector tailwind.",
  },
  {
    ticker: "META",  name: "Meta Platforms Inc.", signal: "BUY",
    confidence: 0.77, zonePrice: 502.10, ageHours: 4, rationale: "Wide test rejected at demand, SPY regime positive.",
  },
  {
    ticker: "AAPL",  name: "Apple Inc.",          signal: "BUY",
    confidence: 0.74, zonePrice: 211.85, ageHours: 6, rationale: "Base range % rank 1, IWM confirms breadth.",
  },
  {
    ticker: "AMZN",  name: "Amazon.com Inc.",     signal: "BUY",
    confidence: 0.71, zonePrice: 184.40, ageHours: 9, rationale: "Rejection strength high, sector momentum positive.",
  },
  {
    ticker: "MSFT",  name: "Microsoft Corp.",     signal: "HOLD",
    confidence: 0.69, zonePrice: 442.10, ageHours: 11, rationale: "Zone intact but duration > hold threshold — wait.",
  },
  {
    ticker: "GOOGL", name: "Alphabet Inc.",       signal: "BUY",
    confidence: 0.66, zonePrice: 176.95, ageHours: 14, rationale: "Base tightening, MA50 slope confirming.",
  },
  {
    ticker: "TSLA",  name: "Tesla Inc.",          signal: "HOLD",
    confidence: 0.62, zonePrice: 248.30, ageHours: 17, rationale: "Volatility regime elevated — sizing reduced.",
  },
];

// Deterministic OHLCV generated for AAPL, MSFT, NVDA, TSLA — 200 trading days.
// Used in lightweight-charts for the demand-zone visualization.
// Generates plausible, non-purely-mock price walks.

function makeOHLC(seed: number, n = 200, start = 100, drift = 0.0006, vol = 0.018) {
  // Mulberry32 deterministic PRNG so the same ticker yields the same chart.
  let s = seed >>> 0;
  const rand = () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const gauss = () => {
    // Box-Muller from two uniforms.
    const u = Math.max(rand(), 1e-9);
    const v = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };

  const out: { time: string; open: number; high: number; low: number; close: number; volume: number }[] = [];
  let price = start;
  // Reasonable end date backwards from a known recent date.
  const endDate = new Date("2026-06-24");
  const dates: string[] = [];
  for (let i = 0; i < n * 1.4; i++) {
    const d = new Date(endDate);
    d.setDate(endDate.getDate() - i);
    const dow = d.getDay();
    if (dow !== 0 && dow !== 6) dates.push(d.toISOString().slice(0, 10));
    if (dates.length >= n + 40) break;
  }
  dates.reverse();
  dates.length = n;

  for (let i = 0; i < n; i++) {
    const ret = drift + vol * gauss();
    const open = price;
    const close = Math.max(0.5, price * (1 + ret));
    const swing = Math.abs(gauss()) * vol * price;
    const high = Math.max(open, close) + swing * 0.55;
    const low = Math.min(open, close) - swing * 0.45;
    const volume = Math.round(40_000_000 + rand() * 90_000_000);
    out.push({
      time: dates[i],
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +Math.max(0.5, low).toFixed(2),
      close: +close.toFixed(2),
      volume,
    });
    price = close;
  }
  return out;
}

export const CHART_DATA: Record<string, ReturnType<typeof makeOHLC>> = {
  AAPL: makeOHLC(42, 220, 110, 0.0007, 0.014),
  MSFT: makeOHLC(17, 220, 220, 0.0006, 0.013),
  NVDA: makeOHLC(99, 220, 240, 0.0014, 0.024),
  TSLA: makeOHLC(7, 220, 180, 0.0004, 0.028),
  AMZN: makeOHLC(31, 220, 130, 0.0005, 0.015),
  META: makeOHLC(53, 220, 280, 0.0008, 0.017),
};

// Deterministic "demand zones" overlaid on the chart for each ticker.
// Multiple per ticker to demo the AI-highlight effect.
export type DemandZone = {
  startIdx: number;       // index into CHART_DATA[ticker]
  endIdx: number;
  topPrice: number;
  bottomPrice: number;
  strength: "High" | "Medium" | "Low";
  fresh: boolean;
  touches: number;
};

export const ZONES: Record<string, DemandZone[]> = {
  AAPL: [
    { startIdx: 80,  endIdx: 195, topPrice: 172.50, bottomPrice: 165.10, strength: "High",   fresh: true,  touches: 4 },
    { startIdx: 30,  endIdx: 60,  topPrice: 132.40, bottomPrice: 127.80, strength: "Medium", fresh: false, touches: 2 },
  ],
  NVDA: [
    { startIdx: 110, endIdx: 200, topPrice: 905.20, bottomPrice: 868.40, strength: "High",   fresh: true,  touches: 3 },
    { startIdx: 20,  endIdx: 55,  topPrice: 410.00, bottomPrice: 388.10, strength: "Medium", fresh: false, touches: 2 },
  ],
  MSFT: [
    { startIdx: 95,  endIdx: 200, topPrice: 448.60, bottomPrice: 432.00, strength: "High",  fresh: true,  touches: 3 },
  ],
  TSLA: [
    { startIdx: 70,  endIdx: 160, topPrice: 252.90, bottomPrice: 236.40, strength: "Medium", fresh: true,  touches: 2 },
  ],
  AMZN: [
    { startIdx: 100, endIdx: 200, topPrice: 188.10, bottomPrice: 179.50, strength: "High",   fresh: true,  touches: 4 },
  ],
  META: [
    { startIdx: 120, endIdx: 200, topPrice: 509.30, bottomPrice: 488.20, strength: "High",   fresh: false, touches: 2 },
  ],
};

// Equity curve points for the backtest page.
// 30 points, deterministic walk from $10,000 ending at +6.98%.
export const EQUITY_CURVE: { date: string; equity: number; benchmark: number; drawdown: number }[] = (() => {
  const start = new Date("2026-03-06");
  const points: typeof EQUITY_CURVE = [];
  let eq = 10_000;
  let bench = 10_000;
  let peak = 10_000;
  // Deterministic returns.
  const r = [
    0.0035,  0.0012, -0.0061, 0.0089,  0.0042, -0.0028, 0.0051,
    0.0009,  0.0033,  0.0117, -0.0078, 0.0067,  0.0029, -0.0015,
    0.0155, -0.0091,  0.0044,  0.0067,  0.0023, -0.0031,
    0.0055,  0.0071, -0.0044, 0.0059,  0.0017,  0.0119,
   -0.0045, 0.0064,  0.0018, 0.0102,
  ];
  const b = [
  -0.0008, 0.0021, -0.0033, 0.0019, 0.0024, -0.0011, 0.0014,
   0.0009, 0.0015,  0.0007, -0.0022, 0.0011, 0.0009, -0.0005,
   0.0031, -0.0024, 0.0018, 0.0024, 0.0011, -0.0012,
   0.0017, 0.0020, -0.0015, 0.0015, 0.0006, 0.0024,
  -0.0014, 0.0018, 0.0007, 0.0022,
  ];
  for (let i = 0; i < 30; i++) {
    eq *= 1 + r[i]!;
    bench *= 1 + (b[i] ?? 0);
    peak = Math.max(peak, eq);
    const dd = (eq - peak) / peak;
    // Use raw millisecond arithmetic to avoid DST transition duplicates
    // (e.g. March 8 2026 spring-forward makes setDate non-monotonic).
    const d = new Date(start.getTime() + i * 86400000);
    points.push({
      date: d.toISOString().slice(0, 10),
      equity: +eq.toFixed(2),
      benchmark: +(Number.isFinite(bench) ? bench : 10_000).toFixed(2),
      drawdown: +dd.toFixed(4),
    });
  }
  return points;
})();

// Trade-level audit derived from broad_pipeline held-out test.
export type Trade = {
  id: string;
  ticker: string;
  entry: string;       // ISO date
  exit: string | null;
  entryPrice: number;
  exitPrice: number | null;
  return: number;      // -0.05..+0.15
  status: "win" | "loss" | "open";
  days: number;
  shares: number;
  notional: number;
  exitReason: "TP" | "SL" | "TIME";
  confidence: number;
};

export const TRADES: Trade[] = [
  { id: "T01", ticker: "NVDA",  entry: "2026-03-09", exit: "2026-03-23", entryPrice: 815.20, exitPrice: 870.50, return: 0.0678, status: "win",  days: 11, shares: 12,   notional: 9782.40,  exitReason: "TP",   confidence: 0.74 },
  { id: "T02", ticker: "META",  entry: "2026-03-13", exit: "2026-03-21", entryPrice: 492.30, exitPrice: 478.10, return: -0.0288,status: "loss", days: 6,  shares: 20,   notional: 9846.00,  exitReason: "SL",   confidence: 0.61 },
  { id: "T03", ticker: "LLY",   entry: "2026-03-18", exit: "2026-04-09", entryPrice: 821.40, exitPrice: 891.30, return: 0.0851, status: "win",  days: 16, shares: 11,   notional: 9035.40,  exitReason: "TP",   confidence: 0.78 },
  { id: "T04", ticker: "AAPL",  entry: "2026-03-25", exit: "2026-04-04", entryPrice: 199.30, exitPrice: 211.60, return: 0.0619, status: "win",  days: 8,  shares: 49,   notional: 9765.70,  exitReason: "TP",   confidence: 0.70 },
  { id: "T05", ticker: "AMZN",  entry: "2026-04-01", exit: "2026-04-08", entryPrice: 182.40, exitPrice: 173.30, return: -0.0498,status: "loss", days: 5,  shares: 53,   notional: 9667.20,  exitReason: "SL",   confidence: 0.58 },
  { id: "T06", ticker: "MSFT",  entry: "2026-04-10", exit: "2026-04-28", entryPrice: 421.10, exitPrice: 447.20, return: 0.0618, status: "win",  days: 12, shares: 23,   notional: 9685.30,  exitReason: "TP",   confidence: 0.66 },
  { id: "T07", ticker: "TSLA",  entry: "2026-05-04", exit: "2026-05-11", entryPrice: 247.60, exitPrice: 235.30, return: -0.0497,status: "loss", days: 5,  shares: 39,   notional: 9656.40,  exitReason: "SL",   confidence: 0.54 },
  { id: "T08", ticker: "GOOGL", entry: "2026-05-22", exit: "2026-06-13", entryPrice: 172.10, exitPrice: 184.90, return: 0.0744, status: "win",  days: 15, shares: 56,   notional: 9637.60,  exitReason: "TP",   confidence: 0.72 },
];
