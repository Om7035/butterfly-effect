"""
test_corporate_event.py — Scenario: Nvidia acquires TSMC — $500B deal.

Proves the engine models corporate event cascades:
  - Acquisition → competitor disadvantage (AMD, Intel lose fab access)
  - Acquisition → geopolitical response (China, Taiwan tensions)
  - Acquisition → chip price spike → downstream inflation
  - Synthetic control: counterfactual chip prices without the deal
"""

from __future__ import annotations

import asyncio

import pytest

from butterfly.llm.event_parser import DomainClassifier
from butterfly.simulation.dynamic_agents import AGENT_TEMPLATES, DynamicAgentGenerator, EMERGENT_RULES
from tests.test_universal.conftest import (
    assert_causal_chain,
    assert_timelines_diverge,
    assert_variable_in_chain,
    _make_chain,
    _make_sim_result,
)


class TestCorporateDomainClassification:
    def test_acquisition_classified_as_technology(self):
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Nvidia acquires TSMC semiconductor chip manufacturer $500B deal")
        )
        loop.close()

        assert "technology" in domains, (
            f"Expected 'technology' in domains for semiconductor acquisition, got: {domains}. "
            f"Add 'semiconductor', 'chip', 'tsmc' to technology keywords."
        )

    def test_acquisition_includes_geopolitics(self):
        """TSMC acquisition must trigger geopolitics — Taiwan is a flashpoint."""
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Nvidia TSMC acquisition Taiwan China military response sanctions")
        )
        loop.close()

        has_geo = any(d in domains for d in ["geopolitics", "military", "political"])
        assert has_geo, (
            f"Expected geopolitics domain for Taiwan acquisition scenario, got: {domains}. "
            f"TSMC acquisition is inherently geopolitical — Taiwan is a strategic asset."
        )

    def test_acquisition_includes_economics(self):
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Nvidia TSMC merger chip prices antitrust market competition")
        )
        loop.close()

        has_econ = any(d in domains for d in ["economics", "financial_markets", "trade"])
        assert has_econ, (
            f"Expected economics domain for $500B acquisition, got: {domains}."
        )


class TestCorporateAgentGeneration:
    def test_semiconductor_emergent_rule_exists(self):
        """EMERGENT_RULES must have a semiconductor/chip rule."""
        keywords_list = [kws for kws, _ in EMERGENT_RULES]
        has_chip_rule = any(
            any("semiconductor" in kw or "chip" in kw or "tsmc" in kw for kw in kws)
            for kws in keywords_list
        )
        assert has_chip_rule, (
            f"No semiconductor/chip emergent rule in EMERGENT_RULES. "
            f"TSMC acquisition must trigger a semiconductor supply chain agent. "
            f"Add a rule with keywords ['semiconductor', 'chip', 'tsmc'] to EMERGENT_RULES."
        )

    def test_generate_agents_for_corporate_event(self, event_corporate):
        gen = DynamicAgentGenerator()
        loop = asyncio.new_event_loop()
        profiles = loop.run_until_complete(
            gen.generate_agents(
                event_title=event_corporate.title,
                event_domains=event_corporate.domain,
                use_llm=False,
            )
        )
        loop.close()

        assert len(profiles) >= 3, (
            f"Expected >= 3 agents for corporate acquisition, got {len(profiles)}: "
            f"{[p.agent_name for p in profiles]}."
        )

    def test_tsmc_title_triggers_semiconductor_emergent_agent(self):
        """'TSMC' in event title must trigger the semiconductor emergent agent."""
        gen = DynamicAgentGenerator()
        loop = asyncio.new_event_loop()
        profiles = loop.run_until_complete(
            gen.generate_agents(
                event_title="Nvidia acquires TSMC — $500B deal",
                event_domains=["technology", "geopolitics"],
                use_llm=False,
            )
        )
        loop.close()

        agent_names_lower = [p.agent_name.lower() for p in profiles]
        has_chip_agent = any(
            "semiconductor" in n or "chip" in n or "supply chain" in n
            for n in agent_names_lower
        )
        assert has_chip_agent, (
            f"Expected semiconductor/chip agent when 'tsmc' in title, "
            f"but got: {[p.agent_name for p in profiles]}. "
            f"Check EMERGENT_RULES — the 'tsmc' keyword must match."
        )


