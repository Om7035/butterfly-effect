"""Simulation data models."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SimulationRun(BaseModel):
    """Tracks a simulation job."""

    run_id: str
    event_id: str
    status: str = "queued"          # queued | running | complete | failed
    timeline_a_id: str = ""
    timeline_b_id: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class SimulationResult(BaseModel):
    """Full output of a parallel A/B simulation run."""

    run_id: str
    event_id: str
    timeline_a: dict[int, dict] = Field(default_factory=dict)   # step -> agent snapshot
    timeline_b: dict[int, dict] = Field(default_factory=dict)
    agent_logs: list[dict] = Field(default_factory=list)
    steps_completed: int = 0
    duration_seconds: float = 0.0
    n_agents: int = 0
