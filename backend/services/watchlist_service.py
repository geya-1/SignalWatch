"""
Watchlist Service

Business logic for watchlist CRUD, snapshotting, and turning snapshots
into scored ChangeEvents. Routers stay thin and delegate here so the
logic is unit-testable without spinning up FastAPI.
"""
import random
from datetime import datetime, time as dtime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.models import User, Watchlist, Snapshot, ChangeEvent
from services.market_adapter import fetch_quote, fetch_quotes, MarketQuoteData
from services.change_engine import (
    evaluate_change,
    BaselineSnapshot,
    LABEL_IMPORTANT,
    LABEL_WORTH_CHECKING,
)
from utils.symbols import normalize_symbol
from utils.timeframes import IST


DEFAULT_USER_ID = 1  # single-user hackathon scope; see docs/architecture.md

# If the most recent snapshot for a symbol is younger than this and the
# price hasn't actually moved, skip writing a new one. Prevents rapid
# reloads / multiple open tabs from spamming near-duplicate snapshot
# rows -- a genuine price move within the window still gets recorded.
SNAPSHOT_THROTTLE_SECONDS = 45


def get_or_create_default_user(db: Session) -> User:
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    if user is None:
        user = User(id=DEFAULT_USER_ID, name="Guest")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def add_symbol(db: Session, symbol: str) -> Watchlist:
    symbol = normalize_symbol(symbol)
    get_or_create_default_user(db)
    existing = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == DEFAULT_USER_ID, Watchlist.symbol == symbol)
        .first()
    )
    if existing:
        raise ValueError(f"{symbol} is already in your watchlist")

    item = Watchlist(user_id=DEFAULT_USER_ID, symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_symbol(db: Session, symbol: str) -> bool:
    symbol = normalize_symbol(symbol)
    item = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == DEFAULT_USER_ID, Watchlist.symbol == symbol)
        .first()
    )
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def get_watchlist_item(db: Session, symbol: str) -> Optional[Watchlist]:
    symbol = normalize_symbol(symbol)
    return (
        db.query(Watchlist)
        .filter(Watchlist.user_id == DEFAULT_USER_ID, Watchlist.symbol == symbol)
        .first()
    )


def list_symbols(db: Session) -> List[Watchlist]:
    return (
        db.query(Watchlist)
        .filter(Watchlist.user_id == DEFAULT_USER_ID)
        .order_by(Watchlist.added_at.asc())
        .all()
    )


def get_latest_snapshot(db: Session, symbol: str, before_id: Optional[int] = None) -> Optional[Snapshot]:
    query = db.query(Snapshot).filter(Snapshot.symbol == symbol)
    if before_id is not None:
        query = query.filter(Snapshot.id < before_id)
    return query.order_by(desc(Snapshot.timestamp)).first()


