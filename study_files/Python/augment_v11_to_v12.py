"""
Augment v11 dataset → v12 with additional derived features.
Does NOT overwrite v11.

New targets:
  - strong_hit: hit_target with SPY not crashing (cleaner 8.8% positive rate)

New features:
  - spy_momentum: composite SPY momentum score
  - zone_to_vol: zone width normalized by volatility
  - trend_momentum_cross: trend × momentum interaction
  - rejection_with_volume: rejection strength × relative volume
"""

import pandas as pd
import numpy as np
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "outputs" / "v11" / "demand_zone_ml_dataset_v11.csv"
DST = Path(__file__).resolve().parent.parent / "outputs" / "v12"
DST.mkdir(parents=True, exist_ok=True)
DST_FILE = DST / "demand_zone_ml_dataset_v12.csv"

EPS = 1e-4

print(f"Loading {SRC} ...")
df = pd.read_csv(SRC)
print(f"  Rows: {len(df):,}  Columns: {len(df.columns)}")

added = []

# ── Target: strong_hit (hit + SPY not in correction) ───────────────
df["strong_hit"] = (
    (df["hit_target"] == 1) &
    (df["spy_return_20d"] > -0.01)
).astype(int)
pos_s = int(df["strong_hit"].sum())
added.append("strong_hit")
print(f"  strong_hit: {pos_s:,} positive ({pos_s/len(df)*100:.1f}%)")

# ── Feature 1: SPY composite momentum ─────────────────────────────
df["spy_momentum"] = (
    df["spy_return_5d"] * 0.3 +
    df["spy_return_20d"] * 0.5 +
    df["spy_return_50d"] * 0.2
)
added.append("spy_momentum")

# ── Feature 2: zone width vs volatility ───────────────────────────
df["zone_to_vol"] = df["zone_width_pct"] / (df["atr_pct"] + EPS)
added.append("zone_to_vol")

# ── Feature 3: trend × momentum cross ─────────────────────────────
df["trend_momentum_cross"] = df["ema_50_slope_20"] * df["adx_14"]
added.append("trend_momentum_cross")

# ── Feature 4: rejection × volume ─────────────────────────────────
df["rejection_with_volume"] = df["rejection_strength"] * df["rel_volume"]
added.append("rejection_with_volume")

# ── Feature 5: zone_depth (how far below zone is price from 52w high) ──
df["zone_depth"] = df["distance_from_52w_high_pct"].abs()
added.append("zone_depth")

# ── Feature 6: liquidity × trend ──────────────────────────────────
df["liquidity_trend"] = df["liquidity_depth_score"] * (1 + df["spy_return_50d"])
added.append("liquidity_trend")

print(f"\nAdded {len(added)} columns: {added}")

# ── Save ───────────────────────────────────────────────────────────
df.to_csv(DST_FILE, index=False)
print(f"\nSaved to {DST_FILE}")
print(f"  Shape: {df.shape}  Columns: {len(df.columns)}")

print(f"\n  hit_target: {df['hit_target'].mean():.4f} ({df['hit_target'].sum():,})")
print(f"  strong_hit: {df['strong_hit'].mean():.4f} ({df['strong_hit'].sum():,})")
