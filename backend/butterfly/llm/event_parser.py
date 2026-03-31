"""
UniversalEventParser — turns ANY plain-English input into a structured
UniversalEvent. Uses multi-provider LLM (Gemini → Mistral → Anthropic → fallback).
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field

from butterfly.config import settings

# ── Model ─────────────────────────────────────────────────────────────────────

VALID_DOMAINS = {
    "geopolitics", "economics", "climate", "technology", "health",
    "social", "energy", "logistics", "financial_markets", "humanitarian",
    "environment", "political", "military", "trade", "cultural",
}

VALID_SEVERITIES = {"minor", "moderate", "major", "catastrophic"}
VALID_HORIZONS   = {"hours", "days", "weeks", "months", "years"}


class UniversalEvent(BaseModel):
    """Structured representation of any real-world event."""

    raw_input:          str
    title:              str
    domain:             list[str] = Field(min_length=1)
    primary_actors:     list[str] = Field(min_length=1)
    affected_systems:   list[str] = Field(min_length=1)
    geographic_scope:   list[str] = Field(min_length=1)
    time_horizon:       str       = "weeks"
    severity:           str       = "moderate"
    causal_seeds:       list[str] = Field(min_length=3)
    data_fetch_queries: list[str] = Field(min_length=3)
    occurred_at:        datetime  = Field(default_factory=datetime.utcnow)
    confidence:         float     = Field(ge=0.0, le=1.0)


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a geopolitical and systems analyst with expertise in
complex adaptive systems, causal inference, and global risk. Your job is to
analyze any event and identify its STRUCTURAL CAUSAL CHAIN.

You think in second and third order effects. Find the structural vulnerabilities
nobody is talking about yet.

For causal_seeds: generate the 3-5 MOST NON-OBVIOUS first dominoes this event
will push. Skip the headlines. Find the structural vulnerabilities.

For data_fetch_queries: generate specific, dateable search queries that would
find real quantitative data. Include dates, metrics, and specific actors.

You MUST respond with ONLY valid JSON matching this exact schema:

{
  "title": "string — clean 5-10 word event title",
  "domain": ["list", "of", "domain", "strings"],
  "primary_actors": ["list of key entities driving this event"],
  "affected_systems": ["list of systems this will ripple through"],
  "geographic_scope": ["list of countries/regions affected"],
  "time_horizon": "hours|days|weeks|months|years",
  "severity": "minor|moderate|major|catastrophic",
  "causal_seeds": ["3-5 non-obvious first dominoes"],
  "data_fetch_queries": ["3-8 specific dateable search queries"],
  "confidence": 0.85
}

Valid domain values: geopolitics, economics, climate, technology, health,
social, energy, logistics, financial_markets, humanitarian, environment,
political, military, trade, cultural

Return ONLY the JSON object. No prose, no markdown fences, no explanation."""


# ── Domain keyword classifier ─────────────────────────────────────────────────

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "geopolitics":       ["war", "conflict", "invasion", "sanction", "nato", "un ", "treaty", "diplomat", "alliance", "coup"],
    "military":          ["attack", "missile", "troops", "military", "bomb", "airstrike", "navy", "army", "weapon", "nuclear"],
    "economics":         ["gdp", "recession", "inflation", "rate hike", "fed ", "ecb", "imf", "world bank", "tariff", "trade deficit", "basis point", "bps", "fomc", "federal reserve"],
    "financial_markets": ["stock", "bond", "yield", "market crash", "ipo", "nasdaq", "s&p", "equity", "hedge fund", "crypto"],
    "energy":            ["oil", "gas", "opec", "pipeline", "energy", "petroleum", "lng", "coal", "electricity", "grid"],
    "climate":           ["hurricane", "flood", "drought", "wildfire", "earthquake", "tsunami", "climate", "temperature", "storm", "cyclone"],
    "technology":        ["ai", "chip", "semiconductor", "software", "launch", "startup", "tech", "algorithm", "data center", "cloud"],
    "health":            ["pandemic", "virus", "outbreak", "who ", "vaccine", "pathogen", "epidemic", "hospital", "mortality", "infection"],
    "humanitarian":      ["refugee", "displacement", "famine", "aid", "civilian", "casualt", "shelter", "food crisis", "water"],
    "logistics":         ["supply chain", "shipping", "port", "freight", "container", "suez", "panama", "airline", "cargo"],
    "trade":             ["export", "import", "tariff", "wto", "trade war", "sanction", "embargo", "quota", "customs"],
    "political":         ["election", "president", "parliament", "vote", "government", "policy", "legislation", "protest", "revolution"],
    "environment":       ["deforestation", "pollution", "carbon", "emission", "biodiversity", "ocean", "glacier", "species"],
    "social":            ["protest", "movement", "inequality", "poverty", "education", "migration", "demographic"],
    "cultural":          ["media", "social media", "censorship", "propaganda", "narrative", "public opinion"],
}


class DomainClassifier:
    """Lightweight rule-based domain classifier."""

    async def classify(self, text: str) -> list[str]:
        text_lower = text.lower()
        matched: list[str] = []
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(domain)
        return matched[:5] if matched else ["economics"]


# ── EventParser ───────────────────────────────────────────────────────────────

class EventParser:
    """Parse any plain-English event description into a UniversalEvent.

    Uses multi-provider LLM: Gemini → Mistral → Anthropic → raises.
    """

    def __init__(self) -> None:
        self._classifier = DomainClassifier()
        has_provider = any([
            settings.gemini_api_key,
            settings.mistral_api_key,
            settings.anthropic_api_key,
        ])
        if not has_provider:
            raise RuntimeError(
                "No LLM API key configured. Set one of: "
                "GEMINI_API_KEY, MISTRAL_API_KEY, or ANTHROPIC_API_KEY in backend/.env"
            )

    async def parse(self, raw_input: str) -> UniversalEvent:
        """Parse raw input into a UniversalEvent. Retries once on JSON failure."""
        from butterfly.llm.providers import llm_complete, extract_json

        for attempt in range(2):
            try:
                raw_text = await llm_complete(
                    system=_SYSTEM_PROMPT,
                    user=raw_input,
                    max_tokens=1024,
                )

                data = extract_json(raw_text)
                data["raw_input"] = raw_input

                # Sanitise
                data["domain"] = [d for d in data.get("domain", []) if d in VALID_DOMAINS] or ["economics"]
                data["severity"] = data.get("severity", "moderate") if data.get("severity") in VALID_SEVERITIES else "moderate"
                data["time_horizon"] = data.get("time_horizon", "weeks") if data.get("time_horizon") in VALID_HORIZONS else "weeks"

                # Ensure minimum list lengths
                if len(data.get("causal_seeds", [])) < 3:
                    data["causal_seeds"] = (data.get("causal_seeds", []) + [
                        "Initial shock propagates to financial markets",
                        "Supply chain disruption follows within 48-72 hours",
                        "Policy response from governments and central banks",
                    ])[:3]
                if len(data.get("data_fetch_queries", [])) < 3:
                    short = raw_input[:50]
                    data["data_fetch_queries"] = [short, f"{short} economic impact", f"{short} market reaction"]

                event = UniversalEvent(**data)
                logger.info(f"Parsed event: '{event.title}' domains={event.domain}")
                return event

            except Exception as e:
                if attempt == 0:
                    logger.warning(f"EventParser attempt 1 failed ({e}), retrying...")
                    continue
                logger.error(f"EventParser failed after 2 attempts: {e}")
                raise

        raise RuntimeError("EventParser: unreachable")