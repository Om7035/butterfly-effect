"use client";

import { useEffect } from "react";
import { useAnalysisStore } from "@/store/analysis";
import { DEMO_COUNTERFACTUAL, DEMO_GRAPH_NODES, DEMO_GRAPH_EDGES, DEMO_EVENT } from "@/lib/demo-data";
import EventSidebar from "@/components/EventSidebar";
import CausalGraph from "@/components/CausalGraph";
import EvidencePanel from "@/components/EvidencePanel";
import TemporalScrubber from "@/components/TemporalScrubber";
import CounterfactualDiff from "@/components/CounterfactualDiff";

const SCENARIOS = [
  { id: "fed_2022", label: "2022 Fed Hike" },
  { id: "texas_2021", label: "2021 Texas Storm" },
  { id: "covid_supply", label: "COVID Supply Chain" },
] as const;

export default function DemoPage() {
  const { setDemoMode, setGraph, setCounterfactual, setSelectedEvent } = useAnalysisStore();

  useEffect(() => {
    setDemoMode(true);
    setGraph(DEMO_GRAPH_NODES, DEMO_GRAPH_EDGES);
    setCounterfactual(DEMO_COUNTERFACTUAL);
    setSelectedEvent(DEMO_EVENT);
  }, []);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Banner */}
      <div className="bg-violet-900/40 border-b border-violet-700/40 px-4 py-2 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xs text-violet-300 font-medium">Demo mode — pre-loaded fixture data</span>
          <div className="flex gap-1">
            {SCENARIOS.map((s) => (
              <button
                key={s.id}
                className={`text-[10px] px-2 py-0.5 rounded transition-colors ${
                  s.id === "fed_2022"
                    ? "bg-violet-700 text-white"
                    : "text-violet-400 hover:text-white"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <a
          href="https://github.com/Om7035/butterfly-effect"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-violet-300 hover:text-white transition-colors"
        >
          Deploy your own →
        </a>
      </div>

      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-[#111827] shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold tracking-tight">butterfly-effect</span>
          <span className="text-xs text-gray-500">causal chain tracer</span>
        </div>
        <a href="/" className="text-xs text-gray-400 hover:text-white transition-colors">
          Back to dashboard
        </a>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        <EventSidebar />
        <main className="flex-1 flex flex-col overflow-hidden">
          <CausalGraph />
          <TemporalScrubber />
        </main>
        <aside className="w-80 border-l border-gray-800 flex flex-col overflow-hidden">
          <EvidencePanel />
          <CounterfactualDiff />
        </aside>
      </div>
    </div>
  );
}
