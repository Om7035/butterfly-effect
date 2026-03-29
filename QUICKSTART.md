# butterfly-effect Quick Start Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- pip

## 5-Minute Setup

### 1. Start Docker Services

```bash
docker compose up -d
```

Verify all services are healthy:
```bash
docker compose ps
# All should show "healthy"
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Download spaCy Model (for NLP)

```bash
python -m spacy download en_core_web_sm
```

### 4. Start the API

```bash
uvicorn butterfly.main:app --reload
```

The API will be available at `http://localhost:8000`

### 5. In Another Terminal: Start Celery Worker

```bash
cd backend
celery -A butterfly.worker worker --loglevel=info
```

### 6. In Another Terminal: Start Celery Beat (Scheduler)

```bash
cd backend
celery -A butterfly.worker beat --loglevel=info
```

## Testing the System

### Check Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "postgres": true,
  "redis": true,
  "neo4j": true
}
```

### Create an Event

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Federal Reserve raises rates",
    "description": "FOMC decision to raise benchmark rate by 25 basis points",
    "source": "manual",
    "occurred_at": "2024-01-15T14:00:00Z",
    "raw_text": "The Federal Reserve raised its benchmark interest rate by 25 basis points to combat inflation."
  }'
```

Expected response:
```json
{
  "event_id": "event_abc123def456",
  "status": "processing",
  "created_at": "2024-01-15T14:05:00.123456"
}
```

### List Events

```bash
curl http://localhost:8000/api/v1/events
```

### Get Single Event

```bash
curl http://localhost:8000/api/v1/events/event_abc123def456
```

## Running Tests

### Test Ingestion

```bash
cd backend
pytest tests/test_ingestion/ -v
```

### Test Extraction

```bash
cd backend
pytest tests/test_extraction/ -v
```

### Test API

```bash
cd backend
pytest tests/test_api/ -v
```

### Run All Tests

```bash
cd backend
pytest tests/ -v
```

## Monitoring

### View API Logs

The API logs are printed to stdout. Look for:
- `INFO` — Normal operations
- `WARNING` — Potential issues
- `ERROR` — Failures

### View Celery Logs

The Celery worker logs show:
- Task execution
- Ingestion results
- Errors

### View Database Logs

```bash
docker compose logs postgres
docker compose logs redis
docker compose logs neo4j
```

## Accessing Databases

### PostgreSQL

```bash
docker compose exec postgres psql -U butterfly -d butterfly
```

Query events:
```sql
SELECT event_id, title, source, created_at FROM events LIMIT 10;
```

### Redis

```bash
docker compose exec redis redis-cli
```

Check cache:
```
KEYS *
GET fred:FEDFUNDS:last_value
```

### Neo4j

Open browser: `http://localhost:7474`

Default credentials:
- Username: `neo4j`
- Password: `butterfly_dev`

Query entities:
```cypher
MATCH (n) RETURN labels(n), count(n)
```

Query causal chains:
```cypher
MATCH path = (e:Event)-[:CAUSES|TRIGGERS|INFLUENCES*1..3]->(m:Metric)
RETURN path LIMIT 5
```

## Stopping Services

### Stop All Services

```bash
docker compose down
```

### Stop Only API

Press `Ctrl+C` in the API terminal

### Stop Only Celery

Press `Ctrl+C` in the Celery terminal

## Troubleshooting

### "Connection refused" on localhost:8000

- Make sure the API is running: `uvicorn butterfly.main:app --reload`
- Check that port 8000 is not in use: `lsof -i :8000`

### "PostgreSQL connection failed"

- Check Docker: `docker compose ps`
- Verify PostgreSQL is healthy: `docker compose logs postgres`
- Restart: `docker compose restart postgres`

### "Redis connection failed"

- Check Docker: `docker compose ps`
- Verify Redis is healthy: `docker compose logs redis`
- Restart: `docker compose restart redis`

### "Neo4j connection failed"

- Check Docker: `docker compose ps`
- Verify Neo4j is healthy: `docker compose logs neo4j`
- Restart: `docker compose restart neo4j`
- Access browser: `http://localhost:7474`

### "spaCy model not found"

```bash
python -m spacy download en_core_web_sm
```

### Tests failing

1. Make sure all services are running: `docker compose ps`
2. Make sure dependencies are installed: `pip install -r requirements.txt`
3. Run with verbose output: `pytest tests/ -vv`

## Next Steps

1. **Set up FRED API key** (optional, for real data)
   - Get key at: https://fred.stlouisfed.org/docs/api/api_key.html
   - Add to `.env`: `FRED_API_KEY=your_key_here`

2. **Explore the code**
   - Start with `backend/butterfly/main.py`
   - Then `backend/butterfly/ingestion/`
   - Then `backend/butterfly/extraction/`

3. **Read the documentation**
   - `context.md` — Architecture and decisions
   - `phases.md` — Full build plan
   - `backend/PHASE_1_2_README.md` — Detailed Phase 1 & 2 guide

4. **Build Phase 3** — Causal inference
   - pgmpy DAG builder
   - DoWhy causal identification
   - Counterfactual diff engine

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

## Key Files

- `backend/butterfly/main.py` — FastAPI app
- `backend/butterfly/ingestion/fred.py` — FRED data ingester
- `backend/butterfly/ingestion/gdelt.py` — GDELT data ingester
- `backend/butterfly/extraction/ner.py` — Entity extraction
- `backend/butterfly/extraction/relations.py` — Relationship extraction
- `backend/butterfly/extraction/graph_builder.py` — Neo4j graph builder
- `backend/butterfly/api/events.py` — Event API routes

## Support

For issues or questions:
1. Check `IMPLEMENTATION_STATUS.md` for current status
2. Read `backend/PHASE_1_2_README.md` for detailed guides
3. Review `context.md` for architecture decisions
4. Check test files for usage examples

---

**Happy building! 🦋**
