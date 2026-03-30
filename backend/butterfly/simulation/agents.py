"""Mesa agent definitions with empirically constrained reaction functions.

Decision 1 from context.md: agents use historical data, NOT LLMs.
Sources: Bernanke (2005) transmission mechanism, NAR historical data.
"""

from __future__ import annotations

import random
from typing import Any

from mesa import Agent


class MarketAgent(Agent):
    """Institutional investor / fund reacting to interest rate events.

    Reaction grounded in Bernanke (2005) monetary transmission mechanism.
    """

    def __init__(
        self,
        unique_id: int,
        model: Any,
        portfolio_exposure: float = 0.6,
        risk_tolerance: float = 0.5,
        sector_focus: str = "equities",
    ) -> None:
        super().__init__(unique_id, model)
        self.portfolio_exposure = portfolio_exposure
        self.risk_tolerance = risk_tolerance
        self.sector_focus = sector_focus

    def react_to_rate_change(self, rate_change: float) -> None:
        """Adjust portfolio exposure on interest rate event.

        Formula: delta = -(rate_change * 0.6 * (1 - risk_tolerance)) + N(0, 0.05)
        """
        old = self.portfolio_exposure
        delta = -(rate_change * 0.6 * (1 - self.risk_tolerance))
        noise = random.gauss(0, 0.05)
        self.portfolio_exposure = max(0.0, min(1.0, old + delta + noise))
        self.model.log_event(
            self.unique_id, self.model.schedule.steps,
            "portfolio_exposure", old, self.portfolio_exposure,
            f"rate_change={rate_change:.3f}",
        )

    def step(self) -> None:
        rate_delta = getattr(self.model, "rate_delta", 0.0)
        if abs(rate_delta) > 1e-6 and self.model.schedule.steps == 1:
            self.react_to_rate_change(rate_delta)

    def get_state(self) -> dict:
        return {
            "type": "MarketAgent",
            "id": self.unique_id,
            "portfolio_exposure": round(self.portfolio_exposure, 4),
            "risk_tolerance": self.risk_tolerance,
            "sector_focus": self.sector_focus,
        }


class HousingAgent(Agent):
    """Real estate market participant reacting to mortgage rate changes.

    Reaction grounded in NAR historical correlation data.
    Lag: 2 simulation steps.
    """

    LAG_STEPS = 2

    def __init__(
        self,
        unique_id: int,
        model: Any,
        inventory_level: float = 1000.0,
        price_index: float = 100.0,
        region: str = "national",
    ) -> None:
        super().__init__(unique_id, model)
        self.inventory_level = inventory_level
        self.price_index = price_index
        self.region = region
        self._pending_delta: float = 0.0
        self._lag_counter: int = 0

    def react_to_mortgage_change(self, mortgage_delta: float) -> None:
        """Queue a reaction with a 2-step lag.

        Formula: delta = -(mortgage_delta * 2.3) + N(0, 10)
        """
        self._pending_delta = -(mortgage_delta * 2.3) + random.gauss(0, 10)
        self._lag_counter = self.LAG_STEPS

    def step(self) -> None:
        mortgage_delta = getattr(self.model, "mortgage_delta", 0.0)
        if abs(mortgage_delta) > 1e-6 and self.model.schedule.steps == 1:
            self.react_to_mortgage_change(mortgage_delta)

        if self._lag_counter > 0:
            self._lag_counter -= 1
            if self._lag_counter == 0 and abs(self._pending_delta) > 1e-6:
                old = self.inventory_level
                self.inventory_level = max(0.0, old + self._pending_delta)
                self.model.log_event(
                    self.unique_id, self.model.schedule.steps,
                    "inventory_level", old, self.inventory_level,
                    f"mortgage_delta={mortgage_delta:.3f}",
                )
                self._pending_delta = 0.0

    def get_state(self) -> dict:
        return {
            "type": "HousingAgent",
            "id": self.unique_id,
            "inventory_level": round(self.inventory_level, 2),
            "price_index": round(self.price_index, 2),
            "region": self.region,
        }


class SupplyChainAgent(Agent):
    """Manufacturer/supplier reacting to energy or commodity price events.

    Lag: 3 simulation steps.
    """

    LAG_STEPS = 3

    def __init__(
        self,
        unique_id: int,
        model: Any,
        input_cost_index: float = 100.0,
        output_capacity: float = 1.0,
        supplier_count: int = 5,
    ) -> None:
        super().__init__(unique_id, model)
        self.input_cost_index = input_cost_index
        self.output_capacity = output_capacity
        self.supplier_count = max(1, supplier_count)
        self._pending_delta: float = 0.0
        self._lag_counter: int = 0

    def react_to_price_change(self, price_delta: float) -> None:
        """Queue a reaction with a 3-step lag.

        Formula: delta = -(price_delta * 0.4 * (1/supplier_count)) + N(0, 0.02)
        """
        self._pending_delta = (
            -(price_delta * 0.4 * (1.0 / self.supplier_count)) + random.gauss(0, 0.02)
        )
        self._lag_counter = self.LAG_STEPS

    def step(self) -> None:
        price_delta = getattr(self.model, "commodity_delta", 0.0)
        if abs(price_delta) > 1e-6 and self.model.schedule.steps == 1:
            self.react_to_price_change(price_delta)

        if self._lag_counter > 0:
            self._lag_counter -= 1
            if self._lag_counter == 0 and abs(self._pending_delta) > 1e-6:
                old = self.output_capacity
                self.output_capacity = max(0.0, old + self._pending_delta)
                self.model.log_event(
                    self.unique_id, self.model.schedule.steps,
                    "output_capacity", old, self.output_capacity,
                    f"commodity_delta={price_delta:.3f}",
                )
                self._pending_delta = 0.0

    def get_state(self) -> dict:
        return {
            "type": "SupplyChainAgent",
            "id": self.unique_id,
            "input_cost_index": round(self.input_cost_index, 2),
            "output_capacity": round(self.output_capacity, 4),
            "supplier_count": self.supplier_count,
        }


class PolicyAgent(Agent):
    """Regulator / observer — reads metrics, does not react.

    Feeds observations back to the causal graph.
    """

    def __init__(
        self,
        unique_id: int,
        model: Any,
        mandate_metric: str = "UNRATE",
        current_reading: float = 3.6,
        target: float = 4.0,
    ) -> None:
        super().__init__(unique_id, model)
        self.mandate_metric = mandate_metric
        self.current_reading = current_reading
        self.target = target

    def step(self) -> None:
        pass  # Observer only

    def get_state(self) -> dict:
        return {
            "type": "PolicyAgent",
            "id": self.unique_id,
            "mandate_metric": self.mandate_metric,
            "current_reading": round(self.current_reading, 3),
            "target": self.target,
        }
