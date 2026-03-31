"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2 } from "lucide-react";

const STAGE_LABELS: Record<string, string> = {
  parsing:    "Parsing event context",
  fetching:   "Fetching live data sources",
  extracting: "Extracting causal relations",
  simulating: "Running agent simulation",
  done:       "Analysis complete",
};

const STAGE_DESCRIPTIONS: Record<string, string> = {
  parsing:    "NLP entity extraction + temporal anchoring",
  fetching:   "FRED · GDELT · EDGAR · News APIs",
  extracting: "Building causal DAG with confidence scores",
  simulating: "Multi-agent ABM — 83 agents · 168 steps",
  done:       "Causal chain ready",
};

interface Props {
  stage: number;
  stages: readonly string[];
  liveStats: { nodes: number; agents: number; steps: number };
  query: string;
  prefersReduced: boolean;
  currentMessage?: string;
}

export default function AnalysisStream({ stage, stages, liveStats, query, prefersReduced, currentMessage }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px", gap: "32px" }}
    >
      <motion.div
        animate={prefersReduced ? {} : { rotate: [0, 5, -5, 0], scale: [1, 1.05, 1] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
      >
        <svg width="56" height="56" viewBox="0 0 48 48" fill="none">
          <motion.path d="M24 24 C18 16, 6 12, 4 20 C2 28, 12 32, 24 24Z" fill="rgba(124,58,237,0.8)"
            animate={prefersReduced ? {} : { opacity: [0.6, 1, 0.6] }} transition={{ duration: 1.5, repeat: Infinity }} />
          <motion.path d="M24 24 C30 16, 42 12, 44 20 C46 28, 36 32, 24 24Z" fill="rgba(124,58,237,0.8)"
            animate={prefersReduced ? {} : { opacity: [1, 0.6, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
          <path d="M24 24 C18 30, 8 34, 10 40 C12 46, 22 42, 24 24Z" fill="rgba(124,58,237,0.4)" />
          <path d="M24 24 C30 30, 40 34, 38 40 C36 46, 26 42, 24 24Z" fill="rgba(124,58,237,0.4)" />
          <line x1="24" y1="10" x2="24" y2="38" stroke="rgba(167,139,250,0.6)" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </motion.div>

      <div style={{ textAlign: "center", maxWidth: "500px" }}>
        <p style={{ fontSize: "11px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "6px" }}>Tracing causal chain for</p>
        <p style={{ fontSize: "16px", color: "#e2e8f0", fontWeight: "600", lineHeight: 1.4 }}>{query}</p>
        {currentMessage && (
          <p style={{ fontSize: "11px", color: "#475569", marginTop: "6px", fontFamily: "monospace" }}>{currentMessage}</p>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%", maxWidth: "400px" }}>
        {stages.filter(s => s !== "done").map((s, i) => {
          const isDone = stage > i;
          const isActive = stage === i;
          return (
            <motion.div key={s}
              initial={{ opacity: 0, x: -10 }} animate={{ opacity: isDone || isActive ? 1 : 0.3, x: 0 }}
              transition={{ delay: i * 0.08 }}
              style={{ display: "flex", alignItems: "center", gap: "12px", padding: "10px 14px", borderRadius: "10px",
                background: isActive ? "rgba(124,58,237,0.1)" : isDone ? "rgba(52,211,153,0.05)" : "rgba(255,255,255,0.02)",
                border: `1px solid ${isActive ? "rgba(124,58,237,0.3)" : isDone ? "rgba(52,211,153,0.15)" : "rgba(255,255,255,0.04)"}`,
                transition: "all 0.3s" }}
            >
              <div style={{ width: "20px", height: "20px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                background: isDone ? "rgba(52,211,153,0.2)" : isActive ? "rgba(124,58,237,0.2)" : "rgba(255,255,255,0.05)" }}>
                {isDone ? (
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 400 }}>
                    <Check size={11} color="#34d399" />
                  </motion.div>
                ) : isActive ? (
                  <motion.div animate={prefersReduced ? {} : { rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
                    <Loader2 size={11} color="#7c3aed" />
                  </motion.div>
                ) : (
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "rgba(255,255,255,0.15)" }} />
                )}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "12px", fontWeight: "600", color: isDone ? "#34d399" : isActive ? "#e2e8f0" : "#475569" }}>
                  {STAGE_LABELS[s]}
                </div>
                <div style={{ fontSize: "10px", color: "#475569", marginTop: "1px" }}>{STAGE_DESCRIPTIONS[s]}</div>
              </div>
            </motion.div>
          );
        })}
      </div>

      <AnimatePresence>
        {liveStats.nodes > 0 && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            style={{ display: "flex", gap: "24px", padding: "12px 24px", background: "rgba(15,23,42,0.8)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "12px" }}>
            {([
              { label: "nodes",  value: liveStats.nodes,  color: "#7c3aed" },
              { label: "agents", value: liveStats.agents, color: "#34d399" },
              { label: "steps",  value: liveStats.steps,  color: "#60a5fa" },
            ] as const).map(({ label, value, color }) => (
              <div key={label} style={{ textAlign: "center" }}>
                <div style={{ fontSize: "20px", fontWeight: "800", fontFamily: "monospace", color }}>{value}</div>
                <div style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
