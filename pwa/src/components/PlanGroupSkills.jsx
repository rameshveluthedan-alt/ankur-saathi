import React from 'react';
import { groupSkillLines, GROUP_HI } from '../services/planSummary';

/**
 * The top right of the lesson screen: the date, and which skill each group is on (when they differ), with "पुनः शिक्षण (Re-teach)" against a group that is re-teaching.
 * When every group is on the same skill, that one skill is shown, as before, and a re-teach is still named.
 */
export default function PlanGroupSkills({ planDate, selectedId, groups, blocks }) {
  const s = groupSkillLines({ groups, blocks, selectedId });
  const tag = { marginLeft: 4, color: 'var(--reteach)', fontWeight: 600 };
  return (
    <div style={{ textAlign: 'right', fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.4 }} data-testid="plan-group-skills">
      <div>{planDate}{!s.differ && <span> · {selectedId}</span>}</div>
      {s.differ && s.lines.map((l) => (
        <div key={l.label} data-testid={`plan-skill-${l.label}`} title={l.name_hi}>
          <span aria-hidden="true">{l.emoji}</span> <b>{l.short}</b> {l.skillId}
          {l.reteach && (
            <span style={tag} data-testid={`plan-reteach-${l.label}`}>🔄 पुनः शिक्षण<span className="en en-inline" lang="en" style={{ color: 'inherit', fontSize: '0.625rem' }}>Re-teach</span></span>
          )}
        </div>
      ))}
      {!s.differ && s.reteachLabels.length > 0 && (
        <div style={tag} data-testid="plan-reteach-all">
          🔄 पुनः शिक्षण: {s.reteachLabels.map((l) => GROUP_HI[l]).join(', ')}<span className="en en-inline" lang="en" style={{ color: 'inherit', fontSize: '0.625rem' }}>Re-teach</span>
        </div>
      )}
    </div>
  );
}
