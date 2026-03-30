"use client";

import { useAnalysisStore } from "@/store/analysis";

export default function EvidencePanel() {
  const { selectedNode, counterfactual, edges } = useAnalysisStore();

  if (!selectedNode) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-xs text-gray-600 text-center">Click a node to see evidence</p>
      </div>
    );
  }

  const outEdges = edges.filter((e) => e.source === selectedNode.id);
  const inEdges = edges.filter((e) => e.target === selectedNode.id);

  const delta = counterfactual?.diff[selectedNode.id];
  const peakDelta = delta ? Math.max(...delta.map(Math.abs)) : null;
  const peakHour = counterfactual?.peak_delta_at_hours[selectedNode.id];

  const causalEdge = counterfactual?.causal_edges.find(
    (e) => e.target_node_id === selectedNode.id
  );

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-4">
      {/* Node header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-gray-200">{selectedNode.label}</span>
          <span className="text-[10px] bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded">
            {selectedNode.type}
          </span>
        </div>
        {peakDelta !== null && (
          <div className={`text-sm font-bold ${peakDelta > 0 ? "text-amber-400" : "text-teal-400"}`}>
            {peakDelta > 0 ? "+" : ""}{peakDelta.toFixed(3)} vs baseline
            {peakHour !== undefined && (
              <span className="text-xs font-normal text-gray-500 ml-1">at T+{peakHour}h</span>
            )}
          </div>
        )}
      </div>

      {/* Confidence bar */}
      {causalEdge && (
        <div>
          <div className="flex justify-between text-[10px] text-gray-500 mb-1">
            <span>Confidence</span>
            <span>{(causalEdge.strength_score * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-gray-700 rounded-full">
            <div
              className="h-full bg-violet-500 rounded-full"
              style={{ width: `${causalEdge.strength_score * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
            <span>{causalEdge.confidence_interval[0].toFixed(2)}</span>
            <span>{causalEdge.confidence_interval[1].toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Edges */}
      {outEdges.length > 0 && (
        <div>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Causes</p>
          {outEdges.map((e) => (
            <div key={e.id} className="flex items-center justify-between py-1 border-b border-gray-800">
              <span className="text-xs text-gray-300">{e.target}</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-500">{e.latency_hours}h</span>
                <div className="w-12 h-1 bg-gray-700 rounded-full">
                  <div className="h-full bg-violet-500 rounded-full" style={{ width: `${e.strength * 100}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {inEdges.length > 0 && (
        <div>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Caused by</p>
          {inEdges.map((e) => (
            <div key={e.id} className="flex items-center justify-between py-1 border-b border-gray-800">
              <span className="text-xs text-gray-300">{e.source}</span>
              <span className="text-[10px] text-gray-500">{e.relationship_type}</span>
            </div>
          ))}
        </div>
      )}

      {/* Evidence paths */}
      {causalEdge?.evidence_path && causalEdge.evidence_path.length > 0 && (
        <div>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Evidence</p>
          {causalEdge.evidence_path.map((src) => (
            <div key={src} className="text-xs text-violet-400 py-0.5">{src}</div>
          ))}
          {causalEdge.refutation_passed && (
            <div className="text-[10px] text-teal-400 mt-1">Refutation tests passed</div>
          )}
        </div>
      )}
    </div>
  );
}
