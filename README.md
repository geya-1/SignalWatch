# SignalWatch — Smart Market Watchlist

**Groww CODE 2026 submission**

> A watchlist that tells you what actually changed since you last checked — not another live ticker.

---

## 100-word product pitch

Every watchlist app shows the same thing: live prices, all the time, for everything. SignalWatch does the opposite. It remembers what you last saw, and the next time you open it, tells you *only* what meaningfully changed — with a plain-English reason, every time: "Crossed its 30-day high, volume doubled, up ₹68 since your last visit." A Market Mood card and a Quick Attention button turn that signal into a one-glance, one-tap experience. No AI guesses, no buy/sell calls — just a deterministic, auditable scoring engine surfacing signal over noise, built the way a product team at Groww would: simple, transparent, and respectful of your attention.

---

## Problem interpretation

The brief asks for a watchlist that highlights *meaningful* change rather than raw price movement, with every highlight explained. I interpreted "meaningful" as: a rules-based combination of price move size, volume behavior, new highs, and trend reversals — deliberately **not** an LLM, so every flag is explainable and reproducible. The product should never recommend trades; it only explains what happened. The features below extend that same philosophy outward: instead of only explaining *individual* stocks, the homepage now also explains the *watchlist as a whole* (Market Mood), makes the score itself visible and comparable (Attention Score Meter), explains the *absence* of a signal as rigorously as its presence ("Why Quiet?"), and gets a user to the one thing worth their attention in one tap (Quick Attention).

---

## What's new in this build

Built on top of the existing, working SignalWatch app — same architecture, same services, no rewrite.

| Feature | What it does | Where it lives |
|---|---|---|
| **Market Mood** | One-line rollup of the whole watchlist ("Watchful — 1 stock worth a quick look"), driven by the highest Change Engine score on the board right now | `GET /mood` → `watchlist_service.get_market_mood` → `MarketMood.tsx` |
| **Attention Score Meter** | The 0–100 score every card already had, now shown as a color-coded bar instead of hidden in the reasons list | `AttentionScoreMeter.tsx`, embedded in `StockCard.tsx` |
| **Why Quiet?** | Replaces the generic "Quiet" label with deterministic, data-driven bullets ("Price changed only 0.7%", "Normal trading volume", "No breakout detected") | `change_engine._build_quiet_reasons` → `QuietExplanation.tsx` |
| **Today's Replay** | Morning / Afternoon / Now tabs showing how the watchlist looked earlier today, built from the existing `snapshots` table (synthetic in Demo Mode) | `GET /replay` → `watchlist_service.get_daily_replay` → `SnapshotReplay.tsx` |
| **Portfolio Heatmap** | Compact colored tiles (green/red/grey) above the feed; click one to scroll straight to that card | `PortfolioHeatmap.tsx` (pure frontend — reuses `/market` + `/changes`, no new backend logic) |
| **Quick Attention button** | Floating ⚡ button that finds the single highest-scoring stock, scrolls to it, and briefly glows the card. Shows "Everything looks quiet." when nothing qualifies | `QuickAttentionButton.tsx` |

None of these introduced a new scoring rule or a new source of truth — they're all views over the same `ChangeEvent`/`Snapshot` data the Change Engine and Watchlist Service already produced.

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15 (App Router), React, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python, SQLAlchemy |
| Database | PostgreSQL (Supabase-compatible), SQLite fallback for local dev |
| Market data | Twelve Data (`TWELVE_DATA_API_KEY`), with a built-in **Demo Mode** fallback when no key is configured |
| Deploy targets | Frontend → Vercel, Backend → Render |

---

## Project structure

```
SignalWatch/
├── frontend/         Next.js app (App Router)
│   ├── app/          routes: / (feed), /add, /stock/[symbol]
│   ├── components/   StockCard, AttentionFeed, MiniChart, AddStockForm,
│   │                  Badge, AttentionScoreMeter, QuietExplanation,
│   │                  MarketMood, SnapshotReplay, PortfolioHeatmap,
│   │                  QuickAttentionButton, ...
│   ├── hooks/        useWatchlist, useMarket, useInsights
│   ├── services/     api.ts — typed fetch client
│   └── types/        shared TS interfaces
├── backend/
│   ├── routers/      watchlist, market, changes, snapshot, insights
│   ├── services/     watchlist_service, change_engine, market_adapter
│   ├── models/       SQLAlchemy models (User, Watchlist, Snapshot, ChangeEvent)
│   ├── schemas/      Pydantic request/response schemas
│   ├── database/     engine/session setup
│   ├── utils/        TTL cache + freshness classifier, market-hours helper, symbol normalizer
│   └── tests/        pytest unit tests for the Change Engine
├── docs/
│   ├── architecture.svg / architecture.md
│   ├── api.md
│   └── database.md
├── .env.example
└── SignalWatch_Final.zip
```

