"""
Meaningful Change Engine

This is the heart of SignalWatch. Instead of a live price ticker, we
compare the *newest* snapshot of a symbol against the last snapshot the
user actually saw, and produce a deterministic, explainable score.

Deliberately NOT an LLM / ML model:
  - Judges and users can audit exactly why a stock was flagged.
  - No latency or cost from an external inference call.
  - Reproducible: the same two snapshots always produce the same score.

Scoring rules (additive, capped at 100):
    Price change > 3%             -> +40
    Price change > 5%              -> +70 (replaces the >3% rule, not additive)
    Volume roughly doubled         -> +25
    New 30-day high                -> +30
    Trend reversal (sign flip)     -> +35

Labels:
    score >= 60   -> "Important"
    score >= 30   -> "Worth Checking"
    else          -> "Quiet"
"""
from dataclasses import dataclass
from typing import List, Optional

from services.market_adapter import MarketQuoteData


PRICE_MOVE_MODERATE = 3.0
PRICE_MOVE_LARGE = 5.0
VOLUME_DOUBLE_FACTOR = 2.0

SCORE_PRICE_MODERATE = 40
SCORE_PRICE_LARGE = 70
SCORE_VOLUME_DOUBLE = 25
SCORE_NEW_HIGH = 30
SCORE_TREND_REVERSAL = 35

LABEL_IMPORTANT = "Important"
LABEL_WORTH_CHECKING = "Worth Checking"
LABEL_QUIET = "Quiet"


@dataclass
class BaselineSnapshot:
    """Minimal shape the engine needs from a previously stored Snapshot."""
    price: float
    volume: Optional[float] = None
    percent_change: Optional[float] = None  # sign used for trend reversal


@dataclass
class ChangeResult:
    score: int
    label: str
    reasons: List[str]
    percent_change: float


def _label_for_score(score: int) -> str:
    if score >= 60:
        return LABEL_IMPORTANT
    if score >= 30:
        return LABEL_WORTH_CHECKING
    return LABEL_QUIET


def _build_quiet_reasons(abs_change: float, baseline: BaselineSnapshot, current: MarketQuoteData) -> List[str]:
    """
    Deterministic, data-driven explanation for why a stock scored as
    Quiet -- used by the "Why Quiet?" section instead of a generic
    "nothing happened" message. Every line here is derived directly from
    the same numbers the scoring rules above look at; nothing here is
    guessed or generated.
    """
    reasons = [f"Price changed only {abs_change:.1f}%"]

    if baseline.volume and current.volume and baseline.volume > 0:
        ratio = current.volume / baseline.volume
        if ratio >= VOLUME_DOUBLE_FACTOR:
            # Shouldn't normally happen alongside a Quiet result (volume
            # doubling scores points on its own), but guard it anyway.
            reasons.append(f"Volume up {(ratio - 1) * 100:.0f}%")
        elif ratio >= 1.2:
            reasons.append(f"Volume up {(ratio - 1) * 100:.0f}%, not enough to flag")
        elif ratio <= 0.8:
            reasons.append(f"Volume down {(1 - ratio) * 100:.0f}%")
        else:
            reasons.append("Normal trading volume")
    else:
        reasons.append("Normal trading volume")

    if current.thirty_day_high is not None and current.price is not None and current.price >= current.thirty_day_high:
        reasons.append("Near its 30-day high, but no fresh breakout")
    else:
        reasons.append("No breakout detected")

    return reasons


def evaluate_change(
    baseline: Optional[BaselineSnapshot],
    current: MarketQuoteData,
) -> ChangeResult:
    """
    Compare a baseline (last-seen) snapshot against the current quote and
    produce a scored, explained ChangeResult.

    If there is no baseline (first time this symbol has ever been
    snapshotted), we can't compute a "since last visit" delta, so we
    return a Quiet, zero-score result rather than guessing.
    """
    reasons: List[str] = []
    score = 0

    if baseline is None or current.price is None:
        return ChangeResult(score=0, label=LABEL_QUIET, reasons=["No prior snapshot yet"], percent_change=0.0)

    price_then = baseline.price
    price_now = current.price
    percent_change = ((price_now - price_then) / price_then) * 100 if price_then else 0.0
    abs_change = abs(percent_change)

    # --- Price move rules (mutually exclusive: take the stronger one) ---
    if abs_change > PRICE_MOVE_LARGE:
        score += SCORE_PRICE_LARGE
        direction = "up" if percent_change > 0 else "down"
        reasons.append(f"Moved {direction} {abs_change:.1f}% since your last visit")
    elif abs_change > PRICE_MOVE_MODERATE:
        score += SCORE_PRICE_MODERATE
        direction = "up" if percent_change > 0 else "down"
        reasons.append(f"Moved {direction} {abs_change:.1f}% since your last visit")

    # --- Volume doubled ---
    if baseline.volume and current.volume and baseline.volume > 0:
        if current.volume >= baseline.volume * VOLUME_DOUBLE_FACTOR:
            score += SCORE_VOLUME_DOUBLE
            reasons.append("Trading volume roughly doubled")

    # --- New 30-day high ---
    if current.thirty_day_high is not None and current.price is not None:
        if current.price >= current.thirty_day_high:
            score += SCORE_NEW_HIGH
            reasons.append("Crossed its 30-day high")

    # --- Trend reversal: previous move and current move point opposite ways ---
    if baseline.percent_change is not None and percent_change != 0:
        prev_sign = 1 if baseline.percent_change > 0 else (-1 if baseline.percent_change < 0 else 0)
        curr_sign = 1 if percent_change > 0 else -1
        if prev_sign != 0 and prev_sign != curr_sign:
            score += SCORE_TREND_REVERSAL
            reasons.append("Reversed direction from its previous trend")

    score = min(score, 100)

    if not reasons:
        reasons = _build_quiet_reasons(abs_change, baseline, current)

    price_delta = price_now - price_then
    rupee_sign = "\u20b9"
    direction_word = "Up" if price_delta >= 0 else "Down"
    reasons.append(f"{direction_word} {rupee_sign}{abs(price_delta):.2f} since your last visit")

    # --- Above/below yesterday's close (explanatory context, no score) ---
    if current.prev_close is not None and current.price is not None:
        if current.price > current.prev_close:
            reasons.append("Trading above yesterday's close")
        elif current.price < current.prev_close:
            reasons.append("Trading below yesterday's close")

    return ChangeResult(
        score=score,
        label=_label_for_score(score),
        reasons=reasons,
        percent_change=round(percent_change, 2),
    )
