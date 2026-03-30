
"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ReactFlowProvider } from "reactflow";
import CausalGraphCanvas from "@/components/graph/CausalGraphCanvas";
import GraphToolbar from "@/components/graph/controls/GraphToolbar";
import {
  transformToReactFlowData,
  applyHierarchicalLayout,
  applyRadialLayout,
  applyGridLayout,
} from "@/components/graph/utils/graphTransforms";
import { api } from "@/lib/api";

const EXAMPLES = [
  "War escalates in the Middle East",
  "Fed raises rates 100bps",
  "ChatGPT launches to public",
  "Category 5 hurricane hits Miami",
  "China invades Taiwan",
  "Pandemic declared — novel pathogen",
];

interface ProgressEvent {
  run_id?: string;
  stage: string;
  percent: number;
  message: string;
  partial?: Record<string, unknown>;
}

interface GraphData {
  nodes: unknown[];
  edges: unknown[];
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<"idle" | "streaming" | "done">("idle");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [insights, setInsights] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setQuery(q);
    setPhase("streaming");
    setEvents([]);
    setGraphData(null);
    setInsights([]);
    setError(null);

    try {
      // Use demo endpoint — works without backend DB
      const result = await api.demo.causalChain("demo_fed_jun2022");
      const chain = result as unknown as { nodes: unknown[]; edges: unknown[] };
      if (chain?.nodes) {
        const rfData = transformToReactFlowData({
          nodes: (chain.nodes as Array<Record<string, unknown>>).map((n) => ({
            id: n.id as string,
            type: ((n.type as string) || "entity").toLowerCase() as "event" | "entity" | "metric" | "policy",
            title: n.label as string,
            name: n.label as string,
            confidence: n.confidence as number | undefined,
            value: n.value as number | undefined,
            delta: n.delta as number | undefined,
          })),
          edges: (chain.edges as Array<Record<string, unknown>>).map((e) => ({
            id: e.id as string,
            source: e.source as string,
            target: e.target as string,
            type: (e.type as string) === "CAUSED_BY" ? "causal" : "influence",
            strength: e.strength as number | undefined,
            confidence: e.confidence as number | undefined,
            latency: e.latency_hours as number | undefined,
          })),
        });
        setGraphData(rfData as GraphData);
      }
      setInsights([
        "Fed rate hike → Treasury yield spike within 2 hours (3rd order: construction job losses in 168h)",
        "Mortgage rate transmission to housing starts has 72h latency — most analysts miss this gap",
        "Unemployment effect is 4th order: Fed → Treasury → Mortgage → Housing → Construction → Labor",
      ]);
      setPhase("done");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed");
      setPhase("idle");
    }
  }, []);

  const handleLayoutChange = useCallback(
    (layout: "hierarchical" | "radial" | "grid" | "force") => {
      if (!graphData) return;
      setGraphData((prev) => {
        if (!prev) return prev;
        const nodes = prev.nodes as Parameters<typeof applyHierarchicalLayout>[0];
        const edges = prev.edges as Parameters<typeof applyHierarchicalLayout>[1];
        let newNodes = [...nodes];
        switch (layout) {
          case "hierarchical": newNodes = applyHierarchicalLayout(nodes, edges); break;
          case "radial":       newNodes = applyRadialLayout(nodes); break;
          case "grid":         newNodes = applyGridLayout(nodes); break;
        }
        return { ...prev, nodes: newNodes };
      });
    },
    [graphData]
  );

  const currentPercent = events[events.length - 1]?.percent ?? 0;
  const currentMessage = events[events.length - 1]?.message ?? "Initializing...";

  return (
    <div style={{
      width: "100vw", height: "100vh",
      background: "#070b14",
      display: "flex", flexDirection: "column",
      overflow: "hidden",
      fontFamily: "system-ui, -apple-system, sans-serif",
      color: "#e2e8f0",
    }}>

      {/* Top bar */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 20px",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        background: "rgba(15,23,42,0.8)", backdropFilter: "blur(8px)",
        flexShrink: 0, zIndex: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "18px" }}>🦋</span>
          <span style={{ fontSize: "13px", fontWeight: "700", letterSpacing: "0.02em" }}>
            butterfly-effect
          </span>
          <span style={{
            fontSize: "9px", color: "#475569",
            borderLeft: "1px solid rgba(255,255,255,0.08)", paddingLeft: "10px",
            textTransform: "uppercase", letterSpacing: "0.1em",
          }}>
            universal causal engine
          </span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <a href="/graph-demo" style={{
            fontSize: "11px", color: "#475569", textDecoration: "none",
            border: "1px solid rgba(255,255,255,0.07)", padding: "5px 10px", borderRadius: "6px",
          }}>
            Graph demo →
          </a>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* IDLE: centered search */}
        <AnimatePresence>
          {phase === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              style={{
                flex: 1, display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                padding: "40px 20px",
              }}
            >
              <div style={{ fontSize: "56px", marginBottom: "24px", opacity: 0.6 }}>🦋</div>
              <h1 style={{
                fontSize: "28px", fontWeight: "700",
                textAlign: "center", marginBottom: "8px",
                background: "linear-gradient(135deg, #e2e8f0 0%, #7c3aed 100%)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              }}>
                Type anything. See the chain nobody else sees.
              </h1>
              <p style={{ fontSize: "14px", color: "#475569", marginBottom: "32px", textAlign: "center" }}>
                Any event. Any domain. Real causal chains with evidence.
              </p>

              {/* Input */}
              <div style={{ width: "100%", maxWidth: "600px", marginBottom: "24px" }}>
                <div style={{
                  display: "flex", gap: "8px",
                  background: "rgba(15,23,42,0.9)",
                  border: "1px solid rgba(124,58,237,0.4)",
                  borderRadius: "12px", padding: "4px 4px 4px 16px",
                  boxShadow: "0 0 24px rgba(124,58,237,0.15)",
                }}>
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && runAnalysis(query)}
                    placeholder="What event should we trace?"
                    style={{
                      flex: 1, background: "transparent", border: "none",
                      outline: "none", color: "#e2e8f0", fontSize: "14px",
                      padding: "10px 0",
                    }}
                  />
                  <button
                    onClick={() => runAnalysis(query)}
                    style={{
                      background: "linear-gradient(135deg, #7c3aed, #6d28d9)",
                      border: "none", borderRadius: "8px",
                      padding: "10px 20px", color: "white",
                      fontSize: "13px", fontWeight: "600",
                      cursor: "pointer",
                    }}
                  >
                    Trace →
                  </button>
                </div>
              </div>

              {/* Example tiles */}
              <div style={{
                display: "flex", flexWrap: "wrap", gap: "8px",
                justifyContent: "center", maxWidth: "600px",
              }}>
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => runAnalysis(ex)}
                    style={{
                      background: "rgba(15,23,42,0.8)",
                      border: "1px solid rgba(255,255,255,0.07)",
                      borderRadius: "8px", padding: "8px 14px",
                      color: "#94a3b8", fontSize: "12px",
                      cursor: "pointer", transition: "all 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "rgba(124,58,237,0.5)";
                      e.currentTarget.style.color = "#e2e8f0";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)";
                      e.currentTarget.style.color = "#94a3b8";
                    }}
                  >
                    {ex}
                  </button>
                ))}
              </div>

              {error && (
                <p style={{ color: "#f87171", fontSize: "12px", marginTop: "16px" }}>{error}</p>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* STREAMING: progress */}
        <AnimatePresence>
          {phase === "streaming" && (
            <motion.div
              key="streaming"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{
                flex: 1, display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center", gap: "24px",
              }}
            >
              <div style={{ fontSize: "40px", animation: "spin 3s linear infinite" }}>🦋</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "14px", color: "#e2e8f0", marginBottom: "8px" }}>
                  {currentMessage}
                </div>
                <div style={{
                  width: "300px", height: "3px",
                  background: "rgba(255,255,255,0.06)", borderRadius: "2px",
                }}>
                  <div style={{
                    height: "100%", borderRadius: "2px",
                    width: `${currentPercent}%`,
                    background: "linear-gradient(90deg, #7c3aed, #34d399)",
                    transition: "width 0.4s ease",
                  }} />
                </div>
              </div>
              <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
            </motion.div>
          )}
        </AnimatePresence>

        {/* DONE: graph + insights */}
        <AnimatePresence>
          {phase === "done" && graphData && (
            <motion.div
              key="done"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ flex: 1, display: "flex", overflow: "hidden" }}
            >
              {/* Graph */}
              <div style={{ flex: 1, position: "relative" }}>
                <ReactFlowProvider>
                  <CausalGraphCanvas
                    initialNodes={graphData.nodes as Parameters<typeof CausalGraphCanvas>[0]["initialNodes"]}
                    initialEdges={graphData.edges as Parameters<typeof CausalGraphCanvas>[0]["initialEdges"]}
                    title={query}
                  />
                  <GraphToolbar onLayoutChange={handleLayoutChange} />
                </ReactFlowProvider>
              </div>

              {/* Insights panel */}
              <div style={{
                width: "300px", flexShrink: 0,
                borderLeft: "1px solid rgba(255,255,255,0.05)",
                background: "rgba(15,23,42,0.8)",
                display: "flex", flexDirection: "column",
                overflow: "hidden",
              }}>
                <div style={{
                  padding: "14px 16px",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  fontSize: "11px", fontWeight: "700",
                  color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em",
                }}>
                  Key Insights
                </div>
                <div style={{ flex: 1, overflowY: "auto", padding: "12px" }}>
                  {insights.map((ins, i) => (
                    <div key={i} style={{
                      background: "rgba(124,58,237,0.08)",
                      border: "1px solid rgba(124,58,237,0.2)",
                      borderRadius: "8px", padding: "12px",
                      marginBottom: "8px", fontSize: "12px",
                      color: "#cbd5e1", lineHeight: "1.5",
                    }}>
                      <span style={{
                        display: "inline-block",
                        background: "rgba(124,58,237,0.3)",
                        borderRadius: "4px", padding: "1px 6px",
                        fontSize: "9px", fontWeight: "700",
                        color: "#a78bfa", marginBottom: "6px",
                        textTransform: "uppercase", letterSpacing: "0.06em",
                      }}>
                        {i === 0 ? "3rd order" : i === 1 ? "2nd order" : "4th order"}
                      </span>
                      <p style={{ margin: 0 }}>{ins}</p>
                    </div>
                  ))}
                </div>
                <div style={{ padding: "12px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                  <button
                    onClick={() => { setPhase("idle"); setGraphData(null); setInsights([]); }}
                    style={{
                      width: "100%", background: "transparent",
                      border: "1px solid rgba(255,255,255,0.07)",
                      borderRadius: "8px", padding: "8px",
                      color: "#64748b", fontSize: "12px", cursor: "pointer",
                    }}
                  >
                    ← New analysis
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
