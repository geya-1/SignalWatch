"""
Market Adapter

The single place in the codebase that talks to an external market-data
provider. Everything else in the app depends on the MarketQuote shape
defined here, not on the provider directly -- so if Groww's real
internal market-data service replaced this tomorrow, only this file
would change.

Provider: Twelve Data (https://twelvedata.com). Chosen over yfinance
because yfinance scrapes Yahoo Finance with no SLA and breaks silently
whenever Yahoo changes its page/response shape (the root cause of the
"market data unavailable" errors this replaces). Twelve Data has a
documented REST API, a usable free tier, and native NSE/BSE support via
the `SYMBOL:EXCHANGE` format.

Design decisions (unchanged from before):
  - Every symbol lookup is wrapped in try/except. A failure for one
    symbol must never take down the whole watchlist response.
  - Quotes are cached for a short TTL to reduce upstream calls and
    smooth over transient provider errors.
  - Indian tickers default to NSE unless the caller supplies an explicit
    .BO/.BSE suffix.

New in this version:
  - One automatic retry on a failed/timed-out upstream request before
    giving up and returning a friendly error quote.
  - A `freshness` tag ("live" / "cached" / "market_closed") so the
    frontend can render an accurate badge instead of guessing from
    `is_stale` alone.
  - DEMO_MODE: if no TWELVE_DATA_API_KEY is configured, the adapter
    serves deterministic synthetic quotes instead of failing outright,
    so the app is runnable out of the box for local dev / demos.
"""
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from utils.cache import quote_cache, classify_freshness
from utils.timeframes import is_market_open
from utils.symbols import normalize_symbol, exchange_hint


TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()

# If there's no API key configured, or DEMO_MODE is explicitly set, run
# on synthetic data rather than failing every request. This keeps the
# app usable for local development/demos without requiring anyone to
# get a key first.
DEMO_MODE = bool(os.getenv("DEMO_MODE", "").strip().lower() in ("1", "true", "yes")) or not TWELVE_DATA_API_KEY

REQUEST_TIMEOUT_SECONDS = 8.0
RETRY_BACKOFF_SECONDS = 0.5


@dataclass
class MarketQuoteData:
    symbol: str
    company_name: Optional[str] = None
    price: Optional[float] = None
    percent_change: Optional[float] = None
    volume: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    prev_close: Optional[float] = None
    thirty_day_high: Optional[float] = None
    chart_points: List[float] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    freshness: str = "live"  # "live" | "cached" | "market_closed"
    is_stale: bool = False
    error: Optional[str] = None


def _provider_symbol(symbol: str) -> str:
    """Build the Twelve Data symbol, e.g. RELIANCE -> RELIANCE:NSE.

    Twelve Data uses a `SYMBOL:EXCHANGE` format for non-US exchanges. An
    explicit .BO/.BSE suffix routes to BSE; anything else (bare ticker,
    or an explicit .NS/.NSE suffix) defaults to NSE, matching the
    behaviour this app has always had for Indian tickers. US-style
    tickers would need a different default, but that's out of scope for
    this app the same way it was with the old yfinance ".NS" heuristic.
    """
    hint = exchange_hint(symbol)
    base = normalize_symbol(symbol)
    exchange = "BSE" if hint == "BSE" else "NSE"
    return f"{base}:{exchange}"


