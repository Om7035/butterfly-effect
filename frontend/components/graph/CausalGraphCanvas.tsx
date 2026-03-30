'use client';

import { useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

import EventNode from './nodes/EventNode';
import EntityNode from './nodes/EntityNode';
import MetricNode from './nodes/MetricNode';
import PolicyNode from './nodes/PolicyNode';
import CausalEdge from './edges/CausalEdge';
import InfluenceEdge from './edges/InfluenceEdge';

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

interface CausalGraphCanvasProps {
  initialNodes?: Node[];
  initialEdges?: Edge[];
  title?: string;
}

export default function CausalGraphCanvas({
  initialNodes = [],
  initialEdges = [],
  title,
}: CausalGraphCanvasProps) {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const defaultEdgeOptions = useMemo(() => ({
    type: 'causal',
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: '#34d399' },
  }), []);

  return (
    <div style={{ width: '100%', height: '100%', background: '#070b14' }}>
      {/* Global keyframes injected once */}
      <style>{`
        .react-flow__attribution { display: none; }
        .react-flow__controls { background: rgba(15,23,42,0.9) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 8px !important; box-shadow: none !important; }
        .react-flow__controls-button { background: transparent !important; border: none !important; color: #64748b !important; fill: #64748b !important; }
        .react-flow__controls-button:hover { background: rgba(255,255,255,0.05) !important; color: #e2e8f0 !important; fill: #e2e8f0 !important; }
        .react-flow__minimap { background: rgba(15,23,42,0.9) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 8px !important; }
        .react-flow__handle { opacity: 0 !important; }
        .react-flow__node:hover .react-flow__handle { opacity: 1 !important; }
        @keyframes pulse-ring {
          0%   { transform: scale(1); opacity: 0.6; }
          100% { transform: scale(1.8); opacity: 0; }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.3; }
        }
      `}</style>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        minZoom={0.15}
        maxZoom={2.5}
        proOptions={{ hideAttribution: true }}
      >
        {/* Subtle dot grid */}
        <Background
          variant={BackgroundVariant.Dots}
          gap={28}
          size={1}
          color="rgba(255,255,255,0.04)"
        />

        <Controls showInteractive={false} />

        <MiniMap
          nodeColor={(n) => {
            switch (n.type) {
              case 'event':  return '#7c3aed';
              case 'entity': return '#3b82f6';
              case 'metric': return '#10b981';
              case 'policy': return '#a78bfa';
              default:       return '#334155';
            }
          }}
          maskColor="rgba(7,11,20,0.7)"
          style={{ bottom: 16, right: 16 }}
        />

        {title && (
          <Panel position="top-left">
            <div style={{
              background: 'rgba(15,23,42,0.85)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '8px',
              padding: '8px 14px',
              backdropFilter: 'blur(8px)',
            }}>
              <div style={{ fontSize: '11px', fontWeight: '700', color: '#e2e8f0', letterSpacing: '0.02em' }}>
                🦋 {title}
              </div>
              <div style={{ fontSize: '9px', color: '#475569', marginTop: '2px' }}>
                {nodes.length} nodes · {edges.length} edges
              </div>
            </div>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}
