# ✅ Verification Checklist - Real Backend vs Demo

## Setup

### Backend
```bash
cd backend
uvicorn butterfly.main:app --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Frontend
```bash
cd frontend
npm run dev
```

Expected output:
```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

## Test 1: Landing Page

### Steps
1. Open http://localhost:3000
2. Check top-right corner

### Expected
- [ ] "View Demo" button visible in top-right
- [ ] Centered search input
- [ ] 6 example query tiles
- [ ] Butterfly icon
- [ ] Dark theme (#0a0e1a background)
- [ ] NO mention of demo in footer

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 2: Real Backend - Economics Domain

### Steps
1. On landing page, type: "Fed raises rates 100bps"
2. Press Enter or click "Analyze"
3. Watch the analysis stream

### Expected
- [ ] Redirects to `/analyze?q=Fed+raises+rates+100bps`
- [ ] Stage indicators show: parsing → fetching → extracting → simulating
- [ ] Live stats counter updates (nodes, agents, steps)
- [ ] Graph appears with 5-6 nodes
- [ ] Nodes include: Fed Rate Hike, Federal Funds Rate, Mortgage Rate, Housing Starts, Employment
- [ ] Edges are color-coded (green/amber/red)
- [ ] Insights sidebar shows 2-3 insights
- [ ] Insights mention "2nd order" and "3rd order"
- [ ] Sources include: FRED, NAR, MBA, BLS
- [ ] Temporal replay controls appear
- [ ] Total time: ~5 seconds

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 3: Real Backend - Geopolitics Domain

### Steps
1. Go back to landing page
2. Type: "War escalates in Middle East"
3. Press Enter

### Expected
- [ ] Graph shows 6 nodes
- [ ] Nodes include: Conflict, Oil Price, Shipping Routes, Insurance, LNG, Inflation
- [ ] Insights mention supply chain disruption
- [ ] Sources include: EIA, Lloyd's List, Kpler, Eurostat
- [ ] Latencies are different from economics (6h, 72h, 96h, 168h, 336h)

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 4: Real Backend - Climate Domain

### Steps
1. Go back to landing page
2. Click example tile: "Category 5 hurricane hits Miami"

### Expected
- [ ] Graph shows 4-5 nodes
- [ ] Nodes include: Hurricane, Infrastructure, Supply Chain, Commodities
- [ ] Insights mention infrastructure damage cascade
- [ ] Sources include: NOAA, FEMA, CME, USDA

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 5: Real Backend - Technology Domain

### Steps
1. Go back to landing page
2. Click example tile: "ChatGPT launches to public"

### Expected
- [ ] Graph shows 5 nodes
- [ ] Nodes include: AI Launch, Enterprise Demand, Cloud Costs, SaaS Margins, Employment
- [ ] Insights mention tech disruption and layoffs
- [ ] Sources include: Cloud providers, Gartner
- [ ] Latencies are longer (168h, 720h, 1440h, 2880h)

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 6: Demo Mode

### Steps
1. Go to landing page
2. Click "View Demo" button in top-right
3. Observe the demo page

### Expected
- [ ] Redirects to `/demo`
- [ ] Page loads instantly (< 1 second)
- [ ] Banner shows: "Demo mode — using pre-analyzed data"
- [ ] Graph shows Israel-Hamas Oct 2023 analysis
- [ ] 12 nodes visible
- [ ] 11 edges visible
- [ ] 3 insights in sidebar
- [ ] Temporal replay controls work
- [ ] NO backend connection made (check Network tab)

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 7: Error Handling (Backend Down)

### Steps
1. Stop the backend (Ctrl+C in backend terminal)
2. Go to landing page
3. Type: "Fed raises rates 100bps"
4. Press Enter

### Expected
- [ ] Redirects to `/analyze?q=...`
- [ ] Shows error message: "Analysis failed"
- [ ] Shows: "Failed to connect to backend"
- [ ] Shows backend start command
- [ ] Shows "View Demo" button
- [ ] Clicking "View Demo" goes to `/demo` and works

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 8: Mobile Responsiveness

### Steps
1. Open DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Set to iPhone SE (375px width)
4. Navigate through landing, analyze, and demo pages

### Expected
- [ ] Landing page: search input and tiles stack vertically
- [ ] Analyze page: graph is zoomable/pannable
- [ ] Insights sidebar becomes scrollable
- [ ] Temporal replay controls are touch-friendly
- [ ] Demo page: same as analyze page
- [ ] All text is readable
- [ ] No horizontal scroll

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 9: SSE Stream Format

### Steps
1. Open DevTools Network tab
2. Type: "Fed raises rates 100bps"
3. Find the `/api/v1/analyze` request
4. Check the response

### Expected
- [ ] Request method: POST
- [ ] Request body: `{"question":"Fed raises rates 100bps"}`
- [ ] Response type: text/event-stream
- [ ] Response contains: `data: {"stage":"parsing",...}`
- [ ] Response contains: `data: {"stage":"fetching",...}`
- [ ] Response contains: `data: {"stage":"extracting",...}`
- [ ] Response contains: `data: {"stage":"simulating",...}`
- [ ] Response contains: `data: {"stage":"done","nodes":[...],"edges":[...],...}`
- [ ] Response contains: `data: {"done":true}`

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Test 10: Component Integration

### Steps
1. Run a full analysis
2. Check each component

### Expected

**AnalysisStream:**
- [ ] Shows 4 stage indicators
- [ ] Checkmarks appear as stages complete
- [ ] Live stats counter updates
- [ ] Smooth animations

**CausalGraph:**
- [ ] Custom node types render (Event=violet, Entity=emerald, Metric=blue)
- [ ] Edges are color-coded by confidence
- [ ] Edge labels show relationship type + latency
- [ ] Zoom/pan controls work
- [ ] Minimap shows graph overview

**InsightCard:**
- [ ] Hop badges visible
- [ ] Order labels (2nd, 3rd, 4th) visible
- [ ] Confidence bars color-coded
- [ ] "Why this matters" expands on click
- [ ] Share button copies to clipboard

**TemporalReplay:**
- [ ] Play/pause button works
- [ ] Speed control (0.5x, 1x, 2x, 4x) works
- [ ] Timeline scrubber works
- [ ] Current time displays correctly

### Result
- [ ] PASS
- [ ] FAIL (describe issue): _______________

## Summary

### Total Tests: 10
### Passed: _____ / 10
### Failed: _____ / 10

### Critical Issues
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### Non-Critical Issues
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### Notes
_____________________________________________________
_____________________________________________________
_____________________________________________________

## Sign-off

- [ ] All critical tests pass
- [ ] Backend and frontend are in sync
- [ ] Demo mode is separate from real backend
- [ ] Error handling works correctly
- [ ] Mobile responsive
- [ ] Ready for deployment

**Tested by:** _______________
**Date:** _______________
**Signature:** _______________
