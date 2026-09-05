"""
Unit tests for the deterministic Change Engine.

These run without a database or network access, since they operate on
plain dataclasses -- run with: pytest backend/tests
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.change_engine import evaluate_change, BaselineSnapshot, LABEL_QUIET, LABEL_IMPORTANT, LABEL_WORTH_CHECKING
from services.market_adapter import MarketQuoteData


def make_quote(price, volume=None, thirty_day_high=None):
    return MarketQuoteData(symbol="TEST", price=price, volume=volume, thirty_day_high=thirty_day_high)


def test_no_baseline_returns_quiet():
    result = evaluate_change(None, make_quote(100))
    assert result.label == LABEL_QUIET
    assert result.score == 0


def test_small_move_stays_quiet():
    baseline = BaselineSnapshot(price=100, volume=1000)
    result = evaluate_change(baseline, make_quote(101, volume=1000))
    assert result.label == LABEL_QUIET


def test_moderate_move_is_worth_checking():
    baseline = BaselineSnapshot(price=100, volume=1000)
    result = evaluate_change(baseline, make_quote(104, volume=1000))  # +4%
    assert result.score == 40
    assert result.label == LABEL_WORTH_CHECKING


def test_large_move_is_important():
    baseline = BaselineSnapshot(price=100, volume=1000)
    result = evaluate_change(baseline, make_quote(106, volume=1000))  # +6%
    assert result.score == 70
    assert result.label == LABEL_IMPORTANT


def test_volume_doubling_adds_score():
    baseline = BaselineSnapshot(price=100, volume=1000)
    result = evaluate_change(baseline, make_quote(101, volume=2500))
    assert "Trading volume roughly doubled" in result.reasons
    assert result.score >= 25


def test_new_high_adds_score():
    baseline = BaselineSnapshot(price=100, volume=1000)
    result = evaluate_change(baseline, make_quote(101, volume=1000, thirty_day_high=101))
    assert "Crossed its 30-day high" in result.reasons


def test_trend_reversal_adds_score():
    baseline = BaselineSnapshot(price=100, volume=1000, percent_change=3.0)
    result = evaluate_change(baseline, make_quote(97, volume=1000))  # now falling
    assert "Reversed direction from its previous trend" in result.reasons


def test_score_is_capped_at_100():
    baseline = BaselineSnapshot(price=100, volume=1000, percent_change=5.0)
    result = evaluate_change(baseline, make_quote(110, volume=5000, thirty_day_high=110))
    assert result.score <= 100


def test_quiet_result_has_data_driven_explanation():
    baseline = BaselineSnapshot(price=100, volume=1000)
    result = evaluate_change(baseline, make_quote(100.5, volume=1050, thirty_day_high=105))
    assert result.label == LABEL_QUIET
    assert "Price changed only 0.5%" in result.reasons
    assert "Normal trading volume" in result.reasons
    assert "No breakout detected" in result.reasons
