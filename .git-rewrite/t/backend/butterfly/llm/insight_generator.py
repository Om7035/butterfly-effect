
"""InsightGenerator — turns a causal chain into plain-English non-obvious insights.

Uses Claude to generate 3-5 insights that:
  - Reference specific causal hops (not vague claims)
  - Flag 3rd/4th order effects explicitly
  - Are specific about timing
  - Name specific actors
  - Flag uncertainty honestly

Falls back to rule-based generation when no API key is available.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    pass

_SYSTEM_PROMPT = """You are a geopolitical and systems analyst specializing in
second and third-order effects. You have read Nassim Taleb, George Soros, and
Judea Pearl. You think in causal chains, not headlines.

Your job: given a causal chain from a simulation, generate 3-5 insights that
a smart analyst would MISS if they only read the news.

Rules (non-negotiable):
1. Every insight MUST start with "What most people miss: "
2. Reference a SPECIFIC hop in the chain by name (e.g. "the oil_price → inflation hop")
3. Flag 3rd/4th order effects with "[3rd order]" or "[4th order]" at the start
4. Be specific about timing: "within 6-8 weeks" not "soon"
5. Name specific actors: "OPEC" not "oil producers", "ECB" not "central banks"
6. Flag uncertainty: "this assumes continued escalation" or "if sanctions hold"
7. PRIORITIZE the surprising over the obvious — skip the headlines

Respond with ONLY a JSON array of strings. No prose, no markdown, no explanation."""


class InsightGenerator:
    """Generate non-obvious causal insights using Claude or rule-based fallback."""

    async def generate(
        self,
        chain,  # SimulationCausalChain
        event,  # UniversalEvent
    ) -> list[str]:
        """Generate insights from a SimulationCausalChain object."""
        chain_dict = chain.model_dump() if hasattr(chain, "model_dump") else chain
        return await self.generate_from_dict(chain_dict, event)

    async def generate_from_dict(
        self,
        chain_dict: dict,
        event,  # UniversalEvent
    ) -> list[str]:
        """Generate insights from a chain dict (works with both Pydantic and plain dicts)."""
        try:
            from butterfly.config import settings
            if not settings.anthropic_api_key:
                raise RuntimeError("No ANTHROPIC_API_KEY")

            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

            prompt = self._build_prompt(chain_dict, event)
            resp = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = resp.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            insights = json.loads(raw)

            if not isinstance(insights, list):
                raise ValueError("Expected JSON array")

            # Validate: each insight must start with "What most people miss:"
            validated = []
            for ins in insights[:5]:
                if isinstance(ins, str) and len(ins) > 20:
                    if not ins.startswith("What most people miss:"):
                        ins = "What most people miss: " + ins
                    validated.append(ins)

            if len(validated) < 3:
                raise ValueError(f"Only {len(validated)} valid insights generated")

            logger.info(f"InsightGenerator: {len(validated)} insights for '{event.title}'")
            return validated

        except Exception as e:
            logger.warning(f"InsightGenerator LLM failed ({e}), using rule-based fallback")
            return self._rule_based(chain_dict, event)

    @staticmethod
    def _build_prompt(chain_dict: dict, event) -> str:
        """Build the user prompt from chain and event data."""
        # Extract hop descriptions
        hops = chain_dict.get("chains", [])
        edges = chain_dict.get("edges", [])

        if hops:
            hop_lines = "\n".join(
                f"  Hop {i+1}: {h.get('from_agent', '?')} → {h.get('to_variable', '?')} "
                f"(magnitude={h.get('magnitude', '?'):.2f}, "
                f"step={h.get('step_triggered', '?')}, "
                f"confidence={h.get('confidence', '?'):.2f})"
                for i, h in enumerate(hops[:8])
            )
        elif edges:
            hop_lines = "\n".join(
                f"  Edge {i+1}: {e.get('source', '?')} → {e.get('target', '?')} "
                f"(confidence={e.get('confidence', '?')}, latency={e.get('latency_hours', '?')}h)"
                for i, e in enumerate(edges[:8])
            )
        else:
            hop_lines = "  No hops extracted"

        domains = getattr(event, "domain", []) or chain_dict.get("domain_coverage", [])
        actors = getattr(event, "primary_actors", [])
        scope = getattr(event, "geographic_scope", [])
        severity = getattr(event, "severity", "moderate")
        total_hops = chain_dict.get("total_hops", len(edges))
        feedback_loops = chain_dict.get("feedback_loops", [])

        return f"""Event: {getattr(event, 'title', 'Unknown Event')}
Severity: {severity}
Domains: {', '.join(domains)}
Primary actors: {', '.join(actors[:5]) if actors else 'Unknown'}
Geographic scope: {', '.join(scope[:5]) if scope else 'Global'}

Causal chain ({total_hops} hops):
{hop_lines}

Feedback loops detected: {len(feedback_loops)} {'(cycles: ' + str(feedback_loops[:2]) + ')' if feedback_loops else '(none)'}

Domain coverage: {', '.join(chain_dict.get('domain_coverage', domains))}

Generate 4 non-obvious insights. Remember: specific hops, specific actors, specific timing, flag order."""

    @staticmethod
    def _rule_based(chain_dict: dict, event) -> list[str]:
        """Rule-based fallback when LLM is unavailable."""
        hops = chain_dict.get("chains", [])
        edges = chain_dict.get("edges", [])
        domains = getattr(event, "domain", []) or ["economics"]
        seeds = getattr(event, "causal_seeds", [])
        systems = getattr(event, "affected_systems", [])
        scope = getattr(event, "geographic_scope", ["Global"])
        title = getattr(event, "title", "this event")

        # Pick the most interesting hop (highest magnitude or latest step)
        interesting_hop = ""
        if hops:
            top = max(hops, key=lambda h: h.get("magnitude", 0))
            interesting_hop = f"the {top.get('from_agent', '?')} → {top.get('to_variable', '?')} hop"
        elif edges and len(edges) >= 3:
            e = edges[2]
            interesting_hop = f"the {e.get('source', '?')} → {e.get('target', '?')} edge"
        else:
            interesting_hop = f"the {seeds[0] if seeds else 'first-order'} effect"

        third_order = seeds[2] if len(seeds) > 2 else (systems[0] if systems else "downstream systems")
        fourth_order = domains[-1] if len(domains) > 1 else "financial markets"
        region2 = scope[1] if len(scope) > 1 else "neighboring regions"

        return [
            f"What most people miss: {interesting_hop} will manifest within 24-48 hours — "
            f"before most analysts have updated their models for {title}.",
            f"What most people miss: [3rd order] {third_order} is structurally exposed to this chain. "
            f"This is the non-obvious vulnerability that won't appear in headlines for 2-3 weeks.",
            f"What most people miss: Geographic spillover to {region2} is underpriced. "
            f"Markets are pricing only the direct impact, not the second-order contagion.",
            f"What most people miss: [4th order] The {fourth_order} domain effects will peak "
            f"6-8 weeks after the initial event — this is the butterfly effect nobody is modeling yet.",
        ]
