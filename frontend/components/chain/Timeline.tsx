"use client";

import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { Play, Pause } from "lucide-react";
import type { ChainHop } from "@/lib/chainData";
import { confidenceTier, formatTimeDelta } from "@/lib/chainData";

const SPEEDS = [1, 2, 5] as const;
type Speed = typeof SPEEDS[number];
const BASE_REPLAY_SECONDS = 12; // full replay at 1x takes ~12s regardless of real time span

const REFERENCE_TICKS = [
  { h: 0, label: "T+0" },
  { h: 24, label: "T+24h" },
  { h: 72, label: "T+3 days" },
  { h: 168, label: "T+1 week" },
  { h: 720, label: "T+1 month" },
  { h: 4380, label: "T+6 months" },
];

interface Props {
  hops: ChainHop[];
  prefersReduced: boolean;
  onCrossMarker?: (hopId: string) => void;
  onScrubToHop?: (hopId: string) => void;
}

function logPos(hours: number, axisMax: number): number {
  return Math.log1p(Math.max(0, hours)) / Math.log1p(axisMax);
}

function posToHours(pct: number, axisMax: number): number {
  return Math.expm1(pct * Math.log1p(axisMax));
}

export default function Timeline({ hops, prefersReduced, onCrossMarker, onScrubToHop }: Props) {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>(1);
  const [currentHours, setCurrentHours] = useState(0);
  const trackRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number>(0);
  const crossedRef = useRef<Set<string>>(new Set());

  const axisMax = useMemo(() => {
    const maxHop = Math.max(24, ...hops.map((h) => h.latencyHours));
    return maxHop * 1.15;
  }, [hops]);

  const visibleTicks = REFERENCE_TICKS.filter((t) => t.h <= axisMax);

  // Decongest marker labels — hops are sorted chronologically; skip a label
  // if it would sit too close to the last one we decided to show.
  const MIN_LABEL_GAP_PCT = 9;
  const hopsWithLabelFlag = useMemo(() => {
    let lastShownPct = -Infinity;
    return hops.map((hop) => {
      const pct = logPos(hop.latencyHours, axisMax) * 100;
      const showLabel = pct - lastShownPct >= MIN_LABEL_GAP_PCT;
      if (showLabel) lastShownPct = pct;
      return { hop, pct, showLabel };
    });
  }, [hops, axisMax]);

  // Playback loop
  useEffect(() => {
    if (!playing) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }
    const durationMs = (BASE_REPLAY_SECONDS / speed) * 1000;
    startRef.current = performance.now() - logPos(currentHours, axisMax) * durationMs;

    const tick = (now: number) => {
      const elapsed = now - startRef.current;
      const pct = Math.min(1, elapsed / durationMs);
      const hours = posToHours(pct, axisMax);
      setCurrentHours(hours);

      hops.forEach((hop) => {
        if (!crossedRef.current.has(hop.id) && hours >= hop.latencyHours) {
          crossedRef.current.add(hop.id);
          onCrossMarker?.(hop.id);
        }
      });

      if (pct >= 1) {
        setPlaying(false);
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speed, axisMax]);

  const togglePlay = useCallback(() => {
    if (!playing && currentHours >= axisMax) {
      setCurrentHours(0);
      crossedRef.current = new Set();
    }
    setPlaying((p) => !p);
  }, [playing, currentHours, axisMax]);

  // Spacebar shortcut — ignore while typing in an input/textarea
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.code !== "Space") return;
      const tag = (document.activeElement?.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea") return;
      e.preventDefault();
      togglePlay();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [togglePlay]);

  const setFromClientX = useCallback((clientX: number) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const hours = posToHours(pct, axisMax);
    setCurrentHours(hours);
    setPlaying(false);
    // Scrub to nearest hop
    let nearest: ChainHop | null = null;
    let nearestDist = Infinity;
    for (const hop of hops) {
      const d = Math.abs(hop.latencyHours - hours);
      if (d < nearestDist) { nearestDist = d; nearest = hop; }
    }
    if (nearest) onScrubToHop?.(nearest.id);
  }, [axisMax, hops, onScrubToHop]);

  const playheadPct = logPos(currentHours, axisMax) * 100;

  return (
    <div style={{
      flexShrink: 0, height: "160px", borderTop: "1px solid rgba(255,255,255,0.07)",
      background: "rgba(10,14,26,0.97)", padding: "14px 24px", display: "flex",
      flexDirection: "column", gap: "10px", boxSizing: "border-box",
    }}>
      {/* Controls row */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <button
          onClick={togglePlay}
          title="Play/Pause (spacebar)"
          style={{
            background: "rgba(124,58,237,0.18)", border: "1px solid rgba(124,58,237,0.4)",
            borderRadius: "8px", color: "#a78bfa", cursor: "pointer", padding: "7px 14px",
            display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", fontWeight: "700",
            letterSpacing: "0.04em",
          }}
        >
          {playing ? <Pause size={13} /> : <Play size={13} />}
          REPLAY
        </button>

        <div style={{ flex: 1 }} />

        <div style={{ display: "flex", gap: "4px" }}>
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              style={{
                background: s === speed ? "rgba(124,58,237,0.2)" : "rgba(255,255,255,0.04)",
                border: `1px solid ${s === speed ? "rgba(124,58,237,0.5)" : "rgba(255,255,255,0.07)"}`,
                borderRadius: "6px", color: s === speed ? "#a78bfa" : "#64748b",
                cursor: "pointer", padding: "4px 10px", fontSize: "10px", fontWeight: "700",
              }}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>

      {/* Axis + markers */}
      <div style={{ flex: 1, position: "relative" }}>
        {/* Tick labels */}
        <div style={{ position: "relative", height: "12px" }}>
          {visibleTicks.map((t) => (
            <span
              key={t.h}
              style={{
                position: "absolute", fontSize: "8px", color: "#475569",
                transform: "translateX(-50%)", left: `${logPos(t.h, axisMax) * 100}%`,
                whiteSpace: "nowrap",
              }}
            >
              {t.label}
            </span>
          ))}
        </div>

        {/* Track */}
        <div
          ref={trackRef}
          onMouseDown={(e) => setFromClientX(e.clientX)}
          onMouseMove={(e) => { if (e.buttons === 1) setFromClientX(e.clientX); }}
          style={{ height: "3px", background: "rgba(255,255,255,0.08)", borderRadius: "2px", position: "relative", marginTop: "14px", cursor: "pointer" }}
        >
          {/* Filled progress */}
          <div style={{
            position: "absolute", left: 0, top: 0, height: "100%", width: `${playheadPct}%`,
            background: "linear-gradient(90deg, #7c3aed, #a78bfa)", borderRadius: "2px",
            transition: playing ? "none" : "width 0.15s",
          }} />

          {/* Hop markers */}
          {hopsWithLabelFlag.map(({ hop, pct, showLabel }) => {
            const tier = confidenceTier(hop.confidence);
            const passed = currentHours >= hop.latencyHours;
            return (
              <div
                key={hop.id}
                onClick={(e) => { e.stopPropagation(); onScrubToHop?.(hop.id); }}
                style={{ position: "absolute", left: `${pct}%`, top: "50%", transform: "translate(-50%, -50%)", cursor: "pointer" }}
                title={`${hop.toLabel} — ${formatTimeDelta(hop.latencyHours)}`}
              >
                <div style={{
                  width: "9px", height: "9px", borderRadius: "50%",
                  background: passed ? tier.color : "rgba(15,23,42,0.95)",
                  border: `2px solid ${tier.color}`,
                  boxShadow: passed ? `0 0 6px ${tier.color}aa` : "none",
                  transition: "background 0.2s",
                }} />
                {showLabel && (
                  <div style={{
                    position: "absolute", top: "16px", left: "50%", transform: "translateX(-50%)",
                    width: "70px", textAlign: "center",
                  }}>
                    <div style={{ fontSize: "8px", color: "#64748b", lineHeight: 1.3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {hop.toLabel.split(" ").slice(0, 3).join(" ")}
                    </div>
                    <div style={{ fontSize: "7px", color: "#334155", fontFamily: "monospace" }}>
                      {formatTimeDelta(hop.latencyHours).replace("T + ", "")}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Playhead */}
          <motion.div
            style={{
              position: "absolute", top: "-44px", left: `${playheadPct}%`,
              width: "2px", height: "88px", background: "#e2e8f0",
              boxShadow: "0 0 6px rgba(226,232,240,0.6)", pointerEvents: "none",
              transform: "translateX(-50%)",
            }}
            transition={{ duration: 0 }}
          />
        </div>
      </div>
    </div>
  );
}
