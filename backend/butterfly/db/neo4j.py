"""Neo4j graph database connection and utilities.

Falls back gracefully when Neo4j is unavailable — the app starts and runs
with an in-memory NetworkX graph instead.
"""

from typing import Optional, List, Dict, Any

import networkx as nx
from loguru import logger

from butterfly.config import settings

neo4j_driver = None
_neo4j_unavailable: bool = False

# ── In-memory fallback ────────────────────────────────────────────────────────
_memory_graph: nx.MultiDiGraph = nx.MultiDiGraph()


def _memory_store_node(label: str, props: dict) -> None:
    node_id = props.get("event_id") or props.get("entity_id") or props.get("name", str(id(props)))
    _memory_graph.add_node(node_id, label=label, **props)


def _memory_query_causal_chain(event_id: str, max_hops: int = 4) -> list[dict]:
    if event_id not in _memory_graph:
        return []
    results = []
    visited: set = set()
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
        )
        async with neo4j_driver.session() as session:
            await session.run("RETURN 1")
        _neo4j_unavailable = False
        logger.info("Neo4j connection established")
        return neo4j_driver
    except Exception as e:
        logger.warning(f"Neo4j unavailable — using in-memory graph fallback: {type(e).__name__}: {e}")
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
        raise ConnectionError("Neo4j unavailable")
    if neo4j_driver is None:
        await init_neo4j()
        if _neo4j_unavailable:
            raise ConnectionError("Neo4j unavailable")
    return neo4j_driver


async def run_query(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
    """Run a Cypher query. Falls back to in-memory graph on connection error."""
    try:
        driver = await get_neo4j()
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.fetch(1000)
            return [dict(record) for record in records]
    except ConnectionError:
        params = parameters or {}
        if "event_id" in params:
            return _memory_query_causal_chain(params["event_id"])
        return []
    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")
        return []


async def init_constraints() -> None:
    """Initialize Neo4j constraints — silently skipped if unavailable."""
    if _neo4j_unavailable:
        logger.info("Neo4j unavailable — skipping constraint initialization")
        return
    constraints = [
        "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
        "CREATE INDEX event_occurred_at IF NOT EXISTS FOR (e:Event) ON (e.occurred_at)",
        "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
    ]
    try:
        driver = await get_neo4j()
        async with driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception:
                    pass
        logger.info("Neo4j constraints initialized")
    except Exception as e:
        logger.warning(f"Neo4j constraint init skipped: {e}")
