import React from 'react';
import { boardProblems } from '../services/boardWork';

// Under a group's You Do: the worksheet's required problems, ready to copy to the board (asked on the click-through: where are the 6 board problems?).
export default function BoardWork({ plan, group, domain }) {
  const b = boardProblems(plan, group, domain);
  if (!b) return null;
  return (
    <div data-testid={`board-work-${group}`} style={{ marginTop: 8, padding: '6px 8px', background: 'var(--bg-secondary, #f4f6f2)', borderRadius: 6, fontSize: '0.85rem' }}>
      <div style={{ fontWeight: 600 }}>
        📝 बोर्ड पर लिखें (सवाल 1–{b.required})
        <span className="en" lang="en" style={{ fontSize: '0.75rem' }}>Copy to the board: problems 1–{b.required} of the worksheet</span>
      </div>
      <div style={{ marginTop: 2, display: 'grid', gridTemplateColumns: 'repeat(3, max-content)', columnGap: 18, rowGap: 2 }}>
        {b.items.map((t, i) => (<div key={i} data-testid="board-problem" style={{ whiteSpace: 'nowrap' }}>{i + 1}. {t}</div>))}
      </div>
    </div>
  );
}
