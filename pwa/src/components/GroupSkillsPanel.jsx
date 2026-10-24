import React from 'react';
import { GROUPS, DECISION_LABELS, staysOnYesterdaysSkill, withSkill, acceptReteach, skillChoices, canReturnToYesterday } from '../services/groupSkills';

const GROUP_LABELS = {
  beginner: { hi: 'शुरुआती', en: 'Beginner' },
  progressor: { hi: 'प्रगतिशील', en: 'Progressor' },
  proficient: { hi: 'दक्ष', en: 'Proficient' },
};
const SOURCE_TAGS = {
  selected: { hi: 'आपका चुना कौशल', en: 'The skill you chose' },
  review: { hi: 'आपके कल के निर्णय से', en: 'From your decision at the review' },
  recommendation: { hi: 'कल की जाँच के सुझाव से', en: 'From the evidence of the last review' },
  derived: { hi: 'चुने कौशल से तय', en: 'Follows the skill you chose' },
  teacher: { hi: 'आपकी पसंद', en: 'Your choice' },
};

/**
 * Each group's skill for today, and the choice to re-teach.
 * The suggestions come from the teacher's decisions at the last review and from the children's evidence; the teacher can change them, and the final decision is theirs.
 * The Beginners and the Proficients can only be given a skill that makes sense for them (see skillChoices), and a re-teach can only be ticked for a group that is on yesterday's skill.
 */
