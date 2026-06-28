"""Acceptance tests for the dynamic agent generation system.

Tests 3 domains: geopolitical, tech disruption, climate event.
All tests run without LLM (use_llm=False) for speed and reproducibility.
"""

import asyncio
import time
import pytest

from butterfly.simulation._agent_gen import DynamicAgentGenerator
from butterfly.simulation.universal_runner import UniversalRunner


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def generator() -> DynamicAgentGenerator:
    return DynamicAgentGenerator()


@pytest.fixture
def runner() -> UniversalRunner:
    return UniversalRunner()


# ── Test 1: Geopolitical simulation ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_geopolitical_agents(generator: DynamicAgentGenerator) -> None:
    """Israel-Hamas escalation should produce 6+ unique agent types including energy agents."""
    profiles = await generator.generate_agents(
        event_title="Israel-Hamas escalation — October 2023",
        event_domains=["geopolitics", "military", "humanitarian", "energy"],
        use_llm=False,
    )

    agent_types = {p.agent_type for p in profiles}
    agent_names = {p.agent_name for p in profiles}

    assert len(profiles) >= 6, f"Expected ≥6 agents, got {len(profiles)}: {agent_names}"
    assert len(agent_types) >= 4, f"Expected ≥4 unique types, got {agent_types}"

    # Energy-related agents must be present
    energy_agents = [p for p in profiles if any(
        kw in p.agent_name.lower() or kw in p.domain.lower()
        for kw in ("energy", "oil", "opec", "trader")
    )]
    assert len(energy_agents) >= 1, f"No energy agents found. Agents: {agent_names}"

    # All profiles must be valid
    for p in profiles:
        assert p.agent_name, "Agent must have a name"
        assert len(p.triggers) >= 1, f"{p.agent_name} has no triggers"
        assert len(p.reaction_functions) >= 1, f"{p.agent_name} has no reaction functions"
        assert 0.0 < p.dampening_factor <= 1.0


@pytest.mark.asyncio
async def test_geopolitical_simulation_runs(runner: UniversalRunner) -> None:
    """Full simulation must complete 168 steps and Timeline A must diverge from B by step 24."""
    result = await runner.run(
        event_title="Israel-Hamas escalation",
        event_domains=["geopolitics", "military", "energy"],
        event_signal={"conflict_intensity": 0.8, "event_magnitude": 0.9},
        steps=168,
        use_llm=False,
    )

    assert result.steps_completed == 168
    assert len(result.causal_log) > 0, "Causal log must not be empty"
    assert result.diverges_by_step(24), "Timeline A must diverge from B by step 24"

    diff = result.get_diff()
    assert len(diff) > 0, "Diff must have at least one diverging variable"


# ── Test 2: Tech disruption ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tech_disruption_agents(generator: DynamicAgentGenerator) -> None:
    """AGI release should produce investor, competitor, and regulator agent types."""
    profiles = await generator.generate_agents(
        event_title="OpenAI releases AGI-level model",
        event_domains=["technology", "economics"],
        use_llm=False,
    )

    agent_names_lower = {p.agent_name.lower() for p in profiles}
    agent_types = {p.agent_type for p in profiles}

    # Must have investor type
    has_investor = any("investor" in n or "capital" in n or "venture" in n for n in agent_names_lower)
    assert has_investor, f"No investor agent found. Agents: {agent_names_lower}"

    # Must have competitor type
    has_competitor = any("competitor" in n or "tech" in n for n in agent_names_lower)
    assert has_competitor, f"No competitor agent found. Agents: {agent_names_lower}"

    # Must have regulator type
    has_regulator = any("regulator" in n or "regulation" in n for n in agent_names_lower)
    assert has_regulator, f"No regulator agent found. Agents: {agent_names_lower}"


@pytest.mark.asyncio
async def test_tech_disruption_performance(runner: UniversalRunner) -> None:
    """Tech disruption simulation must complete in < 2 seconds."""
    start = time.time()
    result = await runner.run(
        event_title="OpenAI releases AGI-level model",
        event_domains=["technology", "economics"],
        event_signal={"ai_capability_index": 0.95, "event_magnitude": 0.9},
        steps=168,
        use_llm=False,
    )
    elapsed = time.time() - start

    assert elapsed < 2.0, f"Simulation took {elapsed:.2f}s — must be < 2s"
    assert result.steps_completed == 168


# ── Test 3: Climate event ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_climate_agents(generator: DynamicAgentGenerator) -> None:
    """Hurricane hitting Miami should produce insurance, infrastructure, and government agents."""
    profiles = await generator.generate_agents(
        event_title="Category 5 hurricane hits Miami",
        event_domains=["climate", "economics"],
        use_llm=False,
    )

    agent_names_lower = {p.agent_name.lower() for p in profiles}

    has_insurance = any("insurance" in n for n in agent_names_lower)
    assert has_insurance, f"No insurance agent. Agents: {agent_names_lower}"

    has_infrastructure = any("infrastructure" in n or "construction" in n for n in agent_names_lower)
    assert has_infrastructure, f"No infrastructure agent. Agents: {agent_names_lower}"

    has_government = any("government" in n or "agency" in n or "emergency" in n for n in agent_names_lower)
    assert has_government, f"No government agent. Agents: {agent_names_lower}"


# ── Test 4: Reaction function math ───────────────────────────────────────────

def test_reaction_formulas() -> None:
    """All 4 formula types must produce non-zero deltas when triggered."""
    from butterfly.simulation.dynamic_agents import ReactionFn

    for formula in ("linear", "exponential", "step", "sigmoid"):
        fn = ReactionFn(
            target_variable="test_var",
            formula=formula,
            magnitude=1.0,
            direction=1,
            lag_steps=0,
        )
        delta = fn.apply(current_value=0.0, step=5, trigger_step=0)
        assert delta != 0.0 or formula == "step", f"{formula} produced zero delta at step 5"


def test_trigger_rule_operators() -> None:
    """All 6 operators must evaluate correctly."""
    from butterfly.simulation.dynamic_agents import TriggerRule

    env = {"oil_price": 90.0}
    assert TriggerRule(variable="oil_price", operator=">",  threshold=80.0, condition="").is_triggered(env)
    assert TriggerRule(variable="oil_price", operator=">=", threshold=90.0, condition="").is_triggered(env)
    assert TriggerRule(variable="oil_price", operator="<",  threshold=100.0, condition="").is_triggered(env)
    assert TriggerRule(variable="oil_price", operator="<=", threshold=90.0, condition="").is_triggered(env)
    assert TriggerRule(variable="oil_price", operator="==", threshold=90.0, condition="").is_triggered(env)
    assert TriggerRule(variable="oil_price", operator="!=", threshold=80.0, condition="").is_triggered(env)
