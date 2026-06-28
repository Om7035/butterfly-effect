"use client";

import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { EventNode, ActorNode, MetricNode, InsightNode } from "./nodes";
import { CausalEdge } from "./edges";
import type { GraphNode, GraphEdge } from "@/lib/types";

interface CausalGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const nodeTypes = {
  Event: EventNode,
  Entity: ActorNode,
  Metric: MetricNode,
  Policy: InsightNode,
};

const edgeTypes = {
  causal: CausalEdge,
};

export function CausalGraph({ nodes: graphNodes, edges: graphEdges }: CausalGraphProps) {
  // Convert to React Flow format
  const initialNodes: Node[] = useMemo(() => {
    return graphNodes.map((node, i) => ({
      id: node.id,
      type: node.type,
      position: node.x && node.y ? { x: node.x, y: node.y } : { x: i * 200, y: i * 100 },
      data: { label: node.label, type: node.type },
    }));
  }, [graphNodes]);

  const initialEdges: Edge[] = useMemo(() => {
    return graphEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "causal",
      data: {
        strength: edge.strength,
        latency: edge.latency_hours,
        confidence: edge.confidence,
        relationship: edge.relationship_type,
      },
      animated: edge.strength > 0.7,
    }));
  }, [graphEdges]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="w-full h-full bg-[#0a0e1a]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          style: { strokeWidth: 2 },
        }}
      >
        <Background color="#1f2937" gap={16} />
        <Controls className="bg-gray-900 border-gray-800" />
        <MiniMap
          className="bg-gray-900 border-gray-800"
          nodeColor={(node) => {
            if (node.type === "Event") return "#7c3aed";
            if (node.type === "Metric") return "#3b82f6";
            if (node.type === "Entity") return "#10b981";
            return "#6b7280";
          }}
        />
      </ReactFlow>
    </div>
  );
}
