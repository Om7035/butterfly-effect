"""Universal relationship extraction — maps text to all 14 causal edge types."""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from loguru import logger
import re

from butterfly.extraction.ner import ExtractedEntity


@dataclass
class ExtractedRelation:
    source_entity: str
    target_entity: str
    relation_type: str
    confidence: float
    evidence_text: str
    latency_hours: Optional[int] = None
    direction: Optional[str] = None
    strength: Optional[float] = None
    mechanism: Optional[str] = None
    severity: Optional[float] = None
    probability: Optional[float] = None
    volume: Optional[str] = None
    destination: Optional[str] = None
    vulnerability: Optional[float] = None
    criticality: Optional[float] = None
    substitutability: Optional[float] = None
    cost_premium: Optional[float] = None
    feasibility: Optional[float] = None
    sentiment: Optional[float] = None
    r_squared: Optional[float] = None
    validated: bool = False


# (regex, relation_type, base_confidence, direction_hint)
_PATTERNS: List[Tuple[str, str, float, Optional[str]]] = [
    # CAUSES
    (r"\b(\w[\w\s]{0,25}?)\s+caused\s+([\w\s]{1,25}?)\b",         "CAUSES", 0.95, None),
    (r"\b(\w[\w\s]{0,25}?)\s+led\s+to\s+([\w\s]{1,25}?)\b",       "CAUSES", 0.90, None),
    (r"\b(\w[\w\s]{0,25}?)\s+resulted\s+in\s+([\w\s]{1,25}?)\b",  "CAUSES", 0.90, None),
    (r"due\s+to\s+([\w\s]{1,25}?),\s+([\w\s]{1,25}?)\b",          "CAUSES", 0.85, None),
    (r"because\s+of\s+([\w\s]{1,25}?),\s+([\w\s]{1,25}?)\b",      "CAUSES", 0.85, None),
    # TRIGGERS
    (r"\b(\w[\w\s]{0,25}?)\s+triggered\s+([\w\s]{1,25}?)\b",      "TRIGGERS", 0.95, None),
    (r"\b(\w[\w\s]{0,25}?)\s+sparked\s+([\w\s]{1,25}?)\b",        "TRIGGERS", 0.90, None),
    (r"\b(\w[\w\s]{0,25}?)\s+ignited\s+([\w\s]{1,25}?)\b",        "TRIGGERS", 0.88, None),
    # INFLUENCES
    (r"\b(\w[\w\s]{0,25}?)\s+drove\s+([\w\s]{1,25}?)\s+(?:up|higher)", "INFLUENCES", 0.85, "increases"),
    (r"\b(\w[\w\s]{0,25}?)\s+drove\s+([\w\s]{1,25}?)\s+(?:down|lower)","INFLUENCES", 0.85, "decreases"),
    (r"\b(\w[\w\s]{0,25}?)\s+drove\s+([\w\s]{1,25}?)\b",          "INFLUENCES", 0.78, None),
    (r"\b(\w[\w\s]{0,25}?)\s+raised\s+([\w\s]{1,25}?)\b",         "INFLUENCES", 0.80, "increases"),
    (r"\b(\w[\w\s]{0,25}?)\s+lowered\s+([\w\s]{1,25}?)\b",        "INFLUENCES", 0.80, "decreases"),
    (r"\b(\w[\w\s]{0,25}?)\s+boosted\s+([\w\s]{1,25}?)\b",        "INFLUENCES", 0.80, "increases"),
    (r"\b(\w[\w\s]{0,25}?)\s+dampened\s+([\w\s]{1,25}?)\b",       "INFLUENCES", 0.80, "decreases"),
    (r"\b(\w[\w\s]{0,25}?)\s+destabilized\s+([\w\s]{1,25}?)\b",   "INFLUENCES", 0.85, "destabilizes"),
    (r"\b(\w[\w\s]{0,25}?)\s+affected\s+([\w\s]{1,25}?)\b",       "INFLUENCES", 0.68, None),
    # DISRUPTS
    (r"\b(\w[\w\s]{0,25}?)\s+disrupted\s+([\w\s]{1,25}?)\b",      "DISRUPTS", 0.90, None),
    (r"\b(\w[\w\s]{0,25}?)\s+halted\s+([\w\s]{1,25}?)\b",         "DISRUPTS", 0.88, None),
    (r"\b(\w[\w\s]{0,25}?)\s+crippled\s+([\w\s]{1,25}?)\b",       "DISRUPTS", 0.88, None),
    (r"\b(\w[\w\s]{0,25}?)\s+paralyzed\s+([\w\s]{1,25}?)\b",      "DISRUPTS", 0.90, None),
    (r"\b(\w[\w\s]{0,25}?)\s+collapsed\s+([\w\s]{1,25}?)\b",      "DISRUPTS", 0.88, None),
    # DEPENDS_ON
    (r"\b(\w[\w\s]{0,25}?)\s+depends?\s+on\s+([\w\s]{1,25}?)\b",  "DEPENDS_ON", 0.88, None),
    (r"\b(\w[\w\s]{0,25}?)\s+relies?\s+on\s+([\w\s]{1,25}?)\b",   "DEPENDS_ON", 0.85, None),
    (r"\b(\w[\w\s]{0,25}?)\s+requires?\s+([\w\s]{1,25}?)\b",      "DEPENDS_ON", 0.78, None),
    # ESCALATES_TO
    (r"\b(\w[\w\s]{0,25}?)\s+escalated\s+(?:in)?to\s+([\w\s]{1,25}?)\b", "ESCALATES_TO", 0.90, None),
    (r"\b(\w[\w\s]{0,25}?)\s+could\s+escalate\s+to\s+([\w\s]{1,25}?)\b", "ESCALATES_TO", 0.62, None),
    # DISPLACES
    (r"\b(\w[\w\s]{0,25}?)\s+displaced\s+([\w\s]{1,25}?)\b",      "DISPLACES", 0.88, None),
    (r"\b(\w[\w\s]{0,25}?)\s+forced\s+([\w\s]{1,25}?)\s+(?:to flee|out)", "DISPLACES", 0.85, None),
    # RETALIATES
    (r"\b(\w[\w\s]{0,25}?)\s+retaliated\s+against\s+([\w\s]{1,25}?)\b",   "RETALIATES", 0.92, None),
    (r"\b(\w[\w\s]{0,25}?)\s+struck\s+back\s+at\s+([\w\s]{1,25}?)\b",    "RETALIATES", 0.88, None),
    (r"\b(\w[\w\s]{0,25}?)\s+counterattacked\s+([\w\s]{1,25}?)\b",        "RETALIATES", 0.85, None),
    # SUBSTITUTES
    (r"\b(\w[\w\s]{0,25}?)\s+replaced\s+([\w\s]{1,25}?)\b",       "SUBSTITUTES", 0.88, None),
    (r"\b(\w[\w\s]{0,25}?)\s+substituted\s+(?:for\s+)?([\w\s]{1,25}?)\b", "SUBSTITUTES", 0.88, None),
    (r"\b(\w[\w\s]{0,25}?)\s+switched\s+(?:from|to)\s+([\w\s]{1,25}?)\b", "SUBSTITUTES", 0.80, None),
    # SANCTIONED_BY
    (r"\b(\w[\w\s]{0,25}?)\s+sanctioned\s+([\w\s]{1,25}?)\b",     "SANCTIONED_BY", 0.90, None),
    (r"\b(\w[\w\s]{0,25}?)\s+imposed\s+sanctions\s+on\s+([\w\s]{1,25}?)\b","SANCTIONED_BY", 0.90, None),
    (r"\b(\w[\w\s]{0,25}?)\s+embargoed\s+([\w\s]{1,25}?)\b",      "SANCTIONED_BY", 0.88, None),
    # FLOWS_THROUGH
    (r"\b(\w[\w\s]{0,25}?)\s+flows?\s+through\s+([\w\s]{1,25}?)\b","FLOWS_THROUGH", 0.88, None),
    (r"\b(\w[\w\s]{0,25}?)\s+transits?\s+through\s+([\w\s]{1,25}?)\b","FLOWS_THROUGH", 0.85, None),
    (r"\b(\w[\w\s]{0,25}?)\s+shipped\s+(?:via|through)\s+([\w\s]{1,25}?)\b","FLOWS_THROUGH", 0.80, None),
    # CORRELATES_WITH
    (r"\b(\w[\w\s]{0,25}?)\s+correlates?\s+with\s+([\w\s]{1,25}?)\b","CORRELATES_WITH", 0.70, None),
    (r"\b(\w[\w\s]{0,25}?)\s+tracks?\s+([\w\s]{1,25}?)\b",        "CORRELATES_WITH", 0.58, None),
]


