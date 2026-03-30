"use client";

import { useAnalysisStore } from "@/store/analysis";
import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";

const METRIC_LABELS: Record<string, string> = {
  FEDFUNDS: "Fed Funds Rate",
  MORTGAGE30US: "30yr Mortgage",
  HOUST: "Housing Starts",
  UNRATE: "Unemployment",
  T10Y2Y: "Yield Curve",
};

interface CounterfactualDiffProps {
  eventTitle?: string;
}

export default function CounterfactualDiff({ eventTitle }: CounterfactualDiffProps) {
  const { counterfactual, selectedEvent } = useAnalysisStore();

  if (!counterfactual) {
    return (
      <div className="h-48 flex items-center justify-center border-t border-gray-800">
        <p className="text-xs text-gray-600">No counterfactual data</p>
      </div>
    );
  }

  const title = eventTitle ?? selectedEvent?.title ?? "Event";
  const metrics = Object.keys(counterfactual.diff).slice(0, 4);

  // Count significant deviations
  const significant = metrics.filter((m) => {
    const vals = counterfactual.diff[m] ?? [];
    return Math.max(...vals.map(Math.abs)) > 0.01;
  });

  return (
    <div className="border-t border-gray-800 overflow-y-auto" style={{ maxHeight: "280px" }}>
      <div className="px-3 py-2 border-b border-gray-800">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider">Counterfactual Diff</p>
      </div>

      <div className="p-3 space-y-3">
        {metrics.map((metric) => {
          const aVals = counterfactual.timeline_a[metric] ?? [];
          const bVals = counterfactual.timeline_b[metric] ?? [];
          const diffVals = counterfactual.diff[metric] ?? [];
          const peakDelta = diffVals.length ? Math.max(...diffVals.map(Math.abs)) : 0;
          const peakHour = counterfactual.peak_delta_at_hours[metric] ?? 0;

          // Downsample to 30 points for sparkline
          const step = Math.max(1, Math.floor(aVals.length / 30));
          const chartData = aVals
            .filter((_, i) => i % step === 0)
            .map((a, i) => ({ t: i * step, a, b: bVals[i * step] ?? a }));

          const isPositive = (diffVals[diffVals.length - 1] ?? 0) > 0;

          return (
            <div key={metric} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-300">{METRIC_LABELS[metric] ?? metric}</span>
                <span className={`text-xs font-semibold ${isPositive ? "text-amber-400" : "text-teal-400"}`}>
                  {isPositive ? "+" : ""}{peakDelta.toFixed(3)}
                  <span className="text-[9px] text-gray-500 font-normal ml-1">@{peakHour}h</span>
                </span>
              </div>
              <ResponsiveContainer width="100%" height={36}>
                <LineChart data={chartData}>
                  <Line type="monotone" dataKey="a" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
                  <Line type="monotone" dataKey="b" stroke="#6b7280" dot={false} strokeWidth={1} strokeDasharray="3 3" />
                  <Tooltip
                    contentStyle={{ background: "#111827", border: "1px solid #374151", fontSize: 10 }}
                    formatter={(v: number) => v.toFixed(3)}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          );
        })}

        {/* Summary */}
        <div className="bg-gray-800/50 rounded p-2 text-[10px] text-gray-400 space-y-0.5">
          <p>{significant.length} metric{significant.length !== 1 ? "s" : ""} deviated significantly</p>
          <p>Causal chain: {counterfactual.causal_edges.length} edges</p>
        </div>
      </div>
    </div>
  );
}
