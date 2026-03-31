"""CausalLogExtractor — turns raw simulation logs into structured causal chains.

Produces SimulationCausalChain: ordered hops with human-readable labels,
causal explanations, domain tags, timing, and confidence scores.
"""

from __future__ import annotations

import time
from collections import defaultdict

from loguru import logger
from pydantic import BaseModel


class CausalHop(BaseModel):
    """One hop in the causal chain — fully human-readable."""

    from_agent: str
    to_variable: str
    label: str           # "Oil prices rise"
    why: str             # "Energy traders price in supply risk and geopolitical uncertainty"
    domain: str          # "Energy", "Finance", "Geopolitics", etc.
    time_label: str      # "Immediate", "2 days later", "1 week later"
    confidence_label: str  # "High", "Medium", "Low"
    mechanism: str
    step_triggered: int
    step_peak: int
    magnitude: float
    persistence: float
    confidence: float


class SimulationCausalChain(BaseModel):
    """Full causal chain extracted from a simulation run."""

    event_title: str
    chains: list[CausalHop]
    feedback_loops: list[list[str]]
    total_hops: int
    peak_effect_step: int
    domain_coverage: list[str]
    extraction_ms: float = 0.0


_VAR_LABELS: dict[str, str] = {
    "oil_price":             "Oil prices rise",
    "oil_supply":            "Oil supply decreases",
    "shipping_disruption":   "Shipping routes disrupted",
    "conflict_intensity":    "Conflict intensity increases",
    "diplomatic_activity":   "Diplomatic activity increases",
    "displacement_count":    "Civilian displacement rises",
    "insurance_premium":     "Insurance premiums spike",
    "interest_rate_delta":   "Interest rates change",
    "interest_rate":         "Interest rates rise",
    "mortgage_rate":         "Mortgage rates rise",
    "housing_starts":        "Housing construction drops",
    "portfolio_exposure":    "Investment portfolios rebalance",
    "bond_yield":            "Bond yields rise",
    "risk_sentiment":        "Market risk sentiment shifts",
    "ai_capability_index":   "AI capability advances",
    "ai_investment_flow":    "AI investment surges",
    "rd_spending":           "R&D spending increases",
    "regulatory_pressure":   "Regulatory pressure builds",
    "tech_employment":       "Tech employment falls",
    "chip_shortage_index":   "Semiconductor shortage worsens",
    "demand_shock":          "Demand shock hits markets",
    "storm_intensity":       "Storm intensity peaks",
    "infrastructure_damage": "Infrastructure is damaged",
    "construction_demand":   "Construction demand surges",
    "emergency_spending":    "Emergency spending rises",
    "insurance_payout":      "Insurance payouts triggered",
    "infection_rate":        "Infection rate rises",
    "hospital_capacity_used":"Hospital capacity strained",
    "mobility_restriction":  "Mobility restrictions imposed",
    "consumer_spending":     "Consumer spending falls",
}

_VAR_DOMAIN_MAP: dict[str, str] = {
    "oil_price": "Energy", "oil_supply": "Energy", "shipping_disruption": "Logistics",
    "conflict_intensity": "Geopolitics", "diplomatic_activity": "Geopolitics",
    "displacement_count": "Humanitarian", "insurance_premium": "Finance",
    "interest_rate_delta": "Finance", "mortgage_rate": "Finance",
    "housing_starts": "Real Estate", "portfolio_exposure": "Finance",
    "bond_yield": "Finance", "risk_sentiment": "Finance",
    "ai_capability_index": "Technology", "ai_investment_flow": "Technology",
    "rd_spending": "Technology", "regulatory_pressure": "Policy",
    "tech_employment": "Labor", "chip_shortage_index": "Technology",
    "storm_intensity": "Climate", "infrastructure_damage": "Infrastructure",
    "construction_demand": "Construction", "emergency_spending": "Government",
    "insurance_payout": "Finance", "infection_rate": "Health",
    "hospital_capacity_used": "Health", "mobility_restriction": "Policy",
    "consumer_spending": "Economy",
}

