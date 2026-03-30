
"""Dynamic agent generation system for universal domain simulation.

Replaces hardcoded MarketAgent/HousingAgent/SupplyChainAgent with
domain-agnostic agents whose behavior is parameterized from the knowledge
graph. LLM runs ONCE at setup to generate BehaviorProfiles; agents then
execute pure math at runtime (no LLM calls during simulation).

Design principles:
  - Agents react to environment variables, not to each other directly
  - Influence propagates through a NetworkX graph (not all-to-all)
  - Every state change is logged with: who, what, why, how much
  - 100 agents × 168 steps must complete in < 2 seconds
"""

from __future__ import annotations

import json
import math
import random
import uuid

from loguru import logger
from pydantic import BaseModel, Field

# ── Pydantic models ───────────────────────────────────────────────────────────


class TriggerRule(BaseModel):
    """Condition that activates an agent's reaction."""
    variable: str           # environment variable to watch
    operator: str           # ">" | "<" | "==" | "!=" | ">=" | "<="
    threshold: float
    condition: str = ""     # human-readable description (auto-generated)

    def is_triggered(self, env: dict[str, float]) -> bool:
        val = env.get(self.variable, 0.0)
        match self.operator:
            case ">":
                return val > self.threshold
            case "<":
                return val < self.threshold
            case ">=":
                return val >= self.threshold
            case "<=":
                return val <= self.threshold
            case "==":
                return abs(val - self.threshold) < 1e-6
            case "!=":
                return abs(val - self.threshold) >= 1e-6
            case _:
                return False


class ReactionFn(BaseModel):
    """Mathematical reaction function — no LLM at runtime."""
    target_variable: str    # environment variable this agent changes
    formula: str            # "linear" | "exponential" | "step" | "sigmoid"
    magnitude: float        # base effect size
    direction: int          # +1 increase, -1 decrease
    lag_steps: int = 0      # steps before effect kicks in
    noise_std: float = 0.02 # Gaussian noise added to each application

    def apply(self, current_value: float, step: int, trigger_step: int) -> float:
        """Compute the delta to apply to target_variable."""
        elapsed = step - trigger_step
        if elapsed < self.lag_steps:
            return 0.0

        t = max(0.0, elapsed - self.lag_steps)
        noise = random.gauss(0, self.noise_std)

        match self.formula:
            case "linear":
                delta = self.direction * self.magnitude * (1.0 + noise)
            case "exponential":
                # Decays over time: peak at t=0, fades with half-life ~10 steps
                decay = math.exp(-t / 10.0)
                delta = self.direction * self.magnitude * decay * (1.0 + noise)
            case "step":
                # Immediate jump, then flat
                delta = self.direction * self.magnitude * (1.0 + noise) if t == 0 else 0.0
            case "sigmoid":
                # S-curve: slow start, fast middle, plateau
                s = 1.0 / (1.0 + math.exp(-0.5 * (t - 5)))
                delta = self.direction * self.magnitude * s * (1.0 + noise)
            case _:
                delta = self.direction * self.magnitude * (1.0 + noise)

        return delta


class BehaviorProfile(BaseModel):
    """Complete behavioral specification for one simulation agent."""
    agent_id: str = Field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:8]}")
    agent_name: str
    agent_type: str                         # "nation-state" | "market" | "person" | etc.
    domain: str                             # primary domain: "geopolitics" | "finance" | etc.
    primary_concern: str                    # what this agent optimizes for
    triggers: list[TriggerRule]
    reaction_functions: list[ReactionFn]
    influence_targets: list[str] = Field(default_factory=list)
    reaction_speed_hours: int = 24          # how fast it reacts (maps to lag_steps)
    dampening_factor: float = 0.85          # how fast response fades (0-1)
    initial_state: dict[str, float] = Field(default_factory=dict)


# ── Domain-specific agent templates ──────────────────────────────────────────
# These are pre-built profiles for common agent types.
# DynamicAgentGenerator uses these as defaults when LLM is unavailable.

def _make_profile(
    name: str,
    agent_type: str,
    domain: str,
    concern: str,
    triggers: list[dict],
    reactions: list[dict],
    influence_targets: list[str] | None = None,
    reaction_speed_hours: int = 24,
    dampening_factor: float = 0.85,
) -> BehaviorProfile:
    return BehaviorProfile(
        agent_name=name,
        agent_type=agent_type,
        domain=domain,
        primary_concern=concern,
        triggers=[TriggerRule(**t) for t in triggers],
        reaction_functions=[ReactionFn(**r) for r in reactions],
        influence_targets=influence_targets or [],
        reaction_speed_hours=reaction_speed_hours,
        dampening_factor=dampening_factor,
    )


