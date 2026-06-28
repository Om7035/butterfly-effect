"""Tests for evidence-based confidence updates."""

import pytest
from dataclasses import dataclass

from butterfly.causal.dag import DAGBuilder, EvidenceAudit


@dataclass
class MockEvidence:
    """Mock evidence object for testing."""
    source: str
    title: str
    content: str
    url: str = "http://example.com"
    relevance_score: float = 0.7


@pytest.fixture
def sample_graph():
    """Create a simple test graph."""
    return {
        "nodes": [
            {"id": "n0", "label": "Fed Rate Hike", "type": "Event", "hop": 0},
            {"id": "n1", "label": "Bond Yields Rise", "type": "Metric", "hop": 1},
            {"id": "n2", "label": "Mortgage Rates Increase", "type": "Metric", "hop": 2},
            {"id": "n3", "label": "Housing Starts Drop", "type": "Metric", "hop": 3},
        ],
        "edges": [
            {
                "source": "n0",
                "target": "n1",
                "confidence": 0.7,
                "latency_hours": 24,
                "relationship_type": "TRIGGERS",
            },
            {
                "source": "n1",
                "target": "n2",
                "confidence": 0.65,
                "latency_hours": 48,
                "relationship_type": "CAUSES",
            },
            {
                "source": "n2",
                "target": "n3",
                "confidence": 0.60,
                "latency_hours": 168,
                "relationship_type": "INFLUENCES",
            },
        ],
    }


def test_evidence_update_increases_confidence_on_corroboration(sample_graph):
    """Test that matching evidence increases confidence."""
    evidence = [
        MockEvidence(
            source="fred",
            title="Federal Reserve Announces Rate Increase",
            content="Bond yields rose sharply following the Fed rate hike decision. Treasury curves repriced upward.",
        ),
    ]

    builder = DAGBuilder()
    updated_graph, audit = builder.apply_evidence_updates(sample_graph, evidence)

    # Edge n0->n1 should be updated (mentions "rate", "bond yields", "fed")
    edges = {(e["source"], e["target"]): e for e in updated_graph["edges"]}
    n0_n1_edge = edges[("n0", "n1")]

    # Confidence should increase (base 0.7 * (1 + 0.15 * corr))
    assert n0_n1_edge["confidence"] > 0.7
    assert "fred" in n0_n1_edge.get("evidence_sources", [])
    assert n0_n1_edge.get("evidence_adjusted") is True


def test_evidence_update_clamps_to_bounds(sample_graph):
    """Test that confidence is clamped to [0.05, 0.95]."""
    # Create evidence that would push confidence very high
    evidence = [
        MockEvidence(
            source="fred",
            title="Bond yields rise",
            content="Bond yields bond yields bond yields bond yields bond yields bond yields",
        ),
    ] * 10

    builder = DAGBuilder()
    updated_graph, audit = builder.apply_evidence_updates(sample_graph, evidence)

    edges = {(e["source"], e["target"]): e for e in updated_graph["edges"]}
    for edge in edges.values():
        conf = edge["confidence"]
        assert 0.05 <= conf <= 0.95, f"Confidence {conf} outside bounds"


def test_evidence_audit_records_source_names(sample_graph):
    """Test that evidence audit records which sources updated each edge."""
    evidence = [
        MockEvidence(
            source="fred",
            title="Fed Rate",
            content="bond yields rise significantly",
        ),
        MockEvidence(
            source="wikipedia",
            title="Bond Market",
            content="bond yields mortgage rates",
        ),
    ]

    builder = DAGBuilder()
    updated_graph, audit = builder.apply_evidence_updates(sample_graph, evidence)

    audit_dict = audit.model_dump()
    # Should have at least one edge updated
    assert len(audit_dict) > 0
    for edge_key, details in audit_dict.items():
        assert "sources" in details
        assert "confidence_delta" in details
        assert "corroboration_count" in details


def test_evidence_update_handles_empty_evidence(sample_graph):
    """Test that empty evidence list returns unchanged graph."""
    builder = DAGBuilder()
    updated_graph, audit = builder.apply_evidence_updates(sample_graph, [])

    # Graph should be unchanged
    assert updated_graph["nodes"] == sample_graph["nodes"]
    # All edges should have evidence_sources set (even if empty)
    for edge in updated_graph["edges"]:
        assert "evidence_sources" in edge
        assert edge.get("evidence_adjusted") is False


def test_evidence_update_multiple_sources(sample_graph):
    """Test that matching evidence from multiple sources is recorded."""
    evidence = [
        MockEvidence(
            source="fred",
            title="Fed Rate Decision",
            content="bond yields rise treasury market",
        ),
        MockEvidence(
            source="gdelt",
            title="Market Report",
            content="fed decision bond yields increase",
        ),
        MockEvidence(
            source="wikipedia",
            title="Interest Rates",
            content="bond yields mortgage rates housing",
        ),
    ]

    builder = DAGBuilder()
    updated_graph, audit = builder.apply_evidence_updates(sample_graph, evidence)

    edges = {(e["source"], e["target"]): e for e in updated_graph["edges"]}
    n0_n1_edge = edges[("n0", "n1")]

    # Should record multiple sources
    sources = n0_n1_edge.get("evidence_sources", [])
    assert len(sources) >= 2, f"Expected multiple sources, got {sources}"


def test_evidence_audit_structure():
    """Test EvidenceAudit model_dump format."""
    audit = EvidenceAudit()
    audit.updates[("n1", "n2")] = {
        "sources": ["fred", "gdelt"],
        "delta": 0.08,
        "corr": 2,
        "contra": 0,
    }

    audit_dict = audit.model_dump()
    assert "('n1', 'n2')" in audit_dict
    assert audit_dict["('n1', 'n2')"]["sources"] == ["fred", "gdelt"]
    assert audit_dict["('n1', 'n2')"]["confidence_delta"] == 0.08
