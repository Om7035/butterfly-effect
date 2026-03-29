"""Relationship extraction from text."""

from dataclasses import dataclass
from typing import List, Optional
from loguru import logger
import re
import spacy
from spacy.language import Language

from butterfly.extraction.ner import ExtractedEntity


@dataclass
class ExtractedRelation:
    """Extracted relationship between entities."""

    source_entity: str
    target_entity: str
    relation_type: str  # CAUSES, TRIGGERS, INFLUENCES, CORRELATES_WITH
    confidence: float
    evidence_text: str


class RelationExtractor:
    """Extract relationships between entities from text."""

    # Causal language patterns
    CAUSAL_PATTERNS = [
        (r"\b(\w+)\s+caused\s+(\w+)\b", "CAUSES", 0.95),
        (r"\b(\w+)\s+led\s+to\s+(\w+)\b", "CAUSES", 0.90),
        (r"\b(\w+)\s+resulted\s+in\s+(\w+)\b", "CAUSES", 0.90),
        (r"\b(\w+)\s+triggered\s+(\w+)\b", "TRIGGERS", 0.95),
        (r"\b(\w+)\s+drove\s+(\w+)\b", "INFLUENCES", 0.85),
        (r"due\s+to\s+(\w+),\s+(\w+)", "CAUSES", 0.85),
        (r"following\s+(\w+),\s+(\w+)", "CAUSES", 0.80),
        (r"\b(\w+)\s+pushed\s+(\w+)\b", "INFLUENCES", 0.80),
        (r"\b(\w+)\s+raised\s+(\w+)\b", "INFLUENCES", 0.80),
        (r"\b(\w+)\s+lowered\s+(\w+)\b", "INFLUENCES", 0.80),
    ]

    def __init__(self):
        """Initialize relation extractor."""
        try:
            self.nlp: Language = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found for relation extraction")
            self.nlp = None

    def extract_relations(
        self, text: str, entities: List[ExtractedEntity]
    ) -> List[ExtractedRelation]:
        """Extract relationships between entities.

        Args:
            text: Input text
            entities: List of extracted entities

        Returns:
            List of extracted relationships
        """
        if not text or not entities:
            return []

        relations = []

        # Strategy A: Pattern matching
        relations.extend(self._extract_by_patterns(text, entities))

        # Strategy B: Co-occurrence + proximity
        relations.extend(self._extract_by_proximity(text, entities))

        # Filter by confidence threshold
        relations = [r for r in relations if r.confidence >= 0.4]

        # Sort by confidence
        relations.sort(key=lambda r: r.confidence, reverse=True)

        return relations

    def _extract_by_patterns(
        self, text: str, entities: List[ExtractedEntity]
    ) -> List[ExtractedRelation]:
        """Extract relationships using causal language patterns.

        Args:
            text: Input text
            entities: List of extracted entities

        Returns:
            List of extracted relationships
        """
        relations = []

        for pattern, rel_type, base_confidence in self.CAUSAL_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    source = match.group(1)
                    target = match.group(2)

                    # Find matching entities
                    source_entity = self._find_entity(source, entities)
                    target_entity = self._find_entity(target, entities)

                    if source_entity and target_entity:
                        relation = ExtractedRelation(
                            source_entity=source_entity.text,
                            target_entity=target_entity.text,
                            relation_type=rel_type,
                            confidence=base_confidence,
                            evidence_text=match.group(0),
                        )
                        relations.append(relation)
                except Exception as e:
                    logger.debug(f"Pattern matching error: {e}")

        return relations

    def _extract_by_proximity(
        self, text: str, entities: List[ExtractedEntity]
    ) -> List[ExtractedRelation]:
        """Extract relationships by entity co-occurrence and proximity.

        Args:
            text: Input text
            entities: List of extracted entities

        Returns:
            List of extracted relationships
        """
        relations = []

        # Look for directional verbs
        directional_verbs = [
            "increase",
            "decrease",
            "rise",
            "fall",
            "grow",
            "shrink",
            "expand",
            "contract",
            "improve",
            "worsen",
        ]

        for i, entity1 in enumerate(entities):
            for entity2 in entities[i + 1 :]:
                # Check if entities are within 50 tokens
                distance = abs(entity1.end - entity2.start)
                if distance > 500:  # 500 chars ≈ 50 tokens
                    continue

                # Check for directional verb between entities
                between_text = text[entity1.end : entity2.start].lower()
                has_verb = any(verb in between_text for verb in directional_verbs)

                if has_verb:
                    relation = ExtractedRelation(
                        source_entity=entity1.text,
                        target_entity=entity2.text,
                        relation_type="CORRELATES_WITH",
                        confidence=0.5,
                        evidence_text=text[entity1.start : entity2.end],
                    )
                    relations.append(relation)

        return relations

    @staticmethod
    def _find_entity(text: str, entities: List[ExtractedEntity]) -> Optional[ExtractedEntity]:
        """Find an entity by text (fuzzy match).

        Args:
            text: Entity text to find
            entities: List of entities to search

        Returns:
            Matching entity or None
        """
        text_lower = text.lower().strip()

        # Exact match first
        for entity in entities:
            if entity.text.lower() == text_lower:
                return entity

        # Partial match
        for entity in entities:
            if text_lower in entity.text.lower() or entity.text.lower() in text_lower:
                return entity

        return None
