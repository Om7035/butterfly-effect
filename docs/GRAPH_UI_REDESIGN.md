# 🎨 Graph UI Redesign - Miro/Figjam Style

**Goal:** Transform the current Sigma.js force-directed graph into a Miro/Figjam-style infinite canvas with freeform manipulation.

---

## 🎯 Design Principles

### Visual Aesthetic
- Soft, rounded shapes with subtle shadows
- Hand-drawn connector lines (bezier curves, not straight)
- Sticky note aesthetic for nodes
- Pastel color palette with gradients
- Whiteboard/canvas feel
- Depth through layering and shadows

### Interaction Model
- Freeform drag-and-drop positioning
- Snap-to-grid (optional, toggleable)
- Multi-select with lasso tool
- Connector auto-routing around nodes
- Zoom to fit / zoom to selection
- Pan with spacebar + drag or middle mouse
- Infinite canvas with minimap

---

## 🛠️ Recommended Technology: React Flow

**Why React Flow over Sigma.js:**

| Feature | Sigma.js | React Flow |
|---------|----------|------------|
| React integration | ❌ Canvas-based | ✅ Native React |
| Custom node components | ❌ Limited | ✅ Full JSX/TSX |
| Freeform positioning | ❌ Force-directed only | ✅ Drag anywhere |
| Edge customization | ⚠️ Basic | ✅ Bezier, smooth, custom |
| Minimap | ❌ No | ✅ Built-in |
| Touch support | ⚠️ Limited | ✅ Full mobile support |
| TypeScript | ⚠️ Partial | ✅ Full type safety |
| Documentation | ⚠️ Moderate | ✅ Excellent |
| Active development | ⚠️ Slow | ✅ Very active |

**Installation:**
```bash
npm install reactflow
```

**Official Docs:** https://reactflow.dev

---

## 📐 Component Architecture

### New Component Structure

```
frontend/components/
├── graph/
│   ├── CausalGraphCanvas.tsx      # Main React Flow wrapper
│   ├── nodes/
│   │   ├── EventNode.tsx          # Sticky note style for events
│   │   ├── EntityNode.tsx         # Card style for entities
│   │   ├── MetricNode.tsx         # Chart style for metrics
│   │   └── PolicyNode.tsx         # Badge style for policies
│   ├── edges/
│   │   ├── CausalEdge.tsx         # Hand-drawn bezier edge
│   │   └── InfluenceEdge.tsx      # Dashed influence edge
│   ├── controls/
│   │   ├── GraphToolbar.tsx       # Zoom, fit, layout controls
│   │   ├── GraphMinimap.tsx       # Overview minimap
│   │   └── NodePalette.tsx        # Drag-to-add node palette
│   └── utils/
│       ├── layoutEngine.ts        # Auto-layout algorithms
│       └── graphTransforms.ts     # Data transformations
```

---

## 🎨 Node Design Specifications

### 1. Event Node (Sticky Note Style)

**Visual:**
- Rounded rectangle (border-radius: 12px)
- Soft shadow (box-shadow: 0 4px 12px rgba(0,0,0,0.1))
- Gradient background (yellow → light orange)
- Slightly rotated (-2deg to 2deg for organic feel)
- Title in bold, description in smaller text
- Timestamp badge in corner

**Size:** 200px × 150px (minimum)

**Example JSX:**
```tsx
function EventNode({ data }: NodeProps) {
  return (
    <div className="event-node" style={{
      background: 'linear-gradient(135deg, #FFF9C4 0%, #FFE082 100%)',
      borderRadius: '12px',
      padding: '16px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      transform: `rotate(${data.rotation || 0}deg)`,
      minWidth: '200px',
      minHeight: '150px',
    }}>
      <div className="node-header">
        <h3>{data.title}</h3>
        <span className="timestamp">{data.timestamp}</span>
      </div>
      <p className="description">{data.description}</p>
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Left} />
    </div>
  );
}
```

### 2. Entity Node (Card Style)

**Visual:**
- Clean white card with border
- Icon on left (company, person, sector)
- Name + type label
- Confidence score bar at bottom
- Hover: lift effect (translateY: -2px)

**Size:** 180px × 100px

### 3. Metric Node (Chart Style)

**Visual:**
- Mini sparkline chart
- Current value (large)
- Delta indicator (↑ ↓)
- Color-coded by direction (green/red)

**Size:** 160px × 120px

### 4. Policy Node (Badge Style)

**Visual:**
- Pill shape (border-radius: 24px)
- Blue gradient background
- Icon + short label
- Compact design

**Size:** 140px × 60px

---

## 🔗 Edge Design Specifications

### 1. Causal Edge (Strong Relationship)

**Visual:**
- Smooth bezier curve (not straight line)
- Animated flow particles (dots moving along edge)
- Thickness based on strength (2px - 6px)
- Color based on confidence:
  - High (>0.8): Solid green
  - Medium (0.5-0.8): Solid blue
  - Low (<0.5): Dashed gray
