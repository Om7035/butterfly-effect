"""UniversalAgent and UniversalModel — domain-agnostic Mesa simulation.

Replaces ButterflyModel for universal event simulation.
Agents react to a shared environment dict via parameterized math functions.
Influence propagates through a NetworkX graph (not all-to-all).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import networkx as nx
from mesa import Agent, Model
from mesa.datacollection import DataCollector

# Mesa 3.x: RandomActivation is deprecated — use AgentSet-based stepping
try:
    from mesa.time import RandomActivation
    _USE_LEGACY_SCHEDULER = True
except ImportError:
    _USE_LEGACY_SCHEDULER = False

from butterfly.simulation.dynamic_agents import BehaviorProfile, ReactionFn


class UniversalAgent(Agent):
    """Domain-agnostic agent driven by a BehaviorProfile.

    At each step:
    1. Check all TriggerRules against model.environment
    2. If triggered: queue ReactionFns (with lag)
    3. Apply pending reactions
    4. Log every state change
    5. Propagate influence to NetworkX neighbors
    """

    def __init__(self, model: "UniversalModel", profile: BehaviorProfile) -> None:
        super().__init__(model)
        self.profile = profile
        self._trigger_step: int | None = None   # step when first triggered
        self._pending: list[tuple[int, ReactionFn]] = []  # (apply_at_step, fn)

    def step(self) -> None:
        env = self.model.environment
        current_step = self.model.schedule.steps

        # 1. Check triggers
        for trigger in self.profile.triggers:
            if trigger.is_triggered(env):
                if self._trigger_step is None:
                    self._trigger_step = current_step
                    # Queue all reaction functions
                    for fn in self.profile.reaction_functions:
                        apply_at = current_step + fn.lag_steps
                        self._pending.append((apply_at, fn))
                break  # one trigger activation per step

        # 2. Apply pending reactions
        still_pending = []
        for apply_at, fn in self._pending:
            if current_step >= apply_at:
                old_val = env.get(fn.target_variable, 0.0)
                delta = fn.apply(old_val, current_step, self._trigger_step if self._trigger_step is not None else current_step)
                new_val = old_val + delta * self.profile.dampening_factor
                env[fn.target_variable] = new_val

                self.model.log_event(
                    agent_id=self.profile.agent_id,
                    agent_name=self.profile.agent_name,
                    timestep=current_step,
                    variable=fn.target_variable,
                    old_value=old_val,
                    new_value=new_val,
                    trigger_fired=self.profile.triggers[0].condition if self.profile.triggers else "unknown",
                    delta=delta,
                )

                # Propagate to NetworkX neighbors
                self._propagate_influence(fn.target_variable, delta)
            else:
                still_pending.append((apply_at, fn))

        self._pending = still_pending

    def _propagate_influence(self, variable: str, delta: float) -> None:
        """Dampen and pass influence to graph neighbors."""
        graph: nx.DiGraph = self.model.influence_graph
        if self.profile.agent_id not in graph:
            return
        for neighbor_id in graph.successors(self.profile.agent_id):
            edge_data = graph.edges[self.profile.agent_id, neighbor_id]
            weight = edge_data.get("weight", 0.5)
            neighbor_agent = self.model.agent_by_id.get(neighbor_id)
            if neighbor_agent:
                env = self.model.environment
                old = env.get(variable, 0.0)
                env[variable] = old + delta * weight * 0.3


class UniversalModel(Model):
    """Mesa model for universal domain simulation.

    Runs one timeline (A = event happens, B = counterfactual baseline).
    """

    def __init__(
        self,
        profiles: list[BehaviorProfile],
        event_signal: dict | None = None,
        progress_cb: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__()
        self.event_signal = event_signal
        self.progress_cb = progress_cb
        self._causal_log: list[dict] = []

        # Shared environment — all agents read/write this
        self.environment: dict[str, float] = self._init_environment(profiles, event_signal)

        # Build influence graph from profiles
        self.influence_graph: nx.DiGraph = self._build_influence_graph(profiles)

        # Create agents — use AgentSet (Mesa 3.x) or RandomActivation (legacy)
        self._step_count = 0
        self.agent_by_id: dict[str, UniversalAgent] = {}

        if _USE_LEGACY_SCHEDULER:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                self.schedule = RandomActivation(self)
            for profile in profiles:
                agent = UniversalAgent(self, profile)
                self.schedule.add(agent)
                self.agent_by_id[profile.agent_id] = agent
        else:
            # Mesa 3.1+ — agents register themselves via super().__init__
            self.schedule = None
            for profile in profiles:
                agent = UniversalAgent(self, profile)
                self.agent_by_id[profile.agent_id] = agent

        # DataCollector: track all environment variables
        env_keys = list(self.environment.keys())
        self.datacollector = DataCollector(
            model_reporters={k: lambda m, k=k: m.environment.get(k, 0.0) for k in env_keys}
        )

    def step(self) -> None:
        self.datacollector.collect(self)
        if self.schedule is not None:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                self.schedule.step()
            self._step_count = self.schedule.steps
        else:
            # Mesa 3.1+ AgentSet API
            self.agents.shuffle_do("step")
            self._step_count += 1
        if self.progress_cb:
            self.progress_cb(self._step_count)

    def log_event(
        self,
        agent_id: str,
        agent_name: str,
        timestep: int,
        variable: str,
        old_value: float,
        new_value: float,
        trigger_fired: str,
        delta: float,
    ) -> None:
        self._causal_log.append({
            "agent_id": agent_id,
            "agent_name": agent_name,
            "timestep": timestep,
            "variable_changed": variable,
            "old_value": round(old_value, 4),
            "new_value": round(new_value, 4),
            "delta": round(delta, 4),
            "trigger_fired": trigger_fired,
        })

    def get_causal_log(self) -> list[dict]:
        return sorted(self._causal_log, key=lambda x: x["timestep"])

    def get_environment_snapshot(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in self.environment.items()}

    @staticmethod
    def _init_environment(
        profiles: list[BehaviorProfile], event_signal: dict | None
    ) -> dict[str, float]:
        """Populate environment from profile initial states + event signal."""
        env: dict[str, float] = {
            # Universal baseline variables
            "event_magnitude": 0.0,
            "conflict_intensity": 0.0,
            "oil_price": 80.0,
            "oil_supply": 1.0,
            "interest_rate_delta": 0.0,
            "mortgage_rate": 4.5,
            "housing_starts": 1500.0,
            "portfolio_exposure": 0.6,
            "ai_capability_index": 0.0,
            "ai_investment_flow": 1.0,
            "rd_spending": 1.0,
            "regulatory_pressure": 0.0,
            "tech_employment": 1.0,
            "storm_intensity": 0.0,
            "infrastructure_damage": 0.0,
            "insurance_payout": 0.0,
            "emergency_spending": 0.0,
            "construction_demand": 1.0,
            "infection_rate": 0.0,
            "hospital_capacity_used": 0.3,
            "mobility_restriction": 0.0,
            "consumer_spending": 1.0,
            "displacement_count": 0.0,
            "diplomatic_activity": 0.0,
            "insurance_premium": 1.0,
            "bond_yield": 3.5,
            "risk_sentiment": 0.5,
            "shipping_disruption": 0.0,
            "chip_shortage_index": 0.0,
            "demand_shock": 0.0,
        }

        # Apply profile initial states
        for profile in profiles:
            env.update(profile.initial_state)

        # Apply event signal
        if event_signal:
            for k, v in event_signal.items():
                if k != "event_id":
                    env[k] = float(v)

        return env

    @staticmethod
    def _build_influence_graph(profiles: list[BehaviorProfile]) -> nx.DiGraph:
        """Build directed influence graph from profile influence_targets."""
        graph = nx.DiGraph()
        for profile in profiles:
            graph.add_node(profile.agent_id, name=profile.agent_name)
        for profile in profiles:
            for target_id in profile.influence_targets:
                if target_id in graph:
                    graph.add_edge(profile.agent_id, target_id, weight=0.5)
        return graph
