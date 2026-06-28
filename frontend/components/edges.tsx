"use client";

import { memo } from "react";
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
} from "@xyflow/react";

export const CausalEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // Color by confidence
  const confidence = (data?.confidence as number[] | undefined)?.[0] ?? 0.5;
  const color =
    confidence > 0.7
      ? "#10b981" // green
      : confidence > 0.5
      ? "#f59e0b" // amber
      : "#ef4444"; // red

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth: 2,
          strokeDasharray: data?.relationship === "CORRELATES_WITH" ? "5,5" : undefined,
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
          className="nodrag nopan"
        >
          <div className="px-2 py-1 bg-gray-900 border border-gray-800 rounded text-xs text-gray-400 whitespace-nowrap">
            {(data?.relationship as string) || "CAUSES"} · {(data?.latency as number) || 0}h
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  );
});
CausalEdge.displayName = "CausalEdge";
