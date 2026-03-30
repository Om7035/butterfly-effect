"use client";

import { useEffect, useRef, useCallback } from "react";
import { useAnalysisStore } from "@/store/analysis";
import type { GraphNode, GraphEdge } from "@/lib/types";

const NODE_COLORS: Record<string, string> = {
  Event: "#8b5cf6",
  Metric: "#14b8a6",
  Entity: "#f97316",
  Policy: "#3b82f6",
};

const NODE_GLOW: Record<string, string> = {
  Event: "rgba(139,92,246,0.4)",
  Metric: "rgba(20,184,166,0.4)",
  Entity: "rgba(249,115,22,0.4)",
  Policy: "rgba(59,130,246,0.4)",
};

interface NodePos { x: number; y: number; vx: number; vy: number; }

// Force-directed layout engine
function runForce(
  nodes: GraphNode[],
  edges: GraphEdge[],
  W: number,
  H: number,
  iterations = 120
): Record<string, { x: number; y: number }> {
  const pos: Record<string, NodePos> = {};
  const cx = W / 2, cy = H / 2;

  // Init in a circle
  nodes.forEach((n, i) => {
    const angle = (i / nodes.length) * Math.PI * 2;
    const r = Math.min(W, H) * 0.28;
    pos[n.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle), vx: 0, vy: 0 };
  });

  for (let iter = 0; iter < iterations; iter++) {
    const cooling = 1 - iter / iterations;

    // Repulsion between all nodes
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = pos[nodes[i].id], b = pos[nodes[j].id];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const force = (120 * 120) / dist;
        const fx = (dx / dist) * force * 0.01;
        const fy = (dy / dist) * force * 0.01;
        a.vx += fx; a.vy += fy;
        b.vx -= fx; b.vy -= fy;
      }
    }

    // Attraction along edges
    edges.forEach((e) => {
      const a = pos[e.source], b = pos[e.target];
      if (!a || !b) return;
      const dx = b.x - a.x, dy = b.y - a.y;
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const ideal = 160;
      const force = (dist - ideal) * 0.03;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx; a.vy += fy;
      b.vx -= fx; b.vy -= fy;
    });

    // Center gravity
    nodes.forEach((n) => {
      const p = pos[n.id];
      p.vx += (cx - p.x) * 0.005;
      p.vy += (cy - p.y) * 0.005;
    });

    // Apply velocity with cooling + damping
    nodes.forEach((n) => {
      const p = pos[n.id];
      p.x += p.vx * cooling;
      p.y += p.vy * cooling;
      p.vx *= 0.8;
      p.vy *= 0.8;
      // Clamp to canvas
      p.x = Math.max(60, Math.min(W - 60, p.x));
      p.y = Math.max(50, Math.min(H - 50, p.y));
    });
  }

  const result: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n) => { result[n.id] = { x: pos[n.id].x, y: pos[n.id].y }; });
  return result;
}

