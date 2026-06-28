"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

// Event Node - root event with pulsing border
export const EventNode = memo(({ data }: NodeProps) => {
  return (
    <div className="relative">
      <div className="absolute inset-0 bg-violet-600/20 rounded-lg animate-pulse" />
      <div className="relative px-4 py-3 bg-gray-900 border-2 border-violet-600 rounded-lg shadow-lg min-w-[180px]">
        <div className="text-xs text-violet-400 font-medium mb-1">EVENT</div>
        <div className="text-sm text-gray-100 font-medium">{String(data.label)}</div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-violet-600" />
    </div>
  );
});
EventNode.displayName = "EventNode";

// Actor Node - entities like nations, orgs, people
export const ActorNode = memo(({ data }: NodeProps) => {
  return (
    <div className="relative">
      <div className="px-4 py-3 bg-gray-900 border border-emerald-600/50 rounded-lg shadow-lg min-w-[160px]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-emerald-600/20 flex items-center justify-center">
            <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div className="flex-1">
            <div className="text-xs text-emerald-400 font-medium">ENTITY</div>
            <div className="text-sm text-gray-100">{String(data.label)}</div>
          </div>
        </div>
      </div>
      <Handle type="target" position={Position.Top} className="!bg-emerald-600" />
      <Handle type="source" position={Position.Bottom} className="!bg-emerald-600" />
    </div>
  );
});
ActorNode.displayName = "ActorNode";

// Metric Node - shows data with sparkline
export const MetricNode = memo(({ data }: NodeProps) => {
  return (
    <div className="relative">
      <div className="px-4 py-3 bg-gray-900 border border-blue-600/50 rounded-lg shadow-lg min-w-[160px]">
        <div className="text-xs text-blue-400 font-medium mb-1">METRIC</div>
        <div className="text-sm text-gray-100 font-medium mb-2">{String(data.label)}</div>
        {/* Simple sparkline placeholder */}
        <div className="h-6 flex items-end gap-0.5">
          {[3, 5, 4, 6, 8, 7, 9, 8, 10, 9].map((h, i) => (
            <div
              key={i}
              className="flex-1 bg-blue-500/30 rounded-t"
              style={{ height: `${h * 10}%` }}
            />
          ))}
        </div>
      </div>
      <Handle type="target" position={Position.Top} className="!bg-blue-600" />
      <Handle type="source" position={Position.Bottom} className="!bg-blue-600" />
    </div>
  );
});
MetricNode.displayName = "MetricNode";

// Insight Node - sticky note style
export const InsightNode = memo(({ data }: NodeProps) => {
  return (
    <div className="relative">
      <div className="px-4 py-3 bg-amber-900/20 border border-amber-600/50 rounded-lg shadow-lg min-w-[160px] transform rotate-1">
        <div className="text-xs text-amber-400 font-medium mb-1">POLICY</div>
        <div className="text-sm text-gray-100">{String(data.label)}</div>
      </div>
      <Handle type="target" position={Position.Top} className="!bg-amber-600" />
      <Handle type="source" position={Position.Bottom} className="!bg-amber-600" />
    </div>
  );
});
InsightNode.displayName = "InsightNode";