def record_snapshot(db: Session, quote: MarketQuoteData) -> Optional[Snapshot]:
    """Persist a snapshot for a successfully-fetched quote.

    Returns None (and records nothing) if the quote failed to fetch --
    we never want a bad upstream response to poison the change history.
    """
    if quote.error or quote.price is None:
        return None

    last = get_latest_snapshot(db, quote.symbol)
    if last is not None:
        age_seconds = (datetime.utcnow() - last.timestamp).total_seconds()
        if age_seconds < SNAPSHOT_THROTTLE_SECONDS and last.price == quote.price:
            # We just snapshotted this symbol moments ago and nothing
            # has actually moved -- skip writing a near-duplicate row.
            return None

    snapshot = Snapshot(
        symbol=quote.symbol,
        price=quote.price,
        volume=quote.volume,
        day_high=quote.day_high,
        day_low=quote.day_low,
        prev_close=quote.prev_close,
        thirty_day_high=quote.thirty_day_high,
        timestamp=datetime.utcnow(),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def snapshot_watchlist(db: Session, symbols: Optional[List[str]] = None) -> List[Snapshot]:
    if symbols is None:
        symbols = [w.symbol for w in list_symbols(db)]
    if not symbols:
        return []

    quotes = fetch_quotes(symbols)
    snapshots = []
    for quote in quotes:
        snap = record_snapshot(db, quote)
        if snap:
            snapshots.append(snap)
    return snapshots


def compute_change_events(db: Session, symbols: Optional[List[str]] = None) -> List[ChangeEvent]:
    """
    For each symbol: compare its newest snapshot against the watchlist
    item's `last_seen_snapshot_id` -- a fixed baseline that only advances
    when we actually compute a change event for that symbol -- run the
    pair through the Change Engine, and persist the resulting
    ChangeEvent.

    This is the fix for the "always Quiet" bug. The old version diffed
    against "whichever snapshot is chronologically previous", which on a
    page-load-triggered snapshot cadence meant two nearly-back-to-back
    snapshots (and therefore two nearly-identical prices) almost every
    time -- so the Change Engine correctly, but uselessly, found nothing
    to report. Anchoring the baseline to "the snapshot as of your last
    visit" instead of "one snapshot ago" makes the diff actually
    correspond to what the feature promises: what changed since you last
    looked.
    """
    if symbols is None:
        symbols = [w.symbol for w in list_symbols(db)]

    events: List[ChangeEvent] = []
    for symbol in symbols:
        watchlist_item = get_watchlist_item(db, symbol)
        if watchlist_item is None:
            continue  # symbol isn't (or is no longer) on the watchlist

        latest = get_latest_snapshot(db, symbol)
        if latest is None:
            continue  # no snapshot for this symbol yet

        baseline_snap = None
        if watchlist_item.last_seen_snapshot_id is not None:
            baseline_snap = (
                db.query(Snapshot)
                .filter(Snapshot.id == watchlist_item.last_seen_snapshot_id)
                .first()
            )

        if baseline_snap is None or baseline_snap.id == latest.id:
            # Either this is the first snapshot we've ever taken for the
            # symbol, or nothing new has arrived since the baseline was
            # last set. Establish/refresh the baseline so the *next*
            # genuinely new snapshot has something real to diff against,
            # but don't manufacture a change event for it.
            watchlist_item.last_seen_snapshot_id = latest.id
            continue

        baseline = BaselineSnapshot(
            price=baseline_snap.price,
            volume=baseline_snap.volume,
            percent_change=(
                ((baseline_snap.price - baseline_snap.prev_close) / baseline_snap.prev_close * 100)
                if baseline_snap.prev_close else None
            ),
        )
        current_quote = MarketQuoteData(
            symbol=symbol,
            price=latest.price,
            volume=latest.volume,
            thirty_day_high=latest.thirty_day_high,
            prev_close=latest.prev_close,
        )
        result = evaluate_change(baseline, current_quote)

        event = ChangeEvent(
            symbol=symbol,
            score=result.score,
            label=result.label,
            reasons="|".join(result.reasons),
            price_then=baseline.price,
            price_now=latest.price,
            percent_change=result.percent_change,
            seen=False,
        )
        db.add(event)
        events.append(event)

        # Advance the baseline to this visit -- the *next* comparison
        # should be "since this check", not "since two snapshots ago".
        watchlist_item.last_seen_snapshot_id = latest.id

    db.commit()
    for e in events:
        db.refresh(e)

    return events


def get_change_events(db: Session, unseen_only: bool = False) -> List[ChangeEvent]:
    query = db.query(ChangeEvent)
    if unseen_only:
        query = query.filter(ChangeEvent.seen.is_(False))
    return query.order_by(desc(ChangeEvent.score), desc(ChangeEvent.created_at)).all()


def mark_seen(db: Session, symbol: Optional[str], change_event_id: Optional[int], mark_all: bool) -> int:
    query = db.query(ChangeEvent)
    if mark_all:
        pass
    elif change_event_id is not None:
        query = query.filter(ChangeEvent.id == change_event_id)
    elif symbol is not None:
        query = query.filter(ChangeEvent.symbol == symbol)
    else:
        return 0

    count = query.update({"seen": True})
    db.commit()
    return count


# ---------------------------------------------------------------------
# Market Mood -- a one-line rollup of the Attention Feed, driven by the
# same ChangeEvent scores the feed already computes. No new scoring
# logic lives here; this only classifies numbers the Change Engine
# already produced.
# ---------------------------------------------------------------------

MOOD_CALM = "Calm"
MOOD_WATCHFUL = "Watchful"
MOOD_ACTIVE = "Active"
MOOD_VOLATILE = "Volatile"

# icon/color are presentation metadata, but keeping them here (next to
# the thresholds that decide the mood) means the frontend never has to
# re-implement the score -> mood mapping just to know which color to use.
_MOOD_META = {
    MOOD_CALM: {"icon": "\U0001F60C", "color": "grey"},        # 😌
    MOOD_WATCHFUL: {"icon": "\U0001F9D0", "color": "blue"},     # 🧐
    MOOD_ACTIVE: {"icon": "\u26A1", "color": "orange"},         # ⚡
    MOOD_VOLATILE: {"icon": "\U0001F525", "color": "red"},      # 🔥
}


def _mood_for_score(score: int) -> str:
    if score > 70:
        return MOOD_VOLATILE
    if score >= 41:
        return MOOD_ACTIVE
    if score >= 21:
        return MOOD_WATCHFUL
    return MOOD_CALM


def get_latest_change_events_per_symbol(db: Session) -> List[ChangeEvent]:
    """The most recent ChangeEvent for each watchlist symbol.

    Mood should reflect "as of now", not every historical event ever
    computed for a symbol -- so we only look at each symbol's latest.
    """
    events: List[ChangeEvent] = []
    for symbol in [w.symbol for w in list_symbols(db)]:
        latest = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.symbol == symbol)
            .order_by(desc(ChangeEvent.created_at))
            .first()
        )
        if latest is not None:
            events.append(latest)
    return events


