"""
Insights endpoints: Market Mood and Daily Replay.

Both are read-only rollups of data the app already computes and stores
(ChangeEvents and Snapshots) -- this router stays thin and delegates
everything to watchlist_service, same as every other router in the app.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from schemas.schemas import MarketMoodOut, ReplayOut
from services import watchlist_service

router = APIRouter(tags=["insights"])


@router.get("/mood", response_model=MarketMoodOut)
def get_market_mood(db: Session = Depends(get_db)):
    """One-line rollup of the Attention Feed: how much does today deserve
    your attention, at a glance."""
    return watchlist_service.get_market_mood(db)


@router.get("/replay", response_model=ReplayOut)
def get_daily_replay(db: Session = Depends(get_db)):
    """Morning / Afternoon / Now prices for everything on the watchlist."""
    return watchlist_service.get_daily_replay(db)