_VAR_WHY: dict[str, str] = {
    "oil_price":             "Energy traders price in supply risk and geopolitical uncertainty",
    "oil_supply":            "Production disruptions or policy decisions reduce available supply",
    "shipping_disruption":   "Conflict or sanctions force vessels to reroute, raising costs",
    "conflict_intensity":    "Military escalation increases direct risk to people and assets",
    "diplomatic_activity":   "Governments respond to crisis with negotiations and pressure",
    "displacement_count":    "Civilians flee conflict zones, creating humanitarian pressure",
    "insurance_premium":     "Insurers reprice risk exposure in affected regions",
    "interest_rate_delta":   "Central banks adjust rates in response to economic conditions",
    "mortgage_rate":         "Banks pass higher funding costs to borrowers",
    "housing_starts":        "Higher borrowing costs make new construction less viable",
    "portfolio_exposure":    "Investors reduce risk exposure in response to uncertainty",
    "bond_yield":            "Bond markets reprice based on rate expectations",
    "risk_sentiment":        "Market participants shift to defensive positioning",
    "ai_capability_index":   "New AI capabilities unlock previously impossible applications",
    "ai_investment_flow":    "Capital floods into AI infrastructure and startups",
    "rd_spending":           "Companies accelerate R&D to stay competitive",
    "regulatory_pressure":   "Governments respond to disruption with oversight and rules",
    "tech_employment":       "Automation displaces workers in affected sectors",
    "chip_shortage_index":   "Demand outpaces supply for critical semiconductor components",
    "storm_intensity":       "Extreme weather causes direct physical and economic damage",
    "infrastructure_damage": "Physical assets are destroyed or rendered unusable",
    "construction_demand":   "Rebuilding creates surge demand for materials and labor",
    "emergency_spending":    "Government mobilizes disaster relief and recovery funds",
    "insurance_payout":      "Insurers pay out claims, straining capital reserves",
    "infection_rate":        "Pathogen spreads through population via contact",
    "hospital_capacity_used":"Patient surge overwhelms available healthcare capacity",
    "mobility_restriction":  "Governments limit movement to slow disease spread",
    "consumer_spending":     "Uncertainty and restrictions cause households to cut spending",
}


def _infer_domain(variable: str) -> str:
    return _VAR_DOMAIN_MAP.get(variable, "General")


def _step_to_time_label(step: int) -> str:
    if step <= 6:
        return "Immediate (hours)"
    elif step <= 48:
        return f"{step}h later"
    elif step <= 168:
        days = round(step / 24)
        return f"{days} day{'s' if days > 1 else ''} later"
    elif step <= 720:
        weeks = round(step / 168)
        return f"{weeks} week{'s' if weeks > 1 else ''} later"
    else:
        months = round(step / 720)
        return f"{months} month{'s' if months > 1 else ''} later"


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "High"
    elif confidence >= 0.5:
        return "Medium"
    return "Low"


def _mechanism_text(agent_name: str, variable: str, trigger: str) -> str:
    direction = "increased" if ">" in trigger else "changed"
    return f"{agent_name} reacted to {trigger.split('>')[0].strip()} -> {direction} {variable.replace('_', ' ')}"


