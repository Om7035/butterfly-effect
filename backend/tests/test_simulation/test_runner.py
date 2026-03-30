"""Tests for simulation runner."""

import pytest
from butterfly.simulation.runner import SimulationRunner


FED_SIGNAL = {
    "event_id": "test_event",
    "rate_delta": 0.75,
    "mortgage_delta": 1.93,
    "commodity_delta": 0.0,
}


@pytest.mark.asyncio
async def test_run_parallel_completes():
    """Simulation should complete and return a result."""
    runner = SimulationRunner()
    result = await runner.run_parallel(
        event_signal=FED_SIGNAL,
        steps=10,
        n_market=5,
        n_housing=3,
        n_supply=2,
        n_policy=1,
    )

    assert result.steps_completed == 10
    assert result.duration_seconds >= 0  # can be 0.0 on fast machines
    assert result.n_agents == 11


@pytest.mark.asyncio
async def test_timelines_diverge():
    """Timeline A should differ from Timeline B after event injection."""
    runner = SimulationRunner()
    result = await runner.run_parallel(
        event_signal=FED_SIGNAL,
        steps=20,
        n_market=10,
        n_housing=5,
        n_supply=3,
        n_policy=2,
    )

    # Both timelines should have data
    assert len(result.timeline_a) > 0
    assert len(result.timeline_b) > 0

    # At least one metric should differ between A and B
    a_vals = list(result.timeline_a.values())
    b_vals = list(result.timeline_b.values())

    if a_vals and b_vals:
        a_last = a_vals[-1]
        b_last = b_vals[-1]
        # Check avg_portfolio_exposure differs
        a_exp = a_last.get("avg_portfolio_exposure", 0)
        b_exp = b_last.get("avg_portfolio_exposure", 0)
        assert abs(a_exp - b_exp) > 0.001, "Timelines should diverge after event"


@pytest.mark.asyncio
async def test_agent_logs_populated():
    """Agent logs should be non-empty after event injection."""
    runner = SimulationRunner()
    result = await runner.run_parallel(
        event_signal=FED_SIGNAL,
        steps=5,
        n_market=5,
        n_housing=3,
        n_supply=2,
        n_policy=1,
    )

    assert len(result.agent_logs) > 0
    log = result.agent_logs[0]
    assert "agent_id" in log
    assert "property" in log
    assert "old_value" in log
    assert "new_value" in log
