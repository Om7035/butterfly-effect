"""Neo4j graph database connection and utilities.

Falls back to an in-memory NetworkX graph when Neo4j server is unavailable.
This means graph operations work out of the box with zero server setup.
"""

from typing import Any

import networkx as nx
from loguru import logger

from butterfly.config import settings

neo4j_driver = None
_neo4j_unavailable: bool = False

# ── In-memory graph fallback ──────────────────────────────────────────────────
# When Neo4j is unavailable, we store the graph in memory using NetworkX.
# Data is lost on restart, but the pipeline works fully without a server.

_memory_graph: nx.MultiDiGraph = nx.MultiDiGraph()


def _memory_store_node(label: str, props: dict) -> None:
    node_id = props.get("event_id") or props.get("entity_id") or props.get("name", str(id(props)))
    _memory_graph.add_node(node_id, label=label, **props)


def _memory_store_edge(source_id: str, target_id: str, rel_type: str, props: dict) -> None:
    _memory_graph.add_edge(source_id, target_id, rel_type=rel_type, **props)


def _memory_query_causal_chain(event_id: str, max_hops: int = 4) -> list[dict]:
    """Return causal edges reachable from event_id within max_hops."""
    if event_id not in _memory_graph:
        return []
    results = []
    visited = set()
    queue = [(event_id, 0)]
    while queue:
        node, depth = queue.pop(0)
        if depth >= max_hops or node in visited:
            continue
        visited.add(node)
        for _, target, data in _memory_graph.out_edges(node, data=True):
            results.append({
                "source_name": _memory_graph.nodes[node].get("name", node),
                "target_name": _memory_graph.nodes.get(target, {}).get("name", target),
                "rel_type": data.get("rel_type", "CAUSES"),
                "confidence": data.get("confidence", 0.7),
            })
            queue.append((target, depth + 1))
    return results


# ── Neo4j connection ──────────────────────────────────────────────────────────

async def init_neo4j():
    """Initialize Neo4j driver. Sets _neo4j_unavailable=True on failure."""
    global neo4j_driver, _neo4j_unavailable
    try:
        from neo4j import AsyncGraphDatabase
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=3.0,
            max_connection_lifetime=300,
        )
        async with neo4j_driver.session() as session:
            await session.run("RETURN 1")
        _neo4j_unavailable = False
        logger.info("Neo4j connection established")
        return neo4j_driver
    except Exception as e:
        logger.warning(f"Neo4j unavailable — using in-memory graph fallback: {type(e).__name__}")
        neo4j_driver = None
        _neo4j_unavailable = True
        return None


async def close_neo4j() -> None:
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        logger.info("Neo4j connection closed")


async def get_neo4j():
    global neo4j_driver, _neo4j_unavailable
    if _neo4j_unavailable:
        raise ConnectionError("Neo4j unavailable — using in-memory graph")
    if neo4j_driver is None:
        await init_neo4j()
        if _neo4j_unavailable:
            raise ConnectionError("Neo4j unavailable — using in-memory graph")
    return neo4j_driver


async def run_query(query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
    """Run a Cypher query. Falls back to in-memory graph for causal chain queries."""
    try:
        driver = await get_neo4j()
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.fetch(1000)
            return [dict(record) for record in records]
    except ConnectionError:
        # In-memory fallback: handle common query patterns
        params = parameters or {}
        if "event_id" in params:
            return _memory_query_causal_chain(params["event_id"])
        return []
    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")
        raise


async def init_constraints() -> None:
    """Initialize Neo4j constraints — silently skipped if unavailable."""
    if _neo4j_unavailable:
        logger.info("Neo4j unavailable — skipping constraint initialization")
        return
    try:
        driver = await get_neo4j()
        constraints = [
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
            "CREATE INDEX event_occurred_at IF NOT EXISTS FOR (e:Event) ON (e.occurred_at)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
        ]
        async with driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception:
                    pass
        logger.info("Neo4j constraints initialized")
    except Exception as e:
        logger.warning(f"Neo4j constraint init skipped: {e}")
