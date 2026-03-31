"""Neo4j graph database connection and utilities."""

from typing import Any

from loguru import logger
from neo4j import AsyncDriver, AsyncGraphDatabase

from butterfly.config import settings

neo4j_driver: AsyncDriver | None = None
_neo4j_unavailable: bool = False  # cached unavailability to skip retries


async def init_neo4j() -> AsyncDriver | None:
    """Initialize Neo4j driver."""
    global neo4j_driver, _neo4j_unavailable
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=3.0,   # fail fast — don't wait 30s
            max_connection_lifetime=300,
        )
        async with neo4j_driver.session() as session:
            await session.run("RETURN 1")
        _neo4j_unavailable = False
        logger.info("Neo4j connection established")
        return neo4j_driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        neo4j_driver = None
        _neo4j_unavailable = True
        raise


async def close_neo4j() -> None:
    """Close Neo4j driver."""
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        logger.info("Neo4j connection closed")


async def get_neo4j() -> AsyncDriver:
    """Get Neo4j driver. Raises immediately if known unavailable."""
    global neo4j_driver, _neo4j_unavailable
    if _neo4j_unavailable:
        raise ConnectionError("Neo4j is unavailable (cached)")
    if neo4j_driver is None:
        neo4j_driver = await init_neo4j()
    return neo4j_driver


async def run_query(query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
    """Run a Cypher query and return results."""
    try:
        driver = await get_neo4j()
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.fetch(1000)  # Fetch up to 1000 records
            return [dict(record) for record in records]
    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")
        raise


async def init_constraints() -> None:
    """Initialize Neo4j constraints and indexes."""
    constraints = [
        "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
        "CREATE INDEX event_occurred_at IF NOT EXISTS FOR (e:Event) ON (e.occurred_at)",
        "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
        "CREATE INDEX causal_edge_strength IF NOT EXISTS FOR (c:CausalEdge) ON (c.strength_score)",
    ]

    try:
        driver = await get_neo4j()
        async with driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                    logger.debug(f"Constraint/Index created: {constraint[:50]}...")
                except Exception as e:
                    # Constraint might already exist
                    logger.debug(f"Constraint/Index already exists or error: {e}")
        logger.info("Neo4j constraints and indexes initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j constraints: {e}")
        raise
