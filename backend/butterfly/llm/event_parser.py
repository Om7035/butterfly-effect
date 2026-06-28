"""
UniversalEventParser — turns ANY plain-English input into a structured
UniversalEvent. Uses multi-provider LLM (Gemini → Mistral → Anthropic → fallback).
"""

from __future__ import annotations

import asyncio
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

_SYSTEM_PROMPT = """You are a geopolitical and systems analyst specializing in cascade effects.
Analyze the event and return ONLY a valid JSON object — no prose, no markdown fences.

Schema (all fields required):
{
  "title": "5-10 word clean event title",
  "domain": ["geopolitics","economics","military","energy","health","climate","technology","trade","humanitarian","financial_markets","political","logistics","social","environment","cultural"],
  "primary_actors": ["list of key entities"],
  "affected_systems": ["list of systems this ripples through"],
  "geographic_scope": ["list of countries/regions"],
  "time_horizon": "hours|days|weeks|months|years",
  "severity": "minor|moderate|major|catastrophic",
  "causal_seeds": ["3-5 non-obvious first dominoes — skip headlines, find structural vulnerabilities"],
  "data_fetch_queries": ["3-5 specific search queries with dates and metrics"],
  "confidence": 0.85
}

Return ONLY the JSON. No explanation. No markdown."""


# ── Domain keyword classifier (fallback) ─────────────────────────────────────

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "geopolitics":       ["war", "conflict", "invasion", "sanction", "nato", "treaty", "diplomat", "alliance", "coup", "taiwan", "strait"],
    "military":          ["attack", "missile", "troops", "military", "bomb", "airstrike", "navy", "army", "weapon", "nuclear"],
    "economics":         ["gdp", "recession", "inflation", "rate hike", "fed ", "ecb", "imf", "world bank", "tariff", "basis point", "bps", "fomc", "federal reserve", "interest rate"],
    "financial_markets": ["stock", "bond", "yield", "market crash", "ipo", "nasdaq", "s&p", "equity", "hedge fund", "crypto"],
    "energy":            ["oil", "gas", "opec", "pipeline", "energy", "petroleum", "lng", "coal", "electricity", "grid"],
    "climate":           ["hurricane", "flood", "drought", "wildfire", "earthquake", "tsunami", "climate", "temperature", "storm", "cyclone"],
    "technology":        ["ai", "chip", "semiconductor", "software", "launch", "startup", "tech", "algorithm", "data center", "cloud", "chatgpt", "openai"],
    "health":            ["pandemic", "virus", "outbreak", "who ", "vaccine", "pathogen", "epidemic", "hospital", "mortality", "infection"],
    "humanitarian":      ["refugee", "displacement", "famine", "aid", "civilian", "casualt", "shelter", "food crisis", "water"],
    "logistics":         ["supply chain", "shipping", "port", "freight", "container", "suez", "panama", "airline", "cargo"],
    "trade":             ["export", "import", "tariff", "wto", "trade war", "embargo", "quota", "customs"],
    "political":         ["election", "president", "parliament", "vote", "government", "policy", "legislation", "protest", "revolution"],
    "environment":       ["deforestation", "pollution", "carbon", "emission", "biodiversity", "ocean", "glacier", "species"],
    "social":            ["protest", "movement", "inequality", "poverty", "education", "migration", "demographic"],
    "cultural":          ["media", "social media", "censorship", "propaganda", "narrative", "public opinion"],
}


# ── EventParser ───────────────────────────────────────────────────────────────

