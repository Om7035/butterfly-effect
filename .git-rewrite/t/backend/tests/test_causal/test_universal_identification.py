"""Acceptance tests for the universal causal identification system.

Tests:
1. OutcomeTypeDetector — all 5 types
2. UniversalCausalEstimator — geopolitical fixture (continuous)
3. UniversalCausalEstimator — count data (Poisson)
4. UniversalCausalEstimator — binary data (logistic)
5. UniversalCausalEstimator — rate data (logit transform)
6. SyntheticControlEstimator — basic functionality
7. DAG templates — all 5 domains
8. DAG merge — template enrichment
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from butterfly.causal.identification import OutcomeTypeDetector, UniversalCausalEstimator
from butterfly.causal.synthetic_control import SyntheticControlEstimator
from butterfly.causal.dag import DAGBuilder, DOMAIN_TEMPLATES, get_template_for_domain

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def geopolitical_data() -> pd.DataFrame:
    """Load Israel-Hamas 2023 fixture."""
    with open(FIXTURES / "israel_hamas_2023.json") as f:
        raw = json.load(f)
    return pd.DataFrame(raw["data"])


@pytest.fixture
def simple_dag() -> dict:
    """Minimal DAG for testing."""
    return {
        "nodes": ["military_action", "oil_price", "conflict_intensity"],
        "edges": [
            ("military_action", "conflict_intensity", 0.9),
            ("conflict_intensity", "oil_price", 0.8),
        ],
    }


# ── Test 1: OutcomeTypeDetector ───────────────────────────────────────────────

class TestOutcomeTypeDetector:
    def setup_method(self):
        self.detector = OutcomeTypeDetector()

    def test_binary(self):
        assert self.detector.detect(pd.Series([0, 1, 0, 1, 1])) == "binary"
        assert self.detector.detect(pd.Series([0.0, 1.0, 0.0, 1.0])) == "binary"

    def test_count(self):
        assert self.detector.detect(pd.Series([100, 250, 180, 310])) == "count"
        assert self.detector.detect(pd.Series([0, 5, 12, 3, 8, 100])) == "count"

    def test_continuous(self):
        assert self.detector.detect(pd.Series([0.2, -0.3, 0.8, 0.1])) == "continuous"
        assert self.detector.detect(pd.Series([84.2, 87.3, 91.4, 88.0])) == "continuous"
        assert self.detector.detect(pd.Series([-1.5, 2.3, -0.8, 4.1])) == "continuous"

    def test_rate(self):
        assert self.detector.detect(pd.Series([0.1, 0.3, 0.25, 0.45, 0.6])) == "rate"
        assert self.detector.detect(pd.Series([0.03, 0.05, 0.08, 0.04])) == "rate"

    def test_ordinal(self):
        assert self.detector.detect(pd.Series([1, 3, 5, 2, 4, 3, 1, 5])) == "ordinal"
        assert self.detector.detect(pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])) == "ordinal"

    def test_empty_series(self):
        # Should not crash
        result = self.detector.detect(pd.Series([], dtype=float))
        assert result == "continuous"


# ── Test 2: Geopolitical estimator (continuous) ───────────────────────────────

def test_geopolitical_continuous(geopolitical_data, simple_dag):
    """Acceptance test: military_action → oil_price, continuous outcome."""
    estimator = UniversalCausalEstimator()
    result = estimator.estimate(
        dag=simple_dag,
        treatment="military_action",
        outcome="oil_price",
        data=geopolitical_data,
        outcome_type="continuous",
    )

    # ATE must be positive (conflict → oil price increases)
    assert result.ate > 0, f"Expected positive ATE (conflict → oil price up), got {result.ate}"

    # CI must bracket the ATE
    assert result.confidence_interval[0] < result.ate < result.confidence_interval[1], (
        f"ATE {result.ate} not in CI {result.confidence_interval}"
    )

    # Method must be populated
    assert result.method is not None and len(result.method) > 0

    # Limitations must be non-empty (honesty requirement)
    assert len(result.limitations) > 0, "Must document limitations"

    # Assumptions must be non-empty
    assert len(result.assumptions) > 0, "Must document assumptions"

    # Outcome type must be set
    assert result.outcome_type == "continuous"


# ── Test 3: Count data (Poisson) ──────────────────────────────────────────────

def test_count_estimator(geopolitical_data, simple_dag):
    """Poisson GLM for refugee count data."""
    estimator = UniversalCausalEstimator()
    result = estimator.estimate(
        dag=simple_dag,
        treatment="military_action",
        outcome="refugee_count",
        data=geopolitical_data,
        outcome_type="count",
    )

    assert result.outcome_type == "count"
    assert result.estimator_used in ("poisson_glm", "ols_fallback")
    assert result.confidence_interval[0] <= result.confidence_interval[1]
    assert len(result.limitations) > 0
    assert result.method is not None


# ── Test 4: Binary data (logistic) ────────────────────────────────────────────

def test_binary_estimator(simple_dag):
    """Logistic regression for binary outcome."""
    np.random.seed(42)
    n = 100
    treatment = np.random.binomial(1, 0.5, n)
    outcome = np.random.binomial(1, 0.3 + 0.4 * treatment)
    data = pd.DataFrame({"treatment": treatment, "outcome": outcome})

    estimator = UniversalCausalEstimator()
    result = estimator.estimate(
        dag={"nodes": ["treatment", "outcome"], "edges": [("treatment", "outcome", 0.8)]},
        treatment="treatment",
        outcome="outcome",
        data=data,
        outcome_type="binary",
    )

    assert result.outcome_type == "binary"
    assert result.estimator_used in ("logistic_regression", "ols_fallback")
    assert -1.0 <= result.ate <= 1.0, f"AME should be in [-1,1], got {result.ate}"
    assert len(result.limitations) > 0


# ── Test 5: Rate data (logit transform) ───────────────────────────────────────

def test_rate_estimator(simple_dag):
    """OLS on logit-transformed rate outcome."""
    np.random.seed(42)
    n = 50
    treatment = np.random.uniform(0, 1, n)
    rate = np.clip(0.1 + 0.3 * treatment + np.random.normal(0, 0.05, n), 0.01, 0.99)
    data = pd.DataFrame({"treatment": treatment, "infection_rate": rate})

    estimator = UniversalCausalEstimator()
    result = estimator.estimate(
        dag={"nodes": ["treatment", "infection_rate"], "edges": [("treatment", "infection_rate", 0.7)]},
        treatment="treatment",
        outcome="infection_rate",
        data=data,
        outcome_type="rate",
    )

    assert result.outcome_type == "rate"
    assert result.estimator_used in ("ols_logit_transform", "ols_fallback")
    assert result.confidence_interval[0] <= result.confidence_interval[1]
    assert len(result.limitations) > 0


# ── Test 6: Missing column → error result (no crash) ─────────────────────────

def test_missing_column_no_crash(simple_dag):
    """Missing column must return error result, not raise."""
    data = pd.DataFrame({"military_action": [0, 1, 0, 1]})
    estimator = UniversalCausalEstimator()
    result = estimator.estimate(
        dag=simple_dag,
        treatment="military_action",
        outcome="nonexistent_column",
        data=data,
    )
    assert result.error is not None
    assert result.ate == 0.0
    assert result.identified is False


# ── Test 7: Synthetic control ─────────────────────────────────────────────────

def test_synthetic_control_basic():
    """Basic synthetic control: Lebanon vs Jordan/Egypt/Morocco."""
    np.random.seed(42)
    # Use dates that straddle the treatment date
    dates = pd.date_range("2023-09-27", periods=30, freq="D")
    treatment_date = datetime(2023, 10, 7)  # day 11 in the series

    data = pd.DataFrame(index=dates)
    data["Lebanon"] = np.concatenate([
        np.linspace(100, 110, 10),          # pre: rising
        np.linspace(110, 85, 20),           # post: sharp drop (conflict)
    ])
    data["Jordan"]  = np.linspace(100, 112, 30) + np.random.normal(0, 1, 30)
    data["Egypt"]   = np.linspace(98,  108, 30) + np.random.normal(0, 1, 30)
    data["Morocco"] = np.linspace(102, 114, 30) + np.random.normal(0, 1, 30)

    estimator = SyntheticControlEstimator()
    result = estimator.estimate(
        treated_unit="Lebanon",
        control_units=["Jordan", "Egypt", "Morocco"],
        outcome_variable="tourist_arrivals",
        treatment_date=treatment_date,
        data=data,
    )

    # Must not crash
    assert result is not None
    assert isinstance(result.weights, dict)
    assert len(result.weights) == 3

    # Weights must sum to ~1
    assert abs(sum(result.weights.values()) - 1.0) < 0.01

    # ATE must be negative (conflict → tourist arrivals drop)
    assert result.ate < 0, f"Expected negative ATE (conflict → drop), got {result.ate}"

    # Limitations must be populated
    assert len(result.limitations) > 0

    # Assumptions must be populated
    assert len(result.assumptions) > 0

    # p_value must be in [0, 1]
    assert 0.0 <= result.p_value <= 1.0


def test_synthetic_control_insufficient_data():
    """Insufficient pre-treatment data must return error result, not crash."""
    dates = pd.date_range("2023-10-01", periods=5, freq="D")
    data = pd.DataFrame({
        "Treated": [100, 101, 102, 103, 104],
        "Control": [100, 101, 102, 103, 104],
    }, index=dates)

    estimator = SyntheticControlEstimator()
    result = estimator.estimate(
        treated_unit="Treated",
        control_units=["Control"],
        outcome_variable="test",
        treatment_date=datetime(2023, 10, 4),
        data=data,
    )
    # Should return error result, not crash
    assert result is not None
    assert len(result.limitations) > 0


# ── Test 8: DAG templates ─────────────────────────────────────────────────────

def test_all_domain_templates_exist():
    """All 5 domain templates must be registered."""
    for domain in ("finance", "geopolitics", "climate", "health", "technology"):
        template = get_template_for_domain(domain)
        assert template is not None, f"No template for domain '{domain}'"
        assert len(template["nodes"]) >= 5
        assert len(template["edges"]) >= 5
        for src, tgt, props in template["edges"]:
            assert "latency_hours" in props
            assert "confidence" in props
            assert "mechanism" in props


def test_dag_template_merge_bootstrap():
    """Bootstrap mode: empty DAG gets all template edges."""
    builder = DAGBuilder()
    empty_dag: dict = {"nodes": [], "edges": []}
    merged = builder.merge_with_template(empty_dag, "finance")

    assert len(merged["nodes"]) > 0
    assert len(merged["edges"]) > 0
    assert merged.get("template_domain") == "finance"


def test_dag_template_merge_enrichment():
    """Enrichment mode: only template edges where both nodes exist are added."""
    builder = DAGBuilder()
    existing_dag = {
        "nodes": ["federal_funds_rate", "mortgage_rate"],
        "edges": [("federal_funds_rate", "mortgage_rate", 0.9)],
    }
    merged = builder.merge_with_template(existing_dag, "finance")

    # Should have added edges between existing nodes from template
    edge_pairs = {(e[0], e[1]) for e in merged["edges"]}
    assert ("federal_funds_rate", "mortgage_rate") in edge_pairs


def test_unknown_domain_returns_unchanged():
    """Unknown domain must return DAG unchanged."""
    builder = DAGBuilder()
    dag = {"nodes": ["a", "b"], "edges": [("a", "b", 0.8)]}
    result = builder.merge_with_template(dag, "unknown_domain_xyz")
    assert result == dag
