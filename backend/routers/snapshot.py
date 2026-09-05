"""
Snapshot endpoint.

In production this would typically be triggered by a background worker
(see docs/architecture.md) rather than the client, but exposing it as a
POST endpoint keeps the hackathon build simple: the frontend calls it on
load, then immediately calls /changes to see what's new.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from schemas.schemas import SnapshotCreateRequest, SnapshotOut
from services import watchlist_service

router = APIRouter(prefix="/snapshot", tags=["snapshot"])


@router.post("", response_model=list[SnapshotOut])
def create_snapshot(payload: SnapshotCreateRequest, db: Session = Depends(get_db)):
    snapshots = watchlist_service.snapshot_watchlist(db, symbols=payload.symbols)
    # Immediately compute change events off the back of the new snapshots
    # so the Attention Feed is fresh the moment this call returns.
    watchlist_service.compute_change_events(db, symbols=payload.symbols)
    return snapshots