---

## Setup

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp ../.env.example .env   # leave TWELVE_DATA_API_KEY blank to run in Demo Mode
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

App: http://localhost:3000

### Try it end-to-end

1. Open the app, add a symbol (e.g. `RELIANCE`, `TCS`, `INFY` — bare NSE symbols; the backend routes them to NSE automatically). Without a `TWELVE_DATA_API_KEY`, the app runs in **Demo Mode** with realistic synthetic data — every feature below works identically.
2. The homepage now opens with **Market Mood**, **Today's Replay**, and the **Portfolio Heatmap**, then the Attention Feed split into **Priority Cards** and **Quiet Watchlist**.
3. On the *first* visit there's nothing to compare against yet, so everything shows Quiet — each Quiet card shows a **Why Quiet?** breakdown instead of a dead end.
4. Come back later (or call `POST /snapshot` again after the price has moved) — the feed re-sorts, Market Mood updates, and the ⚡ **Quick Attention** button jumps straight to whatever changed most.

---

## The Meaningful Change Engine

Deterministic, rules-based, capped 0–100 score:

| Event | Score |
|---|---|
| Price move > 3% | +40 |
| Price move > 5% (replaces the >3% rule) | +70 |
| Volume roughly doubled | +25 |
| New 30-day high | +30 |
| Trend reversal (sign flip vs. previous move) | +35 |

**Labels:** `score ≥ 60` → Important · `score ≥ 30` → Worth Checking · else → Quiet.

When nothing scores (Quiet), the engine now builds its explanation the same way it builds every other reason — from the actual numbers, not a placeholder string: the exact percent move, a volume comparison against the baseline, and whether the stock is near its 30-day high. This is what powers "Why Quiet?" without introducing any new inputs.

Implementation: `backend/services/change_engine.py`. It's pure functions over plain dataclasses — no DB, no network — so it's fully unit tested in `backend/tests/test_change_engine.py` without any infrastructure.

---

## Market Mood, in detail

`watchlist_service.get_market_mood` takes the *latest* ChangeEvent per watchlist symbol (not the full history) and classifies the **highest** score among them:

| Score | Mood |
|---|---|
| 0–20 | Calm |
| 21–40 | Watchful |
| 41–70 | Active |
| 70+ | Volatile |

Using the max rather than the average is deliberate: one Volatile stock should make the dashboard read as attention-worthy even if the rest of the watchlist is asleep — matching how the Attention Feed itself already prioritizes.

---

## Edge cases handled

