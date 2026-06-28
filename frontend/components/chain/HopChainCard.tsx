"use client";

import { useState, forwardRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import type { ChainHop } from "@/lib/chainData";
import { confidenceTier, orderColor, orderLabel } from "@/lib/chainData";

interface Props {
  hop: ChainHop;
  index: number;
  prefersReduced: boolean;
  pulsing?: boolean;
}

const HopChainCard = forwardRef<HTMLDivElement, Props>(function HopChainCard(
  { hop, index, prefersReduced, pulsing },
  ref
) {
  const [expanded, setExpanded] = useState(false);
  const tier = confidenceTier(hop.confidence);
  const depthColor = orderColor(hop.order);
  const hasWhy = !!(hop.mechanism || hop.evidenceSources.length > 0);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: prefersReduced ? 0 : 16 }}
      animate={{
        opacity: 1,
        y: 0,
        boxShadow: pulsing
          ? `0 0 0 1px ${depthColor}88, 0 0 24px ${depthColor}55`
          : "0 0 0 1px rgba(255,255,255,0.06)",
      }}
      transition={{ delay: prefersReduced ? 0 : index * 0.06, duration: pulsing ? 0.3 : 0.4 }}
      style={{
        background: "rgba(15,23,42,0.85)",
        borderRadius: "14px",
        padding: "18px 20px",
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      {/* Header row: order badge + confidence */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px", gap: "12px" }}>
        <span
          style={{
            fontSize: "10px",
            fontWeight: "800",
            color: depthColor,
            background: `${depthColor}18`,
            border: `1px solid ${depthColor}44`,
            padding: "3px 9px",
            borderRadius: "5px",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            flexShrink: 0,
          }}
        >
          {orderLabel(hop.order)}
        </span>

        {/* Confidence: label + horizontal bar, right-aligned */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
          <span style={{ fontSize: "10px", fontWeight: "700", color: tier.color, letterSpacing: "0.04em" }}>
            {tier.label}
          </span>
          <div style={{ width: "64px", height: "4px", background: "rgba(255,255,255,0.08)", borderRadius: "2px", overflow: "hidden" }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${hop.confidence * 100}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              style={{ height: "100%", background: tier.color, borderRadius: "2px" }}
            />
          </div>
        </div>
      </div>

      {/* Headline */}
      <p style={{ fontSize: "15px", fontWeight: "700", color: "#e2e8f0", margin: "0 0 4px 0", lineHeight: 1.4 }}>
        {hop.toLabel}
      </p>

      {/* Full description — readable width, no truncation */}
      <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0, lineHeight: 1.6 }}>
        {hop.description}
      </p>

      {/* Why this matters accordion — only rendered if there's something to show */}
      {hasWhy && (
        <div style={{ marginTop: "12px" }}>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              display: "flex", alignItems: "center", gap: "5px",
              background: "none", border: "none", color: "#64748b",
              cursor: "pointer", fontSize: "11px", padding: 0, fontFamily: "inherit",
            }}
          >
            Why this matters
            <motion.span animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
              <ChevronDown size={12} />
            </motion.span>
          </button>
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                style={{ overflow: "hidden" }}
              >
                {hop.mechanism && (
                  <p style={{ fontSize: "12px", color: "#94a3b8", lineHeight: 1.6, margin: "10px 0 0" }}>
                    {hop.mechanism}
                  </p>
                )}
                {hop.evidenceSources.length > 0 && (
                  <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "5px" }}>
                    {hop.evidenceSources.map((src) => (
                      <span
                        key={src}
                        style={{
                          fontSize: "9px", color: "#94a3b8",
                          background: "rgba(255,255,255,0.05)", padding: "2px 7px",
                          borderRadius: "4px", border: "1px solid rgba(255,255,255,0.08)",
                          textTransform: "uppercase", letterSpacing: "0.04em",
                        }}
                      >
                        {src}
                      </span>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
});

export default HopChainCard;
