# Quick Reference Guide

## Start Everything

```bash
# Terminal 1: Backend
cd backend
uvicorn butterfly.main:app --reload

# Terminal 2: Frontend  
cd frontend
npm run dev
```

Open: http://localhost:3000

## Routes

| Route | Purpose | Backend | Data Source |
|-------|---------|---------|-------------|
| `/` | Landing page | ❌ | None |
| `/analyze?q=...` | Real analysis | ✅ Required | SSE stream |
| `/demo` | Demo mode | ❌ | Pre-loaded |

## User Flows

### Normal Flow (Real Backend)
```
Landing (/) 
  → Type question 
  → /analyze?q=... 
  → SSE stream from backend 
  → Interactive graph
```

### Demo Flow (No Backend)
```
Landing (/) 
  → Click "View Demo" 
  → /demo 
  → Pre-loaded data 
  → Interactive graph
```

## Test Queries

| Query | Domain | Expected Nodes |
|-------|--------|----------------|
| "Fed raises rates 100bps" | Economics | Fed → Mortgage → Housing → Employment |
| "War escalates in Middle East" | Geopolitics | Conflict → Oil → Shipping → LNG → Inflation |
| "Category 5 hurricane hits Miami" | Climate | Hurricane → Infrastructure → Supply Chain |
| "ChatGPT launches to public" | Technology | AI → Demand → Cloud → SaaS → Employment |

## API Endpoints

### POST /api/v1/analyze
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question":"Fed raises rates 100bps"}'
```

Response: SSE stream

### GET /health
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "postgres": false,
  "redis": false,
  "neo4j": false
}
```

## Environment Variables

### Frontend
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend
```bash
# backend/.env
GEMINI_API_KEY=your-key-here  # Optional for demo
```

## Troubleshooting

### "Failed to connect to backend"
**Problem:** Backend not running
**Solution:**
```bash
cd backend
uvicorn butterfly.main:app --reload
```

### "Module not found"
**Problem:** Dependencies not installed
**Solution:**
```bash
# Frontend
cd frontend
npm install

# Backend
cd backend
pip install -r requirements.txt
```

### "Port already in use"
**Problem:** Port 3000 or 8000 in use
**Solution:**
```bash
# Frontend on different port
npm run dev -- -p 3001

# Backend on different port
uvicorn butterfly.main:app --port 8001
```

## Key Files

### Frontend
- `app/page.tsx` - Landing page
- `app/analyze/page.tsx` - Real analysis (SSE)
- `app/demo/page.tsx` - Demo mode (no backend)
- `lib/api.ts` - API client
- `lib/demo-data.ts` - Pre-loaded data

### Backend
- `butterfly/main.py` - FastAPI app
- `butterfly/api/analyze.py` - SSE endpoint
- `butterfly/api/events.py` - Event CRUD

### Documentation
- `REAL_VS_DEMO.md` - Architecture
- `VERIFICATION_CHECKLIST.md` - Testing
- `FINAL_INTEGRATION_STATUS.md` - Status

## Quick Checks

### Is backend running?
```bash
curl http://localhost:8000/health
```

### Is frontend running?
Open: http://localhost:3000

### Is SSE working?
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question":"test"}'
```

Should see streaming data.

## Domain Detection

Backend automatically detects domain from keywords:

| Keywords | Domain | Example |
|----------|--------|---------|
| fed, rate, interest, mortgage | Economics | "Fed raises rates" |
| war, conflict, attack, military | Geopolitics | "War escalates" |
| hurricane, storm, flood, climate | Climate | "Hurricane hits" |
| ai, chatgpt, tech, launch | Technology | "ChatGPT launches" |

## Component Status

| Component | Status | Purpose |
|-----------|--------|---------|
| AnalysisStream | ✅ Working | Stage indicators |
| CausalGraph | ✅ Working | Interactive graph |
| InsightCard | ✅ Working | Insight display |
| TemporalReplay | ✅ Working | Timeline controls |

## Performance

- Backend response: ~5 seconds
- Frontend first paint: < 100ms
- Graph render: < 100ms
- Demo load: < 1 second

## Mobile

- Responsive: 375px+
- Touch-friendly controls
- Scrollable insights
- Zoomable graph

---

**Need help?** Check `VERIFICATION_CHECKLIST.md` for detailed testing.
