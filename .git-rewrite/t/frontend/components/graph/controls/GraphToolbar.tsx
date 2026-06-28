'use client';

import { useReactFlow } from 'reactflow';

interface GraphToolbarProps {
  onLayoutChange: (layout: 'hierarchical' | 'radial' | 'grid' | 'force') => void;
}

const BTN = {
  background: 'none',
  border: 'none',
  color: '#64748b',
  cursor: 'pointer',
  padding: '7px 10px',
  borderRadius: '6px',
  fontSize: '11px',
  fontWeight: '600',
  transition: 'all 0.15s',
  letterSpacing: '0.02em',
  display: 'flex',
  alignItems: 'center',
  gap: '5px',
} as const;

export default function GraphToolbar({ onLayoutChange }: GraphToolbarProps) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();

  return (
    <div style={{
      position: 'absolute',
      top: '16px',
      right: '16px',
      background: 'rgba(15,23,42,0.9)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '10px',
      padding: '6px',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
      zIndex: 10,
    }}>
      {/* Zoom */}
      {[
        { label: '+', title: 'Zoom in',  fn: () => zoomIn() },
        { label: '−', title: 'Zoom out', fn: () => zoomOut() },
        { label: '⊡', title: 'Fit view', fn: () => fitView({ padding: 0.25, duration: 600 }) },
      ].map(({ label, title, fn }) => (
        <button key={title} title={title} onClick={fn} style={BTN}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = '#e2e8f0'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = '#64748b'; }}
        >
          {label}
        </button>
      ))}

      <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)', margin: '2px 0' }} />

      {/* Layouts */}
      {[
        { label: '⬇ Tree',   title: 'Hierarchical layout', layout: 'hierarchical' as const },
        { label: '◎ Radial', title: 'Radial layout',       layout: 'radial' as const },
        { label: '⊞ Grid',   title: 'Grid layout',         layout: 'grid' as const },
      ].map(({ label, title, layout }) => (
        <button key={layout} title={title} onClick={() => onLayoutChange(layout)} style={BTN}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = '#e2e8f0'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = '#64748b'; }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
