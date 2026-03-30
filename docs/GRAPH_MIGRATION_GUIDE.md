# Graph UI Migration Guide

## Quick Start

The new Miro/Figjam-style graph is ready to use! Here's how to switch from the old Sigma.js graph to the new React Flow graph.

## Option 1: Use the Demo Page

Visit `/graph-demo` to see the new graph with sample data:

```bash
npm run dev
# Open http://localhost:3000/graph-demo
```

## Option 2: Replace CausalGraph Component

In your page/component, replace:

```tsx
// Old (Sigma.js)
import CausalGraph from '@/components/CausalGraph';

// New (React Flow)
import CausalGraphNew from '@/components/CausalGraphNew';
```

Then use it:

```tsx
<CausalGraphNew />
```

## What's Different?

### Visual Changes
- ✅ Sticky note style for events (yellow gradient)
- ✅ Card style for entities (blue gradient)
- ✅ Chart style for metrics (green gradient)
- ✅ Badge style for policies (purple gradient)
- ✅ Smooth bezier edges (not straight lines)
- ✅ Animated particles on causal edges
- ✅ Confidence-based coloring
- ✅ Latency labels

### Interaction Changes
- ✅ Drag nodes anywhere (freeform positioning)
- ✅ Nodes stay where you put them
- ✅ Zoom with mouse wheel
- ✅ Pan with spacebar + drag
- ✅ Built-in minimap (bottom-right)
- ✅ Layout controls (top-right toolbar)

### Layout Options
1. **Hierarchical** - Top-down flow (good for causal chains)
2. **Radial** - Center-out (good for impact analysis)
3. **Grid** - Aligned grid (good for comparison)
4. **Freeform** - Manual positioning (default)

## Component API

### CausalGraphNew

Uses data from `useAnalysisStore()` automatically.

```tsx
import CausalGraphNew from '@/components/CausalGraphNew';

function MyPage() {
  return <CausalGraphNew />;
}
```

### CausalGraphCanvas (Low-level)

For custom implementations:

```tsx
import { ReactFlowProvider } from 'reactflow';
import CausalGraphCanvas from '@/components/graph/CausalGraphCanvas';
import GraphToolbar from '@/components/graph/controls/GraphToolbar';

function CustomGraph() {
  const [nodes, setNodes] = useState([...]);
  const [edges, setEdges] = useState([...]);

  return (
    <ReactFlowProvider>
      <CausalGraphCanvas
        initialNodes={nodes}
        initialEdges={edges}
      />
      <GraphToolbar onLayoutChange={handleLayoutChange} />
    </ReactFlowProvider>
  );
}
```

## Data Format

### Node Format

```typescript
{
  id: string;
  type: 'event' | 'entity' | 'metric' | 'policy';
  position: { x: number; y: number };
  data: {
    // For event nodes:
    title?: string;
    description?: string;
    timestamp?: string;
    rotation?: number;
    
    // For entity nodes:
    name?: string;
    type?: string;
    confidence?: number;
    entityType?: 'company' | 'person' | 'sector';
    
    // For metric nodes:
    name?: string;
    value?: number;
    delta?: number;
    unit?: string;
    
    // For policy nodes:
    name?: string;
    status?: 'active' | 'pending' | 'inactive';
  };
}
```

### Edge Format

```typescript
{
  id: string;
  source: string;
  target: string;
  type: 'causal' | 'influence';
  data: {
    strength?: number;      // 0-1
    confidence?: number;    // 0-1
    latency?: number;       // hours
  };
}
```

## Styling

The graph uses Miro-inspired colors:

```css
/* Node gradients */
--event-yellow: linear-gradient(135deg, #FFF9C4 0%, #FFE082 100%);
--entity-blue: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
--metric-green: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
--policy-purple: linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%);

/* Edge colors */
--confidence-high: #4CAF50;    /* Green */
--confidence-medium: #2196F3;  /* Blue */
--confidence-low: #9E9E9E;     /* Gray */
```

## Keyboard Shortcuts (Coming Soon)

- `Space + Drag` - Pan canvas
- `Ctrl + Scroll` - Zoom
- `Ctrl + A` - Select all
- `Delete` - Delete selected
- `Ctrl + Z` - Undo
- `Ctrl + Shift + Z` - Redo

## Performance

- Tested with 100+ nodes
- 60 FPS animations
- Smooth zoom/pan
- Efficient re-renders

## Browser Support

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile: ⚠️ Basic support (touch gestures work)

## Troubleshooting

### Graph not showing?

Check that React Flow is installed:
```bash
npm install reactflow
```

### Nodes overlapping?

Use a layout algorithm:
- Click the layout button in the toolbar
- Choose "Hierarchical" or "Radial"

### Performance issues?

- Reduce number of nodes (<100 recommended)
- Disable animations in edge components
- Use `memo()` on custom node components

## Next Steps

1. Try the demo: `/graph-demo`
2. Read the design doc: `docs/GRAPH_UI_REDESIGN.md`
3. Explore components: `frontend/components/graph/`
4. Customize node styles in `frontend/components/graph/nodes/`

## Feedback

Found a bug or have a suggestion? Open an issue on GitHub!

---

*Last updated: March 30, 2026*
