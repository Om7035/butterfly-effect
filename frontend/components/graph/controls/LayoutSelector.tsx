'use client';

import { useState } from 'react';
import { Network, Circle, LayoutGrid, Sparkles } from 'lucide-react';

interface LayoutSelectorProps {
  onLayoutChange: (layout: 'hierarchical' | 'radial' | 'grid' | 'force') => void;
  currentLayout?: string;
}

export default function LayoutSelector({ onLayoutChange, currentLayout = 'force' }: LayoutSelectorProps) {
  const [selected, setSelected] = useState(currentLayout);

  const layouts = [
    { id: 'hierarchical', icon: Network, label: 'Hierarchical', description: 'Top-down flow' },
    { id: 'radial', icon: Circle, label: 'Radial', description: 'Center-out' },
    { id: 'grid', icon: LayoutGrid, label: 'Grid', description: 'Aligned' },
    { id: 'force', icon: Sparkles, label: 'Freeform', description: 'Manual' },
  ];

  const handleSelect = (layoutId: string) => {
    setSelected(layoutId);
    onLayoutChange(layoutId as any);
  };

  return (
    <div style={{
      background: 'white',
      borderRadius: '12px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      border: '1px solid #e0e0e0',
      padding: '12px',
      minWidth: '200px',
    }}>
      <div style={{
        fontSize: '12px',
        fontWeight: '600',
        color: '#666',
        marginBottom: '8px',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}>
        Layout
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {layouts.map((layout) => {
          const Icon = layout.icon;
          const isSelected = selected === layout.id;
          
          return (
            <button
              key={layout.id}
              onClick={() => handleSelect(layout.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 12px',
                border: 'none',
                background: isSelected ? '#f0f0f0' : 'transparent',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                textAlign: 'left',
              }}
              onMouseEnter={(e) => {
                if (!isSelected) e.currentTarget.style.background = '#f8f8f8';
              }}
              onMouseLeave={(e) => {
                if (!isSelected) e.currentTarget.style.background = 'transparent';
              }}
            >
              <Icon size={18} color={isSelected ? '#333' : '#666'} />
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: '13px',
                  fontWeight: isSelected ? '600' : '500',
                  color: isSelected ? '#333' : '#666',
                }}>
                  {layout.label}
                </div>
                <div style={{
                  fontSize: '11px',
                  color: '#999',
                }}>
                  {layout.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
