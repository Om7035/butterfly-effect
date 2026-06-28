/**
 * AlternativeChainsPanel - Display alternative causal chains and feedback loops
 *
 * Shows:
 * - Primary chain (highest probability)
 * - Alternative chains (less likely but plausible)
 * - Detected feedback loops (cycles in causality)
 */

import { useState } from "react";
import { ChevronDown, Zap, AlertTriangle } from "lucide-react";

interface CausalChain {
  rank: number;
  hops: string[];
  description: string;
  cumulative_probability: number;
  primary: boolean;
}

interface FeedbackLoop {
  nodes: string[];
  length: number;
  mean_confidence: number;
  has_feedback: boolean;
  description: string;
}

interface AlternativeChainsProps {
  chains?: CausalChain[];
  feedbackLoops?: FeedbackLoop[];
}

export default function AlternativeChainsPanel({
  chains = [],
  feedbackLoops = [],
}: AlternativeChainsProps) {
  const [expandedChain, setExpandedChain] = useState<number | null>(chains.length > 0 ? 1 : null);
  const [expandedLoop, setExpandedLoop] = useState<number | null>(null);

  if (chains.length === 0 && feedbackLoops.length === 0) return null;

  return (
    <div className="mt-6 space-y-4">
      {/* Alternative Chains */}
      {chains.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-semibold text-slate-200 text-sm flex items-center gap-2">
            <Zap size={16} className="text-yellow-500" />
            Causal Chains
          </h3>

          {chains.map((chain) => (
            <div
              key={chain.rank}
              className={`border rounded-lg overflow-hidden transition-all ${
                chain.primary
                  ? "border-blue-500 bg-blue-950"
                  : "border-slate-700 bg-slate-900"
              }`}
            >
              {/* Chain Header */}
              <button
                onClick={() =>
                  setExpandedChain(expandedChain === chain.rank ? null : chain.rank)
                }
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-800 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 text-left">
                  {chain.primary && (
                    <span className="px-2 py-1 bg-blue-600 text-white text-xs font-bold rounded">
                      PRIMARY
                    </span>
                  )}
                  <div className="flex-1">
                    <p className="font-medium text-slate-200">{chain.description}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Chain probability: {(chain.cumulative_probability * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
                <ChevronDown
                  size={18}
                  className={`text-slate-400 transition-transform ${
                    expandedChain === chain.rank ? "rotate-180" : ""
                  }`}
                />
              </button>

              {/* Chain Details */}
              {expandedChain === chain.rank && (
                <div className="px-4 py-3 bg-slate-800 border-t border-slate-700 space-y-2">
                  <p className="text-xs text-slate-400 font-semibold">Hops in chain:</p>
                  <div className="space-y-1">
                    {chain.hops.map((hop, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm text-slate-300">
                        <span className="text-slate-500 font-mono">{idx + 1}</span>
                        <span>{hop}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-slate-700">
                    Probability compounds: each hop multiplies by its confidence.
                    Longer chains are naturally less certain.
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Feedback Loops */}
      {feedbackLoops.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-semibold text-slate-200 text-sm flex items-center gap-2">
            <AlertTriangle size={16} className="text-orange-500" />
            Feedback Loops Detected ({feedbackLoops.length})
          </h3>

          {feedbackLoops.map((loop, idx) => (
            <div
              key={idx}
              className="border border-orange-700 bg-orange-950 rounded-lg overflow-hidden"
            >
              {/* Loop Header */}
              <button
                onClick={() => setExpandedLoop(expandedLoop === idx ? null : idx)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-orange-900 transition-colors"
              >
                <div className="flex-1 text-left">
                  <p className="font-medium text-orange-200">
                    {loop.has_feedback ? "✓ Corrective" : ""} {loop.description}
                  </p>
                  <p className="text-xs text-orange-300 mt-1">
                    Mean confidence: {(loop.mean_confidence * 100).toFixed(0)}%
                  </p>
                </div>
                <ChevronDown
                  size={18}
                  className={`text-orange-400 transition-transform ${
                    expandedLoop === idx ? "rotate-180" : ""
                  }`}
                />
              </button>

              {/* Loop Details */}
              {expandedLoop === idx && (
                <div className="px-4 py-3 bg-orange-900 border-t border-orange-700 space-y-2">
                  <p className="text-xs text-orange-200 font-semibold">Cycle path:</p>
                  <div className="space-y-1">
                    {loop.nodes.map((node, nidx) => (
                      <div key={nidx} className="flex items-center gap-2 text-sm text-orange-100">
                        <span className="text-orange-400">→</span>
                        <span>{node}</span>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 text-sm text-orange-100 pt-1 border-t border-orange-700">
                      <span className="text-orange-400">↻</span>
                      <span className="italic">Closes to start (feedback)</span>
                    </div>
                  </div>

                  <div className="mt-3 pt-3 border-t border-orange-700 space-y-1">
                    <p className="text-xs text-orange-300">
                      <strong>What this means:</strong> This is a self-correcting loop.
                      The system naturally responds to counteract the initial effect.
                    </p>
                    <p className="text-xs text-orange-300">
                      Example: Fed raises rates → inflation drops → Fed keeps rates high.
                    </p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
