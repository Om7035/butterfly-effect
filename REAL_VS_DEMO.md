# Real Backend vs Demo Mode

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Landing Page (/)                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  "What event should we trace?"                      │    │
│  │  [Search Input]                                     │    │
│  │                                                      │    │
│  │  Example tiles (clickable)                          │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  [View Demo] button (top right) → /demo                     │
│                                                              │
│  On submit → /analyze?q=... (ALWAYS uses real backend)      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Analysis Page (/analyze)                   │
│                                                              │
│  ALWAYS connects to real backend:                           │
│  POST http://localhost:8000/api/v1/analyze                  │
│                                                              │
│  SSE Stream:                                                 │
│  1. parsing → fetching → extracting → simulating            │
│  2. Real-time stats updates                                 │
│  3. Domain-specific causal graph                            │
│  4. Realistic insights with sources                         │
│                                                              │
│  If backend is down:                                         │
│  - Shows error message                                       │
│  - Provides backend start command                           │
│  - Offers link to demo mode                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Demo Page (/demo)                        │
│                                                              │
│  NEVER connects to backend                                   │
│  Uses pre-loaded data from frontend/lib/demo-data.ts        │
│                                                              │
│  Shows:                                                      │
│  - Israel-Hamas Oct 2023 analysis                           │
│  - Full causal graph (12 nodes, 11 edges)                   │
│  - 3 detailed insights                                       │
│  - Temporal replay                                           │
│                                                              │
│  Loads in < 1 second (no network calls)                     │
│  Banner: "Demo mode — using pre-analyzed data"              │
└─────────────────────────────────────────────────────────────┘
```

## User Flow

### Normal Flow (Real Backend)
1. User lands on `/`
2. User types question or clicks example
3. Redirects to `/analyze?q=...`
4. Frontend connects to `POST /api/v1/analyze`
5. Backend streams SSE events
6. Frontend updates in real-time
7. Shows domain-specific causal graph

### Demo Flow (No Backend)
1. User clicks "View Demo" button on landing page
2. Redirects to `/demo`
3. Pre-loaded data renders instantly
4. No backend connection
5. Full interactive graph available
6. Banner indicates demo mode

## Backend Connection

### API Endpoint
```
POST http://localhost:8000/api/v1/analyze
Content-Type: application/json

{
  "question": "Fed raises rates 100bps"
}
```

### SSE Response
```
data: {"stage":"parsing","stats":{"nodes":0,"agents":0,"steps":0}}

data: {"stage":"fetching","stats":{"nodes":3,"agents":0,"steps":0}}

data: {"stage":"extracting","stats":{"nodes":8,"agents":50,"steps":0}}

data: {"stage":"simulating","stats":{"nodes":12,"agents":100,"steps":168}}

data: {"stage":"done","nodes":[...],"edges":[...],"insights":[...],"run_id":"run_abc123"}

data: {"done":true}
```

### Environment Variable
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Error Handling

### Backend Down
When backend is not running, the analyze page shows:

```
┌─────────────────────────────────────────────────────────────┐
│                     Analysis failed                          │
│                                                              │
│  Failed to connect to backend: [error message]              │
│  Make sure the backend is running at http://localhost:8000  │
│                                                              │
│  Make sure the backend is running:                          │
│  cd backend && uvicorn butterfly.main:app --reload          │
│                                                              │
│  Or try the demo mode:                                       │
│  [View Demo]                                                 │
└─────────────────────────────────────────────────────────────┘
```

### Backend Error
If backend returns an error during analysis:

```
data: {"error":"LLM API key not configured"}
```

Frontend shows the error message and suggests checking backend logs.

## Testing

### Test Real Backend Connection
```bash
# Terminal 1: Start backend
cd backend
uvicorn butterfly.main:app --reload

# Terminal 2: Start frontend
cd frontend
npm run dev

# Browser: Go to http://localhost:3000
# Type: "Fed raises rates 100bps"
# Should see: Real-time SSE stream, domain-specific graph
```

### Test Demo Mode
```bash
# Terminal: Start frontend only (no backend needed)
cd frontend
npm run dev

