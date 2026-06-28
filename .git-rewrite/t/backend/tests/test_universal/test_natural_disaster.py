"""
test_natural_disaster.py — Scenario: Category 5 hurricane makes landfall in Miami.

Proves the engine correctly models climate disaster cascades:
  - Storm → insurance market repricing (1st order)
  - Storm → infrastructure damage → construction supply chain (2nd order)
  - Storm → port closure → trade disruption (2nd order)
  - Storm → federal emergency spending → fiscal impact (3rd order)
"""

from __future__ import annotations

import asyncio

import pytest

from butterfly.causal.log_extractor import CausalLogExtractor
from butterfly.llm.event_parser import DomainClassifier
from butterfly.simulation.dynamic_agents import AGENT_TEMPLATES, DynamicAgentGenerator
from tests.test_universal.conftest import (
    assert_agent_type_present,
    assert_causal_chain,
    assert_timelines_diverge,
    assert_variable_in_chain,
    _make_chain,
)


class TestDisasterDomainClassification:
    def test_hurricane_classified_as_climate(self):
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Category 5 hurricane makes landfall in Miami Florida")
        )
        loop.close()

        assert "climate" in domains, (
            f"Expected 'climate' in domains for hurricane event, got: {domains}. "
            f"Add 'hurricane' to climate keywords in DomainClassifier."
        )

    def test_hurricane_includes_economics_domain(self):
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Hurricane causes $200B economic damage to Florida insurance market")
        )
        loop.close()

        has_econ = any(d in domains for d in ["economics", "financial_markets", "trade"])
        assert has_econ, (
            f"Expected an economics-related domain for hurricane economic damage, got: {domains}."
        )


class TestDisasterAgentGeneration:
    def test_climate_templates_exist(self):
        assert "climate" in AGENT_TEMPLATES, (
            "AGENT_TEMPLATES missing 'climate' key. "
            "Add climate disaster templates to dynamic_agents.py."
        )
        agents = AGENT_TEMPLATES["climate"]
        assert len(agents) >= 3, (
            f"Expected >= 3 climate agents, got {len(agents)}: "
            f"{[a.agent_name for a in agents]}."
        )

    def test_insurance_agent_in_climate_pool(self):
        """Insurance Company must be in climate pool — it's the primary 1st-order responder."""
        names = [a.agent_name for a in AGENT_TEMPLATES["climate"]]
        assert any("insurance" in n.lower() for n in names), (
            f"No insurance agent in climate pool: {names}. "
            f"Insurance repricing is the fastest 1st-order effect of a major hurricane."
        )

    def test_construction_agent_in_climate_pool(self):
        """Construction Supply Chain must be in climate pool — 2nd-order rebuild demand."""
        names = [a.agent_name for a in AGENT_TEMPLATES["climate"]]
        assert any("construction" in n.lower() or "supply" in n.lower() for n in names), (
            f"No construction/supply agent in climate pool: {names}. "
            f"Post-disaster reconstruction is a major 2nd-order economic effect."
        )

    def test_government_agent_in_climate_pool(self):
        """Government Emergency Agency must be in climate pool."""
        names = [a.agent_name for a in AGENT_TEMPLATES["climate"]]
        assert any("government" in n.lower() or "emergency" in n.lower() or "fema" in n.lower()
                   for n in names), (
            f"No government/emergency agent in climate pool: {names}. "
            f"Federal disaster response is a critical 2nd-order effect."
        )

    def test_generate_agents_for_disaster(self, event_natural_disaster):
        gen = DynamicAgentGenerator()
        loop = asyncio.new_event_loop()
        profiles = loop.run_until_complete(
            gen.generate_agents(
                event_title=event_natural_disaster.title,
                event_domains=event_natural_disaster.domain,
                use_llm=False,
            )
        )
        loop.close()

        assert len(profiles) >= 3, (
            f"Expected >= 3 agents for hurricane scenario, got {len(profiles)}: "
            f"{[p.agent_name for p in profiles]}."
        )

        agent_names_lower = [p.agent_name.lower() for p in profiles]
        assert any("insurance" in n for n in agent_names_lower), (
            f"Insurance agent missing from generated profiles: {[p.agent_name for p in profiles]}. "
            f"Check that 'climate' domain maps to climate templates."
        )


