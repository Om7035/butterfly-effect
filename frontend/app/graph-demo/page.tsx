'use client';

import { useState, useCallback, useEffect } from 'react';
import { ReactFlowProvider } from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';
import CausalGraphCanvas from '@/components/graph/CausalGraphCanvas';
import GraphToolbar from '@/components/graph/controls/GraphToolbar';
import {
  transformToReactFlowData,
  applyHierarchicalLayout,
  applyRadialLayout,
  applyGridLayout,
  CausalChainData,
} from '@/components/graph/utils/graphTransforms';

// ── Scenarios ────────────────────────────────────────────────────────────────

const SCENARIOS: Record<string, { label: string; color: string; data: CausalChainData }> = {
  fed: {
    label: 'Fed Rate Hike — 2022',
    color: '#7c3aed',
    data: {
      nodes: [
        { id: 'n8', type: 'policy',  name: 'Monetary Policy',    status: 'active' },
        { id: 'n4', type: 'entity',  name: 'Federal Reserve',    subtype: 'Central Bank',  confidence: 0.99, entityType: 'company' },
        { id: 'n1', type: 'event',   title: 'Fed Rate Hike',     description: '75bps FOMC decision', timestamp: 'Jun 15 2022' },
        { id: 'n2', type: 'metric',  name: 'Treasury Yield',     value: 3.45, delta: 0.75, unit: '%' },
        { id: 'n3', type: 'metric',  name: 'Mortgage Rate',      value: 5.81, delta: 0.92, unit: '%' },
        { id: 'n5', type: 'metric',  name: 'Housing Starts',     value: 1559, delta: -247, unit: 'K' },
        { id: 'n6', type: 'entity',  name: 'Construction Sector', subtype: 'Industry', confidence: 0.78, entityType: 'sector' },
        { id: 'n7', type: 'metric',  name: 'Unemployment',       value: 3.7,  delta: 0.23, unit: '%' },
      ],
      edges: [
        { id: 'e0', source: 'n8', target: 'n4', type: 'influence', strength: 0.85, confidence: 0.90 },
        { id: 'e1', source: 'n4', target: 'n1', type: 'causal',    strength: 0.99, confidence: 0.99, latency: 0 },
        { id: 'e2', source: 'n1', target: 'n2', type: 'causal',    strength: 0.92, confidence: 0.95, latency: 2 },
        { id: 'e3', source: 'n2', target: 'n3', type: 'causal',    strength: 0.78, confidence: 0.88, latency: 48 },
        { id: 'e4', source: 'n3', target: 'n5', type: 'causal',    strength: 0.71, confidence: 0.82, latency: 72 },
        { id: 'e5', source: 'n5', target: 'n6', type: 'influence', strength: 0.65, confidence: 0.75 },
        { id: 'e6', source: 'n6', target: 'n7', type: 'causal',    strength: 0.54, confidence: 0.68, latency: 168 },
      ],
    },
  },
  texas: {
    label: 'Texas Winter Storm — 2021',
    color: '#3b82f6',
    data: {
      nodes: [
        { id: 'n1', type: 'event',  title: 'ERCOT Grid Failure', description: 'Texas power grid collapse', timestamp: 'Feb 10 2021' },
        { id: 'n2', type: 'metric', name: 'Natural Gas Price',   value: 23.5, delta: 20.0, unit: '$/MMBtu' },
        { id: 'n3', type: 'entity', name: 'Manufacturing Sector', subtype: 'Industry', confidence: 0.85, entityType: 'sector' },
        { id: 'n4', type: 'metric', name: 'TX Employment',       value: 98.2, delta: -0.26, unit: 'idx' },
        { id: 'n5', type: 'policy', name: 'ERCOT Regulation',    status: 'pending' },
      ],
      edges: [
        { id: 'e1', source: 'n1', target: 'n2', type: 'causal',    strength: 0.92, confidence: 0.92, latency: 6 },
        { id: 'e2', source: 'n1', target: 'n3', type: 'causal',    strength: 0.85, confidence: 0.85, latency: 24 },
        { id: 'e3', source: 'n3', target: 'n4', type: 'influence', strength: 0.78, confidence: 0.78 },
        { id: 'e4', source: 'n5', target: 'n1', type: 'influence', strength: 0.60, confidence: 0.60 },
      ],
    },
  },
  covid: {
    label: 'COVID Supply Chain — 2021',
    color: '#10b981',
    data: {
      nodes: [
        { id: 'n1', type: 'event',  title: 'Semiconductor Shortage', description: 'Global chip shortage declared', timestamp: 'Sep 2021' },
        { id: 'n2', type: 'entity', name: 'Auto Industry',           subtype: 'Sector', confidence: 0.92, entityType: 'sector' },
        { id: 'n3', type: 'metric', name: 'Auto Production',         value: 8.2,   delta: -25.5, unit: 'M units' },
        { id: 'n4', type: 'metric', name: 'Used Car Prices',         value: 236.3, delta: 48.0,  unit: 'idx' },
        { id: 'n5', type: 'metric', name: 'CPI',                     value: 8.5,   delta: 1.2,   unit: '%' },
        { id: 'n6', type: 'policy', name: 'CHIPS Act',               status: 'pending' },
      ],
      edges: [
        { id: 'e1', source: 'n1', target: 'n2', type: 'causal',    strength: 0.92, confidence: 0.92, latency: 48 },
        { id: 'e2', source: 'n2', target: 'n3', type: 'causal',    strength: 0.88, confidence: 0.88, latency: 72 },
        { id: 'e3', source: 'n3', target: 'n4', type: 'causal',    strength: 0.82, confidence: 0.82, latency: 120 },
        { id: 'e4', source: 'n4', target: 'n5', type: 'influence', strength: 0.75, confidence: 0.75 },
        { id: 'e5', source: 'n6', target: 'n1', type: 'influence', strength: 0.40, confidence: 0.40 },
      ],
    },
  },
};

