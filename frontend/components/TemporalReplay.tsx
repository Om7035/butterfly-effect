"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { Play, Pause, SkipBack, ChevronDown } from "lucide-react";

const SPEEDS = [0.5, 1, 2, 4] as const;
type Speed = typeof SPEEDS[number];

const MAX_HOURS = 720;
const MARKERS = [
  { h: 0,   label: "t=0" },
  { h: 48,  label: "48h" },
  { h: 168, label: "1wk" },
  { h: 720, label: "30d" },
];

function formatTime(h: number) {
  if (h < 24) return `t + ${h}h`;
  if (h < 168) return `t + ${Math.round(h / 24)}d`;
  return `t + ${Math.round(h / 168)}wk`;
}

interface Props { prefersReduced: boolean }

export default function TemporalReplay({ prefersReduced }: Props) {
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>(1);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);
  const lastTickRef = useRef<number>(0);

  // Playback loop
  useEffect(() => {
    if (!playing) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }
    const tick = (now: number) => {
      if (lastTickRef.current === 0) lastTickRef.current = now;
      const dt = now - lastTickRef.current;
      lastTickRef.current = now;
      // advance 1 hour per 100ms at 1x speed
      setTime((t) => {
        const next = t + (dt / 100) * speed;
        if (next >= MAX_HOURS) { setPlaying(false); return MAX_HOURS; }
        return next;
      });
      rafRef.current = requestAnimationFrame(tick);
    };
    lastTickRef.current = 0;
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [playing, speed]);

  const setFromMouse = useCallback((clientX: number) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    setTime(pct * MAX_HOURS);
  }, []);

  const pct = (time / MAX_HOURS) * 100;
  const activeMarkers = MARKERS.filter((m) => time >= m.h);

  return (
    <div style={{ flexShrink: 0, borderTop: "1px solid rgba(255,255,255,0.05)", background: "rgba(10,14,26,0.95)", padding: "10px 16px" }}>
      {/* Active effects strip */}
      {activeMarkers.length > 1 && (
        <div style={{ display: "flex", gap: "6px", marginBottom: "8px", flexWrap: "wrap" }}>
          {activeMarkers.slice(1).map((m) => (
            <motion.span
              key={m.h}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{ fontSize: "9px", padding: "2px 8px", borderRadius: "20px", border: "1px solid rgba(52,211,153,0.3)", background: "rgba(52,211,153,0.08)", color: "#34d399", fontFamily: "monospace" }}
            >
              {m.label} effects active
            </motion.span>
          ))}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px", flexShrink: 0 }}>
          <button
            onClick={() => { setTime(0); setPlaying(false); }}
            style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", padding: "4px", display: "flex", alignItems: "center" }}
          >
            <SkipBack size={13} />
          </button>
          <button
            onClick={() => { if (time >= MAX_HOURS) setTime(0); setPlaying(!playing); }}
            style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.3)", borderRadius: "6px", color: "#a78bfa", cursor: "pointer", padding: "5px 8px", display: "flex", alignItems: "center" }}
          >
            {playing ? <Pause size={13} /> : <Play size={13} />}
          </button>
        </div>

        {/* Time display */}
        <div style={{ width: "64px", flexShrink: 0 }}>
          <div style={{ fontSize: "11px", fontFamily: "monospace", color: "#7c3aed", fontWeight: "700" }}>{formatTime(Math.round(time))}</div>
        </div>

        {/* Track */}
        <div style={{ flex: 1, position: "relative" }}>
          <div style={{ position: "relative", height: "14px", marginBottom: "2px" }}>
            {MARKERS.map((m) => (
              <span key={m.h} style={{ position: "absolute", fontSize: "8px", color: time >= m.h ? "#475569" : "#2d3748", transform: "translateX(-50%)", left: `${(m.h / MAX_HOURS) * 100}%`, transition: "color 0.3s" }}>
                {m.label}
              </span>
            ))}
          </div>
          <div
            ref={trackRef}
            onMouseDown={(e) => { setFromMouse(e.clientX); }}
            onMouseMove={(e) => { if (e.buttons === 1) setFromMouse(e.clientX); }}
            style={{ height: "6px", background: "rgba(255,255,255,0.06)", borderRadius: "3px", position: "relative", cursor: "pointer" }}
          >
            <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${pct}%`, background: "linear-gradient(90deg, #7c3aed, #34d399)", borderRadius: "3px", transition: playing ? "none" : "width 0.1s" }} />
            {MARKERS.slice(1).map((m) => (
              <div key={m.h} style={{ position: "absolute", top: "50%", transform: "translateY(-50%)", width: "3px", height: "10px", borderRadius: "2px", left: `${(m.h / MAX_HOURS) * 100}%`, background: time >= m.h ? "#34d399" : "#2d3748", transition: "background 0.3s" }} />
            ))}
            <div style={{ position: "absolute", top: "50%", transform: "translateY(-50%)", width: "14px", height: "14px", borderRadius: "50%", background: "#0a0e1a", border: "2px solid #7c3aed", left: `calc(${pct}% - 7px)`, boxShadow: "0 0 8px rgba(124,58,237,0.5)", transition: playing ? "none" : "left 0.1s" }} />
          </div>
        </div>

        {/* Speed control */}
        <div style={{ position: "relative", flexShrink: 0 }}>
          <button
            onClick={() => setShowSpeedMenu(!showSpeedMenu)}
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "6px", padding: "4px 8px", color: "#94a3b8", fontSize: "10px", cursor: "pointer", display: "flex", alignItems: "center", gap: "3px", fontFamily: "monospace" }}
          >
            {speed}x <ChevronDown size={9} />
          </button>
          {showSpeedMenu && (
            <div style={{ position: "absolute", bottom: "100%", right: 0, marginBottom: "4px", background: "rgba(15,23,42,0.98)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "8px", overflow: "hidden", zIndex: 10 }}>
              {SPEEDS.map((s) => (
                <button key={s} onClick={() => { setSpeed(s); setShowSpeedMenu(false); }} style={{ display: "block", width: "100%", padding: "6px 14px", background: s === speed ? "rgba(124,58,237,0.15)" : "none", border: "none", color: s === speed ? "#a78bfa" : "#94a3b8", fontSize: "11px", cursor: "pointer", textAlign: "left", fontFamily: "monospace" }}>
                  {s}x
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
