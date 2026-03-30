"use client";

import { useAnalysisStore } from "@/store/analysis";
import { AreaChart, Area, ResponsiveContainer, Tooltip, ReferenceLine } from "recharts";

const METRIC_META: Record<string, { label: string; unit: string; icon: string }> = {
  FEDFUNDS:    { label: "Fed Funds Rate",  unit: "%",       icon: "🏦" },
  MORTGAGE30US:{ label: "30yr Mortgage",   unit: "%",       icon: "🏠" },
  HOUST:       { label: "Housing Starts",  unit: "k units", icon: "🏗️" },
  UNRATE:      { label: "Unemployment",    unit: "%",       icon: "👷" },
  T10Y2Y:      { label: "Yield Curve",     unit: "%",       icon: "📈" },
};

export default function CounterfactualDiff() {
  const { counterfactual, selectedEvent } = useAnalysisStore();

  if (!counterfactual) {
    return (
      <div className="border-t border-gray-800/80 h-40 flex items-center justify-center">
        <p className="text-xs text-gray-600">No counterfactual data</p>
      </div>
    );
  }

  const metrics = Object.keys(counterfactual.diff).slice(0, 4);
  const significant = metrics.filter((m) => {
    const vals = counterfactual.diff[m] ?? [];
    return Math.max(...vals.map(Math.abs)) > 0.01;
  });

  return (
    <div className="border-t border-gray-800/80 overflow-y-auto" style={{ maxHeight: "320px" }}>
      <div className="px-3 py-2 border-b border-gray-800/60 flex items-center justify-between">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">Counterfactual Diff</p>
        <span className="text-[9px] text-teal-500 bg-teal-900/20 px-1.5 py-0.5 rounded-full border border-teal-800/30">
          {significant.length} significant
        </span>
      </div>

      <div className="p-3 space-y-3">
        {metrics.map((metric) => {
          const meta = METRIC_META[metric] ?? { label: metric, unit: "", icon: "📊" };
          const aVals = counterfactual.timeline_a[metric] ?? [];
          const bVals = counterfactual.timeline_b[metric] ?? [];
          const diffVals = counterfactual.diff[metric] ?? [];
          const peakDelta = diffVals.length ? Math.max(...diffVals.map(Math.abs)) : 0;
          const peakHour = counterfactual.peak_delta_at_hours[metric] ?? 0;
          const lastDiff = diffVals[diffVals.length - 1] ?? 0;
          const isPositive = lastDiff > 0;

          // Downsample to 40 points
          const step = Math.max(1, Math.floor(aVals.length / 40));
          const chartData = aVals
            .filter((_, i) => i % step === 0)
            .map((a, i) => ({
              t: i * step,
              a: parseFloat(a.toFixed(3)),
              b: parseFloat((bVals[i * step] ?? a).toFixed(3)),
            }));

          return (
            <div key={metric} className="bg-gray-900/50 rounded-lg p-2.5 border border-gray-800/50 hover:border-gray-700/60 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm">{meta.icon}</span>
                  <span className="text-xs text-gray-300 font-medium">{meta.label}</span>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-bold font-mono ${isPositive ? "text-amber-400" : "text-teal-400"}`}>
                    {isPositive ? "+" : ""}{peakDelta.toFixed(3)}{meta.unit}
                  </span>
                  <div className="text-[9px] text-gray-600">peak @T+{peakHour}h</div>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={44}>
                <AreaChart data={chartData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id={`ga-${metric}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id={`gb-${metric}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6b7280" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#6b7280" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area type="monotone" dataKey="b" stroke="#4b5563" strokeWidth={1} fill={`url(#gb-${metric})`} dot={false} strokeDasharray="3 3" />
                  <Area type="monotone" dataKey="a" stroke="#f59e0b" strokeWidth={1.5} fill={`url(#ga-${metric})`} dot={false} />
                  <Tooltip
                    contentStyle={{ background: "#111827", border: "1px solid #374151", fontSize: 9, padding: "4px 8px" }}
                    formatter={(v: number, name: string) => [v.toFixed(3), name === "a" ? "With event" : "Baseline"]}
                    labelFormatter={(l) => `T+${l}h`}
                  />
                </AreaChart>
              </ResponsiveContainer>

              {/* Delta bar */}
              <div className="mt-1.5 flex items-center gap-2">
                <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${Math.min(100, (peakDelta / (Math.abs(aVals[0] ?? 1) * 0.5)) * 100)}%`,
                      background: isPositive ? "#f59e0b" : "#14b8a6",
                    }}
                  />
                </div>
                <div className="flex gap-2 text-[9px]">
                  <span className="flex items-center gap-0.5 text-amber-500">
                    <span className="w-2 h-0.5 bg-amber-500 inline-block" /> With event
                  </span>
                  <span className="flex items-center gap-0.5 text-gray-500">
                    <span className="w-2 h-0.5 bg-gray-500 inline-block border-dashed" /> Baseline
                  </span>
                </div>
              </div>
            </div>
          );
        })}

        {/* Summary */}
        <div className="bg-gradient-to-r from-violet-900/20 to-teal-900/20 rounded-lg p-2.5 border border-violet-800/20 text-[10px] text-gray-400 space-y-1">
          <div className="flex items-center gap-1.5 text-gray-300 font-medium">
            <svg className="w-3 h-3 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Causal Summary
          </div>
          <p>{significant.length} of {metrics.length} metrics deviated significantly</p>
          <p>Chain depth: {counterfactual.causal_edges.length} edges</p>
          {counterfactual.causal_edges.some((e) => e.refutation_passed) && (
            <p className="text-teal-500">Refutation tests passed</p>
          )}
        </div>
      </div>
    </div>
  );
}
