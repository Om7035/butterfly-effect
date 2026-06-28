# Butterfly Effect — Frontend

The "one input, everything visible" causal intelligence interface.

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- React Flow (@xyflow/react) — Interactive causal graphs
- Framer Motion — Animations
- React Syntax Highlighter — Evidence display

## Design System

- Background: `#0a0e1a` (deep indigo/navy)
- Accent: `#7c3aed` (electric violet)
- Edge colors: Green (high confidence), Amber (medium), Red (low)
- Typography: System sans for UI, monospace for data

## Pages

### `/` — Landing
- Centered search input
- 6 example query tiles
- Moth/butterfly icon
- Animates to `/analyze` on submit

### `/analyze?q=...` — Live Analysis
- SSE stream from backend
- Stage indicators (parsing → fetching → extracting → simulating)
- Live stats (nodes, agents, steps)
- Causal graph with React Flow
- Insights sidebar
- Temporal replay controls

### `/demo` — Demo Mode
- Pre-loaded: Israel-Hamas Oct 2023
- Full causal chain visible immediately
- No backend required
- < 1 second load time

## Components

### `<CausalGraph />`
Custom node types:
- EventNode: Root event (pulsing violet border)
- ActorNode: Entities (emerald, avatar-style)
- MetricNode: Metrics (blue, with sparkline)
- InsightNode: Policies (amber, sticky-note style)

Custom edge types:
- CausalEdge: Animated, color by confidence
- Label shows: relationship type + latency

### `<TemporalReplay />`
- Play/pause button
- Speed control (0.5x, 1x, 2x, 4x)
- Timeline scrubber
- Shows "t + Xh" current time

### `<InsightCard />`
- Hop number badge
- Order label (2nd, 3rd, 4th)
- Confidence bar
- Expandable "Why this matters"
- Share button

### `<AnalysisStream />`
- Stage checkmarks
- Live stats counter
- Smooth animations

## Development

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Build

```bash
npm run build
npm start
```

## Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Performance

- Lighthouse score > 85 on all categories
- Graph renders < 100ms for 50-node layout
- Demo mode loads in < 1 second
- Respects `prefers-reduced-motion`

## Mobile

- Graph stacks vertically on mobile
- Insights sidebar becomes bottom sheet
- Touch-friendly controls
- Readable on 375px width
