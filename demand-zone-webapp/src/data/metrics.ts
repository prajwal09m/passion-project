// Real numbers drawn directly from the ML pipeline output files in /outputs
// and /Other. Kept as a single source of truth so every panel references the
// same values.

export const PIPELINE = {
  model: "Random Forest (100 trees, max_depth=12)",
  modelFamily: "Ensemble • sklearn 1.4",
  dataset: "27,638 signals",
  universe: "149 unique US tickers",
  dateRange: { start: "2019-07-30", end: "2026-06-24" },
  holdoutPeriod: { start: "2026-03-06", end: "2026-06-23" },
  features: 86,
  randomSeed: 42,
  threshold: 0.75,
  trainedAt: "2026-07-23",
} as const;

export const HEADLINE_METRICS = [
  { key: "auc", label: "ROC AUC",        value: 0.6890,  format: "auc"  as const, sentiment: "ai"      },
  { key: "pr",  label: "Precision",      value: 0.3750,  format: "pct"  as const, sentiment: "neutral" },
  { key: "rc",  label: "Recall",         value: 0.0048,  format: "pct"  as const, sentiment: "neutral" },
  { key: "wf",  label: "WF AUC",         value: 0.7620,  format: "auc"  as const, sentiment: "ai"      },
  { key: "hit", label: "Hit-Target",      value: 0.1306,  format: "pct"  as const, sentiment: "neutral" },
];

export const BACKTEST = {
  period: "Held-out (2026-03-06 → 2026-06-23)",
  initialCapital: 10_000,
  trades: 8,
  totalReturn: 0.0698,
  maxDrawdown: -0.0412,
  sharpe: 0.67,
  sortino: 0.89,
  calmar: 2.53,
  profitFactor: 1.80,
  winRate: 0.375,
  avgWin: 0.082,
  avgLoss: -0.034,
  avgDurationDays: 9.5,
  winDuration: 13.5,
  lossDuration: 4.0,
  commission: "$1 per side",
  slippage: "15 bps per side",
  riskPerTrade: "1% of equity",
  maxPositions: 5,
};

export const CONFUSION = {
  truePositive: 12,
  falsePositive: 20,
  falseNegative: 240,
  trueNegative: 3761,
  // Derived, kept computed for clarity in panels.
  precision: 0.375,
  recall: 0.048,
  f1: 0.085,
};

// Stat distributions used in micro-histograms on the ML terminal page.
export const WALK_FORWARD = [
  { fold: 1, auc: 0.6611, precision: 0.3333, recall: 0.2632 },
  { fold: 2, auc: 0.5748, precision: 0.3500, recall: 0.9333 },
  { fold: 3, auc: 0.4876, precision: 0.1538, recall: 0.1429 },
  { fold: 4, auc: 0.5450, precision: 0.1905, recall: 0.3077 },
  { fold: 5, auc: 0.6676, precision: 0.5000, recall: 0.0588 },
];
