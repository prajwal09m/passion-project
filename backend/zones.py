"""
Demand and supply zone detection.
Reuses the zone detection logic from the existing pipeline.
"""

import numpy as np
import pandas as pd
from .utils import load_data


def detect_demand_zones(
    df: pd.DataFrame,
    trailing_days: int = 90,
    min_touches: int = 2,
    touch_threshold: float = 0.03,
) -> list[dict]:
    """Detect demand zones using swing-low (5-bar pivot) detection."""

    if len(df) < trailing_days:
        trailing_df = df.copy()
    else:
        trailing_df = df.tail(trailing_days).copy()

    if len(trailing_df) < min_touches + 4:
        return []

    zones = []
    lows = trailing_df["Low"].values
    dates = trailing_df.index

    for i in range(2, len(lows) - 2):
        if (lows[i] <= lows[i - 1] and lows[i] <= lows[i - 2]
                and lows[i] <= lows[i + 1] and lows[i] <= lows[i + 2]):
            zone_price = float(lows[i])

            # Get ATR for volatility-adjusted thresholds
            atr = float(trailing_df["atr_14"].iloc[i]) if "atr_14" in trailing_df.columns else None
            if atr and atr > 0 and zone_price > 0:
                thresh = 0.5 * atr / zone_price
            else:
                thresh = touch_threshold

            touches = int(np.count_nonzero(
                np.abs(lows - zone_price) / np.where(zone_price > 0, zone_price, 1) <= thresh
            ))

            # Check if zone was broken (after formation)
            broken = False
            closes = trailing_df["Close"].values
            for j in range(i, len(closes)):
                if zone_price > 0 and closes[j] < zone_price * (1 - thresh * 1.5):
                    broken = True
                    break

            if touches >= min_touches and not broken:
                zone_age = int((dates[i] - dates[max(0, i - touches)]).days) if touches > 0 else 0

                zones.append({
                    "price": float(zone_price),
                    "touches": touches,
                    "upper_bound": float(zone_price * (1 + thresh)),
                    "lower_bound": float(zone_price * (1 - thresh)),
                    "age_days": zone_age,
                    "strength": "High" if touches >= 4 else "Medium" if touches >= 3 else "Low",
                    "fresh": zone_age < 30,
                    "created_at": str(dates[i].date()) if hasattr(dates[i], "date") else str(dates[i]),
                    "win_rate": min(0.45 + touches * 0.12, 0.85),
                    "avg_bounce_pct": 0.02 + touches * 0.015,
                    "avg_duration_days": 7 + touches * 3,
                })

    # Sort by quality: more touches, fresher, lower price
    zones.sort(key=lambda z: (-z["touches"], z["age_days"], z["price"]))

    # Merge overlapping
    merged = []
    for zone in zones:
        dup = False
        for existing in merged:
            if existing["price"] > 0 and abs(zone["price"] - existing["price"]) / existing["price"] < touch_threshold:
                dup = True
                break
        if not dup:
            merged.append(zone)

    return merged[:6]  # Limit to top 6 zones


def detect_supply_zones(
    df: pd.DataFrame,
    trailing_days: int = 90,
    min_touches: int = 2,
    touch_threshold: float = 0.03,
) -> list[dict]:
    """Detect supply zones using swing-high (5-bar pivot) detection."""

    if len(df) < trailing_days:
        trailing_df = df.copy()
    else:
        trailing_df = df.tail(trailing_days).copy()

    if len(trailing_df) < min_touches + 4:
        return []

    zones = []
    highs = trailing_df["High"].values
    dates = trailing_df.index

    for i in range(2, len(highs) - 2):
        if (highs[i] >= highs[i - 1] and highs[i] >= highs[i - 2]
                and highs[i] >= highs[i + 1] and highs[i] >= highs[i + 2]):
            zone_price = float(highs[i])

            atr = float(trailing_df["atr_14"].iloc[i]) if "atr_14" in trailing_df.columns else None
            if atr and atr > 0 and zone_price > 0:
                thresh = 0.5 * atr / zone_price
            else:
                thresh = touch_threshold

            touches = int(np.count_nonzero(
                np.abs(highs - zone_price) / np.where(zone_price > 0, zone_price, 1) <= thresh
            ))

            # Check if zone was broken upward
            broken = False
            closes = trailing_df["Close"].values
            for j in range(i, len(closes)):
                if zone_price > 0 and closes[j] > zone_price * (1 + thresh * 1.5):
                    broken = True
                    break

            if touches >= min_touches and not broken:
                zone_age = int((dates[i] - dates[max(0, i - touches)]).days) if touches > 0 else 0

                zones.append({
                    "price": float(zone_price),
                    "touches": touches,
                    "upper_bound": float(zone_price * (1 + thresh)),
                    "lower_bound": float(zone_price * (1 - thresh)),
                    "age_days": zone_age,
                    "strength": "High" if touches >= 4 else "Medium" if touches >= 3 else "Low",
                    "fresh": zone_age < 30,
                    "created_at": str(dates[i].date()) if hasattr(dates[i], "date") else str(dates[i]),
                    "win_rate": min(0.45 + touches * 0.10, 0.80),
                    "avg_bounce_pct": 0.02 + touches * 0.012,
                    "avg_duration_days": 6 + touches * 2,
                })

    zones.sort(key=lambda z: (-z["touches"], z["age_days"], z["price"]))

    merged = []
    for zone in zones:
        dup = False
        for existing in merged:
            if existing["price"] > 0 and abs(zone["price"] - existing["price"]) / existing["price"] < touch_threshold:
                dup = True
                break
        if not dup:
            merged.append(zone)

    return merged[:6]
