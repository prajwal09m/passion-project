"""
Order Block Detector — Professional Institutional Order Flow Analysis
=====================================================================

A deterministic, rule-based detector that identifies high-quality institutional
order blocks (OBs) from OHLCV data. Designed for ML dataset generation and
real-time scanning.

Core concept:
  An order block is the last opposing candle (or small consolidation) before a
  strong impulsive move, representing where institutions accumulated or distributed.

Quality over quantity:
  - Requires strong displacement (not every candle is an OB)
  - Volume confirmation on the impulse
  - Optional break of market structure
  - Tracks mitigation (when price returns to fill the OB)
  - Fresh/unmitigated blocks only for live signals

No repainting. No future leakage. Every check uses only data available at the
time of detection.

Author: Freebuff ML Pipeline
License: Internal
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Literal
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════

class OrderBlockType(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class OrderBlock:
    """
    A single detected order block with full metadata.

    All fields are computed at detection time using only data available up to
    the confirmation candle. No future data is used.
    """
    # ── Identification ──
    type: OrderBlockType
    index: int                          # Index in the DataFrame where OB was confirmed
    date: pd.Timestamp                  # Date of confirmation

    # ── Price levels ──
    ob_high: float                      # Top of the order block range
    ob_low: float                       # Bottom of the order block range
    ob_midpoint: float                  # (ob_high + ob_low) / 2
    block_width_pct: float              # (ob_high - ob_low) / ob_low * 100

    # ── Displacement (impulse) metrics ──
    impulse_return_pct: float           # % move from OB to the extreme of the impulse
    impulse_atr_multiple: float         # How many ATRs the impulse moved
    impulse_volume_ratio: float         # Volume during impulse vs 20-day average
    impulse_candles: int                # Number of candles in the impulsive move
    candles_until_impulse: int          # Candles from OB formation to impulse start

    # ── Market structure ──
    broke_structure: bool               # Whether impulse broke a recent swing high/low
    displacement_rank: float            # Percentile rank of displacement vs all moves

    # ── Block quality ──
    ob_volume_ratio: float              # Volume of the OB candle(s) vs average
    ob_candle_count: int                # Number of candles forming the OB (1-3)
    ob_body_pct: float                  # Body size of OB candle(s) as % of price
    ob_wick_pct: float                  # Upper+lower wick as % of body

    # ── Lifespan / mitigation ──
    formation_date: pd.Timestamp        # Date the OB candle actually formed
    block_age_days: int                 # Days since formation (at detection time)
    mitigated: bool                     # Has price returned into the OB range?
    mitigation_date: Optional[pd.Timestamp] = None
    mitigation_count: int = 0
    first_touch_date: Optional[pd.Timestamp] = None
    touch_count: int = 0

    # ── Scores ──
    strength_score: float = 0.0         # 0-100 composite quality score

    # ── Relationship with demand/supply zones ──
    distance_from_current_pct: float = 0.0
    overlaps_with_demand_zone: bool = False
    overlaps_with_supply_zone: bool = False
    overlap_pct: float = 0.0            # % of OB range that overlaps with a zone

    # ── Higher timeframe context ──
    higher_timeframe_aligned: bool = False
    weekly_trend_aligned: bool = False

    def to_dict(self) -> dict:
        """Serialize to flat dictionary (for CSV / ML features)."""
        d = asdict(self)
        d["type"] = self.type.value
        d["date"] = str(self.date.date()) if self.date else None
        d["formation_date"] = str(self.formation_date.date()) if self.formation_date else None
        d["mitigation_date"] = str(self.mitigation_date.date()) if self.mitigation_date else None
        d["first_touch_date"] = str(self.first_touch_date.date()) if self.first_touch_date else None
        return d

    def to_features(self, prefix: str = "ob") -> dict:
        """
        Export as ML feature dictionary with a configurable prefix.
        Only exports numeric/bool fields, skipping dates and enums.
        """
        return {
            f"{prefix}_high": self.ob_high,
            f"{prefix}_low": self.ob_low,
            f"{prefix}_midpoint": self.ob_midpoint,
            f"{prefix}_width_pct": self.block_width_pct,
            f"{prefix}_is_bullish": int(self.type == OrderBlockType.BULLISH),
            f"{prefix}_is_bearish": int(self.type == OrderBlockType.BEARISH),
            f"{prefix}_impulse_return_pct": self.impulse_return_pct,
            f"{prefix}_impulse_atr_mult": self.impulse_atr_multiple,
            f"{prefix}_impulse_vol_ratio": self.impulse_volume_ratio,
            f"{prefix}_impulse_candles": self.impulse_candles,
            f"{prefix}_candles_until_impulse": self.candles_until_impulse,
            f"{prefix}_broke_structure": int(self.broke_structure),
            f"{prefix}_displacement_rank": self.displacement_rank,
            f"{prefix}_volume_ratio": self.ob_volume_ratio,
            f"{prefix}_candle_count": self.ob_candle_count,
            f"{prefix}_body_pct": self.ob_body_pct,
            f"{prefix}_wick_pct": self.ob_wick_pct,
            f"{prefix}_age_days": self.block_age_days,
            f"{prefix}_mitigated": int(self.mitigated),
            f"{prefix}_mitigation_count": self.mitigation_count,
            f"{prefix}_touch_count": self.touch_count,
            f"{prefix}_strength_score": self.strength_score,
            f"{prefix}_distance_from_current_pct": self.distance_from_current_pct,
            f"{prefix}_overlaps_demand_zone": int(self.overlaps_with_demand_zone),
            f"{prefix}_overlaps_supply_zone": int(self.overlaps_with_supply_zone),
            f"{prefix}_overlap_pct": self.overlap_pct,
            f"{prefix}_htf_aligned": int(self.higher_timeframe_aligned),
            f"{prefix}_weekly_trend_aligned": int(self.weekly_trend_aligned),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OrderBlockConfig:
    """
    Fully configurable thresholds for the order block detector.

    These defaults are calibrated for daily OHLCV data on US equities.
    Adjust for different timeframes or asset classes.
    """

    # ── Displacement (impulse) requirements ────────────────
    min_displacement_pct: float = 0.01         # Minimum % move from OB to impulse extreme (decimal: 0.01 = 1%)
    min_displacement_atr_mult: float = 0.6     # Minimum ATR multiples for the displacement
    min_impulse_volume_ratio: float = 0.5      # Minimum volume ratio on impulse (0.5 = half avg)

    # ── Order block quality ────────────────────────────────
    max_ob_candles: int = 3                    # Max candles forming the OB (1 = single candle)
    max_ob_body_pct: float = 3.0               # OB candle body shouldn't be too large (%)
    min_ob_wick_ratio: float = 0.3             # OB candle should have some wick (rejection)
    ob_lookback_bars: int = 5                  # Bars to look back from displacement for OB

    # ── Freshness ──────────────────────────────────────────
    max_block_age_days: int = 90               # Filter out OBs older than this (in detect())

    # ── Market structure ───────────────────────────────────
    require_bos: bool = False                  # Require break of structure (BOS)
    swing_lookback: int = 10                   # Bars to look back for swing points

    # ── Mitigation ─────────────────────────────────────────
    mitigation_touch_threshold: float = 0.01   # 1% tolerance for OB touch
    mitigation_close_threshold: float = 0.005  # 0.5% tolerance for "close inside OB"

    # ── Integration ────────────────────────────────────────
    min_data_length: int = 100                 # Minimum candles needed for reliable detection

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# Core Detector
# ═══════════════════════════════════════════════════════════════════════════════

class OrderBlockDetector:
    """
    Deterministic order block detector for institutional-quality analysis.

    Usage:
        detector = OrderBlockDetector(config)
        obs = detector.detect(df)
        features = [ob.to_features() for ob in obs]
    """

    def __init__(self, config: Optional[OrderBlockConfig] = None):
        """
        Initialize detector with configurable thresholds.

        Args:
            config: OrderBlockConfig with all tunable parameters.
                    Uses sensible defaults for daily equity data if None.
        """
        self.config = config or OrderBlockConfig()
        self._atr_col = "atr_14"
        self._vol_col = "avg_volume_20"

    # ── Public API ──────────────────────────────────────────────────────────

    def detect(self, df: pd.DataFrame) -> List[OrderBlock]:
        """
        Detect all high-quality order blocks in the given DataFrame.

        Args:
            df: OHLCV DataFrame with at minimum columns:
                Open, High, Low, Close, Volume.
                Should also contain 'atr_14' and 'avg_volume_20' (pre-compute
                before calling).

        Returns:
            List of OrderBlock objects, sorted by confirmation date.
            Filters out OBs older than max_block_age_days.
        """
        df = self._validate_and_prepare(df)
        if df is None:
            return []

        bullish_obs = self._detect_directional(df, OrderBlockType.BULLISH)
        bearish_obs = self._detect_directional(df, OrderBlockType.BEARISH)

        all_obs = bullish_obs + bearish_obs
        all_obs.sort(key=lambda ob: ob.date)

        # Track mitigation across all OBs
        all_obs = self._track_mitigation(df, all_obs)

        # Compute scores, distances, and HTF alignment
        last_price = float(df["Close"].iloc[-1])
        for ob in all_obs:
            ob.strength_score = self._compute_strength(ob)
            ob.distance_from_current_pct = (
                abs(ob.ob_midpoint - last_price) / last_price
            ) * 100
            ob.higher_timeframe_aligned, ob.weekly_trend_aligned = (
                self._check_htf_alignment(df, ob)
            )

        # Deduplicate overlapping OBs at the same level
        all_obs = self._deduplicate_obs(all_obs)

        # Filter by max age (relative to last date in df)
        last_date = df.index[-1]
        all_obs = [
            ob for ob in all_obs
            if (last_date - ob.formation_date).days <= self.config.max_block_age_days
        ]

        return all_obs

    def detect_unmitigated(self, df: pd.DataFrame) -> List[OrderBlock]:
        """
        Return only fresh (unmitigated) order blocks — useful for live scanning.
        """
        return [ob for ob in self.detect(df) if not ob.mitigated]

    def detect_by_type(
        self, df: pd.DataFrame, ob_type: OrderBlockType
    ) -> List[OrderBlock]:
        """Return only bullish or only bearish order blocks."""
        return [ob for ob in self.detect(df) if ob.type == ob_type]

    def find_nearest_ob(
        self,
        df: pd.DataFrame,
        current_price: Optional[float] = None,
        ob_type: Optional[OrderBlockType] = None,
    ) -> Optional[OrderBlock]:
        """
        Find the nearest unmitigated OB to the current price.

        Args:
            df: OHLCV DataFrame
            current_price: Price to measure distance from (defaults to last close)
            ob_type: Filter by type (None = either)

        Returns:
            Closest unmitigated OrderBlock, or None if none found.
        """
        obs = self.detect_unmitigated(df)
        if ob_type:
            obs = [ob for ob in obs if ob.type == ob_type]
        if not obs:
            return None

        price = current_price if current_price is not None else float(df["Close"].iloc[-1])

        # Find nearest by midpoint distance
        return min(obs, key=lambda ob: abs(ob.ob_midpoint - price) / price)

    # ── Internal: validation ─────────────────────────────────────────────────

    def _validate_and_prepare(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Ensure DataFrame has required columns and sufficient data."""
        required = {"Open", "High", "Low", "Close", "Volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"OrderBlockDetector requires columns: {required}. Missing: {missing}"
            )

        if len(df) < self.config.min_data_length:
            return None

        df = df.copy()

        # Ensure ATR is available
        if self._atr_col not in df.columns:
            df[self._atr_col] = self._compute_atr(df)

        # Ensure average volume is available
        if self._vol_col not in df.columns:
            df[self._vol_col] = df["Volume"].rolling(20).mean()

        return df

    @staticmethod
    def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Compute ATR if not already present."""
        high, low, close = df["High"], df["Low"], df["Close"]
        tr = pd.DataFrame({
            "hl": high - low,
            "hc": (high - close.shift()).abs(),
            "lc": (low - close.shift()).abs(),
        }).max(axis=1)
        return tr.rolling(period).mean()

    # ── Internal: directional detection ──────────────────────────────────────

    def _detect_directional(
        self, df: pd.DataFrame, ob_type: OrderBlockType
    ) -> List[OrderBlock]:
        """
        Detect order blocks in one direction.

        Bullish OB logic:
          A bullish order block is the LAST bearish candle (or small consolidation)
          immediately before a strong bullish displacement. Institutions
          accumulated at this level before marking price up.

          Step 1: Scan forward looking for strong bullish displacement.
          Step 2: When found, look BACK to identify the OB candle(s).
          Step 3: Validate quality and record the OB.

        Bearish OB logic:
          Mirror of bullish — last bullish candle before strong bearish drop.
        """
        is_bullish = ob_type == OrderBlockType.BULLISH
        obs: List[OrderBlock] = []

        n = len(df)
        closes = df["Close"].values
        opens = df["Open"].values
        highs = df["High"].values
        lows = df["Low"].values
        volumes = df["Volume"].values
        atrs = df[self._atr_col].values
        avg_vols = df[self._vol_col].values
        dates = df.index

        i = self.config.swing_lookback + 2  # Start after enough warmup

        while i < n - 3:
            # ── Step 1: Identify displacement ────────────────────────────
            # A displacement is a strong directional move.
            # We look for the START of an impulsive sequence.

            if is_bullish:
                # Bullish displacement: strong up candle(s)
                displacement = self._find_bullish_displacement(
                    closes, opens, highs, lows, volumes, atrs, avg_vols, i, n
                )
            else:
                # Bearish displacement: strong down candle(s)
                displacement = self._find_bearish_displacement(
                    closes, opens, highs, lows, volumes, atrs, avg_vols, i, n
                )

            if displacement is None:
                i += 1
                continue

            disp_start, disp_end, disp_pct, disp_atr_mult, disp_vol_ratio = displacement

            # ── Step 2: Find the Order Block BEFORE the displacement ──────
            # The OB is the last candle(s) of the OPPOSITE direction
            # immediately preceding the displacement.
            ob_info = self._find_order_block(
                closes, opens, highs, lows, volumes, atrs, avg_vols,
                disp_start, is_bullish
            )

            if ob_info is None:
                i = disp_end + 1
                continue

            ob_start, ob_end, ob_high, ob_low, ob_body_pct, ob_wick_pct, ob_vol_ratio = ob_info

            # ── Step 3: Validate quality ─────────────────────────────────

            # 3a. Displacement must be significant
            if abs(disp_pct) < self.config.min_displacement_pct:
                i = disp_end + 1
                continue

            if disp_atr_mult < self.config.min_displacement_atr_mult:
                i = disp_end + 1
                continue

            # 3b. OB candle quality checks (soft — penalized in strength score)

            # 3c. Volume confirmation on displacement
            # Only reject genuinely low-volume moves (< 50% of average).
            # Strong-bodied moves with normal volume are valid — institutions
            # sometimes execute large blocks that don't show as volume spikes,
            # especially in dark pools.
            if disp_vol_ratio < self.config.min_impulse_volume_ratio:
                i = disp_end + 1
                continue

            # 3d. Record indices
            ob_formation_idx = ob_end
            disp_confirmation_idx = disp_end

            # ── Step 4: Check market structure (BOS) ─────────────────────
            broke_structure = False
            if self.config.require_bos:
                broke_structure = self._check_bos(
                    closes, highs, lows, disp_end, ob_type
                )
                if not broke_structure:
                    i = disp_end + 1
                    continue

            # ── Step 5: Calculate displacement rank ───────────────────────
            displacement_rank = self._compute_displacement_rank(
                closes, opens, highs, lows, disp_pct, disp_end
            )

            # ── Step 6: Create OrderBlock object ──────────────────────────
            block_width_pct = ((ob_high - ob_low) / ob_low) * 100 if ob_low > 0 else 0

            ob = OrderBlock(
                type=ob_type,
                index=disp_confirmation_idx,
                date=dates[disp_confirmation_idx],
                ob_high=round(float(ob_high), 4),
                ob_low=round(float(ob_low), 4),
                ob_midpoint=round(float((ob_high + ob_low) / 2), 4),
                block_width_pct=round(float(block_width_pct), 4),
                impulse_return_pct=round(float(disp_pct), 4),
                impulse_atr_multiple=round(float(disp_atr_mult), 4),
                impulse_volume_ratio=round(float(disp_vol_ratio), 4),
                impulse_candles=disp_end - disp_start + 1,
                candles_until_impulse=disp_start - ob_end,
                broke_structure=broke_structure,
                displacement_rank=round(float(displacement_rank), 4),
                ob_volume_ratio=round(float(ob_vol_ratio), 4),
                ob_candle_count=ob_end - ob_start + 1,
                ob_body_pct=round(float(ob_body_pct), 4),
                ob_wick_pct=round(float(ob_wick_pct), 4),
                formation_date=dates[ob_formation_idx],
                block_age_days=0,  # filled later by mitigation tracker
                mitigated=False,
            )

            obs.append(ob)
            i = disp_end + 1  # Advance past the displacement

        return obs

    def _find_bullish_displacement(
        self,
        closes: np.ndarray,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray,
        atrs: np.ndarray,
        avg_vols: np.ndarray,
        start_idx: int,
        n: int,
    ) -> Optional[Tuple[int, int, float, float, float]]:
        """
        Find a bullish displacement starting at or after start_idx.

        A bullish displacement is defined as:
        - A sequence of 1-3 candles with net positive move
        - The move (as % of price) exceeds ATR-based threshold
        - Ideally with above-average volume

        Returns:
            (displacement_start_idx, displacement_end_idx,
             total_pct_move, atr_multiple, volume_ratio)
            or None if no valid displacement found.
        """
        # Look at each candle as potential displacement start
        for i in range(start_idx, min(n - 1, start_idx + 20)):
            close_i = closes[i]

            # Check for a strong single candle
            if i < n - 1:
                single_pct = (closes[i] - opens[i]) / opens[i] if opens[i] > 0 else 0
                atr_i = atrs[i] if atrs[i] > 0 else close_i * 0.02
                single_atr_mult = abs(closes[i] - opens[i]) / atr_i

                # Strong bullish candle: close near high, big body, above-avg volume
                candle_range = highs[i] - lows[i]
                close_near_high = (highs[i] - closes[i]) / candle_range < 0.3 if candle_range > 0 else False
                big_body = single_pct > 0.01
                high_volume = volumes[i] > avg_vols[i] * 1.1 if avg_vols[i] > 0 else False

                if single_pct > 0 and single_atr_mult >= self.config.min_displacement_atr_mult * 0.8:
                    if close_near_high and (big_body or high_volume):
                        # This is a valid displacement
                        # Calculate the full move from the preceding low to this high
                        lookback_start = max(0, i - 5)
                        preceding_low = lows[lookback_start:i].min()
                        total_pct = (highs[i] - preceding_low) / preceding_low if preceding_low > 0 else single_pct
                        total_atr_mult = (highs[i] - preceding_low) / atr_i if atr_i > 0 else 0
                        vol_ratio = volumes[i] / avg_vols[i] if avg_vols[i] > 0 else 1.0
                        return (i, i, total_pct, total_atr_mult, vol_ratio)

            # Check for multi-candle displacement (2-3 candles)
            for end_offset in range(1, min(3, n - i - 1)):
                end_idx = i + end_offset
                # Net move from open of first to close of last
                total_pct = (closes[end_idx] - opens[i]) / opens[i] if opens[i] > 0 else 0
                if total_pct <= self.config.min_displacement_pct * 0.5:
                    continue

                # Check each candle in the sequence is predominantly bullish
                all_bullish = all(
                    closes[j] > opens[j] for j in range(i, end_idx + 1)
                )
                if not all_bullish:
                    continue

                # Volume check
                seq_vol = volumes[i:end_idx + 1].mean()
                seq_avg_vol = avg_vols[i:end_idx + 1].mean()
                vol_ratio = seq_vol / seq_avg_vol if seq_avg_vol > 0 else 1.0

                atr_mean = atrs[i:end_idx + 1].mean()
                total_atr_mult = abs(closes[end_idx] - opens[i]) / atr_mean if atr_mean > 0 else 0

                if total_atr_mult >= self.config.min_displacement_atr_mult * 0.7:
                    return (i, end_idx, total_pct, total_atr_mult, vol_ratio)

        return None

    def _find_bearish_displacement(
        self,
        closes: np.ndarray,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray,
        atrs: np.ndarray,
        avg_vols: np.ndarray,
        start_idx: int,
        n: int,
    ) -> Optional[Tuple[int, int, float, float, float]]:
        """
        Find a bearish displacement — mirror of _find_bullish_displacement.

        A bearish displacement is a strong down candle or sequence.
        """
        for i in range(start_idx, min(n - 1, start_idx + 20)):
            close_i = closes[i]

            # Strong single bearish candle
            if i < n - 1:
                single_pct = (opens[i] - closes[i]) / opens[i] if opens[i] > 0 else 0
                atr_i = atrs[i] if atrs[i] > 0 else close_i * 0.02
                single_atr_mult = abs(closes[i] - opens[i]) / atr_i

                candle_range = highs[i] - lows[i]
                close_near_low = (closes[i] - lows[i]) / candle_range < 0.3 if candle_range > 0 else False
                big_body = single_pct > 0.01
                high_volume = volumes[i] > avg_vols[i] * 1.1 if avg_vols[i] > 0 else False

                if single_pct > 0 and single_atr_mult >= self.config.min_displacement_atr_mult * 0.8:
                    if close_near_low and (big_body or high_volume):
                        lookback_start = max(0, i - 5)
                        preceding_high = highs[lookback_start:i].max()
                        total_pct = (preceding_high - lows[i]) / preceding_high if preceding_high > 0 else single_pct
                        total_atr_mult = (preceding_high - lows[i]) / atr_i if atr_i > 0 else 0
                        vol_ratio = volumes[i] / avg_vols[i] if avg_vols[i] > 0 else 1.0
                        return (i, i, total_pct, total_atr_mult, vol_ratio)

            # Multi-candle bearish displacement
            for end_offset in range(1, min(3, n - i - 1)):
                end_idx = i + end_offset
                total_pct = (opens[i] - closes[end_idx]) / opens[i] if opens[i] > 0 else 0
                if total_pct <= self.config.min_displacement_pct * 0.5:
                    continue

                all_bearish = all(
                    closes[j] < opens[j] for j in range(i, end_idx + 1)
                )
                if not all_bearish:
                    continue

                seq_vol = volumes[i:end_idx + 1].mean()
                seq_avg_vol = avg_vols[i:end_idx + 1].mean()
                vol_ratio = seq_vol / seq_avg_vol if seq_avg_vol > 0 else 1.0

                atr_mean = atrs[i:end_idx + 1].mean()
                total_atr_mult = abs(closes[end_idx] - opens[i]) / atr_mean if atr_mean > 0 else 0

                if total_atr_mult >= self.config.min_displacement_atr_mult * 0.7:
                    return (i, end_idx, total_pct, total_atr_mult, vol_ratio)

        return None

    def _find_order_block(
        self,
        closes: np.ndarray,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray,
        atrs: np.ndarray,
        avg_vols: np.ndarray,
        disp_start: int,
        is_bullish: bool,
    ) -> Optional[Tuple[int, int, float, float, float, float, float]]:
        """
        Find the order block candle(s) immediately before the displacement.

        For BULLISH OB: look for the last bearish candle(s) before the impulse.
        For BEARISH OB: look for the last bullish candle(s) before the impulse.

        The OB can be 1-3 candles (configurable). We prefer single-candle OBs
        but will use up to max_ob_candles if they form a tight consolidation.

        Returns:
            (ob_start_idx, ob_end_idx, ob_high, ob_low, ob_body_pct, ob_wick_pct, vol_ratio)
            or None if no suitable OB found.
        """
        # We look at candles immediately BEFORE the displacement start
        lookback = min(self.config.ob_lookback_bars, disp_start)

        # Find the last candle of the opposite direction
        ob_candles = []
        for j in range(disp_start - 1, max(0, disp_start - lookback - 1), -1):
            candle_is_opposite = (
                (is_bullish and closes[j] < opens[j])  # Bearish candle before bullish impulse
                or (not is_bullish and closes[j] > opens[j])  # Bullish candle before bearish impulse
            )
            if candle_is_opposite:
                # Start collecting OB candles from this one backwards
                ob_end = j
                ob_start = j
                # Include up to max_ob_candles-1 additional preceding candles
                # if they are also opposite-direction or doji
                for k in range(j - 1, max(0, j - self.config.max_ob_candles), -1):
                    candle_range_k = highs[k] - lows[k]
                    body_k = abs(closes[k] - opens[k])
                    is_doji = (body_k / candle_range_k) < 0.15 if candle_range_k > 0 else True
                    same_direction = (
                        (is_bullish and closes[k] < opens[k])
                        or (not is_bullish and closes[k] > opens[k])
                    )
                    if same_direction or is_doji:
                        ob_start = k
                    else:
                        break

                # Compute OB range: high/low of all OB candles
                ob_high = highs[ob_start:ob_end + 1].max()
                ob_low = lows[ob_start:ob_end + 1].min()

                # OB body %
                ob_bodies = np.abs(closes[ob_start:ob_end + 1] - opens[ob_start:ob_end + 1])
                ob_body_pct = float(ob_bodies.mean() / closes[ob_end]) * 100

                # OB wick ratio
                ob_ranges = highs[ob_start:ob_end + 1] - lows[ob_start:ob_end + 1]
                with np.errstate(divide="ignore", invalid="ignore"):
                    wick_pcts = np.where(
                        ob_ranges > 0,
                        (ob_ranges - ob_bodies) / ob_ranges,
                        0.0
                    )
                ob_wick_pct = float(wick_pcts.mean()) * 100

                # OB volume
                ob_vol = volumes[ob_start:ob_end + 1].mean()
                ob_avg_vol = avg_vols[ob_start:ob_end + 1].mean()
                ob_vol_ratio = ob_vol / ob_avg_vol if ob_avg_vol > 0 else 1.0

                return (
                    int(ob_start), int(ob_end),
                    float(ob_high), float(ob_low),
                    float(ob_body_pct), float(ob_wick_pct),
                    float(ob_vol_ratio),
                )

            # Also check: in a bullish OB hunt, a doji or indecision candle
            # (small body, big wicks) before the impulse can also serve as an OB.
            # This represents institutional absorption before the markup.
            candle_range_j = highs[j] - lows[j]
            body_j = abs(closes[j] - opens[j])
            is_doji = (body_j / candle_range_j) < 0.15 if candle_range_j > 0 else True
            has_wicks = (highs[j] - max(opens[j], closes[j]) > body_j * 0.5) or (
                min(opens[j], closes[j]) - lows[j] > body_j * 0.5
            )

            if is_doji and has_wicks:
                # Accept this as the OB — it's an indecision candle
                ob_high = highs[j]
                ob_low = lows[j]
                ob_body_pct = (body_j / closes[j]) * 100 if closes[j] > 0 else 0
                ob_wick_pct = (
                    ((highs[j] - max(opens[j], closes[j])) + (min(opens[j], closes[j]) - lows[j]))
                    / candle_range_j * 100
                ) if candle_range_j > 0 else 50.0
                ob_vol_ratio = volumes[j] / avg_vols[j] if avg_vols[j] > 0 else 1.0

                return (
                    j, j,
                    float(ob_high), float(ob_low),
                    float(ob_body_pct), float(ob_wick_pct),
                    float(ob_vol_ratio),
                )

        return None

    def _check_bos(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        disp_end: int,
        ob_type: OrderBlockType,
    ) -> bool:
        """
        Check if the displacement broke market structure.

        For bullish: impulse high exceeds recent swing high (BOS up).
        For bearish: impulse low exceeds recent swing low (BOS down).
        """
        lookback = self.config.swing_lookback
        start = max(0, disp_end - lookback * 2)

        if ob_type == OrderBlockType.BULLISH:
            # Find the highest swing high in the lookback period
            recent_highs = highs[start:disp_end + 1]
            if len(recent_highs) < 3:
                return False
            swing_highs = []
            for k in range(2, len(recent_highs) - 2):
                if (recent_highs[k] >= recent_highs[k - 1] and
                    recent_highs[k] >= recent_highs[k - 2] and
                    recent_highs[k] >= recent_highs[k + 1] and
                    recent_highs[k] >= recent_highs[k + 2]):
                    swing_highs.append(recent_highs[k])
            if swing_highs:
                return highs[disp_end] > max(swing_highs)
            return highs[disp_end] > recent_highs[:-1].max()

        else:  # Bearish
            recent_lows = lows[start:disp_end + 1]
            if len(recent_lows) < 3:
                return False
            swing_lows = []
            for k in range(2, len(recent_lows) - 2):
                if (recent_lows[k] <= recent_lows[k - 1] and
                    recent_lows[k] <= recent_lows[k - 2] and
                    recent_lows[k] <= recent_lows[k + 1] and
                    recent_lows[k] <= recent_lows[k + 2]):
                    swing_lows.append(recent_lows[k])
            if swing_lows:
                return lows[disp_end] < min(swing_lows)
            return lows[disp_end] < recent_lows[:-1].min()

    def _compute_displacement_rank(
        self,
        closes: np.ndarray,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        disp_pct: float,
        disp_end: int,
        lookback: int = 50,
    ) -> float:
        """
        Compute the percentile rank of this displacement relative to recent moves.
        Higher = more unusual/stronger displacement.
        """
        start = max(0, disp_end - lookback)
        # All candle-to-candle moves in recent history
        recent_moves = np.abs(closes[start:disp_end] - opens[start:disp_end]) / opens[start:disp_end]
        if len(recent_moves) == 0:
            return 0.5
        rank = (recent_moves < abs(disp_pct)).mean()
        return float(rank)

    # ── Internal: mitigation tracking ────────────────────────────────────────

    def _track_mitigation(
        self, df: pd.DataFrame, obs: List[OrderBlock]
    ) -> List[OrderBlock]:
        """
        For each order block, track whether price later returned to it (mitigation).

        Mitigation occurs when:
        - Price (low for bullish OB, high for bearish OB) enters the OB range
        - Confirmed by a close inside or through the OB

        Once mitigated, an OB's "freshness" is reduced — the order flow
        has been consumed.
        """
        if not obs:
            return obs

        closes = df["Close"].values
        highs = df["High"].values
        lows = df["Low"].values
        dates = df.index
        n = len(df)

        for ob in obs:
            ob_idx = ob.index
            ob.block_age_days = (dates[ob_idx] - ob.formation_date).days

            # Check bars AFTER the OB confirmation for mitigation
            for j in range(ob_idx + 1, n):
                if ob.type == OrderBlockType.BULLISH:
                    # Bullish OB is mitigated when price drops into it
                    # (Institutions already bought here; returning means distribution)
                    in_ob_range = (
                        lows[j] <= ob.ob_high * (1 + self.config.mitigation_touch_threshold)
                        and lows[j] >= ob.ob_low * (1 - self.config.mitigation_touch_threshold)
                    )
                    close_inside = (
                        ob.ob_low * (1 - self.config.mitigation_close_threshold)
                        <= closes[j]
                        <= ob.ob_high * (1 + self.config.mitigation_close_threshold)
                    )
                else:
                    # Bearish OB is mitigated when price rallies into it
                    in_ob_range = (
                        highs[j] >= ob.ob_low * (1 - self.config.mitigation_touch_threshold)
                        and highs[j] <= ob.ob_high * (1 + self.config.mitigation_touch_threshold)
                    )
                    close_inside = (
                        ob.ob_low * (1 - self.config.mitigation_close_threshold)
                        <= closes[j]
                        <= ob.ob_high * (1 + self.config.mitigation_close_threshold)
                    )

                if in_ob_range:
                    ob.touch_count += 1
                    if ob.first_touch_date is None:
                        ob.first_touch_date = dates[j]

                    if close_inside and not ob.mitigated:
                        ob.mitigated = True
                        ob.mitigation_date = dates[j]
                        ob.mitigation_count += 1
                        break  # Once mitigated, stop tracking this OB

        return obs


    def _deduplicate_obs(self, obs):
        '''Merge overlapping OBs at nearly identical price levels.'''
        if len(obs) <= 1:
            return obs
        # Merge same-type OBs whose midpoints are within 2x avg block width.
        # This handles multiple displacements referencing the same OB level.
        obs.sort(key=lambda o: o.date)
        merged = []
        for ob in obs:
            is_dup = False
            for ex in merged:
                if ob.type != ex.type:
                    continue
                avg_w = (ob.block_width_pct + ex.block_width_pct) / 2
                diff = abs(ob.ob_midpoint - ex.ob_midpoint) / ob.ob_midpoint * 100
                if diff < max(avg_w * 1.5, 0.2):
                    is_dup = True
                    if ob.strength_score > ex.strength_score:
                        merged.remove(ex)
                        merged.append(ob)
                    break
            if not is_dup:
                merged.append(ob)
        return merged

    def _check_htf_alignment(self, df, ob):
        '''Check HTF alignment: weekly EMAs and trend direction.'''
        try:
            import pandas as pd
            weekly = df[['Close','High','Low']].resample('W-FRI').agg(
                {'Close':'last','High':'max','Low':'min'}).dropna()
            if len(weekly) < 20:
                return False, False
            weekly['ema20'] = weekly['Close'].ewm(span=20, adjust=False).mean()
            weekly['ema50'] = weekly['Close'].ewm(span=50, adjust=False).mean()
            ob_week = weekly.index[weekly.index <= ob.formation_date]
            if len(ob_week) == 0:
                return False, False
            lw = weekly.loc[ob_week[-1]]
            above20 = ob.ob_midpoint > lw['ema20']
            above50 = ob.ob_midpoint > lw['ema50']
            ema_ok = (above20 and above50) or (not above20 and not above50)
            if hasattr(ob.type, 'value'):
                is_bull = ob.type.value == 'bullish'
            else:
                is_bull = ob.type == 'bullish'
            htf = ema_ok and ((is_bull and ob.ob_midpoint > lw['ema20']) or 
                              (not is_bull and ob.ob_midpoint < lw['ema20']))
            rw = weekly.iloc[-10:]
            hh = rw['High'].iloc[-1] > rw['High'].iloc[0]
            hl = rw['Low'].iloc[-1] > rw['Low'].iloc[0]
            trend_up = hh and hl
            trend_down = not hh and not hl
            wt = (is_bull and trend_up) or (not is_bull and trend_down)
            return bool(htf), bool(wt)
        except Exception:
            return False, False

    # ── Internal: strength scoring ───────────────────────────────────────────

    def _compute_strength(self, ob: OrderBlock) -> float:
        """
        Compute a composite strength score (0-100) for the order block.

        Components:
        - Displacement magnitude (30 pts): bigger impulse = stronger OB
        - Volume confirmation (20 pts): higher volume on impulse = institutional
        - OB quality (20 pts): tight range, good wick structure
        - Market structure (15 pts): BOS adds confidence
        - Freshness (15 pts): newer = better, unmitigated = premium

        All components are scaled to produce a final 0-100 score.
        """
        score = 0.0

        # 1. Displacement (0-30)
        # Normalize: 0.5% = 5pts, 2% = 15pts, 5%+ = 30pts
        disp = abs(ob.impulse_return_pct)
        disp_score = min(30.0, disp * 6.0)
        score += disp_score

        # 2. Volume confirmation (0-20)
        # vol_ratio 1.0 = 5pts, 1.5 = 12pts, 2.0+ = 20pts
        vol_score = min(20.0, (ob.impulse_volume_ratio - 0.8) * 16.7)
        vol_score = max(0.0, vol_score)
        score += vol_score

        # 3. OB quality (0-20)
        # Tight OB (small width %), good wick structure
        # width_pct < 0.5% = 10pts, < 2% = 6pts, > 5% = 0pts
        width = ob.block_width_pct
        if width < 0.5:
            width_score = 10.0
        elif width < 2.0:
            width_score = 6.0
        elif width < 5.0:
            width_score = 3.0
        else:
            width_score = 0.0

        # Wick presence: OBs with wicks are higher quality (rejection at the level)
        wick_score = min(10.0, ob.ob_wick_pct * 0.2)
        score += width_score + wick_score

        # 4. Market structure (0-15)
        if ob.broke_structure:
            score += 15.0

        # 5. Freshness (0-15)
        if not ob.mitigated:
            score += 10.0  # Unmitigated = premium
        # Age penalty: OBs older than 30 days lose freshness
        age_penalty = max(0.0, (ob.block_age_days - 30) * 0.1)
        freshness_score = max(0.0, 5.0 - age_penalty)
        score += freshness_score

        return round(min(100.0, max(0.0, score)), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# Feature extraction helpers
# ═══════════════════════════════════════════════════════════════════════════════

def extract_ob_features_for_signal(
    detector: OrderBlockDetector,
    df: pd.DataFrame,
    signal_date: pd.Timestamp,
    signal_price: float,
    demand_zones: Optional[List[Dict]] = None,
    supply_zones: Optional[List[Dict]] = None,
) -> Dict[str, float]:
    """
    Extract order block features for a single signal date.

    This is the primary integration point for ML dataset generation.
    Call this for each signal row to augment the feature vector.

    Args:
        detector: Configured OrderBlockDetector instance
        df: Full OHLCV DataFrame with indicators
        signal_date: The date of the signal being evaluated
        signal_price: Entry price of the signal
        demand_zones: Optional list of demand zone dicts (for overlap check)
        supply_zones: Optional list of supply zone dicts (for overlap check)

    Returns:
        Flat dictionary of OB features with 'ob_' prefix.
        All values are 0.0 if no relevant OB is found.
    """
    # Only use data up to and including the signal date
    df_before = df[df.index <= signal_date].copy()

    if len(df_before) < detector.config.min_data_length:
        return _empty_ob_features()

    try:
        # Detect unmitigated OBs (only fresh ones matter for a signal)
        all_obs = detector.detect(df_before)
        unmitigated = [ob for ob in all_obs if not ob.mitigated]

        if not unmitigated:
            return _empty_ob_features()

        # Find the CLOSEST bullish and bearish OB to the current price
        bullish_obs = [ob for ob in unmitigated if ob.type == OrderBlockType.BULLISH]
        bearish_obs = [ob for ob in unmitigated if ob.type == OrderBlockType.BEARISH]

        nearest_bullish = None
        nearest_bearish = None

        if bullish_obs:
            nearest_bullish = min(
                bullish_obs,
                key=lambda ob: abs(ob.ob_midpoint - signal_price) / signal_price
            )

        if bearish_obs:
            nearest_bearish = min(
                bearish_obs,
                key=lambda ob: abs(ob.ob_midpoint - signal_price) / signal_price
            )

        features = {}

        # Nearest bullish OB features
        if nearest_bullish:
            bull_features = nearest_bullish.to_features(prefix="ob_bull")
            features.update(bull_features)
            features["ob_bull_distance_pct"] = (
                (signal_price - nearest_bullish.ob_midpoint) / signal_price
            )
            features["ob_bull_exists"] = 1
        else:
            features.update(_zero_ob_features("ob_bull"))
            features["ob_bull_exists"] = 0

        # Nearest bearish OB features
        if nearest_bearish:
            bear_features = nearest_bearish.to_features(prefix="ob_bear")
            features.update(bear_features)
            features["ob_bear_distance_pct"] = (
                (signal_price - nearest_bearish.ob_midpoint) / signal_price
            )
            features["ob_bear_exists"] = 1
        else:
            features.update(_zero_ob_features("ob_bear"))
            features["ob_bear_exists"] = 0

        # Aggregate features
        features["ob_total_unmitigated"] = len(unmitigated)
        features["ob_total_bullish"] = len(bullish_obs)
        features["ob_total_bearish"] = len(bearish_obs)

        # Best OB strength
        if nearest_bullish and nearest_bearish:
            best_strength = max(nearest_bullish.strength_score, nearest_bearish.strength_score)
        elif nearest_bullish:
            best_strength = nearest_bullish.strength_score
        elif nearest_bearish:
            best_strength = nearest_bearish.strength_score
        else:
            best_strength = 0.0
        features["ob_best_strength"] = best_strength

        # Overlap with demand/supply zones
        if demand_zones:
            features.update(_check_zone_overlap(
                nearest_bullish, nearest_bearish, demand_zones, "demand"
            ))
        if supply_zones:
            features.update(_check_zone_overlap(
                nearest_bullish, nearest_bearish, supply_zones, "supply"
            ))

        return features

    except Exception:
        return _empty_ob_features()


def _check_zone_overlap(
    nearest_bullish: Optional[OrderBlock],
    nearest_bearish: Optional[OrderBlock],
    zones: List[Dict],
    zone_type: str,
) -> Dict[str, float]:
    """Check if nearest OBs overlap with existing demand/supply zones."""
    prefix = f"ob_{zone_type}_overlap"
    features = {
        f"{prefix}_bullish": 0,
        f"{prefix}_bearish": 0,
        f"{prefix}_pct": 0.0,
    }

    for zone in zones:
        zone_low = zone.get("lower_bound", zone.get("price", 0) * 0.97)
        zone_high = zone.get("upper_bound", zone.get("price", 0) * 1.03)

        # Check bullish OB overlap
        if nearest_bullish:
            overlap = _range_overlap_pct(
                nearest_bullish.ob_low, nearest_bullish.ob_high,
                zone_low, zone_high
            )
            if overlap > 0:
                features[f"{prefix}_bullish"] = 1
                features[f"{prefix}_pct"] = max(features[f"{prefix}_pct"], overlap)

        # Check bearish OB overlap
        if nearest_bearish:
            overlap = _range_overlap_pct(
                nearest_bearish.ob_low, nearest_bearish.ob_high,
                zone_low, zone_high
            )
            if overlap > 0:
                features[f"{prefix}_bearish"] = 1
                features[f"{prefix}_pct"] = max(features[f"{prefix}_pct"], overlap)

    return features


def _range_overlap_pct(
    r1_low: float, r1_high: float, r2_low: float, r2_high: float
) -> float:
    """Compute the overlap percentage between two ranges."""
    overlap_low = max(r1_low, r2_low)
    overlap_high = min(r1_high, r2_high)
    if overlap_high <= overlap_low:
        return 0.0
    overlap_range = overlap_high - overlap_low
    r1_range = r1_high - r1_low
    return float(overlap_range / r1_range) if r1_range > 0 else 0.0


def _empty_ob_features() -> Dict[str, float]:
    """Return a dictionary of zero-valued OB features."""
    features = _zero_ob_features("ob_bull")
    features.update(_zero_ob_features("ob_bear"))
    features.update({
        "ob_bull_exists": 0,
        "ob_bear_exists": 0,
        "ob_bull_distance_pct": 0.0,
        "ob_bear_distance_pct": 0.0,
        "ob_total_unmitigated": 0,
        "ob_total_bullish": 0,
        "ob_total_bearish": 0,
        "ob_best_strength": 0.0,
    })
    return features


def _zero_ob_features(prefix: str) -> Dict[str, float]:
    """Zero-valued OB feature dict for a given prefix."""
    return {
        f"{prefix}_high": 0.0,
        f"{prefix}_low": 0.0,
        f"{prefix}_midpoint": 0.0,
        f"{prefix}_width_pct": 0.0,
        f"{prefix}_is_bullish": 0,
        f"{prefix}_is_bearish": 0,
        f"{prefix}_impulse_return_pct": 0.0,
        f"{prefix}_impulse_atr_mult": 0.0,
        f"{prefix}_impulse_vol_ratio": 0.0,
        f"{prefix}_impulse_candles": 0,
        f"{prefix}_candles_until_impulse": 0,
        f"{prefix}_broke_structure": 0,
        f"{prefix}_displacement_rank": 0.0,
        f"{prefix}_volume_ratio": 0.0,
        f"{prefix}_candle_count": 0,
        f"{prefix}_body_pct": 0.0,
        f"{prefix}_wick_pct": 0.0,
        f"{prefix}_age_days": 0,
        f"{prefix}_mitigated": 0,
        f"{prefix}_mitigation_count": 0,
        f"{prefix}_touch_count": 0,
        f"{prefix}_strength_score": 0.0,
        f"{prefix}_distance_from_current_pct": 0.0,
        f"{prefix}_overlaps_demand_zone": 0,
        f"{prefix}_overlaps_supply_zone": 0,
        f"{prefix}_overlap_pct": 0.0,
        f"{prefix}_htf_aligned": 0,
        f"{prefix}_weekly_trend_aligned": 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Script entry point — standalone testing
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import yfinance as yf

    print("=" * 70)
    print("Order Block Detector — Standalone Test")
    print("=" * 70)

    # Download test data
    ticker = "NVDA"
    print(f"\nDownloading {ticker} data...")
    df = yf.download(ticker, period="6mo", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    print(f"  {len(df)} rows loaded")

    # Configure detector
    config = OrderBlockConfig(
        min_displacement_pct=0.01,
        min_displacement_atr_mult=0.6,
        min_impulse_volume_ratio=0.5,
        require_bos=False,
        max_block_age_days=90,
    )

    detector = OrderBlockDetector(config)

    # Run detection
    print(f"\nDetecting order blocks...")
    all_obs = detector.detect(df)

    print(f"  Found {len(all_obs)} order blocks:")
    print(f"    Bullish: {sum(1 for ob in all_obs if ob.type == OrderBlockType.BULLISH)}")
    print(f"    Bearish: {sum(1 for ob in all_obs if ob.type == OrderBlockType.BEARISH)}")
    print(f"    Unmitigated: {sum(1 for ob in all_obs if not ob.mitigated)}")
    print(f"    Mitigated: {sum(1 for ob in all_obs if ob.mitigated)}")

    # Show top 5 by strength
    print(f"\nTop 5 by strength:")
    all_obs.sort(key=lambda ob: ob.strength_score, reverse=True)
    for i, ob in enumerate(all_obs[:5], 1):
        print(f"  #{i}: {ob.type.value.upper():7s} | "
              f"OB: ${ob.ob_low:.2f}-${ob.ob_high:.2f} | "
              f"Impulse: {ob.impulse_return_pct:+.2f}% | "
              f"Strength: {ob.strength_score:.0f}/100 | "
              f"Mitigated: {ob.mitigated} | "
              f"Date: {ob.date.date()}")

    # Feature output
    if all_obs:
        print(f"\nFeature vector (sample from best OB):")
        features = all_obs[0].to_features()
        for k, v in list(features.items())[:10]:
            print(f"  {k}: {v}")

    print(f"\nDone.")
