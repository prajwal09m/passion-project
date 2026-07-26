// Top-10 features for the production model — sourced from
// outputs/broad_pipeline_results_v6.txt (broad-market held-out test set).
// Used on both the Performance (ML terminal) page and the Analysis sidebar.

export type Feature = {
  rank: number;
  key: string;
  displayName: string;
  category: "Zone Quality" | "Market Context" | "Volatility" | "Volume" | "Sector Context";
  importance: number; // 0..0.05
  direction: "positive" | "negative";
  description: string;
};

export const TOP_FEATURES: Feature[] = [
  {
    rank: 1,
    key: "base_range_pct",
    displayName: "Base Range %",
    category: "Zone Quality",
    importance: 0.0281,
    direction: "positive",
    description: "Normalized price consolidation range before departure.",
  },
  {
    rank: 2,
    key: "zone_width_pct",
    displayName: "Zone Width %",
    category: "Zone Quality",
    importance: 0.0273,
    direction: "positive",
    description: "Width of the demand zone as % of price.",
  },
  {
    rank: 3,
    key: "spy_return_50d",
    displayName: "SPY Return 50d",
    category: "Market Context",
    importance: 0.0252,
    direction: "positive",
    description: "Broad-market 50-day trailing return — regime filter.",
  },
  {
    rank: 4,
    key: "ma_50_slope_20",
    displayName: "MA50 Slope 20d",
    category: "Market Context",
    importance: 0.0213,
    direction: "positive",
    description: "Slope of 50-day moving average over the last 20 days.",
  },
  {
    rank: 5,
    key: "iwm_return_20d",
    displayName: "IWM Return 20d",
    category: "Market Context",
    importance: 0.0178,
    direction: "positive",
    description: "Russell 2000 20-day return — small-cap risk appetite.",
  },
  {
    rank: 6,
    key: "vix_percentile_60d",
    displayName: "VIX Percentile 60d",
    category: "Volatility",
    importance: 0.0101,
    direction: "negative",
    description: "VIX percentile over the trailing 60 sessions.",
  },
  {
    rank: 7,
    key: "xly_return_20d",
    displayName: "XLY Return 20d",
    category: "Sector Context",
    importance: 0.0083,
    direction: "positive",
    description: "Consumer Discretionary sector momentum (XLY).",
  },
  {
    rank: 8,
    key: "departure_volume_ratio",
    displayName: "Departure Vol ×",
    category: "Volume",
    importance: 0.0048,
    direction: "positive",
    description: "Volume ratio on the candle that departed the zone.",
  },
  {
    rank: 9,
    key: "vix_level",
    displayName: "VIX Level",
    category: "Volatility",
    importance: 0.0045,
    direction: "negative",
    description: "Absolute VIX level at signal time.",
  },
  {
    rank: 10,
    key: "rejection_strength",
    displayName: "Rejection Strength",
    category: "Zone Quality",
    importance: 0.0043,
    direction: "positive",
    description: "Wick-to-body ratio on rejection candles inside the zone.",
  },
];

export const FEATURE_CATEGORY_COLORS: Record<Feature["category"], string> = {
  "Zone Quality":     "ai",
  "Market Context":   "fg",
  "Volatility":       "warn",
  "Volume":           "fg",
  "Sector Context":   "ai",
};