_DEEP_SYSTEM_PROMPT = """You are a systems analyst specializing in NON-OBVIOUS cascade effects.
You have already identified the immediate (1st and 2nd order) effects of an event.
Your job is to find the 3rd, 4th, and 5th order effects that most analysts miss.

Given the event and its known immediate effects, identify what happens NEXT — the downstream
consequences that emerge weeks and months later, crossing into unexpected domains.

Return ONLY a valid JSON object:
{
  "deep_causal_seeds": ["3-5 third/fourth order effects — must be different domains from immediate effects"],
  "cross_domain_links": [
    {"from": "immediate effect", "to": "deep effect", "mechanism": "why this link exists", "latency": "weeks|months"}
  ],
  "non_obvious_actors": ["actors who respond to the 3rd/4th order effects, not the original event"]
}

Return ONLY the JSON. No explanation. No markdown."""


class EventParser:
    """Parse any plain-English event description into a UniversalEvent.

    Uses multi-provider LLM: Gemini → Mistral → Anthropic → keyword fallback.
    Never raises — always returns a valid UniversalEvent.
    Supports two-pass parsing for deeper causal chains (parse_deep).
    """

    def __init__(self) -> None:
        has_provider = any([
            settings.gemini_api_key,
            settings.mistral_api_key,
            settings.anthropic_api_key,
        ])
        if not has_provider:
            logger.warning(
                "No LLM API key configured — EventParser will use keyword fallback only. "
                "Set GEMINI_API_KEY or MISTRAL_API_KEY in backend/.env"
            )

    async def parse(self, raw_input: str) -> UniversalEvent:
        """Pass 1: Parse raw input into a UniversalEvent (immediate effects)."""
        for attempt in range(3):
            try:
                event = await self._llm_parse(raw_input)
                logger.info(f"[PARSER] LLM success attempt {attempt+1}: '{event.title}' domains={event.domain}")
                return event
            except Exception as e:
                wait = 2 ** attempt
                logger.warning(f"[PARSER] Attempt {attempt+1} failed: {e} — waiting {wait}s")
                if attempt < 2:
                    await asyncio.sleep(wait)

        logger.warning("[PARSER] All LLM attempts failed — using keyword fallback")
        return self._fallback_parse(raw_input)

    async def parse_deep(self, raw_input: str, pass1_seeds: list[str]) -> dict:
        """
        Pass 2: Given pass1 immediate effects, find 3rd/4th/5th order effects.
        Returns dict with deep_causal_seeds, cross_domain_links, non_obvious_actors.
        Never raises — returns empty dict on failure.
        """
        from butterfly.llm.providers import llm_complete

        user_prompt = (
            f"Event: {raw_input}\n\n"
            f"Known immediate effects (1st/2nd order):\n"
            + "\n".join(f"- {s}" for s in pass1_seeds[:5])
        )

        try:
            raw_text = await llm_complete(
                system=_DEEP_SYSTEM_PROMPT,
                user=user_prompt,
                max_tokens=1024,
            )
            text = raw_text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*\n?", "", text)
                text = re.sub(r"\n?```\s*$", "", text)
                text = text.strip()
            data = json.loads(text)
            logger.info(f"[PARSER] Deep parse: {len(data.get('deep_causal_seeds', []))} deep seeds")
            return data
        except Exception as e:
            logger.warning(f"[PARSER] Deep parse failed: {e}")
            return {}

    async def _llm_parse(self, raw_input: str) -> UniversalEvent:
        """Single LLM call attempt. Raises on any failure."""
        from butterfly.llm.providers import llm_complete

        raw_text = await llm_complete(
            system=_SYSTEM_PROMPT,
            user=raw_input,
            max_tokens=2048,  # JSON needs room — was 1024, bumped to 2048
        )

        # Strip markdown fences if model added them despite instructions
        text = raw_text.strip()
        if text.startswith("```"):
            # Remove opening fence
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            # Remove closing fence
            text = re.sub(r"\n?```\s*$", "", text)
            text = text.strip()

        data = json.loads(text)
        data["raw_input"] = raw_input

        # Sanitise domain — keep only valid values
        raw_domains = data.get("domain", [])
        if isinstance(raw_domains, str):
            raw_domains = [raw_domains]
        data["domain"] = [d for d in raw_domains if d in VALID_DOMAINS]
        if not data["domain"]:
            # Fallback: classify from text
            data["domain"] = _keyword_domains(raw_input)

        # Sanitise enums
        if data.get("severity") not in VALID_SEVERITIES:
            data["severity"] = "moderate"
        if data.get("time_horizon") not in VALID_HORIZONS:
            data["time_horizon"] = "weeks"

        # Ensure minimum list lengths
        _pad_list(data, "causal_seeds", 3, [
            "Initial shock propagates to financial markets",
            "Supply chain disruption follows within 48-72 hours",
            "Policy response from governments and central banks",
        ])
        _pad_list(data, "data_fetch_queries", 3, [
            raw_input[:60],
            f"{raw_input[:50]} economic impact",
            f"{raw_input[:50]} market reaction",
        ])
        _pad_list(data, "primary_actors", 1, ["Unknown Actor"])
        _pad_list(data, "affected_systems", 1, ["Global Economy"])
        _pad_list(data, "geographic_scope", 1, ["Global"])

        if "confidence" not in data:
            data["confidence"] = 0.85

        return UniversalEvent(**data)

    def _fallback_parse(self, raw_input: str) -> UniversalEvent:
        """
        Deterministic keyword extraction — never fails, never returns None.
        Used when all LLM attempts fail.
        """
        text_lower = raw_input.lower()
        domain = _keyword_domains(raw_input)
        short = raw_input[:60].strip()

        # Build domain-specific seeds
        seed_map = {
            "geopolitics": [
                "Energy markets reprice risk premium within hours",
                "Shipping insurance premiums spike across affected sea lanes",
                "Refugee flows strain neighboring country infrastructure",
            ],
            "military": [
                "Defense contractor stocks surge on increased procurement expectations",
                "Civilian infrastructure damage disrupts supply chains",
                "Allied nations activate mutual defense consultations",
            ],
            "economics": [
                "Bond yields reprice across the curve within 48 hours",
                "Currency markets reflect capital flight from affected region",
                "Corporate credit spreads widen as refinancing risk rises",
            ],
            "health": [
                "Healthcare supply chains face PPE and pharmaceutical shortages",
                "Labor force participation drops as illness spreads",
                "Insurance sector faces unprecedented claims exposure",
            ],
            "climate": [
                "Infrastructure repair costs strain municipal bond markets",
                "Agricultural commodity prices spike on supply disruption",
                "Insurance sector reassesses catastrophic risk models",
            ],
            "technology": [
                "Incumbent software vendors face accelerated displacement",
                "Data center demand spikes driving energy consumption",
                "Labor market bifurcates between AI-augmented and displaced workers",
            ],
        }

        primary_domain = domain[0] if domain else "economics"
        seeds = seed_map.get(primary_domain, seed_map["economics"])

        return UniversalEvent(
            raw_input=raw_input,
            title=short,
            domain=domain,
            primary_actors=["Unknown Actor"],
            affected_systems=["Global Economy", "Financial Markets", "Supply Chains"],
            geographic_scope=["Global"],
            time_horizon="weeks",
            severity="moderate",
            causal_seeds=seeds,
            data_fetch_queries=[
                short,
                f"{short} economic impact",
                f"{short} market reaction",
                f"{short} policy response",
            ],
            occurred_at=datetime.utcnow(),
            confidence=0.4,  # flag: this is a fallback, not LLM output
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _keyword_domains(text: str) -> list[str]:
    """Classify domains from text using keyword matching."""
    text_lower = text.lower()
    matched = []
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(domain)
    return matched[:5] if matched else ["economics"]


def _pad_list(data: dict, key: str, min_len: int, defaults: list) -> None:
    """Ensure data[key] is a list with at least min_len items."""
    current = data.get(key, [])
    if not isinstance(current, list):
        current = [str(current)]
    if len(current) < min_len:
        current = (current + defaults)[:max(min_len, len(current))]
    data[key] = current