// ── Legend ────────────────────────────────────────────────────────────────────

const LEGEND = [
  { color: '#7c3aed', label: 'Event' },
  { color: '#3b82f6', label: 'Entity' },
  { color: '#10b981', label: 'Metric' },
  { color: '#a78bfa', label: 'Policy' },
];

const EDGE_LEGEND = [
  { color: '#34d399', label: 'High confidence (>80%)' },
  { color: '#60a5fa', label: 'Medium (60–80%)' },
  { color: '#fbbf24', label: 'Low (<60%)' },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function GraphDemoPage() {
  const [activeScenario, setActiveScenario] = useState<keyof typeof SCENARIOS>('fed');
  const [graphData, setGraphData] = useState(() =>
    transformToReactFlowData(SCENARIOS.fed.data)
  );
  const [showLegend, setShowLegend] = useState(true);

  // Switch scenario
  useEffect(() => {
    setGraphData(transformToReactFlowData(SCENARIOS[activeScenario].data));
  }, [activeScenario]);

  const handleLayoutChange = useCallback(
    (layout: 'hierarchical' | 'radial' | 'grid' | 'force') => {
      setGraphData((prev) => {
        let newNodes = [...prev.nodes];
        switch (layout) {
          case 'hierarchical': newNodes = applyHierarchicalLayout(prev.nodes, prev.edges); break;
          case 'radial':       newNodes = applyRadialLayout(prev.nodes); break;
          case 'grid':         newNodes = applyGridLayout(prev.nodes); break;
        }
        return { ...prev, nodes: newNodes };
      });
    },
    []
  );

  const scenario = SCENARIOS[activeScenario];

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#070b14',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>

      {/* ── Top bar ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        background: 'rgba(15,23,42,0.8)',
        backdropFilter: 'blur(8px)',
        flexShrink: 0,
        zIndex: 10,
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '18px' }}>🦋</span>
          <span style={{ fontSize: '13px', fontWeight: '700', color: '#e2e8f0', letterSpacing: '0.02em' }}>
            butterfly-effect
          </span>
          <span style={{
            fontSize: '9px',
            color: '#475569',
            borderLeft: '1px solid rgba(255,255,255,0.08)',
            paddingLeft: '10px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>
            causal chain tracer
          </span>
        </div>

        {/* Scenario switcher */}
        <div style={{ display: 'flex', gap: '6px' }}>
          {(Object.keys(SCENARIOS) as Array<keyof typeof SCENARIOS>).map((key) => (
            <button
              key={key}
              onClick={() => setActiveScenario(key)}
              style={{
                padding: '5px 12px',
                borderRadius: '6px',
                border: `1px solid ${activeScenario === key ? SCENARIOS[key].color + '80' : 'rgba(255,255,255,0.07)'}`,
                background: activeScenario === key ? `${SCENARIOS[key].color}18` : 'transparent',
                color: activeScenario === key ? '#e2e8f0' : '#64748b',
                fontSize: '11px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {SCENARIOS[key].label}
            </button>
          ))}
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '14px', fontWeight: '700', color: scenario.color }}>
              {graphData.nodes.length}
            </div>
            <div style={{ fontSize: '9px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>nodes</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '14px', fontWeight: '700', color: '#34d399' }}>
              {graphData.edges.length}
            </div>
            <div style={{ fontSize: '9px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>edges</div>
          </div>
          <a href="/" style={{
            fontSize: '11px',
            color: '#475569',
            textDecoration: 'none',
            border: '1px solid rgba(255,255,255,0.07)',
            padding: '5px 10px',
            borderRadius: '6px',
            transition: 'color 0.2s',
          }}>
            ← Dashboard
          </a>
        </div>
      </div>

      {/* ── Graph ── */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeScenario}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            style={{ width: '100%', height: '100%' }}
          >
            <ReactFlowProvider>
              <CausalGraphCanvas
                initialNodes={graphData.nodes}
                initialEdges={graphData.edges}
                title={scenario.label}
              />
              <GraphToolbar onLayoutChange={handleLayoutChange} />
            </ReactFlowProvider>
          </motion.div>
        </AnimatePresence>

        {/* ── Legend ── */}
        <AnimatePresence>
          {showLegend && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              style={{
                position: 'absolute',
                bottom: '20px',
                left: '20px',
                background: 'rgba(15,23,42,0.9)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '10px',
                padding: '12px 16px',
                backdropFilter: 'blur(8px)',
                zIndex: 5,
              }}
            >
              <div style={{ fontSize: '9px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
                Node types
              </div>
              <div style={{ display: 'flex', gap: '12px', marginBottom: '10px' }}>
                {LEGEND.map(({ color, label }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <div style={{
                      width: '8px', height: '8px', borderRadius: '50%',
                      background: color,
                      boxShadow: `0 0 6px ${color}`,
                    }} />
                    <span style={{ fontSize: '10px', color: '#94a3b8' }}>{label}</span>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: '9px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
                Edge confidence
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                {EDGE_LEGEND.map(({ color, label }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <div style={{ width: '16px', height: '2px', background: color, borderRadius: '1px' }} />
                    <span style={{ fontSize: '10px', color: '#94a3b8' }}>{label}</span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setShowLegend(false)}
                style={{
                  position: 'absolute', top: '8px', right: '10px',
                  background: 'none', border: 'none', color: '#475569',
                  cursor: 'pointer', fontSize: '12px', lineHeight: 1,
                }}
              >
                ×
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Show legend button */}
        {!showLegend && (
          <button
            onClick={() => setShowLegend(true)}
            style={{
              position: 'absolute', bottom: '20px', left: '20px',
              background: 'rgba(15,23,42,0.9)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '6px',
              padding: '5px 10px',
              color: '#64748b',
              fontSize: '10px',
              cursor: 'pointer',
              zIndex: 5,
            }}
          >
            Show legend
          </button>
        )}
      </div>
    </div>
  );
}
