"use client";

import { useState } from "react";
import { useAnalysisStore } from "@/store/analysis";
import { DEMO_EVENT } from "@/lib/demo-data";
import type { Event } from "@/lib/types";

const SOURCE_STYLES: Record<string, string> = {
  fred:   "bg-blue-900/40 text-blue-300 border-blue-700/40",
  gdelt:  "bg-green-900/40 text-green-300 border-green-700/40",
  manual: "bg-violet-900/40 text-violet-300 border-violet-700/40",
  news:   "bg-amber-900/40 text-amber-300 border-amber-700/40",
  edgar:  "bg-rose-900/40 text-rose-300 border-rose-700/40",
};

function EventItem({ event, active, onClick }: { event: Event; active: boolean; onClick: () => void }) {
  const date = new Date(event.occurred_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-3 rounded-xl transition-all duration-150 group ${
        active
          ? "bg-violet-900/30 border border-violet-700/50 shadow-lg shadow-violet-900/20"
          : "hover:bg-gray-800/60 border border-transparent"
      }`}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`text-[9px] px-1.5 py-0.5 rounded-md border font-semibold tracking-wide ${SOURCE_STYLES[event.source] ?? "bg-gray-700 text-gray-300 border-gray-600"}`}>
          {event.source.toUpperCase()}
        </span>
        <span className="text-[9px] text-gray-600 ml-auto">{date}</span>
      </div>
      <p className="text-xs text-gray-200 leading-snug line-clamp-2 group-hover:text-white transition-colors">
        {event.title}
      </p>
      {active && (
        <div className="mt-1.5 flex items-center gap-1 text-[9px] text-violet-400">
          <div className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
          Analyzing
        </div>
      )}
    </button>
  );
}

export default function EventSidebar() {
  const { selectedEvent, setSelectedEvent, isDemoMode } = useAnalysisStore();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", raw_text: "", source: "manual" });

  const events: Event[] = isDemoMode ? [DEMO_EVENT] : [];

  return (
    <aside className="w-60 border-r border-gray-800/80 flex flex-col bg-[#0d1117]">
      {/* Header */}
      <div className="px-3 py-3 border-b border-gray-800/60 flex items-center justify-between">
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Events</span>
        <button
          onClick={() => setShowForm(!showForm)}
          className={`text-[10px] px-2 py-1 rounded-md transition-all ${
            showForm
              ? "bg-violet-700 text-white"
              : "text-violet-400 hover:bg-violet-900/30 border border-violet-800/40"
          }`}
        >
          {showForm ? "Cancel" : "+ Add"}
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="p-3 border-b border-gray-800/60 space-y-2 bg-gray-900/30">
          <input
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-600 transition-colors"
            placeholder="Event title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <textarea
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200 placeholder-gray-600 resize-none focus:outline-none focus:border-violet-600 transition-colors"
            placeholder="Describe the event..."
            rows={3}
            value={form.raw_text}
            onChange={(e) => setForm({ ...form, raw_text: e.target.value })}
          />
          <button
            className="w-full bg-violet-700 hover:bg-violet-600 text-white text-xs py-1.5 rounded-lg transition-colors font-medium"
            onClick={() => setShowForm(false)}
          >
            Analyze Event
          </button>
        </div>
      )}

      {/* Event list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {events.map((e) => (
          <EventItem
            key={e.event_id}
            event={e}
            active={selectedEvent?.event_id === e.event_id}
            onClick={() => setSelectedEvent(e)}
          />
        ))}
        {events.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 gap-2">
            <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center">
              <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <p className="text-xs text-gray-600 text-center">Add an event to start<br />causal analysis</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-gray-800/60">
        <div className="text-[9px] text-gray-700 text-center">
          butterfly-effect v0.1 · causal inference
        </div>
      </div>
    </aside>
  );
}