# Browser: Go to http://localhost:3000
# Click: "View Demo" button
# Should see: Instant load, Israel-Hamas analysis
```

### Test Error Handling
```bash
# Terminal: Start frontend only (backend NOT running)
cd frontend
npm run dev

# Browser: Go to http://localhost:3000
# Type: "Fed raises rates 100bps"
# Should see: Error message with backend start command
```

## Domain-Specific Responses

### Economics Domain
**Trigger:** "Fed raises rates 100bps"

**Backend generates:**
- 6 nodes: Fed Rate Hike → Federal Funds Rate → Mortgage Rate → Housing Starts → Employment
- 5 edges with realistic latencies (0h, 48h, 168h, 720h)
- 2-3 insights about monetary transmission
- Sources: FRED, NAR, MBA, BLS

### Geopolitics Domain
**Trigger:** "War escalates in Middle East"

**Backend generates:**
- 6 nodes: Conflict → Oil Price → Shipping Routes → Insurance → LNG → Inflation
- 5 edges with conflict-specific latencies (6h, 72h, 96h, 168h, 336h)
- 3-4 insights about supply chain cascade
- Sources: EIA, Lloyd's List, Kpler, Eurostat

### Climate Domain
**Trigger:** "Category 5 hurricane hits Miami"

**Backend generates:**
- 5 nodes: Hurricane → Infrastructure → Supply Chain → Commodities → Insurance
- 4 edges with disaster-specific latencies (24h, 72h, 168h, 336h)
- 2-3 insights about infrastructure cascade
- Sources: NOAA, FEMA, CME, USDA

### Technology Domain
**Trigger:** "ChatGPT launches to public"

**Backend generates:**
- 5 nodes: AI Launch → Enterprise Demand → Cloud Costs → SaaS Margins → Employment
- 4 edges with tech adoption latencies (168h, 720h, 1440h, 2880h)
- 2-3 insights about tech disruption
- Sources: Cloud providers, Gartner, Tech layoff trackers

## Files

### Real Backend Integration
- `frontend/app/page.tsx` - Landing page (always uses real backend)
- `frontend/app/analyze/page.tsx` - Analysis page (SSE stream from backend)
- `frontend/lib/api.ts` - API client (configured with BASE URL)
- `backend/butterfly/api/analyze.py` - SSE endpoint (domain-specific logic)

### Demo Mode
- `frontend/app/demo/page.tsx` - Demo page (no backend connection)
- `frontend/lib/demo-data.ts` - Pre-loaded data (Israel-Hamas Oct 2023)

### Configuration
- `frontend/.env.local` - Backend URL configuration
- `frontend/.env.local.example` - Template

## Key Differences

| Feature | Real Backend (`/analyze`) | Demo Mode (`/demo`) |
|---------|---------------------------|---------------------|
| Backend connection | ✅ Required | ❌ Not used |
| Data source | SSE stream from API | Pre-loaded fixtures |
| Load time | ~5 seconds | < 1 second |
| Domain detection | ✅ Automatic | ❌ Fixed (geopolitics) |
| Insights | ✅ Domain-specific | ✅ Pre-written |
| Temporal replay | ✅ Based on real latencies | ✅ Based on fixture data |
| Error handling | ✅ Shows backend errors | ❌ No errors possible |
| Caching | ✅ Redis (when implemented) | ❌ Not applicable |

## Production Deployment

### Frontend (Vercel)
```bash
cd frontend
vercel

# Set environment variable in Vercel dashboard:
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Backend (Any host)
```bash
cd backend
uvicorn butterfly.main:app --host 0.0.0.0 --port 8000
```

### CORS Configuration
Backend must allow frontend origin:

```python
# backend/butterfly/main.py
origins = [
    "http://localhost:3000",
    "https://yourdomain.com",
    "https://yourdomain.vercel.app",
]
```

## Summary

✅ **Landing page (/)** - Always uses real backend
✅ **Analysis page (/analyze)** - Always uses real backend via SSE
✅ **Demo page (/demo)** - Never uses backend, pre-loaded data only
✅ **Error handling** - Shows helpful message when backend is down
✅ **Domain detection** - Backend automatically detects domain from question
✅ **Realistic responses** - Domain-specific graphs and insights

**The real backend and demo mode are completely separated.**