class CausalLogExtractor:
    DIVERGENCE_THRESHOLD = 0.02
    SIGNIFICANCE_THRESHOLD = 0.01

    def extract(
        self,
        log: list[dict],
        timeline_a: dict[int, dict[str, float]],
        timeline_b: dict[int, dict[str, float]],
        event_title: str = "Unknown Event",
        total_steps: int = 168,
    ) -> SimulationCausalChain:
        t0 = time.perf_counter()
        logger.debug(f"CausalLogExtractor.extract: {len(log)} log entries, {total_steps} steps")

        if not log:
            return SimulationCausalChain(
                event_title=event_title, chains=[], feedback_loops=[],
                total_hops=0, peak_effect_step=0, domain_coverage=[], extraction_ms=0.0,
            )

        var_entries: dict[str, list[dict]] = defaultdict(list)
        for entry in log:
            var = entry.get("variable_changed", "")
            if var:
                var_entries[var].append(entry)
        for var in var_entries:
            var_entries[var].sort(key=lambda e: e["timestep"])

        diff_series = self._compute_diff_series(timeline_a, timeline_b)

        hops: list[CausalHop] = []
        peak_effect_step = 0

        for var, entries in var_entries.items():
            hop = self._build_hop(var, entries, diff_series.get(var, {}), total_steps)
            if hop is not None:
                hops.append(hop)
                if hop.step_peak > peak_effect_step:
                    peak_effect_step = hop.step_peak

        hops.sort(key=lambda h: (h.step_triggered, h.step_peak))
        feedback_loops = self._detect_feedback_loops(hops, var_entries)
        domains = list({_infer_domain(h.to_variable) for h in hops} - {"General"})

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"Extracted {len(hops)} hops, {len(feedback_loops)} loops, {len(domains)} domains in {elapsed_ms:.1f}ms")

        return SimulationCausalChain(
            event_title=event_title, chains=hops, feedback_loops=feedback_loops,
            total_hops=len(hops), peak_effect_step=peak_effect_step,
            domain_coverage=domains, extraction_ms=round(elapsed_ms, 2),
        )

    def _compute_diff_series(self, timeline_a, timeline_b):
        diff: dict[str, dict[int, float]] = defaultdict(dict)
        all_steps = sorted(set(timeline_a.keys()) | set(timeline_b.keys()))
        for step in all_steps:
            snap_a = timeline_a.get(step, {})
            snap_b = timeline_b.get(step, {})
            for var in set(snap_a.keys()) | set(snap_b.keys()):
                d = snap_a.get(var, 0.0) - snap_b.get(var, 0.0)
                if abs(d) > 1e-9:
                    diff[var][step] = d
        return dict(diff)

    def _build_hop(self, variable, entries, diff_series, total_steps):
        if not entries:
            return None
        step_triggered = self._find_divergence_step(variable, entries, diff_series)
        if step_triggered is None:
            return None

        responsible_entry = next((e for e in entries if e["timestep"] >= step_triggered), entries[0])
        agent_name = responsible_entry.get("agent_name", responsible_entry.get("agent_id", "unknown"))
        trigger_fired = responsible_entry.get("trigger_fired", "unknown trigger")

        magnitude = self._compute_magnitude(variable, diff_series)
        step_peak = max(diff_series, key=lambda s: abs(diff_series[s])) if diff_series else step_triggered
        persistence = self._compute_persistence(diff_series, total_steps)
        n_entries = len(entries)
        confidence = min(1.0, 0.4 * min(1.0, n_entries / 10.0) + 0.4 * magnitude + 0.2 * persistence)

        return CausalHop(
            from_agent=agent_name,
            to_variable=variable,
            label=_VAR_LABELS.get(variable, variable.replace("_", " ").title()),
            why=_VAR_WHY.get(variable, f"{agent_name} caused {variable.replace('_', ' ')} to change"),
            domain=_infer_domain(variable),
            time_label=_step_to_time_label(step_triggered),
            confidence_label=_confidence_label(confidence),
            mechanism=_mechanism_text(agent_name, variable, trigger_fired),
            step_triggered=step_triggered,
            step_peak=step_peak,
            magnitude=round(magnitude, 4),
            persistence=round(persistence, 4),
            confidence=round(confidence, 4),
        )

    def _find_divergence_step(self, variable, entries, diff_series):
        if diff_series:
            for step in sorted(diff_series.keys()):
                if abs(diff_series[step]) > self.DIVERGENCE_THRESHOLD:
                    return step
        for entry in entries:
            old_val = entry.get("old_value", 0.0)
            new_val = entry.get("new_value", 0.0)
            delta = abs(new_val - old_val)
            baseline = abs(old_val) if abs(old_val) > 1e-6 else 1.0
            if delta / baseline > self.DIVERGENCE_THRESHOLD:
                return entry["timestep"]
        return None

    def _compute_magnitude(self, variable, diff_series):
        if not diff_series:
            return 0.0
        max_delta = max(abs(d) for d in diff_series.values())
        all_vals = sorted(abs(d) for d in diff_series.values())
        baseline = max(all_vals[len(all_vals) // 2] if all_vals else 1.0, 1e-6)
        return min(1.0, max_delta / (baseline + max_delta))

    def _compute_persistence(self, diff_series, total_steps):
        if not diff_series or total_steps == 0:
            return 0.0
        significant = sum(1 for d in diff_series.values() if abs(d) > self.SIGNIFICANCE_THRESHOLD)
        return min(1.0, significant / total_steps)

    def _detect_feedback_loops(self, hops, var_entries):
        agent_to_vars: dict[str, list[str]] = defaultdict(list)
        for var, entries in var_entries.items():
            for entry in entries:
                agent = entry.get("agent_name", entry.get("agent_id", ""))
                if agent and var not in agent_to_vars[agent]:
                    agent_to_vars[agent].append(var)

        import networkx as nx
        graph: nx.DiGraph = nx.DiGraph()
        hop_vars = {h.to_variable for h in hops}
        for var in hop_vars:
            graph.add_node(var)

        for agent, vars_changed in agent_to_vars.items():
            vars_with_step = [(var_entries[v][0]["timestep"], v) for v in vars_changed if v in hop_vars and var_entries.get(v)]
            vars_with_step.sort()
            for i in range(len(vars_with_step) - 1):
                _, v_from = vars_with_step[i]
                _, v_to = vars_with_step[i + 1]
                if v_from != v_to:
                    graph.add_edge(v_from, v_to, agent=agent)

        try:
            return [c for c in nx.simple_cycles(graph) if len(c) >= 2]
        except Exception:
            return []