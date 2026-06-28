"""
UniversalRunner — Hybrid simulation: mathematical baseline + swarm corrections.

Architecture:
  1. Mathematical runner produces 168-step baseline (timeline_a, timeline_b)
  2. Agent swarm runs 48 steps and produces delta corrections
  3. Swarm deltas are applied to timeline_a (not timeline_b)
  4. Final diff = (math + swarm) - math = true causal effect including agent dynamics

Uncertainty model:
  - Gaussian noise added to each intention (2% std dev, grows with hop)
  - Confidence decays over time (halves around step 140)
  - Each hop reduces confidence by 15%
  - Soft sigmoid clamp replaces hard max(-1, min(1, x))
"""
from __future__ import annotations

import math
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger

from butterfly.simulation.esaa import AgentIntention, ESAAOrchestrator


# ── Soft clamp (sigmoid) ──────────────────────────────────────────────────────

def _soft_clamp(x: float) -> float:
    """
    Sigmoid-based soft clamp. Approaches ±1 asymptotically.
    More realistic than hard max(-1, min(1, x)) — real systems saturate gradually.
    """
    return 2.0 / (1.0 + math.exp(-3.0 * x)) - 1.0


# ── Result model ──────────────────────────────────────────────────────────────

@dataclass
class SimulationResult:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps_completed: int = 0
    agent_count: int = 0
    n_agents: int = 0
    timeline_a: dict = field(default_factory=dict)
    timeline_b: dict = field(default_factory=dict)
    causal_log: list = field(default_factory=list)
    esaa_stats: dict = field(default_factory=dict)
    projection_hash: str = ""
    mode: str = "hybrid"
    duration_seconds: float = 0.0
    predictability_horizon: dict = field(default_factory=dict)

    def get_diff(self) -> dict:
        diff: dict = {}
        for step, snapshot in self.timeline_a.items():
            for var, val in snapshot.items():
                baseline = self.timeline_b.get(step, {}).get(var, 0.0)
                if var not in diff:
                    diff[var] = {}
                diff[var][step] = round(val - baseline, 4)
        return diff

    def model_dump(self) -> dict:
        return {
            "run_id": self.run_id,
            "steps_completed": self.steps_completed,
            "agent_count": self.agent_count,
            "mode": self.mode,
            "esaa_stats": self.esaa_stats,
            "projection_hash_sha256": self.projection_hash,
            "duration_seconds": self.duration_seconds,
            "predictability_horizon": self.predictability_horizon,
        }


# ── Runner ────────────────────────────────────────────────────────────────────

