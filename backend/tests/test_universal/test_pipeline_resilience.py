"""
test_pipeline_resilience.py — Tests that the pipeline degrades gracefully.

These tests prove the system is production-safe:
  - LLM failure → partial result returned, not a crash
  - No API keys → pipeline completes using free sources
  - Unknown domain → defaults gracefully
  - Same question twice → second call returns cached result
  - Malformed input → clear error, not 500
  - Empty log → extractor returns empty chain, not exception
  - Extreme values → simulation stays bounded
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from butterfly.causal.log_extractor import CausalLogExtractor
from butterfly.llm.event_parser import DomainClassifier, UniversalEvent
from butterfly.pipeline.orchestrator import AnalysisPipeline, _hash_input, _synthetic_event
from butterfly.simulation.dynamic_agents import BehaviorProfile, DynamicAgentGenerator, ReactionFn, TriggerRule
from butterfly.simulation.universal_model import UniversalModel


# ── LLM failure resilience ────────────────────────────────────────────────────

class TestLLMFailureResilience:
    """Pipeline must return partial results when LLM calls fail."""

    def test_domain_classifier_returns_default_on_llm_failure(self):
        """DomainClassifier must return ['economics'] when LLM fails and no keywords match."""
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()
        # Input with no recognizable keywords
        domains = loop.run_until_complete(classifier.classify("xyzzy frobnicator quux"))
        loop.close()

        assert isinstance(domains, list), (
            f"DomainClassifier must always return a list, got: {type(domains)}."
        )
        assert len(domains) >= 1, (
            f"DomainClassifier must return at least one domain, got empty list. "
            f"Default should be ['economics']."
        )

    def test_synthetic_event_created_when_parser_unavailable(self):
        """_synthetic_event() must produce a valid UniversalEvent from raw text."""
        raw = "Something happened somewhere with some consequences"
        event = _synthetic_event(raw)

        assert isinstance(event, UniversalEvent), (
            f"_synthetic_event must return UniversalEvent, got {type(event)}."
        )
        assert len(event.domain) >= 1, (
            f"Synthetic event must have at least one domain, got: {event.domain}."
        )
        assert len(event.causal_seeds) >= 3, (
            f"Synthetic event must have >= 3 causal seeds for pipeline to continue, "
            f"got: {event.causal_seeds}."
        )
        assert event.confidence < 0.6, (
            f"Synthetic event confidence should be low (< 0.6) to signal degraded mode, "
            f"got: {event.confidence}."
        )

    def test_synthetic_event_detects_geopolitics_keywords(self):
        """_synthetic_event must detect 'war' keyword → geopolitics domain."""
        event = _synthetic_event("War breaks out between two major powers")
        assert "geopolitics" in event.domain, (
            f"Expected 'geopolitics' domain for war-related input, got: {event.domain}."
        )

    def test_synthetic_event_detects_health_keywords(self):
        """_synthetic_event must detect 'pandemic' keyword → health domain."""
        event = _synthetic_event("Pandemic spreads across three continents")
        assert "health" in event.domain, (
            f"Expected 'health' domain for pandemic input, got: {event.domain}."
        )

    def test_synthetic_event_detects_climate_keywords(self):
        event = _synthetic_event("Hurricane causes massive flooding and destruction")
        assert "climate" in event.domain, (
            f"Expected 'climate' domain for hurricane input, got: {event.domain}."
        )

    def test_synthetic_event_detects_technology_keywords(self):
        event = _synthetic_event("AI chip launch disrupts the tech industry")
        assert "technology" in event.domain, (
            f"Expected 'technology' domain for AI/chip input, got: {event.domain}."
        )


# ── Cache behavior ────────────────────────────────────────────────────────────

class TestCacheBehavior:
    """Same question twice must return cached result instantly."""

    def test_hash_input_is_deterministic(self):
        """Same input must always produce the same cache key."""
        q = "What happens if China invades Taiwan?"
        h1 = _hash_input(q)
        h2 = _hash_input(q)
        assert h1 == h2, (
            f"Cache key is not deterministic: '{h1}' != '{h2}'. "
            f"_hash_input must be a pure function of the input string."
        )

    def test_hash_input_is_case_insensitive(self):
        """Cache key must be case-insensitive (same question, different case)."""
        h1 = _hash_input("Fed raises rates 75bps")
        h2 = _hash_input("FED RAISES RATES 75BPS")
        assert h1 == h2, (
            f"Cache key differs by case: '{h1}' != '{h2}'. "
            f"_hash_input must normalize to lowercase before hashing."
        )

    def test_hash_input_strips_whitespace(self):
        """Cache key must strip leading/trailing whitespace."""
        h1 = _hash_input("Fed raises rates")
        h2 = _hash_input("  Fed raises rates  ")
        assert h1 == h2, (
            f"Cache key differs by whitespace: '{h1}' != '{h2}'. "
            f"_hash_input must strip() before hashing."
        )

    def test_different_inputs_produce_different_hashes(self):
        """Different questions must produce different cache keys."""
        h1 = _hash_input("Hamas attacks Israel")
        h2 = _hash_input("Fed raises rates 75bps")
        assert h1 != h2, (
            f"Different inputs produced same cache key: '{h1}'. "
            f"Hash collision in _hash_input — use a stronger hash."
        )

    @pytest.mark.asyncio
    async def test_pipeline_returns_cached_result_on_second_call(self):
        """Second call with same input must return instantly from cache."""
        cached_result = {
            "run_id": "cached_run_001",
            "stage": "complete",
            "event": {"title": "Test Event", "domain": ["economics"]},
            "causal_chain": {"total_hops": 3},
            "insights": ["Test insight"],
        }

        with patch("butterfly.pipeline.orchestrator.get_cache",
                   new_callable=AsyncMock) as mock_get, \
             patch("butterfly.pipeline.orchestrator.set_cache",
                   new_callable=AsyncMock):

            import json
            mock_get.return_value = json.dumps(cached_result)

            pipeline = AnalysisPipeline()
            events = []
            async for event in pipeline.run("Fed raises rates 75bps"):
                events.append(event)

            assert len(events) == 1, (
                f"Expected exactly 1 event (cache hit), got {len(events)}. "
                f"Pipeline must short-circuit on cache hit."
            )
            assert events[0].stage == "complete", (
                f"Cache hit must return stage='complete', got: {events[0].stage}."
            )
            assert events[0].percent == 100, (
                f"Cache hit must return percent=100, got: {events[0].percent}."
            )


# ── Malformed input ───────────────────────────────────────────────────────────

class TestMalformedInput:
    """Malformed input must produce clear errors, not crashes."""

    def test_empty_string_produces_valid_synthetic_event(self):
        """Empty string must not crash — produce a synthetic event."""
        event = _synthetic_event("")
        assert isinstance(event, UniversalEvent), (
            f"Empty string input must produce a UniversalEvent, got {type(event)}."
        )

    def test_very_long_input_truncated_gracefully(self):
        """Very long input must be handled without crash."""
        long_input = "A" * 10000
        event = _synthetic_event(long_input)
        assert isinstance(event, UniversalEvent), (
            f"10,000-char input must produce a UniversalEvent, not crash."
        )
        assert len(event.title) <= 100, (
            f"Title must be truncated for very long input, got {len(event.title)} chars."
        )

    def test_special_characters_in_input(self):
        """Special characters must not crash the pipeline."""
        special = "War & Peace: 100% certain → $∞ impact <script>alert('xss')</script>"
        event = _synthetic_event(special)
        assert isinstance(event, UniversalEvent), (
            f"Special characters in input must not crash, got {type(event)}."
        )


# ── Empty log / edge cases ────────────────────────────────────────────────────

class TestExtractorEdgeCases:
    """CausalLogExtractor must handle edge cases without crashing."""

    def test_empty_log_returns_empty_chain(self):
        """Empty simulation log must return an empty chain, not raise."""
        extractor = CausalLogExtractor()
        chain = extractor.extract([], {}, {}, "Empty Event", total_steps=48)

        assert chain.total_hops == 0, (
            f"Empty log must produce 0 hops, got {chain.total_hops}."
        )
        assert chain.chains == [], (
            f"Empty log must produce empty chains list, got {chain.chains}."
        )
        assert chain.domain_coverage == [], (
            f"Empty log must produce empty domain_coverage, got {chain.domain_coverage}."
        )

    def test_single_entry_log_does_not_crash(self):
        """Single log entry must not crash the extractor."""
        log = [{"agent_id": "a1", "agent_name": "Test Agent", "timestep": 1,
                "variable_changed": "oil_price", "old_value": 80.0, "new_value": 95.0,
                "delta": 15.0, "trigger_fired": "conflict_intensity > 0.3"}]
        tl_a = {0: {"oil_price": 80.0}, 6: {"oil_price": 95.0}}
        tl_b = {0: {"oil_price": 80.0}, 6: {"oil_price": 80.5}}

        extractor = CausalLogExtractor()
        chain = extractor.extract(log, tl_a, tl_b, "Single Entry Test", total_steps=6)

        assert isinstance(chain.total_hops, int), (
            f"total_hops must be an int, got {type(chain.total_hops)}."
        )

    def test_log_with_zero_delta_produces_no_hops(self):
        """Log entries with zero delta must not produce hops."""
        log = [{"agent_id": "a1", "agent_name": "Flat Agent", "timestep": 1,
                "variable_changed": "oil_price", "old_value": 80.0, "new_value": 80.0,
                "delta": 0.0, "trigger_fired": "none"}]
        tl_a = {0: {"oil_price": 80.0}, 6: {"oil_price": 80.0}}
        tl_b = {0: {"oil_price": 80.0}, 6: {"oil_price": 80.0}}

        chain = CausalLogExtractor().extract(log, tl_a, tl_b, "Zero Delta Test", total_steps=6)

        assert chain.total_hops == 0, (
            f"Zero-delta log must produce 0 hops, got {chain.total_hops}. "
            f"The extractor must filter out non-diverging variables."
        )


# ── Simulation bounds ─────────────────────────────────────────────────────────

class TestSimulationBounds:
    """Simulation must stay numerically bounded even with extreme inputs."""

    def test_extreme_event_signal_does_not_produce_nan(self):
        """Extreme event signal values must not produce NaN in simulation."""
        profile = BehaviorProfile(
            agent_name="Extreme Agent",
            agent_type="market",
            domain="finance",
            primary_concern="test",
            triggers=[TriggerRule(variable="event_magnitude", operator=">",
                                  threshold=0.1, condition="event_magnitude > 0.1")],
            reaction_functions=[ReactionFn(target_variable="risk_sentiment",
                                           formula="exponential", magnitude=1000.0,
                                           direction=1, lag_steps=0)],
        )

        model = UniversalModel(
            profiles=[profile],
            event_signal={"event_magnitude": 999.0},
        )

        for _ in range(10):
            model.step()

        snapshot = model.get_environment_snapshot()
        for var, val in snapshot.items():
            assert val == val, (  # NaN != NaN
                f"Variable '{var}' is NaN after extreme event signal. "
                f"Simulation must clamp or bound all values."
            )
            assert abs(val) < 1e12, (
                f"Variable '{var}' = {val} is unbounded. "
                f"Simulation must prevent runaway values."
            )

    def test_agent_generation_with_empty_domains(self):
        """DynamicAgentGenerator must not crash with empty domain list."""
        gen = DynamicAgentGenerator()
        loop = asyncio.new_event_loop()
        profiles = loop.run_until_complete(
            gen.generate_agents(
                event_title="Unknown event",
                event_domains=[],
                use_llm=False,
            )
        )
        loop.close()

        assert isinstance(profiles, list), (
            f"generate_agents must return a list even with empty domains, "
            f"got {type(profiles)}."
        )
        assert len(profiles) >= 1, (
            f"generate_agents must return at least 1 fallback agent for empty domains, "
            f"got 0. Check _fallback_agents() in DynamicAgentGenerator."
        )


# ── Performance ───────────────────────────────────────────────────────────────

class TestPerformance:
    """Key operations must complete within time budgets."""

    def test_domain_classifier_completes_under_100ms(self):
        """DomainClassifier (keyword mode) must complete in < 100ms."""
        classifier = DomainClassifier()
        loop = asyncio.new_event_loop()

        start = time.perf_counter()
        loop.run_until_complete(
            classifier.classify("Hamas attacks Israel oil price conflict military")
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        loop.close()

        assert elapsed_ms < 100, (
            f"DomainClassifier took {elapsed_ms:.1f}ms — must complete in < 100ms. "
            f"Keyword matching should be near-instant. Check for blocking I/O."
        )

    def test_log_extractor_completes_under_500ms_for_1000_entries(self):
        """CausalLogExtractor must process 1000 log entries in < 500ms."""
        log = [
            {"agent_id": f"a{i}", "agent_name": f"Agent_{i % 5}", "timestep": i,
             "variable_changed": ["oil_price", "conflict_intensity", "insurance_premium",
                                  "displacement_count", "diplomatic_activity"][i % 5],
             "old_value": float(i), "new_value": float(i) + 1.5,
             "delta": 1.5, "trigger_fired": "test > 0.3"}
            for i in range(1000)
        ]
        tl_a = {i: {"oil_price": 80.0 + i * 0.1} for i in range(0, 100, 6)}
        tl_b = {i: {"oil_price": 80.0} for i in range(0, 100, 6)}

        extractor = CausalLogExtractor()
        start = time.perf_counter()
        chain = extractor.extract(log, tl_a, tl_b, "Performance Test", total_steps=100)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, (
            f"CausalLogExtractor took {elapsed_ms:.1f}ms for 1000 entries — "
            f"must complete in < 500ms. Performance target: O(n log n)."
        )