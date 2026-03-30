"""CausalEdge model — canonical data model for all causal relationships."""

from datetime import datetime

from pydantic import BaseModel, Field


class CausalEdge(BaseModel):
    """Canonical causal edge model. Every causal claim in the system is a CausalEdge."""

    edge_id: str                                    # "causal_{source}_{target}_{timestamp}"
    source_node_id: str                             # Neo4j node ID or entity name
    target_node_id: str                             # Neo4j node ID or entity name
    relationship_type: str                          # "influences_price" | "triggers_sentiment" | ...
    strength_score: float = Field(ge=0.0, le=1.0)  # 0.0 = no effect, 1.0 = deterministic
    time_decay_factor: float = 0.1                  # How fast effect fades
    latency_hours: float = 24.0                     # Expected hours until effect manifests
    counterfactual_delta: float = 0.0               # A(t) - B(t) at effect peak
    confidence_interval: tuple[float, float] = (0.0, 1.0)  # 95% CI (lower, upper)
    evidence_path: list[str] = Field(default_factory=list)  # Source IDs supporting this edge
    refutation_passed: bool = False                 # Did automated refutation tests pass?
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None


class CausalEstimate(BaseModel):
    """Result of a DoWhy causal identification and estimation."""

    treatment: str
    outcome: str
    ate: float                                      # Average Treatment Effect
    confidence_interval: tuple[float, float]
    identification_method: str                      # "backdoor" | "frontdoor" | "iv"
    estimator_used: str
    refutation_results: dict
    identified: bool                                # False if DoWhy couldn't identify


class CounterfactualResult(BaseModel):
    """Full result of a counterfactual analysis run."""

    event_id: str
    timeline_a: dict[str, list[float]]              # {metric_id: [values t0..tn]}
    timeline_b: dict[str, list[float]]              # Same but counterfactual
    diff: dict[str, list[float]]                    # A - B at each timestep
    causal_edges: list[CausalEdge]
    peak_delta_at_hours: dict[str, float]           # When does each effect peak?
    run_metadata: dict