def get_market_mood(db: Session) -> dict:
    """
    Roll the watchlist's current ChangeEvents up into a single mood.

    Driven by the *highest* score across the watchlist right now: one
    Volatile stock should make the whole dashboard read as attention-
    worthy, even if everything else is Calm.
    """
    events = get_latest_change_events_per_symbol(db)

    if not events:
        meta = _MOOD_META[MOOD_CALM]
        return {
            "mood": MOOD_CALM,
            "score": 0,
            "important_count": 0,
            "worth_checking_count": 0,
            "explanation": "Add a stock to your watchlist to see how it's doing.",
            **meta,
        }

    top_score = max(e.score for e in events)
    important_count = sum(1 for e in events if e.label == LABEL_IMPORTANT)
    worth_count = sum(1 for e in events if e.label == LABEL_WORTH_CHECKING)
    mood = _mood_for_score(top_score)

    if important_count:
        explanation = (
            f"{important_count} stock{'s' if important_count != 1 else ''} "
            f"deserve{'s' if important_count == 1 else ''} your attention today."
        )
    elif worth_count:
        explanation = f"{worth_count} stock{'s' if worth_count != 1 else ''} worth a quick look."
    else:
        explanation = "Nothing significant since your last visit."

    meta = _MOOD_META[mood]
    return {
        "mood": mood,
        "score": top_score,
        "important_count": important_count,
        "worth_checking_count": worth_count,
        "explanation": explanation,
        **meta,
    }


# ---------------------------------------------------------------------
# Daily Snapshot Replay -- "how did the watchlist look earlier today".
# Built entirely from the existing Snapshot table; no new persistence.
# ---------------------------------------------------------------------

def _bucket_for_timestamp(ts: datetime) -> str:
    """Classify a UTC snapshot timestamp into a replay stage (IST day-part)."""
    # Snapshots are stored naive-UTC (datetime.utcnow()); treat them as
    # UTC explicitly before converting to IST for the day-part bucket.
    from datetime import timezone as _tz
    aware = ts.replace(tzinfo=_tz.utc) if ts.tzinfo is None else ts
    local_time = aware.astimezone(IST).time()
    return "morning" if local_time < dtime(12, 0) else "afternoon"


def _demo_replay(symbols: List[str]) -> dict:
    """
    Synthetic Morning / Afternoon / Now prices for Demo Mode.

    Reuses the same per-symbol demo state the market adapter already
    maintains for "Now", and derives Morning/Afternoon by walking that
    price backwards with a symbol-seeded RNG -- deterministic across
    calls within a session, no new persistence, no duplicated business
    logic.
    """
    from services.market_adapter import _demo_state  # local import avoids a hard circular dependency at module load

    stages: Dict[str, list] = {"Morning": [], "Afternoon": [], "Now": []}
    for symbol in symbols:
        canonical = normalize_symbol(symbol)
        rng = random.Random(f"{canonical}-replay")
        state = _demo_state.get(canonical)
        current_price = state["price"] if state else round(rng.uniform(50, 4000), 2)

        morning_price = round(current_price * (1 + rng.uniform(-0.035, 0.035)), 2)
        afternoon_price = round(morning_price * (1 + rng.uniform(-0.025, 0.025)), 2)

        stages["Morning"].append({"symbol": canonical, "price": morning_price})
        stages["Afternoon"].append({"symbol": canonical, "price": afternoon_price})
        stages["Now"].append({"symbol": canonical, "price": current_price})

    return {"stages": [{"label": label, "prices": prices} for label, prices in stages.items()]}


def get_daily_replay(db: Session) -> dict:
    """
    Bucket today's snapshots into Morning / Afternoon / Now per symbol.

    In Demo Mode there usually isn't enough real snapshot history yet
    (the app might have been running for minutes, not hours), so we
    generate a realistic synthetic replay instead. In live mode this
    reads straight from the Snapshot table -- no new writes.
    """
    from services.market_adapter import DEMO_MODE

    symbols = [w.symbol for w in list_symbols(db)]
    if not symbols:
        return {"stages": []}

    if DEMO_MODE:
        return _demo_replay(symbols)

    today_start = datetime.combine(datetime.utcnow().date(), dtime.min)
    bucketed: Dict[str, Dict[str, float]] = {"morning": {}, "afternoon": {}}
    latest_price: Dict[str, float] = {}

    todays_snapshots = (
        db.query(Snapshot)
        .filter(Snapshot.symbol.in_(symbols), Snapshot.timestamp >= today_start)
        .order_by(Snapshot.timestamp.asc())
        .all()
    )
    for snap in todays_snapshots:
        bucket = _bucket_for_timestamp(snap.timestamp)
        bucketed[bucket][snap.symbol] = snap.price
        latest_price[snap.symbol] = snap.price  # ends up holding the latest snapshot per symbol

    stages = []
    for label, key in (("Morning", "morning"), ("Afternoon", "afternoon")):
        prices = bucketed[key]
        stages.append({
            "label": label,
            "prices": [{"symbol": s, "price": prices.get(s)} for s in symbols],
        })
    stages.append({
        "label": "Now",
        "prices": [{"symbol": s, "price": latest_price.get(s)} for s in symbols],
    })

    return {"stages": stages}
