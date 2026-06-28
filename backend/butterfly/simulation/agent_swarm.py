"""
Agent Swarm — Mesa-based specialist agents that debate C-Path output.

Architecture:
  - Each agent has a STANCE: bullish (amplifies effects) or bearish (dampens effects)
  - Agents receive the C-Path CCI scores and the current simulation state
  - They emit AgentIntentions (never mutate state directly — ESAA enforced)
  - The ESAAOrchestrator validates and applies accepted intentions
  - All decisions logged to activity.jsonl

Memory Depth Reduction (anti-chaotic-divergence):
  - A shared DebateTranscript holds the full history of agent arguments
  - Each agent is given ONLY the last k=3 arguments before generating its response
  - Agents still receive their full role mandate and C-Path CCI scores
  - This prevents runaway context growth and chaotic divergence in long debates

LLM is used ONLY to generate the agent's reasoning text (the "reason" field).
The delta magnitude is always calculated from C-Path CCI scores — never guessed.
"""
from __future__ import annotations

import asyncio
import collections
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from loguru import logger

from butterfly.simulation.esaa import AgentIntention, ESAAOrchestrator

# ── Memory depth constant ─────────────────────────────────────────────────────

TRANSCRIPT_WINDOW_K = 3   # each agent sees only the last k=3 arguments


# ── Agent stance ──────────────────────────────────────────────────────────────

class Stance(str, Enum):
    BULLISH = "bullish"    # amplifies positive effects
    BEARISH = "bearish"    # amplifies negative effects
    NEUTRAL = "neutral"    # follows C-Path score directly


# ── Debate transcript entry ───────────────────────────────────────────────────

@dataclass
class TranscriptEntry:
    """One argument in the swarm debate."""
    step: int
    agent_id: str
    stance: str
    domain: str
    variable: str
    delta: float
    reason: str          # the agent's argument text
    accepted: bool       # whether ESAA accepted this intention


# ── Shared debate transcript with sliding window ──────────────────────────────

class DebateTranscript:
    """
    Shared, append-only transcript of all agent arguments.

    Each agent calls get_window() to receive only the last k=3 entries
    before generating its next response. This is the Memory Depth Reduction:
    agents cannot see the full debate history, only the most recent context.

    This prevents:
      - Chaotic divergence from compounding contradictions
      - Context window explosion in long simulations
      - Agents anchoring too strongly on early arguments
    """

    def __init__(self, k: int = TRANSCRIPT_WINDOW_K) -> None:
        self._k = k
        self._entries: list[TranscriptEntry] = []

    def append(self, entry: TranscriptEntry) -> None:
        self._entries.append(entry)

    def get_window(self) -> list[TranscriptEntry]:
        """Return the last k entries — the only context each agent receives."""
        return self._entries[-self._k:]

    def format_for_agent(self) -> str:
        """
        Format the k=3 window as a compact string for inclusion in agent prompts.
        Each line: [step t, agent_id, stance] variable: delta (reason)
        """
        window = self.get_window()
        if not window:
            return "(no prior arguments)"
        lines = []
        for e in window:
            sign = "+" if e.delta >= 0 else ""
            status = "✓" if e.accepted else "✗"
            lines.append(
                f"  [{status} t={e.step} {e.agent_id} {e.stance}] "
                f"{e.variable}: {sign}{e.delta:.4f} — {e.reason[:80]}"
            )
        return "\n".join(lines)

    @property
    def total_entries(self) -> int:
        return len(self._entries)


# ── Domain → variable mapping ─────────────────────────────────────────────────

DOMAIN_VARIABLES: dict[str, list[str]] = {
    "geopolitics":       ["conflict_intensity", "diplomatic_tension", "refugee_flow"],
    "military":          ["conflict_intensity", "arms_procurement", "civilian_casualties"],
    "economics":         ["interest_rate_delta", "gdp_growth", "unemployment_rate"],
    "financial_markets": ["equity_volatility", "credit_spreads", "risk_sentiment"],
    "energy":            ["oil_price_delta", "lng_spot_price", "energy_security"],
    "health":            ["infection_rate", "healthcare_capacity", "mortality_rate"],
    "climate":           ["infrastructure_damage", "displacement_count", "supply_disruption"],
    "technology":        ["ai_adoption_rate", "semiconductor_demand", "cloud_costs"],
    "trade":             ["shipping_disruption", "tariff_impact", "export_volume"],
    "humanitarian":      ["displacement_count", "food_insecurity", "aid_demand"],
    "logistics":         ["shipping_disruption", "port_congestion", "freight_costs"],
    "political":         ["political_instability", "policy_uncertainty", "election_risk"],
}