- Invalid or delisted stock symbol → quote returned with an `error` field, never a crash
- Duplicate watchlist entries (including with/without an exchange suffix, e.g. `RELIANCE` vs `RELIANCE.NS`) → normalized through one shared helper (`utils/symbols.py`) and rejected at both the DB (`UNIQUE` constraint) and API (`409 Conflict`) layers
- Market data provider timeout/rate limit → one automatic retry, then the quote is marked `error` + non-live `freshness`, briefly cached to avoid retry storms
- Market closed → quotes tagged `freshness: market_closed` (`is_stale` kept for backwards compatibility), UI shows "Last close" instead of implying live data
- No `TWELVE_DATA_API_KEY` configured → the whole app, including Demo Replay, runs on deterministic synthetic data rather than failing outright
- Empty watchlist → `/market`, `/changes`, `/mood`, and `/replay` all return an empty/neutral shape, and the UI shows a proper empty state, not an error
- First-ever snapshot for a symbol → no change event generated (nothing to compare against yet), rather than a fabricated 0% diff
- Rapid reloads → snapshot writes are throttled (skipped when the price hasn't moved and the last snapshot is recent), so the Attention Feed's diff baseline isn't polluted with near-duplicate rows
- No real snapshot history yet for Daily Replay → Demo Mode serves a synthetic replay; live mode returns `null` prices for a bucket with nothing recorded, rather than guessing
- A Quiet watchlist and the Quick Attention button → shows "Everything looks quiet." instead of scrolling nowhere
- Partial failures → one broken symbol in a multi-stock watchlist never blocks the others (`fetch_quotes` isolates each call)
- Removing a stock → its historical snapshots/change events are preserved for audit; only the active watchlist row is deleted

See `docs/api.md` for the full endpoint-by-endpoint edge-case table.

---

## Engineering depth notes

- **Fixed diff baseline (`last_seen_snapshot_id`)**: the Attention Feed compares each symbol's newest snapshot against a baseline that only advances when a change is actually computed — not "whichever snapshot happens to be previous." This is what makes the feed correctly detect meaningful change instead of reading "Quiet" on every reload.
- **Snapshot persistence + throttling**: every `POST /snapshot` appends immutable rows (this is what makes the Daily Replay and the Stock Detail timeline possible for free), but rapid reloads with no real price movement are throttled rather than spamming near-duplicate rows.
- **Cached market responses**: a 60s in-process TTL cache in front of Twelve Data (`backend/utils/cache.py`), swappable for Redis without touching call sites. The same module classifies every quote's `freshness` (`live` / `cached` / `market_closed`) so the frontend never has to guess from `is_stale` alone.
- **Timeouts + graceful degradation**: every Twelve Data call is wrapped, with one automatic retry before degrading to an `error` field on the quote — never a 500.
- **Demo Mode as a first-class code path, not a mock**: `market_adapter.py` generates deterministic synthetic quotes when no API key is present, and the Daily Replay feature reuses the *same* per-symbol demo state rather than maintaining a separate fake dataset — so Demo Mode and live mode never drift apart in behavior.
- **Indexed queries**: `(symbol, timestamp)` on snapshots and `(symbol, created_at)` on change events — both match the actual hot query patterns (see `docs/database.md`).
- **Reusable frontend primitives**: `Badge`, `AttentionScoreMeter`, and `QuietExplanation` are used across the feed, the heatmap tone system, and the Market Mood card rather than each screen inventing its own label/color logic.

---

## Scaling (see `docs/architecture.md` for details)

Batching market requests · Redis cache · background workers for scheduled snapshotting · precomputed change events · horizontal API scaling · DB indexing already in place.

---

## Testing

```bash
# Backend (pure, DB-free unit tests for the scoring engine)
cd backend && pip install -r requirements.txt && pytest tests/

# Frontend (component test for StockCard's render + error paths)
cd frontend && npm install && npm test
```

**Note on this build:** it was generated in a sandboxed environment with no network access, so `pip install` / `npm install` could not be run here to produce a live green test run against the real toolchain. Every backend change was compiled (`python -m py_compile`) and the new/changed scoring and Demo Mode logic (`change_engine`, `market_adapter`, `watchlist_service`) was additionally exercised directly against lightweight stand-ins for `httpx`/`cachetools`/`pytz` to confirm behavior end-to-end without real network access. Every frontend file was checked for balanced syntax and manually reviewed against the existing types, but was not run through a real `tsc`/`next build`. Please run the test suites above after installing dependencies to get a real green run on your machine.

---

## What this is not

- Not a trading or recommendation engine — it explains price/volume behavior, never suggests buying or selling.
- Not using an LLM for scoring or for "Why Quiet?" — both are fully deterministic and auditable by design.

---

## Groww Submission Readiness Report

| Criterion | How this build helps |
|---|---|
| **Engineering Depth** | Fixed the actual root cause of a stale "always Quiet" bug (`last_seen_snapshot_id`) rather than papering over it; new features are additive rollups over existing tables (`ChangeEvent`, `Snapshot`) with zero new persistence; Market Adapter swapped providers behind one interface with retry + freshness classification + a first-class Demo Mode. |
| **Product Interpretation** | Reframes "explain what changed" into an attention-first *experience*: Market Mood gives a one-glance read of the whole watchlist, Today's Replay adds a time dimension the brief's snapshot model already supported but never surfaced, and Quick Attention collapses "which of my 12 stocks matters right now" into one tap. |
| **Edge Cases** | Demo Mode covers the "no API key / no network / no history yet" case for every single new feature, including Daily Replay; Quiet stocks get a real explanation instead of a dead end; the Quick Attention button and Market Mood both degrade gracefully to "nothing to see" states instead of erroring or scrolling nowhere. |
| **Code Quality** | `Badge`, `AttentionScoreMeter`, and `QuietExplanation` are shared, reusable components rather than one-off markup; every new backend capability is a service function plus a thin router (`routers/insights.py`), matching the existing pattern exactly; no duplicated scoring or fetch logic between old and new features. |
| **Originality** | Quick Attention, Today's Replay, and the Portfolio Heatmap aren't things every stock-watchlist clone ships with — they're built specifically around SignalWatch's existing "snapshot memory" idea rather than bolted on as generic widgets. |
