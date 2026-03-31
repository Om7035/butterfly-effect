"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Share2 } from "lucide-react";

interface Insight {
  order: number;
  hop: number;
  text: string;
  why: string;
  confidence: number;
  sources: string[];
}

interface Props {
  insight: Insight;
  index: number;
  prefersReduced: boolean;
}

// Parse the structured STEP:n|WHAT:...|WHY:...|DOMAIN:...|TIMING:...|CONFIDENCE:... format
function parseStructuredInsight(text: string): {
  isStep: boolean; isInsight: boolean;
  step?: number; what?: string; why?: string; domain?: string; timing?: string; confidence?: string;
  insightText?: string;
} {
  if (text.startsWith("STEP:")) {
    const parts: Record<string, string> = {};
    text.split("|").forEach(p => {
      const idx = p.indexOf(":");
      if (idx > 0) parts[p.slice(0, idx)] = p.slice(idx + 1);
    });
    return {
      isStep: true, isInsight: false,
      step: parseInt(parts.STEP || "1"),
      what: parts.WHAT || "",
      why: parts.WHY || "",
      domain: parts.DOMAIN || "",
      timing: parts.TIMING || "",
      confidence: parts.CONFIDENCE || "Medium",
    };
  }
  if (text.startsWith("INSIGHT:")) {
    return { isStep: false, isInsight: true, insightText: text.slice(8) };
  }
  // Legacy format fallback
  return { isStep: false, isInsight: false };
}

const CONFIDENCE_COLORS: Record<string, string> = {
  High: "#34d399",
  Medium: "#60a5fa",
  Low: "#fbbf24",
};

const DOMAIN_COLORS: Record<string, string> = {
  Energy: "#f59e0b", Finance: "#60a5fa", Geopolitics: "#ef4444",
  Economy: "#a78bfa", Technology: "#8b5cf6", Health: "#34d399",
  "Supply Chain": "#fb923c", Policy: "#94a3b8", Labor: "#e2e8f0",
  Climate: "#22d3ee", Infrastructure: "#f97316", Humanitarian: "#f43f5e",
};

export default function InsightCard({ insight, index, prefersReduced }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const parsed = parseStructuredInsight(insight.text);

  const handleShare = () => {
    navigator.clipboard.writeText(insight.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Structured step card ──────────────────────────────────────────────────
  if (parsed.isStep) {
    const confColor = CONFIDENCE_COLORS[parsed.confidence || "Medium"] || "#60a5fa";
    const domainColor = DOMAIN_COLORS[parsed.domain || "Economy"] || "#a78bfa";

    return (
      <motion.div
        initial={{ opacity: 0, y: prefersReduced ? 0 : 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.08, duration: 0.3 }}
        style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "10px", overflow: "hidden" }}
      >
        <div style={{ padding: "12px 14px" }}>
          {/* Step header */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
            <span style={{ fontSize: "10px", fontWeight: "800", color: "#0a0e1a", background: "#7c3aed", padding: "2px 7px", borderRadius: "4px", minWidth: "20px", textAlign: "center" }}>
              {parsed.step}
            </span>
            <span style={{ fontSize: "9px", padding: "2px 7px", borderRadius: "4px", background: `${domainColor}18`, border: `1px solid ${domainColor}40`, color: domainColor, fontWeight: "600" }}>
              {parsed.domain}
            </span>
            <div style={{ flex: 1 }} />
            <span style={{ fontSize: "9px", color: confColor, fontWeight: "600" }}>{parsed.confidence}</span>
            <button onClick={handleShare} style={{ background: "none", border: "none", color: copied ? "#34d399" : "#475569", cursor: "pointer", padding: "2px", display: "flex" }}>
              <Share2 size={10} />
            </button>
          </div>

          {/* What happened */}
          <p style={{ fontSize: "13px", fontWeight: "600", color: "#e2e8f0", margin: "0 0 6px 0", lineHeight: 1.4 }}>
            {parsed.what}
          </p>

          {/* Why */}
          <p style={{ fontSize: "11px", color: "#64748b", margin: "0 0 8px 0", lineHeight: 1.5 }}>
            {parsed.why}
          </p>

          {/* Timing */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "9px", color: "#475569", background: "rgba(255,255,255,0.04)", padding: "2px 7px", borderRadius: "4px", border: "1px solid rgba(255,255,255,0.06)" }}>
              {parsed.timing}
            </span>
          </div>
        </div>
      </motion.div>
    );
  }

  // ── Key insight card ──────────────────────────────────────────────────────
  if (parsed.isInsight) {
    return (
      <motion.div
        initial={{ opacity: 0, y: prefersReduced ? 0 : 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.08, duration: 0.3 }}
        style={{ background: "rgba(124,58,237,0.08)", border: "1px solid rgba(124,58,237,0.25)", borderRadius: "10px", padding: "12px 14px" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <span style={{ fontSize: "9px", fontWeight: "700", color: "#a78bfa", textTransform: "uppercase", letterSpacing: "0.08em" }}>Key Insight</span>
        </div>
        <p style={{ fontSize: "12px", color: "#cbd5e1", lineHeight: "1.6", margin: 0 }}>
          {parsed.insightText}
        </p>
      </motion.div>
    );
  }

  // ── Legacy format fallback ────────────────────────────────────────────────
  const ORDER_COLORS: Record<number, { bg: string; border: string; text: string; label: string }> = {
    2: { bg: "rgba(96,165,250,0.08)", border: "rgba(96,165,250,0.2)", text: "#60a5fa", label: "2nd order" },
    3: { bg: "rgba(124,58,237,0.08)", border: "rgba(124,58,237,0.2)", text: "#a78bfa", label: "3rd order" },
    4: { bg: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.2)", text: "#fbbf24", label: "4th order" },
  };
  const style = ORDER_COLORS[insight.order] ?? ORDER_COLORS[3];

  return (
    <motion.div
      initial={{ opacity: 0, y: prefersReduced ? 0 : 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.35 }}
      style={{ background: style.bg, border: `1px solid ${style.border}`, borderRadius: "12px", overflow: "hidden" }}
    >
      <div style={{ padding: "12px 14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
          <span style={{ fontSize: "9px", fontWeight: "700", color: style.text, background: style.border, padding: "2px 7px", borderRadius: "4px", textTransform: "uppercase", letterSpacing: "0.06em", border: `1px solid ${style.border}` }}>
            {style.label}
          </span>
          <div style={{ flex: 1 }} />
          <button onClick={handleShare} style={{ background: "none", border: "none", color: copied ? "#34d399" : "#475569", cursor: "pointer", padding: "2px", display: "flex" }}>
            <Share2 size={11} />
          </button>
        </div>
        <p style={{ fontSize: "12px", color: "#cbd5e1", lineHeight: "1.55", margin: "0 0 8px 0" }}>{insight.text}</p>
        {insight.why && (
          <>
            <button onClick={() => setExpanded(!expanded)} style={{ display: "flex", alignItems: "center", gap: "4px", background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: "10px", padding: "0", fontFamily: "inherit" }}>
              Why this matters
              <motion.span animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
                <ChevronDown size={10} />
              </motion.span>
            </button>
            <AnimatePresence>
              {expanded && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} style={{ overflow: "hidden" }}>
                  <p style={{ fontSize: "11px", color: "#94a3b8", lineHeight: "1.6", margin: "8px 0 0" }}>{insight.why}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>
    </motion.div>
  );
}