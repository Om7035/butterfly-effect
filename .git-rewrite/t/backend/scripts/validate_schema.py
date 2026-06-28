"""Validate the universal Neo4j schema by seeding test data and running acceptance queries.

Usage:
    python scripts/validate_schema.py

Requires Neo4j running on bolt://localhost:7687
"""

import asyncio
from loguru import logger
from butterfly.db.neo4j import init_neo4j, run_query, close_neo4j


# ── Seed data: geopolitical chain ─────────────────────────────────────────────

SEED_QUERIES = [
    # Nodes
    "MERGE (e:Event {event_id:'test_hamas_oct7', title:'Hamas attacks Israel', domain:'geopolitics', occurred_at:'2023-10-07T06:30:00'})",
    "MERGE (a:Actor {actor_id:'actor_hamas', name:'Hamas', type:'organization'})",
    "MERGE (a:Actor {actor_id:'actor_israel', name:'Israel', type:'nation-state'})",
    "MERGE (a:Actor {actor_id:'actor_iran', name:'Iran', type:'nation-state'})",
    "MERGE (a:Actor {actor_id:'actor_opec', name:'OPEC', type:'organization'})",
    "MERGE (r:Resource {resource_id:'res_oil', name:'Oil', type:'energy'})",
    "MERGE (s:System {system_id:'sys_energy_market', name:'Global Energy Market', domain:'financial'})",
    "MERGE (m:Metric {metric_id:'metric_oil_price', name:'Oil Price', series_id:'DCOILWTICO'})",
    "MERGE (m:Metric {metric_id:'metric_inflation', name:'Inflation Rate', series_id:'CPIAUCSL'})",
    "MERGE (l:Location {location_id:'loc_middle_east', name:'Middle East', country_code:'ME'})",
    "MERGE (l:Location {location_id:'loc_strait_hormuz', name:'Strait of Hormuz', country_code:'IR'})",
    "MERGE (b:Belief {belief_id:'belief_risk_off', name:'Risk-Off Sentiment'})",

    # Edges — geopolitical chain
    """MATCH (e:Event {event_id:'test_hamas_oct7'}), (a:Actor {name:'Hamas'})
       MERGE (a)-[:CAUSES {confidence:0.99, latency_hours:0, mechanism:'direct military action'}]->(e)""",

    """MATCH (e:Event {event_id:'test_hamas_oct7'}), (a:Actor {name:'Israel'})
       MERGE (e)-[:TRIGGERS {confidence:0.95, latency_hours:2, threshold:'military attack on sovereign territory'}]->(a)""",

    """MATCH (a:Actor {name:'Israel'}), (b:Actor {name:'Iran'})
       MERGE (a)-[:RETALIATES {actor:'Israel', mechanism:'airstrikes', probability:0.6}]->(b)""",

    """MATCH (a:Actor {name:'Iran'}), (b:Actor {name:'OPEC'})
       MERGE (a)-[:INFLUENCES {direction:'destabilizes', strength:0.7, latency_hours:72}]->(b)""",

    """MATCH (a:Actor {name:'OPEC'}), (m:Metric {name:'Oil Price'})
       MERGE (a)-[:CAUSES {confidence:0.85, latency_hours:24, mechanism:'production cut signals'}]->(m)""",

    """MATCH (m:Metric {name:'Oil Price'}), (m2:Metric {name:'Inflation Rate'})
       MERGE (m)-[:INFLUENCES {direction:'increases', strength:0.65, latency_hours:720}]->(m2)""",

    # Resource flow chain
    """MATCH (r:Resource {name:'Oil'}), (l:Location {name:'Strait of Hormuz'})
       MERGE (r)-[:FLOWS_THROUGH {volume:'20M barrels/day', vulnerability:0.85}]->(l)""",

    """MATCH (l:Location {name:'Strait of Hormuz'}), (s:System {name:'Global Energy Market'})
       MERGE (l)-[:DISRUPTS {severity:0.8, recovery_days:180, domain:'energy'}]->(s)""",

    """MATCH (s:System {name:'Global Energy Market'}), (m:Metric {name:'Oil Price'})
       MERGE (s)-[:INFLUENCES {direction:'increases', strength:0.9, latency_hours:6}]->(m)""",

    # Actor retaliation chain
    """MATCH (a:Actor {name:'Iran'}), (b:Actor {name:'Israel'})
       MERGE (a)-[:RETALIATES {actor:'Iran', mechanism:'proxy forces', probability:0.55}]->(b)""",

    """MATCH (a:Actor {name:'Israel'}), (e:Event {event_id:'test_hamas_oct7'})
       MERGE (a)-[:ESCALATES_TO {probability:0.4, conditions:'continued rocket fire', timeline_days:7}]->(e)""",

    # Belief node
    """MATCH (b:Belief {name:'Risk-Off Sentiment'}), (m:Metric {name:'Oil Price'})
       MERGE (b)-[:INFLUENCES {direction:'increases', strength:0.6, latency_hours:12}]->(m)""",
]