class RelationExtractor:
    """Extract relationships between entities from text."""

    def extract_relations(
        self, text: str, entities: List[ExtractedEntity]
    ) -> List[ExtractedRelation]:
        if not text or not entities:
            return []

        relations: List[ExtractedRelation] = []
        relations.extend(self._extract_by_patterns(text, entities))
        relations.extend(self._extract_by_proximity(text, entities))

        relations = [r for r in relations if r.confidence >= 0.45]

        seen: dict[tuple[str, str, str], ExtractedRelation] = {}
        for r in relations:
            key = (r.source_entity.lower(), r.target_entity.lower(), r.relation_type)
            if key not in seen or r.confidence > seen[key].confidence:
                seen[key] = r

        return sorted(seen.values(), key=lambda r: r.confidence, reverse=True)

    def _extract_by_patterns(
        self, text: str, entities: List[ExtractedEntity]
    ) -> List[ExtractedRelation]:
        relations = []
        for pattern, rel_type, base_conf, direction in _PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    src = _find_entity(match.group(1).strip(), entities)
                    tgt = _find_entity(match.group(2).strip(), entities)
                    if src and tgt and src.text != tgt.text:
                        relations.append(ExtractedRelation(
                            source_entity=src.text,
                            target_entity=tgt.text,
                            relation_type=rel_type,
                            confidence=base_conf,
                            evidence_text=match.group(0),
                            direction=direction,
                        ))
                except (IndexError, AttributeError):
                    pass
        return relations

    def _extract_by_proximity(
        self, text: str, entities: List[ExtractedEntity]
    ) -> List[ExtractedRelation]:
        relations = []
        up_verbs = {"increase", "rise", "grow", "expand", "improve", "surge", "spike", "climb", "boost"}
        down_verbs = {"decrease", "fall", "shrink", "contract", "worsen", "plunge", "drop", "slide"}
        all_verbs = up_verbs | down_verbs

        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1:]:
                if abs(e1.end - e2.start) > 300:
                    continue
                between = text[e1.end:e2.start].lower()
                for verb in all_verbs:
                    if verb in between:
                        direction = "increases" if verb in up_verbs else "decreases"
                        relations.append(ExtractedRelation(
                            source_entity=e1.text,
                            target_entity=e2.text,
                            relation_type="INFLUENCES",
                            confidence=0.50,
                            evidence_text=text[e1.start:e2.end],
                            direction=direction,
                        ))
                        break
        return relations


def _find_entity(text: str, entities: List[ExtractedEntity]) -> Optional[ExtractedEntity]:
    text_lower = text.lower().strip()
    for e in entities:
        if e.text.lower() == text_lower:
            return e
    for e in entities:
        if text_lower in e.text.lower() or e.text.lower() in text_lower:
            return e
    return None
