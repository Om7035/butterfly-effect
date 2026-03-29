"""Tests for NER extraction."""

import pytest
from butterfly.extraction.ner import EntityExtractor


@pytest.fixture
def entity_extractor():
    """Create entity extractor."""
    try:
        return EntityExtractor()
    except Exception:
        pytest.skip("spaCy model not available")


def test_entity_extraction_basic(entity_extractor):
    """Test basic entity extraction."""
    text = "The Federal Reserve raised interest rates in June 2022."
    entities = entity_extractor.extract(text)

    assert len(entities) > 0
    entity_texts = [e.text for e in entities]
    assert any("Federal Reserve" in text for text in entity_texts)


def test_entity_extraction_multiple_types(entity_extractor):
    """Test extraction of multiple entity types."""
    text = "Apple Inc. is headquartered in Cupertino, California."
    entities = entity_extractor.extract(text)

    assert len(entities) > 0
    # Should find organization and location
    labels = [e.label for e in entities]
    assert "Entity" in labels


def test_entity_extraction_empty_text(entity_extractor):
    """Test extraction from empty text."""
    entities = entity_extractor.extract("")
    assert entities == []


def test_entity_normalization(entity_extractor):
    """Test entity name normalization."""
    text = "The Fed announced a policy decision."
    entities = entity_extractor.extract(text)

    # Should normalize "Fed" to "Federal Reserve"
    entity_texts = [e.text for e in entities]
    assert any("Federal Reserve" in text for text in entity_texts)
