"""Watchlist CRUD endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.db import get_db
from schemas.schemas import WatchlistAddRequest, WatchlistItem
from services import watchlist_service
from utils.symbols import normalize_symbol

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.post("", response_model=WatchlistItem, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(payload: WatchlistAddRequest, db: Session = Depends(get_db)):
    try:
        item = watchlist_service.add_symbol(db, payload.symbol)
    except ValueError as exc:
        # Duplicate symbol -> 409, not a generic 500.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return item


@router.get("", response_model=list[WatchlistItem])
def get_watchlist(db: Session = Depends(get_db)):
    return watchlist_service.list_symbols(db)


@router.delete("/{symbol}", status_code=status.HTTP_200_OK)
def delete_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    # Normalize through the same helper used on add, so 'RELIANCE.NS' and
    # 'RELIANCE' both resolve to the row that was actually stored.
    canonical = normalize_symbol(symbol)
    removed = watchlist_service.remove_symbol(db, canonical)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{symbol} not in watchlist")
    return {"detail": f"{canonical} removed"}
