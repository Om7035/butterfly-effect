'use client';
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface PolicyNodeData {
  name: string;
  status?: 'active' | 'pending' | 'inactive';
}

const STATUS_COLOR: Record<string, string> = {
  active: '#a78bfa',
  pending: '#fbbf24',
  inactive: '#475569',
};

function PolicyNode({ data, selected }: NodeProps<PolicyNodeData>) {
  const color = STATUS_COLOR[data.status || 'active'];

  return (
    <div style={{
      background: selected ? 'rgba(46,16,101,0.9)' : 'rgba(15,23,42,0.85)',
      border: `1px solid ${selected ? `${color}99` : `${color}33`}`,
      borderRadius: '20px',
      padding: '8px 16px',
      backdropFilter: 'blur(8px)',
      boxShadow: selected
        ? `0 0 20px ${color}33, inset 0 1px 0 rgba(255,255,255,0.05)`
        : '0 4px 16px rgba(0,0,0,0.4)',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      whiteSpace: 'nowrap',
    }}>
      <Handle type="target" position={Position.Left}
        style={{ background: color, width: 7, height: 7, border: '2px solid #0f172a' }} />

      <div style={{
        width: '6px', height: '6px', borderRadius: '50%',
        background: color,
        boxShadow: `0 0 6px ${color}`,
        animation: data.status === 'active' ? 'blink 2s ease-in-out infinite' : 'none',
        flexShrink: 0,
      }} />

      <span style={{ fontSize: '11px', fontWeight: '600', color: '#e2e8f0' }}>
        {data.name}
      </span>

      <Handle type="source" position={Position.Right}
        style={{ background: color, width: 7, height: 7, border: '2px solid #0f172a' }} />
    </div>
  );
}

export default memo(PolicyNode);
