"""Small date/market-hours helpers used across services."""
from datetime import datetime, time as dtime
import pytz


IST = pytz.timezone("Asia/Kolkata")


def is_market_open(now: datetime | None = None) -> bool:
    """
    Rough NSE/BSE market-hours check (9:15 AM - 3:30 PM IST, Mon-Fri).

    This intentionally ignores exchange holidays -- good enough to decide
    whether to label data as "live" vs "last close" in the UI, not a
    trading-system-grade calendar.
    """
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        now = IST.localize(now)
    now = now.astimezone(IST)

    if now.weekday() >= 5:  # Saturday/Sunday
        return False

    open_t = dtime(9, 15)
    close_t = dtime(15, 30)
    return open_t <= now.time() <= close_t
