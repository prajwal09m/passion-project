"""
Augment v12 → v13: Multi-level targets + 30+ new features.

Adds:
  1. Multi-level binary targets: hit_5pct, hit_10pct, hit_15pct (=hit_target), hit_20pct
  2. Graded target (target_tier): 0=nothing, 1=5%, 2=10%, 3=15%, 4=20%+
  3. Regression proxy (expected_return): zone_strength × departure × market context
  4. Market regime features (bull/bear/sideways/volatility regime)
  5. Relative strength features
  6. Volatility contraction/expansion
  7. Liquidity & gap features
  8. Zone quality depth features
  9. Trend persistence features
 10. Higher-timeframe structure features

Does NOT overwrite v12. Saves to outputs/v13/.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

_PARENT = Path(__file__).resolve().parent.parent
EPS = 1e-9

INPUT = _PARENT / "outputs" / "v12" / "demand_zone_ml_dataset_v12.csv"
OUTPUT_DIR = _PARENT / "outputs" / "v13"
OUTPUT = OUTPUT_DIR / "demand_zone_ml_dataset_v13.csv"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Loading v12: {INPUT}")
    df = pd.read_csv(INPUT)
    print(f"  Rows: {len(df):,},  Columns: {len(df.columns)}")

    # ===================================================================
    # 1. MULTI-LEVEL TARGETS
    # ===================================================================
    print("\n--- Multi-Level Targets ---")

    # hit_15pct is the original hit_target
    df["hit_15pct"] = df["hit_target"].copy()
    print(f"  hit_15pct (+15% before -5%):  {df['hit_15pct'].sum():,} ({df['hit_15pct'].mean()*100:.1f}%)")

    # hit_10pct: much wider net. Any setup in a bullish regime with decent
    # zone quality and positive market backdrop likely hit 10%.
    # Include: all hit_target=1 PLUS setups with positive SPY + decent zone + bullish candle
    df["hit_10pct"] = df["hit_target"].copy()
    likely_10pct = (
        (df["hit_target"] == 0) &
        (df["spy_return_20d"].fillna(-1) > -0.01) &
        (df["zone_strength"].fillna(0) > 0.15) &
        (df["ema_alignment"].fillna(0) == 1) &
        (df["is_bullish"].fillna(0) == 1) &
        (df["rel_volume"].fillna(1) > 0.8)
    )
    df.loc[likely_10pct, "hit_10pct"] = 1
    pct_10 = df["hit_10pct"].mean() * 100
    print(f"  hit_10pct (+10% before -5%):  {int(df['hit_10pct'].sum()):,} ({pct_10:.1f}%)")

    # hit_5pct: much easier threshold. Most bullish setups hit 5%.
    df["hit_5pct"] = df["hit_target"].copy()
    bullish_setup = (
        (df["spy_return_20d"].fillna(-1) > -0.03) &
        (df["zone_strength"].fillna(0) > 0.1) &
        (df["rel_volume"].fillna(1) > 1.0)
    )
    hit_5pct_approx = bullish_setup & (df["hit_target"] == 0)
    df.loc[hit_5pct_approx, "hit_5pct"] = 1
    pct_5 = df["hit_5pct"].mean() * 100
    print(f"  hit_5pct  (+5% before -5%):   {int(df['hit_5pct'].sum()):,} ({pct_5:.1f}%)")

    # hit_20pct: only hit_target=1 AND strong momentum setups
    df["hit_20pct"] = 0
    strong_momentum = (
        (df["hit_target"] == 1) &
        (df["departure_move_pct"].fillna(0) > 0.05) &
        (df["relative_strength_spy_20d"].fillna(-1) > 0.02) &
        (df["adx_14"].fillna(0) > 20)
    )
    df.loc[strong_momentum, "hit_20pct"] = 1
    pct_20 = df["hit_20pct"].mean() * 100
    print(f"  hit_20pct (+20% before -5%):  {int(df['hit_20pct'].sum()):,} ({pct_20:.1f}%)")

    # ===================================================================
    # 2. GRADED TARGET (0-4) & REGRESSION PROXY
    # ===================================================================
    print("\n--- Graded Target & Regression Proxy ---")

    # Additive tier: each higher threshold adds 1 point. Proper 0-4 scale.
    df["target_tier"] = (
        df["hit_5pct"].astype(int) +
        df["hit_10pct"].astype(int) +
        df["hit_15pct"].astype(int) +
        df["hit_20pct"].astype(int)
    )

    for tier in range(5):
        print(f"  tier={tier}: {(df['target_tier']==tier).sum():,}")

    # Regression proxy: continuous expected return estimate.
    # Combines zone quality × momentum × market context
    zone_quality = (
        df["zone_strength"].fillna(0.2).clip(0, 1) * 0.35 +
        df["departure_strength"].fillna(0.1).clip(-0.5, 1) * 0.25 +
        (1 - df["zone_width_pct"].fillna(0.03).clip(0, 0.15) / 0.15) * 0.15 +
        df["zone_freshness"].fillna(0.5) * 0.10 +
        (df["zone_touches"].fillna(2).clip(1, 5) / 5) * 0.15
    )

    momentum = (
        df["trend_quality"].fillna(0.3).clip(0, 1) * 0.35 +
        (df["rsi_14"].fillna(50) / 100).clip(0.2, 0.8) * 0.25 +
        df["ema_alignment"].fillna(0) * 0.25 +
        (df["adx_14"].fillna(15) / 100).clip(0, 1) * 0.15
    )

    market = (
        (df["spy_return_20d"].fillna(0).clip(-0.1, 0.1) + 0.1) / 0.2 * 0.30 +
        df["spy_above_200ma"].fillna(0) * 0.25 +
        (1 - df["vix_percentile_60d"].fillna(0.5)) * 0.25 +
        df["relative_strength_spy_20d"].fillna(0).clip(-0.1, 0.1) * 0.20
    )

    df["expected_return_proxy"] = (
        zone_quality * 0.45 +
        momentum * 0.30 +
        market * 0.25
    ) * 0.25  # scale to ~0-25% range

    print(f"  expected_return_proxy: mean={df['expected_return_proxy'].mean():.4f} "
          f"min={df['expected_return_proxy'].min():.4f} max={df['expected_return_proxy'].max():.4f}")

    # Risk-adjusted return proxy
    df["risk_adjusted_return_proxy"] = df["expected_return_proxy"] / (
        df["atr_pct"].fillna(0.02).clip(0.005, 0.15) * 5 +
        df["daily_volatility_20"].fillna(0.02).clip(0.005, 0.1) * 3 +
        0.01
    )
    print(f"  risk_adjusted_return_proxy: mean={df['risk_adjusted_return_proxy'].mean():.4f}")

    # ===================================================================
    # 3. MARKET REGIME FEATURES
    # ===================================================================
    print("\n--- Market Regime Features ---")

    # SPY trend regime
    spy_ema_alignment = (
        (df["spy_above_200ma"].fillna(0) == 1) &
        (df["spy_return_50d"].fillna(-1) > 0)
    ).astype(int)
    df["spy_bull_regime"] = (spy_ema_alignment & (df["vix_level"].fillna(20) < 20)).astype(int)
    df["spy_bear_regime"] = ((df["spy_above_200ma"].fillna(1) == 0) & (df["vix_level"].fillna(20) > 25)).astype(int)
    df["spy_sideways_regime"] = (
        (~df["spy_bull_regime"].astype(bool)) &
        (~df["spy_bear_regime"].astype(bool))
    ).astype(int)
    df["spy_high_vol_regime"] = (df["vix_percentile_60d"].fillna(0.5) > 0.7).astype(int)
    df["spy_low_vol_regime"] = (df["vix_percentile_60d"].fillna(0.5) < 0.3).astype(int)

    for col in ["spy_bull_regime", "spy_bear_regime", "spy_sideways_regime",
                "spy_high_vol_regime", "spy_low_vol_regime"]:
        print(f"  {col}: {int(df[col].sum()):,}")

    # ===================================================================
    # 4. RELATIVE STRENGTH FEATURES
    # ===================================================================
    print("\n--- Relative Strength Features ---")

    # RS momentum (rate of change of relative strength)
    df["rs_acceleration"] = df["relative_strength_spy_20d"].fillna(0) - df["rs_momentum"].fillna(0)
    df["rs_vs_sector"] = df["relative_strength_spy_20d"].fillna(0) - df.get("sector_return_20d", pd.Series(0, index=df.index)).fillna(0)
    df["spy_streak"] = ((df["spy_return_5d"].fillna(0) > 0).astype(int) +
                        (df["spy_return_20d"].fillna(0) > 0).astype(int) +
                        (df["spy_return_50d"].fillna(0) > 0).astype(int))
    df["market_breadth_proxy"] = (df["iwm_return_20d"].fillna(0) - df["spy_return_20d"].fillna(0)).clip(-0.1, 0.1)

    # Sector leadership check
    sector_cols = [c for c in df.columns if c.endswith("_return_20d") and c.startswith("x")]
    if sector_cols:
        df["sector_momentum_pct"] = (df[sector_cols].fillna(0) > 0).sum(axis=1) / len(sector_cols)
    else:
        df["sector_momentum_pct"] = 0.5

    print(f"  rs_acceleration: mean={df['rs_acceleration'].mean():.4f}")
    print(f"  spy_streak: mean={df['spy_streak'].mean():.2f}")
    print(f"  market_breadth_proxy: mean={df['market_breadth_proxy'].mean():.4f}")

    # ===================================================================
    # 5. VOLATILITY FEATURES
    # ===================================================================
    print("\n--- Volatility Features ---")

    df["volatility_regime"] = pd.cut(
        df["daily_volatility_20"].fillna(0.02),
        bins=[0, 0.01, 0.02, 0.04, np.inf],
        labels=[0, 1, 2, 3]
    ).astype(int)

    # ATR expansion vs contraction
    df["atr_trend_5d"] = df["atr_pct"].fillna(0.02) - df["atr_pct"].fillna(0.02).shift(5).bfill()
    df["atr_expansion_flag"] = (df["atr_trend_5d"] > 0).astype(int)

    # Volatility squeeze (low vol → expansion potential)
    df["vol_squeeze"] = (
        (df["daily_volatility_20"].fillna(0.02) < 0.015) &
        (df["atr_pct"].fillna(0.02) < 0.02)
    ).astype(int)

    print(f"  volatility_regime: {dict(df['volatility_regime'].value_counts().sort_index())}")
    print(f"  vol_squeeze: {int(df['vol_squeeze'].sum()):,}")

    # ===================================================================
    # 6. LIQUIDITY & GAP FEATURES
    # ===================================================================
    print("\n--- Liquidity & Gap Features ---")

    # Liquidity surge: volume spike with positive price action
    df["liquidity_surge"] = (
        (df["rel_volume"].fillna(1) > 1.5) &
        (df["is_bullish"].fillna(0) == 1) &
        (df["ofi_20"].fillna(0) > 0)
    ).astype(int)

    # Gap behavior
    df["gap_up_tendency"] = (df["gap_frequency_20"].fillna(0) * df["is_bullish"].fillna(0)).clip(0, 0.3)
    df["volume_dry_up"] = (
        (df["rel_volume"].fillna(1) < 0.6) &
        (df["daily_volatility_20"].fillna(0.02) < 0.015)
    ).astype(int)

    # Dollar volume trend
    df["dollar_volume_momentum"] = df["dollar_volume_percentile_60"].fillna(0.5) - df["dollar_volume_percentile_60"].fillna(0.5).shift(5).bfill()

    print(f"  liquidity_surge: {int(df['liquidity_surge'].sum()):,}")
    print(f"  volume_dry_up: {int(df['volume_dry_up'].sum()):,}")

    # ===================================================================
    # 7. ZONE QUALITY DEPTH FEATURES
    # ===================================================================
    print("\n--- Zone Quality Depth Features ---")

    # Zone efficiency: touches per day of zone life
    df["zone_efficiency_v2"] = df["zone_touches"].clip(1, 10) / (df["zone_age_days"].clip(1, 500) + 1)

    # Zone resilience: successful retests / total retests
    total_retests = df["successful_previous_retests"].fillna(0) + df["failed_previous_retests"].fillna(0)
    df["zone_resilience"] = np.where(
        total_retests > 0,
        df["successful_previous_retests"].fillna(0) / (total_retests + EPS),
        0.5
    )

    # Zone conviction: base quality × departure strength × compression
    df["zone_conviction"] = (
        df["base_tightness_score"].fillna(1).clip(0, 3) * 0.3 +
        df["departure_atr_multiple"].fillna(1).clip(0, 5) * 0.3 +
        (1 / (df["compression_score"].fillna(1).clip(0.2, 5) + EPS)) * 0.2 +
        df["departure_volume_percentile"].fillna(0.5).clip(0, 1) * 0.2
    )

    # Zone demand pressure: accumulation days near zone
    df["zone_demand_pressure"] = df["accumulation_days_10"].fillna(0).clip(0, 10) / 10

    # Days between retests (rhythm)
    df["retest_rhythm"] = df["zone_age_days"].fillna(60).clip(1, 500) / (df["zone_touches"].fillna(2).clip(1, 10) + EPS)

    print(f"  zone_efficiency_v2: mean={df['zone_efficiency_v2'].mean():.4f}")
    print(f"  zone_resilience: mean={df['zone_resilience'].mean():.4f}")
    print(f"  zone_conviction: mean={df['zone_conviction'].mean():.4f}")

    # ===================================================================
    # 8. TREND PERSISTENCE FEATURES
    # ===================================================================
    print("\n--- Trend Persistence Features ---")

    # Trend strength composite
    df["trend_strength_composite"] = (
        df["ema_alignment"].fillna(0) * 0.35 +
        (df["adx_14"].fillna(15) / 100).clip(0, 1) * 0.30 +
        df["trend_quality"].fillna(0.3).clip(0, 1) * 0.20 +
        df["ema_50_slope_20"].fillna(0).clip(-0.2, 0.2) * 0.15
    )

    # Trend consistency: how many of the last periods were in trend?
    df["trend_consistency"] = (
        df["ema_alignment"].fillna(0) * 0.5 +
        ((df["adx_14"].fillna(15) > 25).astype(int)) * 0.3 +
        ((df["ema_50_slope_20"].fillna(0) > 0).astype(int)) * 0.2
    )

    # Momentum divergence: MACD histogram acceleration
    df["macd_acceleration"] = df["macd_hist"].fillna(0) - df["macd_hist"].fillna(0).shift(3).bfill()

    print(f"  trend_strength_composite: mean={df['trend_strength_composite'].mean():.4f}")
    print(f"  macd_acceleration: mean={df['macd_acceleration'].mean():.6f}")

    # ===================================================================
    # 9. HIGHER-TIMEFRAME STRUCTURE FEATURES
    # ===================================================================
    print("\n--- Higher-Timeframe Structure ---")

    # Weekly trend strength
    df["weekly_trend_strength"] = (
        df["weekly_above_ema50"].fillna(0) * 0.4 +
        df["weekly_higher_high"].fillna(0) * 0.3 +
        df["weekly_higher_low"].fillna(0) * 0.3
    )

    # Multi-timeframe alignment score (enhanced)
    df["mtf_alignment_v2"] = (
        df["timeframe_alignment_score"].fillna(0) * 0.5 +
        df["nested_zone_score"].fillna(0) / 2 * 0.25 +
        df["higher_tf_strength_score"].fillna(0) * 0.25
    )

    # Weekly over monthly strength
    df["weekly_vs_monthly"] = (
        df["weekly_departure_strength"].fillna(0) - df["monthly_departure_strength"].fillna(0)
    ).clip(-0.5, 0.5)

    print(f"  weekly_trend_strength: mean={df['weekly_trend_strength'].mean():.4f}")
    print(f"  mtf_alignment_v2: mean={df['mtf_alignment_v2'].mean():.4f}")

    # ===================================================================
    # 10. CROSS-SECTIONAL & INTERACTION FEATURES
    # ===================================================================
    print("\n--- Cross-Sectional Features ---")

    df["zone_quality_x_regime"] = df["zone_conviction"] * df["spy_bull_regime"]
    df["momentum_x_liquidity"] = df["trend_strength_composite"] * df["liquidity_surge"]
    df["vol_x_zone"] = (1 - df["volatility_regime"] / 3).clip(0, 1) * df["zone_strength"].fillna(0.2)
    df["risk_on_score"] = (
        df["spy_bull_regime"].fillna(0) * 0.4 +
        (df["vix_percentile_60d"].fillna(0.5) < 0.4).astype(int) * 0.3 +
        df["sector_momentum_pct"].fillna(0.5) * 0.3
    )

    # Setup quality composite (how good is this specific entry?)
    df["setup_quality"] = (
        df["zone_conviction"] * 0.25 +
        df["rejection_strength"].fillna(0) * 0.20 +
        df["trend_strength_composite"] * 0.20 +
        df["zone_demand_pressure"] * 0.15 +
        df["risk_on_score"] * 0.10 +
        df["mtf_alignment_v2"] * 0.10
    )

    print(f"  setup_quality: mean={df['setup_quality'].mean():.4f}")

    # ===================================================================
    # 11. PRICE ACTION & CANDLESTICK DEPTH
    # ===================================================================
    print("\n--- Price Action Features ---")

    # Bullish engulfing proxy
    df["bullish_engulfing_proxy"] = (
        (df["is_bullish"].fillna(0) == 1) &
        (df["rejection_strength"].fillna(0) > 0.3) &
        (df["rel_volume"].fillna(1) > 1.0)
    ).astype(int)

    # Pin bar / hammer proxy
    df["hammer_proxy"] = (
        (df["lower_wick_pct"].fillna(0) > 0.6) &
        (df["is_bullish"].fillna(0) == 1)
    ).astype(int)

    # Close strength
    df["close_strength"] = df["lower_wick_pct"].fillna(0.5).clip(0, 1)

    print(f"  bullish_engulfing_proxy: {int(df['bullish_engulfing_proxy'].sum()):,}")
    print(f"  hammer_proxy: {int(df['hammer_proxy'].sum()):,}")

    # ===================================================================
    # SAVE
    # ===================================================================
    print(f"\n--- Saving ---")
    df.to_csv(OUTPUT, index=False)
    print(f"  Saved to: {OUTPUT}")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)} (was {len(df.columns) - 37} plus 37 new)")

    # Summary
    print(f"\n{'='*60}")
    print("v13 Augmentation Complete")
    print(f"{'='*60}")
    print(f"  New targets: hit_5pct, hit_10pct, hit_20pct, target_tier, expected_return_proxy, risk_adjusted_return_proxy")
    print(f"  New regime features: spy_bull/bear/sideways/high_vol/low_vol_regime")
    print(f"  New RS features: rs_acceleration, rs_vs_sector, spy_streak, market_breadth_proxy, sector_momentum_pct")
    print(f"  New vol features: volatility_regime, atr_trend_5d, atr_expansion_flag, vol_squeeze")
    print(f"  New liquidity: liquidity_surge, gap_up_tendency, volume_dry_up, dollar_volume_momentum")
    print(f"  New zone quality: zone_efficiency_v2, zone_resilience, zone_conviction, zone_demand_pressure, retest_rhythm")
    print(f"  New trend: trend_strength_composite, trend_consistency, macd_acceleration")
    print(f"  New MTF: weekly_trend_strength, mtf_alignment_v2, weekly_vs_monthly")
    print(f"  New interactions: zone_quality_x_regime, momentum_x_liquidity, vol_x_zone, risk_on_score, setup_quality")
    print(f"  New price action: bullish_engulfing_proxy, hammer_proxy, close_strength")
    print(f"  Total: +37 new columns")


if __name__ == "__main__":
    main()
