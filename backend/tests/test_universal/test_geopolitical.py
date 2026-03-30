"""
test_geopolitical.py — Scenario: Hamas attacks Israel, October 7 2023.

These tests prove the engine correctly models geopolitical conflict cascades:
  - Conflict → energy markets (oil price spike)
  - Conflict → humanitarian crisis (displacement)
  - Conflict → insurance repricing
  - Multi-hop: conflict → shipping → EU energy → inflation
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


# ── Domain classification ─────────────────────────────────────────────────────

class TestGeopoliticalDomainClassification:
    """The engine must correctly identify geopolitical + military domains."""

    def test_hamas_attack_classified_as_geopolitics(self):
        """'Hamas attacks Israel' must trigger geopolitics domain."""
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Hamas attacks Israel — October 7 2023")
        )
        loop.close()

        assert "geopolitics" in domains or "military" in domains, (
            f"Expected 'geopolitics' or 'military' in classified domains, got: {domains}. "
            f"The DomainClassifier keyword list is missing 'attack' or 'military' keywords "
            f"for the geopolitics/military domain."
        )

    def test_conflict_event_includes_energy_domain(self):
        """Middle East conflict must trigger energy domain (oil chokepoint)."""
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        domains = loop.run_until_complete(
            classifier.classify("Israel-Hamas war — oil price risk Strait of Hormuz")
        )
        loop.close()

        assert "energy" in domains, (
            f"Expected 'energy' in domains for oil-related conflict text, got: {domains}. "
            f"Add 'oil', 'strait', 'hormuz' to energy keywords in DomainClassifier."
        )


# ── Agent generation ──────────────────────────────────────────────────────────

class TestGeopoliticalAgentGeneration:
    """The right agents must be generated for a geopolitical conflict."""

    def test_geopolitical_templates_exist(self):
        """AGENT_TEMPLATES must have a 'geopolitics' key with >= 4 agents."""
        assert "geopolitics" in AGENT_TEMPLATES, (
            "AGENT_TEMPLATES missing 'geopolitics' key. "
            "Add geopolitics templates to dynamic_agents.py."
        )
        agents = AGENT_TEMPLATES["geopolitics"]
        assert len(agents) >= 4, (
            f"Expected >= 4 geopolitics agents, got {len(agents)}: "
            f"{[a.agent_name for a in agents]}. "
            f"Add more agent templates for geopolitical scenarios."
        )

    def test_energy_trader_in_geopolitics_pool(self):
        """Energy Trader must be in the geopolitics agent pool."""
        names = [a.agent_name for a in AGENT_TEMPLATES["geopolitics"]]
        assert any("energy" in n.lower() or "trader" in n.lower() for n in names), (
            f"No energy/trader agent in geopolitics pool: {names}. "
            f"Oil price is the primary 1st-order effect of Middle East conflict — "
            f"an Energy Trader agent is required."
        )

    def test_humanitarian_agent_in_geopolitics_pool(self):
        """A humanitarian agent (refugee/displacement) must exist."""
        names = [a.agent_name for a in AGENT_TEMPLATES["geopolitics"]]
        assert any("refugee" in n.lower() or "humanitarian" in n.lower() for n in names), (
            f"No humanitarian agent in geopolitics pool: {names}. "
            f"Displacement is a key 2nd-order effect of armed conflict."
        )

    def test_generate_agents_for_conflict(self, event_geopolitical):
        """DynamicAgentGenerator must produce >= 4 agents for geopolitical event."""
        gen = DynamicAgentGenerator()
        loop = asyncio.new_event_loop()
        profiles = loop.run_until_complete(
            gen.generate_agents(
                event_title=event_geopolitical.title,
                event_domains=event_geopolitical.domain,
                use_llm=False,
            )
        )
        loop.close()

        assert len(profiles) >= 4, (
            f"Expected >= 4 agents for geopolitical conflict, got {len(profiles)}: "
            f"{[p.agent_name for p in profiles]}. "
            f"Check domain mapping in DynamicAgentGenerator._map_domain()."
        )

        agent_types = {p.agent_type for p in profiles}
        assert len(agent_types) >= 2, (
            f"Expected >= 2 distinct agent types, got: {agent_types}. "
            f"A realistic conflict simulation needs markets, organizations, and individuals."
        )


# ── Simulation divergence ─────────────────────────────────────────────────────

class TestGeopoliticalSimulation:
    """Timeline A (conflict happens) must diverge from B (no conflict) on key variables."""

    def test_oil_price_diverges(self, mock_runner_geopolitical):
        """Oil price must diverge between timelines — this is the primary 1st-order effect."""
        assert_timelines_diverge(
            mock_runner_geopolitical, "oil_price", by_step=12,
            label="Hamas attack → oil price"
        )

    def test_conflict_intensity_diverges(self, mock_runner_geopolitical):
        """Conflict intensity must be the root diverging variable."""
        assert_timelines_diverge(
            mock_runner_geopolitical, "conflict_intensity", by_step=6,
            label="Hamas attack → conflict intensity"
        )

    def test_displacement_diverges(self, mock_runner_geopolitical):
        """Displacement count must diverge — humanitarian 2nd-order effect."""
        assert_timelines_diverge(
            mock_runner_geopolitical, "displacement_count", by_step=24,
            label="Hamas attack → displacement"
        )

    def test_insurance_premium_diverges(self, mock_runner_geopolitical):
        """Insurance premiums must spike — war risk repricing."""
        assert_timelines_diverge(
            mock_runner_geopolitical, "insurance_premium", by_step=12,
            label="Hamas attack → insurance premium"
        )

    def test_simulation_has_correct_agent_types(self, mock_runner_geopolitical):
        """Simulation must include energy, diplomatic, and humanitarian agents."""
        assert_agent_type_present(mock_runner_geopolitical, "market",
                                  label="geopolitical simulation")


# ── Causal chain extraction ───────────────────────────────────────────────────

class TestGeopoliticalCausalChain:
    """The extracted causal chain must meet depth and domain requirements."""

    def test_chain_reaches_energy_domain_within_3_hops(self):
        """Energy domain must appear within 3 hops of the root event."""
        chain = _make_chain(
            "Hamas attacks Israel",
            hops=[
                {"to_variable": "conflict_intensity", "step_triggered": 1},
                {"to_variable": "oil_price",          "step_triggered": 3},
                {"to_variable": "insurance_premium",  "step_triggered": 6},
                {"to_variable": "displacement_count", "step_triggered": 12},
                {"to_variable": "shipping_disruption","step_triggered": 18},
            ],
            domains=["geopolitics", "energy", "humanitarian"],
        )

        assert_causal_chain(chain, expected_min_hops=4,
                            expected_domains=["geopolitics", "energy"],
                            label="Hamas attack chain")

        assert_variable_in_chain(chain, "oil_price", max_hop=3,
                                 label="energy domain within 3 hops")

    def test_chain_reaches_humanitarian_domain(self):
        """Humanitarian domain (displacement) must appear in the chain."""
        chain = _make_chain(
            "Hamas attacks Israel",
            hops=[
                {"to_variable": "conflict_intensity", "step_triggered": 1},
                {"to_variable": "oil_price",          "step_triggered": 3},
                {"to_variable": "displacement_count", "step_triggered": 8},
                {"to_variable": "diplomatic_activity","step_triggered": 24},
            ],
            domains=["geopolitics", "energy", "humanitarian"],
        )

        assert_causal_chain(chain, expected_min_hops=4,
                            expected_domains=["humanitarian"],
                            label="Hamas attack humanitarian chain")

    def test_chain_depth_at_least_4_hops(self):
        """Total chain depth must be >= 4 hops to capture 3rd/4th order effects."""
        chain = _make_chain(
            "Hamas attacks Israel",
            hops=[
                {"to_variable": "conflict_intensity"},
                {"to_variable": "oil_price"},
                {"to_variable": "shipping_disruption"},
                {"to_variable": "insurance_premium"},
                {"to_variable": "displacement_count"},
            ],
            domains=["geopolitics", "energy", "humanitarian"],
        )

        assert chain.total_hops >= 4, (
            f"Chain depth {chain.total_hops} < 4. "
            f"A geopolitical conflict must produce at least 4 causal hops "
            f"(conflict → energy → logistics → humanitarian). "
            f"Increase simulation steps or lower agent trigger thresholds."
        )


# ── Log extractor integration ─────────────────────────────────────────────────

class TestGeopoliticalLogExtraction:
    """CausalLogExtractor must correctly process geopolitical simulation logs."""

    def test_extractor_produces_energy_domain(self):
        """Extractor must infer 'energy' domain from oil_price variable."""
        log = [
            {"agent_id": "a1", "agent_name": "Energy Trader", "timestep": 2,
             "variable_changed": "oil_price", "old_value": 80.0, "new_value": 92.0,
             "delta": 12.0, "trigger_fired": "conflict_intensity > 0.3"},
            {"agent_id": "a2", "agent_name": "Diplomat", "timestep": 5,
             "variable_changed": "diplomatic_activity", "old_value": 0.1, "new_value": 0.6,
             "delta": 0.5, "trigger_fired": "conflict_intensity > 0.6"},
        ]
        tl_a = {0: {"oil_price": 80.0, "diplomatic_activity": 0.1},
                6: {"oil_price": 92.0, "diplomatic_activity": 0.6},
                12: {"oil_price": 91.0, "diplomatic_activity": 0.65}}
        tl_b = {0: {"oil_price": 80.0, "diplomatic_activity": 0.1},
                6: {"oil_price": 80.5, "diplomatic_activity": 0.1},
                12: {"oil_price": 80.3, "diplomatic_activity": 0.1}}

        extractor = CausalLogExtractor()
        chain = extractor.extract(log, tl_a, tl_b, "Hamas attacks Israel", total_steps=12)

        assert "energy" in chain.domain_coverage, (
            f"Expected 'energy' in domain_coverage, got: {chain.domain_coverage}. "
            f"'oil_price' must be mapped to 'energy' in _VAR_DOMAIN_MAP."
        )

    def test_extractor_orders_hops_by_step(self):
        """Hops must be ordered by step_triggered (causal order)."""
        log = [
            {"agent_id": "a1", "agent_name": "Energy Trader", "timestep": 2,
             "variable_changed": "oil_price", "old_value": 80.0, "new_value": 92.0,
             "delta": 12.0, "trigger_fired": "conflict_intensity > 0.3"},
            {"agent_id": "a2", "agent_name": "Refugee Population", "timestep": 8,
             "variable_changed": "displacement_count", "old_value": 0.0, "new_value": 50000.0,
             "delta": 50000.0, "trigger_fired": "conflict_intensity > 0.5"},
        ]
        tl_a = {0: {"oil_price": 80.0, "displacement_count": 0.0},
                6: {"oil_price": 92.0, "displacement_count": 10000.0},
                12: {"oil_price": 91.0, "displacement_count": 50000.0}}
        tl_b = {0: {"oil_price": 80.0, "displacement_count": 0.0},
                6: {"oil_price": 80.5, "displacement_count": 0.0},
                12: {"oil_price": 80.3, "displacement_count": 0.0}}

        chain = CausalLogExtractor().extract(log, tl_a, tl_b, "Hamas attacks Israel", 12)

        if len(chain.chains) >= 2:
            steps = [h.step_triggered for h in chain.chains]
            assert steps == sorted(steps), (
                f"Hops not in causal order: {[(h.to_variable, h.step_triggered) for h in chain.chains]}. "
                f"CausalLogExtractor must sort hops by step_triggered."
            )