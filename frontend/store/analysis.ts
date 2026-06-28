// Zustand global UI state
import { create } from "zustand";
import type { Event, CounterfactualResult, GraphNode, GraphEdge } from "@/lib/types";

interface AnalysisState {
  selectedEvent: Event | null;
  counterfactual: CounterfactualResult | null;
  selectedNode: GraphNode | null;
  scrubberTime: number; // 0..168
  showTimeline: "A" | "B";
  isDemoMode: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];

  setSelectedEvent: (e: Event | null) => void;
  setCounterfactual: (r: CounterfactualResult | null) => void;
  setSelectedNode: (n: GraphNode | null) => void;
  setScrubberTime: (t: number) => void;
  setShowTimeline: (t: "A" | "B") => void;
  setDemoMode: (v: boolean) => void;
  setGraph: (nodes: GraphNode[], edges: GraphEdge[]) => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  selectedEvent: null,
  counterfactual: null,
  selectedNode: null,
  scrubberTime: 0,
  showTimeline: "A",
  isDemoMode: false,
  nodes: [],
  edges: [],

  setSelectedEvent: (e) => set({ selectedEvent: e }),
  setCounterfactual: (r) => set({ counterfactual: r }),
  setSelectedNode: (n) => set({ selectedNode: n }),
  setScrubberTime: (t) => set({ scrubberTime: t }),
  setShowTimeline: (t) => set({ showTimeline: t }),
  setDemoMode: (v) => set({ isDemoMode: v }),
  setGraph: (nodes, edges) => set({ nodes, edges }),
}));