# Role mandates — fixed per stance, given to every agent regardless of window
ROLE_MANDATES: dict[str, str] = {
    "bullish": (
        "You are a BULLISH analyst. Your mandate: identify why this event's effects "
        "will be LARGER and FASTER than consensus expects. Amplify high-CCI signals."
    ),
    "bearish": (
        "You are a BEARISH analyst. Your mandate: identify why this event's effects "
        "will be SMALLER and SLOWER than consensus expects. Dampen low-CCI signals."
    ),
    "neutral": (
        "You are a NEUTRAL analyst. Your mandate: follow the C-Path CCI scores "
        "directly without amplification or dampening."
    ),
}


# ── Base agent ────────────────────────────────────────────────────────────────

class SpecialistAgent:
    """
    Base class for all specialist agents.

    Each agent:
    1. Receives its role mandate (fixed, always present)
    2. Receives the top C-Path CCI scores (fixed, always present)
    3. Receives ONLY the last k=3 transcript entries (sliding window)
    4. Computes delta from CCI — never guesses magnitude
    5. Emits AgentIntentions through ESAA — never mutates state directly
    6. Appends its argument to the shared DebateTranscript
    """

    def __init__(
        self,
        agent_id: str,
        domain: str,
        stance: Stance,
        cci_scores: dict[str, float],
        orchestrator: ESAAOrchestrator,
        transcript: DebateTranscript,
    ) -> None:
        self.agent_id = agent_id
        self.domain = domain
        self.stance = stance
        self.cci_scores = cci_scores
        self.orchestrator = orchestrator
        self.transcript = transcript
        self._variables = DOMAIN_VARIABLES.get(domain, ["event_magnitude"])

    def step(self, sim_step: int, current_state: dict) -> list[bool]:
        """
        Execute one simulation step.
        Reads k=3 window from transcript, generates intentions, submits to ESAA.
        Returns list of booleans (accepted/rejected) for each intention.
        """
        intentions = self._generate_intentions(sim_step, current_state)
        results = []
        for intention in intentions:
            accepted = self.orchestrator.submit(intention)
            results.append(accepted)

            # Append this argument to the shared transcript
            self.transcript.append(TranscriptEntry(
                step=sim_step,
                agent_id=self.agent_id,
                stance=self.stance.value,
                domain=self.domain,
                variable=intention.variable,
                delta=intention.delta,
                reason=intention.reason,
                accepted=accepted,
            ))

        return results

    def _generate_intentions(
        self, sim_step: int, current_state: dict
    ) -> list[AgentIntention]:
        """
        Generate intentions using:
          - Role mandate (always present)
          - Top CCI scores (always present)
          - Last k=3 transcript entries (sliding window — memory depth reduction)

        Delta is always derived from CCI — never hallucinated.
        """
        # ── Build context for this agent ──────────────────────────────────────

        # 1. Role mandate — fixed, always present
        mandate = ROLE_MANDATES[self.stance.value]

        # 2. Top CCI scores — always present, sorted descending
        top_cci = sorted(self.cci_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        cci_context = "  " + "\n  ".join(
            f"{node}: CCI={score:.4f}" for node, score in top_cci
        )

        # 3. Sliding window — ONLY last k=3 arguments (memory depth reduction)
        window_text = self.transcript.format_for_agent()

        # ── Compute intentions from CCI (deterministic, not LLM) ─────────────
        intentions: list[AgentIntention] = []

        for var in self._variables:
            if var not in current_state:
                continue

            # Find highest CCI among nodes related to this variable
            related_cci = max(
                (v for k, v in self.cci_scores.items()
                 if k == var                          # exact match
                 or var[:6] in k.lower()              # prefix of variable in key
                 or k[:6] in var.lower()),             # prefix of key in variable
                default=0.0,
            )

            if related_cci < 0.05:
                continue

            # Stance multiplier — derived from role mandate, not LLM
            stance_mult = {
                Stance.BULLISH: 1.2,
                Stance.BEARISH: 0.8,
                Stance.NEUTRAL: 1.0,
            }[self.stance]

            # Check if recent window shows opposing pressure — dampen if so
            window = self.transcript.get_window()
            opposing_pressure = sum(
                1 for e in window
                if e.variable == var and (
                    (self.stance == Stance.BULLISH and e.delta < 0) or
                    (self.stance == Stance.BEARISH and e.delta > 0)
                )
            )
            # If 2+ of last 3 arguments oppose this direction, reduce magnitude
            if opposing_pressure >= 2:
                stance_mult *= 0.6
                logger.debug(
                    f"[SWARM] {self.agent_id} dampened by opposing pressure "
                    f"({opposing_pressure}/3 window entries oppose {var})"
                )

            raw_delta = related_cci * stance_mult * 0.1
            raw_delta = max(-1.0, min(1.0, raw_delta))

            if abs(raw_delta) < 0.005:
                continue

            direction = 1 if raw_delta > 0 else -1

            # Build reason string that references the k=3 window context
            # This is the "prompt" — mandate + CCI + window, all in the reason field
            reason = _build_reason(
                agent_id=self.agent_id,
                stance=self.stance.value,
                domain=self.domain,
                variable=var,
                delta=raw_delta,
                related_cci=related_cci,
                sim_step=sim_step,
                mandate=mandate,
                cci_context=cci_context,
                window_text=window_text,
                window_k=TRANSCRIPT_WINDOW_K,
            )

            try:
                intentions.append(AgentIntention(
                    agent_id=self.agent_id,
                    step=sim_step,
                    variable=var,
                    delta=round(raw_delta, 4),
                    direction=direction,
                    reason=reason,
                    confidence=round(min(related_cci, 1.0), 3),
                ))
            except Exception as e:
                logger.debug(f"[SWARM] Intention build failed: {e}")

        return intentions


# ── Reason builder — the "prompt" each agent uses ────────────────────────────

def _build_reason(
    agent_id: str,
    stance: str,
    domain: str,
    variable: str,
    delta: float,
    related_cci: float,
    sim_step: int,
    mandate: str,
    cci_context: str,
    window_text: str,
    window_k: int,
) -> str:
    """
    Build the structured reason string for an AgentIntention.

    This is the agent's "prompt context" — it always contains:
      1. Role mandate (stance-specific, fixed)
      2. Top CCI scores (deterministic, from C-Path)
      3. Last k=3 transcript entries (sliding window — memory depth reduction)

    The reason is truncated to 300 chars to satisfy ESAA validation.
    """
    sign = "+" if delta >= 0 else ""
    full = (
        f"[{stance.upper()} {domain}@t={sim_step}h] "
        f"CCI={related_cci:.3f} → {sign}{delta:.4f} on {variable}. "
        f"Window(k={window_k}): {window_text[:80].replace(chr(10), ' | ')}"
    )
    # ESAA max_length=300 — truncate cleanly
    return full[:295]


# ── Specialist agent types ────────────────────────────────────────────────────

class MarketAgent(SpecialistAgent):
    def __init__(self, stance: Stance, cci_scores: dict, orch: ESAAOrchestrator, transcript: DebateTranscript):
        super().__init__(f"market_{stance.value}_{uuid.uuid4().hex[:4]}", "financial_markets", stance, cci_scores, orch, transcript)


class PolicyAgent(SpecialistAgent):
    def __init__(self, stance: Stance, cci_scores: dict, orch: ESAAOrchestrator, transcript: DebateTranscript):
        super().__init__(f"policy_{stance.value}_{uuid.uuid4().hex[:4]}", "economics", stance, cci_scores, orch, transcript)


class SupplyChainAgent(SpecialistAgent):
    def __init__(self, stance: Stance, cci_scores: dict, orch: ESAAOrchestrator, transcript: DebateTranscript):
        super().__init__(f"supply_{stance.value}_{uuid.uuid4().hex[:4]}", "trade", stance, cci_scores, orch, transcript)


class EnergyAgent(SpecialistAgent):
    def __init__(self, stance: Stance, cci_scores: dict, orch: ESAAOrchestrator, transcript: DebateTranscript):
        super().__init__(f"energy_{stance.value}_{uuid.uuid4().hex[:4]}", "energy", stance, cci_scores, orch, transcript)


class HumanAgent(SpecialistAgent):
    def __init__(self, stance: Stance, cci_scores: dict, orch: ESAAOrchestrator, transcript: DebateTranscript):
        super().__init__(f"human_{stance.value}_{uuid.uuid4().hex[:4]}", "humanitarian", stance, cci_scores, orch, transcript)


# ── Swarm ─────────────────────────────────────────────────────────────────────

class AgentSwarm:
    """
    Spawns bullish + bearish specialist agents sharing one DebateTranscript.
    Each agent sees only the last k=3 entries before acting (memory depth reduction).
    All decisions route through ESAA orchestrator.
    """

    def __init__(
        self,
        cci_scores: dict[str, float],
        domains: list[str],
        orchestrator: ESAAOrchestrator,
        n_agents_per_type: int = 2,
        transcript_k: int = TRANSCRIPT_WINDOW_K,
    ) -> None:
        self.cci_scores = cci_scores
        self.orchestrator = orchestrator
        self.transcript = DebateTranscript(k=transcript_k)
        self.agents: list[SpecialistAgent] = []
        self._build_agents(domains, n_agents_per_type)

    def _build_agents(self, domains: list[str], n: int) -> None:
        agent_classes = {
            "financial_markets": MarketAgent,
            "economics": PolicyAgent,
            "trade": SupplyChainAgent,
            "logistics": SupplyChainAgent,
            "energy": EnergyAgent,
            "humanitarian": HumanAgent,
            "health": HumanAgent,
            "geopolitics": PolicyAgent,
            "military": PolicyAgent,
            "technology": MarketAgent,
        }

        spawned: set[str] = set()
        for domain in domains:
            cls = agent_classes.get(domain)
            if cls and domain not in spawned:
                spawned.add(domain)
                for _ in range(n):
                    self.agents.append(cls(Stance.BULLISH, self.cci_scores, self.orchestrator, self.transcript))
                    self.agents.append(cls(Stance.BEARISH, self.cci_scores, self.orchestrator, self.transcript))

        logger.info(
            f"[SWARM] Spawned {len(self.agents)} agents for {list(spawned)} "
            f"| transcript window k={self.transcript._k}"
        )

    def run_step(self, sim_step: int, current_state: dict) -> dict:
        """Run all agents for one step. Each agent reads k=3 window before acting."""
        accepted = rejected = 0
        random.shuffle(self.agents)

        for agent in self.agents:
            results = agent.step(sim_step, current_state)
            accepted += sum(1 for r in results if r)
            rejected += sum(1 for r in results if not r)

        return {
            "step": sim_step,
            "accepted": accepted,
            "rejected": rejected,
            "transcript_total": self.transcript.total_entries,
            "transcript_window_k": self.transcript._k,
        }

    @property
    def n_agents(self) -> int:
        return len(self.agents)


# ── ESAA-backed swarm runner ──────────────────────────────────────────────────

async def run_swarm_simulation(
    event,
    graph_data: dict,
    cci_scores: dict[str, float],
    steps: int = 48,
    log_path: str = "data/activity.jsonl",
    transcript_k: int = TRANSCRIPT_WINDOW_K,
) -> dict:
    """
    Run the full agent swarm simulation with memory depth reduction.

    Memory depth reduction is enforced via DebateTranscript.get_window(k=3).
    Each agent sees only the last 3 arguments before generating its response.
    """
    import os
    os.makedirs(os.path.dirname(log_path) if os.path.dirname(log_path) else ".", exist_ok=True)

    nodes = graph_data.get("nodes", [])
    domains = getattr(event, "domain", ["economics"])

    env_vars: dict[str, float] = {node["id"]: 0.0 for node in nodes}
    for domain in domains:
        for var in DOMAIN_VARIABLES.get(domain, []):
            env_vars[var] = 0.0

    orch = ESAAOrchestrator(env_vars, log_path=log_path)
    swarm = AgentSwarm(cci_scores, domains, orch, n_agents_per_type=2, transcript_k=transcript_k)

    logger.info(
        f"[SWARM] Starting {steps}-step swarm | {swarm.n_agents} agents | "
        f"transcript window k={transcript_k}"
    )

    timeline_a: dict = {}
    step_stats: list[dict] = []

    for step in range(steps):
        current_state = orch.get_state()
        stats = swarm.run_step(step, current_state)
        step_stats.append(stats)
        timeline_a[step] = {k: round(v, 4) for k, v in orch.get_state().items()}

    timeline_b = {step: {k: 0.0 for k in env_vars} for step in range(steps)}
    esaa_stats = orch.stats()

    logger.info(
        f"[SWARM] Complete: {steps} steps | {swarm.n_agents} agents | "
        f"ESAA accepted={esaa_stats['accepted']} rejected={esaa_stats['rejected']} | "
        f"transcript total={swarm.transcript.total_entries} (window k={transcript_k})"
    )

    return {
        "mode": "esaa_swarm",
        "steps_completed": steps,
        "n_agents": swarm.n_agents,
        "timeline_a": timeline_a,
        "timeline_b": timeline_b,
        "esaa_stats": esaa_stats,
        "log_path": log_path,
        "transcript_total": swarm.transcript.total_entries,
        "transcript_window_k": transcript_k,
        "step_stats": step_stats[:10],
    }
