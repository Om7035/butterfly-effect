'use client';
import { memo } from 'react';
import { EdgeProps, getBezierPath } from 'reactflow';

function InfluenceEdge({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, markerEnd,
}: EdgeProps) {
  const [edgePath] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });

  return (
    <path
      id={id}
      className="react-flow__edge-path"
      d={edgePath}
      fill="none"
      stroke="rgba(251,191,36,0.35)"
      strokeWidth={1.5}
      strokeDasharray="4 4"
      markerEnd={markerEnd}
    />
  );
}

export default memo(InfluenceEdge);
