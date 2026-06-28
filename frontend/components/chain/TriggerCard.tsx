"use client";

import { motion } from "framer-motion";
import type { ChainTrigger } from "@/lib/chainData";

interface Props {
  trigger: ChainTrigger;
  stats: { nodes: number; agents: number; steps: number };
  prefersReduced: boolean;
}

const SEVERITY_COLOR: Record<string, string> = {
  catastrophic: "#ef4444",
  major: "#f59e0b",
  moderate: "#7c3aed",
  minor: "#3b82f6",
};

export default function TriggerCard({ trigger, stats, prefersReduced }: Props) {
  const accent = SEVERITY_COLOR[trigger.severity || "moderate"] || "#7c3aed";

  return (
    <motion.div
      initial={{ opacity: 0, y: prefersReduced ? 0 : -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      style={{
        background: `linear-gradient(135deg, ${accent}14, rgba(15,23,42,0.9))`,
        border: `1px solid ${accent}55`,
        borderRadius: "16px",
        padding: "22px 24px",
        width: "100%",
        boxSizing: "border-box",
        boxShadow: `0 0 32px ${accent}1a`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
        <span style={{ fontSize: "22px" }}>🦋</span>
        <span style={{ fontSize: "10px", fontWeight: "800", color: accent, letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Trigger Event
        </span>
      </div>
      <p style={{ fontSize: "19px", fontWeight: "800", color: "#f1f5f9", margin: "0 0 14px 0", lineHeight: 1.35 }}>
        {trigger.label}
      </p>
      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
        {trigger.domain && (
          <StatPill label={trigger.domain} color={accent} />
        )}
        <StatPill label={`${stats.nodes} nodes`} color="#475569" />
        <StatPill label={`${stats.agents} agents`} color="#475569" />
      </div>
    </motion.div>
  );
}

function StatPill({ label, color }: { label: string; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
      <div style={{ width: "5px", height: "5px", borderRadius: "50%", background: color }} />
      <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "capitalize" }}>{label}</span>
    </div>
  );
}
