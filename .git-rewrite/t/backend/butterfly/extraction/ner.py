"""Named Entity Recognition — universal domain mapping.

Maps spaCy entities + keyword rules to the 8 universal node labels:
  Event, Actor, System, Resource, Metric, Policy, Location, Belief
"""

import re
from dataclasses import dataclass

from loguru import logger

try:
    import spacy
    from spacy.language import Language
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not installed — NER will use keyword-only mode")

from butterfly.extraction.normalizer import normalize_entity_name


@dataclass
class ExtractedEntity:
    """Extracted entity from text."""

    text: str
    label: str          # Universal label: Actor, Event, System, Resource, Metric, Policy, Location, Belief
    spacy_label: str    # Original spaCy label (for debugging)
    start: int
    end: int
    confidence: float
    actor_type: str | None = None    # "nation-state" | "organization" | "individual" | "market"
    resource_type: str | None = None # "energy" | "food" | "capital" | "data" | "people"
    system_domain: str | None = None # "financial" | "supply_chain" | "energy_grid" | "political"


# ── spaCy label → universal label ────────────────────────────────────────────

_SPACY_TO_UNIVERSAL: dict[str, str] = {
    "ORG":      "Actor",
    "GPE":      "Location",   # Geo-political entity → Location (also Actor if acting)
    "NORP":     "Actor",      # Nationalities, religious groups → Actor
    "PERSON":   "Actor",
    "MONEY":    "Metric",
    "PERCENT":  "Metric",
    "CARDINAL": "Metric",
    "QUANTITY": "Metric",
    "LAW":      "Policy",
    "EVENT":    "Event",
    "PRODUCT":  "Resource",
    "WORK_OF_ART": "Belief",
    "LANGUAGE": "Actor",
    "DATE":     "Event",      # Dates often anchor events
    "TIME":     "Event",
    "LOC":      "Location",
    "FAC":      "Location",   # Facilities (Strait of Hormuz, Suez Canal)
}

# ── Keyword rules for domain-specific entities spaCy misses ──────────────────

_RESOURCE_KEYWORDS = {
    "oil", "crude", "petroleum", "gas", "lng", "coal", "electricity", "power",
    "food", "grain", "wheat", "corn", "rice", "water", "semiconductor", "chip",
    "chips", "capital", "investment", "data", "bandwidth", "lithium", "cobalt",
    "copper", "steel", "aluminum", "timber", "cotton", "coffee", "sugar",
    "refugees", "migrants", "labor", "workers",
}

_SYSTEM_KEYWORDS = {
    "supply chain", "supply-chain", "grid", "network", "market", "exchange",
    "swift", "payment system", "banking system", "financial system",
    "healthcare system", "power grid", "internet", "logistics", "infrastructure",
    "pipeline", "port", "shipping lane", "trade route", "ecosystem",
    "semiconductor supply", "chip supply", "energy market", "bond market",
    "stock market", "equity market", "credit market", "derivatives market",
}

_BELIEF_KEYWORDS = {
    "sentiment", "confidence", "fear", "panic", "optimism", "pessimism",
    "market sentiment", "public opinion", "narrative", "perception",
    "propaganda", "disinformation", "morale", "trust", "credibility",
    "expectations", "inflation expectations", "risk appetite",
}

_POLICY_KEYWORDS = {
    "sanction", "sanctions", "tariff", "tariffs", "embargo", "ban",
    "regulation", "law", "act", "treaty", "agreement", "accord",
    "executive order", "directive", "mandate", "resolution", "ceasefire",
    "stimulus", "bailout", "subsidy", "tax", "rate hike", "rate cut",
    "quantitative easing", "qe", "austerity",
}

