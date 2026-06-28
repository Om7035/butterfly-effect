"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { ReactFlowProvider } from "reactflow";
import { Search, Zap, ArrowRight, Globe, TrendingUp, AlertTriangle } from "lucide-react";
import CausalGraphCanvas from "@/components/graph/CausalGraphCanvas";
import GraphToolbar from "@/components/graph/controls/GraphToolbar";
import AnalysisStream from "@/components/AnalysisStream";
import InsightCard from "@/components/InsightCard";
import EvidencePanelNew from "@/components/EvidencePanelNew";
import ChainView from "@/components/chain/ChainView";
import Timeline from "@/components/chain/Timeline";
import { buildChainModel, type RawNode, type RawEdge, type RawInsight } from "@/lib/chainData";
import { categorizeInsights } from "@/lib/insightCategories";
import {
  transformToReactFlowData,
  applyHierarchicalLayout,
  applyRadialLayout,
  applyGridLayout,
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

const STAGE_ORDER = ["parsing", "fetching", "extracting", "simulating", "done"] as const;

interface GraphData { nodes: unknown[]; edges: unknown[] }
interface Insight {
  order: number; hop: number; text: string; why: string;
  confidence: number; sources: string[];
  snn_verified?: boolean; snn_max_cci?: number;
}

function backendToGraphData(
  rawNodes: Array<Record<string, unknown>>,
  rawEdges: Array<Record<string, unknown>>,
  eventMeta?: Record<string, unknown>
): GraphData {
  const typeMap: Record<string, "event" | "entity" | "metric" | "policy"> = {
    Event: "event", Entity: "entity", Metric: "metric", Policy: "policy",
    event: "event", entity: "entity", metric: "metric", policy: "policy",
  };

  const rfData = transformToReactFlowData({
    nodes: rawNodes.map((n) => ({
      id: (n.id as string) || String(Math.random()),
      type: typeMap[(n.type as string) || "entity"] || "entity",
      title: (n.label as string) || (n.id as string),
      name: (n.label as string) || (n.id as string),
      confidence: n.confidence as number | undefined,
      strength: n.strength as number | undefined,
      value: n.value as number | undefined,
      delta: n.delta as number | undefined,
      hop: n.hop as number | undefined,
      domain: n.domain as string | undefined,
      // Inject severity from event_meta into the root node
      severity: (n.id === "root" && eventMeta?.severity)
        ? (eventMeta.severity as string)
        : (n.severity as string | undefined),
      fred_series: n.fred_series as string | undefined,
      fred_date: n.fred_date as string | undefined,
      source: n.source as string | undefined,
    })),
    edges: rawEdges.map((e, i) => {
      const conf = Array.isArray(e.confidence)
        ? (e.confidence as number[])[0]
        : (e.confidence as number) || 0.7;
      return {
        id: (e.id as string) || `e${i}`,
        source: e.source as string,
        target: e.target as string,
        type: "causal" as const,
        strength: e.strength as number | undefined,
        confidence: conf,
        latency: (e.latency_hours as number) || 0,
      };
    }),
  });

  // Inject edge confidence + strength into target nodes so they can show impact
  const edgeConfByTarget: Record<string, { conf: number; strength: number }> = {};
  for (const e of rawEdges) {
    const tgt = e.target as string;
    const conf = Array.isArray(e.confidence)
      ? (e.confidence as number[])[0]
      : (e.confidence as number) || 0.7;
    const str = (e.strength as number) || 0.5;
    if (!edgeConfByTarget[tgt] || conf > edgeConfByTarget[tgt].conf) {
      edgeConfByTarget[tgt] = { conf, strength: str };
    }
  }

  const enrichedNodes = rfData.nodes.map((node) => {
    const edgeData = edgeConfByTarget[node.id];
    if (edgeData && !node.data.confidence) {
      return {
        ...node,
        data: {
          ...node.data,
          confidence: edgeData.conf,
          strength: edgeData.strength,
        },
      };
    }
    return node;
  });

  const laid = applyHierarchicalLayout(
    enrichedNodes as Parameters<typeof applyHierarchicalLayout>[0],
    rfData.edges as Parameters<typeof applyHierarchicalLayout>[1]
  );
  return { nodes: laid, edges: rfData.edges };
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
  const [rawGraph, setRawGraph] = useState<{ nodes: RawNode[]; edges: RawEdge[] } | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [liveEvidence, setLiveEvidence] = useState<Array<{node_id:string;source:string;title:string;content:string;url?:string;relevance:number}>>([]);
  const [fredData, setFredData] = useState<Record<string, {value:number;delta:number;date:string}>>({});
  const [predictabilityHorizon, setPredictabilityHorizon] = useState<{hours:number;label:string;warning:string} | undefined>(undefined);

  // View toggle — persisted across analyses within the session
  const [viewMode, setViewMode] = useState<"chain" | "graph">("chain");
  useEffect(() => {
    const saved = typeof window !== "undefined" ? window.sessionStorage.getItem("be_view_mode") : null;
    if (saved === "chain" || saved === "graph") setViewMode(saved);
  }, []);
  const updateViewMode = useCallback((mode: "chain" | "graph") => {
    setViewMode(mode);
    if (typeof window !== "undefined") window.sessionStorage.setItem("be_view_mode", mode);
  }, []);

  // Mobile: Chain View only, Graph/Timeline hidden with a "best on desktop" notice
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Chain View hop refs + playhead-crossing pulse
  const hopRefs = useRef<Map<string, HTMLDivElement | null>>(new Map());
  const [pulsingHopId, setPulsingHopId] = useState<string | null>(null);
  const pulseTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const registerHopRef = useCallback((hopId: string, el: HTMLDivElement | null) => {
    hopRefs.current.set(hopId, el);
  }, []);

  const focusHop = useCallback((hopId: string) => {
    const el = hopRefs.current.get(hopId);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    setPulsingHopId(hopId);
    if (pulseTimeoutRef.current) clearTimeout(pulseTimeoutRef.current);
    pulseTimeoutRef.current = setTimeout(() => setPulsingHopId(null), 350);
  }, []);

  const chainModel = useMemo(() => {
    if (!rawGraph) return { trigger: null, hops: [] };
    return buildChainModel(rawGraph.nodes, rawGraph.edges, insights as unknown as RawInsight[]);
  }, [rawGraph, insights]);

  // Source-tag filter — clicking a source tag in an insight dims unsupported graph nodes
  const [activeSource, setActiveSource] = useState<string | null>(null);
  const handleSourceClick = useCallback((source: string) => {
    setActiveSource((prev) => (prev === source ? null : source));
  }, []);
  const sourceMatchedNodeIds = useMemo(() => {
    if (!activeSource) return null;
    return new Set(liveEvidence.filter((e) => e.source === activeSource).map((e) => e.node_id));
  }, [activeSource, liveEvidence]);
  const displayGraphData = useMemo(() => {
    if (!graphData || !sourceMatchedNodeIds) return graphData;
    return {
      ...graphData,
      nodes: (graphData.nodes as Array<Record<string, unknown>>).map((n) => ({
        ...n,
        data: { ...(n.data as Record<string, unknown>), dimmed: !sourceMatchedNodeIds.has(n.id as string) },
      })),
    };
  }, [graphData, sourceMatchedNodeIds]);

  const runAnalysis = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setQuery(q);
    setPhase("streaming");
    setStage(0);
    setCurrentMessage("Connecting to analysis engine...");
    setLiveStats({ nodes: 0, agents: 0, steps: 0 });
    setGraphData(null);
    setRawGraph(null);
    setInsights([]);
    setError(null);
    setSelectedNodeId(null);
    setLiveEvidence([]);
    setFredData({});
    setPredictabilityHorizon(undefined);
    setPulsingHopId(null);

    try {
      await api.analyze.stream(q, (event) => {
        const ev = event as Record<string, unknown>;

        if (ev.error) {
          console.error("Analysis pipeline error (in-stream):", ev.error);
          setError("Analysis failed — the pipeline returned an error. Try rephrasing the event.");
          setPhase("idle");
          return;
        }

        if (ev.stage) {
          const idx = STAGE_ORDER.indexOf(ev.stage as typeof STAGE_ORDER[number]);
          if (idx >= 0) setStage(idx);
          if (ev.message) setCurrentMessage(ev.message as string);
        }

        if (ev.run_id) setRunId(ev.run_id as string);

        if (ev.stats) {
          const s = ev.stats as { nodes?: number; agents?: number; steps?: number };
          setLiveStats({ nodes: s.nodes || 0, agents: s.agents || 0, steps: s.steps || 0 });
        }

        if (ev.stage === "done") {
          const rawNodes = ev.nodes as Array<Record<string, unknown>> | undefined;
          const rawEdges = ev.edges as Array<Record<string, unknown>> | undefined;
          const rawInsights = ev.insights as Insight[] | undefined;

          if (rawNodes && rawNodes.length > 0) {
            const gd = backendToGraphData(rawNodes, rawEdges || [], ev.event_meta as Record<string, unknown> | undefined);
            setGraphData(gd);
            setRawGraph({
              nodes: rawNodes.map((n) => ({
                id: n.id as string,
                type: n.type as string | undefined,
                label: n.label as string | undefined,
                hop: n.hop as number | undefined,
                domain: n.domain as string | undefined,
                confidence: typeof n.confidence === "number" ? n.confidence : undefined,
                strength: n.strength as number | undefined,
                severity: (n.id === "root" ? (ev.event_meta as Record<string, unknown> | undefined)?.severity : n.severity) as string | undefined,
              })),
              edges: (rawEdges || []).map((e) => ({
                id: e.id as string | undefined,
                source: e.source as string,
                target: e.target as string,
                confidence: e.confidence as number | number[] | undefined,
                latency_hours: e.latency_hours as number | undefined,
                relationship_type: e.relationship_type as string | undefined,
                evidence_sources: e.evidence_sources as string[] | undefined,
              })),
            });
            setLiveStats({
              nodes: gd.nodes.length,
              agents: (ev.stats as { agents?: number })?.agents || 0,
              steps: (ev.stats as { steps?: number })?.steps || 0,
            });
          }

          if (rawInsights && rawInsights.length > 0) {
            setInsights(rawInsights);
          }

          // Store live evidence and FRED data for evidence panel
          if (ev.evidence) setLiveEvidence(ev.evidence as any[]);
          if (ev.fred_data) setFredData(ev.fred_data as any);
          if (ev.predictability_horizon) setPredictabilityHorizon(ev.predictability_horizon as any);

          setPhase("done");
        }

        if (ev.done) setPhase("done");
      });
    } catch (err: unknown) {
      console.error("Analysis pipeline error:", err);
      setError("Analysis failed — the pipeline returned an error. Try rephrasing the event.");
      setPhase("idle");
    }
  }, []);

  // Handle ?q= param for direct links
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("q");
      if (q) runAnalysis(q);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLayoutChange = useCallback(
    (layout: "hierarchical" | "radial" | "grid" | "force") => {
      if (!graphData) return;
      setGraphData((prev) => {
        if (!prev) return prev;
        const nodes = prev.nodes as Parameters<typeof applyHierarchicalLayout>[0];
        const edges = prev.edges as Parameters<typeof applyHierarchicalLayout>[1];
        if (layout === "hierarchical") return { ...prev, nodes: applyHierarchicalLayout(nodes, edges) };
        if (layout === "radial") return { ...prev, nodes: applyRadialLayout(nodes) };
        if (layout === "grid") return { ...prev, nodes: applyGridLayout(nodes) };
        return prev;
      });
    },
    [graphData]
  );

  const shareUrl = runId
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/analyze/${runId}`
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
            <button onClick={() => navigator.clipboard.writeText(shareUrl)}
              style={{ fontSize: "11px", color: "#7c3aed", background: "rgba(124,58,237,0.1)", border: "1px solid rgba(124,58,237,0.3)", padding: "5px 12px", borderRadius: "6px", cursor: "pointer" }}>
              Share ↗
            </button>
          )}
          <a href="/demo" style={{ fontSize: "11px", color: "#475569", textDecoration: "none", border: "1px solid rgba(255,255,255,0.07)", padding: "5px 10px", borderRadius: "6px" }}>Demo →</a>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative" }}>
        <AnimatePresence mode="wait">
          {phase === "idle" && (
            <IdleView key="idle" query={query} setQuery={setQuery} onSubmit={runAnalysis}
              error={error} prefersReduced={!!prefersReduced} inputRef={inputRef} />
          )}
          {phase === "streaming" && (
            <AnalysisStream key="stream" stage={stage} stages={STAGE_ORDER}
              liveStats={liveStats} query={query} prefersReduced={!!prefersReduced}
              currentMessage={currentMessage} />
          )}
          {phase === "done" && graphData && (
            <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{ flex: 1, display: "flex", overflow: "hidden" }}>
              {/* Results area */}
              <div style={{ flex: 1, position: "relative", display: "flex", flexDirection: "column" }}>
                <div style={{ padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.8)", display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
                  <Search size={14} color="#475569" />
                  <span style={{ fontSize: "13px", color: "#94a3b8", flex: 1 }}>{query}</span>
                  <span style={{ fontSize: "10px", color: "#475569", fontFamily: "monospace" }}>
                    {liveStats.nodes} nodes · {liveStats.agents} agents · {liveStats.steps} steps
                  </span>
                  {!isMobile && (
                    <div style={{ display: "flex", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "7px", padding: "2px" }}>
                      {(["chain", "graph"] as const).map((mode) => (
                        <button key={mode} onClick={() => updateViewMode(mode)}
                          style={{
                            fontSize: "11px", fontWeight: "600", textTransform: "capitalize",
                            color: viewMode === mode ? "#e2e8f0" : "#64748b",
                            background: viewMode === mode ? "rgba(124,58,237,0.25)" : "none",
                            border: "none", borderRadius: "5px", padding: "4px 12px", cursor: "pointer",
                          }}>
                          {mode}
                        </button>
                      ))}
                    </div>
                  )}
                  <button onClick={() => { setPhase("idle"); setGraphData(null); setInsights([]); }}
                    style={{ fontSize: "11px", color: "#475569", background: "none", border: "1px solid rgba(255,255,255,0.07)", padding: "4px 10px", borderRadius: "6px", cursor: "pointer" }}>
                    ← New
                  </button>
                </div>

                {viewMode === "graph" && !isMobile ? (
                  <div style={{ flex: 1, position: "relative" }}>
                    <ReactFlowProvider>
                      <CausalGraphCanvas
                        initialNodes={displayGraphData!.nodes as Parameters<typeof CausalGraphCanvas>[0]["initialNodes"]}
                        initialEdges={displayGraphData!.edges as Parameters<typeof CausalGraphCanvas>[0]["initialEdges"]}
                        title={query}
                        onNodeClick={(id) => setSelectedNodeId(id)}
                      />
                      <GraphToolbar onLayoutChange={handleLayoutChange} />
                    </ReactFlowProvider>
                  </div>
                ) : (
                  <ChainView
                    chain={chainModel}
                    stats={liveStats}
                    prefersReduced={!!prefersReduced}
                    pulsingHopId={pulsingHopId}
                    registerHopRef={registerHopRef}
                  />
                )}

                {!isMobile && (
                  <Timeline
                    hops={chainModel.hops}
                    prefersReduced={!!prefersReduced}
                    onCrossMarker={focusHop}
                    onScrubToHop={focusHop}
                  />
                )}
                {isMobile && (
                  <div style={{ flexShrink: 0, padding: "8px 16px", borderTop: "1px solid rgba(255,255,255,0.05)", textAlign: "center" }}>
                    <span style={{ fontSize: "10px", color: "#475569" }}>Graph view and the replay timeline are best on desktop.</span>
                  </div>
                )}
              </div>

              {/* Right panel */}
              <div style={{ width: "320px", flexShrink: 0, borderLeft: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.9)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
                <AnimatePresence mode="wait">
                  {selectedNodeId ? (
                    <motion.div key="evidence" initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 20, opacity: 0 }}
                      style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                      <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "10px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: "700" }}>Evidence</span>
                        <button onClick={() => setSelectedNodeId(null)} style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: "16px", lineHeight: 1 }}>×</button>
                      </div>
                      <EvidencePanelNew nodeId={selectedNodeId} liveEvidence={liveEvidence} fredData={fredData} />
                    </motion.div>
                  ) : (
                    <motion.div key="insights" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                      <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "10px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: "700" }}>Key Insights</span>
                        {shareUrl && (
                          <button onClick={() => navigator.clipboard.writeText(shareUrl)}
                            style={{ fontSize: "10px", color: "#7c3aed", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                            Share ↗
                          </button>
                        )}
                      </div>
                      <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "flex", flexDirection: "column", gap: "16px" }}>
                        {categorizeInsights(insights).map((group) => (
                          <div key={group.category}>
                            <div style={{ fontSize: "9px", fontWeight: "800", color: "#a78bfa", letterSpacing: "0.1em", marginBottom: "8px" }}>
                              {group.category}
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                              {group.items.map((ins, i) => (
                                <InsightCard
                                  key={i} insight={ins} index={i} prefersReduced={!!prefersReduced}
                                  activeSource={activeSource} onSourceClick={handleSourceClick}
                                />
                              ))}
                            </div>
                          </div>
                        ))}
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
  query: string; setQuery: (v: string) => void; onSubmit: (q: string) => void;
  error: string | null; prefersReduced: boolean; inputRef: React.RefObject<HTMLInputElement>;
}) {
  useEffect(() => { inputRef.current?.focus(); }, [inputRef]);

  return (
    <motion.div
      initial={{ opacity: 0, y: prefersReduced ? 0 : 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: prefersReduced ? 0 : -24 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px" }}
    >
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

      <div style={{ width: "100%", maxWidth: "620px", marginBottom: "20px" }}>
        <div style={{ display: "flex", background: "rgba(15,23,42,0.95)", border: "1px solid rgba(124,58,237,0.45)", borderRadius: "14px", padding: "4px 4px 4px 18px", boxShadow: "0 0 40px rgba(124,58,237,0.12)" }}>
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

      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", justifyContent: "center", maxWidth: "620px" }}>
        {EXAMPLES.map((ex) => (
          <ExampleTile key={ex.text} example={ex} onClick={() => onSubmit(ex.text)} prefersReduced={prefersReduced} />
        ))}
      </div>

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          style={{ marginTop: "16px", color: "#f87171", fontSize: "12px", background: "rgba(239,68,68,0.1)", padding: "8px 14px", borderRadius: "8px", border: "1px solid rgba(239,68,68,0.2)", maxWidth: "500px", textAlign: "center" }}>
          {error}
          <div style={{ marginTop: "8px" }}>
            <a href="/demo" style={{ color: "#a78bfa", fontSize: "11px" }}>Try demo mode →</a>
          </div>
        </motion.div>
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
