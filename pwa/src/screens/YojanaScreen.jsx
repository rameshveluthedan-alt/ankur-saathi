import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getCachedPlan, openAuthedPage, worksheetPath, prepareOfflineCopy } from '../services/api';
import { isOnline } from '../services/network';
import PlanGroupSkills from '../components/PlanGroupSkills';
import { reteachGroupsOf } from '../services/planSummary';
import ReteachNote from '../components/ReteachNote';
import SignalPanel from '../components/SignalPanel';
import BoardWork from '../components/BoardWork';
import { reteachTitleParts } from '../services/reteachInfo';
import { GROUP_LABELS } from '../tiers';
import Bi from '../components/Bi';
import { notify } from '../services/notify';
import { localToday } from '../services/today';
import { getFamiliarMode } from '../services/preferences';

// Generated text may contain line breaks (lists) and stray markdown markers.
// Keep the line breaks, wrap long strings, and drop ** / __ since we do not render markdown.
const ML = { whiteSpace: 'pre-line', overflowWrap: 'anywhere' };
const fmt = (s) => String(s ?? '').replace(/\*\*|__/g, '');
// the screen already shows the group's name, so drop a repeated leading label such as "शुरुआती:"
const stripGroup = (t) => fmt(t).replace(/^\s*(शुरुआती|प्रगतिशील|दक्ष)(\s*\([^)]*\))?\s*[:：]\s*/, '');

