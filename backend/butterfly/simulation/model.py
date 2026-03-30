"""Mesa ButterflyModel — runs one timeline (A or B)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mesa import Model
from mesa.datacollection import DataCollector
from mesa.time import RandomActivation

from butterfly.simulation.agents import (
    HousingAgent,
    MarketAgent,
    PolicyAgent,
    SupplyChainAgent,
)


class ButterflyModel(Model):
    """ABM model for one simulation timeline.

    If event_signal is provided this is Timeline A (event happens).
    If event_signal is None this is Timeline B (counterfactual baseline).
    """

    def __init__(
        self,
        event_signal: dict | None = None,
        n_market: int = 50,
        n_housing: int = 30,
        n_supply: int = 15,
        n_policy: int = 5,
        progress_cb: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__()
        self.event_signal = event_signal
        self.progress_cb = progress_cb

        # Extract event deltas (zero for Timeline B)
        self.rate_delta: float = 0.0
        self.mortgage_delta: float = 0.0
        self.commodity_delta: float = 0.0

        if event_signal:
            self.rate_delta = float(event_signal.get("rate_delta", 0.0))
            self.mortgage_delta = float(event_signal.get("mortgage_delta", 0.0))
            self.commodity_delta = float(event_signal.get("commodity_delta", 0.0))

        self.schedule = RandomActivation(self)
        self._agent_logs: list[dict] = []

        uid = 0
        for _ in range(n_market):
            self.schedule.add(MarketAgent(uid, self, portfolio_exposure=0.6))
            uid += 1
        for _ in range(n_housing):
            self.schedule.add(HousingAgent(uid, self, inventory_level=1000.0))
            uid += 1
        for _ in range(n_supply):
            self.schedule.add(SupplyChainAgent(uid, self, output_capacity=1.0))
            uid += 1
        for _ in range(n_policy):
            self.schedule.add(PolicyAgent(uid, self))
            uid += 1

        self.datacollector = DataCollector(
            model_reporters={
                "avg_portfolio_exposure": lambda m: _avg(m, "MarketAgent", "portfolio_exposure"),
                "avg_inventory_level": lambda m: _avg(m, "HousingAgent", "inventory_level"),
                "avg_output_capacity": lambda m: _avg(m, "SupplyChainAgent", "output_capacity"),
            }
        )

    def log_event(
        self,
        agent_id: int,
        timestep: int,
        prop: str,
        old_val: Any,
        new_val: Any,
        reason: str,
    ) -> None:
        """Record a state-change event for causal tracing."""
        self._agent_logs.append({
            "agent_id": agent_id,
            "timestep": timestep,
            "property": prop,
            "old_value": old_val,
            "new_value": new_val,
            "reason": reason,
        })

    def step(self) -> None:
        self.datacollector.collect(self)
        self.schedule.step()
        if self.progress_cb:
            self.progress_cb(self.schedule.steps)

    def get_snapshot(self) -> dict:
        """Return current state of all agents."""
        return {
            "step": self.schedule.steps,
            "agents": [a.get_state() for a in self.schedule.agents],
        }

    @property
    def agent_logs(self) -> list[dict]:
        return self._agent_logs


def _avg(model: ButterflyModel, agent_type: str, attr: str) -> float:
    """Compute average of an attribute across agents of a given type."""
    vals = [
        getattr(a, attr)
        for a in model.schedule.agents
        if type(a).__name__ == agent_type
    ]
    return sum(vals) / len(vals) if vals else 0.0