class UniversalRunner:

    async def run(
        self,
        event,
        graph_data: dict,
        steps: int = 168,
        log_path: str | None = None,
        precomputed_dag=None,
        precomputed_cci: dict | None = None,
        **kwargs,
    ) -> SimulationResult:
        """
        Run hybrid simulation: mathematical baseline + swarm corrections.

        Every state change goes through ESAAOrchestrator.
        Swarm deltas are applied as corrections to the math baseline.
        """
        t_start = datetime.utcnow()
        title = getattr(event, "title", "unknown")
        run_id = str(uuid.uuid4())[:8]

        if log_path is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
            os.makedirs(data_dir, exist_ok=True)
            log_path = os.path.join(data_dir, f"activity_{run_id}.jsonl")

        logger.info(f"[RUNNER] Starting hybrid simulation for '{title}' → {log_path}")

        nodes = graph_data.get("nodes", [])
        result = SimulationResult(run_id=run_id)

        if not nodes:
            logger.warning("[RUNNER] No nodes — returning empty simulation")
            result.steps_completed = steps
            return result

        severity_mult = {
            "minor": 0.3, "moderate": 0.6, "major": 0.85, "catastrophic": 1.0
        }
        severity = severity_mult.get(getattr(event, "severity", "moderate"), 0.6)

        # ── Step 1: Mathematical baseline (168 steps) ─────────────────────────
        env_a = {node["id"]: 0.0 for node in nodes}
        orch_a = ESAAOrchestrator(env_a, log_path=log_path)

        timeline_a: dict = {}
        causal_log: list = []

        for step in range(steps):
            intentions = _build_intentions(nodes, step, severity, run_id)
            for intention in intentions:
                accepted = orch_a.submit(intention)
                if accepted and step == intention.step:
                    causal_log.append({
                        "step": step,
                        "variable": intention.variable,
                        "label": next(
                            (n.get("label", intention.variable) for n in nodes if n["id"] == intention.variable),
                            intention.variable,
                        ),
                        "delta": intention.delta,
                        "hop": next(
                            (n.get("hop", 0) for n in nodes if n["id"] == intention.variable),
                            0,
                        ),
                        "accepted": accepted,
                        "reason": intention.reason,
                        "confidence": intention.confidence,
                    })
            timeline_a[step] = {k: round(v, 4) for k, v in orch_a.get_state().items()}

        # Timeline B — counterfactual: no event, flat baseline
        timeline_b = {
            step: {node["id"]: 0.0 for node in nodes}
            for step in range(steps)
        }

        esaa_stats = orch_a.stats()

        # ── Step 2: Agent swarm corrections (12 steps) ────────────────────────
        swarm_agent_count = 0
        try:
            # Use pre-computed DAG/CCI if provided, otherwise compute
            if precomputed_dag is not None and precomputed_cci is not None:
                dag = precomputed_dag
                cci_scores = precomputed_cci
            else:
                from butterfly.causal.dag import DAGBuilder
                from butterfly.causal.cpath import CPathCalculator
                dag = DAGBuilder().build_from_graph_data(graph_data)
                cci_scores = CPathCalculator().calculate(dag, "root")

            swarm_log_path = log_path.replace("activity_", "swarm_")
            from butterfly.simulation.agent_swarm import run_swarm_simulation
            swarm_result = await run_swarm_simulation(
                event=event,
                graph_data=graph_data,
                cci_scores=cci_scores,
                steps=12,
                log_path=swarm_log_path,
                transcript_k=3,
            )
            swarm_agent_count = swarm_result.get("n_agents", 0)

            # Extract swarm deltas from the ESAA log
            swarm_deltas: dict[int, dict[str, float]] = {}
            import json as _json
            if os.path.exists(swarm_log_path):
                with open(swarm_log_path, encoding="utf-8") as _f:
                    for _line in _f:
                        _line = _line.strip()
                        if not _line:
                            continue
                        try:
                            entry = _json.loads(_line)
                            if entry.get("accepted") and entry.get("variable") and entry.get("delta") is not None:
                                s = entry.get("step", 0)
                                v = entry["variable"]
                                d = float(entry["delta"])
                                swarm_deltas.setdefault(s, {}).setdefault(v, 0.0)
                                swarm_deltas[s][v] += d
                        except Exception:
                            pass

            # Dynamic merge weight based on swarm consensus
            # consensus = 1 - (std_dev / max_possible) → 0.1 when chaotic, 0.5 when unanimous
            import statistics as _stats
            all_deltas = []
            for step_deltas in swarm_deltas.values():
                all_deltas.extend(step_deltas.values())

            if len(all_deltas) >= 2:
                std = _stats.stdev(all_deltas)
                consensus = max(0.0, 1.0 - (std / 1.0))  # max delta is 1.0
                SWARM_WEIGHT = round(0.1 + 0.4 * consensus, 3)
            else:
                SWARM_WEIGHT = 0.3  # default when too few samples

            logger.info(f"[RUNNER] Swarm merge weight: {SWARM_WEIGHT} (consensus from {len(all_deltas)} deltas)")
            swarm_steps_applied = 0
            for step in range(min(48, steps)):
                if step in swarm_deltas:
                    for var, delta in swarm_deltas[step].items():
                        if var in timeline_a[step]:
                            current = timeline_a[step][var]
                            corrected = _soft_clamp(current + delta * SWARM_WEIGHT)
                            timeline_a[step][var] = round(corrected, 4)
                            swarm_steps_applied += 1

            # Merge swarm esaa_stats
            swarm_esaa = swarm_result.get("esaa_stats", {})
            esaa_stats = {
                "accepted": esaa_stats.get("accepted", 0) + swarm_esaa.get("accepted", 0),
                "rejected": esaa_stats.get("rejected", 0) + swarm_esaa.get("rejected", 0),
                "swarm_agents": swarm_agent_count,
                "swarm_steps_applied": swarm_steps_applied,
                "transcript_total": swarm_result.get("transcript_total", 0),
            }

            logger.info(
                f"[RUNNER] Swarm applied: {swarm_agent_count} agents, "
                f"{swarm_steps_applied} corrections to timeline_a"
            )

        except Exception as e:
            logger.warning(f"[RUNNER] Swarm correction failed (non-fatal): {e}")
            esaa_stats["swarm_agents"] = 0
            esaa_stats["swarm_steps_applied"] = 0

        # ── Step 3: Predictability horizon ────────────────────────────────────
        max_hop = max((n.get("hop", 0) for n in nodes), default=0)
        # Each hop roughly doubles uncertainty; cap at 168h
        horizon_hours = min(168, 24 * (2 ** max(0, 4 - max_hop)))
        predictability_horizon = {
            "hours": horizon_hours,
            "label": f"t+{horizon_hours}h",
            "max_hop": max_hop,
            "warning": (
                "High confidence — well-established causal mechanisms"
                if max_hop <= 1 else
                "Medium confidence — treat as directional signal"
                if max_hop <= 2 else
                "Low confidence — 3rd/4th order effects are structural signals, not precise predictions"
            ),
        }

        duration = (datetime.utcnow() - t_start).total_seconds()

        logger.info(
            f"[RUNNER] Complete: {steps} steps, {len(nodes)} nodes, "
            f"ESAA accepted={esaa_stats.get('accepted', 0)}, "
            f"swarm_agents={swarm_agent_count}, {duration:.2f}s"
        )

        result.steps_completed = steps
        result.agent_count = swarm_agent_count or len(nodes)
        result.n_agents = swarm_agent_count or len(nodes)
        result.timeline_a = timeline_a
        result.timeline_b = timeline_b
        result.causal_log = causal_log
        result.esaa_stats = esaa_stats
        result.mode = "hybrid" if swarm_agent_count > 0 else "mathematical"
        result.duration_seconds = duration
        result.predictability_horizon = predictability_horizon

        # Seal log with cryptographic projection hash
        from butterfly.simulation.esaa import write_projection_hash
        import json as _json2

        _replay_state: dict[str, float] = {}
        try:
            with open(log_path, encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if not _line:
                        continue
                    _entry = _json2.loads(_line)
                    if _entry.get("accepted") and _entry.get("variable"):
                        _v = _entry["variable"]
                        if _v not in _replay_state:
                            _replay_state[_v] = 0.0
                        _replay_state[_v] = round(
                            _soft_clamp(_replay_state[_v] + _entry["delta"]), 8
                        )
        except Exception as _e:
            logger.warning(f"[RUNNER] Log replay for hash failed: {_e}")
            _replay_state = {k: round(v, 8) for k, v in orch_a.environment.items()}

        projection_hash = write_projection_hash(log_path, _replay_state)
        result.projection_hash = projection_hash
        logger.info(f"[RUNNER] Projection hash sealed: {projection_hash[:16]}...")

        return result


# ── Intention builder — with noise + confidence decay ─────────────────────────

def _build_intentions(
    nodes: list[dict],
    step: int,
    severity: float,
    run_id: str,
) -> list[AgentIntention]:
    """
    Build AgentIntentions for a single simulation step.

    Uncertainty model:
    - Gaussian noise (2% std dev, grows slightly with hop) — honest about stochasticity
    - Confidence decays over time (halves around step 140)
    - Each hop reduces confidence by 15%
    - Soft sigmoid clamp on all values
    """
    intentions: list[AgentIntention] = []

    for node in nodes:
        hop = node.get("hop", 0)
        if hop == 0:
            continue

        peak = hop * 24
        decay = 0.7 ** hop

        if step < peak:
            continue

        if step == peak:
            base_effect = severity * decay

            # Fix 1: Gaussian noise — honest about uncertainty
            noise_std = 0.02 * (1 + hop * 0.01)
            noise = random.gauss(0, noise_std)
            effect = _soft_clamp(base_effect + noise)

            if abs(effect) < 0.01:
                continue

            # Fix 2: Confidence decay over time + hop penalty
            time_decay = math.exp(-0.005 * step)
            hop_penalty = 0.15 * hop
            confidence = round(max(0.05, (1.0 - hop_penalty) * time_decay * severity), 3)

            try:
                intentions.append(AgentIntention(
                    agent_id=f"math_agent_{run_id}",
                    step=step,
                    variable=node["id"],
                    delta=round(effect, 4),
                    direction=1 if effect > 0 else -1,
                    reason=(
                        f"Hop-{hop} effect peaks at t={step}h. "
                        f"Severity={severity:.2f}, decay={decay:.2f}, "
                        f"noise={noise:.4f}, conf={confidence:.3f}."
                    ),
                    confidence=confidence,
                ))
            except Exception:
                pass

        else:
            # Decay phase
            base_current = severity * decay * math.exp(-0.015 * (step - peak))
            base_prev = severity * decay * math.exp(-0.015 * (step - peak - 1))
            base_delta = base_current - base_prev

            # Noise on decay phase too
            noise = random.gauss(0, 0.005 * (1 + hop * 0.005))
            delta = round(_soft_clamp(base_delta + noise), 4)

            if abs(delta) < 0.001:
                continue

            # Confidence decays faster in decay phase
            time_decay = math.exp(-0.005 * step)
            hop_penalty = 0.15 * hop
            confidence = round(max(0.02, (1.0 - hop_penalty) * time_decay * severity * 0.5), 3)

            direction = 1 if delta > 0 else (-1 if delta < 0 else 0)
            try:
                intentions.append(AgentIntention(
                    agent_id=f"math_agent_{run_id}",
                    step=step,
                    variable=node["id"],
                    delta=max(-1.0, min(1.0, delta)),
                    direction=direction,
                    reason=f"Decay at t={step}h (hop={hop}, conf={confidence:.3f}).",
                    confidence=confidence,
                ))
            except Exception:
                pass

    return intentions
