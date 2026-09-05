# SignalWatch Database Schema

Postgres in production (Supabase-compatible connection string), SQLite by default for zero-config local dev. Managed via SQLAlchemy models in `backend/models/models.py`.

## Tables

### `users`
| Column | Type | Notes |
|---|---|---|
| id | int, PK | |
| name | varchar(120) | defaults to "Guest" |
| created_at | datetime | |

Single-user scope for this build (see `DEFAULT_USER_ID` in `watchlist_service.py`); the schema already supports multiple users so adding auth later doesn't require a migration of the core tables.

### `watchlist`
| Column | Type | Notes |
|---|---|---|
| id | int, PK | |
| user_id | int, FK → users.id | |
| symbol | varchar(20), indexed | |
| added_at | datetime | |
| last_seen_snapshot_id | int, FK → snapshots.id, nullable | the fixed "as of your last visit" baseline the Change Engine diffs against (see below) |

**Constraint:** `UNIQUE(user_id, symbol)` — enforces "no duplicate stocks" at the database level, not just in application code.
**Index:** `(user_id, symbol)` — the watchlist read path filters on both.

`last_seen_snapshot_id` only advances when `compute_change_events` actually runs a comparison for that symbol — not on every snapshot. Diffing against "whichever snapshot is chronologically previous" instead of this fixed baseline was the root cause of an earlier bug where the Attention Feed almost always read "Quiet": rapid page loads produce near-identical back-to-back snapshots, so a "previous snapshot" comparison rarely finds anything, even when the price has genuinely moved since the user's last real visit.

### `snapshots`
| Column | Type | Notes |
|---|---|---|
| id | int, PK | |
| symbol | varchar(20), indexed | |
| price | float | |
| volume | float, nullable | |
| day_high / day_low | float, nullable | |
| prev_close | float, nullable | |
| thirty_day_high | float, nullable | |
| timestamp | datetime, indexed | |

**Index:** `(symbol, timestamp)` — the Change Engine's core query is "give me the two most recent snapshots for symbol X", which this index serves directly instead of a full table scan.

This table is the system's memory. Every `POST /snapshot` call appends new rows; nothing is ever overwritten, which also gives us the "snapshot history" shown on the Stock Detail page for free.

### `change_events`
| Column | Type | Notes |
|---|---|---|
| id | int, PK | |
| symbol | varchar(20), indexed | |
| score | int | 0–100, from the Change Engine |
| label | varchar(20) | Quiet / Worth Checking / Important |
| reasons | varchar(1000) | `\|`-joined list of explanation strings |
| price_then / price_now / percent_change | float, nullable | |
| seen | boolean | drives the "unseen only" attention feed filter |
| created_at | datetime | |

**Index:** `(symbol, created_at)` — powers the per-stock "explanation timeline" on the detail page.

`reasons` is stored as a delimited string rather than a separate table. At this scale (a handful of short strings per event) a join table would add complexity without a real query benefit; if reasons needed independent querying later, this is the first table I'd normalize.

## Why snapshots and change_events are separate tables

Snapshots are raw, append-only observations — the truth. Change events are *derived* — a scored interpretation of two snapshots at a point in time. Keeping them separate means:
- The scoring rules can change (e.g. adjusted thresholds) and we can recompute historical change events from the raw snapshots without having lost any data.
- Snapshotting (cheap, frequent) and change computation (a bit more work) can scale independently — e.g. snapshot every 5 minutes but only recompute change events on demand.
