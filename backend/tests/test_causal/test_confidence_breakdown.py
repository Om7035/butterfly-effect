"""Tests for confidence breakdown and explainability."""

import pytest
from butterfly.causal.log_extractor import CausalLogExtractor, ConfidenceBreakdown


@pytest.fixture
def extractor():
    return CausalLogExtractor()


def test_confidence_breakdown_components_sum_to_score(extractor):
    """Test that components contribute to final score."""
    edge_data = {
        "evidence_sources": [],
        "evidence_adjusted": False,
    }
    breakdown = extractor._generate_confidence_breakdown(
        base_confidence=0.7,
        cci_score=0.6,
        hop_count=2,
        edge_data=edge_data,
        nodes=[],
    )

    # Score should be weighted combination of components
    expected_score = (
        0.4 * breakdown.components["simulation_consistency"]
        + 0.4 * breakdown.components["effect_magnitude"]
        + 0.2 * breakdown.components["persistence"]
    )
    assert abs(breakdown.score - expected_score) < 0.01

    # All components should be in [0, 1]
    for comp_name, comp_val in breakdown.components.items():
        assert 0.0 <= comp_val <= 1.0, f"{comp_name} out of bounds: {comp_val}"


def test_confidence_breakdown_with_evidence(extractor):
    """Test that evidence adjustment is recorded in breakdown."""
    edge_data = {
        "evidence_sources": ["fred", "gdelt"],
        "evidence_adjusted": True,
    }
    breakdown = extractor._generate_confidence_breakdown(
        base_confidence=0.75,
        cci_score=0.7,
        hop_count=2,
        edge_data=edge_data,
        nodes=[],
    )

    assert breakdown.evidence_adjusted is True
    assert "fred" in breakdown.evidence_sources
    assert "gdelt" in breakdown.evidence_sources


def test_confidence_breakdown_identifies_primary_driver(extractor):
    """Test that primary_driver is correctly identified."""
    edge_data = {
        "evidence_sources": [],
        "evidence_adjusted": False,
    }
    breakdown = extractor._generate_confidence_breakdown(
        base_confidence=0.5,
        cci_score=0.8,
        hop_count=2,
        edge_data=edge_data,
        nodes=[],
    )

    # With high cci_score, simulation_consistency should be primary driver
    assert breakdown.primary_driver in breakdown.components
    assert breakdown.components[breakdown.primary_driver] == max(breakdown.components.values())


def test_plain_english_high_confidence_simulation_driven(extractor):
    """Test plain English template for high confidence with simulation driver."""
    edge_data = {
        "evidence_sources": [],
        "evidence_adjusted": False,
    }
    breakdown = extractor._generate_confidence_breakdown(
        base_confidence=0.8,
        cci_score=0.75,
        hop_count=1,
        edge_data=edge_data,
        nodes=[],
    )

    plain_english = breakdown.plain_english
    assert isinstance(plain_english, str)
    assert len(plain_english) > 10
    assert "simulation" in plain_english.lower() or "consistency" in plain_english.lower()


def test_plain_english_evidence_supported(extractor):
    """Test plain English template for evidence-supported finding."""
    edge_data = {
        "evidence_sources": ["fred", "wikipedia"],
        "evidence_adjusted": True,
    }
    breakdown = extractor._generate_confidence_breakdown(
        base_confidence=0.75,
        cci_score=0.7,
        hop_count=2,
        edge_data=edge_data,
        nodes=[],
    )

    plain_english = breakdown.plain_english
    # Should mention sources or evidence
    assert "source" in plain_english.lower() or "support" in plain_english.lower() or "corroborate" in plain_english.lower()


def test_plain_english_low_confidence_deep_chain(extractor):
    """Test plain English template for deep chain with lower confidence."""
    edge_data = {
        "evidence_sources": [],
        "evidence_adjusted": False,
    }
    breakdown = extractor._generate_confidence_breakdown(
        base_confidence=0.4,
        cci_score=0.3,
        hop_count=4,
        edge_data=edge_data,
        nodes=[],
    )

    plain_english = breakdown.plain_english
    # Should acknowledge the deep chain
    assert "chain" in plain_english.lower() or "hop" in plain_english.lower() or "uncertainty" in plain_english.lower()


def test_confidence_breakdown_model_dump(extractor):
    """Test that confidence breakdown serializes correctly."""
    edge_data = {
        "evidence_sources": ["fred"],
        "evidence_adjusted": True,
    }
    breakdown = extractor._generate_confidence_breakdown(
        base_confidence=0.7,
        cci_score=0.6,
        hop_count=2,
        edge_data=edge_data,
        nodes=[],
    )

    dumped = breakdown.model_dump()
    assert isinstance(dumped, dict)
    assert "score" in dumped
    assert "components" in dumped
    assert "evidence_adjusted" in dumped
    assert "evidence_sources" in dumped
    assert "primary_driver" in dumped
    assert "plain_english" in dumped

    # All numeric values should be rounded to 3 decimals
    assert isinstance(dumped["score"], float)
    assert 0.05 <= dumped["score"] <= 0.95
