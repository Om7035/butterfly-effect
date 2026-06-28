"""
conftest.py — Universal test suite fixtures.

All tests run in mock mode by default (no API keys, no network, < 60s total).
Pass --live to pytest to run against real APIs.

Usage:
    pytest backend/tests/test_universal/          # mock mode (fast)
    pytest backend/tests/test_universal/ --live   # real APIs (slow)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from butterfly.causal.log_extractor import CausalHop, CausalLogExtractor, SimulationCausalChain
from butterfly.llm.event_parser import UniversalEvent
from butterfly.simulation.dynamic_agents import BehaviorProfile, ReactionFn, TriggerRule
from butterfly.simulation.universal_runner import UniversalRunner, UniversalSimulationResult


# ── CLI flag ──────────────────────────────────────────────────────────────────

def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False,
                     help="Run against real APIs (requires API keys)")


@pytest.fixture(scope="session")
def live_mode(request):
    return request.config.getoption("--live")


# ── Event fixtures ────────────────────────────────────────────────────────────

def _make_event(
    title: str,
    domain: list[str],
    actors: list[str],
    systems: list[str],
    scope: list[str],
    severity: str,
    seeds: list[str],
    raw: str = "",
) -> UniversalEvent:
    return UniversalEvent(
        raw_input=raw or title,
        title=title,
        domain=domain,
        primary_actors=actors,
        affected_systems=systems,
        geographic_scope=scope,
        time_horizon="weeks",
        severity=severity,
        causal_seeds=seeds,
        data_fetch_queries=[f"{title} economic impact", f"{title} market reaction", f"{title} policy response"],
        occurred_at=datetime(2024, 1, 1),
        confidence=0.85,
    )


@pytest.fixture
def event_geopolitical():
    return _make_event(
        title="Hamas attacks Israel — October 7 2023",
        domain=["geopolitics", "military", "humanitarian", "energy"],
        actors=["Hamas", "Israel", "Iran", "United States", "Hezbollah"],
        systems=["Middle East oil supply", "global shipping", "refugee systems", "US defense budget"],
        scope=["Israel", "Gaza", "Lebanon", "Iran", "Global"],
        severity="catastrophic",
        seeds=[
            "Oil futures spike on Strait of Hormuz risk premium",
            "US carrier groups deploy — defense contractor stocks surge",
            "Red Sea shipping reroutes add 14 days to EU-Asia transit",
            "Iran proxy network activates across Lebanon, Yemen, Iraq",
            "Humanitarian corridor negotiations stall — displacement accelerates",
        ],
    )


@pytest.fixture
def event_natural_disaster():
    return _make_event(
        title="Category 5 hurricane makes landfall in Miami",
        domain=["climate", "economics", "logistics"],
        actors=["FEMA", "Florida Governor", "Insurance Industry", "Army Corps of Engineers"],
        systems=["insurance market", "construction supply chain", "Florida real estate", "port of Miami"],
        scope=["Florida", "Southeast US", "Caribbean", "Global reinsurance"],
        severity="catastrophic",
        seeds=[
            "Insurance market reprices Florida coastal risk — premiums spike 40%",
            "Construction material shortage as 3 states compete for lumber and concrete",
            "Port of Miami closure disrupts $1B/day in trade",
            "Federal disaster declaration unlocks $50B in emergency spending",
            "Climate risk models force mortgage market repricing",
        ],
    )


@pytest.fixture
def event_tech_disruption():
    return _make_event(
        title="OpenAI releases model that outperforms all human experts",
        domain=["technology", "economics", "geopolitics"],
        actors=["OpenAI", "Google DeepMind", "US Government", "China", "Venture Capital"],
        systems=["labor market", "venture capital", "knowledge work", "AI regulation", "US-China AI race"],
        scope=["United States", "China", "European Union", "Global"],
        severity="catastrophic",
        seeds=[
            "Venture capital floods into AI infrastructure — $200B deployment in 90 days",
            "White-collar employment contracts trigger mass renegotiation",
            "China accelerates domestic AI program — export controls tighten",
            "EU AI Act enforcement triggers regulatory arbitrage to Singapore",
            "Knowledge worker unions form in 12 countries within 6 months",
        ],
    )


@pytest.fixture
def event_pandemic():
    return _make_event(
        title="Novel pathogen with 30% mortality rate detected in 3 cities",
        domain=["health", "economics", "political"],
        actors=["WHO", "CDC", "National Governments", "Pharmaceutical Companies", "Hospital Systems"],
        systems=["global supply chain", "hospital capacity", "political stability", "pharmaceutical supply"],
        scope=["Global", "United States", "China", "Europe"],
        severity="catastrophic",
        seeds=[
            "WHO declares PHEIC — 47 countries close borders within 72 hours",
            "Hospital systems in affected cities hit 100% capacity by day 14",
            "Supply chain disruption: 60% of PPE manufactured in affected region",
            "Political instability as governments impose emergency powers",
            "Pharmaceutical companies pivot all capacity to vaccine development",
        ],
    )


@pytest.fixture
def event_corporate():
    return _make_event(
        title="Nvidia acquires TSMC — $500B deal announced",
        domain=["technology", "economics", "geopolitics"],
        actors=["Nvidia", "TSMC", "AMD", "Intel", "US Government", "China", "Taiwan"],
        systems=["semiconductor supply chain", "AI hardware market", "US-China relations", "chip pricing"],
        scope=["Taiwan", "United States", "China", "South Korea", "Global"],
        severity="major",
        seeds=[
            "AMD and Intel lose access to leading-edge fab capacity",
            "China threatens military response — Taiwan Strait tensions spike",
            "US antitrust review triggers 18-month regulatory uncertainty",
            "Chip prices spike 60% as customers panic-buy inventory",
            "South Korea accelerates Samsung fab expansion as hedge",
        ],
    )


# ── Simulation result builder ─────────────────────────────────────────────────

def _make_sim_result(
    event_title: str,
    diverging_vars: dict[str, float],
    agent_types: list[str],
    steps: int = 48,
) -> UniversalSimulationResult:
    """Build a realistic UniversalSimulationResult for testing."""
    tl_a: dict[int, dict] = {}
    tl_b: dict[int, dict] = {}

    for step in range(0, steps + 1, 6):
        snap_a = {}
        snap_b = {}
        for var, delta in diverging_vars.items():
            base = 50.0
            snap_b[var] = base
            snap_a[var] = base + delta * (step / steps)
        tl_a[step] = snap_a
        tl_b[step] = snap_b

    causal_log = []
    for i, (var, delta) in enumerate(diverging_vars.items()):
        causal_log.append({
            "agent_id": f"agent_{i:03d}",
            "agent_name": agent_types[i % len(agent_types)],
            "timestep": i * 3 + 1,
            "variable_changed": var,
            "old_value": 50.0,
            "new_value": 50.0 + delta,
            "delta": delta,
            "trigger_fired": f"{var} > 0.3",
        })

    return UniversalSimulationResult(
        run_id=f"test_run_{event_title[:10]}",
        event_title=event_title,
        timeline_a=tl_a,
        timeline_b=tl_b,
        causal_log=causal_log,
        steps_completed=steps,
        duration_seconds=0.5,
        n_agents=len(agent_types),
        agent_types=agent_types,
    )


# ── Causal chain builder ──────────────────────────────────────────────────────

def _make_chain(
    event_title: str,
    hops: list[dict],
    domains: list[str],
) -> SimulationCausalChain:
    """Build a SimulationCausalChain for testing."""
    chain_hops = []
    for i, h in enumerate(hops):
        chain_hops.append(CausalHop(
            from_agent=h.get("from_agent", f"Agent_{i}"),
            to_variable=h["to_variable"],
            mechanism=h.get("mechanism", f"Agent reacted to trigger → changed {h['to_variable']}"),
            step_triggered=h.get("step_triggered", i * 4 + 1),
            step_peak=h.get("step_peak", i * 4 + 6),
            magnitude=h.get("magnitude", 0.5),
            persistence=h.get("persistence", 0.6),
            confidence=h.get("confidence", 0.75),
        ))
    return SimulationCausalChain(
        event_title=event_title,
        chains=chain_hops,
        feedback_loops=[],
        total_hops=len(chain_hops),
        peak_effect_step=max((h.step_peak for h in chain_hops), default=0),
        domain_coverage=domains,
        extraction_ms=1.0,
    )


# ── Mock runner fixture ───────────────────────────────────────────────────────

@pytest.fixture
def mock_runner_geopolitical():
    return _make_sim_result(
        "Hamas attacks Israel",
        diverging_vars={
            "conflict_intensity": 0.85,
            "oil_price": 12.0,
            "insurance_premium": 0.4,
            "displacement_count": 75000.0,
            "diplomatic_activity": 0.6,
            "shipping_disruption": 0.35,
        },
        agent_types=["Energy Trader", "OPEC", "Diplomat", "Refugee Population",
                     "Insurance Market", "Central Bank (Affected Region)"],
    )


@pytest.fixture
def mock_runner_disaster():
    return _make_sim_result(
        "Category 5 hurricane Miami",
        diverging_vars={
            "storm_intensity": 0.95,
            "insurance_payout": 18.0,
            "infrastructure_damage": 0.8,
            "construction_demand": 0.75,
            "emergency_spending": 6.0,
        },
        agent_types=["Insurance Company", "Infrastructure Agency",
                     "Government Emergency Agency", "Construction Supply Chain"],
    )


@pytest.fixture
def mock_runner_tech():
    return _make_sim_result(
        "OpenAI AGI release",
        diverging_vars={
            "ai_capability_index": 0.95,
            "ai_investment_flow": 3.2,
            "rd_spending": 0.5,
            "regulatory_pressure": 0.6,
            "tech_employment": -0.12,
        },
        agent_types=["Venture Capitalist", "Tech Competitor", "Regulator", "Labor Market"],
    )


@pytest.fixture
def mock_runner_pandemic():
    return _make_sim_result(
        "Novel pathogen 30% mortality",
        diverging_vars={
            "infection_rate": 0.18,
            "hospital_capacity_used": 0.45,
            "mobility_restriction": 0.6,
            "consumer_spending": -0.3,
        },
        agent_types=["Hospital System", "Policymaker", "General Public"],
    )


# ── Assert helpers ────────────────────────────────────────────────────────────

def assert_causal_chain(
    chain: SimulationCausalChain,
    expected_min_hops: int,
    expected_domains: list[str],
    label: str = "",
) -> None:
    """Assert a causal chain meets minimum quality requirements.

    Args:
        chain: The SimulationCausalChain to validate
        expected_min_hops: Minimum number of causal hops required
        expected_domains: Domain strings that must appear in domain_coverage
        label: Human-readable label for failure messages
    """
    prefix = f"[{label}] " if label else ""

    assert chain.total_hops >= expected_min_hops, (
        f"{prefix}Expected at least {expected_min_hops} causal hops, "
        f"got {chain.total_hops}. "
        f"Hops found: {[h.to_variable for h in chain.chains]}. "
        f"This means the simulation did not produce enough causal divergence — "
        f"check that event_signal values are above agent trigger thresholds."
    )

    missing_domains = [d for d in expected_domains if d not in chain.domain_coverage]
    assert not missing_domains, (
        f"{prefix}Expected domains {expected_domains} in chain, "
        f"but missing: {missing_domains}. "
        f"Domains found: {chain.domain_coverage}. "
        f"Variables in chain: {[h.to_variable for h in chain.chains]}. "
        f"Check _VAR_DOMAIN_MAP in log_extractor.py — the variables may not be mapped."
    )


def assert_variable_in_chain(
    chain: SimulationCausalChain,
    variable: str,
    max_hop: int,
    label: str = "",
) -> None:
    """Assert a specific variable appears in the chain within N hops."""
    prefix = f"[{label}] " if label else ""
    hop_vars = [h.to_variable for h in chain.chains]

    assert variable in hop_vars, (
        f"{prefix}Expected variable '{variable}' in causal chain, not found. "
        f"Variables present: {hop_vars}. "
        f"This means no agent changed '{variable}' significantly during simulation. "
        f"Check that an agent with a reaction targeting '{variable}' is in the agent pool "
        f"and its trigger threshold is reachable from the event signal."
    )

    hop_index = hop_vars.index(variable)
    assert hop_index < max_hop, (
        f"{prefix}Expected '{variable}' within {max_hop} hops, "
        f"but it appeared at hop {hop_index + 1}. "
        f"Chain order: {hop_vars}. "
        f"The effect is too slow — check lag_steps on the relevant ReactionFn."
    )


def assert_agent_type_present(
    result: UniversalSimulationResult,
    agent_type: str,
    label: str = "",
) -> None:
    """Assert a specific agent type was generated for the simulation."""
    prefix = f"[{label}] " if label else ""
    assert agent_type in result.agent_types, (
        f"{prefix}Expected agent type '{agent_type}' in simulation, "
        f"but only found: {result.agent_types}. "
        f"Check AGENT_TEMPLATES in dynamic_agents.py — the domain mapping may be missing "
        f"an agent of this type, or the domain was not passed to the runner."
    )


def assert_timelines_diverge(
    result: UniversalSimulationResult,
    variable: str,
    by_step: int,
    label: str = "",
) -> None:
    """Assert Timeline A diverges from B on a specific variable by a given step."""
    prefix = f"[{label}] " if label else ""
    diff = result.get_diff()

    assert variable in diff, (
        f"{prefix}Expected Timeline A to diverge from B on '{variable}', "
        f"but no divergence detected. "
        f"Diverging variables: {list(diff.keys())}. "
        f"This means the event signal did not propagate to '{variable}'. "
        f"Check that an agent reacts to the event signal and targets '{variable}'."
    )

    early_divergence = any(step <= by_step for step in diff[variable])
    assert early_divergence, (
        f"{prefix}Expected '{variable}' to diverge by step {by_step}, "
        f"but first divergence at step {min(diff[variable].keys())}. "
        f"Divergence steps: {sorted(diff[variable].keys())}. "
        f"The reaction lag_steps may be too high."
    )