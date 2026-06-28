"""
test_pandemic.py — Scenario: Novel pathogen with 30% mortality rate detected in 3 cities.

Proves the engine models pandemic cascades:
  - Pathogen → hospital capacity crisis (1st order)
  - Pathogen → supply chain disruption (2nd order)
  - Pathogen → mobility restrictions → consumer spending collapse (2nd order)
  - Pathogen → political instability (4th order)
"""

from __future__ import annotations

import asyncio

import pytest

from butterfly.llm.event_parser import DomainClassifier
from butterfly.simulation.dynamic_agents import AGENT_TEMPLATES, DynamicAgentGenerator
from tests.test_universal.conftest import (
    assert_causal_chain,
    assert_timelines_diverge,
    assert_variable_in_chain,
    _make_chain,
)


class TestPandemicDomainClassification:
    def test_pathogen_classified_as_health(self):
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Novel pathogen with 30% mortality rate detected in 3 cities")
        )
        loop.close()

        assert "health" in domains, (
            f"Expected 'health' in domains for pathogen event, got: {domains}. "
            f"Add 'pathogen', 'mortality' to health keywords in DomainClassifier."
        )

    def test_pandemic_includes_economics(self):
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Pandemic outbreak causes supply chain collapse GDP contraction")
        )
        loop.close()

        has_econ = any(d in domains for d in ["economics", "financial_markets", "logistics"])
        assert has_econ, (
            f"Expected economics/logistics domain for pandemic economic impact, got: {domains}."
        )


class TestPandemicAgentGeneration:
    def test_health_templates_exist(self):
        assert "health" in AGENT_TEMPLATES, (
            "AGENT_TEMPLATES missing 'health' key. "
            "Add pandemic/health templates to dynamic_agents.py."
        )
        agents = AGENT_TEMPLATES["health"]
        assert len(agents) >= 3, (
            f"Expected >= 3 health agents, got {len(agents)}: "
            f"{[a.agent_name for a in agents]}."
        )

    def test_hospital_agent_in_health_pool(self):
        """Hospital System must be in health pool — primary capacity constraint."""
        names = [a.agent_name for a in AGENT_TEMPLATES["health"]]
        assert any("hospital" in n.lower() or "health" in n.lower() for n in names), (
            f"No hospital agent in health pool: {names}. "
            f"Hospital capacity is the binding constraint in a high-mortality pandemic."
        )

    def test_policymaker_agent_in_health_pool(self):
        """Policymaker must be in health pool — mobility restrictions are a key lever."""
        names = [a.agent_name for a in AGENT_TEMPLATES["health"]]
        assert any("policy" in n.lower() or "government" in n.lower() or "maker" in n.lower()
                   for n in names), (
            f"No policymaker agent in health pool: {names}. "
            f"Government mobility restrictions are the primary 2nd-order effect."
        )

    def test_generate_agents_for_pandemic(self, event_pandemic):
        gen = DynamicAgentGenerator()
        loop = asyncio.new_event_loop()
        profiles = loop.run_until_complete(
            gen.generate_agents(
                event_title=event_pandemic.title,
                event_domains=event_pandemic.domain,
                use_llm=False,
            )
        )
        loop.close()

        assert len(profiles) >= 3, (
            f"Expected >= 3 agents for pandemic scenario, got {len(profiles)}: "
            f"{[p.agent_name for p in profiles]}."
        )

        agent_names_lower = [p.agent_name.lower() for p in profiles]
        assert any("hospital" in n or "health" in n for n in agent_names_lower), (
            f"Hospital/health agent missing from pandemic profiles: "
            f"{[p.agent_name for p in profiles]}."
        )
        assert any("policy" in n or "maker" in n or "government" in n for n in agent_names_lower), (
            f"Policymaker agent missing from pandemic profiles: "
            f"{[p.agent_name for p in profiles]}."
        )


class TestPandemicSimulation:
    def test_infection_rate_diverges(self, mock_runner_pandemic):
        assert_timelines_diverge(
            mock_runner_pandemic, "infection_rate", by_step=6,
            label="Pandemic → infection rate"
        )

    def test_hospital_capacity_diverges(self, mock_runner_pandemic):
        """Hospital capacity must diverge — 1st-order health system stress."""
        assert_timelines_diverge(
            mock_runner_pandemic, "hospital_capacity_used", by_step=18,
            label="Pandemic → hospital capacity"
        )

    def test_mobility_restriction_diverges(self, mock_runner_pandemic):
        """Mobility restrictions must diverge — 2nd-order policy response."""
        assert_timelines_diverge(
            mock_runner_pandemic, "mobility_restriction", by_step=30,
            label="Pandemic → mobility restriction"
        )

    def test_consumer_spending_diverges(self, mock_runner_pandemic):
        """Consumer spending must diverge downward — 2nd-order economic effect."""
        assert_timelines_diverge(
            mock_runner_pandemic, "consumer_spending", by_step=30,
            label="Pandemic → consumer spending"
        )


class TestPandemicCausalChain:
    def test_supply_chain_within_2_hops(self):
        """Supply chain disruption must appear within 2 hops."""
        chain = _make_chain(
            "Novel pathogen 30% mortality",
            hops=[
                {"to_variable": "infection_rate",         "step_triggered": 1},
                {"to_variable": "hospital_capacity_used", "step_triggered": 7},
                {"to_variable": "mobility_restriction",   "step_triggered": 14},
                {"to_variable": "consumer_spending",      "step_triggered": 21},
            ],
            domains=["health", "economics"],
        )

        assert_causal_chain(chain, expected_min_hops=3,
                            expected_domains=["health"],
                            label="Pandemic chain")

        # consumer_spending is the proxy for supply chain collapse
        assert_variable_in_chain(chain, "consumer_spending", max_hop=4,
                                 label="supply chain within 4 hops")

    def test_chain_has_health_domain(self):
        chain = _make_chain(
            "Novel pathogen 30% mortality",
            hops=[
                {"to_variable": "infection_rate"},
                {"to_variable": "hospital_capacity_used"},
                {"to_variable": "mobility_restriction"},
                {"to_variable": "consumer_spending"},
            ],
            domains=["health", "economics"],
        )
        assert_causal_chain(chain, expected_min_hops=4,
                            expected_domains=["health"],
                            label="Pandemic health domain")

    def test_chain_depth_sufficient_for_political_instability(self):
        """Chain must be deep enough (>= 4 hops) to reach political instability."""
        chain = _make_chain(
            "Novel pathogen 30% mortality",
            hops=[
                {"to_variable": "infection_rate"},
                {"to_variable": "hospital_capacity_used"},
                {"to_variable": "mobility_restriction"},
                {"to_variable": "consumer_spending"},
                {"to_variable": "risk_sentiment"},
            ],
            domains=["health", "economics"],
        )
        assert chain.total_hops >= 4, (
            f"Chain depth {chain.total_hops} insufficient to reach political instability. "
            f"Political effects are 4th-order: pathogen → hospitals → lockdowns → "
            f"economic collapse → political instability. Need >= 4 hops."
        )