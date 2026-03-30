"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Share2, BookOpen } from "lucide-react";

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

const ORDER_COLORS: Record<number, { bg: string; border: string; text: string; label: string }> = {
  2: { bg: "rgba(96,165,250,0.08)",  border: "rgba(96,165,250,0.2)",  text: "#60a5fa", label: "2nd order" },
  3: { bg: "rgba(124,58,237,0.08)",  border: "rgba(124,58,237,0.2)",  text: "#a78bfa", label: "3rd order" },
  4: { bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.2)",  text: "#fbbf24", label: "4th order" },
};

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 0.8 ? "#34d399" : value >= 0.6 ? "#60a5fa" : "#fbbf24";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
      <div style={{ flex: 1, height: "3px", background: "rgba(255,255,255,0.06)", borderRadius: "2px", overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${value * 100}%`, background: color, borderRadius: "2px", transition: "width 0.6s ease" }} />
      </div>
      <span style={{ fontSize: "9px", fontFamily: "monospace", color, minWidth: "28px" }}>{Math.round(value * 100)}%</span>
    </div>
  );
}

export default function InsightCard({ insight, index, prefersReduced }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const style = ORDER_COLORS[insight.order] ?? ORDER_COLORS[3];

  const handleShare = () => {
    const text = `[${style.label} effect]\n${insight.text}\n\nWhy this matters: ${insight.why}\n\nSources: ${insight.sources.join(", ")}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: prefersReduced ? 0 : 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.35 }}
      style={{ background: style.bg, border: `1px solid ${style.border}`, borderRadius: "12px", overflow: "hidden" }}
    >
      <div style={{ padding: "12px 14px" }}>
        {/* Header row */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
          <span style={{ fontSize: "9px", fontWeight: "700", color: style.text, background: `${style.border}`, padding: "2px 7px", borderRadius: "4px", textTransform: "uppercase", letterSpacing: "0.06em", border: `1px solid ${style.border}` }}>
            {style.label}
          </span>
          <span style={{ fontSize: "9px", color: "#475569", fontFamily: "monospace" }}>hop {insight.hop}</span>
          <div style={{ flex: 1 }} />
          <button
            onClick={handleShare}
            title="Copy insight"
            style={{ background: "none", border: "none", color: copied ? "#34d399" : "#475569", cursor: "pointer", padding: "2px", display: "flex", alignItems: "center" }}
          >
            <Share2 size={11} />
          </button>
        </div>

        {/* Insight text */}
        <p style={{ fontSize: "12px", color: "#cbd5e1", lineHeight: "1.55", margin: "0 0 10px 0" }}>
          {insight.text}
        </p>

        {/* Confidence */}
        <ConfidenceBar value={insight.confidence} />

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          style={{ display: "flex", alignItems: "center", gap: "4px", background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: "10px", marginTop: "8px", padding: "0", fontFamily: "inherit" }}
        >
          <BookOpen size={10} />
          Why this matters
          <motion.span animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown size={10} />
          </motion.span>
        </button>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: "hidden" }}
          >
            <div style={{ padding: "0 14px 12px", borderTop: `1px solid ${style.border}` }}>
              <p style={{ fontSize: "11px", color: "#94a3b8", lineHeight: "1.6", margin: "10px 0 8px" }}>
                {insight.why}
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                {insight.sources.map((src) => (
                  <span key={src} style={{ fontSize: "9px", color: "#475569", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)", padding: "2px 6px", borderRadius: "4px" }}>
                    {src}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
