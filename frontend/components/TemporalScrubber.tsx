"use client";

import { useRef, useCallback, useState } from "react";
import { useAnalysisStore } from "@/store/analysis";

const MARKERS = [
  { h: 0, label: "t=0" },
  { h: 48, label: "48h" },
  { h: 168, label: "1wk" },
  { h: 720, label: "30d" },
];

export default function TemporalScrubber() {
  const { scrubberTime, setScrubberTime, showTimeline, setShowTimeline, counterfactual } =
    useAnalysisStore();
  const trackRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);

  const maxHours = 2160; // 90 days

  const setFromMouse = useCallback(
    (clientX: number) => {
      if (!trackRef.current) return;
      const rect = trackRef.current.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      setScrubberTime(Math.round(pct * maxHours));
    },
    [setScrubberTime]
  );

  const pct = (scrubberTime / maxHours) * 100;

  // Find active causal edges at current time
  const activeEdges =
    counterfactual?.causal_edges.filter((e) => scrubberTime >= e.latency_hours) ?? [];

  return (
    <div className="shrink-0 border-t border-gray-800/80 bg-[#0d1117]">
      {/* Active effects strip */}
      {activeEdges.length > 0 && (
        <div className="px-4 pt-2 flex gap-2 flex-wrap">
          {activeEdges.map((e) => (
            <span
              key={e.edge_id}
              className="text-[9px] px-2 py-0.5 rounded-full border border-teal-700/50 bg-teal-900/20 text-teal-400"
            >
              {e.source_node_id} → {e.target_node_id}
              <span className="ml-1 text-teal-600">
                {e.counterfactual_delta > 0 ? "+" : ""}
                {e.counterfactual_delta.toFixed(2)}
              </span>
            </span>
          ))}
        </div>
      )}

      <div className="px-4 py-3 flex items-center gap-4">
        {/* Time display */}
        <div className="w-20 shrink-0">
          <div className="text-xs font-mono text-violet-400">T+{scrubberTime}h</div>
          <div className="text-[9px] text-gray-600">
            {scrubberTime < 24 ? `${scrubberTime}h` : scrubberTime < 168 ? `${Math.round(scrubberTime / 24)}d` : `${Math.round(scrubberTime / 168)}wk`}
          </div>
        </div>

        {/* Track */}
        <div className="flex-1 relative">
          {/* Marker labels */}
          <div className="relative h-4 mb-1">
            {MARKERS.map((m) => (
              <span
                key={m.h}
                className="absolute text-[9px] text-gray-600 -translate-x-1/2"
                style={{ left: `${(m.h / maxHours) * 100}%` }}
              >
                {m.label}
              </span>
            ))}
          </div>

          {/* Track bar */}
          <div
            ref={trackRef}
            className="h-2 bg-gray-800 rounded-full relative cursor-pointer select-none"
            onMouseDown={(e) => { setDragging(true); setFromMouse(e.clientX); }}
            onMouseMove={(e) => { if (dragging) setFromMouse(e.clientX); }}
            onMouseUp={() => setDragging(false)}
            onMouseLeave={() => setDragging(false)}
          >
            {/* Filled portion */}
            <div
              className="absolute left-0 top-0 h-full rounded-full"
              style={{
                width: `${pct}%`,
                background: "linear-gradient(90deg, #7c3aed, #14b8a6)",
              }}
            />

            {/* Latency markers */}
            {MARKERS.slice(1).map((m) => (
              <div
                key={m.h}
                className="absolute top-1/2 -translate-y-1/2 w-1 h-3 rounded-sm"
                style={{
                  left: `${(m.h / maxHours) * 100}%`,
                  background: scrubberTime >= m.h ? "#14b8a6" : "#374151",
                }}
              />
            ))}

            {/* Handle */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-violet-400 bg-[#0d1117] shadow-lg transition-transform"
              style={{
                left: `calc(${pct}% - 8px)`,
                boxShadow: dragging ? "0 0 12px rgba(139,92,246,0.8)" : "0 0 6px rgba(139,92,246,0.4)",
                transform: `translateY(-50%) scale(${dragging ? 1.3 : 1})`,
              }}
            />
          </div>
        </div>

        {/* Timeline toggle */}
        <div className="flex rounded-lg overflow-hidden border border-gray-700 shrink-0">
          {(["A", "B"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setShowTimeline(t)}
              className={`px-3 py-1.5 text-xs font-medium transition-all ${
                showTimeline === t
                  ? "bg-violet-700 text-white shadow-inner"
                  : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
              }`}
            >
              {t === "A" ? "With Event" : "Baseline"}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
