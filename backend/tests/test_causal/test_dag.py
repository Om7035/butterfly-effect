"""Tests for DAG builder."""

import pytest
from butterfly.causal.dag import DAGBuilder


def test_build_dag_from_seed():
    """Test building a DAG from seed edges."""
    builder = DAGBuilder()
    edges = [
        ("Federal Reserve", "FEDFUNDS"),
        ("FEDFUNDS", "MORTGAGE30US"),
        ("MORTGAGE30US", "HOUST"),
        ("HOUST", "UNRATE"),
    ]
    dag = builder.build_dag_from_seed(edges)

    assert "nodes" in dag
    assert "edges" in dag
    assert len(dag["nodes"]) == 5
    assert len(dag["edges"]) == 4


def test_dag_cycle_removal():
    """Test that cycles are detected and removed."""
    builder = DAGBuilder()
    # Introduce a cycle: A→B→C→A
    edges = [
        ("A", "B"),
        ("B", "C"),
        ("C", "A"),  # cycle
    ]
    dag = builder.build_dag_from_seed(edges)

    # Should have removed one edge to break the cycle
    assert len(dag["edges"]) < 3


def test_dag_no_self_loops():
    """Test that self-loops are not included."""
    builder = DAGBuilder()
    edges = [
        ("A", "A"),  # self-loop
        ("A", "B"),
    ]
    dag = builder.build_dag_from_seed(edges)

    # Self-loop should be excluded
    for s, t, *_ in dag["edges"]:
        assert s != t


def test_dag_to_dot():
    """Test DOT graph string generation."""
    from butterfly.causal.identification import CausalIdentifier

    dag = {
        "nodes": ["Federal Reserve", "FEDFUNDS"],
        "edges": [("Federal Reserve", "FEDFUNDS", 0.9)],
    }
    dot = CausalIdentifier._dag_to_dot(dag)

    assert "digraph" in dot
    assert "Federal_Reserve" in dot
    assert "FEDFUNDS" in dot
    assert "->" in dot
