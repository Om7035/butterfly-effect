# Frontend Quickstart — 5 Minutes

## Option 1: Demo Mode (No Backend)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000/demo

You'll see the Israel-Hamas Oct 2023 analysis instantly. Full causal graph, insights, temporal replay — all working with zero setup.

## Option 2: With Backend

### Terminal 1: Start Backend
```bash
cd backend
pip install fastapi uvicorn pydantic-settings loguru httpx google-genai mistralai networkx mesa
```

Add to `backend/.env`:
```env
GEMINI_API_KEY=your-key-here
```

```bash
uvicorn butterfly.main:app --reload
```

### Terminal 2: Start Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

Type any question:
- "Fed raises rates 100bps"
- "War escalates in Middle East"
- "ChatGPT launches to public"

Watch the analysis stream in real-time.

## What You'll See

### Landing Page
- Centered search input
- 6 example query tiles
- Butterfly icon
- Dark theme

### Analysis Page
- Stage indicators (parsing → fetching → extracting → simulating)
- Live stats counter (nodes, agents, steps)
- Causal graph with custom nodes
- Insights sidebar
- Temporal replay controls

### Demo Page
- Pre-loaded analysis
- Full graph visible immediately
- No backend required
- < 1 second load time

## Troubleshooting

### "Module not found"
```bash
cd frontend
npm install
```

### "Port 3000 already in use"
```bash
npm run dev -- -p 3001
```

### "API connection failed"
Check backend is running on http://localhost:8000

```bash
curl http://localhost:8000/health
```

Should return:
```json
{"status": "ok", "postgres": false, "redis": false, "neo4j": false}
```

### "Build failed"
```bash
cd frontend
rm -rf .next node_modules
npm install
npm run build
```

## Environment Variables

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Production Build

```bash
cd frontend
npm run build
npm start
```

Open http://localhost:3000

## Deploy to Vercel

```bash
cd frontend
npm i -g vercel
vercel
```

Follow prompts. Done in 2 minutes.

## Next Steps

1. Try the demo mode
2. Type your own questions
3. Click nodes in the graph
4. Use temporal replay
5. Expand insight cards
6. Share the URL

## Need Help?

- Check `FRONTEND_COMPLETE.md` for full docs
- Check `frontend/README.md` for component details
- Open an issue on GitHub
- Check the backend logs for API errors

## Tips

- Use example queries to see different domains
- Click nodes to see details (coming soon)
- Scrub the timeline to see effects over time
- Check confidence bars on insights
- Try on mobile — it's responsive

---

**Total time**: 5 minutes
**Dependencies**: Node.js 18+, npm
**Backend**: Optional (demo mode works without it)
