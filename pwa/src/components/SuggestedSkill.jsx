import React from 'react';
import Bi from './Bi';

// Why this skill is suggested, from the teacher's decision for the Progressors at the last review (services: GET /plan/proposal, group_skills.propose)
const REASON = {
  advance: { hi: 'प्रगतिशील: ⬆ आगे बढ़ें', en: 'Progressors: ⬆ Advance' },
  advance_no_next: { hi: 'प्रगतिशील: ⬆ आगे बढ़ें; अगला कौशल नहीं है, इसलिए यही फिर', en: 'Progressors: ⬆ Advance; there is no next skill, so the same one again' },
  reteach: { hi: 'प्रगतिशील: 🔄 दोहराएँ', en: 'Progressors: 🔄 Re-teach' },
  not_sure: { hi: 'प्रगतिशील: ❓ पक्का नहीं', en: 'Progressors: ❓ Not sure' },
  recommended: { hi: 'प्रगतिशील के कई बच्चों से गलती हुई', en: 'many Progressors made a mistake' },
};

/** The suggestion for the skill list, or null: the Progressors' proposed skill (the skill the list chooses), when there is one and it is in this subject's list. */
export function suggestion(proposal, competencies) {
  const p = proposal && proposal.has_history && proposal.groups && proposal.groups.progressor;
  if (!p || !p.proposed || !REASON[p.reason]) return null;
  const skill = (competencies || []).find((c) => c.id === p.proposed.id);
  return skill ? { skill, reason: p.reason, date: proposal.previous_date } : null;
}

/**
 * "⭐ सुझाया गया" at the top of the Plan screen's skill list: one tap chooses it, exactly as in the list. Nothing when there is no suggestion
 * (the first plan, or no decision and no warning sign at the last review).
 */
export default function SuggestedSkill({ proposal, competencies, selectedId, onChoose }) {
  const s = suggestion(proposal, competencies);
  if (!s) return null;
  const r = REASON[s.reason];
  const day = s.date && !Number.isNaN(new Date(`${s.date}T00:00:00`).getTime())
    ? new Date(`${s.date}T00:00:00`).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short' }) : '';
  const where = s.reason === 'recommended' ? { hi: 'पिछली जाँच', en: 'At the last check' } : { hi: 'पिछली समीक्षा', en: 'At the last review' };
  const chosen = selectedId === s.skill.id;
  return (
    <div className="card" data-testid="suggested-skill" data-skill={s.skill.id} data-reason={s.reason} style={{ padding: 12, borderLeft: '4px solid var(--progressor)' }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>⭐ <Bi hi="सुझाया गया" en="Suggested" inline /></div>
      <div style={{ marginTop: 4 }}>
        <b style={{ fontFamily: 'monospace' }}>{s.skill.id}</b> — {s.skill.name_hi || s.skill.name_en}
      </div>
      <div data-testid="suggested-why" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
        <Bi hi={`${where.hi}${day ? ` (${day})` : ''}: ${r.hi}`} en={`${where.en}: ${r.en}`} />
      </div>
      <button type="button" className={`btn ${chosen ? 'btn-secondary' : 'btn-primary'} btn-small`} data-testid="choose-suggested" disabled={chosen}
        onClick={() => onChoose(s.skill.id)} style={{ marginTop: 8 }}>
        {chosen ? <Bi hi="✓ चुना गया" en="Chosen" inline /> : <Bi hi="यही चुनें" en="Choose this" inline />}
      </button>
    </div>
  );
}
