"use client";

import { motion } from "framer-motion";
import { ExternalLink, ShieldCheck, Clock, Database } from "lucide-react";

// ── Static FRED evidence for demo/known nodes ─────────────────────────────────

interface StaticEntry {
  label: string; type: string; description: string;
  causalStrength?: number; latencyHours?: number;
  confidenceInterval?: [number, number];
  downstream: string[]; upstream: string[]; sources: string[];
  refutationPassed?: boolean;
}

const STATIC_EVIDENCE: Record<string, StaticEntry> = {
  FEDFUNDS: {
    label: "Fed Funds Rate", type: "Metric",
    description: "Benchmark overnight lending rate set by the FOMC. Directly controlled by Federal Reserve policy decisions.",
    causalStrength: 0.95, latencyHours: 0, confidenceInterval: [0.90, 1.0],
    downstream: ["MORTGAGE30US", "T10Y2Y"], upstream: ["fed_2022_hike"],
    sources: ["FRED FEDFUNDS", "FOMC Statement Jun 2022"], refutationPassed: true,
  },
  MORTGAGE30US: {
    label: "30-Year Mortgage Rate", type: "Metric",
    description: "Average 30-year fixed mortgage rate. Reprices via MBS market within 48h of Fed Funds changes.",
    causalStrength: 0.87, latencyHours: 48, confidenceInterval: [0.74, 1.0],
    downstream: ["HOUST"], upstream: ["FEDFUNDS"],
    sources: ["FRED MORTGAGE30US", "Freddie Mac PMMS"], refutationPassed: true,
  },
  HOUST: {
    label: "Housing Starts", type: "Metric",
    description: "Monthly new residential construction starts. Lags mortgage rate changes by ~168h due to permit processing.",
    causalStrength: 0.72, latencyHours: 168, confidenceInterval: [0.61, 0.83],
    downstream: ["UNRATE"], upstream: ["MORTGAGE30US"],
    sources: ["Census Bureau HOUST", "NAHB Housing Market Index"], refutationPassed: true,
  },
  UNRATE: {
    label: "Unemployment Rate", type: "Metric",
    description: "BLS U-3 unemployment rate. Construction sector job losses visible in JOLTS data ~720h post-hike.",
    causalStrength: 0.51, latencyHours: 720, confidenceInterval: [0.43, 0.59],
    downstream: [], upstream: ["HOUST"],
    sources: ["BLS JOLTS", "FRED UNRATE"], refutationPassed: false,
  },
};

const TYPE_COLORS: Record<string, string> = {
  Event: "#7c3aed", Metric: "#10b981", Entity: "#3b82f6", Policy: "#a78bfa",
};

// ── Live evidence item (from backend) ────────────────────────────────────────

interface LiveEvidenceItem {
  node_id: string;
  source: string;
  title: string;
  content: string;
  url?: string;
  relevance: number;
}

interface Props {
  nodeId: string;
  liveEvidence?: LiveEvidenceItem[];
  fredData?: Record<string, { value: number; delta: number; date: string }>;
}

