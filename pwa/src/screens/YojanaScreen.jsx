import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getCachedPlan, worksheetPath, prepareOfflineCopy, getReviewChannels } from '../services/api';
import { channelOf, OBSERVE, hasObservation, PRACTICE_ONLY, hasWorksheet } from '../services/reviewWays';
import { isOnline } from '../services/network';
import { reteachGroupsOf } from '../services/planSummary';
import ReteachNote from '../components/ReteachNote';
import SignalPanel from '../components/SignalPanel';
import BoardWork from '../components/BoardWork';
import GroupMark from '../components/GroupMark';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import Bi from '../components/Bi';
import { localToday } from '../services/today';
import { getFamiliarMode } from '../services/preferences';
import { planMinutes } from '../services/planMinutes';
import { planSlots, stripParts } from '../services/planSlots';

// Generated text may contain line breaks (lists) and stray markdown markers.
// Keep the line breaks, wrap long strings, and drop ** / __ since we do not render markdown.
const ML = { whiteSpace: 'pre-line', overflowWrap: 'anywhere' };
const fmt = (s) => String(s ?? '').replace(/\*\*|__/g, '');
// "Why this plan?": only the labels the app itself wraps in **…** (the resources item) are bold; anything else stays plain text
const boldLabels = (s) => String(s ?? '').split(/\*\*([^*\n]+)\*\*/g).map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : part.replace(/\*\*|__/g, '')));
// the screen already shows the group's name, so drop a repeated leading label such as "शुरुआती:"
const stripGroup = (t) => fmt(t).replace(/^\s*(शुरुआती|प्रगतिशील|दक्ष)(\s*\([^)]*\))?\s*[:：]\s*/, '');
const MIN = <Bi hi="मि." en="min" inline />;

// A fold inside a slot: one tappable line with an icon, the detail under it. The click stays here (it must never change the tab).
function Fold({ icon, hi, en, testid, open, children }) {
  return (
    <details className="fold slot-fold" data-testid={testid} open={open} onClick={(e) => e.stopPropagation()}>
      <summary><span>{icon} <Bi hi={hi} en={en} inline /></span></summary>
      <div className="slot-fold-body">{children}</div>
    </details>
  );
}

