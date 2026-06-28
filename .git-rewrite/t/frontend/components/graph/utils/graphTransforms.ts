import { Node, Edge } from 'reactflow';

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
  // Transform nodes with automatic positioning
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
      data: {
        ...node,
      },
    };
  });

  // Transform edges
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

export function applyHierarchicalLayout(nodes: Node[], edges: Edge[]): Node[] {
  // Simple hierarchical layout (top to bottom)
  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const inDegree = new Map<string, number>();
  const outEdges = new Map<string, string[]>();

  // Calculate in-degrees
  nodes.forEach(n => {
    inDegree.set(n.id, 0);
    outEdges.set(n.id, []);
  });

  edges.forEach(e => {
    inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
    outEdges.get(e.source)?.push(e.target);
  });

  // Topological sort to determine levels
  const levels: string[][] = [];
  const queue: string[] = [];
  
  inDegree.forEach((degree, nodeId) => {
    if (degree === 0) queue.push(nodeId);
  });

  while (queue.length > 0) {
    const levelNodes = [...queue];
    levels.push(levelNodes);
    queue.length = 0;

    levelNodes.forEach(nodeId => {
      outEdges.get(nodeId)?.forEach(targetId => {
        const newDegree = (inDegree.get(targetId) || 0) - 1;
        inDegree.set(targetId, newDegree);
        if (newDegree === 0) queue.push(targetId);
      });
    });
  }

  // Position nodes
  const levelHeight = 200;
  const nodeSpacing = 250;

  return nodes.map(node => {
    const levelIndex = levels.findIndex(level => level.includes(node.id));
    const positionInLevel = levels[levelIndex]?.indexOf(node.id) || 0;
    const levelWidth = (levels[levelIndex]?.length || 1) * nodeSpacing;

    return {
      ...node,
      position: {
        x: positionInLevel * nodeSpacing - levelWidth / 2 + 400,
        y: levelIndex * levelHeight + 100,
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
