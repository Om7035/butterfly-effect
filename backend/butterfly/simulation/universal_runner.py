"""Universal simulation runner — wraps UniversalModel for parallel A/B execution."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Optional

from loguru import logger

from butterfly.config import settings
from butterfly.simulation._agent_gen import DynamicAgentGenerator
from butterfly.simulation.dynamic_agents import BehaviorProfile
from butterfly.simulation.universal_model import UniversalModel


class UniversalSimulationResult:
    """Result of a universal simulation run."""

    def __init__(
        self,
        run_id: str,
        event_title: str,
        timeline_a: dict[int, dict],
        timeline_b: dict[int, dict],
        causal_log: list[dict],
        steps_completed: int,
        duration_seconds: float,
        n_agents: int,
        agent_types: list[str],
    ) -> None:
        self.run_id = run_id
        self.event_title = event_title
        self.timeline_a = timeline_a
        self.timeline_b = timeline_b
        self.causal_log = causal_log
        self.steps_completed = steps_completed
        self.duration_seconds = duration_seconds
        self.n_agents = n_agents
        self.agent_types = agent_types

    def get_diff(self) -> dict[str, dict[int, float]]:
        """Compute A(t) - B(t) for all environment variables."""
        diff: dict[str, dict[int, float]] = {}
        all_steps = set(self.timeline_a.keys()) | set(self.timeline_b.keys())
        all_vars: set[str] = set()
        for snap in self.timeline_a.values():
            all_vars.update(snap.keys())

        for var in all_vars:
            diff[var] = {}
            for step in sorted(all_steps):
                a_val = self.timeline_a.get(step, {}).get(var, 0.0)
                b_val = self.timeline_b.get(step, {}).get(var, 0.0)
                d = round(a_val - b_val, 4)
                if abs(d) > 1e-6:
                    diff[var][step] = d

        return {k: v for k, v in diff.items() if v}  # drop zero-diff variables

    def diverges_by_step(self, step: int, threshold: float = 0.01) -> bool:
        """Check if timelines have diverged by a given step."""
        diff = self.get_diff()
        for var_diff in diff.values():
            for s, d in var_diff.items():
                if s <= step and abs(d) > threshold:
                    return True
        return False


class UniversalRunner:
    """Runs Timeline A (event) and Timeline B (counterfactual) in parallel."""

    def __init__(self) -> None:
        self.generator = DynamicAgentGenerator()

    async def run(
        self,
        event_title: str,
        event_domains: list[str],
        event_signal: dict,
        steps: int = 168,
        graph_actors: list[dict] | None = None,
        use_llm: bool = False,
    ) -> UniversalSimulationResult:
        """Run a full parallel simulation for any event.

        Args:
            event_title: Plain-text event title
            event_domains: Domain list from UniversalEvent
            event_signal: Dict of environment variable overrides for Timeline A
            steps: Simulation steps (1 step = 1 hour)
            graph_actors: Actor nodes from Neo4j (optional)
            use_llm: Whether to call Claude for profile enrichment

        Returns:
            UniversalSimulationResult with both timelines and causal log
        """
        run_id = f"usim_{uuid.uuid4().hex[:10]}"
        start = time.time()

        # Generate agents (LLM runs once here if enabled)
        profiles = await self.generator.generate_agents(
            event_title=event_title,
            event_domains=event_domains,
            graph_actors=graph_actors,
            use_llm=use_llm,
        )

        n_agents = len(profiles)
        agent_types = list({p.agent_type for p in profiles})
        logger.info(f"[{run_id}] {n_agents} agents, {steps} steps, domains={event_domains}")

        # Run both timelines concurrently in thread pool
        loop = asyncio.get_event_loop()
        a_future = loop.run_in_executor(
            None, self._run_sync, profiles, event_signal, steps, True
        )
        b_future = loop.run_in_executor(
            None, self._run_sync, profiles, None, steps, False
        )

        try:
            (tl_a, log_a), (tl_b, _log_b) = await asyncio.wait_for(
                asyncio.gather(a_future, b_future),
                timeout=settings.simulation_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f"[{run_id}] Simulation timed out")
            raise

        duration = time.time() - start
        logger.info(f"[{run_id}] Complete in {duration:.2f}s")

        return UniversalSimulationResult(
            run_id=run_id,
            event_title=event_title,
            timeline_a=tl_a,
            timeline_b=tl_b,
            causal_log=log_a,
            steps_completed=steps,
            duration_seconds=round(duration, 2),
            n_agents=n_agents,
            agent_types=agent_types,
        )

    @staticmethod
    def _run_sync(
        profiles: list[BehaviorProfile],
        event_signal: dict | None,
        steps: int,
        apply_event: bool,
    ) -> tuple[dict[int, dict], list[dict]]:
        """Run one timeline synchronously (called in thread pool)."""
        model = UniversalModel(
            profiles=profiles,
            event_signal=event_signal if apply_event else None,
        )
        snapshots: dict[int, dict] = {}
        for _ in range(steps):
            model.step()
            step = model.schedule.steps
            # Snapshot every 6 steps to keep memory low
            if step % 6 == 0 or step == steps:
                snapshots[step] = model.get_environment_snapshot()

        return snapshots, model.get_causal_log()
