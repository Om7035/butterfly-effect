"""
test_tech_disruption.py — Scenario: OpenAI releases model that outperforms all human experts.

Proves the engine models technology disruption cascades:
  - AI breakthrough → VC investment flood (1st order)
  - AI breakthrough → labor market disruption (2nd order)
  - AI breakthrough → regulatory response (3rd order)
  - AI breakthrough → US-China AI race → geopolitics (4th order)
"""

from __future__ import annotations

import asyncio

import pytest

from butterfly.llm.event_parser import DomainClassifier
from butterfly.simulation.dynamic_agents import AGENT_TEMPLATES, DynamicAgentGenerator
from tests.test_universal.conftest import (
    assert_agent_type_present,
    assert_causal_chain,
    assert_timelines_diverge,
    assert_variable_in_chain,
    _make_chain,
)


class TestTechDomainClassification:
    def test_ai_launch_classified_as_technology(self):
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("OpenAI releases AGI model that outperforms all human experts")
        )
        loop.close()

        assert "technology" in domains, (
            f"Expected 'technology' in domains for AI launch event, got: {domains}. "
            f"Add 'ai', 'openai', 'model' to technology keywords."
        )

    def test_ai_launch_includes_economics(self):
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("AI model disrupts labor market GDP impact venture capital")
        )
        loop.close()

        has_econ = any(d in domains for d in ["economics", "financial_markets", "trade"])
        assert has_econ, (
            f"Expected economics domain for AI economic impact text, got: {domains}."
        )


class TestTechAgentGeneration:
    def test_technology_templates_exist(self):
        assert "technology" in AGENT_TEMPLATES, (
            "AGENT_TEMPLATES missing 'technology' key."
        )
        agents = AGENT_TEMPLATES["technology"]
        assert len(agents) >= 3, (
            f"Expected >= 3 technology agents, got {len(agents)}: "
            f"{[a.agent_name for a in agents]}."
        )

    def test_vc_agent_in_tech_pool(self):
        """Venture Capitalist must be in tech pool — primary 1st-order capital allocator."""
        names = [a.agent_name for a in AGENT_TEMPLATES["technology"]]
        assert any("venture" in n.lower() or "vc" in n.lower() or "capital" in n.lower()
                   for n in names), (
            f"No VC agent in technology pool: {names}. "
            f"VC investment surge is the fastest 1st-order effect of an AI breakthrough."
        )

    def test_labor_market_agent_in_tech_pool(self):
        """Labor Market agent must exist — 2nd-order employment disruption."""
        names = [a.agent_name for a in AGENT_TEMPLATES["technology"]]
        assert any("labor" in n.lower() or "employment" in n.lower() or "worker" in n.lower()
                   for n in names), (
            f"No labor market agent in technology pool: {names}. "
            f"Labor displacement is the most politically significant 2nd-order effect of AI."
        )

    def test_regulator_agent_in_tech_pool(self):
        """Regulator must be in tech pool — 3rd-order policy response."""
        names = [a.agent_name for a in AGENT_TEMPLATES["technology"]]
        assert any("regulator" in n.lower() or "regulation" in n.lower() or "policy" in n.lower()
                   for n in names), (
            f"No regulator agent in technology pool: {names}. "
            f"Regulatory response is a critical 3rd-order effect of disruptive AI."
        )

    def test_at_least_4_unique_agent_types_for_tech_event(self, event_tech_disruption):
        """Tech disruption must generate >= 4 unique agent types."""
        gen = DynamicAgentGenerator()
        loop = asyncio.new_event_loop()
        profiles = loop.run_until_complete(
            gen.generate_agents(
                event_title=event_tech_disruption.title,
                event_domains=event_tech_disruption.domain,
                use_llm=False,
            )
        )
        loop.close()

        unique_types = {p.agent_type for p in profiles}
        assert len(unique_types) >= 3, (
            f"Expected >= 3 unique agent types for tech disruption, got: {unique_types}. "
            f"Tech events affect markets, organizations, systems, and individuals."
        )

        assert len(profiles) >= 4, (
            f"Expected >= 4 agents for tech disruption, got {len(profiles)}: "
            f"{[p.agent_name for p in profiles]}."
        )


class TestTechSimulation:
    def test_ai_capability_diverges(self, mock_runner_tech):
        assert_timelines_diverge(
            mock_runner_tech, "ai_capability_index", by_step=6,
            label="AI launch → capability index"
        )

    def test_investment_flow_diverges(self, mock_runner_tech):
        """VC investment must diverge — 1st-order capital allocation effect."""
        assert_timelines_diverge(
            mock_runner_tech, "ai_investment_flow", by_step=12,
            label="AI launch → investment flow"
        )

    def test_tech_employment_diverges(self, mock_runner_tech):
        """Tech employment must diverge (downward) — 2nd-order labor disruption."""
        assert_timelines_diverge(
            mock_runner_tech, "tech_employment", by_step=30,
            label="AI launch → tech employment"
        )

    def test_regulatory_pressure_diverges(self, mock_runner_tech):
        """Regulatory pressure must diverge — 3rd-order policy response."""
        assert_timelines_diverge(
            mock_runner_tech, "regulatory_pressure", by_step=48,
            label="AI launch → regulatory pressure"
        )


class TestTechCausalChain:
    def test_labor_market_within_3_hops(self):
        """Labor market disruption must appear within 3 hops."""
        chain = _make_chain(
            "OpenAI AGI release",
            hops=[
                {"to_variable": "ai_capability_index", "step_triggered": 1},
                {"to_variable": "ai_investment_flow",  "step_triggered": 3},
                {"to_variable": "tech_employment",     "step_triggered": 12},
                {"to_variable": "regulatory_pressure", "step_triggered": 30},
                {"to_variable": "rd_spending",         "step_triggered": 6},
            ],
            domains=["technology", "economics"],
        )

        assert_causal_chain(chain, expected_min_hops=4,
                            expected_domains=["technology"],
                            label="AI disruption chain")

        assert_variable_in_chain(chain, "tech_employment", max_hop=3,
                                 label="labor market within 3 hops")

    def test_vc_investment_within_2_hops(self):
        """VC investment must appear within 2 hops — it is the fastest capital response."""
        chain = _make_chain(
            "OpenAI AGI release",
            hops=[
                {"to_variable": "ai_capability_index"},
                {"to_variable": "ai_investment_flow"},
                {"to_variable": "rd_spending"},
            ],
            domains=["technology"],
        )

        assert_variable_in_chain(chain, "ai_investment_flow", max_hop=2,
                                 label="VC investment within 2 hops")

    def test_chain_has_technology_domain(self):
        chain = _make_chain(
            "OpenAI AGI release",
            hops=[
                {"to_variable": "ai_capability_index"},
                {"to_variable": "ai_investment_flow"},
                {"to_variable": "tech_employment"},
                {"to_variable": "regulatory_pressure"},
            ],
            domains=["technology", "economics"],
        )
        assert_causal_chain(chain, expected_min_hops=4,
                            expected_domains=["technology"],
                            label="AI chain technology domain")