export default function YojanaScreen() {
  const { currentPlan, setCurrentPlan, teacher, selectedDomain } = useAuth();
  const navigate = useNavigate();
  const [showWhyPanel, setShowWhyPanel] = useState(false);
  const [slotIndex, setSlotIndex] = useState(0);         // the session-slot tab on screen
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
  useEffect(() => { setSlotIndex(0); }, [currentPlan && currentPlan.plan_date, currentPlan && currentPlan.domain_id, currentPlan && currentPlan.selected_competency_id]);

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
          {loadFailed && <p data-testid="yojana-load-failed" style={{ marginTop: 8, color: 'var(--danger)' }}><Bi hi="आज की योजना खुल नहीं सकी। इंटरनेट जाँचकर फिर कोशिश करें।" en="Today's plan could not be opened. Check the internet and try again." /></p>}
          <p style={{ marginTop: 8, color: 'var(--text-secondary)' }}>
            <Bi hi={'पहले "योजना बनाएँ" टैब पर कौशल चुनें और आज की योजना बनाएँ।'} en={'First choose a skill on the "Make plan" tab, then make today\'s plan.'} />
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
  const groupOf = (label) => groups.find((g) => g.label === label) || {};
  const skillOf = (label) => groupOf(label).target_competency_id;      // the skill a group is taught today, for its slot's title
  const slots = planSlots(blocks, { hasAnchor: !!anchor.narration_hi });
  const active = slots[Math.min(slotIndex, Math.max(slots.length - 1, 0))];
  const sheetUrl = (level) => worksheetPath(teacher.teacher_id, currentPlan.plan_date, currentPlan.domain_id, level);
  const sheetOf = (level) => { const s = plan.worksheets?.[level]; return Array.isArray(s?.problems) && s.problems.length > 0 ? s : null; };
  // how a group is checked today (services/reviewWays.js): the button at the top of its slot records the children's levels during the activity
  const wayOf = (level) => (ways && ways.has_plan ? (ways.levels || []).find((x) => x.level === level) : null);

  // ── one slot's content ──
  const recordButton = (level) => {
    const l = wayOf(level);
    if (!l) return null;
    const way = channelOf(l.channel);
    if (!way) return null;
    const during = l.channel === 'photo'
      ? <Bi hi="वर्कशीट पूरी होने के बाद" en="After the worksheet" inline />
      : <Bi hi="'तुम करोगे' के दौरान" en="During You Do" inline />;
    return (
      <div className="record-bar" data-testid={`record-bar-${level}`}>
        <button type="button" className="btn btn-primary btn-small" data-testid={l.channel === 'photo' ? `record-photo-${level}` : `record-now-${level}`} data-channel={l.channel}
          onClick={(e) => { e.stopPropagation(); navigate('/review', { state: { from: 'plan', channel: l.channel, level } }); }}>
          {way.icon} {l.channel === 'photo' ? <Bi hi="फ़ोटो से स्तर दर्ज करें" en="Record levels from photos" inline /> : <Bi hi="अभी स्तर दर्ज करें" en="Record levels now" inline />}
        </button>
        <span className="record-bar-note">{during} · <Bi hi={way.hi} en={way.en} inline /></span>
      </div>
    );
  };

  const afterLines = (slot) => slot.after.filter((b) => b && (b.script_hi || b.duration_minutes)).map((b, k) => (
    <div key={k} className="slot-after" data-testid="slot-after">
      <b>{b.type === 'setup' ? <Bi hi="📢 सेटअप" en="Setup" inline /> : <Bi hi="↔️ अगले समूह की ओर" en="Move to the next group" inline />}</b>
      {b.duration_minutes ? <> · {b.duration_minutes} {MIN}</> : null}
      {b.script_hi && <div style={{ fontStyle: 'italic', ...ML }}>“{fmt(b.script_hi)}”</div>}
    </div>
  ));

  const anchorPanel = (slot) => {
    const narration = <p style={{ fontSize: '0.9375rem', margin: '4px 0 8px', ...ML }}>{fmt(anchor.narration_hi)}</p>;
    return (
      <div data-testid="anchor-card">
        <h3 style={{ marginBottom: 4 }}>🎯 <Bi hi="एंकर गतिविधि" en="Anchor activity" inline />
          {anchor.title_hi && <span data-testid="anchor-title" style={{ fontWeight: 400 }}>: «{anchor.title_hi}»{anchor.title_en && <span className="en en-inline" lang="en">'{anchor.title_en}'</span>}</span>}
        </h3>
        <div className="slot-meta"><Bi hi="पूरी कक्षा साथ में" en="Whole class together" inline /> · {slot.minutes || 10} {MIN}</div>
        {familiar ? <Fold icon="📖" hi="गतिविधि" en="The activity" testid="anchor-fold">{narration}</Fold> : narration}
        {anchor.opening_question_hi && (
          <div className="talking-point" style={ML}>
            <div className="talking-point-label"><Bi hi="शुरुआती सवाल" en="Opening question" inline /></div>
            {fmt(anchor.opening_question_hi)}
          </div>
        )}
        {GROUP_ORDER.some((level) => anchor[`${level}_participation_hi`]) && (
          <Fold icon="👥" hi="हर समूह कैसे भाग ले" en="How each group takes part" testid="anchor-groups">
            {GROUP_ORDER.map((level) => (anchor[`${level}_participation_hi`] ? (
              <div key={level} className={`group-line tier-${level}`} style={ML}>
                <strong><GroupMark group={level} name />:</strong> {stripGroup(anchor[`${level}_participation_hi`])}
              </div>
            ) : null))}
          </Fold>
        )}
        {afterLines(slot)}
      </div>
    );
  };

  const teachPanel = (slot) => {
    const block = slot.block;
    const level = slot.group;
    const L = GROUP_LABELS[level];
    const tp = block.talking_points || {};
    const skill = skillOf(level);
    return (
      <div>
        <h3 style={{ marginBottom: 2 }}>
          {slot.reteach ? '🔄 ' : '👩‍🏫 '}<GroupMark group={level} />{' '}
          {slot.reteach
            ? <Bi hi={`${L?.hi || level} के साथ पुनः शिक्षण`} en={`Re-teach the ${L?.en || level}s`} inline />
            : <Bi hi={`${L?.hi || level} को पढ़ाएँ`} en={`Teach the ${L?.en || level}s`} inline />}
          {skill && <span data-testid="block-skill" style={{ fontWeight: 400, fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-secondary)' }}> — {skill}</span>}
        </h3>
        <div className="slot-meta">{slot.start && <>{slot.start} · </>}{slot.minutes} {MIN} · {groupOf(level).count ?? '—'} <Bi hi="बच्चे" en="children" inline /></div>
        {recordButton(level)}
        {block.type === 'reteach' && block.affected_rolls && block.affected_rolls.length > 0 && (
          <div data-testid="reteach-rolls" style={{ fontSize: '0.75rem', marginTop: 4, ...ML }}>
            👥 <Bi hi="जिन बच्चों के लिए" en="For" inline />: <Bi hi="रोल" en="Roll" inline /> {block.affected_rolls.join(', ')}
          </div>
        )}
        <ReteachNote block={block} expanded />
        {block.script_hi && (familiar ? (
          <Fold icon="💬" hi="आज की गतिविधि" en="Today's activity" testid="script-fold">
            <div data-testid="block-script" style={{ fontSize: '0.8125rem', fontStyle: 'italic', ...ML }}>“{fmt(block.script_hi)}”</div>
          </Fold>
        ) : (
          <div data-testid="block-script" style={{ fontSize: '0.8125rem', fontStyle: 'italic', marginTop: 4, ...ML }}>“{fmt(block.script_hi)}”</div>
        ))}
        {/* what the children will do (the three core questions, or the writing prompt): visible without a tap, in every mode */}
        {block.type === 'teach' && <SignalPanel signal={block.signal} />}
        {/* a dictation sheet: the sentences are for the teacher only (the child's sheet has blank numbered lines; services/writing_sheets.py) */}
        {(() => {
          const ws = plan.worksheets?.[level];
          const ds = ws && ws.sheet_kind === 'dictation' && Array.isArray(ws.dictation_sentences) ? ws.dictation_sentences.filter(Boolean) : [];
          return ds.length > 0 ? (
            <Fold icon="🗣️" hi="बोलकर लिखवाएँ: वर्कशीट के वाक्य" en="Dictate: the worksheet's sentences" testid={`dictation-${level}`}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0 0 4px' }}>
                <Bi hi="हर वाक्य दो बार साफ़ बोलें; बच्चे उसी नंबर की लाइन पर लिखें। ये वाक्य बोर्ड पर न लिखें।" en="Read each sentence clearly twice; the children write it on the line with its number. Do not write these on the board." />
              </p>
              <ol style={{ paddingLeft: 20, margin: 0 }}>{ds.map((t, k) => <li key={k} data-testid="dictation-sentence">{fmt(t)}</li>)}</ol>
            </Fold>
          ) : null;
        })()}
        {tp.i_do_hi && <Fold icon="🧑‍🏫" hi="मैं करूँगा" en="I do" testid="fold-i-do"><div style={ML}>{fmt(tp.i_do_hi)}</div></Fold>}
        {tp.we_do_hi && <Fold icon="🤝" hi="हम करेंगे" en="We do" testid="fold-we-do"><div style={ML}>{fmt(tp.we_do_hi)}</div></Fold>}
        {tp.you_do_hi && (
          <Fold icon="✏️" hi="तुम करोगे" en="You do" testid="fold-you-do">
            <div style={ML}>{fmt(tp.you_do_hi)}</div>
            <BoardWork plan={plan} group={level} domain={currentPlan.domain_id} />
          </Fold>
        )}
        {Array.isArray(block.cfu) && block.cfu.length > 0 && (
          <Fold icon="✅" hi="समझ की जाँच" en="Check for understanding" testid="cfu">
            {/* the heading names the purpose (a check for understanding), not one technique; the text under "कैसे करें?" says how (today: the show-me). Sticks are named only in a maths plan. */}
            <details className="fold" data-testid="cfu-how" onClick={(e) => e.stopPropagation()} style={{ margin: '2px 0 4px' }}>
              <summary><span><Bi hi="कैसे करें?" en="How to do it" inline /></span></summary>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                <Bi hi={`हर बच्चा उत्तर स्लेट या कॉपी पर लिखकर, बनाकर या उँगलियों से तैयार करे और छिपाए। लगभग 20 सेकंड रुकें, फिर 'तीन, दो, एक — दिखाएँ!' कहें और सब एक साथ दिखाएँ। फिर दो बच्चों से समझाने को कहें: एक जिसने पहले गलती की थी (चुपचाप चुनें, नाम न बुलाएँ) और एक किसी भी बच्चे से, सिर्फ़ हाथ उठाने वालों से नहीं। अगर समूह के एक-चौथाई से ज़्यादा बच्चों के उत्तर गलत हों, तो आगे बढ़ने से पहले वही कदम अभी दोबारा समझाएँ${currentPlan.domain_id === 'numeracy' ? ' (छड़ियों से)' : ''}।`}
                  en={`Everyone prepares the answer on a slate or notebook page, written, drawn or on fingers, and hides it. Wait about 20 seconds, say 'three, two, one, show!' and everyone shows together. Then ask two children to explain: one who made the mistake before (chosen quietly, never named) and one at random, not only those with a hand up. If more than a quarter of the group is wrong, re-teach that step at once${currentPlan.domain_id === 'numeracy' ? ', with sticks,' : ''} before moving on.`} />
              </div>
            </details>
            {block.cfu.map((q, k) => (
              <div key={k} data-testid="cfu-item" style={{ marginTop: 6, paddingTop: 6, borderTop: k ? '1px dashed var(--border)' : 'none' }}>
                <div><strong>{k + 1}.</strong> {fmt(q.question_hi)}</div>
                <div style={{ fontSize: '0.8125rem' }}>✓ <Bi hi="सही उत्तर" en="Right answer" inline />: {fmt(q.expected_hi)}</div>
                {(q.listen_for || []).map((l, j) => (
                  <div key={j} style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    👂 <Bi hi="सुनें" en="Listen for" inline />: {fmt(l.wrong_answer_hi)} → <em>{fmt(l.misconception_name_hi)}</em>
                  </div>
                ))}
                {q.shows_hi && !(q.listen_for || []).length && (
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}><Bi hi="सही उत्तर से पता चलता है" en="A right answer shows" inline />: {fmt(q.shows_hi)}</div>
                )}
              </div>
            ))}
            {block.cfu_note_hi && (
              <div style={{ fontSize: '0.75rem', fontStyle: 'italic', marginTop: 6 }} data-testid="cfu-note">
                <Bi hi={fmt(block.cfu_note_hi)} en={block.cfu_note_en ? fmt(block.cfu_note_en) : ''} inline />
              </div>
            )}
          </Fold>
        )}
        {block.other_groups_hi && (
          <Fold icon="👥" hi="इस बीच बाकी समूह" en="Meanwhile, the other groups" testid="other-groups">
            <div style={{ fontSize: '0.8125rem', ...ML }}>{fmt(block.other_groups_hi)}</div>
          </Fold>
        )}
        {afterLines(slot)}
      </div>
    );
  };

  // "← पिछला" / "अगला →" at the foot of a slot: the next slot, with its tabs back in view (the teacher was at the foot of the last one)
  const goSlot = (k) => {
    setSlotIndex(k);
    const bar = typeof document !== 'undefined' && document.querySelector('[data-testid="slot-tabs"]');
    if (bar && bar.scrollIntoView) bar.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  const slotLabel = (slot) => (slot.kind === 'anchor'
    ? <>🎯 <Bi hi="एंकर" en="Anchor" inline /></>
    : <>{slot.reteach ? '🔄' : ''}<GroupMark group={slot.group} name /></>);

  return (
    <div className="screen">
      {currentPlan.served_from === 'sample' && (
        <div data-testid="sample-banner" className="note note-info">
          📄 <b><Bi hi="नमूना योजना" en="Sample plan" inline /></b>: <Bi hi="AI की सीमा पूरी होने से यह इसी कौशल की पहले से बनी योजना है। समूह और वर्कशीट आपकी कक्षा के हिसाब से जाँचे गए हैं।"
            en="The AI limit was reached, so this is a recorded plan for the same skill. The groups and worksheets are checked for your class." inline />
        </div>
      )}
      <div className="screen-header plan-title">
        <h1>📋 <Bi hi="आज की योजना" en="Today's plan" inline />
          {/* how long this plan is: the time the teacher chose, recorded on the plan (services/planMinutes.js) */}
          {length && (
            <span data-testid="time-chip" data-recorded={length.recorded ? 'true' : 'false'}
              style={{ marginLeft: 8, verticalAlign: 'middle', whiteSpace: 'nowrap', background: 'var(--green-bg)', color: 'var(--green-dark)', border: '1px solid var(--green-light)', borderRadius: 10, padding: '1px 8px', fontSize: '0.75rem', fontWeight: 600 }}>
              ⏱ {length.minutes} <Bi hi="मिनट" en="min" inline />
            </span>
          )}
        </h1>
        {/* one printed page for the whole plan (the worksheets, one per group, are printed from the table below) */}
        <button type="button" className="btn btn-secondary btn-small" data-testid="open-print" onClick={() => navigate('/plan/print')} style={{ order: 2 }}>🖨️ <Bi hi="प्रिंट" en="Print" inline /></button>
      </div>
      <div className="plan-subline" data-testid="plan-group-skills">
        {currentPlan.plan_date} · {currentPlan.selected_competency_id}
        {plan.coverage && plan.coverage.tier && plan.coverage.tier !== 'tested' && (
          <span title={plan.coverage.note || ''} className="chip-flag">
            {({ ai_written: <Bi hi="◐ AI-लिखित सामग्री" en="◐ AI-written content" inline />, experimental: <Bi hi="⚠ प्रयोगात्मक" en="⚠ Experimental" inline />, untested: <Bi hi="○ अभी परखा नहीं" en="○ Not yet tested" inline /> })[plan.coverage.tier]}
          </span>
        )}
      </div>

      {/* Today's groups: one row per group, its colour and mark, its children, its skill and its worksheet */}
      <table className="group-table" data-testid="group-table">
        <thead>
          <tr>
            <th><Bi hi="समूह" en="Group" inline /></th>
            <th style={{ textAlign: 'center' }}>👥</th>
            <th><Bi hi="आज का कौशल" en="Today's skill" inline /></th>
            <th style={{ textAlign: 'center' }}><Bi hi="वर्कशीट" en="Sheet" inline /></th>
          </tr>
        </thead>
        <tbody>
          {GROUP_ORDER.filter((level) => groups.some((g) => g.label === level)).map((level) => {
            const g = groupOf(level);
            const sheet = sheetOf(level);
            return (
              <tr key={level} className={`tier-${level}`} data-testid={`group-row-${level}`}>
                <td><GroupMark group={level} name />
                  {reteachSet.has(level) && <div className="reteach-tag" data-testid={`plan-reteach-${level}`}>🔄 <Bi hi="पुनः शिक्षण" en="Re-teach" inline /></div>}
                </td>
                <td style={{ textAlign: 'center', fontWeight: 700 }}>{g.count}</td>
                <td><span style={{ fontFamily: 'monospace', fontSize: '0.75rem' }} data-testid={`plan-skill-${level}`}>{g.target_competency_id}</span>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{g.target_competency_name_hi}</div></td>
                <td style={{ textAlign: 'center' }}>
                  {sheet ? (
                    <button type="button" className="btn btn-secondary btn-small sheet-btn" data-testid={`worksheet-${level}`}
                      onClick={() => navigate('/page', { state: { path: sheetUrl(level), title: { hi: `वर्कशीट: ${GROUP_LABELS[level].hi}`, en: `Worksheet: ${GROUP_LABELS[level].en}` }, back: '/yojana' } })}>
                      📝
                    </button>
                  ) : <span style={{ color: 'var(--text-light)', fontSize: '0.75rem' }} data-testid={`worksheet-none-${level}`}>—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="hint-line"><Bi hi="📝 वर्कशीट खोलें, प्रिंट करें या बोर्ड पर उतारें।" en="📝 opens the worksheet: print it, or copy it to the board." inline /></p>

      {/* Preparation before class (DIY TLMs etc.) */}
      {Array.isArray(plan.prep_hi) && plan.prep_hi.length > 0 && (
        <details className="card fold section-fold" data-testid="prep-fold">
          <summary><span>🧰 <Bi hi="कक्षा से पहले तैयारी" en="Before class" inline /> <span className="count-chip">{plan.prep_hi.length}</span></span></summary>
          <ul style={{ paddingLeft: 18, marginTop: 6, fontSize: '0.875rem' }}>
            {plan.prep_hi.map((t, i) => <li key={i} style={{ marginBottom: 4, ...ML }}>{fmt(t)}</li>)}
          </ul>
        </details>
      )}

      {/* Today's session: one tab per slot (the anchor, then each group's teaching), the strip above showing the whole session at a glance */}
      <h2 style={{ margin: '16px 0 6px' }}>⏱️ <Bi hi="आज का सत्र" en="Today's session" inline /></h2>
      {slots.length > 0 ? (<>
        <div className="session-strip" aria-hidden="true">
          {stripParts(blocks).map((p, k) => (
            <span key={k} className={`strip-part ${p.type === 'anchor' ? 'strip-anchor' : (p.type === 'teach' || p.type === 'reteach') ? `tier-${p.group}` : 'strip-gap'}`} style={{ flexGrow: p.share }} />
          ))}
        </div>
        <div className="slot-tabs" role="tablist" aria-label="सत्र / Session" data-testid="slot-tabs">
          {slots.map((s, k) => (
            <button key={s.key} type="button" role="tab" id={`slot-tab-${k}`} aria-selected={active === s} aria-controls={`slot-panel-${k}`}
              className={`slot-tab ${s.group ? `tier-${s.group}` : 'slot-anchor'} ${active === s ? 'on' : ''}`} data-testid={`slot-tab-${s.kind === 'anchor' ? 'anchor' : s.group}`}
              onClick={() => setSlotIndex(k)}>
              <span className="slot-tab-name">{slotLabel(s)}</span>
              <span className="slot-tab-time">{s.minutes ? `${s.minutes}′` : ''}</span>
            </button>
          ))}
        </div>
        {/* every slot's panel is in the page (find-in-page, the offline copy, the tests); only the chosen one shows */}
        {slots.map((s, k) => (
          <div key={s.key} className={`slot-panel ${s.group ? `tier-${s.group}` : 'slot-anchor'}${s.reteach ? ' reteach' : ''}`} role="tabpanel" id={`slot-panel-${k}`} aria-labelledby={`slot-tab-${k}`}
            hidden={active !== s} data-testid={active === s ? 'slot-panel' : 'slot-panel-hidden'} data-slot={s.kind} data-slot-group={s.group || 'anchor'}>
            {s.kind === 'anchor' ? anchorPanel(s) : teachPanel(s)}
            <div className="slot-nav">
              {k > 0 && (
                <button type="button" className="btn btn-secondary btn-small" data-testid="slot-prev" onClick={() => goSlot(k - 1)}><span>← <Bi hi="पिछला" en="Previous" inline /></span></button>
              )}
              <span style={{ flex: 1 }} />
              {k < slots.length - 1 ? (
                <button type="button" className="btn btn-secondary btn-small" data-testid="slot-next" onClick={() => goSlot(k + 1)}>
                  <span><Bi hi="अगला" en="Next" inline />: {slotLabel(slots[k + 1])} →</span>
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </>) : (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          <p><Bi hi="सत्र की योजना यहाँ दिखेगी।" en="The session will appear here once the plan is made." /></p>
        </div>
      )}

      {/* today's review, readable before class: how each group is checked, what to look for, the text to read aloud */}
      <details className="card fold section-fold" data-testid="review-today" style={{ marginTop: 16 }}>
        <summary><span>☑️ <Bi hi="आज की समीक्षा: कैसे जाँचें" en="Today's review: how to check" inline /></span></summary>
        {ways && ways.has_plan && (ways.levels || []).length > 0 ? (ways.levels || []).map((l) => {
          const way = channelOf(l.channel);
          return (
            <div key={l.level} data-testid={`review-way-${l.level}`} style={{ fontSize: '0.8125rem', padding: '4px 0', borderTop: '1px dashed var(--border)' }}>
              <b><GroupMark group={l.level} name /></b> <span style={{ fontFamily: 'monospace' }}>{l.competency_id}</span>: {way ? <>{way.icon} <Bi hi={way.hi} en={way.en} inline /></> : l.channel}
              {way && <div style={{ color: 'var(--text-secondary)' }}><Bi hi={way.who.hi} en={way.who.en} inline /></div>}
              {l.channel === 'observed' && hasWorksheet(currentPlan, l.level) && (
                <div data-testid={`review-way-practice-${l.level}`} style={{ color: 'var(--text-secondary)' }}>ℹ️ <Bi hi={PRACTICE_ONLY.hi} en={PRACTICE_ONLY.en} inline /></div>
              )}
              {l.passage && <div data-testid={`review-way-passage-${l.level}`}><Bi hi="पढ़ने का पाठ" en="Text to read" inline />: «{l.passage.title}» ({l.passage.word_count} <Bi hi="शब्द" en="words" inline />)</div>}
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

      {/* Why this plan? */}
      <details className="card fold section-fold" data-testid="why-fold" open={showWhyPanel} onToggle={(e) => setShowWhyPanel(e.currentTarget.open)}>
        <summary data-testid="why-toggle"><span>💡 <Bi hi="यह योजना क्यों?" en="Why this plan?" inline /></span></summary>
        {showWhyPanel && (
          <div style={{ marginTop: 8, fontSize: '0.8125rem' }}>
            {Array.isArray(explainability.items) ? explainability.items.map((item, i) => (
              <div key={i} style={{ marginBottom: 10 }}>
                <strong><Bi hi={fmt(item.title_hi)} en={fmt(item.title_en)} inline /></strong>
                <div style={ML} data-testid="why-body" className={item.body_en ? 'hi' : undefined}>{boldLabels(item.body_hi)}</div>
                {item.body_en && <div className="en" lang="en" style={{ fontSize: '0.75rem', ...ML }}>{boldLabels(item.body_en)}</div>}
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
      </details>

      {/* the next step after teaching, without having to know which tab it is */}
      <button type="button" className="btn btn-primary" data-testid="to-review" onClick={() => navigate('/review')} style={{ marginTop: 12, marginBottom: 80, flexDirection: 'column', gap: 0 }}>
        <Bi hi="पढ़ाने के बाद: समीक्षा करें →" en="After teaching: review" />
      </button>
    </div>
  );
}
