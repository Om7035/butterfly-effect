'use client';

import { useState, useCallback, useEffect } from 'react';
import { ReactFlowProvider } from 'reactflow';
import CausalGraphCanvas from './graph/CausalGraphCanvas';
import GraphToolbar from './graph/controls/GraphToolbar';
import {
  transformToReactFlowData,
  applyHierarchicalLayout,
  applyRadialLayout,
  applyGridLayout,
  CausalChainData,
} from './graph/utils/graphTransforms';
import { useAnalysisStore } from '@/store/analysis';

export default function CausalGraphNew() {
  const { nodes, edges } = useAnalysisStore();

  const [graphData, setGraphData] = useState(() => {
    const data: CausalChainData = {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type.toLowerCase() as 'event' | 'entity' | 'metric' | 'policy',
        title: n.label,
        name: n.label,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.relationship_type === 'CAUSED_BY' ? 'causal' : 'influence',
        strength: e.strength,
        confidence: Array.isArray(e.confidence)
          ? (e.confidence[0] + e.confidence[1]) / 2
          : (e.confidence as unknown as number),
        latency: e.latency_hours,
      })),
    };
    return transformToReactFlowData(data);
  });

  useEffect(() => {
    const data: CausalChainData = {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type.toLowerCase() as 'event' | 'entity' | 'metric' | 'policy',
        title: n.label,
        name: n.label,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.relationship_type === 'CAUSED_BY' ? 'causal' : 'influence',
        strength: e.strength,
        confidence: Array.isArray(e.confidence)
          ? (e.confidence[0] + e.confidence[1]) / 2
          : (e.confidence as unknown as number),
        latency: e.latency_hours,
      })),
    };
    setGraphData(transformToReactFlowData(data));
  }, [nodes, edges]);

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

  if (nodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[#070b14]">
        <div className="text-center">
          <div className="text-5xl mb-4 opacity-30">🦋</div>
          <p className="text-sm text-slate-600">Select an event to trace the causal chain</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 relative overflow-hidden">
      <ReactFlowProvider>
        <CausalGraphCanvas
          initialNodes={graphData.nodes}
          initialEdges={graphData.edges}
        />
        <GraphToolbar onLayoutChange={handleLayoutChange} />
      </ReactFlowProvider>
    </div>
  );
}
