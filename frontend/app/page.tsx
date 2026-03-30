"use client";

import { useEffect } from "react";
import { useAnalysisStore } from "@/store/analysis";
import { DEMO_COUNTERFACTUAL, DEMO_GRAPH_NODES, DEMO_GRAPH_EDGES, DEMO_EVENT } from "@/lib/demo-data";
import EventSidebar from "@/components/EventSidebar";
import CausalGraph from "@/components/CausalGraph";
import EvidencePanel from "@/components/EvidencePanel";
import TemporalScrubber from "@/components/TemporalScrubber";
import CounterfactualDiff from "@/components/CounterfactualDiff";

export default function Dashboard() {
  const { isDemoMode, setDemoMode, setGraph, setCounterfactual, setSelectedEvent, counterfactual } =
    useAnalysisStore();

  useEffect(() => {
    setDemoMode(true);
    setGraph(DEMO_GRAPH_NODES, DEMO_GRAPH_EDGES);
    setCounterfactual(DEMO_COUNTERFACTUAL);
    setSelectedEvent(DEMO_EVENT);
  }, []);

  const edgeCount = counterfactual?.causal_edges.length ?? 0;
  const passedCount = counterfactual?.causal_edges.filter((e) => e.refutation_passed).length ?? 0;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#070b14]">
      {/* Top bar */}
      <header className="flex items-center justify-between px-5 py-2.5 border-b border-gray-800/80 bg-[#0d1117]/90 backdrop-blur shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-violet-600 flex items-center justify-center text-xs">🦋</div>
            <span className="text-sm font-bold tracking-tight text-white">butterfly-effect</span>
          </div>
          <span className="text-[10px] text-gray-600 border-l border-gray-800 pl-3">causal chain tracer</span>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4">
          {edgeCount > 0 && (
            <>
              <div className="text-center">
                <div className="text-sm font-bold text-violet-400">{edgeCount}</div>
                <div className="text-[9px] text-gray-600">causal edges</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-bold text-teal-400">{passedCount}</div>
                <div className="text-[9px] text-gray-600">validated</div>
              </div>
            </>
          )}
          {isDemoMode && (
            <span className="text-[10px] bg-violet-900/40 text-violet-300 px-2.5 py-1 rounded-full border border-violet-700/40">
              Demo · 2022 Fed Rate Cycle
            </span>
          )}
          <a
            href="/demo"
            className="text-[10px] text-gray-500 hover:text-gray-300 transition-colors border border-gray-800 hover:border-gray-700 px-2.5 py-1 rounded-md"
          >
            Scenarios →
          </a>
        </div>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        <EventSidebar />

        <main className="flex-1 flex flex-col overflow-hidden">
          <CausalGraph />
          <TemporalScrubber />
        </main>

        <aside className="w-80 border-l border-gray-800/80 flex flex-col overflow-hidden bg-[#0d1117]">
          {/* Panel header */}
          <div className="px-3 py-2 border-b border-gray-800/60 flex items-center gap-2">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">Evidence</span>
          </div>
          <EvidencePanel />
          <CounterfactualDiff />
        </aside>
      </div>
    </div>
  );
}
