"""Tests for causal identification."""

import pytest
import pandas as pd
import numpy as np
from butterfly.causal.identification import CausalIdentifier


@pytest.fixture
def sample_dag():
    return {
        "nodes": ["FEDFUNDS", "MORTGAGE30US", "HOUST"],
        "edges": [
            ("FEDFUNDS", "MORTGAGE30US", 0.8),
            ("MORTGAGE30US", "HOUST", 0.6),
        ],
    }


@pytest.fixture
def sample_data():
    """Generate synthetic time-series data with known causal relationship."""
    np.random.seed(42)
    n = 100
    fedfunds = np.linspace(1.68, 4.0, n) + np.random.normal(0, 0.05, n)
    mortgage = 3.5 + fedfunds * 0.8 + np.random.normal(0, 0.1, n)
    houst = 1600 - mortgage * 50 + np.random.normal(0, 20, n)
    return pd.DataFrame({
        "FEDFUNDS": fedfunds,
        "MORTGAGE30US": mortgage,
        "HOUST": houst,
    })


def test_ols_fallback(sample_dag, sample_data):
    """Test OLS fallback estimation."""
    identifier = CausalIdentifier()
    result = identifier._ols_fallback("FEDFUNDS", "MORTGAGE30US", sample_data)

    assert result.treatment == "FEDFUNDS"
    assert result.outcome == "MORTGAGE30US"
    assert result.ate != 0.0
    assert result.confidence_interval[0] < result.confidence_interval[1]


def test_missing_column(sample_dag, sample_data):
    """Test graceful handling of missing columns."""
    identifier = CausalIdentifier()
    result = identifier.estimate_effect(sample_dag, "NONEXISTENT", "MORTGAGE30US", sample_data)

    assert result.identified is False
    assert result.error is not None


def test_ate_direction(sample_dag, sample_data):
    """Test that ATE direction is correct (positive: higher fed funds → higher mortgage)."""
    identifier = CausalIdentifier()
    result = identifier._ols_fallback("FEDFUNDS", "MORTGAGE30US", sample_data)

    # Fed funds and mortgage should be positively correlated
    assert result.ate > 0


def test_dag_to_dot_format(sample_dag):
    """Test DOT format output."""
    dot = CausalIdentifier._dag_to_dot(sample_dag)
    assert dot.startswith("digraph")
    assert "FEDFUNDS" in dot
    assert "MORTGAGE30US" in dot
