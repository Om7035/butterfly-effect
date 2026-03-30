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
  const { isDemoMode, setDemoMode, setGraph, setCounterfactual, setSelectedEvent } =
    useAnalysisStore();

  // Auto-load demo on first visit
  useEffect(() => {
    setDemoMode(true);
    setGraph(DEMO_GRAPH_NODES, DEMO_GRAPH_EDGES);
    setCounterfactual(DEMO_COUNTERFACTUAL);
    setSelectedEvent(DEMO_EVENT);
  }, []);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-[#111827] shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold tracking-tight">butterfly-effect</span>
          <span className="text-xs text-gray-500">causal chain tracer</span>
        </div>
        {isDemoMode && (
          <span className="text-xs bg-violet-900/50 text-violet-300 px-2 py-1 rounded">
            Demo mode — 2022 Fed Rate Cycle
          </span>
        )}
        <button
          onClick={() => setDemoMode(!isDemoMode)}
          className="text-xs text-gray-400 hover:text-white transition-colors"
        >
          {isDemoMode ? "Connect API" : "Demo Mode"}
        </button>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <EventSidebar />

        {/* Center: graph */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <CausalGraph />
          <TemporalScrubber />
        </main>

        {/* Right: evidence + diff */}
        <aside className="w-80 border-l border-gray-800 flex flex-col overflow-hidden">
          <EvidencePanel />
          <CounterfactualDiff />
        </aside>
      </div>
    </div>
  );
}
