'use client';
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { getDomainIcon, graphConfidenceColor } from '@/lib/domainIcons';

interface PolicyNodeData {
  name: string;
  domain?: string;
  status?: 'active' | 'pending' | 'inactive';
  // Impact fields
  hop?: number;
  confidence?: number;
  strength?: number;
  dimmed?: boolean;   // true when a source-tag filter excludes this node
}

const STATUS_COLOR: Record<string, string> = {
  active:   '#a78bfa',
  pending:  '#fbbf24',
  inactive: '#475569',
};

const HOP_LABEL: Record<number, string> = {
  1: '1st', 2: '2nd', 3: '3rd', 4: '4th',
};

function PolicyNode({ data, selected }: NodeProps<PolicyNodeData>) {
  const color = STATUS_COLOR[data.status || 'active'];
  const hop = data.hop ?? 2;
  const conf = data.confidence ?? data.strength ?? 0.6;
  const hopLabel = HOP_LABEL[hop] ? `${HOP_LABEL[hop]} order` : `${hop}th order`;
  const confColor = graphConfidenceColor(conf);
  const DomainIcon = getDomainIcon(data.domain);

  return (
    <div title={data.name} style={{
      background: selected ? 'rgba(46,16,101,0.95)' : 'rgba(15,23,42,0.88)',
      border: `1px solid ${selected ? `${color}cc` : `${color}44`}`,
      borderLeft: `3px solid ${confColor}`,
      borderRadius: '6px 14px 14px 6px', padding: '8px 14px',
      backdropFilter: 'blur(8px)',
      boxShadow: selected
        ? `0 0 20px ${color}44, inset 0 1px 0 rgba(255,255,255,0.05)`
        : '0 4px 16px rgba(0,0,0,0.4)',
      cursor: 'pointer', transition: 'all 0.2s ease, opacity 0.2s',
      display: 'flex', alignItems: 'center', gap: '8px', minWidth: '170px', maxWidth: '230px',
      opacity: data.dimmed ? 0.2 : 1,
    }}>
      <Handle type="target" position={Position.Left}
        style={{ background: color, width: 7, height: 7, border: '2px solid #0f172a' }} />

      <DomainIcon size={13} color={color} style={{ flexShrink: 0 }} />

      {/* Status dot */}
      <div style={{
        width: '6px', height: '6px', borderRadius: '50%',
        background: color, boxShadow: `0 0 ${Math.round(conf * 8)}px ${color}`,
        animation: data.status === 'active' ? 'blink 2s ease-in-out infinite' : 'none',
        flexShrink: 0,
      }} />

      {/* Name — full text, wraps instead of truncating */}
      <span style={{
        fontSize: '11px', fontWeight: '600', color: '#e2e8f0', lineHeight: 1.4, flex: 1,
      }}>
        {data.name}
      </span>

      {/* Hop badge */}
      <span style={{
        fontSize: '7px', fontWeight: '700',
        color: color,
        background: `${color}18`,
        border: `1px solid ${color}44`,
        padding: '1px 5px', borderRadius: '10px',
        letterSpacing: '0.04em', flexShrink: 0,
      }}>
        {hopLabel}
      </span>

      <Handle type="source" position={Position.Right}
        style={{ background: color, width: 7, height: 7, border: '2px solid #0f172a' }} />
    </div>
  );
}

export default memo(PolicyNode);
