"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";

interface ConfidenceBreakdown {
  score: number;
  components: {
    simulation_consistency: number;
    effect_magnitude: number;
    persistence: number;
  };
  evidence_adjusted: boolean;
  evidence_sources: string[];
  primary_driver: string;
  plain_english: string;
}

interface Hop {
  from_label: string;
  to_label: string;
  relationship: string;
  latency_hours: number;
  confidence: number;
  cci_score: number;
  is_butterfly_effect: boolean;
  confidence_breakdown?: ConfidenceBreakdown;
}

interface Props {
  hop: Hop;
  hopNumber: number;
  prefersReduced: boolean;
  onHopClick?: (hopNumber: number) => void;
}

const DOMAIN_COLORS: Record<string, string> = {
  Energy: "#f59e0b",
  Finance: "#60a5fa",
  Geopolitics: "#ef4444",
  Economy: "#a78bfa",
  Technology: "#8b5cf6",
  Health: "#34d399",
  "Supply Chain": "#fb923c",
  Policy: "#94a3b8",
  Labor: "#e2e8f0",
  Climate: "#22d3ee",
  Infrastructure: "#f97316",
  Humanitarian: "#f43f5e",
};

function getConfidenceBadgeColor(score: number): string {
  if (score >= 0.7) return "#34d399";
  if (score >= 0.5) return "#60a5fa";
  return "#fbbf24";
}

