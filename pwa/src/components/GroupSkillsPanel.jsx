import React from 'react';
import { GROUPS, DECISION_LABELS, staysOnYesterdaysSkill, withSkill, acceptReteach, skillChoices, canReturnToYesterday, toggleReteach, reteachChoice, selectValue, chooseOption, visibleChoices } from '../services/groupSkills';
import { GROUP_LABELS } from '../tiers';
const SOURCE_TAGS = {
  selected: { hi: 'आपका चुना कौशल', en: 'The skill you chose' },
  review: { hi: 'पिछली समीक्षा में आपके निर्णय से', en: 'From your decision at the review' },
  recommendation: { hi: 'पिछली जाँच के सुझाव से', en: 'From the evidence of the last review' },
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
  // the last plan is often NOT yesterday (a weekend, a holiday): name its date, e.g. "24 अक्टू॰"
  const previousLabel = previousDate && !Number.isNaN(new Date(`${previousDate}T00:00:00`).getTime())
    ? new Date(`${previousDate}T00:00:00`).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short' }) : '';

  // ONE LIST holds both decisions for the Beginners and the Proficients: which skill, and whether to re-teach it (see chooseOption)
  const choose = (label, value) => {
    const t = chooseOption({ label, row: rows[label], value, selectedId, ladder });
    if (!t) return;
    setRows((prev) => ({ ...prev, [label]: t.row }));
    setReteach((prev) => ({ ...prev, [label]: t.reteach }));
  };

  // back to what the app suggested: its skill AND its re-teach setting
  const restoreSuggestion = (label) => {
    const row = rows[label];
    setRows((prev) => ({ ...prev, [label]: withSkill(prev[label], row.initialId) }));
    setReteach((prev) => ({ ...prev, [label]: !!row.initialReteach }));
  };

  // THE BOX IS THE DECISION AND THE SKILL FOLLOWS IT: ticking puts a Beginner or Proficient group back on yesterday's skill (the list shows it), unticking puts it back (see toggleReteach)
  const toggle = (label, checked) => {
    const t = toggleReteach({ label, row: rows[label], checked, selectedId, ladder });
    if (!t) return;
    setRows((prev) => ({ ...prev, [label]: t.row }));
    setReteach((prev) => ({ ...prev, [label]: t.reteach }));
  };

  // "re-teach instead?" and the Progressors' button: the other groups just get ticked; the Progressors' day's skill is changed on purpose (acceptReteach)
  const accept = (label) => {
    if (label !== 'progressor') { toggle(label, true); return; }
    const a = acceptReteach({ label, row: rows[label], selectedId, ladder });
    if (!a) return;
    if (a.type === 'select') { onSelectSkill(a.skillId, { reteach: [label] }); return; }
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
        const canTick = !!reteach[label] || (label === 'progressor' ? stays : canReturn);       // may the box be ticked now?
        const canReteach = !!row.previous && count > 0;
        return (
          <div key={label} className={`tier-${label}`} style={{ borderTop: '1px solid var(--border)', borderLeft: '4px solid var(--tier)', padding: '8px 0 8px 8px' }} data-testid={`group-row-${label}`}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className={`badge badge-${label}`}>{GROUP_LABELS[label].hi}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}><span className="en en-inline" lang="en" style={{ marginLeft: 0, marginRight: 4 }}>{GROUP_LABELS[label].en} ·</span>{count} बच्चे</span>
            </div>
            {row.previous && (
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                पिछली योजना{previousLabel ? ` (${previousLabel})` : ''}: {row.previous.id} · {name(row.previous.id)}
                {dec && <span> · आपका निर्णय: <b>{dec.hi}</b></span>}
                {row.previousReteach && <span data-testid={`previous-reteach-${label}`}> · 🔄 <b>पिछली योजना में पुनः शिक्षण हुआ</b> (Re-taught in the last plan)</span>}
              </div>
            )}
            {row.evidence && row.evidence.assessed > 0 && (
              <div style={{ marginTop: 4, fontSize: '0.7rem' }} data-testid={`evidence-${label}`}>
                <div>
                  पिछली जाँच में: {row.evidence.assessed} में से <b>{row.evidence.with_mistakes}</b> बच्चों ने गलती की
                  {row.evidence.rolls.length > 0 && <span> (रोल {row.evidence.rolls.join(', ')})</span>}
                </div>
                {row.evidence.mistakes.length > 0 && (
                  <div style={{ color: 'var(--text-secondary)' }}>
                    गलतियाँ: {row.evidence.mistakes.map((m) => `${m.name_hi || m.misconception_id} (${m.children})`).join('; ')}
                  </div>
                )}
                {row.recommendation === 'reteach' && (
                  <div style={{ color: 'var(--reteach)', fontWeight: 600 }} data-testid={`recommendation-${label}`}>
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
                    <button type="button" className="btn btn-secondary btn-small" style={{ marginLeft: 6, fontSize: '0.8125rem' }}
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
                  value={selectValue({ label, row, reteachOn: !!reteach[label] })}
                  disabled={disabled}
                  onChange={(e) => choose(label, e.target.value)}
                  data-testid={`group-skill-select-${label}`}
                  style={{ width: '100%', padding: '6px 4px', fontSize: '0.875rem', borderRadius: 6, border: '1px solid var(--border)', fontFamily: 'inherit' }}
                >
                  {(() => {
                    const groupsOfSkills = visibleChoices({ label, ladder, row, selectedId, reteachOn: !!reteach[label] });
                    const reteachOption = canReteach ? reteachChoice({ label, row, ladder }) : null;
                    const plain = (grp) => (
                      <optgroup key={grp.key} label={`${grp.hi} (${grp.en})`}>
                        {grp.ids.map((id) => (
                          <option key={id} value={id}>{id} · {name(id)}{reteachOption && id === row.previous.id ? ' — नया पाठ (दोहराव नहीं)' : ''}</option>
                        ))}
                      </optgroup>
                    );
                    return [
                      ...groupsOfSkills.slice(0, 1).map(plain),
                      reteachOption && (
                        <optgroup key="reteach" label="🔄 पिछली योजना का कौशल दोहराएँ (Re-teach the last plan's skill)">
                          <option value={reteachOption.value}>🔄 दोहराएँ: {reteachOption.id} · {name(reteachOption.id)}</option>
                        </optgroup>
                      ),
                      ...groupsOfSkills.slice(1).map(plain),
                    ];
                  })()}
                </select>
              )}
              <div style={{ fontSize: '0.65rem', color: 'var(--text-light)', marginTop: 2 }}>
                {tag.hi} ({tag.en})
                {row.ignored && (
                  <div style={{ marginTop: 2 }} data-testid={`ignored-${label}`}>
                    ℹ पिछली समीक्षा के निर्णय से सुझाया कौशल {row.ignored.id} आज के कौशल से मेल नहीं खाता ({label === 'beginner' ? 'शुरुआती समूह आज के कौशल से आगे नहीं जा सकता' : 'दक्ष समूह आज के कौशल से पीछे नहीं जा सकता'}), इसलिए कौशल चुने कौशल से तय हुआ।
                    (The suggestion from the last review, {row.ignored.id}, does not fit today's skill, so this group follows the skill you chose.)
                  </div>
                )}
                {label !== 'progressor' && (row.skillId !== row.initialId || !!reteach[label] !== !!row.initialReteach) && (
                  <button type="button" className="btn btn-secondary btn-small" style={{ marginLeft: 6, marginTop: 4, fontSize: '0.8125rem' }}
                    onClick={() => restoreSuggestion(label)} disabled={disabled} data-testid={`restore-suggestion-${label}`}>↺ सुझाव पर लौटें</button>
                )}
              </div>
            </div>
            {label !== 'progressor' && canReteach && reteach[label] && (
              <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: 4 }} data-testid={`reteach-on-${label}`}>
                🔄 इस समूह का मुख्य ब्लॉक पिछली जाँच की गलतियों को दोबारा समझाएगा। (This group's main block re-teaches the mistakes from the last review.)
              </div>
            )}
            {label !== 'progressor' && canReteach && !canReturn && (
              <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: 4 }} data-testid={`reteach-not-today-${label}`}>
                पिछली योजना का कौशल ({row.previous.id}) आज के कौशल से {label === 'beginner' ? 'आगे' : 'पीछे'} है, इसलिए इस समूह के लिए आज दोहराना संभव नहीं। (The last plan's skill, {row.previous.id}, is {label === 'beginner' ? 'ahead of' : 'behind'} today's, so a re-teach is not possible for this group today.)
              </div>
            )}
            {label === 'progressor' && canReteach && (
              <div style={{ marginTop: 6 }}>
                <label style={{ fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: 8, minHeight: 44, opacity: canTick ? 1 : 0.55 }}>
                  <input type="checkbox" checked={!!reteach[label]} disabled={disabled || !canTick} data-testid={`reteach-toggle-${label}`}
                    onChange={(e) => toggle(label, e.target.checked)} />
                  🔄 पुनः शिक्षण (Re-teach)
                </label>
                {reteach[label] && (
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginLeft: 22 }}>
                    इस समूह का मुख्य ब्लॉक पिछली जाँच की गलतियों को दोबारा समझाएगा। (This group's main block will re-teach the mistakes from the last review.)
                  </div>
                )}
                {!canTick && (
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginLeft: 22 }} data-testid="reteach-needs-yesterday-progressor">
                    दोहराने के लिए आज का कौशल पिछली योजना वाला {row.previous.id} होना चाहिए। (To re-teach, today's skill must be the last plan's, {row.previous.id}.)
                    <button type="button" className="btn btn-secondary btn-small" style={{ margin: '4px 0 4px 6px', fontSize: '0.8125rem' }}
                      onClick={() => accept(label)} disabled={disabled} data-testid="go-back-reteach-progressor">🔄 {row.previous.id} चुनकर दोहराएँ</button>
                    <div>यह आज का कौशल बदलता है, इसलिए दूसरे समूहों के कौशल भी बदल सकते हैं। (This changes today's skill, so the other groups' skills can change too.)</div>
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