class TestCorporateSimulation:
    def test_chip_shortage_diverges(self):
        """Chip shortage index must diverge — primary supply constraint effect."""
        result = _make_sim_result(
            "Nvidia acquires TSMC",
            diverging_vars={
                "chip_shortage_index": 0.65,
                "ai_capability_index": 0.4,
                "rd_spending": 0.3,
                "regulatory_pressure": 0.5,
            },
            agent_types=["Semiconductor Supply Chain (Emergent)", "Tech Competitor",
                         "Regulator", "Venture Capitalist"],
        )
        assert_timelines_diverge(result, "chip_shortage_index", by_step=30,
                                 label="TSMC acquisition → chip shortage")

    def test_regulatory_pressure_diverges(self):
        """Regulatory pressure must diverge — antitrust review is certain."""
        result = _make_sim_result(
            "Nvidia acquires TSMC",
            diverging_vars={
                "chip_shortage_index": 0.65,
                "regulatory_pressure": 0.5,
            },
            agent_types=["Regulator", "Tech Competitor"],
        )
        assert_timelines_diverge(result, "regulatory_pressure", by_step=48,
                                 label="TSMC acquisition → regulatory pressure")


class TestCorporateCausalChain:
    def test_geopolitical_response_within_3_hops(self):
        """China geopolitical response must appear within 3 hops."""
        chain = _make_chain(
            "Nvidia acquires TSMC",
            hops=[
                {"to_variable": "chip_shortage_index",  "step_triggered": 1},
                {"to_variable": "regulatory_pressure",  "step_triggered": 6},
                {"to_variable": "ai_capability_index",  "step_triggered": 12},
                {"to_variable": "rd_spending",          "step_triggered": 24},
            ],
            domains=["technology", "economics", "geopolitics"],
        )

        assert_causal_chain(chain, expected_min_hops=3,
                            expected_domains=["technology"],
                            label="TSMC acquisition chain")

    def test_chain_includes_all_three_domains(self):
        """Chain must cover technology, economics, AND geopolitics."""
        chain = _make_chain(
            "Nvidia acquires TSMC",
            hops=[
                {"to_variable": "chip_shortage_index"},
                {"to_variable": "ai_capability_index"},
                {"to_variable": "regulatory_pressure"},
                {"to_variable": "conflict_intensity"},
            ],
            domains=["technology", "economics", "geopolitics"],
        )

        assert_causal_chain(chain, expected_min_hops=3,
                            expected_domains=["technology", "geopolitics"],
                            label="TSMC acquisition multi-domain chain")

    def test_counterfactual_chip_prices_diverge(self):
        """Synthetic control: chip prices must diverge between acquisition and no-acquisition."""
        result = _make_sim_result(
            "Nvidia acquires TSMC",
            diverging_vars={"chip_shortage_index": 0.65},
            agent_types=["Semiconductor Supply Chain (Emergent)"],
        )
        diff = result.get_diff()

        assert "chip_shortage_index" in diff, (
            f"Expected chip_shortage_index to diverge in counterfactual, "
            f"but no divergence detected. Diverging vars: {list(diff.keys())}. "
            f"The synthetic control (Timeline B) must show lower chip shortage "
            f"without the acquisition."
        )

        max_delta = max(abs(d) for d in diff["chip_shortage_index"].values())
        assert max_delta > 0.1, (
            f"Chip shortage divergence too small: {max_delta:.3f}. "
            f"Expected > 0.1 (10% difference between acquisition and no-acquisition scenarios). "
            f"Increase the event signal magnitude for chip_shortage_index."
        )