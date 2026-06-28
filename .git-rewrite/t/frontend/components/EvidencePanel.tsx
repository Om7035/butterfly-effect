"use client";

import { useAnalysisStore } from "@/store/analysis";

const METRIC_UNITS: Record<string, string> = {
  FEDFUNDS: "%",
  MORTGAGE30US: "%",
  HOUST: "k units",
  UNRATE: "%",
  T10Y2Y: "%",
};

export default function EvidencePanel() {
  const { selectedNode, counterfactual, edges } = useAnalysisStore();

  if (!selectedNode) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-3">
        <div className="w-12 h-12 rounded-full bg-gray-800/60 flex items-center justify-center">
          <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-xs text-gray-600 text-center">Click a node in the graph<br />to inspect its causal evidence</p>
      </div>
    );
  }

  const outEdges = edges.filter((e) => e.source === selectedNode.id);
  const inEdges = edges.filter((e) => e.target === selectedNode.id);
  const diffVals = counterfactual?.diff[selectedNode.id] ?? [];
  const peakDelta = diffVals.length ? Math.max(...diffVals.map(Math.abs)) : null;
  const peakHour = counterfactual?.peak_delta_at_hours[selectedNode.id];
  const causalEdge = counterfactual?.causal_edges.find((e) => e.target_node_id === selectedNode.id);
  const unit = METRIC_UNITS[selectedNode.id] ?? "";

  const typeColors: Record<string, string> = {
    Event: "text-violet-400 bg-violet-900/30 border-violet-700/40",
    Metric: "text-teal-400 bg-teal-900/30 border-teal-700/40",
    Entity: "text-orange-400 bg-orange-900/30 border-orange-700/40",
    Policy: "text-blue-400 bg-blue-900/30 border-blue-700/40",
  };

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Node header */}
      <div className="p-4 border-b border-gray-800/80 bg-gradient-to-b from-gray-900/50 to-transparent">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-sm font-semibold text-gray-100 leading-tight">{selectedNode.label}</h3>
          <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium shrink-0 ${typeColors[selectedNode.type] ?? "text-gray-400 bg-gray-800 border-gray-700"}`}>
            {selectedNode.type}
          </span>
        </div>

        {peakDelta !== null && (
          <div className="flex items-baseline gap-2">
            <span className={`text-xl font-bold font-mono ${peakDelta > 0 ? "text-amber-400" : "text-teal-400"}`}>
              {peakDelta > 0 ? "+" : ""}{peakDelta.toFixed(3)}{unit}
            </span>
            <span className="text-xs text-gray-500">vs baseline</span>
            {peakHour !== undefined && (
              <span className="text-xs text-gray-600 ml-auto">peak @T+{peakHour}h</span>
            )}
          </div>
        )}
      </div>

      <div className="p-3 space-y-4">
        {/* Confidence */}
        {causalEdge && (
          <div className="bg-gray-900/60 rounded-lg p-3 border border-gray-800/60">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider">Causal Strength</span>
              <span className="text-sm font-bold text-violet-400">{(causalEdge.strength_score * 100).toFixed(0)}%</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${causalEdge.strength_score * 100}%`,
                  background: "linear-gradient(90deg, #7c3aed, #14b8a6)",
                }}
              />
            </div>
            <div className="flex justify-between text-[9px] text-gray-600 mt-1">
              <span>95% CI: [{causalEdge.confidence_interval[0].toFixed(2)}, {causalEdge.confidence_interval[1].toFixed(2)}]</span>
              <span>latency: {causalEdge.latency_hours}h</span>
            </div>
          </div>
        )}

        {/* Causal chain */}
        {outEdges.length > 0 && (
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Downstream Effects</p>
            <div className="space-y-1.5">
              {outEdges.map((e) => (
                <div key={e.id} className="flex items-center gap-2 bg-gray-900/40 rounded-lg px-3 py-2 border border-gray-800/40">
                  <div className="w-1.5 h-1.5 rounded-full bg-teal-500 shrink-0" />
                  <span className="text-xs text-gray-300 flex-1">{e.target}</span>
                  <span className="text-[10px] text-gray-600">{e.latency_hours}h</span>
                  <div className="w-10 h-1 bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full bg-violet-500 rounded-full" style={{ width: `${e.strength * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {inEdges.length > 0 && (
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Caused By</p>
            <div className="space-y-1.5">
              {inEdges.map((e) => (
                <div key={e.id} className="flex items-center gap-2 bg-gray-900/40 rounded-lg px-3 py-2 border border-gray-800/40">
                  <div className="w-1.5 h-1.5 rounded-full bg-violet-500 shrink-0" />
                  <span className="text-xs text-gray-300 flex-1">{e.source}</span>
                  <span className="text-[10px] text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">{e.relationship_type}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Evidence */}
        {causalEdge?.evidence_path && causalEdge.evidence_path.length > 0 && (
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Evidence Sources</p>
            <div className="space-y-1">
              {causalEdge.evidence_path.map((src) => (
                <div key={src} className="flex items-center gap-2 text-xs text-violet-400 bg-violet-900/10 rounded px-2 py-1.5 border border-violet-800/20">
                  <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {src}
                </div>
              ))}
            </div>
            {causalEdge.refutation_passed && (
              <div className="flex items-center gap-1.5 mt-2 text-[10px] text-teal-400">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Refutation tests passed
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
