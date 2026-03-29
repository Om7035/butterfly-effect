"""Named Entity Recognition (NER) using spaCy."""

from dataclasses import dataclass
from typing import List, Optional
from loguru import logger
import spacy
from spacy.language import Language

from butterfly.extraction.normalizer import normalize_entity_name


@dataclass
class ExtractedEntity:
    """Extracted entity from text."""

    text: str
    label: str  # Our normalized label: Entity, Metric, Policy, Event
    start: int
    end: int
    confidence: float


class EntityExtractor:
    """Extract entities from text using spaCy."""

    # Mapping from spaCy labels to our node labels
    LABEL_MAPPING = {
        "ORG": "Entity",
        "GPE": "Entity",
        "PERSON": "Entity",
        "MONEY": "Metric",
        "PERCENT": "Metric",
        "LAW": "Policy",
        "EVENT": "Event",
    }

    def __init__(self):
        """Initialize entity extractor."""
        try:
            # Try to load transformer model (most accurate)
            self.nlp: Language = spacy.load("en_core_web_trf")
            logger.info("Loaded spaCy model: en_core_web_trf")
        except OSError:
            # Fallback to smaller model
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy model: en_core_web_sm (fallback)")
            except OSError:
                logger.error("No spaCy model found. Install with: python -m spacy download en_core_web_sm")
                raise

    def extract(self, text: str) -> List[ExtractedEntity]:
        """Extract entities from text.

        Args:
            text: Input text to extract entities from

        Returns:
            List of extracted entities
        """
        if not text or not text.strip():
            return []

        try:
            doc = self.nlp(text)
            entities = []

            for ent in doc.ents:
                # Map spaCy label to our label
                our_label = self.LABEL_MAPPING.get(ent.label_, "Entity")

                # Normalize entity text
                normalized_text = normalize_entity_name(ent.text)

                # Get confidence (spaCy doesn't provide per-entity confidence,
                # so we use a heuristic based on entity type)
                confidence = self._get_confidence(ent.label_)

                extracted = ExtractedEntity(
                    text=normalized_text,
                    label=our_label,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=confidence,
                )
                entities.append(extracted)

            # Deduplicate by text (keep highest confidence)
            unique_entities = {}
            for entity in entities:
                key = (entity.text.lower(), entity.label)
                if key not in unique_entities or entity.confidence > unique_entities[key].confidence:
                    unique_entities[key] = entity

            return list(unique_entities.values())

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    @staticmethod
    def _get_confidence(spacy_label: str) -> float:
        """Get confidence score for entity type.

        Args:
            spacy_label: spaCy entity label

        Returns:
            Confidence score (0.0-1.0)
        """
        # Higher confidence for more reliable entity types
        confidence_map = {
            "ORG": 0.95,
            "GPE": 0.95,
            "PERSON": 0.90,
            "MONEY": 0.85,
            "PERCENT": 0.85,
            "LAW": 0.80,
            "EVENT": 0.75,
        }
        return confidence_map.get(spacy_label, 0.70)
