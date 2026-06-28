"""
C-Path Algorithm — Cumulative Causal Influence Calculator.
Based on Liu & Li (2012) cascade influence methodology.

Calculates how much causal influence flows from the triggering event
to every reachable node. This is the mathematical backbone of butterfly-effect:
it tells us which downstream effects are most strongly CAUSED by the event,
not just which ones happen to correlate.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
from loguru import logger


@dataclass
class CascadePath:
    node_id: str
    node_label: str
    cci_score: float            # Cumulative Causal Influence (0–1)
    hop_count: int
    path_from_source: list
    estimated_latency_hours: int
    is_butterfly_effect: bool   # True if hop >= 3


class CPathCalculator:
    """
    Implements C-Path: cumulative causal influence from a source node
    through the entire causal graph.

    Key insight: a node 4 hops away with high-weight edges on every hop
    can have MORE cumulative influence than a node 2 hops away with weak
    edges. C-Path captures this properly.
    """

    def calculate(
        self,
        dag: nx.DiGraph,
        source_node: str,
        alpha: float = 0.85,
    ) -> dict[str, float]:
        """
        Calculate CCI score for every node reachable from source.
        Source node = 1.0. All others in [0, 1].
        """
        if source_node not in dag:
            logger.warning(f"[CPATH] Source '{source_node}' not in DAG")
            return {}

        cci: dict[str, float] = {n: 0.0 for n in dag.nodes()}
        cci[source_node] = 1.0

        try:
            distances = nx.single_source_shortest_path_length(dag, source_node)
        except Exception:
            distances = {source_node: 0}

        try:
            topo_order = list(nx.topological_sort(dag))
        except nx.NetworkXUnfeasible:
            logger.warning("[CPATH] Cycles remain — using BFS order")
            topo_order = list(nx.bfs_tree(dag, source_node).nodes())

        for node in topo_order:
            if node == source_node:
                continue
            dist = distances.get(node, 99)
            for pred in dag.predecessors(node):
                edge_w = dag[pred][node].get("confidence", 0.5)
                cci[node] += cci[pred] * edge_w * (alpha ** dist)

        # Normalise to [0, 1]
        max_score = max(cci.values()) if cci else 1.0
        if max_score > 0:
            cci = {k: round(v / max_score, 4) for k, v in cci.items()}

        logger.info(f"[CPATH] CCI calculated for {len(cci)} nodes from '{source_node}'")
        return cci

    def rank_paths(
        self,
        dag: nx.DiGraph,
        cci_scores: dict,
        source_node: str,
        top_n: int = 10,
    ) -> list[CascadePath]:
        paths: list[CascadePath] = []

        for node_id, score in sorted(cci_scores.items(), key=lambda x: x[1], reverse=True):
            if node_id == source_node or score == 0:
                continue

            try:
                path = nx.shortest_path(dag, source_node, node_id)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                path = [source_node, node_id]

            hop_count = len(path) - 1
            total_latency = sum(
                dag[path[i]][path[i + 1]].get("latency_hours", 24)
                for i in range(len(path) - 1)
                if dag.has_edge(path[i], path[i + 1])
            )

            paths.append(CascadePath(
                node_id=node_id,
                node_label=dag.nodes[node_id].get("label", node_id)
                if node_id in dag else node_id,
                cci_score=score,
                hop_count=hop_count,
                path_from_source=path,
                estimated_latency_hours=total_latency,
                is_butterfly_effect=(hop_count >= 3),
            ))

            if len(paths) >= top_n:
                break

        return paths

    def find_butterfly_effects(
        self,
        dag: nx.DiGraph,
        cci_scores: dict,
        source_node: str,
        min_cci: float = 0.15,
    ) -> list[CascadePath]:
        """Return only 3+ hop effects with CCI above threshold."""
        all_paths = self.rank_paths(dag, cci_scores, source_node, top_n=50)
        butterfly = [p for p in all_paths if p.is_butterfly_effect and p.cci_score >= min_cci]
        logger.info(f"[CPATH] {len(butterfly)} butterfly effects (3+ hops, CCI >= {min_cci})")
        return butterfly
