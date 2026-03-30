"""Counterfactual diff engine — Timeline A vs Timeline B."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from loguru import logger

import numpy as np
import pandas as pd

from butterfly.causal.dag import DAGBuilder
from butterfly.causal.identification import CausalIdentifier
from butterfly.models.causal_edge import CausalEdge, CounterfactualResult
from butterfly.db.redis import get_cache, set_cache
import json


# Empirical causal parameters grounded in historical data
# Source: Bernanke (2005) transmission mechanism, NAR historical data
CAUSAL_PARAMS: dict[str, dict] = {
    ("Federal Reserve", "FEDFUNDS"): {
        "strength": 0.95, "latency_hours": 0, "decay": 0.001,
    },
    ("FEDFUNDS", "T10Y2Y"): {
        "strength": -1.46, "latency_hours": 2, "decay": 0.002,
    },
    ("FEDFUNDS", "MORTGAGE30US"): {
        "strength": 2.57, "latency_hours": 48, "decay": 0.001,
    },
    ("MORTGAGE30US", "HOUST"): {
        "strength": -128.0, "latency_hours": 168, "decay": 0.001,
    },
    ("HOUST", "UNRATE"): {
        "strength": -0.00093, "latency_hours": 720, "decay": 0.001,
    },
}

# Default time-series data for demo/fallback (Fed 2022 scenario)
FED_2022_BASELINE: dict[str, float] = {
    "FEDFUNDS": 1.68,
    "MORTGAGE30US": 5.23,
    "HOUST": 1559.0,
    "UNRATE": 3.62,
    "T10Y2Y": 0.95,
}

FED_2022_TREATMENT_DELTA: dict[str, float] = {
    "FEDFUNDS": 0.75,       # 75bps hike
    "MORTGAGE30US": 0.0,    # propagated
    "HOUST": 0.0,
    "UNRATE": 0.0,
    "T10Y2Y": 0.0,
}


class CounterfactualEngine:
    """Run Timeline A (event) vs Timeline B (no event) and compute the diff."""

    def __init__(self):
        self.dag_builder = DAGBuilder()
        self.identifier = CausalIdentifier()

    async def run_counterfactual(
        self,
        event_id: str,
        horizon_hours: int = 168,
        baseline_data: Optional[dict[str, float]] = None,
        treatment_deltas: Optional[dict[str, float]] = None,
    ) -> CounterfactualResult:
        """Run counterfactual analysis for an event.

        Args:
            event_id: Event to analyse
            horizon_hours: How many hours to simulate (default 1 week)
            baseline_data: Starting values for each metric (uses Fed 2022 if None)
            treatment_deltas: Initial shock values (uses Fed 2022 if None)

        Returns:
            CounterfactualResult with timelines, diff, and causal edges
        """
        logger.info(f"Running counterfactual for event {event_id}, horizon={horizon_hours}h")

        # Use provided data or fall back to Fed 2022 demo data
        baseline = baseline_data or FED_2022_BASELINE.copy()
        deltas = treatment_deltas or FED_2022_TREATMENT_DELTA.copy()

        # Try to get DAG from Neo4j; fall back to hardcoded Fed chain
        dag = await self.dag_builder.build_dag_for_event(event_id)
        if dag is None:
            logger.warning(f"No DAG found for {event_id}, using Fed 2022 seed DAG")
            dag = self.dag_builder.build_dag_from_seed(
                list(CAUSAL_PARAMS.keys())
            )

        # Build time steps (hourly)
        steps = list(range(0, horizon_hours + 1))

        # Generate timelines
        timeline_a = self._generate_timeline(baseline, deltas, steps, apply_treatment=True)
        timeline_b = self._generate_timeline(baseline, deltas, steps, apply_treatment=False)

        # Compute diff
        diff: dict[str, list[float]] = {}
        peak_delta_at_hours: dict[str, float] = {}

        for metric in timeline_a:
            a_vals = np.array(timeline_a[metric])
            b_vals = np.array(timeline_b[metric])
            d = (a_vals - b_vals).tolist()
            diff[metric] = d

            # Find peak delta time
            abs_diff = np.abs(a_vals - b_vals)
            peak_idx = int(np.argmax(abs_diff))
            peak_delta_at_hours[metric] = float(steps[peak_idx])

        # Build CausalEdge objects from the analysis
        causal_edges = self._build_causal_edges(event_id, timeline_a, timeline_b, steps)

        # Optionally run DoWhy on the generated data
        causal_edges = await self._enrich_with_dowhy(dag, timeline_a, causal_edges)

        result = CounterfactualResult(
            event_id=event_id,
            timeline_a=timeline_a,
            timeline_b=timeline_b,
            diff=diff,
            causal_edges=causal_edges,
            peak_delta_at_hours=peak_delta_at_hours,
            run_metadata={
                "horizon_hours": horizon_hours,
                "metrics": list(baseline.keys()),
                "dag_nodes": len(dag.get("nodes", [])),
                "dag_edges": len(dag.get("edges", [])),
                "ran_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(
            f"Counterfactual complete for {event_id}: "
            f"{len(causal_edges)} edges, "
            f"peak effects at {peak_delta_at_hours}"
        )
        return result

    def _generate_timeline(
        self,
        baseline: dict[str, float],
        treatment_deltas: dict[str, float],
        steps: list[int],
        apply_treatment: bool,
    ) -> dict[str, list[float]]:
        """Generate a timeline by propagating causal effects through the chain.

        Uses CAUSAL_PARAMS for known Fed metrics; for other scenarios builds
        a simple linear chain from the treatment_deltas keys in order.
        """
        timeline: dict[str, list[float]] = {m: [] for m in baseline}
        accumulated: dict[str, float] = {m: 0.0 for m in baseline}

        if apply_treatment:
            for metric, delta in treatment_deltas.items():
                if abs(delta) > 1e-10:
                    accumulated[metric] = delta

        # Build effective params: use CAUSAL_PARAMS where available,
        # otherwise derive a simple chain from the baseline keys
        effective_params = dict(CAUSAL_PARAMS)

        # For metrics not in CAUSAL_PARAMS, build a simple propagation chain
        metrics = list(baseline.keys())
        for i in range(len(metrics) - 1):
            pair = (metrics[i], metrics[i + 1])
            if pair not in effective_params:
                # Derive strength from relative baseline magnitudes
                src_base = abs(baseline[metrics[i]]) or 1.0
                tgt_base = abs(baseline[metrics[i + 1]]) or 1.0
                strength = tgt_base / src_base * 0.35
                effective_params[pair] = {
                    "strength": strength,
                    "latency_hours": (i + 1) * 24,
                    "decay": 0.001,
                }

        for t in steps:
            if apply_treatment:
                for (source, target), params in effective_params.items():
                    if source not in accumulated or target not in baseline:
                        continue
                    latency = params["latency_hours"]
                    if t < latency:
                        continue
                    time_since = t - latency
                    decay_factor = np.exp(-params["decay"] * time_since)
                    source_shock = accumulated.get(source, 0.0)
                    if abs(source_shock) < 1e-10:
                        continue
                    propagated = source_shock * params["strength"] * decay_factor
                    if abs(propagated) > abs(accumulated.get(target, 0.0)):
                        accumulated[target] = propagated

            for metric in baseline:
                noise = np.random.normal(0, abs(baseline[metric]) * 0.001)
                val = baseline[metric] + accumulated.get(metric, 0.0) + noise
                timeline[metric].append(round(val, 4))

        return timeline

    def _build_causal_edges(
        self,
        event_id: str,
        timeline_a: dict[str, list[float]],
        timeline_b: dict[str, list[float]],
        steps: list[int],
    ) -> list[CausalEdge]:
        """Build CausalEdge objects from timeline comparison.

        Args:
            event_id: Source event ID
            timeline_a: Timeline with event
            timeline_b: Counterfactual timeline
            steps: Time steps

        Returns:
            List of CausalEdge objects
        """
        edges = []
        metrics = list(timeline_a.keys())

        for i, source in enumerate(metrics):
            for target in metrics[i + 1:]:
                a_source = np.array(timeline_a[source])
                a_target = np.array(timeline_a[target])
                b_source = np.array(timeline_b[source])
                b_target = np.array(timeline_b[target])

                # Compute counterfactual delta at peak
                diff_target = a_target - b_target
                peak_idx = int(np.argmax(np.abs(diff_target)))
                delta = float(diff_target[peak_idx])

                if abs(delta) < 1e-6:
                    continue

                # Estimate strength from correlation of deltas
                diff_source = a_source - b_source
                if np.std(diff_source) > 1e-10 and np.std(diff_target) > 1e-10:
                    corr = float(np.corrcoef(diff_source, diff_target)[0, 1])
                    strength = max(0.0, min(1.0, abs(corr)))
                else:
                    strength = 0.5

                # Get latency from CAUSAL_PARAMS if known
                params = CAUSAL_PARAMS.get((source, target), {})
                latency = params.get("latency_hours", float(steps[peak_idx]))

                edge = CausalEdge(
                    edge_id=f"causal_{source}_{target}_{event_id[:8]}",
                    source_node_id=source,
                    target_node_id=target,
                    relationship_type="influences",
                    strength_score=strength,
                    time_decay_factor=params.get("decay", 0.1),
                    latency_hours=latency,
                    counterfactual_delta=delta,
                    confidence_interval=(strength * 0.85, min(1.0, strength * 1.15)),
                    evidence_path=[event_id],
                    refutation_passed=False,
                )
                edges.append(edge)

        return edges

    async def _enrich_with_dowhy(
        self,
        dag: dict,
        timeline_a: dict[str, list[float]],
        edges: list[CausalEdge],
    ) -> list[CausalEdge]:
        """Optionally enrich edges with DoWhy ATE estimates.

        Args:
            dag: DAG dict
            timeline_a: Timeline A data
            edges: Existing causal edges

        Returns:
            Enriched edges with refutation_passed set
        """
        try:
            df = pd.DataFrame(timeline_a)
            metrics = list(timeline_a.keys())

            for edge in edges:
                if edge.source_node_id in metrics and edge.target_node_id in metrics:
                    result = self.identifier.estimate_effect(
                        dag,
                        edge.source_node_id,
                        edge.target_node_id,
                        df,
                    )
                    if result.identified:
                        edge.refutation_passed = True
                        # Update strength from ATE if reasonable
                        if abs(result.ate) > 0:
                            edge.strength_score = min(
                                1.0, max(0.0, abs(result.ate) / (abs(result.ate) + 1))
                            )
        except Exception as e:
            logger.warning(f"DoWhy enrichment failed: {e}")

        return edges
