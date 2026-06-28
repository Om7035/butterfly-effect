'use client';
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface EntityNodeData {
  name: string;
  type?: string;
  confidence?: number;
  entityType?: 'company' | 'person' | 'sector';
}

const ICONS: Record<string, string> = {
  company: '🏛',
  person: '👤',
  sector: '⚙️',
};

function EntityNode({ data, selected }: NodeProps<EntityNodeData>) {
  const icon = ICONS[data.entityType || 'company'] || '🏛';
  const conf = data.confidence ?? 0.8;

  return (
    <div style={{
      background: selected ? 'rgba(30,58,138,0.9)' : 'rgba(15,23,42,0.85)',
      border: `1px solid ${selected ? 'rgba(96,165,250,0.8)' : 'rgba(96,165,250,0.25)'}`,
      borderRadius: '10px',
      padding: '10px 14px',
      minWidth: '130px',
      backdropFilter: 'blur(8px)',
      boxShadow: selected
        ? '0 0 20px rgba(96,165,250,0.3), inset 0 1px 0 rgba(255,255,255,0.05)'
        : '0 4px 16px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03)',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
    }}>
      <Handle type="target" position={Position.Left}
        style={{ background: '#3b82f6', width: 7, height: 7, border: '2px solid #0f172a' }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
        <span style={{ fontSize: '16px' }}>{icon}</span>
        <span style={{ fontSize: '11px', fontWeight: '600', color: '#93c5fd', letterSpacing: '0.02em' }}>
          {data.name}
        </span>
      </div>

      {data.type && (
        <div style={{ fontSize: '9px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>
          {data.type}
        </div>
      )}

      {/* Confidence bar */}
      <div style={{ height: '2px', background: 'rgba(255,255,255,0.06)', borderRadius: '1px', overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${conf * 100}%`,
          background: 'linear-gradient(90deg, #3b82f6, #60a5fa)',
          transition: 'width 0.6s ease',
        }} />
      </div>

      <Handle type="source" position={Position.Right}
        style={{ background: '#3b82f6', width: 7, height: 7, border: '2px solid #0f172a' }} />
    </div>
  );
}

export default memo(EntityNode);
