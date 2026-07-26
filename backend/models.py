"""
Pydantic models for prediction API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class PredictRequest(BaseModel):
    symbol: str = Field(default="NVDA", description="Ticker symbol (e.g., NVDA, AAPL, TSLA)")

    model_config = {"json_schema_extra": {"example": {"symbol": "NVDA"}}}


class ZoneInfo(BaseModel):
    side: str  # "demand" or "supply"
    price: float
    upper_bound: float
    lower_bound: float
    touches: int
    age_days: int
    strength: str  # "High" | "Medium" | "Low"
    fresh: bool
    created_at: str
    win_rate: float
    avg_bounce_pct: float
    avg_duration_days: int


class IndicatorValue(BaseModel):
    value: float
    status: str  # "bullish" | "bearish" | "neutral"
    score: int   # 0-100


class TechnicalIndicators(BaseModel):
    rsi: IndicatorValue
    macd: IndicatorValue
    adx: IndicatorValue
    atr: IndicatorValue
    vwap: IndicatorValue
    ema20: IndicatorValue
    ema50: IndicatorValue
    ema200: IndicatorValue
    volume: IndicatorValue
    rvol: IndicatorValue
    trend: IndicatorValue


class FeatureImportance(BaseModel):
    name: str
    contribution: float  # 0..1
    description: str


class ReasoningItem(BaseModel):
    text: str
    weight: float  # 0..1


class TradeSetup(BaseModel):
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    position_pct: float
    shares: int
    capital: float
    profit: float
    loss: float
    kelly_pct: float
    risk_pct: float


class OHLCVCandle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class TickerInfo(BaseModel):
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
    price: float
    change: float
    change_abs: float
    open: float
    high: float
    low: float
    prev_close: float
    week_high_52: float
    week_low_52: float
    volume: float
    avg_volume: float
    market_cap: float
    pe: float
    eps: float
    beta: float
    dividend_yield: float
    description: str
    market_status: str


class PredictResponse(BaseModel):
    symbol: str
    ticker: TickerInfo
    recommendation: str  # "BUY" | "SELL" | "HOLD"
    confidence: float  # 0..1
    expected_return: float
    stop_loss_pct: float
    holding_days: int
    probability_target: float
    probability_stop: float
    entry: float
    stop_loss_price: float
    take_profit_price: float
    zones: list[ZoneInfo]
    technicals: TechnicalIndicators
    feature_importance: list[FeatureImportance]
    reasoning: list[ReasoningItem]
    trade_setup: TradeSetup
    model_name: str
    model_metadata: dict
    candles: list[OHLCVCandle]
    predicted_path: list[dict]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    features_count: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
