'use client';
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { getDomainIcon } from '@/lib/domainIcons';

interface MetricNodeData {
  name: string;
  domain?: string;
  value?: number;
  delta?: number;
  unit?: string;
  // Impact fields from backend
  hop?: number;            // 1, 2, 3 — causal distance from root
  confidence?: number;     // 0-1 — how certain this effect is
  strength?: number;       // 0-1 — edge strength from parent
  fred_series?: string;    // e.g. "FEDFUNDS" — real FRED data
  fred_date?: string;
  source?: string;         // "nlp" if NLP-extracted
  dimmed?: boolean;         // true when a source-tag filter excludes this node
}

// Confidence → border color
function confColor(c: number): string {
  if (c > 0.75) return '#34d399';  // green — high confidence
  if (c > 0.5)  return '#60a5fa';  // blue — medium
  if (c > 0.3)  return '#fbbf24';  // amber — low
  return '#f87171';                 // red — very low
}

// Hop → impact label
const HOP_LABEL: Record<number, string> = {
  1: '1st order',
  2: '2nd order',
  3: '3rd order',
  4: '4th order',
};

// Hop → label color
const HOP_COLOR: Record<number, string> = {
  1: '#34d399',
  2: '#60a5fa',
  3: '#a78bfa',
  4: '#fbbf24',
};

// Mini sparkline — 8 bars showing simulated cascade buildup
function Sparkline({ hop, strength }: { hop: number; strength: number }) {
  const bars = 8;
  // Simulate: effect builds up then decays based on hop and strength
  const heights = Array.from({ length: bars }, (_, i) => {
    const peak = Math.floor(bars * 0.4);
    if (i < peak) return (i / peak) * strength;
    return strength * Math.exp(-0.3 * (i - peak));
  });
  const max = Math.max(...heights, 0.01);

  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1px', height: '18px', marginTop: '6px' }}>
      {heights.map((h, i) => (
        <div key={i} style={{
          flex: 1,
          height: `${Math.max(2, (h / max) * 18)}px`,
          background: i === Math.floor(bars * 0.4)
            ? confColor(strength)
            : `${confColor(strength)}55`,
          borderRadius: '1px',
          transition: 'height 0.3s ease',
        }} />
      ))}
    </div>
  );
}

function MetricNode({ data, selected }: NodeProps<MetricNodeData>) {
  const isUp = (data.delta ?? 0) > 0;
  const isDown = (data.delta ?? 0) < 0;
  const deltaColor = isUp ? '#34d399' : isDown ? '#f87171' : '#94a3b8';
  const deltaSymbol = isUp ? '↑' : isDown ? '↓' : '→';

  const hop = data.hop ?? 1;
  const conf = data.confidence ?? data.strength ?? 0.7;
  const borderColor = confColor(conf);
  const hopLabel = HOP_LABEL[hop] || `${hop}th order`;
  const hopColor = HOP_COLOR[hop] || '#94a3b8';
  const hasFred = !!data.fred_series;
  const DomainIcon = getDomainIcon(data.domain);

  return (
    <div title={data.name} style={{
      background: selected ? 'rgba(6,78,59,0.9)' : 'rgba(15,23,42,0.88)',
      border: `1px solid ${selected ? borderColor : `${borderColor}44`}`,
      borderLeft: `3px solid ${borderColor}`,
      borderRadius: '10px', padding: '10px 14px', minWidth: '170px', maxWidth: '220px',
      backdropFilter: 'blur(8px)',
      boxShadow: selected
        ? `0 0 20px ${borderColor}33, inset 0 1px 0 rgba(255,255,255,0.05)`
        : '0 4px 16px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03)',
      cursor: 'pointer', transition: 'all 0.2s ease, opacity 0.2s',
      opacity: data.dimmed ? 0.2 : 1,
    }}>
      <Handle type="target" position={Position.Left}
        style={{ background: borderColor, width: 7, height: 7, border: '2px solid #0f172a' }} />

      {/* Header row: icon + name + hop badge */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '4px', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', flex: 1 }}>
          <DomainIcon size={13} color="#6ee7b7" style={{ flexShrink: 0, marginTop: '1px' }} />
          <div style={{ fontSize: '10px', color: '#6ee7b7', fontWeight: '600', lineHeight: 1.4 }}>
            {data.name}
          </div>
        </div>
        <span style={{
          fontSize: '7px', fontWeight: '700', color: hopColor,
          background: `${hopColor}18`, border: `1px solid ${hopColor}44`,
          padding: '1px 5px', borderRadius: '3px',
          letterSpacing: '0.04em', flexShrink: 0, marginTop: '1px',
        }}>
          {hopLabel}
        </span>
      </div>

      {/* FRED live value OR simulated value */}
      {data.value !== undefined ? (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
          <span style={{ fontSize: '20px', fontWeight: '700', color: '#ecfdf5', fontFamily: 'monospace', lineHeight: 1 }}>
            {typeof data.value === 'number' ? data.value.toFixed(data.value > 100 ? 0 : 2) : data.value}
          </span>
          {data.unit && <span style={{ fontSize: '10px', color: '#6ee7b7' }}>{data.unit}</span>}
          {hasFred && (
            <span style={{ fontSize: '7px', color: '#34d399', background: 'rgba(52,211,153,0.1)', padding: '1px 4px', borderRadius: '3px', marginLeft: '2px' }}>
              LIVE
            </span>
          )}
        </div>
      ) : (
        // No real value — show impact magnitude bar instead
        <div style={{ marginTop: '2px' }}>
          <div style={{ fontSize: '9px', color: '#475569', marginBottom: '3px' }}>impact magnitude</div>
          <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${conf * 100}%`,
              background: `linear-gradient(90deg, ${borderColor}88, ${borderColor})`,
              borderRadius: '2px',
              transition: 'width 0.6s ease',
            }} />
          </div>
          <div style={{ fontSize: '8px', color: '#475569', marginTop: '2px', fontFamily: 'monospace' }}>
            {Math.round(conf * 100)}% confidence
          </div>
        </div>
      )}

      {/* Delta */}
      {data.delta !== undefined && (
        <div style={{ fontSize: '11px', color: deltaColor, fontWeight: '600', marginTop: '3px', fontFamily: 'monospace' }}>
          {deltaSymbol} {data.delta > 0 ? '+' : ''}{data.delta.toFixed(Math.abs(data.delta) > 100 ? 0 : 2)}
          {data.unit && <span style={{ fontSize: '9px', marginLeft: '2px' }}>{data.unit}</span>}
        </div>
      )}

      {/* Sparkline — shows cascade buildup shape */}
      <Sparkline hop={hop} strength={conf} />

      {/* FRED date */}
      {hasFred && data.fred_date && (
        <div style={{ fontSize: '8px', color: '#334155', marginTop: '4px', fontFamily: 'monospace' }}>
          {data.fred_series} · {data.fred_date}
        </div>
      )}

      <Handle type="source" position={Position.Right}
        style={{ background: borderColor, width: 7, height: 7, border: '2px solid #0f172a' }} />
    </div>
  );
}

export default memo(MetricNode);
