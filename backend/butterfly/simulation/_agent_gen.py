"""DynamicAgentGenerator — appended separately due to file size limits."""

from __future__ import annotations

import json

from loguru import logger

from butterfly.simulation.dynamic_agents import (
    AGENT_TEMPLATES,
    EMERGENT_RULES,
    BehaviorProfile,
    ReactionFn,
    TriggerRule,
    _make_profile,
)


class DynamicAgentGenerator:
    """Generates BehaviorProfiles for any event domain."""

    async def generate_agents(
        self,
        event_title: str,
        event_domains: list[str],
        graph_actors: list[dict] | None = None,
        use_llm: bool = False,
    ) -> list[BehaviorProfile]:
        profiles: list[BehaviorProfile] = []
        seen_names: set[str] = set()

        # 1. Template agents from domain mapping
        for domain in event_domains:
            domain_key = self._map_domain(domain)
            for template in AGENT_TEMPLATES.get(domain_key, []):
                if template.agent_name not in seen_names:
                    profiles.append(template.model_copy(deep=True))
                    seen_names.add(template.agent_name)

        # 2. Emergent agents from keyword matching
        title_lower = event_title.lower()
        for keywords, emergent_profile in EMERGENT_RULES:
            if any(kw in title_lower for kw in keywords):
                if emergent_profile.agent_name not in seen_names:
                    profiles.append(emergent_profile.model_copy(deep=True))
                    seen_names.add(emergent_profile.agent_name)

        # 3. Graph-derived agents
        if graph_actors:
            for actor in graph_actors[:10]:
                name = actor.get("name", "Unknown Actor")
                if name not in seen_names:
                    profiles.append(self._profile_from_actor(actor, event_domains))
                    seen_names.add(name)

        # 4. LLM enrichment (optional)
        if use_llm and profiles:
            try:
                profiles = await self._enrich_with_llm(profiles, event_title, event_domains)
            except Exception as e:
                logger.warning(f"LLM enrichment failed: {e}")

        if len(profiles) < 3:
            profiles.extend([
                _make_profile(
                    "Market Sentiment", "market", event_domains[0] if event_domains else "general",
                    "reflect aggregate market expectations",
                    triggers=[{"variable": "event_magnitude", "operator": ">", "threshold": 0.2,
                               "condition": "event_magnitude > 0.2"}],
                    reactions=[{"target_variable": "risk_sentiment", "formula": "exponential",
                                "magnitude": 0.3, "direction": -1, "lag_steps": 1}],
                ),
            ])

        logger.info(f"Generated {len(profiles)} agents for '{event_title}'")
        return profiles

    @staticmethod
    def _map_domain(domain: str) -> str:
        mapping = {
            "geopolitics": "geopolitics", "military": "geopolitics",
            "humanitarian": "geopolitics", "political": "geopolitics",
            "economics": "finance", "financial_markets": "finance",
            "trade": "finance", "energy": "geopolitics",
            "technology": "technology", "digital": "technology",
            "climate": "climate", "environment": "climate",
            "health": "health", "pandemic": "health",
        }
        return mapping.get(domain.lower(), "finance")

    @staticmethod
    def _profile_from_actor(actor: dict, domains: list[str]) -> BehaviorProfile:
        actor_type = actor.get("type", "organization")
        domain = domains[0] if domains else "finance"
        domain_key = DynamicAgentGenerator._map_domain(domain)
        default_var = {
            "geopolitics": "conflict_intensity", "finance": "interest_rate_delta",
            "technology": "ai_capability_index", "climate": "storm_intensity",
            "health": "infection_rate",
        }.get(domain_key, "event_magnitude")
        return BehaviorProfile(
            agent_name=actor.get("name", "Unknown"),
            agent_type=actor_type,
            domain=domain,
            primary_concern=f"Respond to {domain} event",
            triggers=[TriggerRule(variable=default_var, operator=">", threshold=0.3,
                                  condition=f"{default_var} > 0.3")],
            reaction_functions=[ReactionFn(
                target_variable=f"{actor.get('name', 'actor').lower().replace(' ', '_')}_response",
                formula="linear", magnitude=0.2, direction=1, lag_steps=2,
            )],
            reaction_speed_hours=48,
            dampening_factor=0.85,
        )

    async def _enrich_with_llm(
        self, profiles: list[BehaviorProfile], event_title: str, domains: list[str]
    ) -> list[BehaviorProfile]:
        try:
            import anthropic

            from butterfly.config import settings
            if not settings.anthropic_api_key:
                return profiles
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            schema = {"agent_name": "str", "primary_concern": "str",
                      "triggers": [{"variable": "str", "operator": "str", "threshold": 0.0, "condition": "str"}],
                      "reaction_functions": [{"target_variable": "str", "formula": "linear|exponential|step|sigmoid",
                                              "magnitude": 0.0, "direction": 1, "lag_steps": 0}],
                      "reaction_speed_hours": 24, "dampening_factor": 0.85}
            prompt = (f'Event: "{event_title}"\nDomains: {domains}\n'
                      f'Agents: {[p.agent_name for p in profiles]}\n'
                      f'Return JSON array of enriched BehaviorProfiles matching schema:\n'
                      f'{json.dumps(schema)}\nReturn ONLY valid JSON array.')
            msg = await client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            start, end = raw.find("["), raw.rfind("]") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                enriched = []
                for i, d in enumerate(data):
                    if i < len(profiles):
                        try:
                            enriched.append(profiles[i].model_copy(update={
                                "primary_concern": d.get("primary_concern", profiles[i].primary_concern),
                                "triggers": [TriggerRule(**t) for t in d.get("triggers", [])] or profiles[i].triggers,
                                "reaction_functions": [ReactionFn(**r) for r in d.get("reaction_functions", [])] or profiles[i].reaction_functions,
                                "reaction_speed_hours": d.get("reaction_speed_hours", profiles[i].reaction_speed_hours),
                                "dampening_factor": d.get("dampening_factor", profiles[i].dampening_factor),
                            }))
                        except Exception:
                            enriched.append(profiles[i])
                    else:
                        enriched.append(profiles[i])
                return enriched
        except Exception as e:
            logger.warning(f"LLM enrichment error: {e}")
        return profiles
