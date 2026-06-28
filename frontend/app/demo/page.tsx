"use client";

import { ReactFlowProvider } from "reactflow";
import { motion } from "framer-motion";
import CausalGraphCanvas from "@/components/graph/CausalGraphCanvas";
import GraphToolbar from "@/components/graph/controls/GraphToolbar";
import InsightCard from "@/components/InsightCard";
import TemporalReplay from "@/components/TemporalReplay";
import {
  transformToReactFlowData,
  applyHierarchicalLayout,
} from "@/components/graph/utils/graphTransforms";
import {
  DEMO_ISRAEL_HAMAS_NODES,
  DEMO_ISRAEL_HAMAS_EDGES,
  DEMO_ISRAEL_HAMAS_INSIGHTS,
} from "@/lib/demo-data";

// Convert demo data to React Flow format
const rfData = transformToReactFlowData({
  nodes: DEMO_ISRAEL_HAMAS_NODES.map((n) => ({
    id: n.id,
    type: (n.type.toLowerCase() as "event" | "entity" | "metric" | "policy"),
    title: n.label,
    name: n.label,
  })),
  edges: DEMO_ISRAEL_HAMAS_EDGES.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: "causal" as const,
    strength: e.strength,
    confidence: Array.isArray(e.confidence) ? e.confidence[0] : e.confidence,
    latency: e.latency_hours,
  })),
});

const DEMO_NODES = applyHierarchicalLayout(
  rfData.nodes as Parameters<typeof applyHierarchicalLayout>[0],
  rfData.edges as Parameters<typeof applyHierarchicalLayout>[1]
);
const DEMO_EDGES = rfData.edges;

const DEMO_INSIGHTS = DEMO_ISRAEL_HAMAS_INSIGHTS.map((ins) => ({
  order: ins.order,
  hop: ins.hop,
  text: ins.text,
  why: ins.why,
  confidence: ins.confidence,
  sources: ins.sources,
}));

export default function DemoPage() {
  return (
    <div style={{ width: "100vw", height: "100vh", background: "#0a0e1a", display: "flex", flexDirection: "column", overflow: "hidden", fontFamily: "system-ui, -apple-system, sans-serif", color: "#e2e8f0" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 20px", borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.9)", backdropFilter: "blur(12px)", flexShrink: 0, zIndex: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <svg width="22" height="22" viewBox="0 0 48 48" fill="none">
            <path d="M24 24 C18 16, 6 12, 4 20 C2 28, 12 32, 24 24Z" fill="rgba(124,58,237,0.7)" />
            <path d="M24 24 C30 16, 42 12, 44 20 C46 28, 36 32, 24 24Z" fill="rgba(124,58,237,0.7)" />
            <path d="M24 24 C18 30, 8 34, 10 40 C12 46, 22 42, 24 24Z" fill="rgba(124,58,237,0.4)" />
            <path d="M24 24 C30 30, 40 34, 38 40 C36 46, 26 42, 24 24Z" fill="rgba(124,58,237,0.4)" />
            <line x1="24" y1="10" x2="24" y2="38" stroke="rgba(167,139,250,0.6)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <span style={{ fontSize: "13px", fontWeight: "700", letterSpacing: "0.02em" }}>butterfly-effect</span>
          <span style={{ fontSize: "9px", color: "#475569", borderLeft: "1px solid rgba(255,255,255,0.08)", paddingLeft: "10px", textTransform: "uppercase", letterSpacing: "0.1em" }}>demo mode</span>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={{ fontSize: "10px", color: "#f59e0b", background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)", padding: "4px 10px", borderRadius: "6px" }}>
            Pre-analyzed data · Israel-Hamas Oct 2023
          </span>
          <a href="/" style={{ fontSize: "11px", color: "#7c3aed", textDecoration: "none", border: "1px solid rgba(124,58,237,0.3)", padding: "5px 10px", borderRadius: "6px" }}>
            Try live analysis →
          </a>
        </div>
      </div>

      {/* Main */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Graph */}
        <div style={{ flex: 1, position: "relative", display: "flex", flexDirection: "column" }}>
          <div style={{ flex: 1, position: "relative" }}>
            <ReactFlowProvider>
              <CausalGraphCanvas
                initialNodes={DEMO_NODES as Parameters<typeof CausalGraphCanvas>[0]["initialNodes"]}
                initialEdges={DEMO_EDGES as Parameters<typeof CausalGraphCanvas>[0]["initialEdges"]}
                title="Israel-Hamas conflict escalation — October 2023"
              />
              <GraphToolbar onLayoutChange={() => {}} />
            </ReactFlowProvider>
          </div>
          <TemporalReplay prefersReduced={false} />
        </div>

        {/* Insights */}
        <div style={{ width: "320px", flexShrink: 0, borderLeft: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.9)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <span style={{ fontSize: "10px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: "700" }}>Key Insights</span>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
            {DEMO_INSIGHTS.map((ins, i) => (
              <InsightCard key={i} insight={ins} index={i} prefersReduced={false} />
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
