"""Live market data endpoint."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.db import get_db
from schemas.schemas import MarketQuote
from services import watchlist_service
from services.market_adapter import fetch_quote, fetch_quotes

router = APIRouter(prefix="/market", tags=["market"])


@router.get("", response_model=list[MarketQuote])
def get_market_data(symbol: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    """
    Return live quotes.

    - If `symbol` is provided, fetch just that one.
    - Otherwise fetch quotes for the entire watchlist.
    - An empty watchlist returns an empty list (200), not an error --
      that's a legitimate, expected state for a new user.
    """
    if symbol:
        quotes = [fetch_quote(symbol.strip().upper())]
    else:
        symbols = [w.symbol for w in watchlist_service.list_symbols(db)]
        quotes = fetch_quotes(symbols) if symbols else []

    return [
        MarketQuote(
            symbol=q.symbol,
            company_name=q.company_name,
            price=q.price,
            percent_change=q.percent_change,
            volume=q.volume,
            day_high=q.day_high,
            day_low=q.day_low,
            prev_close=q.prev_close,
            chart_points=q.chart_points,
            last_updated=q.last_updated,
            freshness=q.freshness,
            is_stale=q.is_stale,
            error=q.error,
        )
        for q in quotes
    ]
