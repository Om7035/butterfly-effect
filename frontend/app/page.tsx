"use client";

// imports resolved — AnalysisStream, InsightCard, EvidencePanelNew, TemporalReplay
import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { ReactFlowProvider } from "reactflow";
import { Search, Zap, ArrowRight, Globe, TrendingUp, AlertTriangle } from "lucide-react";
import CausalGraphCanvas from "@/components/graph/CausalGraphCanvas";
import GraphToolbar from "@/components/graph/controls/GraphToolbar";
import AnalysisStream from "@/components/AnalysisStream";
import InsightCard from "@/components/InsightCard";
import EvidencePanelNew from "@/components/EvidencePanelNew";
import TemporalReplay from "@/components/TemporalReplay";
import {
  transformToReactFlowData,
  applyHierarchicalLayout,
} from "@/components/graph/utils/graphTransforms";
import { api } from "@/lib/api";

const EXAMPLES = [
  { text: "War escalates in Middle East",       icon: <AlertTriangle size={12} />, color: "#ef4444" },
  { text: "Fed raises rates 100bps",            icon: <TrendingUp size={12} />,    color: "#f59e0b" },
  { text: "ChatGPT launches to public",         icon: <Zap size={12} />,           color: "#8b5cf6" },
  { text: "Category 5 hurricane hits Miami",    icon: <Globe size={12} />,         color: "#3b82f6" },
  { text: "China invades Taiwan",               icon: <AlertTriangle size={12} />, color: "#ef4444" },
  { text: "Pandemic declared — novel pathogen", icon: <Globe size={12} />,         color: "#10b981" },
];

const STAGE_ORDER = ["parsing", "fetching", "extracting", "causal_modeling", "simulating", "extracting_chain", "done"] as const;

interface GraphData { nodes: unknown[]; edges: unknown[] }
interface Insight { order: number; hop: number; text: string; why: string; confidence: number; sources: string[] }

/** Parse LLM insight strings into structured InsightCard props */
function parseInsights(raw: string[]): Insight[] {
  return raw.map((text, i) => {
    const orderMatch = text.match(/(\d+)(st|nd|rd|th)\s+order/i);
    const order = orderMatch ? parseInt(orderMatch[1]) : (i === 0 ? 2 : i === 1 ? 3 : 4);
    return {
      order,
      hop: order,
      text: text.replace(/^What most people miss:\s*/i, ""),
      why: "",
      confidence: Math.max(0.5, 0.9 - i * 0.12),
      sources: [],
    };
  });
}

/** Convert backend causal_chain dict to React Flow nodes/edges */
function chainToGraphData(chain: Record<string, unknown>): GraphData | null {
  // Chain from simulation extractor: has "chains" (hops) array
  const hops = chain.chains as Array<Record<string, unknown>> | undefined;
  // Chain from DAG: has "nodes" and "edges" arrays
  const rawNodes = chain.nodes as Array<Record<string, unknown>> | undefined;
  const rawEdges = chain.edges as Array<Record<string, unknown>> | undefined;

  if (rawNodes && rawNodes.length > 0) {
    // DAG-style chain
    const rfData = transformToReactFlowData({
      nodes: rawNodes.map((n) => ({
        id: (n.id as string) || String(Math.random()),
        type: ((n.type as string) || "entity").toLowerCase() as "event" | "entity" | "metric" | "policy",
        title: (n.label as string) || (n.id as string),
        name: (n.label as string) || (n.id as string),
        confidence: n.confidence as number | undefined,
        value: n.value as number | undefined,
        delta: n.delta as number | undefined,
      })),
      edges: (rawEdges || []).map((e, i) => ({
        id: (e.id as string) || `e${i}`,
        source: e.source as string,
        target: e.target as string,
        type: (e.type as string) === "CAUSED_BY" || (e.type as string) === "causal" ? "causal" : "influence",
        strength: e.strength as number | undefined,
        confidence: (e.confidence as number) || 0.7,
        latency: (e.latency_hours as number) || (e.latency as number) || 0,
      })),
    });
    const laid = applyHierarchicalLayout(
      rfData.nodes as Parameters<typeof applyHierarchicalLayout>[0],
      rfData.edges as Parameters<typeof applyHierarchicalLayout>[1]
    );
    return { nodes: laid, edges: rfData.edges };
  }

  if (hops && hops.length > 0) {
    // Simulation extractor style — build nodes/edges from hops
    const nodes: Array<Record<string, unknown>> = [];
    const edges: Array<Record<string, unknown>> = [];
    const seen = new Set<string>();

    hops.forEach((hop, i) => {
      const fromId = (hop.from_agent as string) || `agent_${i}`;
      const toId = (hop.to_variable as string) || `var_${i}`;
      if (!seen.has(fromId)) { seen.add(fromId); nodes.push({ id: fromId, type: "entity", title: fromId, name: fromId }); }
      if (!seen.has(toId)) { seen.add(toId); nodes.push({ id: toId, type: "metric", title: toId.replace(/_/g, " "), name: toId.replace(/_/g, " "), confidence: hop.confidence as number }); }
      edges.push({ id: `e${i}`, source: fromId, target: toId, type: "causal", confidence: hop.confidence as number || 0.7, latency: hop.step_triggered as number || 0 });
    });

    const rfData = transformToReactFlowData({ nodes: nodes as Parameters<typeof transformToReactFlowData>[0]["nodes"], edges: edges as Parameters<typeof transformToReactFlowData>[0]["edges"] });
    const laid = applyHierarchicalLayout(
      rfData.nodes as Parameters<typeof applyHierarchicalLayout>[0],
      rfData.edges as Parameters<typeof applyHierarchicalLayout>[1]
    );
    return { nodes: laid, edges: rfData.edges };
  }

  return null;
}

