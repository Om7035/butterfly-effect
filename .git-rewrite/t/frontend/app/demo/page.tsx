"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ReactFlowProvider } from "reactflow";
import { ArrowRight, Zap } from "lucide-react";
import CausalGraphCanvas from "@/components/graph/CausalGraphCanvas";
import GraphToolbar from "@/components/graph/controls/GraphToolbar";
import InsightCard from "@/components/InsightCard";
import EvidencePanelNew from "@/components/EvidencePanelNew";
import TemporalReplay from "@/components/TemporalReplay";
import {
  transformToReactFlowData,
  applyHierarchicalLayout,
  CausalChainData,
} from "@/components/graph/utils/graphTransforms";
import {
  DEMO_ISRAEL_HAMAS_NODES,
  DEMO_ISRAEL_HAMAS_EDGES,
  DEMO_ISRAEL_HAMAS_INSIGHTS,
} from "@/lib/demo-data";

// Build React Flow data from demo fixture
const DEMO_CHAIN: CausalChainData = {
  nodes: DEMO_ISRAEL_HAMAS_NODES.map((n) => ({
    id: n.id,
    type: n.type.toLowerCase() as "event" | "entity" | "metric" | "policy",
    title: n.label,
    name: n.label,
  })),
  edges: DEMO_ISRAEL_HAMAS_EDGES.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: e.relationship_type === "CORRELATES_WITH" ? "influence" : "causal",
    strength: e.strength,
    confidence: e.confidence[0],
    latency: e.latency_hours,
  })),
};

export default function DemoPage() {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const graphData = useMemo(() => {
    const rf = transformToReactFlowData(DEMO_CHAIN);
    const laid = applyHierarchicalLayout(
      rf.nodes as Parameters<typeof applyHierarchicalLayout>[0],
      rf.edges as Parameters<typeof applyHierarchicalLayout>[1]
    );
    return { nodes: laid, edges: rf.edges };
  }, []);

  return (
    <div style={{ width: "100vw", height: "100vh", background: "#0a0e1a", display: "flex", flexDirection: "column", overflow: "hidden", fontFamily: "system-ui, -apple-system, sans-serif", color: "#e2e8f0" }}>

      {/* Demo banner */}
      <div style={{ background: "rgba(124,58,237,0.12)", borderBottom: "1px solid rgba(124,58,237,0.2)", padding: "8px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Zap size={12} color="#a78bfa" />
          <span style={{ fontSize: "11px", color: "#a78bfa" }}>Demo mode — using pre-analyzed data · Israel-Hamas conflict escalation, October 2023</span>
        </div>
        <a href="/" style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", color: "#7c3aed", textDecoration: "none", border: "1px solid rgba(124,58,237,0.3)", padding: "4px 10px", borderRadius: "6px" }}>
          Try live analysis <ArrowRight size={10} />
        </a>
      </div>

      {/* Top bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 20px", borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.9)", backdropFilter: "blur(12px)", flexShrink: 0, zIndex: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <ButterflyIcon size={20} />
          <span style={{ fontSize: "13px", fontWeight: "700", letterSpacing: "0.02em" }}>butterfly-effect</span>
          <span style={{ fontSize: "9px", color: "#475569", borderLeft: "1px solid rgba(255,255,255,0.08)", paddingLeft: "10px", textTransform: "uppercase", letterSpacing: "0.1em" }}>causal chain tracer</span>
        </div>
        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "14px", fontWeight: "700", color: "#7c3aed", fontFamily: "monospace" }}>{graphData.nodes.length}</div>
            <div style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em" }}>nodes</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "14px", fontWeight: "700", color: "#34d399", fontFamily: "monospace" }}>{graphData.edges.length}</div>
            <div style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em" }}>edges</div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Graph */}
        <div style={{ flex: 1, position: "relative", display: "flex", flexDirection: "column" }}>
          <div style={{ flex: 1, position: "relative" }}>
            <ReactFlowProvider>
              <CausalGraphCanvas
                initialNodes={graphData.nodes as Parameters<typeof CausalGraphCanvas>[0]["initialNodes"]}
                initialEdges={graphData.edges as Parameters<typeof CausalGraphCanvas>[0]["initialEdges"]}
                title="Israel-Hamas Conflict Escalation — October 2023"
                onNodeClick={(id) => setSelectedNodeId(id)}
              />
              <GraphToolbar onLayoutChange={() => {}} />
            </ReactFlowProvider>
          </div>
          <TemporalReplay prefersReduced={false} />
        </div>

        {/* Right panel */}
        <div style={{ width: "320px", flexShrink: 0, borderLeft: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.9)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {selectedNodeId ? (
            <motion.div key="evidence" initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: "10px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: "700" }}>Evidence</span>
                <button onClick={() => setSelectedNodeId(null)} style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: "16px", lineHeight: 1 }}>×</button>
              </div>
              <EvidencePanelNew nodeId={selectedNodeId} />
            </motion.div>
          ) : (
            <motion.div key="insights" initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <span style={{ fontSize: "10px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: "700" }}>Key Insights</span>
              </div>
              <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                {DEMO_ISRAEL_HAMAS_INSIGHTS.map((ins, i) => (
                  <InsightCard key={i} insight={ins} index={i} prefersReduced={false} />
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}

function ButterflyIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <path d="M24 24 C18 16, 6 12, 4 20 C2 28, 12 32, 24 24Z" fill="rgba(124,58,237,0.7)" />
      <path d="M24 24 C30 16, 42 12, 44 20 C46 28, 36 32, 24 24Z" fill="rgba(124,58,237,0.7)" />
      <path d="M24 24 C18 30, 8 34, 10 40 C12 46, 22 42, 24 24Z" fill="rgba(124,58,237,0.4)" />
      <path d="M24 24 C30 30, 40 34, 38 40 C36 46, 26 42, 24 24Z" fill="rgba(124,58,237,0.4)" />
      <line x1="24" y1="10" x2="24" y2="38" stroke="rgba(167,139,250,0.6)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
