# Miro/Figjam-Style Graph Components

This directory contains the new React Flow-based graph visualization components that replace the old Sigma.js implementation.

## Components

### Core
- `CausalGraphCanvas.tsx` - Main React Flow wrapper with controls and minimap
- `GraphToolbar.tsx` - Layout controls (hierarchical, radial, grid)

### Nodes
- `EventNode.tsx` - Sticky note style for events (yellow gradient)
- `EntityNode.tsx` - Card style for entities (blue gradient)
- `MetricNode.tsx` - Chart style for metrics (green gradient)
- `PolicyNode.tsx` - Badge style for policies (purple gradient)

### Edges
- `CausalEdge.tsx` - Smooth bezier with animated particles
- `InfluenceEdge.tsx` - Dashed line for weak relationships

### Utils
- `graphTransforms.ts` - Data transformation and layout algorithms

## Features

✅ Freeform drag-and-drop positioning
✅ Smooth bezier edges (hand-drawn aesthetic)
✅ Animated flow particles on causal edges
✅ Confidence-based coloring
✅ Latency labels
✅ Built-in minimap
✅ Zoom/pan controls
✅ Multiple layout algorithms
✅ Miro-inspired color palette
✅ Sticky note aesthetic

## Usage

```tsx
import { ReactFlowProvider } from 'reactflow';
import CausalGraphCanvas from '@/components/graph/CausalGraphCanvas';
import GraphToolbar from '@/components/graph/controls/GraphToolbar';

function MyGraph() {
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

## Demo

Visit `/graph-demo` to see the new graph in action with sample data.

## Migration from Sigma.js

The old `CausalGraph.tsx` has been updated to use React Flow. Key changes:
- Force-directed layout → Freeform positioning
- Canvas rendering → React components
- Limited customization → Full JSX/TSX control
- No minimap → Built-in minimap
- Basic edges → Smooth bezier with animations

## Next Steps

- [ ] Add node palette for drag-to-add
- [ ] Implement multi-select with lasso
- [ ] Add keyboard shortcuts
- [ ] Optimize for mobile/touch
- [ ] Add collaborative cursors (future)