export default function EvidencePanelNew({ nodeId, liveEvidence, fredData }: Props) {
  // Check static evidence first (FRED demo nodes)
  const staticData = STATIC_EVIDENCE[nodeId];

  // Filter live evidence for this node
  const nodeEvidence = (liveEvidence || []).filter(e => e.node_id === nodeId);

  // FRED data for this node
  const fredSeries = fredData?.[nodeId];

  // Nothing at all — empty states should be invisible, not announced.
  if (!staticData && nodeEvidence.length === 0 && !fredSeries) {
    return <div style={{ flex: 1 }} />;
  }

  const typeColor = staticData ? (TYPE_COLORS[staticData.type] ?? "#7c3aed") : "#7c3aed";

  return (
    <div style={{ flex: 1, overflowY: "auto" }}>
      {/* Header */}
      <div style={{ padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", background: "linear-gradient(180deg, rgba(124,58,237,0.06) 0%, transparent 100%)" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px", marginBottom: "6px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#e2e8f0", margin: 0, lineHeight: 1.3 }}>
            {staticData?.label || nodeId}
          </h3>
          {staticData && (
            <span style={{ fontSize: "9px", padding: "2px 7px", borderRadius: "4px", background: `${typeColor}20`, border: `1px solid ${typeColor}40`, color: typeColor, fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", flexShrink: 0 }}>
              {staticData.type}
            </span>
          )}
        </div>
        {staticData?.description && (
          <p style={{ fontSize: "11px", color: "#64748b", margin: 0, lineHeight: 1.5 }}>{staticData.description}</p>
        )}
      </div>

      <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: "14px" }}>

        {/* FRED live value */}
        {fredSeries && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            style={{ background: "rgba(52,211,153,0.05)", border: "1px solid rgba(52,211,153,0.15)", borderRadius: "10px", padding: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em" }}>FRED Live Value</span>
              <span style={{ fontSize: "9px", color: "#475569", fontFamily: "monospace" }}>{fredSeries.date}</span>
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
              <span style={{ fontSize: "22px", fontWeight: "800", fontFamily: "monospace", color: "#ecfdf5" }}>
                {fredSeries.value.toFixed(2)}
              </span>
              <span style={{ fontSize: "12px", fontFamily: "monospace", color: fredSeries.delta >= 0 ? "#34d399" : "#f87171", fontWeight: "600" }}>
                {fredSeries.delta >= 0 ? "↑" : "↓"} {Math.abs(fredSeries.delta).toFixed(2)}
              </span>
            </div>
          </motion.div>
        )}

        {/* Static causal strength */}
        {staticData?.causalStrength !== undefined && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "10px", padding: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em" }}>Causal Strength</span>
              <span style={{ fontSize: "16px", fontWeight: "800", fontFamily: "monospace", color: staticData.causalStrength >= 0.8 ? "#34d399" : staticData.causalStrength >= 0.6 ? "#60a5fa" : "#fbbf24" }}>
                {Math.round(staticData.causalStrength * 100)}%
              </span>
            </div>
            <div style={{ height: "4px", background: "rgba(255,255,255,0.06)", borderRadius: "2px", overflow: "hidden" }}>
              <motion.div initial={{ width: 0 }} animate={{ width: `${staticData.causalStrength * 100}%` }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                style={{ height: "100%", background: "linear-gradient(90deg, #7c3aed, #34d399)", borderRadius: "2px" }} />
            </div>
            {staticData.confidenceInterval && (
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px" }}>
                <span style={{ fontSize: "9px", color: "#475569", fontFamily: "monospace" }}>
                  95% CI: [{staticData.confidenceInterval[0].toFixed(2)}, {staticData.confidenceInterval[1].toFixed(2)}]
                </span>
                {staticData.latencyHours !== undefined && (
                  <span style={{ fontSize: "9px", color: "#475569", display: "flex", alignItems: "center", gap: "3px" }}>
                    <Clock size={9} /> {staticData.latencyHours}h latency
                  </span>
                )}
              </div>
            )}
          </motion.div>
        )}

        {/* Live evidence from fetched sources */}
        {nodeEvidence.length > 0 && (
          <div>
            <p style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "8px", display: "flex", alignItems: "center", gap: "4px" }}>
              <Database size={9} /> Live Evidence ({nodeEvidence.length})
            </p>
            {nodeEvidence.map((ev, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                style={{ marginBottom: "8px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "10px 12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                  <span style={{ fontSize: "8px", color: "#475569", background: "rgba(255,255,255,0.05)", padding: "1px 5px", borderRadius: "3px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    {ev.source}
                  </span>
                  <span style={{ fontSize: "8px", color: "#334155", fontFamily: "monospace" }}>
                    {Math.round(ev.relevance * 100)}% match
                  </span>
                </div>
                <p style={{ fontSize: "11px", color: "#94a3b8", margin: "0 0 4px 0", lineHeight: 1.4, fontWeight: "600" }}>
                  {ev.title}
                </p>
                {ev.content && (
                  <p style={{ fontSize: "10px", color: "#475569", margin: "0 0 6px 0", lineHeight: 1.5 }}>
                    {ev.content.slice(0, 180)}{ev.content.length > 180 ? "..." : ""}
                  </p>
                )}
                {ev.url && (
                  <a href={ev.url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: "9px", color: "#7c3aed", display: "flex", alignItems: "center", gap: "3px", textDecoration: "none" }}>
                    <ExternalLink size={9} /> View source
                  </a>
                )}
              </motion.div>
            ))}
          </div>
        )}

        {/* Static downstream/upstream */}
        {staticData?.downstream && staticData.downstream.length > 0 && (
          <div>
            <p style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "6px" }}>Downstream Effects</p>
            {staticData.downstream.map((d) => (
              <div key={d} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "7px 10px", marginBottom: "4px", background: "rgba(52,211,153,0.05)", border: "1px solid rgba(52,211,153,0.12)", borderRadius: "8px" }}>
                <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#34d399", flexShrink: 0 }} />
                <span style={{ fontSize: "11px", color: "#94a3b8", fontFamily: "monospace" }}>{d}</span>
              </div>
            ))}
          </div>
        )}

        {staticData?.upstream && staticData.upstream.length > 0 && (
          <div>
            <p style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "6px" }}>Caused By</p>
            {staticData.upstream.map((u) => (
              <div key={u} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "7px 10px", marginBottom: "4px", background: "rgba(124,58,237,0.05)", border: "1px solid rgba(124,58,237,0.12)", borderRadius: "8px" }}>
                <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#7c3aed", flexShrink: 0 }} />
                <span style={{ fontSize: "11px", color: "#94a3b8", fontFamily: "monospace" }}>{u}</span>
              </div>
            ))}
          </div>
        )}

        {/* Static sources */}
        {staticData?.sources && staticData.sources.length > 0 && (
          <div>
            <p style={{ fontSize: "9px", color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "6px" }}>Evidence Sources</p>
            {staticData.sources.map((src) => (
              <div key={src} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 10px", marginBottom: "4px", background: "rgba(124,58,237,0.05)", border: "1px solid rgba(124,58,237,0.1)", borderRadius: "6px" }}>
                <ExternalLink size={10} color="#7c3aed" />
                <span style={{ fontSize: "10px", color: "#7c3aed" }}>{src}</span>
              </div>
            ))}
          </div>
        )}

        {staticData?.refutationPassed !== undefined && (
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "10px", color: staticData.refutationPassed ? "#34d399" : "#f87171" }}>
            <ShieldCheck size={12} />
            {staticData.refutationPassed ? "Refutation tests passed" : "Refutation tests failed — treat with caution"}
          </div>
        )}
      </div>
    </div>
  );
}