_ACTOR_TYPE_MAP = {
    # Nation-states
    "nation-state": {
        "united states", "us", "usa", "china", "russia", "germany", "france",
        "uk", "britain", "japan", "india", "iran", "israel", "saudi arabia",
        "ukraine", "taiwan", "north korea", "south korea", "brazil", "turkey",
        "pakistan", "egypt", "nigeria", "indonesia", "australia", "canada",
        "mexico", "argentina", "poland", "netherlands", "sweden", "norway",
    },
    # Organizations
    "organization": {
        "fed", "federal reserve", "ecb", "imf", "world bank", "un", "nato",
        "opec", "who", "wto", "g7", "g20", "eu", "european union",
        "sec", "fbi", "cia", "pentagon", "white house", "congress", "senate",
        "hamas", "hezbollah", "isis", "al-qaeda", "ercot", "tsmc", "nvidia",
        "openai", "google", "apple", "microsoft", "amazon", "meta",
    },
}

_LATENCY_PATTERNS = [
    (r"within\s+(\d+)\s+hours?", lambda m: int(m.group(1))),
    (r"within\s+(\d+)\s+days?",  lambda m: int(m.group(1)) * 24),
    (r"within\s+(\d+)\s+weeks?", lambda m: int(m.group(1)) * 168),
    (r"after\s+(\d+)\s+hours?",  lambda m: int(m.group(1))),
    (r"after\s+(\d+)\s+days?",   lambda m: int(m.group(1)) * 24),
    (r"after\s+(\d+)\s+months?", lambda m: int(m.group(1)) * 720),
    (r"(\d+)\s*-\s*(\d+)\s+hours?", lambda m: (int(m.group(1)) + int(m.group(2))) // 2),
    (r"(\d+)\s*-\s*(\d+)\s+days?",  lambda m: ((int(m.group(1)) + int(m.group(2))) // 2) * 24),
]

# Domain-default latencies (hours) when no explicit time is mentioned
DOMAIN_DEFAULT_LATENCY: dict[str, int] = {
    "financial_markets": 2,
    "geopolitics":       72,
    "energy":            24,
    "supply_chain":      168,
    "climate":           720,
    "health":            336,
    "technology":        48,
    "political":         240,
    "humanitarian":      48,
    "default":           48,
}


class EntityExtractor:
    """Extract entities from text and map to universal node labels."""

    def __init__(self) -> None:
        self.nlp = None
        if SPACY_AVAILABLE:
            for model in ("en_core_web_trf", "en_core_web_sm"):
                try:
                    self.nlp = spacy.load(model)
                    logger.info(f"Loaded spaCy model: {model}")
                    break
                except OSError:
                    continue
            if self.nlp is None:
                logger.warning("No spaCy model found — using keyword-only NER")

    # ── Public API ────────────────────────────────────────────────────────────

    def extract(self, text: str) -> list[ExtractedEntity]:
        """Extract entities from text, returning universal-label entities."""
        if not text or not text.strip():
            return []

        entities: list[ExtractedEntity] = []

        # Layer 1: spaCy NER
        if self.nlp:
            entities.extend(self._extract_spacy(text))

        # Layer 2: keyword rules (catches domain-specific terms spaCy misses)
        entities.extend(self._extract_keywords(text, existing=entities))

        # Deduplicate: keep highest confidence per (text, label) pair
        seen: dict[tuple[str, str], ExtractedEntity] = {}
        for ent in entities:
            key = (ent.text.lower(), ent.label)
            if key not in seen or ent.confidence > seen[key].confidence:
                seen[key] = ent

        return list(seen.values())

    def extract_latency(self, text: str, domain: str = "default") -> int:
        """Extract latency in hours from text, or return domain default."""
        text_lower = text.lower()
        for pattern, extractor in _LATENCY_PATTERNS:
            m = re.search(pattern, text_lower)
            if m:
                try:
                    return extractor(m)
                except Exception:
                    continue
        return DOMAIN_DEFAULT_LATENCY.get(domain, DOMAIN_DEFAULT_LATENCY["default"])

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_spacy(self, text: str) -> list[ExtractedEntity]:
        entities = []
        try:
            doc = self.nlp(text)
            for ent in doc.ents:
                label = _SPACY_TO_UNIVERSAL.get(ent.label_, "Actor")
                normalized = normalize_entity_name(ent.text)
                confidence = _SPACY_CONFIDENCE.get(ent.label_, 0.70)

                actor_type = None
                if label == "Actor":
                    actor_type = self._classify_actor_type(normalized)
                elif label == "Location" and ent.label_ == "GPE":
                    # GPE can be both Location and Actor (e.g. "China imposed sanctions")
                    actor_type = "nation-state"

                entities.append(ExtractedEntity(
                    text=normalized,
                    label=label,
                    spacy_label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=confidence,
                    actor_type=actor_type,
                ))
        except Exception as e:
            logger.error(f"spaCy extraction failed: {e}")
        return entities

    def _extract_keywords(
        self, text: str, existing: list[ExtractedEntity]
    ) -> list[ExtractedEntity]:
        """Keyword-based extraction for domain terms spaCy misses."""
        entities = []
        text_lower = text.lower()
        existing_texts = {e.text.lower() for e in existing}

        def _add(term: str, label: str, confidence: float, **kwargs: object) -> None:
            if term not in existing_texts and term in text_lower:
                idx = text_lower.find(term)
                entities.append(ExtractedEntity(
                    text=term.title(),
                    label=label,
                    spacy_label="KEYWORD",
                    start=idx,
                    end=idx + len(term),
                    confidence=confidence,
                    **kwargs,  # type: ignore[arg-type]
                ))

        for kw in _RESOURCE_KEYWORDS:
            _add(kw, "Resource", 0.80, resource_type=_classify_resource(kw))

        for kw in _SYSTEM_KEYWORDS:
            _add(kw, "System", 0.75, system_domain=_classify_system(kw))

        for kw in _BELIEF_KEYWORDS:
            _add(kw, "Belief", 0.70)

        for kw in _POLICY_KEYWORDS:
            _add(kw, "Policy", 0.80)

        return entities

    @staticmethod
    def _classify_actor_type(name: str) -> str:
        name_lower = name.lower()
        for actor_type, names in _ACTOR_TYPE_MAP.items():
            if name_lower in names:
                return actor_type
        # Heuristic: all-caps short names are often organizations
        if name.isupper() and len(name) <= 6:
            return "organization"
        return "organization"  # default


# ── Confidence map ────────────────────────────────────────────────────────────

_SPACY_CONFIDENCE: dict[str, float] = {
    "ORG": 0.90, "GPE": 0.92, "NORP": 0.85, "PERSON": 0.88,
    "MONEY": 0.85, "PERCENT": 0.85, "CARDINAL": 0.75, "QUANTITY": 0.75,
    "LAW": 0.82, "EVENT": 0.78, "PRODUCT": 0.80, "LOC": 0.88, "FAC": 0.85,
}


def _classify_resource(kw: str) -> str:
    if kw in {"oil", "crude", "petroleum", "gas", "lng", "coal", "electricity", "power"}:
        return "energy"
    if kw in {"food", "grain", "wheat", "corn", "rice", "coffee", "sugar", "cotton"}:
        return "food"
    if kw in {"capital", "investment"}:
        return "capital"
    if kw in {"semiconductor", "chip", "chips", "lithium", "cobalt", "copper", "steel"}:
        return "materials"
    if kw in {"data", "bandwidth"}:
        return "data"
    if kw in {"refugees", "migrants", "labor", "workers"}:
        return "people"
    return "commodity"


def _classify_system(kw: str) -> str:
    if any(w in kw for w in ("market", "exchange", "financial", "banking", "swift", "credit", "bond", "equity")):
        return "financial"
    if any(w in kw for w in ("supply chain", "supply-chain", "logistics", "port", "shipping")):
        return "supply_chain"
    if any(w in kw for w in ("grid", "pipeline", "energy")):
        return "energy_grid"
    if any(w in kw for w in ("healthcare", "hospital")):
        return "healthcare"
    if any(w in kw for w in ("internet", "network", "bandwidth")):
        return "digital"
    return "infrastructure"
