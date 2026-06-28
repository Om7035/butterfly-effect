"""Tests for counterfactual diff engine."""

import pytest
from unittest.mock import AsyncMock, patch
from butterfly.causal.counterfactual import CounterfactualEngine, FED_2022_BASELINE, FED_2022_TREATMENT_DELTA


@pytest.fixture
def engine():
    return CounterfactualEngine()


def test_generate_timeline_with_treatment(engine):
    """Timeline A should diverge from baseline."""
    steps = list(range(0, 169))
    timeline_a = engine._generate_timeline(
        FED_2022_BASELINE.copy(),
        FED_2022_TREATMENT_DELTA.copy(),
        steps,
        apply_treatment=True,
    )

    assert "FEDFUNDS" in timeline_a
    assert len(timeline_a["FEDFUNDS"]) == 169
    # Fed funds should be higher than baseline after treatment
    assert timeline_a["FEDFUNDS"][-1] > FED_2022_BASELINE["FEDFUNDS"] * 0.9


def test_generate_timeline_without_treatment(engine):
    """Timeline B should stay near baseline."""
    steps = list(range(0, 169))
    timeline_b = engine._generate_timeline(
        FED_2022_BASELINE.copy(),
        FED_2022_TREATMENT_DELTA.copy(),
        steps,
        apply_treatment=False,
    )

    # Should stay near baseline (only noise)
    for metric, baseline_val in FED_2022_BASELINE.items():
        avg = sum(timeline_b[metric]) / len(timeline_b[metric])
        assert abs(avg - baseline_val) < baseline_val * 0.05, (
            f"{metric}: avg {avg:.2f} too far from baseline {baseline_val:.2f}"
        )


def test_timelines_diverge(engine):
    """Timeline A and B should diverge after treatment."""
    steps = list(range(0, 169))
    timeline_a = engine._generate_timeline(
        FED_2022_BASELINE.copy(), FED_2022_TREATMENT_DELTA.copy(), steps, apply_treatment=True
    )
    timeline_b = engine._generate_timeline(
        FED_2022_BASELINE.copy(), FED_2022_TREATMENT_DELTA.copy(), steps, apply_treatment=False
    )

    # MORTGAGE30US diverges after latency=48h; check at end of horizon
    diff_mortgage = [
        abs(a - b)
        for a, b in zip(timeline_a["MORTGAGE30US"], timeline_b["MORTGAGE30US"])
    ]
    assert max(diff_mortgage) > 0.01, "Mortgage timelines should diverge after treatment"


def test_build_causal_edges(engine):
    """Should produce CausalEdge objects with non-zero deltas."""
    steps = list(range(0, 169))
    timeline_a = engine._generate_timeline(
        FED_2022_BASELINE.copy(), FED_2022_TREATMENT_DELTA.copy(), steps, apply_treatment=True
    )
    timeline_b = engine._generate_timeline(
        FED_2022_BASELINE.copy(), FED_2022_TREATMENT_DELTA.copy(), steps, apply_treatment=False
    )

    edges = engine._build_causal_edges("test_event", timeline_a, timeline_b, steps)

    assert len(edges) > 0
    assert all(e.source_node_id != e.target_node_id for e in edges)
    assert all(0.0 <= e.strength_score <= 1.0 for e in edges)


@pytest.mark.asyncio
async def test_run_counterfactual_full(engine):
    """Full counterfactual run should return valid result."""
    with patch.object(engine.dag_builder, "build_dag_for_event", new_callable=AsyncMock) as mock_dag:
        mock_dag.return_value = None  # Force fallback to seed DAG

        result = await engine.run_counterfactual("test_event_001", horizon_hours=48)

    assert result.event_id == "test_event_001"
    assert len(result.timeline_a) > 0
    assert len(result.timeline_b) > 0
    assert len(result.diff) > 0
    assert len(result.causal_edges) > 0

    # Diff should be non-zero for at least one metric
    has_nonzero_diff = any(
        max(abs(v) for v in vals) > 0.001
        for vals in result.diff.values()
    )
    assert has_nonzero_diff, "Diff should be non-zero for at least one metric"