- Arrow at target end
- Label showing latency ("48h")

**Example:**
```tsx
function CausalEdge({ id, sourceX, sourceY, targetX, targetY, data }: EdgeProps) {
  const edgePath = getBezierPath({
    sourceX, sourceY, targetX, targetY,
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  });

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        strokeWidth={data.strength * 6}
        stroke={getConfidenceColor(data.confidence)}
        markerEnd="url(#arrow)"
      />
      <EdgeLabelRenderer>
        <div className="edge-label" style={{
          transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
        }}>
          {data.latency}h
        </div>
      </EdgeLabelRenderer>
      <AnimatedParticles path={edgePath} />
    </>
  );
}
```

### 2. Influence Edge (Weak Relationship)

**Visual:**
- Dashed line
- Thinner (1px - 3px)
- Gray color
- No animation
- Optional label

---

## 🎮 Interaction Features

### 1. Freeform Positioning
- Drag any node to reposition
- Nodes stay where you put them (no force simulation)
- Edges automatically re-route

### 2. Multi-Select
- Click + drag to create selection box
- Shift + click to add to selection
- Move multiple nodes together
- Delete multiple nodes

### 3. Zoom & Pan
- Mouse wheel to zoom
- Spacebar + drag to pan
- Double-click node to zoom to it
- "Fit View" button to see all nodes

### 4. Minimap
- Small overview in corner
- Shows viewport position
- Click to jump to area
- Draggable viewport rectangle

### 5. Node Palette
- Sidebar with node types
- Drag onto canvas to create
- Pre-configured templates

### 6. Layout Algorithms
- "Auto Layout" button
- Options:
  - Hierarchical (top-down)
  - Radial (center-out)
  - Force-directed (organic)
  - Grid (aligned)
- Animate transition to new layout

---

## 🎨 Color Palette (Miro-Inspired)

### Node Colors
```css
--event-yellow: linear-gradient(135deg, #FFF9C4 0%, #FFE082 100%);
--entity-blue: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
--metric-green: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
--policy-purple: linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%);
--canvas-bg: #F5F5F5;
```

### Edge Colors
```css
--confidence-high: #4CAF50;    /* Green */
--confidence-medium: #2196F3;  /* Blue */
--confidence-low: #9E9E9E;     /* Gray */
--influence: #FF9800;          /* Orange */
```

### Shadows
```css
--shadow-sm: 0 2px 4px rgba(0,0,0,0.08);
--shadow-md: 0 4px 12px rgba(0,0,0,0.1);
--shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
```

---

## 📦 Implementation Plan

### Phase 1: Setup (1 day)
- [ ] Install React Flow
- [ ] Create new CausalGraphCanvas component
- [ ] Set up basic node/edge types
- [ ] Add minimap and controls

### Phase 2: Node Styling (2 days)
- [ ] Design EventNode (sticky note)
- [ ] Design EntityNode (card)
- [ ] Design MetricNode (chart)
- [ ] Design PolicyNode (badge)
- [ ] Add hover effects and animations

### Phase 3: Edge Styling (1 day)
- [ ] Implement smooth bezier edges
- [ ] Add animated particles
- [ ] Add confidence-based coloring
- [ ] Add latency labels

### Phase 4: Interactions (2 days)
- [ ] Freeform drag-and-drop
- [ ] Multi-select with lasso
- [ ] Zoom/pan controls
- [ ] Layout algorithms
- [ ] Node palette

### Phase 5: Polish (1 day)
- [ ] Animations and transitions
- [ ] Keyboard shortcuts
- [ ] Touch/mobile support
- [ ] Performance optimization

**Total:** 7 days

---

## 🔧 Code Example: Complete Setup

```tsx
// frontend/components/graph/CausalGraphCanvas.tsx
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

import EventNode from './nodes/EventNode';
import EntityNode from './nodes/EntityNode';
import CausalEdge from './edges/CausalEdge';

const nodeTypes = {
  event: EventNode,
  entity: EntityNode,
  metric: MetricNode,
  policy: PolicyNode,
};

const edgeTypes = {
  causal: CausalEdge,
  influence: InfluenceEdge,
};

export default function CausalGraphCanvas({ initialNodes, initialEdges }) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div style={{ width: '100%', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
      >
        <Background color="#aaa" gap={16} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            switch (node.type) {
              case 'event': return '#FFE082';
              case 'entity': return '#BBDEFB';
              case 'metric': return '#C8E6C9';
              case 'policy': return '#E1BEE7';
              default: return '#eee';
            }
          }}
        />
      </ReactFlow>
    </div>
  );
}
```

---

## 📚 Resources

- **React Flow Docs:** https://reactflow.dev/learn
- **React Flow Examples:** https://reactflow.dev/examples
- **Miro Design System:** https://miro.com/design-system/
- **Figjam UI Patterns:** https://www.figma.com/community/file/figjam

---

**Next Steps:** Review this design doc, then proceed with Phase 1 implementation.
