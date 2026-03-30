"use client";

import { useState } from "react";
import { useAnalysisStore } from "@/store/analysis";
import { DEMO_EVENT } from "@/lib/demo-data";
import type { Event } from "@/lib/types";

const SOURCE_COLORS: Record<string, string> = {
  fred: "bg-blue-900 text-blue-300",
  gdelt: "bg-green-900 text-green-300",
  manual: "bg-violet-900 text-violet-300",
  news: "bg-amber-900 text-amber-300",
  edgar: "bg-rose-900 text-rose-300",
};

function EventItem({ event, active, onClick }: { event: Event; active: boolean; onClick: () => void }) {
  const rel = new Date(event.occurred_at).toLocaleDateString();
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
        active ? "bg-violet-900/40 border border-violet-700/50" : "hover:bg-gray-800"
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${SOURCE_COLORS[event.source] ?? "bg-gray-700 text-gray-300"}`}>
          {event.source.toUpperCase()}
        </span>
        <span className="text-[10px] text-gray-500">{rel}</span>
      </div>
      <p className="text-xs text-gray-200 leading-snug line-clamp-2">{event.title}</p>
    </button>
  );
}

export default function EventSidebar() {
  const { selectedEvent, setSelectedEvent, isDemoMode } = useAnalysisStore();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", source: "manual", raw_text: "" });

  const events: Event[] = isDemoMode ? [DEMO_EVENT] : [];

  return (
    <aside className="w-60 border-r border-gray-800 flex flex-col bg-[#111827]">
      <div className="px-3 py-2 border-b border-gray-800 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Events</span>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-xs text-violet-400 hover:text-violet-300"
        >
          + Add
        </button>
      </div>

      {showForm && (
        <div className="p-3 border-b border-gray-800 space-y-2">
          <input
            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 placeholder-gray-600"
            placeholder="Event title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <textarea
            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 placeholder-gray-600 resize-none"
            placeholder="Raw text / description"
            rows={3}
            value={form.raw_text}
            onChange={(e) => setForm({ ...form, raw_text: e.target.value })}
          />
          <button
            className="w-full bg-violet-700 hover:bg-violet-600 text-white text-xs py-1.5 rounded transition-colors"
            onClick={() => setShowForm(false)}
          >
            Submit
          </button>
        </div>
      )}

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
          <p className="text-xs text-gray-600 text-center mt-8">No events yet</p>
        )}
      </div>
    </aside>
  );
}
