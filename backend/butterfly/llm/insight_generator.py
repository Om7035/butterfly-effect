"""
InsightGenerator — uses LLM to generate non-obvious insights from causal chain.
Falls back to mathematical insights derived from C-Path scores when LLM fails.
"""
from __future__ import annotations

import json

from loguru import logger

from butterfly.config import settings


class InsightGenerator:

    async def generate(self, chain, event) -> list[dict]:
        """
        Generate 3 non-obvious insights from the causal chain.
        Prioritises 3rd and 4th order butterfly effects.
        """
        prompt = self._build_prompt(chain, event)

        # Try LLM first
        result = await self._llm_insights(prompt)
        if result:
            return result

        # Fallback: derive from chain structure
        return self._structural_insights(chain, event)

    async def generate_from_dict(self, chain_dict: dict, event) -> list[dict]:
        """Alias accepting a plain dict (from orchestrator). Converts to CausalChain-like object."""
        from types import SimpleNamespace
        from butterfly.causal.cpath import CascadePath

        # Reconstruct a minimal chain-like object from the dict
        hops_raw = chain_dict.get("hops", [])
        butterfly_raw = chain_dict.get("butterfly_effects", [])

        class _Hop:
            def __init__(self, d):
                self.from_label = d.get("from_label", "")
                self.to_label = d.get("to_label", "")
                self.relationship = d.get("relationship", "INFLUENCES")
                self.latency_hours = d.get("latency_hours", 24)
                self.confidence = d.get("confidence", 0.5)
                self.cci_score = d.get("cci_score", 0.0)
                self.is_butterfly_effect = d.get("is_butterfly_effect", False)

        class _Butterfly:
            def __init__(self, d):
                self.node_label = d.get("node_label", "")
                self.hop_count = d.get("hop_count", 3)
                self.cci_score = d.get("cci_score", 0.0)
                self.estimated_latency_hours = d.get("estimated_latency_hours", 72)

        chain = SimpleNamespace(
            event_title=chain_dict.get("event_title", getattr(event, "title", "")),
            total_hops=chain_dict.get("total_hops", len(hops_raw)),
            hops=[_Hop(h) for h in hops_raw],
            butterfly_effects=[_Butterfly(b) for b in butterfly_raw],
            domain_coverage=chain_dict.get("domain_coverage", []),
            cpath_ranking=chain_dict.get("cpath_ranking", []),
        )
        return await self.generate(chain, event)

    def _build_prompt(self, chain, event) -> str:
        hops_text = ""
        if hasattr(chain, "hops") and chain.hops:
            lines = [
                f"  {h.from_label} → {h.to_label} "
                f"(confidence={h.confidence:.2f}, latency={h.latency_hours}h, "
                f"CCI={h.cci_score:.2f})"
                for h in chain.hops[:8]
            ]
            hops_text = "\n".join(lines)

        butterfly_text = ""
        if hasattr(chain, "butterfly_effects") and chain.butterfly_effects:
            lines = [
                f"  - {p.node_label} (hop {p.hop_count}, CCI={p.cci_score:.2f}, "
                f"~{p.estimated_latency_hours}h)"
                for p in chain.butterfly_effects[:5]
            ]
            butterfly_text = "\n".join(lines)

        return f"""You are a geopolitical and systems analyst specializing in non-obvious cascade effects.

Event: {getattr(event, 'title', 'Unknown')}
Domains: {', '.join(getattr(event, 'domain', []))}
Severity: {getattr(event, 'severity', 'unknown')}
Primary actors: {', '.join(getattr(event, 'primary_actors', [])[:5])}

Causal chain ({getattr(chain, 'total_hops', 0)} hops):
{hops_text or '  (no hops)'}

Non-obvious butterfly effects (3+ hops):
{butterfly_text or '  (none identified yet)'}

Generate exactly 3 insights. Each must:
1. Name SPECIFIC actors, countries, or sectors — no vague categories
2. Include TIMING — "within 6 weeks", "3-6 months"
3. Explain the MECHANISM — why does this causal link exist?
4. Flag the ORDER — 2nd, 3rd, or 4th order?
5. Be SURPRISING — what would an analyst miss from headlines alone?

Return ONLY a JSON array of exactly 3 objects:
[
  {{
    "order": 2,
    "hop": 2,
    "text": "Concise 1-2 sentence description of the effect",
    "why": "2-3 sentences explaining the mechanism and why it's non-obvious",
    "confidence": 0.75,
    "sources": ["Source 1", "Source 2"]
  }}
]"""

    async def _llm_insights(self, prompt: str) -> list[dict] | None:
        try:
            from butterfly.llm.providers import llm_complete
            raw = await llm_complete(
                system="You are a systems analyst. Return only valid JSON arrays.",
                user=prompt,
                max_tokens=2048,
            )

            # Strip fences
            text = raw.strip()
            if text.startswith("```"):
                import re
                text = re.sub(r"^```(?:json)?\s*\n?", "", text)
                text = re.sub(r"\n?```\s*$", "", text)
                text = text.strip()

            data = json.loads(text)
            if isinstance(data, list) and len(data) > 0:
                # Normalise fields
                normalised = []
                for item in data[:4]:
                    normalised.append({
                        "order": int(item.get("order", 2)),
                        "hop": int(item.get("hop", item.get("order", 2))),
                        "text": str(item.get("text", "")),
                        "why": str(item.get("why", "")),
                        "confidence": float(item.get("confidence", 0.65)),
                        "sources": list(item.get("sources", [])),
                    })
                logger.info(f"[INSIGHTS] LLM generated {len(normalised)} insights")
                return normalised
        except Exception as e:
            logger.warning(f"[INSIGHTS] LLM failed: {e}")
        return None

    def _structural_insights(self, chain, event) -> list[dict]:
        """Derive insights from chain structure — no LLM needed."""
        insights: list[dict] = []
        domain = getattr(event, "domain", ["economics"])
        hops = getattr(chain, "hops", [])
        butterfly = getattr(chain, "butterfly_effects", [])

        # 1st insight — immediate first-order effect
        if hops:
            h = hops[0]
            insights.append({
                "order": 1,
                "hop": 1,
                "text": (
                    f"Immediate: {h.to_label} is directly impacted within "
                    f"{h.latency_hours} hours of {getattr(event, 'title', 'the event')}."
                ),
                "why": (
                    f"The {h.relationship} mechanism activates immediately. "
                    f"{h.to_label} is the first structural vulnerability exposed. "
                    f"This is the obvious first-order effect most analysts track."
                ),
                "confidence": h.confidence,
                "sources": [f"{domain[0].title()} sector data" if domain else "Domain data"],
            })

        # 2nd insight — cross-domain second-order
        second_order = [h for h in hops if not h.is_butterfly_effect and h.latency_hours > 48]
        if second_order:
            h = second_order[0]
            insights.append({
                "order": 2,
                "hop": 2,
                "text": (
                    f"2nd order: {h.to_label} disrupted within "
                    f"{h.latency_hours // 24} days as {h.from_label} shifts."
                ),
                "why": (
                    f"Cross-domain transmission from {domain[0] if domain else 'primary'} "
                    f"to {domain[1] if len(domain) > 1 else 'secondary'} domain. "
                    f"Sector-specific analysts miss this because they stop at the first hop."
                ),
                "confidence": round(h.confidence * 0.85, 2),
                "sources": [f"{d.title()} analysis" for d in domain[:2]],
            })

        # 3rd insight — butterfly effect (3+ hops)
        if butterfly:
            b = butterfly[0]
            insights.append({
                "order": b.hop_count,
                "hop": b.hop_count,
                "text": (
                    f"{b.hop_count}th order (non-obvious): {b.node_label} — "
                    f"CCI score {b.cci_score:.2f}, ~{b.estimated_latency_hours}h latency."
                ),
                "why": (
                    f"This is the true butterfly effect. The causal chain crosses "
                    f"{len(domain)} domains over {b.hop_count} hops. "
                    f"CCI score {b.cci_score:.2f} means this is strongly caused, not just correlated. "
                    f"Invisible without graph analysis."
                ),
                "confidence": round(b.cci_score * 0.7, 2),
                "sources": [f"{g} regional data" for g in getattr(event, "geographic_scope", ["Global"])[:2]],
            })
        elif len(hops) >= 3:
            h = hops[-1]
            insights.append({
                "order": 3,
                "hop": 3,
                "text": (
                    f"3rd order: {h.to_label} — the non-obvious downstream effect "
                    f"manifesting ~{h.latency_hours}h after the initial event."
                ),
                "why": (
                    "By the time this effect manifests, most analysts have stopped tracking. "
                    "The causal chain is long but traceable through the graph."
                ),
                "confidence": round(h.confidence * 0.6, 2),
                "sources": ["Causal graph analysis", "Historical precedent"],
            })

        # Ensure we always return at least 1 insight
        if not insights:
            insights.append({
                "order": 1,
                "hop": 1,
                "text": f"Analysis of '{getattr(event, 'title', 'event')}' is in progress.",
                "why": "Causal chain is being computed. More data needed for non-obvious insights.",
                "confidence": 0.5,
                "sources": [],
            })

        return insights
