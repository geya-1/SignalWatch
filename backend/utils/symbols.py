"""
Shared symbol-normalization helpers.

Every place that touches a Watchlist symbol -- adding it, deleting it,
looking it up, or fetching a quote for it -- needs to agree on one
canonical form. Before this module existed, "RELIANCE" (as stored) and
"RELIANCE.NS" (as sometimes passed to delete/lookup) were treated as two
different symbols, which is why deletes could silently fail to match the
stored row. This is the single source of truth for that normalization.
"""
from typing import Optional

# Exchange suffixes a user might type or paste in, all of which should
# collapse to the same canonical (bare, uppercase) symbol for storage.
_KNOWN_SUFFIXES = (".NS", ".NSE", ".BSE", ".BO")


def normalize_symbol(symbol: str) -> str:
    """Canonical form used for storage, add, delete, and lookup.

    Strips any known exchange suffix and uppercases, so 'reliance',
    'RELIANCE.NS' and 'RELIANCE.NSE' all resolve to the same 'RELIANCE'
    row.
    """
    if not symbol:
        return symbol
    cleaned = symbol.strip().upper()
    for suffix in _KNOWN_SUFFIXES:
        if cleaned.endswith(suffix):
            return cleaned[: -len(suffix)]
    return cleaned


def exchange_hint(symbol: str) -> Optional[str]:
    """Best-effort exchange hint from a user-supplied symbol.

    Looked at *before* normalization strips the suffix, so the market
    adapter can decide which exchange to query upstream. Returns 'BSE',
    'NSE', or None when the caller gave a bare ticker (the adapter picks
    a sensible default for that case).
    """
    if not symbol:
        return None
    cleaned = symbol.strip().upper()
    if cleaned.endswith(".BSE") or cleaned.endswith(".BO"):
        return "BSE"
    if cleaned.endswith(".NS") or cleaned.endswith(".NSE"):
        return "NSE"
    return None