export default function GroupSkillsPanel({ groups, competencies, ladder, selectedId, rows, setRows, reteach, setReteach, onSelectSkill, hasHistory, previousDate, disabled }) {
  const byId = {};
  competencies.forEach((c) => { byId[c.id] = c; });
  ['beginner', 'proficient'].forEach((l) => ((ladder && ladder.options && ladder.options[l]) || []).forEach((c) => { if (!byId[c.id]) byId[c.id] = c; }));
  const name = (id) => { const c = byId[id]; return c ? (c.name_hi || c.name_en) : id; };

  const changeSkill = (label, skillId) => {
    setRows((prev) => ({ ...prev, [label]: withSkill(prev[label], skillId) }));
    // a re-teach is the SAME skill as yesterday: choosing another skill ends it
    const prevId = rows[label].previous && rows[label].previous.id;
    if (skillId !== prevId) setReteach((prev) => ({ ...prev, [label]: false }));
  };

  // go back to yesterday's skill AND re-teach it (also what "re-teach instead?" does): see acceptReteach for the three cases
  const accept = (label) => {
    const a = acceptReteach({ label, row: rows[label], selectedId, ladder });
    if (!a) return;
    if (a.type === 'select') { onSelectSkill(a.skillId, { reteach: [label] }); return; }
    if (a.type === 'skill') setRows((prev) => ({ ...prev, [label]: withSkill(prev[label], a.skillId) }));
    setReteach((prev) => ({ ...prev, [label]: true }));
  };

  return (
    <div className="card" style={{ padding: 12 }} data-testid="group-skills-panel">
      <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
        आज हर समूह का कौशल <span style={{ fontSize: '0.7rem', fontWeight: 400, color: 'var(--text-secondary)' }}>Each group's skill today</span>
      </div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', margin: '2px 0 8px' }}>
        {hasHistory
          ? `सुझाव ${previousDate ? previousDate + ' की ' : 'पिछली '}योजना, उसकी समीक्षा में आपके निर्णयों और बच्चों की जाँच से भरे गए हैं। जो चाहें बदलें; अंतिम निर्णय आपका है। (Suggestions come from the plan of ${previousDate || 'the last plan'}, your decisions at its review and the children's evidence. Change anything; the final decision is yours.)`
          : 'पिछली योजना नहीं मिली, इसलिए हर समूह का कौशल आपके चुने कौशल से तय हुआ है। चाहें तो बदलें। (No earlier plan was found, so each group follows the skill you chose. Change it if you like.)'}
      </div>
      {GROUPS.map((label) => {
        const row = rows[label];
        const g = (groups || []).find((x) => x.label === label);
        const count = g ? g.count : 0;
        const tag = SOURCE_TAGS[row.source] || SOURCE_TAGS.derived;
        const dec = row.decision ? DECISION_LABELS[row.decision] : null;
        const stays = staysOnYesterdaysSkill(row);
        const canReturn = canReturnToYesterday({ label, row, ladder });
        const canReteach = !!row.previous && count > 0;
        return (
          <div key={label} style={{ borderTop: '1px solid var(--border)', padding: '8px 0' }} data-testid={`group-row-${label}`}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className={`badge badge-${label}`}>{GROUP_LABELS[label].hi}</span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-light)' }}>{GROUP_LABELS[label].en} · {count} बच्चे</span>
            </div>
            {row.previous && (
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                कल: {row.previous.id} · {name(row.previous.id)}
                {dec && <span> · आपका निर्णय: <b>{dec.hi}</b></span>}
                {row.previousReteach && <span data-testid={`previous-reteach-${label}`}> · 🔄 <b>कल पुनः शिक्षण हुआ</b> (Re-taught yesterday)</span>}
              </div>
            )}
            {row.evidence && row.evidence.assessed > 0 && (
              <div style={{ marginTop: 4, fontSize: '0.7rem' }} data-testid={`evidence-${label}`}>
                <div>
                  कल की जाँच में: {row.evidence.assessed} में से <b>{row.evidence.with_mistakes}</b> बच्चों ने गलती की
                  {row.evidence.rolls.length > 0 && <span> (रोल {row.evidence.rolls.join(', ')})</span>}
                </div>
                {row.evidence.mistakes.length > 0 && (
                  <div style={{ color: 'var(--text-secondary)' }}>
                    गलतियाँ: {row.evidence.mistakes.map((m) => `${m.name_hi || m.misconception_id} (${m.children})`).join('; ')}
                  </div>
                )}
                {row.recommendation === 'reteach' && (
                  <div style={{ color: 'var(--beginner)', fontWeight: 600 }} data-testid={`recommendation-${label}`}>
                    ✔ सुझाव: 🔄 दोहराएँ — कम से कम {row.evidence.needed} बच्चों ने गलती की। (A re-teach is suggested: at least {row.evidence.needed} children made a mistake.)
                  </div>
                )}
                {row.recommendation === 'very_small' && (
                  <div style={{ color: 'var(--text-secondary)' }} data-testid={`recommendation-${label}`}>
                    ℹ बहुत छोटा समूह: केवल {row.evidence.assessed} बच्चे जाँचे गए, इसलिए सुझाव नहीं; निर्णय आपका। (Very small group: only {row.evidence.assessed} assessed, so no suggestion; your decision.)
                  </div>
                )}
                {!row.recommendation && (
                  <div style={{ color: 'var(--text-secondary)' }} data-testid={`recommendation-${label}`}>
                    ℹ अधिकतर बच्चों ने सही किया: दोहराने का सुझाव नहीं है। (Most children got it: no re-teach is suggested.)
                  </div>
                )}
                {row.conflict && !reteach[label] && canReturn && (
                  <div style={{ marginTop: 4, background: 'var(--green-bg)', borderRadius: 6, padding: '4px 8px' }} data-testid={`conflict-${label}`}>
                    आपने आगे बढ़ना चुना था, पर {row.evidence.with_mistakes}/{row.evidence.assessed} बच्चों ने गलती की। क्या दोहराना चाहेंगे? (You chose to advance, but {row.evidence.with_mistakes} of {row.evidence.assessed} made a mistake. Re-teach instead?)
                    <button type="button" className="btn btn-secondary btn-small" style={{ marginLeft: 6, padding: '0 8px', fontSize: '0.7rem' }}
                      onClick={() => accept(label)} disabled={disabled} data-testid={`accept-reteach-${label}`}>🔄 दोहराएँ</button>
                  </div>
                )}
              </div>
            )}
            <div style={{ marginTop: 4 }}>
              {label === 'progressor' ? (
                <div style={{ fontSize: '0.8rem' }} data-testid="group-skill-progressor">
                  <b>{selectedId}</b> · {name(selectedId)}
                </div>
              ) : (
                <select
                  value={row.skillId}
                  disabled={disabled}
                  onChange={(e) => changeSkill(label, e.target.value)}
                  data-testid={`group-skill-select-${label}`}
                  style={{ width: '100%', padding: '6px 4px', fontSize: '0.8rem', borderRadius: 6, border: '1px solid var(--border)' }}
                >
                  {skillChoices({ label, ladder, row, selectedId }).map((grp) => (
                    <optgroup key={grp.key} label={`${grp.hi} (${grp.en})`}>
                      {grp.ids.map((id) => (
                        <option key={id} value={id}>{id} · {name(id)}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              )}
              <div style={{ fontSize: '0.65rem', color: 'var(--text-light)', marginTop: 2 }}>
                {tag.hi} ({tag.en})
                {row.ignored && (
                  <div style={{ marginTop: 2 }} data-testid={`ignored-${label}`}>
                    ℹ कल के निर्णय से सुझाया कौशल {row.ignored.id} आज के कौशल से मेल नहीं खाता ({label === 'beginner' ? 'शुरुआती समूह आज के कौशल से आगे नहीं जा सकता' : 'दक्ष समूह आज के कौशल से पीछे नहीं जा सकता'}), इसलिए कौशल चुने कौशल से तय हुआ।
                    (Yesterday's suggestion, {row.ignored.id}, does not fit today's skill, so this group follows the skill you chose.)
                  </div>
                )}
                {label !== 'progressor' && row.skillId !== row.initialId && (
                  <button type="button" className="btn btn-secondary btn-small" style={{ marginLeft: 6, padding: '0 6px', fontSize: '0.65rem' }}
                    onClick={() => changeSkill(label, row.initialId)} disabled={disabled}>↺ सुझाव पर लौटें</button>
                )}
              </div>
            </div>
            {canReteach && (
              <div style={{ marginTop: 6 }}>
                <label style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6, opacity: stays || reteach[label] ? 1 : 0.55 }}>
                  <input type="checkbox" checked={!!reteach[label]} disabled={disabled || (!stays && !reteach[label])} data-testid={`reteach-toggle-${label}`}
                    onChange={(e) => setReteach((prev) => ({ ...prev, [label]: e.target.checked }))} />
                  🔄 पुनः शिक्षण (Re-teach)
                </label>
                {reteach[label] && stays && (
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginLeft: 22 }}>
                    इस समूह का मुख्य ब्लॉक कल की गलतियों को दोबारा समझाएगा। (This group's main block will re-teach yesterday's mistakes.)
                  </div>
                )}
                {!stays && (
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginLeft: 22 }} data-testid={`reteach-needs-yesterday-${label}`}>
                    दोहराने के लिए समूह को कल वाले कौशल {row.previous.id} पर होना चाहिए। (To re-teach, this group must be on yesterday's skill, {row.previous.id}.)
                    {canReturn ? (
                      <button type="button" className="btn btn-secondary btn-small" style={{ marginLeft: 6, padding: '0 8px', fontSize: '0.65rem' }}
                        onClick={() => accept(label)} disabled={disabled} data-testid={`go-back-reteach-${label}`}>🔄 {row.previous.id} चुनकर दोहराएँ</button>
                    ) : (
                      <span data-testid={`reteach-not-today-${label}`}> कल का कौशल आज के कौशल से {label === 'beginner' ? 'आगे' : 'पीछे'} है, इसलिए इस समूह के लिए आज दोहराना संभव नहीं। (Yesterday's skill is {label === 'beginner' ? 'ahead of' : 'behind'} today's, so a re-teach is not possible for this group today.)</span>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
