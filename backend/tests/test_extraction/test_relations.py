"""Tests for relationship extraction."""

import pytest
from butterfly.extraction.relations import RelationExtractor
from butterfly.extraction.ner import EntityExtractor, ExtractedEntity


@pytest.fixture
def relation_extractor():
    """Create relation extractor."""
    return RelationExtractor()


@pytest.fixture
def entity_extractor():
    """Create entity extractor."""
    try:
        return EntityExtractor()
    except Exception:
        pytest.skip("spaCy model not available")


def test_causal_pattern_extraction(relation_extractor):
    """Test extraction of causal patterns."""
    text = "The Federal Reserve raised rates, which led to higher mortgage rates."

    # Create mock entities
    entities = [
        ExtractedEntity(
            text="Federal Reserve",
            label="Entity",
            start=4,
            end=20,
            confidence=0.95,
        ),
        ExtractedEntity(
            text="mortgage rates",
            label="Metric",
            start=70,
            end=84,
            confidence=0.85,
        ),
    ]

    relations = relation_extractor.extract_relations(text, entities)

    # Should find at least one causal relation
    assert len(relations) > 0
    assert any(r.relation_type in ["CAUSES", "TRIGGERS"] for r in relations)


def test_correlation_extraction(relation_extractor):
    """Test extraction of correlations."""
    text = "Stock prices increased and unemployment decreased."

    entities = [
        ExtractedEntity(
            text="Stock prices",
            label="Metric",
            start=0,
            end=12,
            confidence=0.85,
        ),
        ExtractedEntity(
            text="unemployment",
            label="Metric",
            start=30,
            end=42,
            confidence=0.85,
        ),
    ]

    relations = relation_extractor.extract_relations(text, entities)

    # Should find correlation
    assert len(relations) > 0


def test_no_relations_empty_entities(relation_extractor):
    """Test with no entities."""
    text = "Some random text."
    relations = relation_extractor.extract_relations(text, [])

    assert relations == []


def test_confidence_threshold(relation_extractor):
    """Test that low-confidence relations are filtered."""
    text = "Something happened and something else occurred."

    entities = [
        ExtractedEntity(
            text="Something",
            label="Entity",
            start=0,
            end=9,
            confidence=0.5,
        ),
        ExtractedEntity(
            text="something else",
            label="Entity",
            start=25,
            end=39,
            confidence=0.5,
        ),
    ]

    relations = relation_extractor.extract_relations(text, entities)

    # All relations should have confidence >= 0.4
    assert all(r.confidence >= 0.4 for r in relations)
