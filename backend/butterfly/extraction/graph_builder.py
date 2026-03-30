"""Neo4j graph builder for causal knowledge graph."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime
import uuid

from butterfly.db.neo4j import get_neo4j, run_query
from butterfly.extraction.ner import ExtractedEntity
from butterfly.extraction.relations import ExtractedRelation
from butterfly.models.event import EventResponse


@dataclass
class GraphBuildResult:
    """Result of graph building operation."""

    nodes_created: int
    edges_created: int
    event_id: str
    timestamp: datetime


class GraphBuilder:
    """Build and manage Neo4j causal knowledge graph."""

    async def upsert_entity(self, entity: ExtractedEntity, event_id: str) -> str:
        """Upsert an entity node in Neo4j.

        Args:
            entity: Extracted entity
            event_id: ID of the event this entity came from

        Returns:
            Neo4j node ID
        """
        try:
            entity_id = f"entity_{uuid.uuid4().hex[:12]}"

            query = f"""
            MERGE (e:{entity.label} {{name: $name}})
            ON CREATE SET
                e.entity_id = $entity_id,
                e.label = $label,
                e.mention_count = 1,
                e.first_seen = datetime(),
                e.last_seen = datetime(),
                e.confidence = $confidence
            ON MATCH SET
                e.mention_count = e.mention_count + 1,
                e.last_seen = datetime()
            RETURN id(e) as node_id
            """

            result = await run_query(
                query,
                {
                    "name": entity.text,
                    "entity_id": entity_id,
                    "label": entity.label,
                    "confidence": entity.confidence,
                },
            )

            if result:
                return str(result[0]["node_id"])
            return entity_id

        except Exception as e:
            logger.error(f"Failed to upsert entity {entity.text}: {e}")
            raise

    async def upsert_relation(
        self, relation: ExtractedRelation, event_id: str
    ) -> str:
        """Upsert a relationship in Neo4j.

        Args:
            relation: Extracted relationship
            event_id: ID of the event this relation came from

        Returns:
            Relationship ID
        """
        try:
            rel_id = f"rel_{uuid.uuid4().hex[:12]}"

            query = f"""
            MATCH (source {{name: $source_name}})
            MATCH (target {{name: $target_name}})
            MERGE (source)-[r:{relation.relation_type}]->(target)
            ON CREATE SET
                r.rel_id = $rel_id,
                r.confidence = $confidence,
                r.mention_count = 1,
                r.first_seen = datetime(),
                r.last_seen = datetime(),
                r.evidence_paths = [$evidence]
            ON MATCH SET
                r.mention_count = r.mention_count + 1,
                r.last_seen = datetime(),
                r.evidence_paths = r.evidence_paths + [$evidence]
            RETURN id(r) as rel_id
            """

            result = await run_query(
                query,
                {
                    "source_name": relation.source_entity,
                    "target_name": relation.target_entity,
                    "rel_id": rel_id,
                    "confidence": relation.confidence,
                    "evidence": relation.evidence_text,
                },
            )

            if result:
                return str(result[0]["rel_id"])
            return rel_id

        except Exception as e:
            logger.error(
                f"Failed to upsert relation {relation.source_entity}->{relation.target_entity}: {e}"
            )
            raise

    async def link_event_to_entities(self, event_id: str, entity_ids: List[str]) -> None:
        """Link an event to extracted entities.

        Args:
            event_id: Event ID
            entity_ids: List of entity IDs
        """
        try:
            for entity_id in entity_ids:
                query = """
                MATCH (e:Event {event_id: $event_id})
                MATCH (ent {entity_id: $entity_id})
                MERGE (e)-[:MENTIONS]->(ent)
                """
                await run_query(query, {"event_id": event_id, "entity_id": entity_id})

        except Exception as e:
            logger.error(f"Failed to link event to entities: {e}")
            raise

    async def get_causal_chain(
        self, start_entity_id: str, max_hops: int = 4
    ) -> List[Dict[str, Any]]:
        """Get causal chain starting from an entity.

        Args:
            start_entity_id: Starting entity ID
            max_hops: Maximum number of hops

        Returns:
            List of paths in the causal chain
        """
        try:
            query = f"""
            MATCH path = (start {{entity_id: $entity_id}})-[:CAUSES|TRIGGERS|INFLUENCES*1..{max_hops}]->(end)
            RETURN path
            ORDER BY length(path) DESC
            LIMIT 100
            """

            result = await run_query(query, {"entity_id": start_entity_id})
            return result

        except Exception as e:
            logger.error(f"Failed to get causal chain: {e}")
            return []

    async def process_event(
        self,
        event: EventResponse,
        entities: List[ExtractedEntity],
        relations: List[ExtractedRelation],
    ) -> GraphBuildResult:
        """Process an event and build graph.

        Args:
            event: Event to process
            entities: Extracted entities
            relations: Extracted relationships

        Returns:
            Result of graph building
        """
        try:
            nodes_created = 0
            edges_created = 0

            # Create Event node
            event_query = """
            MERGE (e:Event {event_id: $event_id})
            ON CREATE SET
                e.title = $title,
                e.source = $source,
                e.occurred_at = $occurred_at,
                e.created_at = datetime()
            RETURN id(e) as node_id
            """

            await run_query(
                event_query,
                {
                    "event_id": event.event_id,
                    "title": event.title,
                    "source": event.source,
                    "occurred_at": event.occurred_at.isoformat(),
                },
            )
            nodes_created += 1

            # Upsert entities
            entity_ids = []
            for entity in entities:
                entity_id = await self.upsert_entity(entity, event.event_id)
                entity_ids.append(entity_id)
                nodes_created += 1

            # Link event to entities
            await self.link_event_to_entities(event.event_id, entity_ids)

            # Upsert relationships
            for relation in relations:
                rel_id = await self.upsert_relation(relation, event.event_id)
                edges_created += 1

            logger.info(
                f"Graph built for event {event.event_id}: {nodes_created} nodes, {edges_created} edges"
            )

            return GraphBuildResult(
                nodes_created=nodes_created,
                edges_created=edges_created,
                event_id=event.event_id,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")
            raise
