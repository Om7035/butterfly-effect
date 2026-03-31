"""InsightGenerator — produces structured, human-readable causal chain output.

Each insight is a structured step with: what happened, why, domain, timing, confidence.
The final output also includes a key insight explaining what is non-obvious.
"""

from __future__ import annotations

from loguru import logger

_SYSTEM_PROMPT = """You are a causal reasoning expert. Given a causal chain from a simulation,
produce a structured analysis that a non-expert can understand immediately.

For each step in the chain, explain:
1. What happened (plain English, not variable names)
2. Why it happened (one sentence causal mechanism)
3. Which domain it belongs to (Economy / Finance / Geopolitics / Energy / Health / Technology / etc.)
4. How long after the original event
5. Confidence level (High / Medium / Low)

Then add a Key Insight: 2-3 sentences explaining what is non-obvious and why it matters.

Return a JSON object with this exact structure:
{
  "steps": [
    {
      "step": 1,
      "what": "Oil prices rise",
      "why": "Energy traders price in supply risk from the conflict zone",
      "domain": "Energy",
      "timing": "Immediate (hours)",
      "confidence": "High"
    }
  ],
  "key_insight": "The non-obvious consequence here is... because..."
}

Rules:
- Use plain English. No jargon.
- "what" must be a complete sentence describing the effect
- "why" must explain the causal mechanism in one sentence
- "domain" must be one of: Economy, Finance, Geopolitics, Energy, Health, Technology, Supply Chain, Policy, Labor, Climate, Infrastructure
- "timing" must be specific: "Immediate (hours)", "1-2 days", "1 week", "2-4 weeks", "1-2 months"
- "confidence" must be: "High", "Medium", or "Low"
- key_insight must explain what most people would miss and why it matters
- Return ONLY valid JSON. No prose, no markdown."""


