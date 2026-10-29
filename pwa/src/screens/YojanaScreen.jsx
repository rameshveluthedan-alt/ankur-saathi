import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getCachedPlan, openAuthedPage, worksheetPath, prepareOfflineCopy, getReviewChannels } from '../services/api';
import { channelOf, OBSERVE, hasObservation, PRACTICE_ONLY, hasWorksheet } from '../services/reviewWays';
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
import { friendlyError } from '../services/errors';
import { localToday } from '../services/today';
import { getFamiliarMode } from '../services/preferences';
import { planMinutes } from '../services/planMinutes';

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
  // loading from the first frame when the plan in memory is not today's for the chosen subject (see below): never a moment of "no plan" first
  const [loadingStored, setLoadingStored] = useState(() => !(currentPlan && currentPlan.plan_date === localToday() && currentPlan.domain_id === selectedDomain));
  // how each group's skill is checked at the review (and what to look for, the text to read aloud): the "आज की समीक्षा" fold, readable before class
  const [ways, setWays] = useState(null);
  useEffect(() => {
    setWays(null);
    if (!currentPlan || !currentPlan.plan_date || !currentPlan.domain_id) return undefined;
    let cancelled = false;
    Promise.resolve().then(() => getReviewChannels(teacher.teacher_id, currentPlan.plan_date, currentPlan.domain_id))
      .then((w) => { if (!cancelled) setWays(w); }).catch(() => {});
    return () => { cancelled = true; };
  }, [currentPlan && currentPlan.plan_date, currentPlan && currentPlan.domain_id]);

  // With a plan on screen, make its offline copy once, quietly: the stored plan and its worksheets (see prepareOfflineCopy in api.js).
  // The key changes when a regenerated plan has different worksheets (there is no plan id), so the offline copy is never an older plan's.
  const sheets = currentPlan && currentPlan.plan && currentPlan.plan.worksheets;
  const sheetsKey = sheets ? Array.from(JSON.stringify(sheets)).reduce((h, c) => (h * 33 + c.charCodeAt(0)) >>> 0, 5381) : 0;
  useEffect(() => {
    if (!currentPlan || !sheets || !isOnline()) return;
    prepareOfflineCopy(teacher.teacher_id, currentPlan.plan_date, currentPlan.domain_id, Object.keys(sheets).filter(l => sheets[l]));
  }, [currentPlan && currentPlan.plan_date, currentPlan && currentPlan.domain_id, sheetsKey]);

  // "आज की योजना" shows TODAY's plan only (29 Oct). The plan in memory may be an older day's (a phone brings back yesterday's page in the morning) or
  // another subject's, or there may be none (a reload): then today's stored plan is loaded for the chosen subject. With none stored, a plan of today in
  // memory (the other subject) is still shown, but an older day's plan is put away, never shown as today's. The day is looked at again whenever the app
  // comes back to the screen, so a phone left open across midnight moves on to the new day; with no plan of today on the screen, coming back also
  // looks again (a plan may have been made meanwhile, on another phone).
  const [today, setToday] = useState(localToday);
  const [wake, setWake] = useState(0);
  const [loadFailed, setLoadFailed] = useState(false);
  useEffect(() => {
    const again = () => { if (document.visibilityState !== 'hidden') { setToday(localToday()); setWake((w) => w + 1); } };
    document.addEventListener('visibilitychange', again);
    window.addEventListener('focus', again);
    return () => { document.removeEventListener('visibilitychange', again); window.removeEventListener('focus', again); };
  }, []);
  const isToday = (p) => !!p && p.plan_date === today;
  const fits = isToday(currentPlan) && currentPlan.domain_id === selectedDomain;
  useEffect(() => {
    if (fits) return undefined;
    let cancelled = false;
    setLoadingStored(true);
    setLoadFailed(false);
    getCachedPlan(teacher.teacher_id, today, selectedDomain)
      .then((p) => { if (!cancelled) setCurrentPlan(p); })
      .catch((e) => {
        if (cancelled) return;
        if (!isToday(currentPlan)) setCurrentPlan(null);          // no plan stored for today: an older day's plan is put away
        if (!(e && e.status === 404)) setLoadFailed(true);         // not "none stored" but a failure (no internet): the empty state says so
      })
      .finally(() => { if (!cancelled) setLoadingStored(false); });
    return () => { cancelled = true; };
  }, [today, selectedDomain, fits, wake]);

  if (loadingStored && !isToday(currentPlan)) {
    return (
      <div className="screen">
        <div className="loading"><div className="spinner" /><span><Bi hi="योजना लोड हो रही है..." en="Loading plan" inline /></span></div>
      </div>
    );
  }

  if (!isToday(currentPlan)) {
    return (
      <div className="screen">
        <div className="empty-state" data-testid="yojana-empty">
          <div className="empty-icon">📋</div>
          <h2><Bi hi="कोई योजना नहीं" en="No plan yet" inline /></h2>
          {loadFailed && <p data-testid="yojana-load-failed" style={{ marginTop: 8, color: '#8A5A00' }}><Bi hi="आज की योजना खुल नहीं सकी। इंटरनेट जाँचकर फिर कोशिश करें।" en="Today's plan could not be opened. Check the internet and try again." /></p>}
          <p style={{ marginTop: 8, color: 'var(--text-secondary)' }}>
            पहले "योजना बनाएँ" टैब पर कौशल चुनें और आज की योजना बनाएँ।
          </p>
          <p className="en" lang="en" style={{ fontSize: '0.8rem', marginTop: 4 }}>
            First choose a skill on the "Make plan" tab, then make today's plan.
          </p>
          <button type="button" className="btn btn-primary" data-testid="yojana-make-plan" onClick={() => navigate('/')} style={{ marginTop: 12, flexDirection: 'column', gap: 0 }}>
            <Bi hi="योजना बनाएँ →" en="Make a plan" />
          </button>
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
  const length = planMinutes(currentPlan);
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
        <h1>📋 <Bi hi="आज की योजना" en="Today's plan" inline />
          {/* how long this plan is: the time the teacher chose, recorded on the plan (services/planMinutes.js) */}
          {length && (
            <span data-testid="time-chip" data-recorded={length.recorded ? 'true' : 'false'}
              style={{ marginLeft: 8, verticalAlign: 'middle', whiteSpace: 'nowrap', background: 'var(--green-bg)', color: 'var(--green-dark)', border: '1px solid var(--green-light)', borderRadius: 10, padding: '1px 8px', fontSize: '0.75rem', fontWeight: 600 }}>
              ⏱ {length.minutes} मिनट<span className="en en-inline" lang="en" style={{ color: 'inherit' }}>min</span>
            </span>
          )}
        </h1>
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
                    {/* observation and reading aloud happen DURING You Do: record them now, from here, without the Review's first judgment */}
                    {block.type === 'teach' && (() => {
                      const l = ways && ways.has_plan ? (ways.levels || []).find((x) => x.level === block.teach_group && (x.channel === 'observed' || x.channel === 'orf')) : null;
                      if (!l) return null;
                      const way = channelOf(l.channel);
                      return (
                        <button type="button" className="btn btn-secondary btn-small" data-testid={`record-now-${block.teach_group}`} data-channel={l.channel}
                          onClick={(e) => { e.stopPropagation(); navigate('/review', { state: { from: 'plan', channel: l.channel, level: l.level } }); }} style={{ display: 'block', marginTop: 8 }}>
                          {way.icon} <Bi hi="अभी दर्ज करें" en="Record now" inline /> <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>· <Bi hi={way.hi} en={way.en} inline /></span>
                        </button>
                      );
                    })()}
                  </div>
                )}
                {Array.isArray(block.cfu) && block.cfu.length > 0 && (
                  <div className="talking-point" style={ML} data-testid="cfu">
                    <div className="talking-point-label"><Bi hi="समझ की जाँच" en="Check for understanding" inline /></div>
                    {/* the heading names the purpose (a check for understanding), not one technique; the text under "कैसे करें?" says how (today: the show-me). The method is the same in every block: folded under one line, so the block's own questions come first. The click stays here (it must not close the block). Sticks are named only in a maths plan: a Hindi lesson has none. */}
                    <details className="fold" data-testid="cfu-how" onClick={(e) => e.stopPropagation()} style={{ margin: '2px 0 4px' }}>
                      <summary>
                        <span><Bi hi="कैसे करें?" en="How to do it" inline /></span>
                      </summary>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                       हर बच्चा उत्तर स्लेट या कॉपी पर लिखकर, बनाकर या उँगलियों से तैयार करे और छिपाए। लगभग 20 सेकंड रुकें, फिर 'तीन, दो, एक — दिखाएँ!' कहें और सब एक साथ दिखाएँ। फिर दो बच्चों से समझाने को कहें: एक जिसने पहले गलती की थी (चुपचाप चुनें, नाम न बुलाएँ) और एक किसी भी बच्चे से, सिर्फ़ हाथ उठाने वालों से नहीं। अगर समूह के एक-चौथाई से ज़्यादा बच्चों के उत्तर गलत हों, तो आगे बढ़ने से पहले वही कदम अभी दोबारा समझाएँ{currentPlan.domain_id === 'numeracy' ? ' (छड़ियों से)' : ''}।
                       <span className="en" lang="en" style={{ fontSize: '0.75rem', marginTop: 2 }}>(Everyone prepares the answer on a slate or notebook page, written, drawn or on fingers, and hides it. Wait about 20 seconds, say 'three, two, one, show!' and everyone shows together. Then ask two children to explain: one who made the mistake before (chosen quietly, never named) and one at random, not only those with a hand up. If more than a quarter of the group is wrong, re-teach that step at once{currentPlan.domain_id === 'numeracy' ? ', with sticks,' : ''} before moving on.)</span>
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
              onClick={() => openAuthedPage(worksheetPath(teacher.teacher_id, currentPlan.plan_date, currentPlan.domain_id, level)).catch(e => notify(friendlyError(e, { hi: 'वर्कशीट नहीं खुल सकी', en: 'The worksheet could not be opened' }), 'error'))}>{inner}</button>
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

      {/* today's review, readable before class: how each group is checked, what to look for, the text to read aloud */}
      <details className="card fold" data-testid="review-today" style={{ padding: '4px 12px', marginTop: 16 }}>
        <summary><span>☑️ <Bi hi="आज की समीक्षा: कैसे जाँचें" en="Today's review: how to check" inline /></span></summary>
        {ways && ways.has_plan && (ways.levels || []).length > 0 ? (ways.levels || []).map((l) => {
          const way = channelOf(l.channel);
          return (
            <div key={l.level} data-testid={`review-way-${l.level}`} style={{ fontSize: '0.8125rem', padding: '4px 0', borderTop: '1px dashed var(--border)' }}>
              <b>{GROUP_LABELS[l.level]?.mark} {GROUP_LABELS[l.level]?.hi}</b> <span style={{ fontFamily: 'monospace' }}>{l.competency_id}</span>: {way ? <>{way.icon} <Bi hi={way.hi} en={way.en} inline /></> : l.channel}
              {way && <div style={{ color: 'var(--text-secondary)' }}><Bi hi={way.who.hi} en={way.who.en} inline /></div>}
              {l.channel === 'observed' && hasWorksheet(currentPlan, l.level) && (
                <div data-testid={`review-way-practice-${l.level}`} style={{ color: '#8A5A00' }}><Bi hi={PRACTICE_ONLY.hi} en={PRACTICE_ONLY.en} inline /></div>
              )}
              {l.passage && <div data-testid={`review-way-passage-${l.level}`}><Bi hi="पढ़ने का पाठ" en="Text to read" inline />: «{l.passage.title}» ({l.passage.word_count} शब्द)</div>}
            </div>
          );
        }) : (
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '4px 0' }}><Bi hi="पढ़ाने के बाद समीक्षा स्क्रीन पर हर समूह का तरीका दिखेगा।" en="After teaching, the Review screen shows each group's way." inline /></p>
        )}
        {(ways && ways.has_plan ? (ways.levels || []).some((l) => l.channel === 'observed') : hasObservation(currentPlan)) && (
          <div data-testid="review-observe" style={{ fontSize: '0.8125rem', paddingTop: 4, borderTop: '1px dashed var(--border)' }}>
            <b>✓ <Bi hi="देखकर दर्ज करना" en="Observing" inline />:</b> <Bi hi={OBSERVE.hi} en={OBSERVE.en} inline />
          </div>
        )}
        {/* recording on paper during You Do (no phone in hand): a sheet of boxes for the observed and read-aloud groups, entered in step 2 after class */}
        {ways && ways.has_plan && (ways.levels || []).some((l) => l.channel === 'observed' || l.channel === 'orf') && (
          <button type="button" className="btn btn-secondary btn-small" data-testid="open-ticks" onClick={() => navigate('/plan/ticks')} style={{ margin: '6px 0 2px' }}>
            🖨️ <Bi hi="टिक शीट (कागज़ पर दर्ज करें)" en="Tick sheet (record on paper)" inline />
          </button>
        )}
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '2px 0 6px' }}><Bi hi="हर तरीके के कदम समीक्षा स्क्रीन पर “कैसे करें?” में हैं।" en="The steps for each way are under “How to do it” on the Review." inline /></p>
      </details>

      {/* the next step after teaching, without having to know which tab it is */}
      <button type="button" className="btn btn-primary" data-testid="to-review" onClick={() => navigate('/review')} style={{ marginTop: 16, flexDirection: 'column', gap: 0 }}>
        <Bi hi="पढ़ाने के बाद: समीक्षा करें →" en="After teaching: review" />
      </button>

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
