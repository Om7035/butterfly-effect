"""
UniversalEventParser — turns ANY plain-English input into a structured
UniversalEvent using Claude. Domain-agnostic by design.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

import anthropic
from loguru import logger
from pydantic import BaseModel, Field

from butterfly.config import settings

# ── Model ────────────────────────────────────────────────────────────────────

VALID_DOMAINS = {
    "geopolitics", "economics", "climate", "technology", "health",
    "social", "energy", "logistics", "financial_markets", "humanitarian",
    "environment", "political", "military", "trade", "cultural",
}

VALID_SEVERITIES = {"minor", "moderate", "major", "catastrophic"}
VALID_HORIZONS   = {"hours", "days", "weeks", "months", "years"}


class UniversalEvent(BaseModel):
    """Structured representation of any real-world event."""

    raw_input:        str
    title:            str
    domain:           list[str]          = Field(min_length=1)
    primary_actors:   list[str]          = Field(min_length=1)
    affected_systems: list[str]          = Field(min_length=1)
    geographic_scope: list[str]          = Field(min_length=1)
    time_horizon:     str                = "weeks"
    severity:         str                = "moderate"
    causal_seeds:     list[str]          = Field(min_length=3)
    data_fetch_queries: list[str]        = Field(min_length=3)
    occurred_at:      datetime           = Field(default_factory=datetime.utcnow)
    confidence:       float              = Field(ge=0.0, le=1.0)


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a geopolitical and systems analyst with expertise in
complex adaptive systems, causal inference, and global risk. Your job is to
analyze any event — war, natural disaster, tech launch, pandemic, policy change,
anything — and identify its STRUCTURAL CAUSAL CHAIN.

You think in second and third order effects. You ask: "What does this break that
nobody is talking about yet?" You identify which systems are STRUCTURALLY
VULNERABLE to this event type, not just the obvious first-order effects.

For causal_seeds: generate the 3-5 MOST NON-OBVIOUS first dominoes this event
will push. Skip the headlines. Find the structural vulnerabilities.

For data_fetch_queries: generate specific, dateable search queries that would
find real quantitative data about this event's effects. Include dates, metrics,
and specific actors. Example: "Gaza conflict crude oil futures October 2023"
not just "Gaza oil".

You MUST respond with ONLY valid JSON matching this exact schema — no prose,
no markdown, no explanation:

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
  "confidence": 0.0
}

Valid domain values: geopolitics, economics, climate, technology, health,
social, energy, logistics, financial_markets, humanitarian, environment,
political, military, trade, cultural

Confidence: your certainty that you've correctly identified the causal structure
(0.0 = no idea, 1.0 = textbook case with clear historical precedent)."""


# ── DomainClassifier ─────────────────────────────────────────────────────────

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "geopolitics":       ["war", "conflict", "invasion", "sanction", "nato", "un ", "treaty", "diplomat", "alliance", "coup"],
    "military":          ["attack", "missile", "troops", "military", "bomb", "airstrike", "navy", "army", "weapon", "nuclear"],
    "economics":         ["gdp", "recession", "inflation", "rate hike", "fed ", "ecb", "imf", "world bank", "tariff", "trade deficit"],
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
    """Lightweight rule-based domain classifier with LLM fallback."""

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None
        if settings.anthropic_api_key:
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def classify(self, text: str) -> list[str]:
        """Classify text into one or more domains."""
        text_lower = text.lower()
        matched: list[str] = []

        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(domain)

        if matched:
            return matched[:5]  # cap at 5

        # LLM fallback
        if self._client:
            try:
                resp = await self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=100,
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Classify this event into 1-3 domains from this list: "
                            f"{', '.join(sorted(VALID_DOMAINS))}.\n"
                            f"Event: {text}\n"
                            f"Respond with ONLY a JSON array of strings, e.g. [\"economics\", \"trade\"]"
                        ),
                    }],
                )
                raw = resp.content[0].text.strip()
                domains = json.loads(raw)
                return [d for d in domains if d in VALID_DOMAINS] or ["economics"]
            except Exception as e:
                logger.warning(f"DomainClassifier LLM fallback failed: {e}")

        return ["economics"]  # safe default


# ── EventParser ───────────────────────────────────────────────────────────────

class EventParser:
    """Parse any plain-English event description into a UniversalEvent."""

    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to backend/.env to enable LLM event parsing."
            )
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._classifier = DomainClassifier()

    async def parse(self, raw_input: str) -> UniversalEvent:
        """Parse raw input into a UniversalEvent. Retries once on JSON failure."""
        for attempt in range(2):
            try:
                resp = await self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": raw_input}],
                )
                raw_json = resp.content[0].text.strip()

                # Strip markdown code fences if present
                raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
                raw_json = re.sub(r"\s*```$", "", raw_json)

                data = json.loads(raw_json)
                data["raw_input"] = raw_input

                # Sanitise domain/severity/horizon
                data["domain"] = [d for d in data.get("domain", []) if d in VALID_DOMAINS] or ["economics"]
                data["severity"] = data.get("severity", "moderate") if data.get("severity") in VALID_SEVERITIES else "moderate"
                data["time_horizon"] = data.get("time_horizon", "weeks") if data.get("time_horizon") in VALID_HORIZONS else "weeks"

                event = UniversalEvent(**data)
                logger.info(f"Parsed event: '{event.title}' domains={event.domain}")
                return event

            except (json.JSONDecodeError, Exception) as e:
                if attempt == 0:
                    logger.warning(f"EventParser attempt 1 failed ({e}), retrying...")
                    continue
                logger.error(f"EventParser failed after 2 attempts: {e}")
                raise

        raise RuntimeError("EventParser: unreachable")
