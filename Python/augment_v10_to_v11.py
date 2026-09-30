"""
Augment the v10 dataset with derived features and save as v11.
Does NOT overwrite the original v10 file.

Adds:
  1. retest_x_strength = retest_number * zone_strength
  2. market_relative_hit = hit_target (proxy: 15% gain beats market)
  3. zone_efficiency = zone_strength / (zone_width_pct + 1e-4)
  4. vol_adjusted_spy = spy_return_20d / (vix_level / 100 + 1e-4)
  5. zone_market_context = zone_strength * (1 + spy_return_50d)
  6. retest_frequency = retest_number / (zone_age_days + 1) * 100
  7. rsi_extremity = abs(rsi_14 - 50) / 50
  8. volume_pressure = rel_volume * (2 * is_bullish - 1)
  9. trend_quality_norm = trend_quality / (atr_pct + 1e-4)
"""

import pandas as pd
import numpy as np
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "outputs" / "v10" / "demand_zone_ml_dataset_v10.csv"
DST = Path(__file__).resolve().parent.parent / "outputs" / "v11"
DST.mkdir(parents=True, exist_ok=True)
DST_FILE = DST / "demand_zone_ml_dataset_v11.csv"

EPS = 1e-4  # prevent division by zero

print(f"Loading {SRC} ...")
df = pd.read_csv(SRC)
print(f"  Rows: {len(df):,}  Columns: {len(df.columns)}")

added = []

# ── 1. retest × strength interaction ──────────────────────────────
df["retest_x_strength"] = df["retest_number"] * df["zone_strength"]
added.append("retest_x_strength")

# ── 2. market-relative label ──────────────────────────────────────
df["market_relative_hit"] = df["hit_target"].copy()
added.append("market_relative_hit")

# ── 3. zone efficiency: strong ÷ wide = high quality ──────────────
df["zone_efficiency"] = df["zone_strength"] / (df["zone_width_pct"] + EPS)
added.append("zone_efficiency")

# ── 4. risk-adjusted market return ────────────────────────────────
df["vol_adjusted_spy"] = df["spy_return_20d"] / (df["vix_level"].clip(lower=5) / 100 + EPS)
added.append("vol_adjusted_spy")

# ── 5. zone quality × market context ──────────────────────────────
df["zone_market_context"] = df["zone_strength"] * (1 + df["spy_return_50d"])
added.append("zone_market_context")

# ── 6. retest frequency (per 100 days) ────────────────────────────
df["retest_frequency"] = df["retest_number"] / (df["zone_age_days"] + 1) * 100
added.append("retest_frequency")

# ── 7. RSI extremity ──────────────────────────────────────────────
df["rsi_extremity"] = (df["rsi_14"] - 50).abs() / 50
added.append("rsi_extremity")

# ── 8. signed volume pressure ─────────────────────────────────────
df["volume_pressure"] = df["rel_volume"] * (2 * df["is_bullish"] - 1)
added.append("volume_pressure")

# ── 9. normalized trend quality ───────────────────────────────────
if "trend_quality" in df.columns:
    df["trend_quality_norm"] = df["trend_quality"] / (df["atr_pct"] + EPS)
    added.append("trend_quality_norm")

print(f"\nAdded {len(added)} features: {added}")

# ── Save ───────────────────────────────────────────────────────────
df.to_csv(DST_FILE, index=False)
print(f"\nSaved to {DST_FILE}")
print(f"  Shape: {df.shape}  Columns: {len(df.columns)}")

print(f"\n  hit_target: {df['hit_target'].mean():.4f} ({df['hit_target'].sum():,} positive)")
for col in added:
    if col in df.columns:
        print(f"  {col}: mean={df[col].mean():.4f}  std={df[col].std():.4f}")
