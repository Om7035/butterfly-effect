"use client";

import { motion } from "framer-motion";
import type { ChainModel } from "@/lib/chainData";
import { confidenceTier, formatTimeDelta } from "@/lib/chainData";
import TriggerCard from "./TriggerCard";
import HopChainCard from "./HopChainCard";

interface Props {
  chain: ChainModel;
  stats: { nodes: number; agents: number; steps: number };
  prefersReduced: boolean;
  pulsingHopId: string | null;
  registerHopRef: (hopId: string, el: HTMLDivElement | null) => void;
}

export default function ChainView({ chain, stats, prefersReduced, pulsingHopId, registerHopRef }: Props) {
  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "24px 24px 200px", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ width: "100%", maxWidth: "680px" }}>
        {chain.trigger && (
          <TriggerCard trigger={chain.trigger} stats={stats} prefersReduced={prefersReduced} />
        )}

        {chain.hops.map((hop, i) => {
          const tier = confidenceTier(hop.confidence);
          return (
            <div key={hop.id}>
              {/* Time connector */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "10px 0" }}>
                <div style={{ width: "2px", height: "16px", background: tier.color, opacity: 0.5 }} />
                <span
                  style={{
                    fontSize: "10px", fontWeight: "700", color: tier.color,
                    background: "rgba(10,14,26,0.95)", border: `1px solid ${tier.color}44`,
                    borderRadius: "20px", padding: "3px 11px", letterSpacing: "0.03em",
                  }}
                >
                  {formatTimeDelta(hop.latencyHours)}
                </span>
                <div style={{ width: "2px", height: "16px", background: tier.color, opacity: 0.5 }} />
              </div>

              <HopChainCard
                ref={(el) => registerHopRef(hop.id, el)}
                hop={hop}
                index={i}
                prefersReduced={prefersReduced}
                pulsing={pulsingHopId === hop.id}
              />
            </div>
          );
        })}

        {chain.hops.length === 0 && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ fontSize: "12px", color: "#475569", textAlign: "center", marginTop: "32px" }}
          >
            No downstream effects were traced for this event.
          </motion.p>
        )}
      </div>
    </div>
  );
}
