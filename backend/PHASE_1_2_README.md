# Phase 1 & 2 — Data Pipeline & Knowledge Graph

## Phase 1: Data Pipeline ✅

### What was built:

1. **Database Layer** (`butterfly/db/`)
   - `postgres.py` — Async SQLAlchemy engine with session management
   - `redis.py` — Redis cache client for deduplication
   - `neo4j.py` — Neo4j driver with constraint initialization

2. **Event Model** (`butterfly/models/event.py`)
   - Pydantic models for API validation
   - SQLAlchemy ORM for PostgreSQL storage
   - Automatic ID generation and timestamps

3. **Data Ingesters** (`butterfly/ingestion/`)
   - `base.py` — Abstract base class for all ingesters
   - `fred.py` — FRED API ingester (5 economic series)
   - `gdelt.py` — GDELT API ingester (4 themes)
   - `scheduler.py` — Celery tasks for periodic ingestion

4. **Celery Worker** (`butterfly/worker.py`)
   - Beat schedule: FRED every 15 min, GDELT every 15 min
   - Async task execution with error handling
   - Result backend for job tracking

5. **API Routes** (`butterfly/api/events.py`)
   - `POST /api/v1/events` — Create new event
   - `GET /api/v1/events` — List events (paginated)
   - `GET /api/v1/events/{event_id}` — Get single event

6. **Tests** (`backend/tests/test_ingestion/`, `backend/tests/test_api/`)
   - FRED ingester tests with mocked API
   - GDELT ingester tests with deduplication
   - Event API tests

### How to run Phase 1:

```bash
# 1. Start Docker services
docker compose up -d

# 2. Install dependencies
cd backend
pip install -r requirements.txt

# 3. Run the API
uvicorn butterfly.main:app --reload

# 4. In another terminal, start Celery worker
celery -A butterfly.worker worker --loglevel=info

# 5. In another terminal, start Celery beat (scheduler)
celery -A butterfly.worker beat --loglevel=info

# 6. Check health
curl http://localhost:8000/health

# 7. Create an event
curl -X POST http://localhost:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Fed raises rates",
    "description": "FOMC decision",
    "source": "manual",
    "occurred_at": "2024-01-15T14:00:00Z",
    "raw_text": "The Federal Reserve raised rates by 25 basis points."
  }'

# 8. List events
curl http://localhost:8000/api/v1/events

# 9. Run tests
pytest tests/test_ingestion/ -v
pytest tests/test_api/ -v
```

### Phase 1 Success Criteria:
- ✅ 50+ events ingested within 30 minutes
- ✅ Events stored in PostgreSQL
- ✅ Deduplication working (Redis cache)
- ✅ All tests passing
- ✅ Health endpoint returns all services healthy

---

## Phase 2: Knowledge Graph ✅

### What was built:

1. **NER Pipeline** (`butterfly/extraction/ner.py`)
   - spaCy-based entity extraction
   - Label mapping: ORG/GPE/PERSON → Entity, MONEY/PERCENT → Metric, LAW → Policy
   - Entity normalization (Fed → Federal Reserve, US → United States)
   - Confidence scoring per entity type

2. **Relationship Extraction** (`butterfly/extraction/relations.py`)
   - Strategy A: Pattern matching for causal language
     - "X caused Y", "X led to Y", "X triggered Y", etc.
     - High precision (0.8-0.95 confidence)
   - Strategy B: Co-occurrence + proximity
     - Entities within 50 tokens with directional verbs
     - Lower precision (0.5 confidence) → tagged as CORRELATES_WITH
   - Confidence threshold: 0.4 minimum

3. **Entity Normalizer** (`butterfly/extraction/normalizer.py`)
   - Canonical mappings for common entities
   - Case-insensitive lookup
   - Fallback to original if no mapping

4. **Graph Builder** (`butterfly/extraction/graph_builder.py`)
   - `upsert_entity()` — Create/update entity nodes
   - `upsert_relation()` — Create/update relationship edges
   - `link_event_to_entities()` — Connect events to entities
   - `get_causal_chain()` — Query 3+ hop causal paths
   - `process_event()` — Full pipeline: extract → build graph

5. **Neo4j Schema**
   - Node labels: Event, Entity, Metric, Policy
   - Relationship types: MENTIONS, CAUSES, TRIGGERS, INFLUENCES, CORRELATES_WITH
   - Constraints: unique event_id, entity_id
   - Indexes: on occurred_at, name, strength_score

6. **Tests** (`backend/tests/test_extraction/`)
   - NER tests: entity extraction, normalization, multiple types
   - Relation tests: causal patterns, correlations, confidence filtering