export default function Home() {
  const prefersReduced = useReducedMotion();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<"idle" | "streaming" | "done">("idle");
  const [stage, setStage] = useState(0);
  const [currentMessage, setCurrentMessage] = useState("");
  const [liveStats, setLiveStats] = useState({ nodes: 0, agents: 0, steps: 0 });
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);

  const runAnalysis = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setQuery(q);
    setPhase("streaming");
    setStage(0);
    setCurrentMessage("Connecting to analysis engine...");
    setLiveStats({ nodes: 0, agents: 0, steps: 0 });
    setGraphData(null);
    setInsights([]);
    setError(null);
    setSelectedNodeId(null);

    try {
      await api.analyze.stream(q, (event) => {
        const ev = event as {
          run_id?: string;
          stage?: string;
          percent?: number;
          message?: string;
          partial?: Record<string, unknown>;
          result?: Record<string, unknown>;
        };

        // Update stage indicator
        if (ev.stage) {
          const idx = STAGE_ORDER.indexOf(ev.stage as typeof STAGE_ORDER[number]);
          if (idx >= 0) setStage(idx);
          setCurrentMessage(ev.message || ev.stage);
        }

        if (ev.run_id) setRunId(ev.run_id);

        // Extract live stats from partial results
        const partial = ev.partial || {};
        if (partial.n_agents) setLiveStats(prev => ({ ...prev, agents: partial.n_agents as number }));
        if (partial.diverging_vars) setLiveStats(prev => ({ ...prev, nodes: partial.diverging_vars as number }));

        // On complete — extract full result
        if (ev.stage === "complete" && ev.result) {
          const result = ev.result;
          const chain = result.causal_chain as Record<string, unknown> | undefined;
          const rawInsights = result.insights as string[] | undefined;

          // Build graph
          if (chain) {
            const gd = chainToGraphData(chain);
            if (gd) {
              setGraphData(gd);
              setLiveStats({
                nodes: gd.nodes.length,
                agents: (chain.total_hops as number) || gd.edges.length,
                steps: (chain.total_hops as number) || 0,
              });
            }
          }

          // Parse insights
          if (rawInsights && rawInsights.length > 0) {
            setInsights(parseInsights(rawInsights));
          }

          setPhase("done");
        }
      });

      // If stream ended without a complete event (shouldn't happen but be safe)
      if (phase === "streaming") {
        setError("Analysis stream ended unexpectedly. Try again.");
        setPhase("idle");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Analysis failed";
      setError(msg);
      setPhase("idle");
    }
  }, [phase]);

  const handleLayoutChange = useCallback(
    (layout: "hierarchical" | "radial" | "grid" | "force") => {
      if (!graphData) return;
      setGraphData((prev) => {
        if (!prev) return prev;
        const nodes = prev.nodes as Parameters<typeof applyHierarchicalLayout>[0];
        const edges = prev.edges as Parameters<typeof applyHierarchicalLayout>[1];
        if (layout === "hierarchical") return { ...prev, nodes: applyHierarchicalLayout(nodes, edges) };
        return prev;
      });
    },
    [graphData]
  );

  const shareUrl = runId
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/analysis/${runId}`
    : null;

  return (
    <div style={{ width: "100vw", height: "100vh", background: "#0a0e1a", display: "flex", flexDirection: "column", overflow: "hidden", fontFamily: "system-ui, -apple-system, sans-serif", color: "#e2e8f0" }}>
      {/* Top bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 20px", borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.9)", backdropFilter: "blur(12px)", flexShrink: 0, zIndex: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <ButterflyIcon size={22} />
          <span style={{ fontSize: "13px", fontWeight: "700", letterSpacing: "0.02em" }}>butterfly-effect</span>
          <span style={{ fontSize: "9px", color: "#475569", borderLeft: "1px solid rgba(255,255,255,0.08)", paddingLeft: "10px", textTransform: "uppercase", letterSpacing: "0.1em" }}>universal causal engine</span>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {phase === "done" && shareUrl && (
            <button onClick={() => navigator.clipboard.writeText(shareUrl)} style={{ fontSize: "11px", color: "#7c3aed", background: "rgba(124,58,237,0.1)", border: "1px solid rgba(124,58,237,0.3)", padding: "5px 12px", borderRadius: "6px", cursor: "pointer" }}>
              Share ↗
            </button>
          )}
          <a href="/demo" style={{ fontSize: "11px", color: "#475569", textDecoration: "none", border: "1px solid rgba(255,255,255,0.07)", padding: "5px 10px", borderRadius: "6px" }}>Demo →</a>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative" }}>
        <AnimatePresence mode="wait">
          {phase === "idle" && <IdleView key="idle" query={query} setQuery={setQuery} onSubmit={runAnalysis} error={error} prefersReduced={!!prefersReduced} inputRef={inputRef} />}
          {phase === "streaming" && <AnalysisStream key="stream" stage={stage} stages={STAGE_ORDER} liveStats={liveStats} query={query} prefersReduced={!!prefersReduced} currentMessage={currentMessage} />}
          {phase === "done" && graphData && (
            <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ flex: 1, display: "flex", overflow: "hidden" }}>
              {/* Graph area */}
              <div style={{ flex: 1, position: "relative", display: "flex", flexDirection: "column" }}>
                {/* Query bar */}
                <div style={{ padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.8)", display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
                  <Search size={14} color="#475569" />
                  <span style={{ fontSize: "13px", color: "#94a3b8", flex: 1 }}>{query}</span>
                  <span style={{ fontSize: "10px", color: "#475569", fontFamily: "monospace" }}>{liveStats.nodes} nodes · {liveStats.agents} agents · {liveStats.steps} steps</span>
                  <button onClick={() => { setPhase("idle"); setGraphData(null); setInsights([]); }} style={{ fontSize: "11px", color: "#475569", background: "none", border: "1px solid rgba(255,255,255,0.07)", padding: "4px 10px", borderRadius: "6px", cursor: "pointer" }}>← New</button>
                </div>
                <div style={{ flex: 1, position: "relative" }}>
                  <ReactFlowProvider>
                    <CausalGraphCanvas
                      initialNodes={graphData.nodes as Parameters<typeof CausalGraphCanvas>[0]["initialNodes"]}
                      initialEdges={graphData.edges as Parameters<typeof CausalGraphCanvas>[0]["initialEdges"]}
                      title={query}
                      onNodeClick={(id) => setSelectedNodeId(id)}
                    />
                    <GraphToolbar onLayoutChange={handleLayoutChange} />
                  </ReactFlowProvider>
                </div>
                <TemporalReplay prefersReduced={!!prefersReduced} />
              </div>
              {/* Right panel */}
              <div style={{ width: "320px", flexShrink: 0, borderLeft: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.9)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
                <AnimatePresence mode="wait">
                  {selectedNodeId ? (
                    <motion.div key="evidence" initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 20, opacity: 0 }} style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                      <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "10px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: "700" }}>Evidence</span>
                        <button onClick={() => setSelectedNodeId(null)} style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: "16px", lineHeight: 1 }}>×</button>
                      </div>
                      <EvidencePanelNew nodeId={selectedNodeId} />
                    </motion.div>
                  ) : (
                    <motion.div key="insights" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                      <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ fontSize: "10px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: "700" }}>Key Insights</span>
                      </div>
                      <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                        {insights.map((ins, i) => <InsightCard key={i} insight={ins} index={i} prefersReduced={!!prefersReduced} />)}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ButterflyIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M24 24 C18 16, 6 12, 4 20 C2 28, 12 32, 24 24Z" fill="rgba(124,58,237,0.7)" />
      <path d="M24 24 C30 16, 42 12, 44 20 C46 28, 36 32, 24 24Z" fill="rgba(124,58,237,0.7)" />
      <path d="M24 24 C18 30, 8 34, 10 40 C12 46, 22 42, 24 24Z" fill="rgba(124,58,237,0.4)" />
      <path d="M24 24 C30 30, 40 34, 38 40 C36 46, 26 42, 24 24Z" fill="rgba(124,58,237,0.4)" />
      <line x1="24" y1="10" x2="24" y2="38" stroke="rgba(167,139,250,0.6)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function IdleView({ query, setQuery, onSubmit, error, prefersReduced, inputRef }: {
  query: string;
  setQuery: (v: string) => void;
  onSubmit: (q: string) => void;
  error: string | null;
  prefersReduced: boolean;
  inputRef: React.RefObject<HTMLInputElement>;
}) {
  useEffect(() => { inputRef.current?.focus(); }, [inputRef]);

  return (
    <motion.div
      initial={{ opacity: 0, y: prefersReduced ? 0 : 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: prefersReduced ? 0 : -24 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px", gap: "0" }}
    >
      {/* Butterfly hero */}
      <motion.div
        animate={prefersReduced ? {} : { y: [0, -6, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        style={{ marginBottom: "28px", opacity: 0.85 }}
      >
        <ButterflyIcon size={72} />
      </motion.div>

      <h1 style={{ fontSize: "clamp(22px, 4vw, 36px)", fontWeight: "800", textAlign: "center", marginBottom: "10px", background: "linear-gradient(135deg, #e2e8f0 0%, #a78bfa 60%, #7c3aed 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", letterSpacing: "-0.02em", lineHeight: 1.15 }}>
        Type anything. See the chain<br />nobody else sees.
      </h1>
      <p style={{ fontSize: "14px", color: "#475569", marginBottom: "36px", textAlign: "center", maxWidth: "420px", lineHeight: 1.6 }}>
        Any event. Any domain. Real causal chains with evidence — traced to the 4th order.
      </p>

      {/* Input */}
      <div style={{ width: "100%", maxWidth: "620px", marginBottom: "20px" }}>
        <div style={{ display: "flex", gap: "0", background: "rgba(15,23,42,0.95)", border: "1px solid rgba(124,58,237,0.45)", borderRadius: "14px", padding: "4px 4px 4px 18px", boxShadow: "0 0 40px rgba(124,58,237,0.12), 0 0 0 1px rgba(124,58,237,0.08)", transition: "box-shadow 0.2s" }}>
          <Search size={16} color="#475569" style={{ alignSelf: "center", flexShrink: 0, marginRight: "8px" }} />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSubmit(query)}
            placeholder="What event should we trace?"
            style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#e2e8f0", fontSize: "15px", padding: "12px 0", fontFamily: "inherit" }}
          />
          <button
            onClick={() => onSubmit(query)}
            disabled={!query.trim()}
            style={{ background: query.trim() ? "linear-gradient(135deg, #7c3aed, #6d28d9)" : "rgba(124,58,237,0.2)", border: "none", borderRadius: "10px", padding: "10px 22px", color: query.trim() ? "white" : "#475569", fontSize: "13px", fontWeight: "700", cursor: query.trim() ? "pointer" : "default", transition: "all 0.2s", display: "flex", alignItems: "center", gap: "6px", whiteSpace: "nowrap" }}
          >
            Trace <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Example tiles */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", justifyContent: "center", maxWidth: "620px" }}>
        {EXAMPLES.map((ex) => (
          <ExampleTile key={ex.text} example={ex} onClick={() => onSubmit(ex.text)} prefersReduced={prefersReduced} />
        ))}
      </div>

      {error && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ color: "#f87171", fontSize: "12px", marginTop: "16px", background: "rgba(239,68,68,0.1)", padding: "8px 14px", borderRadius: "8px", border: "1px solid rgba(239,68,68,0.2)" }}>
          {error}
        </motion.p>
      )}
    </motion.div>
  );
}

function ExampleTile({ example, onClick, prefersReduced }: { example: typeof EXAMPLES[0]; onClick: () => void; prefersReduced: boolean }) {
  const [hovered, setHovered] = useState(false);
  return (
    <motion.button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      whileHover={prefersReduced ? {} : { scale: 1.03, y: -1 }}
      whileTap={prefersReduced ? {} : { scale: 0.97 }}
      style={{ background: hovered ? "rgba(124,58,237,0.1)" : "rgba(15,23,42,0.8)", border: `1px solid ${hovered ? "rgba(124,58,237,0.4)" : "rgba(255,255,255,0.07)"}`, borderRadius: "10px", padding: "8px 14px", color: hovered ? "#e2e8f0" : "#94a3b8", fontSize: "12px", cursor: "pointer", transition: "all 0.2s", display: "flex", alignItems: "center", gap: "6px", fontFamily: "inherit" }}
    >
      <span style={{ color: example.color, opacity: 0.8 }}>{example.icon}</span>
      {example.text}
    </motion.button>
  );
}
