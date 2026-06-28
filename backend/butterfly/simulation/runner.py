"""Parallel simulation runner — Timeline A vs Timeline B."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable

from loguru import logger

from butterfly.config import settings
from butterfly.models.simulation import SimulationResult
from butterfly.simulation.model import ButterflyModel


class SimulationRunner:
    """Runs two ButterflyModel instances concurrently and returns the diff."""

    async def run_parallel(
        self,
        event_signal: dict,
        steps: int = 168,
        n_market: int = 50,
        n_housing: int = 30,
        n_supply: int = 15,
        n_policy: int = 5,
        progress_cb: Callable[[float], None] | None = None,
    ) -> SimulationResult:
        """Run Timeline A (event) and Timeline B (counterfactual) concurrently.

        Args:
            event_signal: Dict with rate_delta, mortgage_delta, commodity_delta
            steps: Number of simulation steps (hours)
            n_market/n_housing/n_supply/n_policy: Agent counts
            progress_cb: Optional callback(fraction_complete)

        Returns:
            SimulationResult with both timelines and agent logs
        """
        n_total = n_market + n_housing + n_supply + n_policy
        if n_total > settings.max_agents:
            scale = settings.max_agents / n_total
            n_market = max(1, int(n_market * scale))
            n_housing = max(1, int(n_housing * scale))
            n_supply = max(1, int(n_supply * scale))
            n_policy = max(1, int(n_policy * scale))
            logger.warning(f"Agent count scaled to {settings.max_agents} max")

        run_id = f"sim_{uuid.uuid4().hex[:12]}"
        event_id = event_signal.get("event_id", "unknown")
        logger.info(
            f"Starting simulation {run_id}: {n_market+n_housing+n_supply+n_policy} agents, "
            f"{steps} steps"
        )

        start = time.time()

        # Run both timelines in the thread pool (Mesa is synchronous)
        loop = asyncio.get_event_loop()

        a_future = loop.run_in_executor(
            None,
            self._run_sync,
            event_signal, steps, n_market, n_housing, n_supply, n_policy, True,
        )
        b_future = loop.run_in_executor(
            None,
            self._run_sync,
            event_signal, steps, n_market, n_housing, n_supply, n_policy, False,
        )

        try:
            (tl_a, logs_a), (tl_b, logs_b) = await asyncio.wait_for(
                asyncio.gather(a_future, b_future),
                timeout=settings.simulation_timeout_seconds,
            )
        except TimeoutError:
            logger.error(f"Simulation {run_id} timed out after {settings.simulation_timeout_seconds}s")
            raise

        duration = time.time() - start
        logger.info(f"Simulation {run_id} complete in {duration:.1f}s")

        return SimulationResult(
            run_id=run_id,
            event_id=event_id,
            timeline_a=tl_a,
            timeline_b=tl_b,
            agent_logs=logs_a + logs_b,
            steps_completed=steps,
            duration_seconds=round(duration, 2),
            n_agents=n_market + n_housing + n_supply + n_policy,
        )

    @staticmethod
    def _run_sync(
        event_signal: dict,
        steps: int,
        n_market: int,
        n_housing: int,
        n_supply: int,
        n_policy: int,
        apply_event: bool,
    ) -> tuple[dict[int, dict], list[dict]]:
        """Run one timeline synchronously (called in thread pool).

        Returns:
            (timeline_snapshots, agent_logs)
        """
        signal = event_signal if apply_event else {}
        model = ButterflyModel(
            event_signal=signal if signal else None,
            n_market=n_market,
            n_housing=n_housing,
            n_supply=n_supply,
            n_policy=n_policy,
        )

        snapshots: dict[int, dict] = {}
        for _ in range(steps):
            model.step()
            step = model.schedule.steps
            # Store summary snapshot (not every agent to keep memory low)
            dc = model.datacollector.get_model_vars_dataframe()
            if not dc.empty:
                row = dc.iloc[-1].to_dict()
                snapshots[step] = {k: round(float(v), 4) for k, v in row.items()}

        return snapshots, model.agent_logs
