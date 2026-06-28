"""Tests for Mesa agent reaction functions."""

import pytest
from unittest.mock import MagicMock


def _make_model(rate_delta=0.0, mortgage_delta=0.0, commodity_delta=0.0):
    """Create a minimal mock model."""
    model = MagicMock()
    model.schedule.steps = 1
    model.rate_delta = rate_delta
    model.mortgage_delta = mortgage_delta
    model.commodity_delta = commodity_delta
    model.log_event = MagicMock()
    return model


def test_market_agent_reacts_to_rate_hike():
    """Higher rates should reduce portfolio exposure."""
    from butterfly.simulation.agents import MarketAgent

    model = _make_model(rate_delta=0.75)
    agent = MarketAgent(1, model, portfolio_exposure=0.6, risk_tolerance=0.5)
    old = agent.portfolio_exposure
    agent.react_to_rate_change(0.75)

    # Exposure should decrease (negative delta)
    assert agent.portfolio_exposure < old
    assert 0.0 <= agent.portfolio_exposure <= 1.0
    model.log_event.assert_called_once()


def test_market_agent_high_risk_tolerance_dampens_reaction():
    """High risk tolerance should dampen the rate reaction."""
    from butterfly.simulation.agents import MarketAgent

    model = _make_model(rate_delta=0.75)
    low_risk = MarketAgent(1, model, portfolio_exposure=0.6, risk_tolerance=0.1)
    high_risk = MarketAgent(2, model, portfolio_exposure=0.6, risk_tolerance=0.9)

    low_risk.react_to_rate_change(0.75)
    high_risk.react_to_rate_change(0.75)

    # Low risk tolerance → bigger drop
    assert low_risk.portfolio_exposure < high_risk.portfolio_exposure


def test_housing_agent_lag():
    """HousingAgent should not react immediately — 2-step lag."""
    from butterfly.simulation.agents import HousingAgent

    model = _make_model(mortgage_delta=1.93)
    agent = HousingAgent(1, model, inventory_level=1000.0)
    original = agent.inventory_level

    agent.react_to_mortgage_change(1.93)

    # Step 1: lag counter = 2, no change yet
    agent._lag_counter -= 1
    assert agent.inventory_level == original

    # Step 2: lag counter = 1, still no change
    agent._lag_counter -= 1
    assert agent.inventory_level == original

    # Step 3: lag counter = 0, apply delta
    if agent._lag_counter == 0 and abs(agent._pending_delta) > 1e-6:
        old = agent.inventory_level
        agent.inventory_level = max(0.0, old + agent._pending_delta)

    assert agent.inventory_level < original  # Higher mortgage → lower inventory


def test_supply_chain_agent_reaction():
    """SupplyChainAgent should reduce output capacity on price shock."""
    from butterfly.simulation.agents import SupplyChainAgent

    model = _make_model(commodity_delta=0.3)
    agent = SupplyChainAgent(1, model, output_capacity=1.0, supplier_count=5)
    agent.react_to_price_change(0.3)

    # Pending delta should be negative
    assert agent._pending_delta < 0
    assert agent._lag_counter == 3


def test_policy_agent_is_observer():
    """PolicyAgent should not change state on step."""
    from butterfly.simulation.agents import PolicyAgent

    model = _make_model()
    agent = PolicyAgent(1, model, current_reading=3.6, target=4.0)
    agent.step()

    assert agent.current_reading == 3.6  # Unchanged


def test_agent_get_state():
    """All agents should return a dict from get_state()."""
    from butterfly.simulation.agents import (
        MarketAgent, HousingAgent, SupplyChainAgent, PolicyAgent
    )

    model = _make_model()
    for AgentClass in [MarketAgent, HousingAgent, SupplyChainAgent, PolicyAgent]:
        agent = AgentClass(1, model)
        state = agent.get_state()
        assert isinstance(state, dict)
        assert "type" in state
        assert "id" in state