function drawScene(
  ctx: CanvasRenderingContext2D,
  W: number,
  H: number,
  nodes: GraphNode[],
  edges: GraphEdge[],
  positions: Record<string, { x: number; y: number }>,
  selectedId: string | null,
  hoverId: string | null,
  scrubTime: number,
  animFrame: number
) {
  // Background
  ctx.fillStyle = "#070b14";
  ctx.fillRect(0, 0, W, H);

  // Subtle grid
  ctx.strokeStyle = "rgba(255,255,255,0.025)";
  ctx.lineWidth = 1;
  for (let x = 0; x < W; x += 60) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let y = 0; y < H; y += 60) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  if (nodes.length === 0) {
    ctx.fillStyle = "rgba(139,92,246,0.5)";
    ctx.font = "15px system-ui";
    ctx.textAlign = "center";
    ctx.fillText("Select an event to trace the causal chain", W / 2, H / 2);
    return;
  }

  // Draw edges
  edges.forEach((e) => {
    const src = positions[e.source];
    const tgt = positions[e.target];
    if (!src || !tgt) return;

    const manifested = scrubTime >= e.latency_hours;
    const alpha = manifested ? 0.85 : 0.15;
    const width = 1.5 + e.strength * 3;

    // Animated pulse on manifested edges
    const pulse = manifested
      ? 0.5 + 0.5 * Math.sin(animFrame * 0.04 + e.latency_hours * 0.01)
      : 0;

    // Gradient edge
    const grad = ctx.createLinearGradient(src.x, src.y, tgt.x, tgt.y);
    grad.addColorStop(0, `rgba(139,92,246,${alpha * 0.6})`);
    grad.addColorStop(1, `rgba(20,184,166,${alpha})`);

    ctx.beginPath();
    ctx.moveTo(src.x, src.y);
    ctx.lineTo(tgt.x, tgt.y);
    ctx.strokeStyle = grad;
    ctx.lineWidth = width + pulse * 1.5;
    ctx.stroke();

    // Animated particle along edge
    if (manifested) {
      const t = ((animFrame * 0.008 + e.latency_hours * 0.003) % 1);
      const px = src.x + (tgt.x - src.x) * t;
      const py = src.y + (tgt.y - src.y) * t;
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${0.6 + pulse * 0.4})`;
      ctx.fill();
    }

    // Arrow head
    const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x);
    const nodeR = 18;
    const ax = tgt.x - nodeR * Math.cos(angle);
    const ay = tgt.y - nodeR * Math.sin(angle);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(ax - 10 * Math.cos(angle - 0.45), ay - 10 * Math.sin(angle - 0.45));
    ctx.lineTo(ax - 10 * Math.cos(angle + 0.45), ay - 10 * Math.sin(angle + 0.45));
    ctx.closePath();
    ctx.fillStyle = `rgba(20,184,166,${alpha})`;
    ctx.fill();

    // Latency label on edge midpoint
    if (manifested) {
      const mx = (src.x + tgt.x) / 2;
      const my = (src.y + tgt.y) / 2;
      ctx.fillStyle = "rgba(156,163,175,0.8)";
      ctx.font = "9px system-ui";
      ctx.textAlign = "center";
      ctx.fillText(`${e.latency_hours}h`, mx, my - 6);
    }
  });

  // Draw nodes
  nodes.forEach((n) => {
    const pos = positions[n.id];
    if (!pos) return;
    const isSelected = n.id === selectedId;
    const isHovered = n.id === hoverId;
    const color = NODE_COLORS[n.type] ?? "#6b7280";
    const glow = NODE_GLOW[n.type] ?? "rgba(107,114,128,0.3)";
    const r = isSelected ? 22 : isHovered ? 19 : 16;

    // Outer glow
    const glowR = r + (isSelected ? 20 : isHovered ? 14 : 8);
    const radGrad = ctx.createRadialGradient(pos.x, pos.y, r * 0.5, pos.x, pos.y, glowR);
    radGrad.addColorStop(0, glow.replace("0.4", isSelected ? "0.6" : "0.3"));
    radGrad.addColorStop(1, "transparent");
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, glowR, 0, Math.PI * 2);
    ctx.fillStyle = radGrad;
    ctx.fill();

    // Node circle
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
    const nodeGrad = ctx.createRadialGradient(pos.x - r * 0.3, pos.y - r * 0.3, 1, pos.x, pos.y, r);
    nodeGrad.addColorStop(0, lighten(color));
    nodeGrad.addColorStop(1, color);
    ctx.fillStyle = nodeGrad;
    ctx.fill();

    // Border
    ctx.strokeStyle = isSelected ? "#fff" : isHovered ? "rgba(255,255,255,0.6)" : "rgba(255,255,255,0.2)";
    ctx.lineWidth = isSelected ? 2.5 : 1.5;
    ctx.stroke();

    // Pulsing ring on selected
    if (isSelected) {
      const pulseR = r + 6 + 4 * Math.sin(animFrame * 0.08);
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, pulseR, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255,255,255,${0.3 + 0.2 * Math.sin(animFrame * 0.08)})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Label
    ctx.fillStyle = isSelected ? "#fff" : "rgba(229,231,235,0.9)";
    ctx.font = `${isSelected ? "bold " : ""}11px system-ui`;
    ctx.textAlign = "center";
    ctx.fillText(n.label, pos.x, pos.y + r + 14);

    // Type badge
    ctx.fillStyle = color + "99";
    ctx.font = "8px system-ui";
    ctx.fillText(n.type, pos.x, pos.y + r + 24);
  });
}

function lighten(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgb(${Math.min(255, r + 60)},${Math.min(255, g + 60)},${Math.min(255, b + 60)})`;
}

export default function CausalGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const positionsRef = useRef<Record<string, { x: number; y: number }>>({});
  const animRef = useRef<number>(0);
  const frameRef = useRef<number>(0);
  const hoverRef = useRef<string | null>(null);

  const { nodes, edges, selectedNode, setSelectedNode, scrubberTime } = useAnalysisStore();

  // Recompute layout when nodes/edges change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;
    positionsRef.current = runForce(nodes, edges, canvas.offsetWidth, canvas.offsetHeight);
  }, [nodes, edges]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const loop = () => {
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      frameRef.current++;
      drawScene(
        ctx, canvas.width, canvas.height,
        nodes, edges, positionsRef.current,
        selectedNode?.id ?? null, hoverRef.current,
        scrubberTime, frameRef.current
      );
      animRef.current = requestAnimationFrame(loop);
    };

    animRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animRef.current);
  }, [nodes, edges, selectedNode, scrubberTime]);

  const getNodeAt = useCallback((mx: number, my: number): GraphNode | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    for (const n of nodes) {
      const pos = positionsRef.current[n.id];
      if (!pos) continue;
      if (Math.hypot(mx - pos.x, my - pos.y) < 22) return n;
    }
    return null;
  }, [nodes]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const node = getNodeAt(e.clientX - rect.left, e.clientY - rect.top);
    setSelectedNode(node);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const node = getNodeAt(e.clientX - rect.left, e.clientY - rect.top);
    hoverRef.current = node?.id ?? null;
    canvas.style.cursor = node ? "pointer" : "default";
  };

  return (
    <div className="flex-1 relative" style={{ background: "#070b14" }}>
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        onClick={handleClick}
        onMouseMove={handleMouseMove}
      />
      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex gap-4 bg-black/40 backdrop-blur px-3 py-2 rounded-lg border border-white/10">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full shadow-lg" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
            <span className="text-[10px] text-gray-400">{type}</span>
          </div>
        ))}
      </div>
      {/* Scrub time indicator */}
      <div className="absolute top-3 right-3 bg-black/50 backdrop-blur px-2.5 py-1 rounded-md border border-white/10 text-[10px] text-gray-400">
        T+{scrubberTime}h
      </div>
    </div>
  );
}
