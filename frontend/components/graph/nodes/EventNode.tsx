'use client';
import { memo, useEffect, useRef } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface EventNodeData {
  title: string;
  description?: string;
  timestamp?: string;
}

function EventNode({ data, selected }: NodeProps<EventNodeData>) {
  const pulseRef = useRef<SVGCircleElement>(null);

  return (
    <div style={{ position: 'relative' }}>
      {/* Outer pulse ring */}
      <div style={{
        position: 'absolute',
        inset: '-8px',
        borderRadius: '50%',
        border: '1px solid rgba(124,58,237,0.4)',
        animation: 'pulse-ring 2.5s ease-out infinite',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute',
        inset: '-16px',
        borderRadius: '50%',
        border: '1px solid rgba(124,58,237,0.15)',
        animation: 'pulse-ring 2.5s ease-out infinite 0.6s',
        pointerEvents: 'none',
      }} />

      {/* Core node */}
      <div style={{
        width: '64px',
        height: '64px',
        borderRadius: '50%',
        background: selected
          ? 'radial-gradient(circle at 35% 35%, #a78bfa, #7c3aed)'
          : 'radial-gradient(circle at 35% 35%, #6d28d9, #4c1d95)',
        boxShadow: selected
          ? '0 0 0 2px #7c3aed, 0 0 24px rgba(124,58,237,0.6)'
          : '0 0 0 1px rgba(124,58,237,0.5), 0 0 16px rgba(124,58,237,0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        fontSize: '22px',
      }}>
        🦋
      </div>

      {/* Label below */}
      <div style={{
        position: 'absolute',
        top: '72px',
        left: '50%',
        transform: 'translateX(-50%)',
        whiteSpace: 'nowrap',
        textAlign: 'center',
      }}>
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          color: '#e2e8f0',
          letterSpacing: '0.02em',
          maxWidth: '140px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {data.title}
        </div>
        {data.timestamp && (
          <div style={{ fontSize: '9px', color: '#7c3aed', marginTop: '2px', fontFamily: 'monospace' }}>
            {data.timestamp}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right}
        style={{ background: '#7c3aed', width: 8, height: 8, border: '2px solid #1e1b4b' }} />
      <Handle type="target" position={Position.Left}
        style={{ background: '#7c3aed', width: 8, height: 8, border: '2px solid #1e1b4b' }} />
    </div>
  );
}

export default memo(EventNode);