# ── Template library ──────────────────────────────────────────────────────────

AGENT_TEMPLATES: dict[str, list[BehaviorProfile]] = {

    "geopolitics": [
        _make_profile(
            "Energy Trader", "market", "geopolitics",
            "maximize energy portfolio returns",
            triggers=[{"variable": "conflict_intensity", "operator": ">", "threshold": 0.3,
                       "condition": "conflict_intensity > 0.3"}],
            reactions=[{"target_variable": "oil_price", "formula": "exponential",
                        "magnitude": 8.0, "direction": 1, "lag_steps": 1}],
            reaction_speed_hours=2,
        ),
        _make_profile(
            "OPEC", "organization", "geopolitics",
            "stabilize oil market and member revenues",
            triggers=[{"variable": "oil_price", "operator": "<", "threshold": 70.0,
                       "condition": "oil_price < 70"}],
            reactions=[{"target_variable": "oil_supply", "formula": "step",
                        "magnitude": 0.15, "direction": -1, "lag_steps": 72}],
            reaction_speed_hours=72,
        ),
        _make_profile(
            "Diplomat", "individual", "geopolitics",
            "de-escalate conflict and protect national interests",
            triggers=[{"variable": "conflict_intensity", "operator": ">", "threshold": 0.6,
                       "condition": "conflict_intensity > 0.6"}],
            reactions=[{"target_variable": "diplomatic_activity", "formula": "sigmoid",
                        "magnitude": 0.5, "direction": 1, "lag_steps": 24}],
            reaction_speed_hours=24,
        ),
        _make_profile(
            "Refugee Population", "humanitarian", "geopolitics",
            "seek safety and basic needs",
            triggers=[{"variable": "conflict_intensity", "operator": ">", "threshold": 0.5,
                       "condition": "conflict_intensity > 0.5"}],
            reactions=[{"target_variable": "displacement_count", "formula": "exponential",
                        "magnitude": 50000.0, "direction": 1, "lag_steps": 12}],
            reaction_speed_hours=12,
        ),
        _make_profile(
            "Central Bank (Affected Region)", "organization", "geopolitics",
            "maintain currency stability and inflation control",
            triggers=[{"variable": "oil_price", "operator": ">", "threshold": 90.0,
                       "condition": "oil_price > 90"}],
            reactions=[{"target_variable": "interest_rate", "formula": "step",
                        "magnitude": 0.25, "direction": 1, "lag_steps": 48}],
            reaction_speed_hours=48,
        ),
        _make_profile(
            "Insurance Market", "market", "geopolitics",
            "price geopolitical risk into premiums",
            triggers=[{"variable": "conflict_intensity", "operator": ">", "threshold": 0.4,
                       "condition": "conflict_intensity > 0.4"}],
            reactions=[{"target_variable": "insurance_premium", "formula": "linear",
                        "magnitude": 0.3, "direction": 1, "lag_steps": 6}],
            reaction_speed_hours=6,
        ),
    ],

    "finance": [
        _make_profile(
            "Institutional Investor", "market", "finance",
            "maximize risk-adjusted portfolio returns",
            triggers=[{"variable": "interest_rate_delta", "operator": ">", "threshold": 0.5,
                       "condition": "interest_rate_delta > 0.5"}],
            reactions=[{"target_variable": "portfolio_exposure", "formula": "linear",
                        "magnitude": 0.15, "direction": -1, "lag_steps": 1, "noise_std": 0.03}],
            reaction_speed_hours=2,
        ),
        _make_profile(
            "Mortgage Lender", "organization", "finance",
            "manage mortgage book profitability",
            triggers=[{"variable": "interest_rate_delta", "operator": ">", "threshold": 0.25,
                       "condition": "interest_rate_delta > 0.25"}],
            reactions=[{"target_variable": "mortgage_rate", "formula": "linear",
                        "magnitude": 0.6, "direction": 1, "lag_steps": 2}],
            reaction_speed_hours=48,
        ),
        _make_profile(
            "Homebuilder", "organization", "finance",
            "maximize housing starts and margins",
            triggers=[{"variable": "mortgage_rate", "operator": ">", "threshold": 5.5,
                       "condition": "mortgage_rate > 5.5"}],
            reactions=[{"target_variable": "housing_starts", "formula": "sigmoid",
                        "magnitude": 120.0, "direction": -1, "lag_steps": 3}],
            reaction_speed_hours=72,
        ),
    ],

    "technology": [
        _make_profile(
            "Venture Capitalist", "market", "technology",
            "maximize portfolio returns through early-stage bets",
            triggers=[{"variable": "ai_capability_index", "operator": ">", "threshold": 0.8,
                       "condition": "ai_capability_index > 0.8"}],
            reactions=[{"target_variable": "ai_investment_flow", "formula": "exponential",
                        "magnitude": 2.5, "direction": 1, "lag_steps": 2}],
            reaction_speed_hours=48,
        ),
        _make_profile(
            "Tech Competitor", "organization", "technology",
            "maintain market position against disruptive entrant",
            triggers=[{"variable": "ai_capability_index", "operator": ">", "threshold": 0.7,
                       "condition": "ai_capability_index > 0.7"}],
            reactions=[{"target_variable": "rd_spending", "formula": "step",
                        "magnitude": 0.4, "direction": 1, "lag_steps": 6}],
            reaction_speed_hours=168,
        ),
        _make_profile(
            "Regulator", "organization", "technology",
            "protect public interest and market stability",
            triggers=[{"variable": "ai_capability_index", "operator": ">", "threshold": 0.9,
                       "condition": "ai_capability_index > 0.9"}],
            reactions=[{"target_variable": "regulatory_pressure", "formula": "sigmoid",
                        "magnitude": 0.6, "direction": 1, "lag_steps": 30}],
            reaction_speed_hours=720,
        ),
        _make_profile(
            "Labor Market", "system", "technology",
            "match workers to available jobs",
            triggers=[{"variable": "ai_capability_index", "operator": ">", "threshold": 0.75,
                       "condition": "ai_capability_index > 0.75"}],
            reactions=[{"target_variable": "tech_employment", "formula": "linear",
                        "magnitude": 0.08, "direction": -1, "lag_steps": 12}],
            reaction_speed_hours=336,
        ),
    ],

    "climate": [
        _make_profile(
            "Insurance Company", "organization", "climate",
            "price catastrophic risk and maintain solvency",
            triggers=[{"variable": "storm_intensity", "operator": ">", "threshold": 0.6,
                       "condition": "storm_intensity > 0.6"}],
            reactions=[{"target_variable": "insurance_payout", "formula": "step",
                        "magnitude": 15.0, "direction": 1, "lag_steps": 0}],
            reaction_speed_hours=6,
        ),
        _make_profile(
            "Infrastructure Agency", "organization", "climate",
            "restore critical infrastructure after disaster",
            triggers=[{"variable": "storm_intensity", "operator": ">", "threshold": 0.5,
                       "condition": "storm_intensity > 0.5"}],
            reactions=[{"target_variable": "infrastructure_damage", "formula": "step",
                        "magnitude": 0.7, "direction": 1, "lag_steps": 0}],
            reaction_speed_hours=1,
        ),
        _make_profile(
            "Government Emergency Agency", "organization", "climate",
            "protect lives and coordinate disaster response",
            triggers=[{"variable": "storm_intensity", "operator": ">", "threshold": 0.4,
                       "condition": "storm_intensity > 0.4"}],
            reactions=[{"target_variable": "emergency_spending", "formula": "exponential",
                        "magnitude": 5.0, "direction": 1, "lag_steps": 2}],
            reaction_speed_hours=12,
        ),
        _make_profile(
            "Construction Supply Chain", "system", "climate",
            "supply materials for reconstruction",
            triggers=[{"variable": "infrastructure_damage", "operator": ">", "threshold": 0.5,
                       "condition": "infrastructure_damage > 0.5"}],
            reactions=[{"target_variable": "construction_demand", "formula": "sigmoid",
                        "magnitude": 0.8, "direction": 1, "lag_steps": 24}],
            reaction_speed_hours=168,
        ),
    ],

    "health": [
        _make_profile(
            "Hospital System", "organization", "health",
            "treat patients and maintain capacity",
            triggers=[{"variable": "infection_rate", "operator": ">", "threshold": 0.05,
                       "condition": "infection_rate > 0.05"}],
            reactions=[{"target_variable": "hospital_capacity_used", "formula": "exponential",
                        "magnitude": 0.3, "direction": 1, "lag_steps": 7}],
            reaction_speed_hours=168,
        ),
        _make_profile(
            "Policymaker", "individual", "health",
            "minimize mortality and economic disruption",
            triggers=[{"variable": "infection_rate", "operator": ">", "threshold": 0.1,
                       "condition": "infection_rate > 0.1"}],
            reactions=[{"target_variable": "mobility_restriction", "formula": "step",
                        "magnitude": 0.5, "direction": 1, "lag_steps": 14}],
            reaction_speed_hours=336,
        ),
        _make_profile(
            "General Public", "humanitarian", "health",
            "protect personal health and maintain livelihood",
            triggers=[{"variable": "infection_rate", "operator": ">", "threshold": 0.03,
                       "condition": "infection_rate > 0.03"}],
            reactions=[{"target_variable": "consumer_spending", "formula": "sigmoid",
                        "magnitude": 0.25, "direction": -1, "lag_steps": 3}],
            reaction_speed_hours=72,
        ),
    ],
}

