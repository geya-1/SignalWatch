"""
Pydantic request/response schemas.

Kept separate from the ORM models so the API's public contract can evolve
independently of the database structure.
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from utils.symbols import normalize_symbol as _normalize_symbol


# ---------- Watchlist ----------

class WatchlistAddRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        # Shared helper -- also strips exchange suffixes (.NS/.NSE/.BSE/.BO)
        # so 'RELIANCE' and 'RELIANCE.NS' resolve to the same watchlist row,
        # and DELETE (which uses the same helper) can always find it again.
        cleaned = _normalize_symbol(v)
        if not cleaned:
            raise ValueError("symbol cannot be empty")
        return cleaned


class WatchlistItem(BaseModel):
    id: int
    symbol: str
    added_at: datetime

    class Config:
        from_attributes = True


# ---------- Market ----------

class MarketQuote(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    price: Optional[float] = None
    percent_change: Optional[float] = None
    volume: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    prev_close: Optional[float] = None
    chart_points: List[float] = Field(default_factory=list)
    last_updated: datetime
    freshness: Literal["live", "cached", "market_closed"] = "live"
    is_stale: bool = False
    error: Optional[str] = None


# ---------- Change Events ----------

class ChangeEventOut(BaseModel):
    id: int
    symbol: str
    score: int
    label: str
    reasons: List[str]
    price_then: Optional[float]
    price_now: Optional[float]
    percent_change: Optional[float]
    seen: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MarkSeenRequest(BaseModel):
    symbol: Optional[str] = None
    change_event_id: Optional[int] = None
    mark_all: bool = False


# ---------- Snapshot ----------

class SnapshotCreateRequest(BaseModel):
    symbols: Optional[List[str]] = None  # if omitted, snapshot whole watchlist


class SnapshotOut(BaseModel):
    id: int
    symbol: str
    price: float
    volume: Optional[float]
    timestamp: datetime

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    detail: str


# ---------- Market Mood ----------

class MarketMoodOut(BaseModel):
    mood: Literal["Calm", "Watchful", "Active", "Volatile"]
    score: int
    icon: str
    color: str
    important_count: int
    worth_checking_count: int
    explanation: str


# ---------- Daily Replay ----------

class ReplayPricePoint(BaseModel):
    symbol: str
    price: Optional[float] = None


class ReplayStage(BaseModel):
    label: str
    prices: List[ReplayPricePoint]


class ReplayOut(BaseModel):
    stages: List[ReplayStage]