function formatTime(hours: number): string {
  if (hours < 1) return "< 1 hour";
  if (hours < 24) return `${Math.round(hours)} hours`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} day${days > 1 ? "s" : ""}`;
  const weeks = Math.round(days / 7);
  if (weeks < 4) return `${weeks} week${weeks > 1 ? "s" : ""}`;
  const months = Math.round(days / 30);
  return `${months} month${months > 1 ? "s" : ""}`;
}

export default function HopCard({
  hop,
  hopNumber,
  prefersReduced,
  onHopClick,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const breakdown = hop.confidence_breakdown;
  const confidenceColor = getConfidenceBadgeColor(hop.confidence);

  const toggleExpanded = () => {
    setExpanded(!expanded);
    if (onHopClick) onHopClick(hopNumber);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: prefersReduced ? 0 : -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: hopNumber * 0.05, duration: 0.3 }}
      style={{
        background: "rgba(255,255,255,0.02)",
        border: `1px solid rgba(255,255,255,0.07)`,
        borderRadius: "10px",
        overflow: "hidden",
        transition: "all 0.2s",
        cursor: "pointer",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(124,58,237,0.3)";
        e.currentTarget.style.background = "rgba(124,58,237,0.03)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)";
        e.currentTarget.style.background = "rgba(255,255,255,0.02)";
      }}
    >
      {/* Main hop content */}
      <div
        style={{ padding: "12px 14px", cursor: "pointer" }}
        onClick={toggleExpanded}
      >
        {/* Header with hop number and timing */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "8px",
          }}
        >
          <span
            style={{
              fontSize: "10px",
              fontWeight: "800",
              color: "#0a0e1a",
              background: "#7c3aed",
              padding: "2px 7px",
              borderRadius: "4px",
              minWidth: "20px",
              textAlign: "center",
            }}
          >
            {hopNumber}
          </span>
          <span style={{ fontSize: "9px", color: "#64748b" }}>
            T+{formatTime(hop.latency_hours)}
          </span>
          <div style={{ flex: 1 }} />
          <span
            style={{
              fontSize: "9px",
              color: confidenceColor,
              fontWeight: "600",
            }}
          >
            {(hop.confidence * 100).toFixed(0)}%
          </span>
          <motion.div
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown size={14} color={confidenceColor} />
          </motion.div>
        </div>

        {/* Main causal flow */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
          <p
            style={{
              fontSize: "11px",
              color: "#cbd5e1",
              margin: 0,
              maxWidth: "45%",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {hop.from_label}
          </p>
          <span style={{ fontSize: "9px", color: "#475569" }}>→</span>
          <p
            style={{
              fontSize: "11px",
              color: "#cbd5e1",
              margin: 0,
              maxWidth: "45%",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {hop.to_label}
          </p>
        </div>

        {/* Relationship description */}
        <p
          style={{
            fontSize: "10px",
            color: "#64748b",
            margin: 0,
            lineHeight: 1.4,
            textTransform: "capitalize",
          }}
        >
          {hop.relationship.replace(/_/g, " ").toLowerCase()}
        </p>

        {/* Butterfly effect badge */}
        {hop.is_butterfly_effect && (
          <span
            style={{
              display: "inline-block",
              fontSize: "8px",
              color: "#ef4444",
              background: "#7f1d1d",
              padding: "2px 6px",
              borderRadius: "3px",
              marginTop: "6px",
              fontWeight: "600",
            }}
          >
            🦋 Butterfly Effect
          </span>
        )}
      </div>

      {/* Expandable confidence breakdown */}
      <AnimatePresence>
        {expanded && breakdown && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              borderTop: "1px solid rgba(255,255,255,0.04)",
              background: "rgba(0,0,0,0.2)",
            }}
          >
            <div style={{ padding: "12px 14px" }}>
              {/* Plain English explanation */}
              <p
                style={{
                  fontSize: "10px",
                  color: "#cbd5e1",
                  margin: "0 0 10px 0",
                  lineHeight: 1.5,
                  fontStyle: "italic",
                }}
              >
                "{breakdown.plain_english}"
              </p>

              {/* Component bars */}
              <div style={{ marginBottom: "10px" }}>
                <p
                  style={{
                    fontSize: "9px",
                    color: "#94a3b8",
                    margin: "0 0 6px 0",
                    fontWeight: "600",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Breakdown
                </p>
                {Object.entries(breakdown.components).map(([key, value]) => (
                  <div key={key} style={{ marginBottom: "6px" }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "2px",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "8px",
                          color: "#64748b",
                          textTransform: "capitalize",
                        }}
                      >
                        {key.replace(/_/g, " ")}
                      </span>
                      <span style={{ fontSize: "8px", color: "#94a3b8", fontWeight: "600" }}>
                        {(value * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div
                      style={{
                        height: "4px",
                        background: "rgba(255,255,255,0.05)",
                        borderRadius: "2px",
                        overflow: "hidden",
                      }}
                    >
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${value * 100}%` }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        style={{
                          height: "100%",
                          background:
                            key === breakdown.primary_driver
                              ? "#7c3aed"
                              : "rgba(124,58,237,0.5)",
                          borderRadius: "2px",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Evidence sources */}
              {breakdown.evidence_sources.length > 0 && (
                <div style={{ marginBottom: "8px" }}>
                  <p
                    style={{
                      fontSize: "9px",
                      color: "#94a3b8",
                      margin: "0 0 4px 0",
                      fontWeight: "600",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    Evidence
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                    {breakdown.evidence_sources.map((source) => (
                      <span
                        key={source}
                        style={{
                          fontSize: "8px",
                          background: "rgba(52,211,153,0.15)",
                          border: "1px solid rgba(52,211,153,0.3)",
                          color: "#34d399",
                          padding: "2px 6px",
                          borderRadius: "3px",
                          textTransform: "uppercase",
                          fontWeight: "600",
                        }}
                      >
                        {source}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Primary driver callout */}
              <div
                style={{
                  fontSize: "8px",
                  color: "#64748b",
                  background: "rgba(124,58,237,0.08)",
                  border: "1px solid rgba(124,58,237,0.2)",
                  padding: "6px 8px",
                  borderRadius: "4px",
                  marginTop: "8px",
                }}
              >
                <span style={{ fontWeight: "600", color: "#cbd5e1" }}>Primary factor:</span>{" "}
                {breakdown.primary_driver.replace(/_/g, " ")}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
