"""pgmpy DAG builder from Neo4j causal graph."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional
from loguru import logger

from butterfly.db.neo4j import run_query
from butterfly.db.redis import get_cache, set_cache


class DAGBuilder:
    """Build a causal DAG from the Neo4j knowledge graph."""

    async def build_dag_for_event(self, event_id: str) -> Optional[dict]:
        """Build a DAG dict for a given event.

        Queries Neo4j for all CAUSES/TRIGGERS edges reachable within 4 hops,
        validates acyclicity, and returns a serialisable dict.

        Args:
            event_id: The event to build the DAG from.

        Returns:
            {"nodes": [...], "edges": [...], "node_names": {...}} or None on failure.
        """
        cache_key = f"dag:{event_id}"
        cached = await get_cache(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

        try:
            # Pull causal edges reachable from this event (up to 4 hops)
            query = """
            MATCH (start:Event {event_id: $event_id})
            CALL apoc.path.subgraphAll(start, {
                relationshipFilter: 'CAUSES>|TRIGGERS>|INFLUENCES>',
                maxLevel: 4
            })
            YIELD nodes, relationships
            RETURN nodes, relationships
            """
            results = await run_query(query, {"event_id": event_id})
        except Exception:
            # APOC may not be available — fall back to simple query
            results = await self._fallback_query(event_id)

        if not results:
            logger.warning(f"No causal graph found for event {event_id}")
            return None

        dag = self._build_dag_from_results(results)
        if dag is None:
            return None

        # Cache for 1 hour
        await set_cache(cache_key, json.dumps(dag), ttl=3600)
        return dag

    async def _fallback_query(self, event_id: str) -> list[dict]:
        """Fallback query without APOC."""
        query = """
        MATCH (start:Event {event_id: $event_id})
        MATCH (start)-[r:CAUSES|TRIGGERS|INFLUENCES*1..4]->(end)
        RETURN DISTINCT
            startNode(r[0]).name AS source_name,
            endNode(r[-1]).name AS target_name,
            type(r[0]) AS rel_type,
            r[0].confidence AS confidence
        LIMIT 200
        """
        try:
            return await run_query(query, {"event_id": event_id})
        except Exception as e:
            logger.error(f"Fallback DAG query failed: {e}")
            return []

    def _build_dag_from_results(self, results: list[dict]) -> Optional[dict]:
        """Convert query results into a DAG dict.

        Args:
            results: Raw Neo4j query results.

        Returns:
            DAG dict or None if cycle detected and unresolvable.
        """
        nodes: set[str] = set()
        edges: list[tuple[str, str, float]] = []  # (source, target, confidence)

        for row in results:
            source = row.get("source_name") or row.get("source")
            target = row.get("target_name") or row.get("target")
            confidence = float(row.get("confidence") or 0.7)

            if source and target and source != target:
                nodes.add(source)
                nodes.add(target)
                edges.append((source, target, confidence))

        if not nodes:
            return None

        # Check for cycles and remove weakest edge if found
        edges = self._remove_cycles(list(nodes), edges)

        node_list = list(nodes)
        return {
            "nodes": node_list,
            "edges": [(s, t, c) for s, t, c in edges],
            "node_names": {n: n for n in node_list},
        }

    def _remove_cycles(
        self, nodes: list[str], edges: list[tuple[str, str, float]]
    ) -> list[tuple[str, str, float]]:
        """Remove cycles by dropping the weakest edge in each cycle.

        Args:
            nodes: List of node names.
            edges: List of (source, target, confidence) tuples.

        Returns:
            Acyclic edge list.
        """
        max_iterations = len(edges)
        for _ in range(max_iterations):
            cycle_edge = self._find_cycle_edge(nodes, edges)
            if cycle_edge is None:
                break
            logger.warning(f"Cycle detected, removing weakest edge: {cycle_edge[:2]}")
            edges = [e for e in edges if e != cycle_edge]
        return edges

    def _find_cycle_edge(
        self, nodes: list[str], edges: list[tuple[str, str, float]]
    ) -> Optional[tuple[str, str, float]]:
        """Find the weakest edge that is part of a cycle using DFS.

        Returns:
            The weakest cycle edge, or None if no cycle.
        """
        adj: dict[str, list[str]] = {n: [] for n in nodes}
        for s, t, _ in edges:
            adj.setdefault(s, []).append(t)

        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str) -> Optional[tuple[str, str]]:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    return (node, neighbor)
            rec_stack.discard(node)
            return None

        for node in nodes:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    # Find the weakest edge in this cycle pair
                    cycle_edges = [e for e in edges if e[0] == cycle[0] and e[1] == cycle[1]]
                    if cycle_edges:
                        return min(cycle_edges, key=lambda e: e[2])

        return None

    def build_dag_from_seed(self, seed_edges: list[tuple[str, str]]) -> dict:
        """Build a DAG from a manually provided edge list (for testing/demo).

        Args:
            seed_edges: List of (source, target) tuples.

        Returns:
            DAG dict.
        """
        nodes: set[str] = set()
        edges: list[tuple[str, str, float]] = []
        for s, t in seed_edges:
            nodes.add(s)
            nodes.add(t)
            edges.append((s, t, 0.8))

        edges = self._remove_cycles(list(nodes), edges)
        node_list = list(nodes)
        return {
            "nodes": node_list,
            "edges": edges,
            "node_names": {n: n for n in node_list},
        }
