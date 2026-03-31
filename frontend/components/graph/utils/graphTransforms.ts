import { Node, Edge } from 'reactflow';
import dagre from '@dagrejs/dagre';

export interface CausalChainData {
  nodes: Array<{
    id: string;
    type: 'event' | 'entity' | 'metric' | 'policy';
    title?: string;
    name?: string;
    description?: string;
    timestamp?: string;
    value?: number;
    delta?: number;
    unit?: string;
    confidence?: number;
    entityType?: 'company' | 'person' | 'sector';
    subtype?: string;
    status?: 'active' | 'pending' | 'inactive';
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type?: 'causal' | 'influence';
    strength?: number;
    confidence?: number;
    latency?: number;
  }>;
}

export function transformToReactFlowData(data: CausalChainData): {
  nodes: Node[];
  edges: Edge[];
} {
  const nodes: Node[] = data.nodes.map((node, index) => {
    const angle = (index / data.nodes.length) * 2 * Math.PI;
    const radius = 300;
    return {
      id: node.id,
      type: node.type,
      position: {
        x: 400 + radius * Math.cos(angle),
        y: 300 + radius * Math.sin(angle),
      },
      data: { ...node },
    };
  });

  const edges: Edge[] = data.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: edge.type || 'causal',
    data: {
      strength: edge.strength,
      confidence: edge.confidence,
      latency: edge.latency,
    },
  }));

  return { nodes, edges };
}

const NODE_WIDTH = 180;
const NODE_HEIGHT = 60;

/**
 * Dagre hierarchical layout — clean top-to-bottom DAG.
 * Replaces the manual topological sort with proper Sugiyama-style layout.
 */
export function applyHierarchicalLayout(nodes: Node[], edges: Edge[]): Node[] {
  if (nodes.length === 0) return nodes;

  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: 'TB',      // top-to-bottom
    nodesep: 60,        // horizontal gap between nodes in same rank
    ranksep: 100,       // vertical gap between ranks
    marginx: 40,
    marginy: 40,
    acyclicer: 'greedy',
    ranker: 'network-simplex',
  });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  const nodeIds = new Set(nodes.map((n) => n.id));
  edges.forEach((edge) => {
    if (nodeIds.has(edge.source) && nodeIds.has(edge.target)) {
      g.setEdge(edge.source, edge.target);
    }
  });

  dagre.layout(g);

  return nodes.map((node) => {
    const pos = g.node(node.id);
    if (!pos) return node;
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });
}

export function applyRadialLayout(nodes: Node[], centerNodeId?: string): Node[] {
  const centerNode = centerNodeId
    ? nodes.find(n => n.id === centerNodeId)
    : nodes[0];

  if (!centerNode) return nodes;

  const otherNodes = nodes.filter(n => n.id !== centerNode.id);
  const radius = 350;

  return nodes.map((node, index) => {
    if (node.id === centerNode.id) {
      return {
        ...node,
        position: { x: 400, y: 300 },
      };
    }

    const otherIndex = otherNodes.findIndex(n => n.id === node.id);
    const angle = (otherIndex / otherNodes.length) * 2 * Math.PI;

    return {
      ...node,
      position: {
        x: 400 + radius * Math.cos(angle),
        y: 300 + radius * Math.sin(angle),
      },
    };
  });
}

export function applyGridLayout(nodes: Node[]): Node[] {
  const cols = Math.ceil(Math.sqrt(nodes.length));
  const cellWidth = 250;
  const cellHeight = 200;

  return nodes.map((node, index) => ({
    ...node,
    position: {
      x: (index % cols) * cellWidth + 100,
      y: Math.floor(index / cols) * cellHeight + 100,
    },
  }));
}