export default function YojanaScreen() {
  const { currentPlan, setCurrentPlan, teacher, selectedDomain } = useAuth();
  const navigate = useNavigate();
  const [expandedBlock, setExpandedBlock] = useState(null);
  const [showWhyPanel, setShowWhyPanel] = useState(false);
  const [loadingStored, setLoadingStored] = useState(false);

  // With a plan on screen, make its offline copy once, quietly: the stored plan and its worksheets (see prepareOfflineCopy in api.js).
  // The key changes when a regenerated plan has different worksheets (there is no plan id), so the offline copy is never an older plan's.
  const sheets = currentPlan && currentPlan.plan && currentPlan.plan.worksheets;
  const sheetsKey = sheets ? Array.from(JSON.stringify(sheets)).reduce((h, c) => (h * 33 + c.charCodeAt(0)) >>> 0, 5381) : 0;
  useEffect(() => {
    if (!currentPlan || !sheets || !isOnline()) return;
    prepareOfflineCopy(teacher.teacher_id, currentPlan.plan_date, currentPlan.domain_id, Object.keys(sheets).filter(l => sheets[l]));
  }, [currentPlan && currentPlan.plan_date, currentPlan && currentPlan.domain_id, sheetsKey]);

  // After a page reload the plan is no longer in memory: load today's stored plan
  // from the backend instead of making the teacher regenerate it.
  useEffect(() => {
    if (currentPlan) return;
    const today = localToday();
    setLoadingStored(true);
    getCachedPlan(teacher.teacher_id, today, selectedDomain)
      .then(setCurrentPlan)
      .catch(() => {})   // no stored plan for today: the empty state below is shown
      .finally(() => setLoadingStored(false));
  }, []);

  if (!currentPlan && loadingStored) {
    return (
      <div className="screen">
        <div className="loading"><div className="spinner" /><span><Bi hi="योजना लोड हो रही है..." en="Loading plan" inline /></span></div>
      </div>
    );
  }

  if (!currentPlan) {
    return (
      <div className="screen">
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h2><Bi hi="कोई योजना नहीं" en="No plan yet" inline /></h2>
          <p style={{ marginTop: 8, color: 'var(--text-secondary)' }}>
            पहले "योजना" टैब से लक्ष्य चुनें और दैनिक योजना बनाएँ।
          </p>
          <p className="en" lang="en" style={{ fontSize: '0.8rem', marginTop: 4 }}>
            Select a Lakshya from the Plan tab first, then generate the daily plan.
          </p>
        </div>
      </div>
    );
  }

  const plan = currentPlan.plan || {};
  const groups = currentPlan.groups || [];
  const anchor = plan.anchor || {};
  const rotation = plan.rotation_schedule || {};
  const blocks = rotation.blocks || [];
  const reteachSet = reteachGroupsOf(blocks);       // the groups that re-teach in this plan
  const explainability = currentPlan.explainability || plan.explainability || {};
  // "छोटी स्क्रीन" (Profile): read on every render, so a change on Profile shows the next time this screen is drawn
  const familiar = getFamiliarMode();
  const skillOf = (label) => (groups.find((g) => g.label === label) || {}).target_competency_id;      // the skill a group is taught today, for its block's title

  return (
    <div className="screen">
      {currentPlan.served_from === 'sample' && (
        <div data-testid="sample-banner" style={{ background: '#FFF4D6', border: '1px solid #E8D28A', borderRadius: 10, padding: '8px 12px', margin: '0 0 10px', fontSize: '0.8125rem' }}>
          📄 <b>नमूना योजना</b>: AI की सीमा पूरी होने से यह इसी कौशल की पहले से बनी योजना है। समूह और वर्कशीट आपकी कक्षा के हिसाब से जाँचे गए हैं।
          <div className="en" lang="en" style={{ fontSize: '0.7rem', color: '#6B4A00', marginTop: 2 }}>Sample plan: the AI limit was reached, so this is a recorded plan for the same skill. The groups and worksheets are checked for your class.</div>
        </div>
      )}
      <div className="screen-header plan-title">
        <h1>📋 <Bi hi="दैनिक योजना" en="Daily Plan" inline /></h1>
        {/* one printed page for the whole plan (the worksheets, one per group, are printed from their own buttons below) */}
        <button type="button" className="btn btn-secondary btn-small" data-testid="open-print" onClick={() => navigate('/plan/print')} style={{ order: 2 }}>🖨️ प्रिंट</button>
        <div className="plan-header-skills" style={{ textAlign: 'right' }}>
          <PlanGroupSkills planDate={currentPlan.plan_date} selectedId={currentPlan.selected_competency_id} groups={groups} blocks={blocks} />
          {plan.coverage && plan.coverage.tier && plan.coverage.tier !== 'tested' && (
            <span title={plan.coverage.note || ''} style={{ marginLeft: 8, background: '#FFF1CC', color: '#8A5A00', borderRadius: 8, padding: '1px 7px', fontSize: '0.65rem', fontWeight: 600 }}>
              {({ ai_written: '◐ AI-लिखित सामग्री', experimental: '⚠ प्रयोगात्मक', untested: '○ अभी परखा नहीं' })[plan.coverage.tier]}
            </span>
          )}
        </div>
      </div>

      {/* Groups summary */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {groups.map(g => (
          <div key={g.label} className={`card tier-card tier-${g.label}`} style={{ flex: 1, padding: 10, textAlign: 'center' }}>
            <span className={`badge badge-${g.label}`}>{GROUP_LABELS[g.label]?.hi}</span>
            <div className="en" lang="en">{GROUP_LABELS[g.label]?.en}</div>
            <div style={{ fontWeight: 700, fontSize: '1.125rem', margin: '4px 0' }}>{g.count}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{g.target_competency_name_hi}</div>
            {reteachSet.has(g.label) && <div style={{ fontSize: '0.75rem', color: 'var(--reteach)', fontWeight: 600, marginTop: 2 }}>🔄 पुनः शिक्षण</div>}
          </div>
        ))}
      </div>

      {/* Preparation before class (DIY TLMs etc.) */}
      {Array.isArray(plan.prep_hi) && plan.prep_hi.length > 0 && (
        <div className="card" style={{ borderLeft: '4px solid var(--progressor)' }}>
          <h3>🧰 <Bi hi="कक्षा से पहले तैयारी" en="Before class" inline /></h3>
          <ul style={{ paddingLeft: 18, marginTop: 6, fontSize: '0.875rem' }}>
            {plan.prep_hi.map((t, i) => <li key={i} style={{ marginBottom: 4, ...ML }}>{fmt(t)}</li>)}
          </ul>
        </div>
      )}

      {/* Anchor Activity */}
      {/* in "छोटी स्क्रीन" it starts folded to its title row (one tap opens it) */}
      {anchor.narration_hi && (() => {
        const title = <h3>🎯 <Bi hi="एंकर गतिविधि" en="Anchor Activity" inline /></h3>;
        const minutes = <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>10 मि.</span>;
        const body = (<>
          <p style={{ fontSize: '0.9375rem', marginBottom: 8, ...ML }}>{fmt(anchor.narration_hi)}</p>
          {anchor.opening_question_hi && (
            <div className="talking-point" style={ML}>
              <div className="talking-point-label"><Bi hi="शुरुआती सवाल" en="Opening Question" inline /></div>
              {fmt(anchor.opening_question_hi)}
            </div>
          )}
          {['beginner', 'progressor', 'proficient'].map(level => {
            const key = `${level}_participation_hi`;
            if (!anchor[key]) return null;
            return (
              <div key={level} style={{ fontSize: '0.8125rem', margin: '4px 0', padding: '4px 8px', borderRadius: 4, background: `var(--${level}-bg)`, ...ML }}>
                <strong>{GROUP_LABELS[level]?.emoji} {GROUP_LABELS[level]?.hi}<span className="en en-inline" lang="en">{GROUP_LABELS[level]?.en}</span>:</strong> {stripGroup(anchor[key])}
              </div>
            );
          })}
        </>);
        return familiar ? (
          <details className="card fold" data-testid="anchor-fold" style={{ borderLeft: '4px solid var(--channel-written)' }}>
            <summary style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ flex: 1 }}>{title}</span>{minutes}</summary>
            <div style={{ marginTop: 6 }}>{body}</div>
          </details>
        ) : (
          <div className="card" data-testid="anchor-card" style={{ borderLeft: '4px solid var(--channel-written)' }}>
            <div className="card-header">{title}{minutes}</div>
            {body}
          </div>
        );
      })()}

      {/* Rotation Timeline */}
      <h2 style={{ margin: '16px 0 8px' }}>⏱️ <Bi hi="रोटेशन शेड्यूल" en="Rotation Schedule" inline /></h2>
      {blocks.length > 0 ? (
        blocks.map((block, i) => (
          <div key={i}
            className={`timeline-block ${block.type === 'teach' ? `teach${block.reteach ? ' reteach' : GROUP_LABELS[block.teach_group] ? ` tier-${block.teach_group}` : ''}`
              : ['anchor', 'reteach', 'setup'].includes(block.type) ? block.type : 'transition'}`}
            role="button" tabIndex={0} aria-expanded={expandedBlock === i}
            onClick={() => setExpandedBlock(expandedBlock === i ? null : i)}
            onKeyDown={(e) => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setExpandedBlock(expandedBlock === i ? null : i); } }}
          >
            <div className="timeline-dot" style={{ background: (block.type === 'reteach' || block.reteach) ? 'var(--reteach)' : block.type === 'teach' ? `var(--${block.teach_group || 'green-dark'})` : 'var(--border)' }} />
            {block.time_start && (
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)', marginBottom: 2 }}>{block.time_start}</div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '0.875rem' }}>
                {block.type === 'teach' && (block.reteach
                  ? <Bi {...reteachTitleParts(block, GROUP_LABELS)} inline />
                  : <Bi hi={`👩‍🏫 ${GROUP_LABELS[block.teach_group]?.hi || block.teach_group} पढ़ाएँ`} en={`Teach ${GROUP_LABELS[block.teach_group]?.en || ''}`.trim()} inline />)}
                {block.type === 'anchor' && <Bi hi="🎯 एंकर" en="Anchor" inline />}
                {block.type === 'setup' && <Bi hi="📢 सेटअप" en="Setup" inline />}
                {block.type === 'reteach' && <Bi hi={`🔄 पुनः शिक्षण${GROUP_LABELS[block.teach_group] ? `: ${GROUP_LABELS[block.teach_group].hi}` : ''}`}
                  en={`Re-teach${GROUP_LABELS[block.teach_group] ? `: ${GROUP_LABELS[block.teach_group].en}` : ''}`} inline />}
                {block.type === 'transition' && <Bi hi="↔️ संक्रमण" en="Transition" inline />}
                {block.type === 'teach' && skillOf(block.teach_group) && (
                  <span data-testid="block-skill" style={{ fontWeight: 400, fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-secondary)' }}> — {skillOf(block.teach_group)}</span>
                )}
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap', flexShrink: 0, marginLeft: 8 }}>{block.duration_minutes} मि.</span>
            </div>

            {block.type === 'reteach' && block.affected_rolls && block.affected_rolls.length > 0 && (
              <div data-testid="reteach-rolls" style={{ fontSize: '0.75rem', marginTop: 4, ...ML }}>
                👥 जिन बच्चों के लिए<span className="en en-inline" lang="en">For</span>: रोल {block.affected_rolls.join(', ')}
              </div>
            )}
            <ReteachNote block={block} expanded={expandedBlock === i} />
            {(block.type === 'teach' || block.type === 'reteach') && block.other_groups_hi && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4, ...ML }}>
                बाकी समूह<span className="en en-inline" lang="en">Other groups</span>: {fmt(block.other_groups_hi)}
              </div>
            )}
            {/* the one-line script: in "छोटी स्क्रीन" it is folded under "आज की गतिविधि" (the click stays here: it must not close the block) */}
            {block.script_hi && (familiar ? (
              <details className="fold" data-testid="script-fold" onClick={(e) => e.stopPropagation()} style={{ margin: '2px 0 0' }}>
                <summary><span><Bi hi="आज की गतिविधि" en="Today's activity" inline /></span></summary>
                <div data-testid="block-script" style={{ fontSize: '0.8125rem', fontStyle: 'italic', marginTop: 2, ...ML }}>“{fmt(block.script_hi)}”</div>
              </details>
            ) : (
              <div data-testid="block-script" style={{ fontSize: '0.8125rem', fontStyle: 'italic', marginTop: 4, ...ML }}>“{fmt(block.script_hi)}”</div>
            ))}
            {/* what the children will do (the three core questions, or the writing prompt): visible without a tap, in every mode */}
            {block.type === 'teach' && <SignalPanel signal={block.signal} />}

            {expandedBlock === i && block.talking_points && (
              <div style={{ marginTop: 8 }}>
                {block.talking_points.i_do_hi && (
                  <div className="talking-point" style={ML}>
                    <div className="talking-point-label"><Bi hi="मैं करूँगा" en="I Do" inline /></div>
                    {fmt(block.talking_points.i_do_hi)}
                  </div>
                )}
                {block.talking_points.we_do_hi && (
                  <div className="talking-point" style={ML}>
                    <div className="talking-point-label"><Bi hi="हम करेंगे" en="We Do" inline /></div>
                    {fmt(block.talking_points.we_do_hi)}
                  </div>
                )}
                {block.talking_points.you_do_hi && (
                  <div className="talking-point" style={ML}>
                    <div className="talking-point-label"><Bi hi="तुम करोगे" en="You Do" inline /></div>
                    {fmt(block.talking_points.you_do_hi)}
                    <BoardWork plan={plan} group={block.teach_group} domain={currentPlan.domain_id} />
                  </div>
                )}
                {Array.isArray(block.cfu) && block.cfu.length > 0 && (
                  <div className="talking-point" style={ML} data-testid="cfu">
                    <div className="talking-point-label"><Bi hi="समझ की जाँच" en="Check for understanding" inline /></div>
                    {/* the heading names the purpose (a check for understanding), not one technique; the text under "कैसे करें?" says how (today: the show-me). The method is the same in every block: folded under one line, so the block's own questions come first. The click stays here (it must not close the block). */}
                    <details className="fold" data-testid="cfu-how" onClick={(e) => e.stopPropagation()} style={{ margin: '2px 0 4px' }}>
                      <summary>
                        <span><Bi hi="कैसे करें?" en="How to do it" inline /></span>
                      </summary>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                       हर बच्चा उत्तर स्लेट या कॉपी पर लिखकर, बनाकर या उँगलियों से तैयार करे और छिपाए। लगभग 20 सेकंड रुकें, फिर 'तीन, दो, एक — दिखाएँ!' कहें और सब एक साथ दिखाएँ। फिर दो बच्चों से समझाने को कहें: एक जिसने पहले गलती की थी (चुपचाप चुनें, नाम न बुलाएँ) और एक किसी भी बच्चे से, सिर्फ़ हाथ उठाने वालों से नहीं। अगर समूह के एक-चौथाई से ज़्यादा बच्चों के उत्तर गलत हों, तो आगे बढ़ने से पहले वही कदम अभी दोबारा समझाएँ (छड़ियों से)।
                       <span className="en" lang="en" style={{ fontSize: '0.75rem', marginTop: 2 }}>(Everyone prepares the answer on a slate or notebook page, written, drawn or on fingers, and hides it. Wait about 20 seconds, say 'three, two, one, show!' and everyone shows together. Then ask two children to explain: one who made the mistake before (chosen quietly, never named) and one at random, not only those with a hand up. If more than a quarter of the group is wrong, re-teach that step at once, with sticks, before moving on.)</span>
                    </div>
                    </details>
                    {block.cfu.map((q, k) => (
                      <div key={k} data-testid="cfu-item" style={{ marginTop: 6, paddingTop: 6, borderTop: k ? '1px dashed var(--border)' : 'none' }}>
                        <div><strong>{k + 1}.</strong> {fmt(q.question_hi)}</div>
                        <div style={{ fontSize: '0.8125rem' }}>✓ सही उत्तर: {fmt(q.expected_hi)}</div>
                        {(q.listen_for || []).map((l, j) => (
                          <div key={j} style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                            👂 सुनें: {fmt(l.wrong_answer_hi)} → <em>{fmt(l.misconception_name_hi)}</em>
                          </div>
                        ))}
                        {q.shows_hi && !(q.listen_for || []).length && (
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>सही उत्तर से पता चलता है: {fmt(q.shows_hi)}</div>
                        )}
                      </div>
                    ))}
                    {block.cfu_note_hi && (
                      <div style={{ fontSize: '0.75rem', fontStyle: 'italic', marginTop: 6 }} data-testid="cfu-note">
                        {fmt(block.cfu_note_hi)} <span className="en en-inline" lang="en">{fmt(block.cfu_note_en)}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            {expandedBlock !== i && block.talking_points && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginTop: 4 }}>
                ▸ बात के मुद्दे{Array.isArray(block.cfu) && block.cfu.length > 0 ? ' और समझ की जाँच' : ''} देखें<span className="en en-inline" lang="en">Tap for talking points</span>
              </div>
            )}
          </div>
        ))
      ) : (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          <p>रोटेशन शेड्यूल योजना बनने के बाद यहाँ दिखेगा।</p>
          <p className="en" lang="en" style={{ fontSize: '0.8rem', marginTop: 4 }}>
            Rotation schedule will appear after plan generation.
          </p>
        </div>
      )}

      {/* Worksheets: each opens the printable A4 sheet for this plan and level */}
      <h2 style={{ margin: '16px 0 8px' }}>📝 <Bi hi="वर्कशीट" en="Worksheets" inline /></h2>
      <div style={{ display: 'flex', gap: 8 }}>
        {['beginner', 'progressor', 'proficient'].map(level => {
          const label = GROUP_LABELS[level];
          const sheet = plan.worksheets?.[level];
          const available = Array.isArray(sheet?.problems) && sheet.problems.length > 0;
          const style = { flex: 1, flexDirection: 'column', gap: 2, padding: '10px 4px', fontSize: '0.8125rem', textDecoration: 'none', textAlign: 'center' };
          const inner = (
            <>
              <span style={{ fontSize: '1.25rem' }}>{label?.emoji}</span>
              <strong>{label?.hi}</strong>
              <span className="en" lang="en">{label?.en}</span>
              {available && sheet.required_count && sheet.required_count < sheet.problems.length && (
                <span style={{ fontSize: '0.6rem', opacity: 0.8 }}>पहले {sheet.required_count} सवाल</span>
              )}
            </>
          );
          return available ? (
            <button key={level} type="button" className="btn btn-secondary" style={style} data-testid={`worksheet-${level}`}
              onClick={() => openAuthedPage(worksheetPath(teacher.teacher_id, currentPlan.plan_date, currentPlan.domain_id, level)).catch(e => notify(e.message, 'error'))}>{inner}</button>
          ) : (
            <span key={level} className="btn" style={{ ...style, opacity: 0.45, border: '2px dashed var(--border)', color: 'var(--text-secondary)' }}>
              {inner}<span style={{ fontSize: '0.6875rem' }}><Bi hi="उपलब्ध नहीं" en="not available" /></span>
            </span>
          );
        })}
      </div>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 6 }}>
        <Bi hi="खुलने पर प्रिंट करें, या बोर्ड पर उतारें।" en="Opens the sheet: print it, or copy it to the board." inline />
      </p>

      {/* Why this plan? */}
      <div style={{ marginTop: 16, marginBottom: 80 }}>
        <button onClick={() => setShowWhyPanel(!showWhyPanel)}
          style={{ background: 'none', border: 'none', color: 'var(--green-dark)', fontSize: '0.875rem', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600, minHeight: 44, padding: '0 4px' }}>
          {showWhyPanel ? '▾' : '▸'} <Bi hi="यह योजना क्यों?" en="Why this plan?" inline />
        </button>
        {showWhyPanel && (
          <div className="card" style={{ marginTop: 8, fontSize: '0.8125rem', background: 'var(--green-bg)' }}>
            {Array.isArray(explainability.items) ? explainability.items.map((item, i) => (
              <div key={i} style={{ marginBottom: 10 }}>
                <strong>{fmt(item.title_hi)} <span className="en en-inline" lang="en">{fmt(item.title_en)}</span></strong>
                <div style={ML}>{fmt(item.body_hi)}</div>
                <div className="en" lang="en" style={{ fontSize: '0.75rem', ...ML }}>{fmt(item.body_en)}</div>
              </div>
            )) : Object.entries(explainability).filter(([key]) => !key.startsWith('teacher_decision_')).map(([key, val]) => (
              <div key={key} style={{ marginBottom: 6 }}>
                <strong>{key}:</strong> {typeof val === 'string' ? val : JSON.stringify(val)}
              </div>
            ))}
            {Object.keys(explainability).length === 0 && (
              <p style={{ color: 'var(--text-secondary)' }}><Bi hi="व्याख्या डेटा उपलब्ध नहीं।" en="Explainability data not available." inline /></p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
