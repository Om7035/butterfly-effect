'use client';
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface MetricNodeData {
  name: string;
  value?: number;
  delta?: number;
  unit?: string;
}

function MetricNode({ data, selected }: NodeProps<MetricNodeData>) {
  const isUp = (data.delta ?? 0) > 0;
  const isDown = (data.delta ?? 0) < 0;
  const deltaColor = isUp ? '#34d399' : isDown ? '#f87171' : '#94a3b8';
  const deltaSymbol = isUp ? '↑' : isDown ? '↓' : '→';

  return (
    <div style={{
      background: selected ? 'rgba(6,78,59,0.85)' : 'rgba(15,23,42,0.85)',
      border: `1px solid ${selected ? 'rgba(52,211,153,0.7)' : 'rgba(52,211,153,0.2)'}`,
      borderRadius: '10px',
      padding: '10px 14px',
      minWidth: '120px',
      backdropFilter: 'blur(8px)',
      boxShadow: selected
        ? '0 0 20px rgba(52,211,153,0.25), inset 0 1px 0 rgba(255,255,255,0.05)'
        : '0 4px 16px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03)',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
    }}>
      <Handle type="target" position={Position.Left}
        style={{ background: '#10b981', width: 7, height: 7, border: '2px solid #0f172a' }} />

      <div style={{ fontSize: '9px', color: '#6ee7b7', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>
        {data.name}
      </div>

      {data.value !== undefined && (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
          <span style={{ fontSize: '20px', fontWeight: '700', color: '#ecfdf5', fontFamily: 'monospace', lineHeight: 1 }}>
            {typeof data.value === 'number' ? data.value.toFixed(data.value > 100 ? 0 : 2) : data.value}
          </span>
          {data.unit && (
            <span style={{ fontSize: '10px', color: '#6ee7b7' }}>{data.unit}</span>
          )}
        </div>
      )}

      {data.delta !== undefined && (
        <div style={{ fontSize: '11px', color: deltaColor, fontWeight: '600', marginTop: '3px', fontFamily: 'monospace' }}>
          {deltaSymbol} {data.delta > 0 ? '+' : ''}{data.delta.toFixed(data.delta > 100 ? 0 : 2)}
          {data.unit && <span style={{ fontSize: '9px', marginLeft: '2px' }}>{data.unit}</span>}
        </div>
      )}

      <Handle type="source" position={Position.Right}
        style={{ background: '#10b981', width: 7, height: 7, border: '2px solid #0f172a' }} />
    </div>
  );
}

export default memo(MetricNode);