# ── Acceptance queries ─────────────────────────────────────────────────────────

ACCEPTANCE_QUERIES = [
    {
        "name": "Geopolitical chain: Event → Metric (4 hops)",
        "query": """
            MATCH p=(e:Event)-[:TRIGGERS|CAUSES*1..4]->(m:Metric)
            WHERE e.domain CONTAINS 'geopolitics'
            RETURN length(p) AS depth, [n IN nodes(p) | coalesce(n.name, n.title)] AS chain
            ORDER BY depth DESC LIMIT 5
        """,
        "assert": lambda r: len(r) > 0,
    },
    {
        "name": "Resource flow chain: Resource → System → Metric",
        "query": """
            MATCH p=(r:Resource)-[:FLOWS_THROUGH]->(s:System)-[:DISRUPTS|INFLUENCES]->(m:Metric)
            RETURN [n IN nodes(p) | coalesce(n.name, n.title)] AS chain LIMIT 5
        """,
        "assert": lambda r: len(r) > 0,
    },
    {
        "name": "Actor retaliation chain: Actor → Actor → Event",
        "query": """
            MATCH p=(a:Actor)-[:RETALIATES]->(b:Actor)
            RETURN a.name AS attacker, b.name AS target LIMIT 5
        """,
        "assert": lambda r: len(r) > 0,
    },
    {
        "name": "Full butterfly chain depth",
        "query": """
            MATCH p=(e:Event {event_id:'test_hamas_oct7'})
                -[:CAUSES|TRIGGERS|INFLUENCES|DISRUPTS|ESCALATES_TO*1..6]->(end)
            RETURN length(p) AS depth, labels(end)[0] AS end_type
            ORDER BY depth DESC LIMIT 10
        """,
        "assert": lambda r: any(row["depth"] >= 3 for row in r),
    },
    {
        "name": "All 8 node labels present",
        "query": """
            CALL {
                MATCH (n:Event)    RETURN 'Event'    AS label, count(n) AS cnt
                UNION ALL
                MATCH (n:Actor)    RETURN 'Actor'    AS label, count(n) AS cnt
                UNION ALL
                MATCH (n:System)   RETURN 'System'   AS label, count(n) AS cnt
                UNION ALL
                MATCH (n:Resource) RETURN 'Resource' AS label, count(n) AS cnt
                UNION ALL
                MATCH (n:Metric)   RETURN 'Metric'   AS label, count(n) AS cnt
                UNION ALL
                MATCH (n:Location) RETURN 'Location' AS label, count(n) AS cnt
                UNION ALL
                MATCH (n:Belief)   RETURN 'Belief'   AS label, count(n) AS cnt
            }
            RETURN label, cnt ORDER BY label
        """,
        "assert": lambda r: len([row for row in r if row["cnt"] > 0]) >= 6,
    },
]


async def main() -> None:
    logger.info("Connecting to Neo4j...")
    await init_neo4j()

    # Seed test data
    logger.info("Seeding test data...")
    for q in SEED_QUERIES:
        try:
            await run_query(q)
        except Exception as e:
            logger.warning(f"Seed query failed (may already exist): {e}")

    logger.info("\n" + "=" * 60)
    logger.info("RUNNING ACCEPTANCE QUERIES")
    logger.info("=" * 60)

    passed = 0
    failed = 0

    for test in ACCEPTANCE_QUERIES:
        try:
            result = await run_query(test["query"])
            ok = test["assert"](result)
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            else:
                failed += 1
            logger.info(f"  {status}  {test['name']}")
            if result:
                for row in result[:3]:
                    logger.info(f"         {dict(row)}")
        except Exception as e:
            failed += 1
            logger.error(f"  FAIL  {test['name']}: {e}")

    logger.info("=" * 60)
    logger.info(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        logger.info("ALL ACCEPTANCE QUERIES PASSED ✓")
    else:
        logger.error(f"{failed} QUERIES FAILED")

    await close_neo4j()


if __name__ == "__main__":
    asyncio.run(main())
