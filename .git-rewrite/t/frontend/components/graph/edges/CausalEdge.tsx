'use client';
import { memo, useEffect, useRef } from 'react';
import { EdgeProps, getBezierPath, EdgeLabelRenderer } from 'reactflow';

interface CausalEdgeData {
  strength?: number;
  confidence?: number;
  latency?: number;
}

// Confidence → color
function edgeColor(confidence: number): string {
  if (confidence > 0.8) return '#34d399'; // emerald
  if (confidence > 0.6) return '#60a5fa'; // blue
  if (confidence > 0.4) return '#fbbf24'; // amber
  return '#f87171';                        // red
}

function CausalEdge({
  id,
  sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition,
  data, markerEnd, selected,
}: EdgeProps<CausalEdgeData>) {
  const dotRef = useRef<SVGCircleElement>(null);
  const animRef = useRef<number>(0);
  const progressRef = useRef(Math.random()); // stagger start

  const confidence = data?.confidence ?? 0.7;
  const strength = data?.strength ?? 0.5;
  const latency = data?.latency;
  const color = edgeColor(confidence);
  const strokeW = 1 + strength * 2.5;

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });

  // Animate a dot along the path
  useEffect(() => {
    const dot = dotRef.current;
    if (!dot) return;

    // Get the path element by id
    const pathEl = document.getElementById(`edge-path-${id}`) as SVGPathElement | null;
    if (!pathEl) return;

    const speed = 0.0008 + confidence * 0.0006; // faster = more confident

    const tick = () => {
      progressRef.current = (progressRef.current + speed) % 1;
      const len = pathEl.getTotalLength();
      const pt = pathEl.getPointAtLength(progressRef.current * len);
      dot.setAttribute('cx', String(pt.x));
      dot.setAttribute('cy', String(pt.y));
      animRef.current = requestAnimationFrame(tick);
    };

    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [id, confidence]);

  return (
    <>
      {/* Ghost track */}
      <path
        id={`edge-path-${id}`}
        d={edgePath}
        fill="none"
        stroke={`${color}18`}
        strokeWidth={strokeW + 2}
      />

      {/* Main edge line */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        fill="none"
        stroke={selected ? color : `${color}66`}
        strokeWidth={selected ? strokeW + 1 : strokeW}
        markerEnd={markerEnd}
        style={{ transition: 'stroke 0.2s, stroke-width 0.2s' }}
      />

      {/* Travelling signal dot */}
      <circle
        ref={dotRef}
        r={2.5 + strength * 1.5}
        fill={color}
        style={{
          filter: `drop-shadow(0 0 4px ${color})`,
          pointerEvents: 'none',
        }}
      />

      {/* Latency label */}
      {latency !== undefined && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan"
            style={{
              position: 'absolute',
              transform: `translate(-50%,-50%) translate(${labelX}px,${labelY}px)`,
              background: 'rgba(15,23,42,0.9)',
              border: `1px solid ${color}44`,
              borderRadius: '6px',
              padding: '2px 7px',
              fontSize: '9px',
              fontWeight: '700',
              color,
              fontFamily: 'monospace',
              letterSpacing: '0.04em',
              backdropFilter: 'blur(4px)',
              pointerEvents: 'none',
            }}
          >
            {latency}h
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export default memo(CausalEdge);