def _request_with_retry(client: httpx.Client, url: str, params: dict) -> dict:
    """GET with one automatic retry on timeout/network/5xx errors.

    A single symbol having a bad moment upstream shouldn't need a full
    page reload to recover from -- but we also don't want to retry
    forever and turn a provider outage into a hung request.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(2):  # initial attempt + one retry
        try:
            resp = client.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp.json()
            last_exc = RuntimeError(f"http_{resp.status_code}")
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
        if attempt == 0:
            time.sleep(RETRY_BACKOFF_SECONDS)
    raise last_exc or RuntimeError("request_failed")


# ---------------------------------------------------------------------
# Demo mode: deterministic synthetic quotes, no network calls.
# ---------------------------------------------------------------------

_demo_state: dict = {}


def _demo_quote(canonical_symbol: str) -> MarketQuoteData:
    """Generate a believable, slowly-drifting quote with no network call.

    State is kept per-symbol in-process so repeated fetches during a
    session show a plausible walk rather than a fixed number -- useful
    for demoing the Change Engine without a live market connection.
    """
    rng = random.Random(canonical_symbol)
    state = _demo_state.get(canonical_symbol)
    if state is None:
        state = {"price": round(rng.uniform(50, 4000), 2), "volume": rng.randint(100_000, 5_000_000)}
        _demo_state[canonical_symbol] = state

    prev_close = state["price"]
    drift = rng.uniform(-0.015, 0.015)
    new_price = round(prev_close * (1 + drift), 2)
    state["price"] = new_price
    state["volume"] = max(1_000, int(state["volume"] * rng.uniform(0.7, 1.4)))

    percent_change = ((new_price - prev_close) / prev_close) * 100 if prev_close else 0.0
    chart_points = [round(prev_close * (1 + rng.uniform(-0.05, 0.05)), 2) for _ in range(29)]
    chart_points.append(new_price)

    return MarketQuoteData(
        symbol=canonical_symbol,
        company_name=f"{canonical_symbol} (Demo Data)",
        price=new_price,
        percent_change=round(percent_change, 2),
        volume=float(state["volume"]),
        day_high=round(new_price * 1.01, 2),
        day_low=round(new_price * 0.99, 2),
        prev_close=round(prev_close, 2),
        thirty_day_high=round(max(chart_points), 2),
        chart_points=chart_points,
        last_updated=datetime.now(timezone.utc),
        freshness="cached",
        is_stale=True,
        error=None,
    )


# ---------------------------------------------------------------------
# Live fetch
# ---------------------------------------------------------------------

def fetch_quote(symbol: str, use_cache: bool = True) -> MarketQuoteData:
    """Fetch a single quote, handling all known failure modes gracefully."""
    canonical = normalize_symbol(symbol)
    cache_key = canonical

    if use_cache:
        cached = quote_cache.get(cache_key)
        if cached is not None:
            # The bytes in `cached` are unchanged, but the badge we show
            # for them isn't: this response is coming from cache right
            # now, even if it was fetched live a few seconds ago.
            cached.freshness = classify_freshness(from_cache=True, market_open=is_market_open())
            cached.is_stale = cached.freshness != "live"
            return cached

    if DEMO_MODE:
        result = _demo_quote(canonical)
        quote_cache.set(cache_key, result)
        return result

    provider_symbol = _provider_symbol(symbol)
    market_open = is_market_open()

    try:
        with httpx.Client() as client:
            quote_payload = _request_with_retry(
                client,
                f"{TWELVE_DATA_BASE_URL}/quote",
                {"symbol": provider_symbol, "apikey": TWELVE_DATA_API_KEY},
            )

            if quote_payload.get("status") == "error" or quote_payload.get("code"):
                result = MarketQuoteData(
                    symbol=canonical,
                    error=quote_payload.get("message", "invalid_symbol_or_no_data"),
                    freshness="market_closed" if not market_open else "live",
                    is_stale=True,
                )
                quote_cache.set(cache_key, result)
                return result

            price = float(quote_payload["close"])
            prev_close = float(quote_payload.get("previous_close") or price)
            percent_change = float(quote_payload.get("percent_change") or 0.0)
            volume = float(quote_payload.get("volume") or 0)
            day_high = float(quote_payload.get("high") or price)
            day_low = float(quote_payload.get("low") or price)
            company_name = quote_payload.get("name") or canonical

            # Chart points / 30-day high come from a second call. This is
            # a nice-to-have, mirroring the old code's tolerance for the
            # flaky yfinance "info" endpoint: never fail the whole quote
            # over it.
            chart_points: List[float] = []
            thirty_day_high: Optional[float] = None
            try:
                series_payload = _request_with_retry(
                    client,
                    f"{TWELVE_DATA_BASE_URL}/time_series",
                    {
                        "symbol": provider_symbol,
                        "interval": "1day",
                        "outputsize": 30,
                        "apikey": TWELVE_DATA_API_KEY,
                    },
                )
                values = series_payload.get("values") or []
                closes = [float(v["close"]) for v in reversed(values) if v.get("close")]
                if closes:
                    chart_points = [round(c, 2) for c in closes]
                    thirty_day_high = round(max(chart_points), 2)
            except Exception:
                pass

            freshness = classify_freshness(from_cache=False, market_open=market_open)

            result = MarketQuoteData(
                symbol=canonical,
                company_name=company_name,
                price=round(price, 2),
                percent_change=round(percent_change, 2),
                volume=volume,
                day_high=round(day_high, 2),
                day_low=round(day_low, 2),
                prev_close=round(prev_close, 2),
                thirty_day_high=thirty_day_high,
                chart_points=chart_points,
                last_updated=datetime.now(timezone.utc),
                freshness=freshness,
                is_stale=freshness != "live",
            )
            quote_cache.set(cache_key, result)
            return result

    except Exception as exc:  # noqa: BLE001 - deliberately broad: any
        # upstream failure (timeout, rate limit, network error, bad
        # response shape) must degrade to a friendly error, not a 500.
        result = MarketQuoteData(
            symbol=canonical,
            error=f"market_data_unavailable: {exc.__class__.__name__}",
            freshness="market_closed" if not market_open else "live",
            is_stale=True,
        )
        # Cache failures briefly too, so a broken symbol doesn't cause a
        # retry storm on every page load.
        quote_cache.set(cache_key, result)
        return result


def fetch_quotes(symbols: List[str]) -> List[MarketQuoteData]:
    """Fetch multiple quotes. Each symbol fails independently."""
    return [fetch_quote(s) for s in symbols]
