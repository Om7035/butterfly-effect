
"""CausalLogExtractor — turns raw simulation logs into structured causal chains.

Takes the causal_log from UniversalModel (list of state-change events) and
produces a SimulationCausalChain: ordered hops, magnitudes, persistence scores,
and detected feedback loops.

Performance target: 10,000 log entries extracted in < 1 second.
Algorithm is O(n log n) — one sort + linear passes per variable.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field


# ── Output models ─────────────────────────────────────────────────────────────


class CausalHop(BaseModel):
    """One hop in the causal chain: agent reaction → variable change."""

    from_agent: str             # agent name that caused this change
    to_variable: str            # environment variable that changed
    mechanism: str              # plain-English description of HOW
    step_triggered: int         # first step where divergence > 2% threshold
    step_peak: int              # step where delta was largest
    magnitude: float            # normalized: |max(A[var]) - max(B[var])| / (|max(B[var])| + ε)
    persistence: float          # fraction of total steps where delta was significant
    confidence: float           # derived from log entry count + magnitude


class SimulationCausalChain(BaseModel):
    """Full causal chain extracted from a simulation run."""

    event_title: str
    chains: list[CausalHop]                     # ordered by step_triggered
    feedback_loops: list[list[str]]             # each inner list is a cycle of variable names
    total_hops: int
    peak_effect_step: int                       # step with the largest single delta
    domain_coverage: list[str]                  # domains touched (inferred from variable names)
    extraction_ms: float = 0.0                  # how long extraction took


# ── Domain inference from variable names ─────────────────────────────────────

_VAR_DOMAIN_MAP: dict[str, str] = {
    "oil_price": "energy", "oil_supply": "energy", "shipping_disruption": "energy",
    "conflict_intensity": "geopolitics", "diplomatic_activity": "geopolitics",
    "displacement_count": "humanitarian", "insurance_premium": "geopolitics",
    "interest_rate_delta": "finance", "mortgage_rate": "finance",
    "housing_starts": "finance", "portfolio_exposure": "finance",
    "bond_yield": "finance", "risk_sentiment": "finance",
    "ai_capability_index": "technology", "ai_investment_flow": "technology",
    "rd_spending": "technology", "regulatory_pressure": "technology",
    "tech_employment": "technology", "chip_shortage_index": "technology",
    "storm_intensity": "climate", "infrastructure_damage": "climate",
    "construction_demand": "climate", "emergency_spending": "climate",
    "insurance_payout": "climate",
    "infection_rate": "health", "hospital_capacity_used": "health",
    "mobility_restriction": "health", "consumer_spending": "health",
}


def _infer_domain(variable: str) -> str:
    return _VAR_DOMAIN_MAP.get(variable, "general")


def _mechanism_text(agent_name: str, variable: str, trigger: str) -> str:
    """Generate a plain-English mechanism description."""
    direction = "increased" if ">" in trigger else "changed"
    return f"{agent_name} reacted to {trigger.split('>')[0].strip()} → {direction} {variable.replace('_', ' ')}"


# ── Main extractor ────────────────────────────────────────────────────────────


class CausalLogExtractor:
    """Extracts structured causal chains from simulation logs.

    Usage:
        extractor = CausalLogExtractor()
        chain = extractor.extract(log, timeline_a, timeline_b, event_title, total_steps)
    """

    # Threshold: A and B must differ by at least this fraction to count as diverged
    DIVERGENCE_THRESHOLD = 0.02
    # Threshold: delta must be at least this fraction of baseline to count as "significant"
    SIGNIFICANCE_THRESHOLD = 0.01

    def extract(
        self,
        log: list[dict],
        timeline_a: dict[int, dict[str, float]],
        timeline_b: dict[int, dict[str, float]],
        event_title: str = "Unknown Event",
        total_steps: int = 168,
    ) -> SimulationCausalChain:
        """Extract a causal chain from simulation logs.

        Args:
            log: Raw causal log from UniversalModel.get_causal_log()
                 Each entry: {agent_id, agent_name, timestep, variable_changed,
                              old_value, new_value, delta, trigger_fired}
            timeline_a: Snapshots from Timeline A (event happens)
                        {step: {variable: value}}
            timeline_b: Snapshots from Timeline B (counterfactual)
                        {step: {variable: value}}
            event_title: Human-readable event title
            total_steps: Total simulation steps (for persistence calculation)

        Returns:
            SimulationCausalChain with ordered hops, feedback loops, and metadata
        """
        t0 = time.perf_counter()
        logger.debug(f"CausalLogExtractor.extract: {len(log)} log entries, {total_steps} steps")

        if not log:
            logger.warning("Empty log — returning empty chain")
            return SimulationCausalChain(
                event_title=event_title,
                chains=[],
                feedback_loops=[],
                total_hops=0,
                peak_effect_step=0,
                domain_coverage=[],
                extraction_ms=0.0,
            )

        # ── Step 1: Group log entries by variable ─────────────────────────────
        # var_entries[variable] = sorted list of log entries that changed it
        var_entries: dict[str, list[dict]] = defaultdict(list)
        for entry in log:
            var = entry.get("variable_changed", "")
            if var:
                var_entries[var].append(entry)

        # Sort each variable's entries by timestep (log is already sorted but be safe)
        for var in var_entries:
            var_entries[var].sort(key=lambda e: e["timestep"])

        # ── Step 2: Compute per-variable diff series from timelines ───────────
        # diff_series[var][step] = A(step, var) - B(step, var)
        diff_series = self._compute_diff_series(timeline_a, timeline_b)

        # ── Step 3: Build one CausalHop per variable that diverged ────────────
        hops: list[CausalHop] = []
        peak_effect_step = 0
        peak_delta_global = 0.0

        for var, entries in var_entries.items():
            hop = self._build_hop(
                variable=var,
                entries=entries,
                diff_series=diff_series.get(var, {}),
                total_steps=total_steps,
            )
            if hop is not None:
                hops.append(hop)
                if hop.step_peak > peak_effect_step:
                    peak_effect_step = hop.step_peak
                    peak_delta_global = hop.magnitude

        # ── Step 4: Sort hops by step_triggered (causal order) ───────────────
        hops.sort(key=lambda h: (h.step_triggered, h.step_peak))

        # ── Step 5: Detect feedback loops via DFS on hop graph ────────────────
        feedback_loops = self._detect_feedback_loops(hops, var_entries)

        # ── Step 6: Infer domain coverage ─────────────────────────────────────
        domains = list({_infer_domain(h.to_variable) for h in hops} - {"general"})

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"Extracted {len(hops)} hops, {len(feedback_loops)} loops, "
            f"{len(domains)} domains in {elapsed_ms:.1f}ms"
        )

        return SimulationCausalChain(
            event_title=event_title,
            chains=hops,
            feedback_loops=feedback_loops,
            total_hops=len(hops),
            peak_effect_step=peak_effect_step,
            domain_coverage=domains,
            extraction_ms=round(elapsed_ms, 2),
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _compute_diff_series(
        self,
        timeline_a: dict[int, dict[str, float]],
        timeline_b: dict[int, dict[str, float]],
    ) -> dict[str, dict[int, float]]:
        """Compute A(t) - B(t) for every variable at every snapshot step.

        Returns:
            {variable: {step: delta}}
        """
        diff: dict[str, dict[int, float]] = defaultdict(dict)
        all_steps = sorted(set(timeline_a.keys()) | set(timeline_b.keys()))

        for step in all_steps:
            snap_a = timeline_a.get(step, {})
            snap_b = timeline_b.get(step, {})
            all_vars = set(snap_a.keys()) | set(snap_b.keys())
            for var in all_vars:
                a_val = snap_a.get(var, 0.0)
                b_val = snap_b.get(var, 0.0)
                d = a_val - b_val
                if abs(d) > 1e-9:
                    diff[var][step] = d

        return dict(diff)

    def _build_hop(
        self,
        variable: str,
        entries: list[dict],
        diff_series: dict[int, float],
        total_steps: int,
    ) -> Optional[CausalHop]:
        """Build a CausalHop for one variable.

        Returns None if the variable never diverged significantly.
        """
        if not entries:
            return None

        # Find first step where A diverges from B by > DIVERGENCE_THRESHOLD
        step_triggered = self._find_divergence_step(variable, entries, diff_series)
        if step_triggered is None:
            # Variable was logged but never diverged from baseline — skip
            return None

        # Find the agent responsible (first entry at or after step_triggered)
        responsible_entry = next(
            (e for e in entries if e["timestep"] >= step_triggered),
            entries[0],
        )
        agent_name = responsible_entry.get("agent_name", responsible_entry.get("agent_id", "unknown"))
        trigger_fired = responsible_entry.get("trigger_fired", "unknown trigger")

        # Magnitude: |max(A[var]) - max(B[var])| / (|max(B[var])| + ε)
        magnitude = self._compute_magnitude(variable, diff_series)

        # Step peak: step with largest absolute delta
        step_peak = step_triggered
        if diff_series:
            step_peak = max(diff_series, key=lambda s: abs(diff_series[s]))

        # Persistence: fraction of steps where |delta| > SIGNIFICANCE_THRESHOLD
        persistence = self._compute_persistence(diff_series, total_steps)

        # Confidence: combination of log entry count, magnitude, persistence
        n_entries = len(entries)
        confidence = min(1.0, (
            0.4 * min(1.0, n_entries / 10.0) +   # more log entries = more confident
            0.4 * magnitude +                      # larger effect = more confident
            0.2 * persistence                      # longer-lasting = more confident
        ))

        return CausalHop(
            from_agent=agent_name,
            to_variable=variable,
            mechanism=_mechanism_text(agent_name, variable, trigger_fired),
            step_triggered=step_triggered,
            step_peak=step_peak,
            magnitude=round(magnitude, 4),
            persistence=round(persistence, 4),
            confidence=round(confidence, 4),
        )

    def _find_divergence_step(
        self,
        variable: str,
        entries: list[dict],
        diff_series: dict[int, float],
    ) -> Optional[int]:
        """Find the first step where A diverges from B by > 2%.

        Strategy:
        1. Check diff_series first (most accurate — uses actual timeline snapshots)
        2. Fall back to log entries if diff_series is empty (variable not in snapshots)
        """
        # Strategy 1: diff_series
        if diff_series:
            for step in sorted(diff_series.keys()):
                delta = diff_series[step]
                if abs(delta) > self.DIVERGENCE_THRESHOLD:
                    return step

        # Strategy 2: log entries — use first entry where delta is non-trivial
        for entry in entries:
            old_val = entry.get("old_value", 0.0)
            new_val = entry.get("new_value", 0.0)
            delta = abs(new_val - old_val)
            baseline = abs(old_val) if abs(old_val) > 1e-6 else 1.0
            if delta / baseline > self.DIVERGENCE_THRESHOLD:
                return entry["timestep"]

        return None

    def _compute_magnitude(
        self,
        variable: str,
        diff_series: dict[int, float],
    ) -> float:
        """Compute normalized magnitude: |max_delta| / (|baseline| + ε).

        Clamped to [0, 1].
        """
        if not diff_series:
            return 0.0

        max_delta = max(abs(d) for d in diff_series.values())
        # Use the median absolute value as baseline proxy
        all_vals = sorted(abs(d) for d in diff_series.values())
        baseline = all_vals[len(all_vals) // 2] if all_vals else 1.0
        baseline = max(baseline, 1e-6)

        raw = max_delta / (baseline + max_delta)  # bounded [0, 1) by construction
        return min(1.0, raw)

    def _compute_persistence(
        self,
        diff_series: dict[int, float],
        total_steps: int,
    ) -> float:
        """Fraction of total steps where |delta| > SIGNIFICANCE_THRESHOLD."""
        if not diff_series or total_steps == 0:
            return 0.0
        significant = sum(
            1 for d in diff_series.values()
            if abs(d) > self.SIGNIFICANCE_THRESHOLD
        )
        return min(1.0, significant / total_steps)

    def _detect_feedback_loops(
        self,
        hops: list[CausalHop],
        var_entries: dict[str, list[dict]],
    ) -> list[list[str]]:
        """Detect feedback loops (A → B → A) using DFS on the hop graph.

        Builds a directed graph: variable → variable (via shared agents).
        Finds all simple cycles.

        Returns:
            List of cycles, each cycle is a list of variable names.
        """
        # Build variable → variable edges:
        # If agent X changed variable A, and agent X also changed variable B later,
        # then A → B (X is the mediator).
        # Also: if variable A's change triggered agent Y, and Y changed variable B → A → B.

        # Map: agent_name → list of variables it changed
        agent_to_vars: dict[str, list[str]] = defaultdict(list)
        for var, entries in var_entries.items():
            for entry in entries:
                agent = entry.get("agent_name", entry.get("agent_id", ""))
                if agent and var not in agent_to_vars[agent]:
                    agent_to_vars[agent].append(var)

        # Build directed graph: var_a → var_b if same agent changed both
        # (var_a changed first → var_b changed later)
        import networkx as nx
        G: nx.DiGraph = nx.DiGraph()

        hop_vars = {h.to_variable for h in hops}
        for var in hop_vars:
            G.add_node(var)

        for agent, vars_changed in agent_to_vars.items():
            # Sort by first occurrence step
            vars_with_step = []
            for var in vars_changed:
                if var in hop_vars and var_entries.get(var):
                    first_step = var_entries[var][0]["timestep"]
                    vars_with_step.append((first_step, var))
            vars_with_step.sort()

            # Add edges in temporal order
            for i in range(len(vars_with_step) - 1):
                _, v_from = vars_with_step[i]
                _, v_to = vars_with_step[i + 1]
                if v_from != v_to:
                    G.add_edge(v_from, v_to, agent=agent)

        # Find all simple cycles (DFS)
        try:
            cycles = list(nx.simple_cycles(G))
            # Filter: only cycles of length >= 2 (A → B → A is length 2)
            meaningful_cycles = [c for c in cycles if len(c) >= 2]
            logger.debug(f"Detected {len(meaningful_cycles)} feedback loops")
            return meaningful_cycles
        except Exception as e:
            logger.warning(f"Cycle detection failed: {e}")
            return []
