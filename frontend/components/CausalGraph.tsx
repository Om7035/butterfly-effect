"use client";

import { useEffect, useRef } from "react";
import { useAnalysisStore } from "@/store/analysis";
import type { GraphNode, GraphEdge } from "@/lib/types";

const NODE_COLORS: Record<string, string> = {
  Event: "#7c3aed",
  Metric: "#0d9488",
  Entity: "#ea580c",
  Policy: "#1d4ed8",
};

// Lightweight canvas-based graph renderer (no Sigma SSR issues)
function drawGraph(
  canvas: HTMLCanvasElement,
  nodes: GraphNode[],
  edges: GraphEdge[],
  selectedId: string | null,
  scrubTime: number
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  if (nodes.length === 0) {
    ctx.fillStyle = "#374151";
    ctx.font = "14px system-ui";
    ctx.textAlign = "center";
    ctx.fillText("Select an event to see the causal graph", W / 2, H / 2);
    return;
  }

  // Simple circular layout
  const positions: Record<string, { x: number; y: number }> = {};
  const cx = W / 2, cy = H / 2;
  const r = Math.min(W, H) * 0.35;
  nodes.forEach((n, i) => {
    const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
    positions[n.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });

  // Draw edges
  edges.forEach((e) => {
    const src = positions[e.source];
    const tgt = positions[e.target];
    if (!src || !tgt) return;

    // Fade edges that haven't manifested yet at scrubTime
    const alpha = scrubTime >= e.latency_hours ? 1 : 0.2;
    const width = 1 + e.strength * 3;

    ctx.beginPath();
    ctx.moveTo(src.x, src.y);
    ctx.lineTo(tgt.x, tgt.y);
    ctx.strokeStyle = `rgba(139,92,246,${alpha})`;
    ctx.lineWidth = width;
    ctx.stroke();

    // Arrow
    const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x);
    const ax = tgt.x - 18 * Math.cos(angle);
    const ay = tgt.y - 18 * Math.sin(angle);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(ax - 8 * Math.cos(angle - 0.4), ay - 8 * Math.sin(angle - 0.4));
    ctx.lineTo(ax - 8 * Math.cos(angle + 0.4), ay - 8 * Math.sin(angle + 0.4));
    ctx.closePath();
    ctx.fillStyle = `rgba(139,92,246,${alpha})`;
    ctx.fill();
  });

  // Draw nodes
  nodes.forEach((n) => {
    const pos = positions[n.id];
    if (!pos) return;
    const isSelected = n.id === selectedId;
    const color = NODE_COLORS[n.type] ?? "#6b7280";

    ctx.beginPath();
    ctx.arc(pos.x, pos.y, isSelected ? 18 : 14, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    if (isSelected) {
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    ctx.fillStyle = "#f9fafb";
    ctx.font = `${isSelected ? "bold " : ""}11px system-ui`;
    ctx.textAlign = "center";
    ctx.fillText(n.label, pos.x, pos.y + 28);
  });
}

export default function CausalGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { nodes, edges, selectedNode, setSelectedNode, scrubberTime } = useAnalysisStore();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      drawGraph(canvas, nodes, edges, selectedNode?.id ?? null, scrubberTime);
    };

    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [nodes, edges, selectedNode, scrubberTime]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const W = canvas.width, H = canvas.height;
    const cx = W / 2, cy = H / 2;
    const r = Math.min(W, H) * 0.35;

    for (let i = 0; i < nodes.length; i++) {
      const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
      const nx = cx + r * Math.cos(angle);
      const ny = cy + r * Math.sin(angle);
      if (Math.hypot(mx - nx, my - ny) < 20) {
        setSelectedNode(nodes[i]);
        return;
      }
    }
    setSelectedNode(null);
  };

  return (
    <div className="flex-1 relative bg-[#0a0e1a]">
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-pointer"
        onClick={handleClick}
      />
      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex gap-3">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            <span className="text-[10px] text-gray-400">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
