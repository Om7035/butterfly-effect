"use client";

import { useRef, useCallback } from "react";
import { useAnalysisStore } from "@/store/analysis";

export default function TemporalScrubber() {
  const { scrubberTime, setScrubberTime, showTimeline, setShowTimeline } = useAnalysisStore();
  const trackRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (e.buttons !== 1 || !trackRef.current) return;
      const rect = trackRef.current.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      setScrubberTime(Math.round(pct * 168));
    },
    [setScrubberTime]
  );

  const pct = (scrubberTime / 168) * 100;

  return (
    <div className="h-14 border-t border-gray-800 bg-[#111827] px-4 flex items-center gap-4 shrink-0">
      <span className="text-xs text-gray-500 w-16 shrink-0">T+{scrubberTime}h</span>

      {/* Track */}
      <div
        ref={trackRef}
        className="flex-1 h-1.5 bg-gray-700 rounded-full relative cursor-pointer"
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseMove}
      >
        <div
          className="absolute left-0 top-0 h-full bg-violet-500 rounded-full"
          style={{ width: `${pct}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-white rounded-full shadow border-2 border-violet-500"
          style={{ left: `calc(${pct}% - 7px)` }}
        />
        {/* Latency markers */}
        {[48, 168, 720].map((h) => (
          <div
            key={h}
            className="absolute top-3 text-[9px] text-gray-600"
            style={{ left: `${(h / 168) * 100}%` }}
          >
            {h}h
          </div>
        ))}
      </div>

      {/* Timeline toggle */}
      <div className="flex rounded overflow-hidden border border-gray-700 shrink-0">
        {(["A", "B"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setShowTimeline(t)}
            className={`px-3 py-1 text-xs transition-colors ${
              showTimeline === t
                ? "bg-violet-700 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Timeline {t}
          </button>
        ))}
      </div>
    </div>
  );
}