class InsightGenerator:

    async def generate(self, chain, event) -> list[str]:
        chain_dict = chain.model_dump() if hasattr(chain, "model_dump") else chain
        return await self.generate_from_dict(chain_dict, event)

    async def generate_from_dict(self, chain_dict: dict, event) -> list[str]:
        try:
            from butterfly.llm.providers import llm_complete, extract_json

            prompt = self._build_prompt(chain_dict, event)
            raw = await llm_complete(system=_SYSTEM_PROMPT, user=prompt, max_tokens=1200)
            data = extract_json(raw)

            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")

            steps = data.get("steps", [])
            key_insight = data.get("key_insight", "")

            if not steps:
                raise ValueError("No steps in response")

            # Format as structured strings the frontend can parse
            result = []
            for s in steps[:6]:
                step_num = s.get("step", "?")
                what = s.get("what", "")
                why = s.get("why", "")
                domain = s.get("domain", "")
                timing = s.get("timing", "")
                confidence = s.get("confidence", "")
                if what:
                    result.append(f"STEP:{step_num}|WHAT:{what}|WHY:{why}|DOMAIN:{domain}|TIMING:{timing}|CONFIDENCE:{confidence}")

            if key_insight:
                result.append(f"INSIGHT:{key_insight}")

            logger.info(f"InsightGenerator: {len(steps)} steps + key insight for '{getattr(event, 'title', '?')}'")
            return result

        except Exception as e:
            logger.warning(f"InsightGenerator LLM failed ({e}), using structured fallback")
            return self._structured_fallback(chain_dict, event)

    @staticmethod
    def _build_prompt(chain_dict: dict, event) -> str:
        hops = chain_dict.get("chains", [])
        edges = chain_dict.get("edges", [])
        title = getattr(event, "title", "Unknown Event")
        domains = getattr(event, "domain", []) or chain_dict.get("domain_coverage", [])
        actors = getattr(event, "primary_actors", [])
        severity = getattr(event, "severity", "moderate")

        if hops:
            # Use enriched hop data if available
            hop_lines = []
            for i, h in enumerate(hops[:8]):
                label = h.get("label", h.get("to_variable", "?"))
                why = h.get("why", h.get("mechanism", ""))
                domain = h.get("domain", "")
                timing = h.get("time_label", f"step {h.get('step_triggered', '?')}")
                conf = h.get("confidence_label", f"{h.get('confidence', 0):.0%}")
                hop_lines.append(f"  Step {i+1}: {label} | Why: {why} | Domain: {domain} | Timing: {timing} | Confidence: {conf}")
            chain_text = "\n".join(hop_lines)
        elif edges:
            chain_text = "\n".join(
                f"  Step {i+1}: {e.get('source','?')} -> {e.get('target','?')} (confidence: {e.get('confidence','?')}, latency: {e.get('latency_hours','?')}h)"
                for i, e in enumerate(edges[:8])
            )
        else:
            chain_text = "  No chain data available"

        return f"""Event: {title}
Severity: {severity}
Domains: {', '.join(domains)}
Primary actors: {', '.join(actors[:5]) if actors else 'Unknown'}

Causal chain extracted from simulation:
{chain_text}

Generate a structured step-by-step analysis with a key insight."""

    @staticmethod
    def _structured_fallback(chain_dict: dict, event) -> list[str]:
        """Rule-based fallback producing the same structured format."""
        hops = chain_dict.get("chains", [])
        edges = chain_dict.get("edges", [])
        domains = getattr(event, "domain", []) or ["economics"]
        seeds = getattr(event, "causal_seeds", [])
        title = getattr(event, "title", "this event")

        result = []

        if hops:
            for i, h in enumerate(hops[:5]):
                label = h.get("label", h.get("to_variable", "?").replace("_", " ").title())
                why = h.get("why", h.get("mechanism", f"Caused by {h.get('from_agent', 'upstream event')}"))
                domain = h.get("domain", "Economy")
                timing = h.get("time_label", "Unknown timing")
                confidence = h.get("confidence_label", "Medium")
                result.append(f"STEP:{i+1}|WHAT:{label}|WHY:{why}|DOMAIN:{domain}|TIMING:{timing}|CONFIDENCE:{confidence}")
        elif seeds:
            domain_labels = ["Economy", "Supply Chain", "Finance", "Policy", "Labor"]
            timings = ["Immediate (hours)", "1-2 days", "1-2 weeks", "2-4 weeks", "1-2 months"]
            for i, seed in enumerate(seeds[:5]):
                d = domain_labels[i % len(domain_labels)]
                t = timings[i % len(timings)]
                result.append(f"STEP:{i+1}|WHAT:{seed}|WHY:Downstream effect of {title}|DOMAIN:{d}|TIMING:{t}|CONFIDENCE:Medium")
        else:
            result.append(f"STEP:1|WHAT:Initial shock to {domains[0] if domains else 'affected'} markets|WHY:Direct impact of the event|DOMAIN:Economy|TIMING:Immediate (hours)|CONFIDENCE:High")
            result.append(f"STEP:2|WHAT:Supply chain disruption follows|WHY:Upstream shock propagates through supply networks|DOMAIN:Supply Chain|TIMING:1-2 days|CONFIDENCE:Medium")
            result.append(f"STEP:3|WHAT:Policy response from governments|WHY:Authorities react to stabilize affected systems|DOMAIN:Policy|TIMING:1-2 weeks|CONFIDENCE:Medium")

        # Key insight
        if hops and len(hops) >= 3:
            last = hops[-1]
            last_label = last.get("label", last.get("to_variable", "downstream effects"))
            result.append(f"INSIGHT:The non-obvious consequence is {last_label.lower()} — this appears {last.get('time_label', 'weeks later')} after the original event, long after most analysts have stopped watching. The chain crosses {len(set(h.get('domain', '') for h in hops))} domains, making it invisible to single-domain analysis.")
        else:
            result.append(f"INSIGHT:The key non-obvious effect is that {title} creates cross-domain ripples that most analysts miss because they focus only on the immediate, first-order impact. The downstream effects in {domains[-1] if len(domains) > 1 else 'adjacent sectors'} typically appear 2-4 weeks later.")

        return result