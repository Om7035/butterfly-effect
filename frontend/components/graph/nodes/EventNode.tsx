'use client';
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface EventNodeData {
  title: string;
  description?: string;
  timestamp?: string;
  // Impact fields from backend
  severity?: string;       // minor | moderate | major | catastrophic
  confidence?: number;     // 0-1
  hop?: number;            // always 0 for root
}

// Severity → ring color
const SEVERITY_COLOR: Record<string, string> = {
  catastrophic: '#ef4444',
  major:        '#f59e0b',
  moderate:     '#7c3aed',
  minor:        '#3b82f6',
};

function EventNode({ data, selected }: NodeProps<EventNodeData>) {
  const severityColor = SEVERITY_COLOR[data.severity || 'moderate'];
  const severityLabel = data.severity ? data.severity.toUpperCase() : null;

  return (
    <div style={{ position: 'relative' }}>
      {/* Outer pulse rings — color reflects severity */}
      <div style={{
        position: 'absolute', inset: '-8px', borderRadius: '50%',
        border: `1px solid ${severityColor}66`,
        animation: 'pulse-ring 2.5s ease-out infinite',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', inset: '-16px', borderRadius: '50%',
        border: `1px solid ${severityColor}22`,
        animation: 'pulse-ring 2.5s ease-out infinite 0.6s',
        pointerEvents: 'none',
      }} />

      {/* Core circle */}
      <div style={{
        width: '64px', height: '64px', borderRadius: '50%',
        background: selected
          ? `radial-gradient(circle at 35% 35%, ${severityColor}cc, ${severityColor}88)`
          : `radial-gradient(circle at 35% 35%, ${severityColor}99, ${severityColor}55)`,
        boxShadow: selected
          ? `0 0 0 2px ${severityColor}, 0 0 28px ${severityColor}88`
          : `0 0 0 1px ${severityColor}66, 0 0 16px ${severityColor}44`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer', transition: 'all 0.2s ease', fontSize: '22px',
      }}>
        🦋
      </div>

      {/* Severity badge — top right of circle */}
      {severityLabel && (
        <div style={{
          position: 'absolute', top: '-4px', right: '-4px',
          background: severityColor,
          color: '#fff',
          fontSize: '7px', fontWeight: '800',
          padding: '2px 5px', borderRadius: '4px',
          letterSpacing: '0.06em',
          boxShadow: `0 0 8px ${severityColor}88`,
        }}>
          {severityLabel}
        </div>
      )}

      {/* Label below */}
      <div style={{
        position: 'absolute', top: '72px', left: '50%',
        transform: 'translateX(-50%)', textAlign: 'center', width: '160px',
      }}>
        <div style={{
          fontSize: '11px', fontWeight: '700', color: '#e2e8f0',
          letterSpacing: '0.02em', lineHeight: 1.4,
          wordBreak: 'break-word', whiteSpace: 'normal',
        }}>
          {data.title}
        </div>
        {data.timestamp && (
          <div style={{ fontSize: '9px', color: '#7c3aed', marginTop: '2px', fontFamily: 'monospace' }}>
            {data.timestamp}
          </div>
        )}
        <div style={{
          fontSize: '8px', color: '#475569', marginTop: '2px',
          textTransform: 'uppercase', letterSpacing: '0.1em',
        }}>
          root event
        </div>
      </div>

      <Handle type="source" position={Position.Right}
        style={{ background: severityColor, width: 8, height: 8, border: '2px solid #1e1b4b' }} />
      <Handle type="target" position={Position.Left}
        style={{ background: severityColor, width: 8, height: 8, border: '2px solid #1e1b4b' }} />
    </div>
  );
}

export default memo(EventNode);