### How to run Phase 2:

```bash
# 1. Ensure Phase 1 is running (Docker, API, Celery)

# 2. Download spaCy model (if not already installed)
python -m spacy download en_core_web_sm
# Or for better accuracy:
python -m spacy download en_core_web_trf

# 3. Test NER extraction
python -c "
from butterfly.extraction.ner import EntityExtractor
import asyncio

extractor = EntityExtractor()
text = 'The Federal Reserve raised interest rates in June 2022.'
entities = extractor.extract(text)
for e in entities:
    print(f'{e.text} ({e.label}): {e.confidence:.2f}')
"

# 4. Test relationship extraction
python -c "
from butterfly.extraction.relations import RelationExtractor
from butterfly.extraction.ner import EntityExtractor, ExtractedEntity

extractor = RelationExtractor()
text = 'The Federal Reserve raised rates, which led to higher mortgage rates.'
entities = [
    ExtractedEntity('Federal Reserve', 'Entity', 4, 20, 0.95),
    ExtractedEntity('mortgage rates', 'Metric', 70, 84, 0.85),
]
relations = extractor.extract_relations(text, entities)
for r in relations:
    print(f'{r.source_entity} --{r.relation_type}--> {r.target_entity} ({r.confidence:.2f})')
"

# 5. Test graph building
python -c "
import asyncio
from butterfly.extraction.graph_builder import GraphBuilder
from butterfly.models.event import EventResponse
from butterfly.extraction.ner import ExtractedEntity
from butterfly.extraction.relations import ExtractedRelation
from datetime import datetime

async def test():
    builder = GraphBuilder()
    
    event = EventResponse(
        event_id='test_event',
        title='Test Event',
        description='Test',
        source='manual',
        source_url=None,
        occurred_at=datetime.utcnow(),
        raw_text='Test',
        entities=[],
        processed=False,
        created_at=datetime.utcnow(),
        updated_at=None,
    )
    
    entities = [
        ExtractedEntity('Federal Reserve', 'Entity', 0, 16, 0.95),
        ExtractedEntity('Interest Rates', 'Metric', 30, 44, 0.85),
    ]
    
    relations = [
        ExtractedRelation('Federal Reserve', 'Interest Rates', 'INFLUENCES', 0.9, 'raised rates'),
    ]
    
    result = await builder.process_event(event, entities, relations)
    print(f'Graph built: {result.nodes_created} nodes, {result.edges_created} edges')

asyncio.run(test())
"

# 6. Query Neo4j directly
# Open http://localhost:7474 and run:
MATCH (n) RETURN labels(n), count(n)
# Should see Event, Entity, Metric nodes

# 7. Test 3-hop query
MATCH path = (e:Event)-[:CAUSES|TRIGGERS|INFLUENCES*1..3]->(m:Metric)
RETURN path LIMIT 5

# 8. Run extraction tests
pytest tests/test_extraction/ -v
```

### Phase 2 Success Criteria:
- ✅ Entities extracted from event text
- ✅ Entity normalization working (Fed → Federal Reserve)
- ✅ Relationships extracted with confidence scores
- ✅ Entities and relationships stored in Neo4j
- ✅ 3-hop causal chains queryable
- ✅ All tests passing

---

## Architecture Overview

```
Event (PostgreSQL)
    ↓
    ├─→ NER Pipeline (spaCy)
    │   └─→ ExtractedEntity[]
    │
    ├─→ Relation Extraction
    │   └─→ ExtractedRelation[]
    │
    └─→ Graph Builder
        ├─→ Upsert entities to Neo4j
        ├─→ Upsert relationships to Neo4j
        └─→ Link event to entities
```

## Data Flow

1. **Ingestion** (Phase 1)
   - FRED API → Event (PostgreSQL)
   - GDELT API → Event (PostgreSQL)
   - Manual submission → Event (PostgreSQL)

2. **Extraction** (Phase 2)
   - Event.raw_text → NER → ExtractedEntity[]
   - ExtractedEntity[] → Relation Extraction → ExtractedRelation[]

3. **Graph Building** (Phase 2)
   - ExtractedEntity[] → Neo4j nodes
   - ExtractedRelation[] → Neo4j edges
   - Event → Neo4j node
   - Event -[:MENTIONS]-> Entity

## Next Steps (Phase 3)

Phase 3 will build the **Causal Core**:
- pgmpy DAG builder from Neo4j graph
- DoWhy causal identification
- Counterfactual diff engine
- Validation against historical data

The knowledge graph built in Phase 2 is the foundation for all causal inference in Phase 3.
