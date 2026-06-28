"""Tests for backtesting infrastructure."""

import pytest
import asyncio
from pathlib import Path
import tempfile

from butterfly.backtesting.cases import get_case, list_cases
from butterfly.backtesting.scorer import ChainScorer
from butterfly.backtesting.runner import BacktestRunner, load_backtest_cache, save_backtest_cache


def test_backtest_case_exists():
    """Test that backtesting cases are defined."""
    cases = list_cases()
    assert len(cases) >= 5
    assert get_case("fed_rate_hike_june_2022") is not None


def test_scorer_marks_matched_hop_correctly():
    """Test that scorer correctly identifies matched hops."""
    scorer = ChainScorer()

    predicted = ["Bond yields rose", "Mortgage rates increased", "Housing starts fell"]
    known = [
        {"description": "Bond yields rose sharply"},
        {"description": "Mortgage rates increased"},
        {"description": "Housing starts declined"},
    ]

    score = scorer.score_chain(predicted, known)

    # All three should match well
    assert score.matched_hops >= 2, f"Expected 2+ matched, got {score.matched_hops}"
    assert score.accuracy_score > 0.6


def test_scorer_marks_missed_hop_correctly():
    """Test that scorer correctly identifies missed hops."""
    scorer = ChainScorer()

    predicted = ["Unrelated event happens"]
    known = [
        {"description": "Bond yields rose sharply"},
        {"description": "Mortgage rates increased"},
    ]

    score = scorer.score_chain(predicted, known)

    # Should mark as missed or unknown
    assert score.matched_hops == 0
    assert score.accuracy_score < 0.5


def test_scorer_handles_partial_match():
    """Test that scorer identifies partial matches."""
    scorer = ChainScorer()

    predicted = ["Bond yields rose sharply"]
    known = [
        {"description": "Bond yields rose in response to rate hike"},
    ]

    score = scorer.score_chain(predicted, known)

    # Should be a partial match
    assert score.partial_hops >= 1, f"Expected partial hop, got: {score}"
    assert score.accuracy_score > 0.4  # Partial is worth 50%


def test_backtest_runner_initialization():
    """Test that runner initializes properly."""
    runner = BacktestRunner()
    assert runner.scorer is not None


def test_backtest_runner_mock_score_all_cases():
    """Test that runner can generate mock scores for all cases."""
    runner = BacktestRunner()

    for case in list_cases():
        result = runner.mock_score_case(case.id)
        assert result["status"] == "success"
        assert result["case_id"] == case.id
        assert "comparison" in result
        assert "predicted_chain" in result


@pytest.mark.asyncio
async def test_backtest_runner_async():
    """Test async backtest running."""
    runner = BacktestRunner()
    result = await runner.run_backtest("fed_rate_hike_june_2022")
    assert result["status"] == "success"
    assert result["case_id"] == "fed_rate_hike_june_2022"


def test_cache_save_and_load():
    """Test that cache saves and loads correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.json"

        # Save cache
        test_cache = {"test_case": {"data": "value"}}
        save_backtest_cache(test_cache, cache_path)
        assert cache_path.exists()

        # Load cache
        loaded = load_backtest_cache(cache_path)
        assert loaded == test_cache


def test_cache_load_missing_file():
    """Test that load returns empty dict for missing file."""
    loaded = load_backtest_cache("/nonexistent/path/cache.json")
    assert loaded == {}


def test_scorer_format_result():
    """Test that scorer formats results correctly."""
    scorer = ChainScorer()

    predicted = ["Bond yields rose", "Rates increased"]
    known = [
        {"description": "Bond yields rose sharply"},
        {"description": "Rates increased"},
    ]

    score = scorer.score_chain(predicted, known)
    score.case_id = "test_case"

    formatted = scorer.format_result(score)

    assert "case_id" in formatted
    assert "accuracy_score" in formatted
    assert "hop_comparisons" in formatted
    assert formatted["accuracy_score"] >= 0
    assert formatted["accuracy_score"] <= 100
    assert "summary" in formatted


def test_known_outcomes_structure():
    """Test that known outcomes have correct structure."""
    case = get_case("fed_rate_hike_june_2022")
    assert case is not None
    assert len(case.known_outcomes) >= 4

    # Each outcome should have required fields
    for outcome in case.known_outcomes:
        assert hasattr(outcome, "hop")
        assert hasattr(outcome, "description")
        assert hasattr(outcome, "verified")
        assert hasattr(outcome, "source")
        assert hasattr(outcome, "timing_actual")
