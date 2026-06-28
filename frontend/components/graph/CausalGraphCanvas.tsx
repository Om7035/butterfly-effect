'use client';

import { useCallback, useMemo, useState } from 'react';
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
  onNodeClick?: (nodeId: string) => void;
}

// ── Legend ────────────────────────────────────────────────────────────────────

function Legend() {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          background: 'rgba(15,23,42,0.92)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '8px',
          padding: '6px 12px',
          color: '#94a3b8',
          fontSize: '11px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          backdropFilter: 'blur(8px)',
        }}
      >
        <span style={{ fontSize: '13px' }}>?</span>
        How to read this
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          marginTop: '6px',
          background: 'rgba(10,14,26,0.98)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '12px',
          padding: '16px',
          width: '280px',
          backdropFilter: 'blur(12px)',
          zIndex: 100,
          boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
        }}>
          <div style={{ fontSize: '11px', fontWeight: '700', color: '#e2e8f0', marginBottom: '12px', letterSpacing: '0.04em' }}>
            HOW TO READ THIS CAUSAL CHAIN
          </div>

          {/* Node types */}
          <div style={{ fontSize: '9px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
            Node types
          </div>
          {[
            { color: '#7c3aed', icon: '🦋', label: 'Root Event', desc: 'The event you typed — the trigger' },
            { color: '#10b981', icon: '📊', label: 'Metric / Effect', desc: 'A measurable outcome that changes' },
            { color: '#3b82f6', icon: '🏛', label: 'Actor / System', desc: 'An entity or system that responds' },
            { color: '#a78bfa', icon: '📋', label: 'Policy Response', desc: 'A government or institutional action' },
          ].map(item => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '8px' }}>
              <div style={{
                width: '10px', height: '10px', borderRadius: '50%',
                background: item.color, flexShrink: 0, marginTop: '2px',
              }} />
              <div>
                <div style={{ fontSize: '10px', fontWeight: '600', color: '#e2e8f0' }}>{item.label}</div>
                <div style={{ fontSize: '9px', color: '#475569', lineHeight: 1.4 }}>{item.desc}</div>
              </div>
            </div>
          ))}

          <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)', margin: '10px 0' }} />

          {/* Order labels */}
          <div style={{ fontSize: '9px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
            Causal order = how many steps from the trigger
          </div>
          {[
            { color: '#34d399', label: '1st order', desc: 'Happens within hours — the obvious effect' },
            { color: '#60a5fa', label: '2nd order', desc: 'Happens within days — what most people see' },
            { color: '#a78bfa', label: '3rd order', desc: 'Happens within weeks — what analysts miss' },
            { color: '#fbbf24', label: '4th order', desc: 'Happens within months — the butterfly effect' },
          ].map(item => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
              <div style={{
                fontSize: '7px', fontWeight: '700', color: item.color,
                background: `${item.color}18`, border: `1px solid ${item.color}44`,
                padding: '1px 5px', borderRadius: '3px', flexShrink: 0, marginTop: '1px',
              }}>
                {item.label}
              </div>
              <div style={{ fontSize: '9px', color: '#475569', lineHeight: 1.4 }}>{item.desc}</div>
            </div>
          ))}

          <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)', margin: '10px 0' }} />

          {/* Edge colors */}
          <div style={{ fontSize: '9px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
            Arrow color = how certain this connection is
          </div>
          {[
            { color: '#34d399', label: 'Green', desc: 'High confidence (>80%) — well-established' },
            { color: '#60a5fa', label: 'Blue',  desc: 'Medium confidence (60-80%)' },
            { color: '#fbbf24', label: 'Amber', desc: 'Low confidence (40-60%) — plausible' },
            { color: '#f87171', label: 'Red',   desc: 'Very uncertain (<40%) — speculative' },
          ].map(item => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }}>
              <div style={{ width: '20px', height: '2px', background: item.color, borderRadius: '1px', flexShrink: 0 }} />
              <div style={{ fontSize: '9px', color: '#475569' }}>
                <span style={{ color: item.color, fontWeight: '600' }}>{item.label}</span> — {item.desc}
              </div>
            </div>
          ))}

          <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)', margin: '10px 0' }} />

          {/* Tips */}
          <div style={{ fontSize: '9px', color: '#475569', lineHeight: 1.6 }}>
            💡 <span style={{ color: '#94a3b8' }}>Click any node</span> to see evidence<br />
            🔍 <span style={{ color: '#94a3b8' }}>Scroll to zoom</span>, drag to pan<br />
            ⏱ <span style={{ color: '#94a3b8' }}>Use the timeline</span> below to replay the cascade
          </div>
        </div>
      )}
    </div>
  );
}

// ── Hop depth ruler ───────────────────────────────────────────────────────────

function HopRuler({ nodeCount }: { nodeCount: number }) {
  if (nodeCount === 0) return null;
  return (
    <div style={{
      background: 'rgba(15,23,42,0.85)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '8px',
      padding: '8px 12px',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
    }}>
      <span style={{ fontSize: '9px', color: '#334155', marginRight: '4px' }}>DEPTH</span>
      {[
        { hop: 0, color: '#7c3aed', label: 'Trigger' },
        { hop: 1, color: '#34d399', label: '1st' },
        { hop: 2, color: '#60a5fa', label: '2nd' },
        { hop: 3, color: '#a78bfa', label: '3rd' },
        { hop: 4, color: '#fbbf24', label: '4th' },
      ].map((item, i) => (
        <div key={item.hop} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {i > 0 && <div style={{ width: '12px', height: '1px', background: 'rgba(255,255,255,0.1)' }} />}
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: item.color, opacity: 0.8,
          }} />
          <span style={{ fontSize: '8px', color: '#475569' }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Main canvas ───────────────────────────────────────────────────────────────

export default function CausalGraphCanvas({
  initialNodes = [],
  initialEdges = [],
  title,
  onNodeClick,
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
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        minZoom={0.15}
        maxZoom={2.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="rgba(255,255,255,0.04)" />
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

        {/* Top-left: title + hop ruler */}
        <Panel position="top-left">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {title && (
              <div style={{
                background: 'rgba(15,23,42,0.85)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '8px', padding: '8px 14px',
                backdropFilter: 'blur(8px)',
              }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: '#e2e8f0', letterSpacing: '0.02em' }}>
                  🦋 {title}
                </div>
                <div style={{ fontSize: '9px', color: '#475569', marginTop: '2px' }}>
                  {nodes.length} nodes · {edges.length} connections · read top to bottom
                </div>
              </div>
            )}
            <HopRuler nodeCount={nodes.length} />
          </div>
        </Panel>

        {/* Top-right: legend */}
        <Panel position="top-right">
          <Legend />
        </Panel>

        {/* Bottom-left: reading guide */}
        <Panel position="bottom-left">
          <div style={{
            background: 'rgba(15,23,42,0.75)',
            border: '1px solid rgba(255,255,255,0.05)',
            borderRadius: '8px',
            padding: '6px 10px',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}>
            <span style={{ fontSize: '9px', color: '#334155' }}>ARROWS MEAN</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div style={{ width: '16px', height: '1.5px', background: '#34d399' }} />
              <span style={{ fontSize: '8px', color: '#475569' }}>causes</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div style={{ width: '16px', height: '1.5px', background: '#fbbf24', borderTop: '1.5px dashed #fbbf24' }} />
              <span style={{ fontSize: '8px', color: '#475569' }}>correlates</span>
            </div>
            <div style={{ width: '1px', height: '12px', background: 'rgba(255,255,255,0.06)' }} />
            <span style={{ fontSize: '8px', color: '#334155' }}>dot speed = certainty</span>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