# Emergent agent rules: if these keywords appear in event domain/title → add these agents
EMERGENT_RULES: list[tuple[list[str], BehaviorProfile]] = [
    (["oil", "energy", "opec"], _make_profile(
        "OPEC (Emergent)", "organization", "geopolitics",
        "stabilize oil revenues",
        triggers=[{"variable": "oil_price", "operator": "<", "threshold": 75.0, "condition": "oil_price < 75"}],
        reactions=[{"target_variable": "oil_supply", "formula": "step", "magnitude": 0.1, "direction": -1, "lag_steps": 72}],
    )),
    (["iran", "middle east", "gulf"], _make_profile(
        "Strait of Hormuz Risk (Emergent)", "system", "geopolitics",
        "model chokepoint vulnerability",
        triggers=[{"variable": "conflict_intensity", "operator": ">", "threshold": 0.5, "condition": "conflict_intensity > 0.5"}],
        reactions=[{"target_variable": "shipping_disruption", "formula": "exponential", "magnitude": 0.4, "direction": 1, "lag_steps": 6}],
    )),
    (["semiconductor", "chip", "tsmc"], _make_profile(
        "Semiconductor Supply Chain (Emergent)", "system", "technology",
        "supply chips to downstream industries",
        triggers=[{"variable": "demand_shock", "operator": ">", "threshold": 0.3, "condition": "demand_shock > 0.3"}],
        reactions=[{"target_variable": "chip_shortage_index", "formula": "sigmoid", "magnitude": 0.6, "direction": 1, "lag_steps": 48}],
    )),
    (["fed", "federal reserve", "interest rate", "fomc"], _make_profile(
        "Bond Market (Emergent)", "market", "finance",
        "price interest rate risk",
        triggers=[{"variable": "interest_rate_delta", "operator": ">", "threshold": 0.25, "condition": "interest_rate_delta > 0.25"}],
        reactions=[{"target_variable": "bond_yield", "formula": "linear", "magnitude": 0.8, "direction": 1, "lag_steps": 1}],
    )),
]


