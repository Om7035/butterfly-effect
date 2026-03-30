"use client";

import { useState, useRef, useCallback } from "react";
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

// ── Example prompts ───────────────────────────────────────────────────────────

const EXAMPLES = [
  "War escalates in the Middle East",
  "Fed raises rates 100bps",
  "ChatGPT launches to public",
  "Category 5 hurricane hits Miami",
  "China invades Taiwan",
  "Pandemic declared — novel pathogen",
];

const STAGES = ["parsing", "fetching", "causal_modeling", "insights", "complete"];

// ── Types ─────────────────────────────────────────────────────────────────────

interface ProgressEvent {
  run_id?: string;
  stage: string;
  percent: number;
  message: string;
  partial?: Record<string, unknown>;
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Home() {
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<"idle" | "streaming" | "done">("idle");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [graphData, setGraphData] = useState<{ nodes: unknown[]; edges: unknown[] } | null>(null);
  const [insights, setInsights] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setQuery(q);
    setPhase("streaming");
    setEvents([]);
    setGraphData(null);
    setInsights([]);
    setError(null);

    try {
      await api.analyze.stream(q, (ev) => {
        const e = ev as ProgressEvent;
        setEvents((prev) => {
          const filtered = prev.filter((p) => p.stage !== e.stage);
          return [...filtered, e];
        });

        if (e.stage === "complete" && e.partial) {
          const result = e.partial as Record<string, unknown>;
          const chain = result.causal_chain as { nodes: unknown[]; edges: unknown[] } | undefined;
          if (chain) {
            const rfData = transformToReactFlowData({
              nodes: (chain.nodes as any[]).map((n: any) => ({
                id: n.id,
                type: (n.type || "entity").toLowerCase() as any,
                title: n.label,
                name: n.label,
                description: n.description,
                confidence: n.confidence,
              })),
              edges: (chain.edges as any[]).map((e: any) => ({
                id: e.id,
                source: e.source,
                target: e.target,
                type: e.type === "causal" ? "causal" : "influence",
                strength: e.strength,
                confidence: e.confidence,
                latency: e.latency_hours,
              })),
            });
            setGraphData(rfData as any);
          }
          if (Array.isArray(result.insights)) {
            setInsights(result.insights as string[]);
          }
          setPhase("done");
        }
      });
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
        let newNodes = [...(prev.nodes as any[])];
        switch (layout) {
          case "hierarchical": newNodes = applyHierarchicalLayout(newNodes, prev.edges as any[]); break;
          case "radial":       newNodes = applyRadialLayout(newNodes); break;
          case "grid":         newNodes = applyGridLayout(newNodes); break;
        }
        return { ...prev, nodes: newNodes };
      });
    },
    [graphData]
  );

  const currentStage = events[events.length - 1]?.stage ?? "";
  const currentPercent = events[events.length - 1]?.percent ?? 0;

  return (
    <div style={{
      width: "100vw",
      height: "100vh",
      background: "#070b14",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      fontFamily: "system-ui, -apple-system, sans-serif",
      color: "#e2e8f0",
    }}>

      {/* ── Top bar (always visible) ── */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 20px",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        background: "rgba(15,23,42,0.8)",
        backdropFilter: "blur(8px)",
        flexShrink: 0,
        zIndex: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "18px" }}>🦋</span>
          <span style={{ fontSize: "13px", fontWeight: "700", letterSpacing: "0.02em" }}>
            butterfly-effect
          </span>
          <span style={{
            fontSize: "9px", color: "#475569",
            borderLeft: "1px solid rgba(255,255,255,0.08)",
            paddingLeft: "10px",
            textTransform: "uppercase", letterSpacing: "0.1em",
          }}>
            universal causal engine
          </span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <a href="/graph-demo" style={{
            fontSize: "11px", color: "#475569", textDecoration: "none",
            border: "1px solid rgba(255,255,255,0.07)",
            padding: "5px 10px", borderRadius: "6px",
          }}>
            Graph demo →
          </a>
        </div>
      </div>

      {/* ── Main content ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* ── IDLE: centered search ── */}
        <AnimatePresence>
          {phase === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "40px 20px",
              }}
            >
              {/* Icon */}
              <div style={{ fontSize: "56px", marginBottom: "24px", opacity: 0.6 }}>🦋</div>

              {/* Headline */}
              <h1 style={{
                fontSize: "28px", fontWeight: "700",
                textAlign: "center", marginBottom: "8px",
                background: "linear-gradient(135deg, #e2e8f0 0%, #7c3aed 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}>
                Type anything. See the chain nobody else sees.
              </h1>
              <p style={{ fontSize: "14px", color: "#475569", marginBottom: "32px", textAlign: "center" }}>
                Any event. Any domain. Real causal chains with evidence.
              