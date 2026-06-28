'use client';
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { getDomainIcon, graphConfidenceColor } from '@/lib/domainIcons';

interface EntityNodeData {
  name: string;
  type?: string;
  domain?: string;
  confidence?: number;
  strength?: number;
  entityType?: 'company' | 'person' | 'sector';
  // Impact fields
  hop?: number;
  source?: string;   // "nlp" if NLP-extracted
  dimmed?: boolean;   // true when a source-tag filter excludes this node
}

// Hop → impact ring color
const HOP_RING: Record<number, string> = {
  1: 'rgba(52,211,153,0.5)',
  2: 'rgba(96,165,250,0.5)',
  3: 'rgba(167,139,250,0.5)',
  4: 'rgba(251,191,36,0.5)',
};

// Hop → label
const HOP_LABEL: Record<number, { text: string; color: string }> = {
  1: { text: '1st order', color: '#34d399' },
  2: { text: '2nd order', color: '#60a5fa' },
  3: { text: '3rd order', color: '#a78bfa' },
  4: { text: '4th order', color: '#fbbf24' },
};

function EntityNode({ data, selected }: NodeProps<EntityNodeData>) {
  const DomainIcon = getDomainIcon(data.domain);
  const conf = data.confidence ?? data.strength ?? 0.7;
  const hop = data.hop ?? 2;
  const ringColor = HOP_RING[hop] || 'rgba(96,165,250,0.3)';
  const hopInfo = HOP_LABEL[hop] || { text: `${hop}th order`, color: '#94a3b8' };
  const isNlp = data.source === 'nlp';
  const confColor = graphConfidenceColor(conf);
  const borderColor = `rgba(96,165,250,${conf * 0.8})`;

  return (
    <div style={{ position: 'relative', opacity: data.dimmed ? 0.2 : 1, transition: 'opacity 0.2s' }}>
      {/* Impact ring — size reflects hop depth */}
      {selected && (
        <div style={{
          position: 'absolute',
          inset: `${-4 - hop * 2}px`,
          borderRadius: '12px',
          border: `1px solid ${ringColor}`,
          pointerEvents: 'none',
          animation: 'pulse-ring 2s ease-out infinite',
        }} />
      )}

      <div title={data.name} style={{
        background: selected ? 'rgba(30,58,138,0.95)' : 'rgba(15,23,42,0.88)',
        border: `1px solid ${selected ? borderColor : `rgba(96,165,250,${conf * 0.3})`}`,
        borderLeft: `3px solid ${confColor}`,
        borderRadius: '10px', padding: '10px 14px', minWidth: '170px', maxWidth: '220px',
        backdropFilter: 'blur(8px)',
        boxShadow: selected
          ? `0 0 20px rgba(96,165,250,${conf * 0.4}), inset 0 1px 0 rgba(255,255,255,0.05)`
          : '0 4px 16px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03)',
        cursor: 'pointer', transition: 'all 0.2s ease',
      }}>
        <Handle type="target" position={Position.Left}
          style={{ background: '#3b82f6', width: 7, height: 7, border: '2px solid #0f172a' }} />

        {/* Icon + name row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '5px' }}>
          <DomainIcon size={14} color="#93c5fd" style={{ flexShrink: 0, marginTop: '1px' }} />
          <span style={{ fontSize: '11px', fontWeight: '600', color: '#93c5fd', letterSpacing: '0.02em', flex: 1, lineHeight: 1.4 }}>
            {data.name}
          </span>
          {isNlp && (
            <span style={{ fontSize: '7px', color: '#a78bfa', background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.3)', padding: '1px 4px', borderRadius: '3px', flexShrink: 0, marginTop: '1px' }}>
              NLP
            </span>
          )}
        </div>

        {/* Type + hop order row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          {data.type && (
            <div style={{ fontSize: '8px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              {data.type}
            </div>
          )}
          <span style={{
            fontSize: '7px', fontWeight: '700',
            color: hopInfo.color,
            background: `${hopInfo.color}18`,
            border: `1px solid ${hopInfo.color}44`,
            padding: '1px 5px', borderRadius: '3px',
            letterSpacing: '0.04em',
          }}>
            {hopInfo.text}
          </span>
        </div>

        {/* Confidence — communicated by the left border; number kept for precision */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ fontSize: '8px', color: '#334155' }}>causal confidence</span>
          <span style={{ fontSize: '10px', color: confColor, fontFamily: 'monospace', fontWeight: '600' }}>
            {Math.round(conf * 100)}%
          </span>
        </div>

        <Handle type="source" position={Position.Right}
          style={{ background: '#3b82f6', width: 7, height: 7, border: '2px solid #0f172a' }} />
      </div>
    </div>
  );
}

export default memo(EntityNode);