# ── DynamicAgentGenerator ─────────────────────────────────────────────────────


class DynamicAgentGenerator:
    """Generates BehaviorProfiles for any event domain.

    Strategy:
    1. Map event domains to template agent pools
    2. Add emergent agents implied by event keywords
    3. If Anthropic API key is set, enrich profiles with LLM (once per run)
    4. Return deduplicated list of BehaviorProfiles
    """

    async def generate_agents(
        self,
        event_title: str,
        event_domains: list[str],
        graph_actors: list[dict] | None = None,
        use_llm: bool = False,
    ) -> list[BehaviorProfile]:
        """Generate agents for an event.

        Args:
            event_title: Plain-text event title
            event_domains: List of domain strings from UniversalEvent
            graph_actors: Actor nodes from Neo4j (optional enrichment)
            use_llm: Whether to call Claude for profile enrichment

        Returns:
            List of BehaviorProfiles, deduplicated by agent_name
        """
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

        # 3. Graph-derived agents (from Neo4j Actor nodes)
        if graph_actors:
            for actor in graph_actors[:10]:  # cap at 10 to avoid explosion
                name = actor.get("name", "Unknown Actor")
                if name not in seen_names:
                    profile = self._profile_from_actor(actor, event_domains)
                    profiles.append(profile)
                    seen_names.add(name)

        # 4. LLM enrichment (optional, runs once)
        if use_llm and profiles:
            try:
                profiles = await self._enrich_with_llm(profiles, event_title, event_domains)
            except Exception as e:
                logger.warning(f"LLM enrichment failed, using templates: {e}")

        # Ensure at least 3 agents
        if len(profiles) < 3:
            profiles.extend(self._fallback_agents(event_domains))

        logger.info(f"Generated {len(profiles)} agents for '{event_title}'")
        return profiles

    @staticmethod
    def _map_domain(domain: str) -> str:
        """Map universal domain string to template key."""
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
        """Create a minimal BehaviorProfile from a Neo4j Actor node."""
        actor_type = actor.get("type", "organization")
        domain = domains[0] if domains else "finance"
        domain_key = DynamicAgentGenerator._map_domain(domain)

        # Pick a sensible default trigger/reaction based on domain
        default_var = {
            "geopolitics": "conflict_intensity",
            "finance": "interest_rate_delta",
            "technology": "ai_capability_index",
            "climate": "storm_intensity",
            "health": "infection_rate",
        }.get(domain_key, "event_magnitude")

        return BehaviorProfile(
            agent_name=actor.get("name", "Unknown"),
            agent_type=actor_type,
            domain=domain,
            primary_concern=f"Respond to {domain} event",
            triggers=[TriggerRule(
                variable=default_var, operator=">", threshold=0.3,
                condition=f"{default_var} > 0.3",
            )],
            reaction_functions=[ReactionFn(
                target_variable=f"{actor.get('name', 'actor').lower().replace(' ', '_')}_response",
                formula="linear", magnitude=0.2, direction=1, lag_steps=2,
            )],
            reaction_speed_hours=48,
            dampening_factor=0.85,
        )

    @staticmethod
    def _fallback_agents(domains: list[str]) -> list[BehaviorProfile]:
        """Return generic fallback agents when templates are insufficient."""
        return [
            _make_profile(
                "Market Sentiment", "market", domains[0] if domains else "general",
                "reflect aggregate market expectations",
                triggers=[{"variable": "event_magnitude", "operator": ">", "threshold": 0.2,
                           "condition": "event_magnitude > 0.2"}],
                reactions=[{"target_variable": "risk_sentiment", "formula": "exponential",
                            "magnitude": 0.3, "direction": -1, "lag_steps": 1}],
            ),
        ]

    async def _enrich_with_llm(
        self,
        profiles: list[BehaviorProfile],
        event_title: str,
        domains: list[str],
    ) -> list[BehaviorProfile]:
        """Call Claude once to enrich profiles with domain-specific parameters."""
        try:
            import anthropic

            from butterfly.config import settings

            if not settings.anthropic_api_key:
                return profiles

            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

            schema = {
                "agent_name": "string",
                "primary_concern": "string",
                "triggers": [{"variable": "str", "operator": "str", "threshold": 0.0, "condition": "str"}],
                "reaction_functions": [{"target_variable": "str", "formula": "linear|exponential|step|sigmoid",
                                        "magnitude": 0.0, "direction": 1, "lag_steps": 0}],
                "reaction_speed_hours": 24,
                "dampening_factor": 0.85,
            }

            prompt = f"""Event: "{event_title}"
Domains: {domains}
Existing agents: {[p.agent_name for p in profiles]}

For each agent, return a JSON array of enriched BehaviorProfiles.
Each profile must follow this schema exactly:
{json.dumps(schema, indent=2)}

Rules:
- magnitude values must be realistic for the domain (e.g. oil price moves in $1-20 range)
- lag_steps should reflect real-world reaction times (1 step = 1 hour)
- Only use formula values: linear, exponential, step, sigmoid
- Return ONLY valid JSON array, no explanation"""

            message = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = message.content[0].text.strip()
            # Extract JSON array
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                enriched_data = json.loads(raw[start:end])
                enriched: list[BehaviorProfile] = []
                for i, data in enumerate(enriched_data):
                    if i < len(profiles):
                        try:
                            # Merge LLM data into existing profile
                            merged = profiles[i].model_copy(update={
                                "primary_concern": data.get("primary_concern", profiles[i].primary_concern),
                                "triggers": [TriggerRule(**t) for t in data.get("triggers", [])] or profiles[i].triggers,
                                "reaction_functions": [ReactionFn(**r) for r in data.get("reaction_functions", [])] or profiles[i].reaction_functions,
                                "reaction_speed_hours": data.get("reaction_speed_hours", profiles[i].reaction_speed_hours),
                                "dampening_factor": data.get("dampening_factor", profiles[i].dampening_factor),
                            })
                            enriched.append(merged)
                        except Exception:
                            enriched.append(profiles[i])
                    else:
                        enriched.append(profiles[i])
                return enriched

        except Exception as e:
            logger.warning(f"LLM enrichment error: {e}")

        return profiles
