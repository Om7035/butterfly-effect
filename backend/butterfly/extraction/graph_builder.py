"""Universal Neo4j graph builder.

Maps extracted entities and relations to the universal ontology:
  Nodes:  Event, Actor, System, Resource, Metric, Policy, Location, Belief
  Edges:  14 relationship types with full property sets
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime
import uuid

from butterfly.db.neo4j import run_query
from butterfly.extraction.ner import ExtractedEntity, EntityExtractor
from butterfly.extraction.relations import ExtractedRelation, RelationExtractor


@dataclass
class GraphBuildResult:
    nodes_created: int
    edges_created: int
    event_id: str
    timestamp: datetime


# ── Node label → ID field name ────────────────────────────────────────────────

_LABEL_ID_FIELD: dict[str, str] = {
    "Event":    "event_id",
    "Actor":    "actor_id",
    "System":   "system_id",
    "Resource": "resource_id",
    "Metric":   "metric_id",
    "Policy":   "policy_id",
    "Location": "location_id",
    "Belief":   "belief_id",
    # Legacy
    "Entity":   "entity_id",
}

# ── Relationship property sets ────────────────────────────────────────────────

_REL_REQUIRED_PROPS: dict[str, list[str]] = {
    "CAUSES":         ["confidence", "latency_hours", "mechanism"],
    "TRIGGERS":       ["confidence", "latency_hours"],
    "INFLUENCES":     ["direction", "strength", "latency_hours"],
    "DISRUPTS":       ["severity", "recovery_days", "domain"],
    "DEPENDS_ON":     ["criticality", "substitutability"],
    "ESCALATES_TO":   ["probability", "conditions"],
    "DISPLACES":      ["volume", "destination"],
    "RETALIATES":     ["actor", "mechanism", "probability"],
    "SUBSTITUTES":    ["cost_premium", "feasibility"],
    "SANCTIONED_BY":  ["imposer", "mechanism", "start_date"],
    "FLOWS_THROUGH":  ["volume", "vulnerability"],
    "BELIEVES":       ["sentiment", "actor_count"],
    "CORRELATES_WITH":["r_squared", "lag_days"],
    "CAUSED_BY":      ["validated", "method"],
    "SIMULATED_REACTION": ["agent_type", "step", "magnitude"],
    "MENTIONS":       ["context", "relevance"],
    "INFLUENCES":     ["direction", "strength", "latency_hours"],
}

# Default property values when not extractable from text
_REL_DEFAULTS: dict[str, dict[str, Any]] = {
    "CAUSES":         {"confidence": 0.7, "latency_hours": 48, "mechanism": "direct causal pathway"},
    "TRIGGERS":       {"confidence": 0.7, "latency_hours": 24, "threshold": "unspecified"},
    "INFLUENCES":     {"direction": "increases", "strength": 0.5, "latency_hours": 48},
    "DISRUPTS":       {"severity": 0.5, "recovery_days": 30, "domain": "general"},
    "DEPENDS_ON":     {"criticality": 0.5, "substitutability": 0.5, "dependency_type": "operational"},
    "ESCALATES_TO":   {"probability": 0.3, "conditions": "unspecified", "timeline_days": 30},
    "DISPLACES":      {"volume": "unspecified", "destination": "unspecified"},
    "RETALIATES":     {"actor": "unspecified", "mechanism": "unspecified", "probability": 0.4},
    "SUBSTITUTES":    {"cost_premium": 0.2, "feasibility": 0.6, "timeline_days": 90},
    "SANCTIONED_BY":  {"imposer": "unspecified", "mechanism": "economic", "start_date": "unspecified", "scope": "partial"},
    "FLOWS_THROUGH":  {"volume": "unspecified", "vulnerability": 0.5},
    "BELIEVES":       {"sentiment": 0.0, "actor_count": 0, "intensity": 0.5},
    "CORRELATES_WITH":{"r_squared": 0.5, "lag_days": 0, "sample_size": 0},
    "CAUSED_BY":      {"validated": False, "method": "observational", "confidence": 0.6},
}


class GraphBuilder:
    """Build and manage the universal causal knowledge graph in Neo4j."""

    # ── Public API ────────────────────────────────────────────────────────────

    async def upsert_universal_entity(
        self, entity: ExtractedEntity, event_id: str
    ) -> str:
        """Upsert any entity type into Neo4j using the universal ontology.

        Returns the node's ID field value.
        """
        label = entity.label
        id_field = _LABEL_ID_FIELD.get(label, "entity_id")
        node_id = f"{label.lower()}_{uuid.uuid4().hex[:12]}"

        # Build extra properties based on label
        extra_props: dict[str, Any] = {}
        if label == "Actor" and entity.actor_type:
            extra_props["type"] = entity.actor_type
        if label == "Resource" and entity.resource_type:
            extra_props["type"] = entity.resource_type
        if label == "System" and entity.system_domain:
            extra_props["domain"] = entity.system_domain

        extra_set = "".join(
            f"\n                e.{k} = ${k},"
            for k in extra_props
        ).rstrip(",")

        query = f"""
        MERGE (e:{label} {{name: $name}})
        ON CREATE SET
            e.{id_field} = $node_id,
            e.mention_count = 1,
            e.first_seen = datetime(),
            e.last_seen = datetime(),
            e.confidence = $confidence{extra_set}
        ON MATCH SET
            e.mention_count = e.mention_count + 1,
            e.last_seen = datetime()
        RETURN e.{id_field} AS nid
        """

        params: dict[str, Any] = {
            "name": entity.text,
            "node_id": node_id,
            "confidence": entity.confidence,
            **extra_props,
        }

        try:
            result = await run_query(query, params)
            return str(result[0]["nid"]) if result else node_id
        except Exception as e:
            logger.error(f"upsert_universal_entity failed for {entity.text}: {e}")
            return node_id

    async def upsert_universal_relation(
        self, relation: ExtractedRelation, event_id: str
    ) -> str:
        """Upsert any of the 14 relationship types into Neo4j."""
        rel_type = relation.relation_type
        rel_id = f"rel_{uuid.uuid4().hex[:12]}"

        # Build property dict: start with defaults, overlay extracted values
        props: dict[str, Any] = dict(_REL_DEFAULTS.get(rel_type, {}))
        props["rel_id"] = rel_id
        props["event_id"] = event_id
        props["mention_count"] = 1
        props["first_seen"] = "datetime()"  # handled in Cypher

        # Overlay extracted values
        if relation.confidence:
            props["confidence"] = relation.confidence
        if relation.latency_hours is not None:
            props["latency_hours"] = relation.latency_hours
        if relation.direction:
            props["direction"] = relation.direction
        if relation.strength is not None:
            props["strength"] = relation.strength
        if relation.mechanism:
            props["mechanism"] = relation.mechanism
        if relation.severity is not None:
            props["severity"] = relation.severity
        if relation.probability is not None:
            props["probability"] = relation.probability
        if relation.volume:
            props["volume"] = relation.volume
        if relation.destination:
            props["destination"] = relation.destination
        if relation.vulnerability is not None:
            props["vulnerability"] = relation.vulnerability
        if relation.criticality is not None:
            props["criticality"] = relation.criticality
        if relation.substitutability is not None:
            props["substitutability"] = relation.substitutability
        if relation.cost_premium is not None:
            props["cost_premium"] = relation.cost_premium
        if relation.feasibility is not None:
            props["feasibility"] = relation.feasibility
        if relation.sentiment is not None:
            props["sentiment"] = relation.sentiment
        if relation.r_squared is not None:
            props["r_squared"] = relation.r_squared
        if relation.validated:
            props["validated"] = relation.validated

        # Remove datetime placeholder — set in Cypher
        props.pop("first_seen", None)

        set_clause = ", ".join(f"r.{k} = ${k}" for k in props if k != "mention_count")

        query = f"""
        MATCH (src {{name: $src_name}})
        MATCH (tgt {{name: $tgt_name}})
        MERGE (src)-[r:{rel_type}]->(tgt)
        ON CREATE SET
            {set_clause},
            r.mention_count = 1,
            r.first_seen = datetime(),
            r.last_seen = datetime(),
            r.evidence = $evidence
        ON MATCH SET
            r.mention_count = r.mention_count + 1,
            r.last_seen = datetime(),
            r.evidence = $evidence
        RETURN r.rel_id AS rid
        """

        params: dict[str, Any] = {
            "src_name": relation.source_entity,
            "tgt_name": relation.target_entity,
            "evidence": relation.evidence_text,
            **props,
        }

        try:
            result = await run_query(query, params)
            return str(result[0]["rid"]) if result else rel_id
        except Exception as e:
            logger.error(
                f"upsert_universal_relation failed "
                f"{relation.source_entity}-[{rel_type}]->{relation.target_entity}: {e}"
            )
            return rel_id

    async def process_event(
        self,
        event_id: str,
        title: str,
        source: str,
        occurred_at: datetime,
        raw_text: str,
        domain: Optional[str] = None,
    ) -> str:
        """Create or update an Event node in Neo4j."""
        query = """
        MERGE (e:Event {event_id: $event_id})
        ON CREATE SET
            e.title = $title,
            e.source = $source,
            e.occurred_at = $occurred_at,
            e.domain = $domain,
            e.created_at = datetime()
        ON MATCH SET
            e.title = $title,
            e.domain = $domain
        RETURN e.event_id AS eid
        """
        try:
            await run_query(query, {
                "event_id": event_id,
                "title": title,
                "source": source,
                "occurred_at": occurred_at.isoformat(),
                "domain": domain or "general",
            })
            return event_id
        except Exception as e:
            logger.error(f"process_event failed for {event_id}: {e}")
            return event_id

    async def link_event_to_entity(
        self, event_id: str, entity_name: str, relevance: float = 0.8
    ) -> None:
        """Create MENTIONS edge from Event to entity node."""
        query = """
        MATCH (e:Event {event_id: $event_id})
        MATCH (ent {name: $entity_name})
        MERGE (e)-[r:MENTIONS]->(ent)
        ON CREATE SET r.relevance = $relevance, r.context = "extracted"
        """
        try:
            await run_query(query, {
                "event_id": event_id,
                "entity_name": entity_name,
                "relevance": relevance,
            })
        except Exception as e:
            logger.debug(f"link_event_to_entity: {e}")

    async def build_from_text(
        self,
        event_id: str,
        title: str,
        source: str,
        occurred_at: datetime,
        raw_text: str,
        domain: Optional[str] = None,
    ) -> GraphBuildResult:
        """Full pipeline: text → entities → relations → Neo4j graph.

        This is the main entry point for processing any event text.
        """
        nodes_created = 0
        edges_created = 0

        # 1. Create Event node
        await self.process_event(event_id, title, source, occurred_at, raw_text, domain)
        nodes_created += 1

        # 2. Extract entities
        extractor = EntityExtractor()
        entities = extractor.extract(raw_text)
        logger.info(f"Extracted {len(entities)} entities from event {event_id}")

        # 3. Upsert entity nodes
        for entity in entities:
            await self.upsert_universal_entity(entity, event_id)
            await self.link_event_to_entity(event_id, entity.text)
            nodes_created += 1

        # 4. Extract relations
        rel_extractor = RelationExtractor()
        relations = rel_extractor.extract_relations(raw_text, entities)
        logger.info(f"Extracted {len(relations)} relations from event {event_id}")

        # 5. Upsert relation edges
        for relation in relations:
            # Enrich latency from text if not already set
            if relation.latency_hours is None:
                relation.latency_hours = extractor.extract_latency(
                    relation.evidence_text, domain or "default"
                )
            await self.upsert_universal_relation(relation, event_id)
            edges_created += 1

        logger.info(
            f"Graph built for {event_id}: {nodes_created} nodes, {edges_created} edges"
        )
        return GraphBuildResult(
            nodes_created=nodes_created,
            edges_created=edges_created,
            event_id=event_id,
            timestamp=datetime.utcnow(),
        )

    async def get_causal_chain(
        self, event_id: str, max_hops: int = 5
    ) -> List[Dict[str, Any]]:
        """Traverse the causal chain from an event up to max_hops deep."""
        query = f"""
        MATCH path = (e:Event {{event_id: $event_id}})
            -[:CAUSES|TRIGGERS|INFLUENCES|DISRUPTS|ESCALATES_TO*1..{max_hops}]->
            (end)
        RETURN
            [n IN nodes(path) | {{
                id: coalesce(n.event_id, n.actor_id, n.metric_id, n.system_id,
                             n.resource_id, n.policy_id, n.location_id, n.belief_id,
                             n.entity_id, id(n)),
                label: labels(n)[0],
                name: coalesce(n.name, n.title, 'unknown')
            }}] AS nodes,
            [r IN relationships(path) | {{
                type: type(r),
                confidence: r.confidence,
                latency_hours: r.latency_hours,
                mechanism: r.mechanism,
                direction: r.direction
            }}] AS edges,
            length(path) AS depth
        ORDER BY depth DESC
        LIMIT 50
        """
        try:
            return await run_query(query, {"event_id": event_id})
        except Exception as e:
            logger.error(f"get_causal_chain failed: {e}")
            return []

    # ── Legacy compatibility ──────────────────────────────────────────────────

    async def upsert_entity(self, entity: ExtractedEntity, event_id: str) -> str:
        """Legacy method — delegates to upsert_universal_entity."""
        return await self.upsert_universal_entity(entity, event_id)

    async def upsert_relation(
        self, relation: ExtractedRelation, event_id: str
    ) -> str:
        """Legacy method — delegates to upsert_universal_relation."""
        return await self.upsert_universal_relation(relation, event_id)
