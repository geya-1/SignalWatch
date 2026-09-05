"""
SQLAlchemy ORM models.

Tables:
    User         - a person using SignalWatch
    Watchlist    - the (user, symbol) pairs a user is tracking
    Snapshot     - a point-in-time capture of a symbol's price/volume,
                   used as the "what you last saw" baseline
    ChangeEvent  - a computed, explained change between two snapshots
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, default="Guest")
    created_at = Column(DateTime, default=datetime.utcnow)

    watchlist_items = relationship(
        "Watchlist", back_populates="user", cascade="all, delete-orphan"
    )


class Watchlist(Base):
    """A single stock a user has chosen to track."""
    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_symbol"),
        Index("ix_watchlist_user_symbol", "user_id", "symbol"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    # The snapshot this item was last diffed against. This is the actual
    # fix for the "always Quiet" bug: comparing against whichever
    # snapshot happens to be chronologically previous means two
    # back-to-back page loads diff two nearly-identical snapshots and
    # (correctly) find nothing. This column is a fixed baseline that
    # only advances when we actually compute a change event, so the
    # comparison is genuinely "since you last checked", not "since a
    # few seconds ago".
    last_seen_snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=True)

    user = relationship("User", back_populates="watchlist_items")


class Snapshot(Base):
    """
    A recorded observation of a symbol at a point in time.

    Snapshots are the memory that powers the Meaningful Change Engine:
    each time we fetch fresh market data we store one, and the next time
    the user opens the app we diff the newest snapshot against the last
    one they *saw* (see ChangeEvent.seen) to find what actually changed.
    """
    __tablename__ = "snapshots"
    __table_args__ = (
        Index("ix_snapshot_symbol_time", "symbol", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    day_high = Column(Float, nullable=True)
    day_low = Column(Float, nullable=True)
    prev_close = Column(Float, nullable=True)
    thirty_day_high = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class ChangeEvent(Base):
    """
    A scored, explained difference between two snapshots for a symbol.

    `seen` tracks whether the user has acknowledged this event (via the
    /mark-seen endpoint), which lets the Attention Feed distinguish
    "new since your last visit" from "already reviewed".
    """
    __tablename__ = "change_events"
    __table_args__ = (
        Index("ix_change_symbol_time", "symbol", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    score = Column(Integer, nullable=False, default=0)
    label = Column(String(20), nullable=False, default="Quiet")
    reasons = Column(String(1000), nullable=False, default="")  # "|" separated
    price_then = Column(Float, nullable=True)
    price_now = Column(Float, nullable=True)
    percent_change = Column(Float, nullable=True)
    seen = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
