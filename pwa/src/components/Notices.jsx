import React, { useEffect, useState } from 'react';
import { onNotify, SUCCESS_MS } from '../services/notify';

const COLORS = {
  success: { background: '#E4F4EA', border: '#9CC4A8', color: '#1B4D33' },
  error: { background: '#FCE4E1', border: '#E8A99F', color: '#7A1F14' },
  info: { background: '#E8EEF4', border: '#C9D6E3', color: '#26405A' },
};

/**
 * The messages from services/notify.js, at the top of the screen, over the page and never blocking it.
 * A success disappears after a few seconds; an error stays until the teacher taps it away (so it is never missed).
 */
export default function Notices() {
  const [items, setItems] = useState([]);
  const dismiss = (id) => setItems((list) => list.filter((n) => n.id !== id));

  useEffect(() => onNotify((n) => {
    setItems((list) => [...list.slice(-2), n]);           // at most three at once
    if (n.kind !== 'error') setTimeout(() => dismiss(n.id), SUCCESS_MS);
  }), []);

  if (!items.length) return null;
  return (
    <div data-testid="notices" style={{ position: 'fixed', top: 'calc(var(--safe-top) + 8px)', left: 12, right: 12, maxWidth: 456, margin: '0 auto', zIndex: 200, display: 'flex', flexDirection: 'column', gap: 6 }}>
      {items.map((n) => {
        const c = COLORS[n.kind] || COLORS.info;
        return (
          <div key={n.id} data-testid={`notice-${n.kind}`} role={n.kind === 'error' ? 'alert' : 'status'}
            style={{ display: 'flex', alignItems: 'flex-start', gap: 8, background: c.background, border: `1px solid ${c.border}`, color: c.color, borderRadius: 10, padding: '10px 12px', fontSize: '0.875rem', boxShadow: '0 2px 10px rgba(0,0,0,0.12)' }}>
            <span style={{ flex: 1, whiteSpace: 'pre-line', overflowWrap: 'anywhere' }}>{n.text}</span>
            <button type="button" onClick={() => dismiss(n.id)} aria-label="बंद करें (Close)"
              style={{ minWidth: 36, minHeight: 36, margin: '-8px -8px -8px 0', background: 'none', border: 'none', color: 'inherit', fontSize: '1.1rem', cursor: 'pointer' }}>✕</button>
          </div>
        );
      })}
    </div>
  );
}