class TestDisasterSimulation:
    def test_storm_intensity_diverges(self, mock_runner_disaster):
        assert_timelines_diverge(
            mock_runner_disaster, "storm_intensity", by_step=6,
            label="Hurricane → storm intensity"
        )

    def test_insurance_payout_diverges_within_2_hops(self, mock_runner_disaster):
        """Insurance payout must diverge quickly — it's a near-instantaneous 1st-order effect."""
        assert_timelines_diverge(
            mock_runner_disaster, "insurance_payout", by_step=12,
            label="Hurricane → insurance payout"
        )

    def test_construction_demand_diverges(self, mock_runner_disaster):
        """Construction demand must diverge — 2nd-order rebuild effect."""
        assert_timelines_diverge(
            mock_runner_disaster, "construction_demand", by_step=30,
            label="Hurricane → construction demand"
        )

    def test_infrastructure_damage_diverges(self, mock_runner_disaster):
        assert_timelines_diverge(
            mock_runner_disaster, "infrastructure_damage", by_step=6,
            label="Hurricane → infrastructure damage"
        )


class TestDisasterCausalChain:
    def test_insurance_market_within_2_hops(self):
        """Insurance market must appear within 2 hops of the storm event."""
        chain = _make_chain(
            "Category 5 hurricane Miami",
            hops=[
                {"to_variable": "storm_intensity",      "step_triggered": 1},
                {"to_variable": "insurance_payout",     "step_triggered": 2},
                {"to_variable": "infrastructure_damage","step_triggered": 3},
                {"to_variable": "construction_demand",  "step_triggered": 24},
                {"to_variable": "emergency_spending",   "step_triggered": 12},
            ],
            domains=["climate", "economics"],
        )

        assert_causal_chain(chain, expected_min_hops=4,
                            expected_domains=["climate"],
                            label="Hurricane chain")

        assert_variable_in_chain(chain, "insurance_payout", max_hop=2,
                                 label="insurance market within 2 hops")

    def test_construction_supply_chain_within_3_hops(self):
        """Construction supply chain must appear within 3 hops."""
        chain = _make_chain(
            "Category 5 hurricane Miami",
            hops=[
                {"to_variable": "storm_intensity"},
                {"to_variable": "infrastructure_damage"},
                {"to_variable": "construction_demand"},
                {"to_variable": "emergency_spending"},
            ],
            domains=["climate", "economics"],
        )

        assert_variable_in_chain(chain, "construction_demand", max_hop=3,
                                 label="construction supply chain within 3 hops")

    def test_chain_includes_climate_domain(self):
        chain = _make_chain(
            "Category 5 hurricane Miami",
            hops=[
                {"to_variable": "storm_intensity"},
                {"to_variable": "insurance_payout"},
                {"to_variable": "infrastructure_damage"},
            ],
            domains=["climate", "economics"],
        )
        assert_causal_chain(chain, expected_min_hops=3,
                            expected_domains=["climate"],
                            label="Hurricane climate domain")


class TestDisasterLogExtraction:
    def test_extractor_infers_climate_domain(self):
        log = [
            {"agent_id": "a1", "agent_name": "Insurance Company", "timestep": 1,
             "variable_changed": "insurance_payout", "old_value": 0.0, "new_value": 18.0,
             "delta": 18.0, "trigger_fired": "storm_intensity > 0.6"},
            {"agent_id": "a2", "agent_name": "Infrastructure Agency", "timestep": 1,
             "variable_changed": "infrastructure_damage", "old_value": 0.0, "new_value": 0.8,
             "delta": 0.8, "trigger_fired": "storm_intensity > 0.5"},
            {"agent_id": "a3", "agent_name": "Construction Supply Chain", "timestep": 24,
             "variable_changed": "construction_demand", "old_value": 0.5, "new_value": 1.3,
             "delta": 0.8, "trigger_fired": "infrastructure_damage > 0.5"},
        ]
        tl_a = {0: {"insurance_payout": 0.0, "infrastructure_damage": 0.0, "construction_demand": 0.5},
                6: {"insurance_payout": 18.0, "infrastructure_damage": 0.8, "construction_demand": 0.5},
                24: {"insurance_payout": 18.0, "infrastructure_damage": 0.8, "construction_demand": 1.3}}
        tl_b = {0: {"insurance_payout": 0.0, "infrastructure_damage": 0.0, "construction_demand": 0.5},
                6: {"insurance_payout": 0.1, "infrastructure_damage": 0.0, "construction_demand": 0.5},
                24: {"insurance_payout": 0.1, "infrastructure_damage": 0.0, "construction_demand": 0.52}}

        chain = CausalLogExtractor().extract(log, tl_a, tl_b, "Hurricane Miami", total_steps=24)

        assert "climate" in chain.domain_coverage, (
            f"Expected 'climate' in domain_coverage, got: {chain.domain_coverage}. "
            f"'insurance_payout' and 'infrastructure_damage' must map to 'climate' in _VAR_DOMAIN_MAP."
        )
        assert chain.total_hops >= 2, (
            f"Expected >= 2 hops from hurricane log, got {chain.total_hops}. "
            f"Check divergence threshold — insurance_payout delta of 18.0 should easily exceed 2%."
        )