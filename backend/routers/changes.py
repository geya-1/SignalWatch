"""Change-event (Attention Feed) endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.db import get_db
from schemas.schemas import ChangeEventOut, MarkSeenRequest
from services import watchlist_service

router = APIRouter(tags=["changes"])


@router.get("/changes", response_model=list[ChangeEventOut])
def get_changes(unseen_only: bool = Query(default=False), db: Session = Depends(get_db)):
    events = watchlist_service.get_change_events(db, unseen_only=unseen_only)
    return [
        ChangeEventOut(
            id=e.id,
            symbol=e.symbol,
            score=e.score,
            label=e.label,
            reasons=[r for r in e.reasons.split("|") if r],
            price_then=e.price_then,
            price_now=e.price_now,
            percent_change=e.percent_change,
            seen=e.seen,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.post("/mark-seen")
def mark_seen(payload: MarkSeenRequest, db: Session = Depends(get_db)):
    count = watchlist_service.mark_seen(
        db, symbol=payload.symbol, change_event_id=payload.change_event_id, mark_all=payload.mark_all
    )
    return {"marked_seen": count}
