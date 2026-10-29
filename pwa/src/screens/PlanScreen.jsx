import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getCompetencies, getGroups, generatePlan, getGroupProposal, getLadder, getCachedPlan } from '../services/api';
import GroupSkillsPanel from '../components/GroupSkillsPanel';
import GroupSkillsDrawer from '../components/GroupSkillsDrawer';
import { initialRows, buildGenerateOptions, summarize, panelStatus } from '../services/groupSkills';
import { TAB_RESELECT_EVENT } from '../services/tabs';
import { useOnline } from '../components/OfflineBanner';
import { GROUP_LABELS } from '../tiers';
import Bi from '../components/Bi';
import { bi } from '../services/language';
import { notify } from '../services/notify';
import { friendlyError } from '../services/errors';
import { localToday } from '../services/today';
import SessionLength from '../components/SessionLength';
import { getSessionMinutes, setSessionMinutes } from '../services/preferences';
import ReplacePlanDialog from '../components/ReplacePlanDialog';
import SuggestedSkill from '../components/SuggestedSkill';
import { planMinutes, PRESETS } from '../services/planMinutes';

const GRADE_LABELS = { balvatika: 'BV', grade_1: 'G1', grade_2: 'G2', grade_3: 'G3' };
const GRADE_LABELS_HI = { balvatika: 'बालवाटिका', grade_1: 'कक्षा 1', grade_2: 'कक्षा 2', grade_3: 'कक्षा 3' };
const GRADE_ORDER = ['balvatika', 'grade_1', 'grade_2', 'grade_3'];
// Generating a plan takes about a minute (measured: 59-82 s). Tell the teacher, and reassure if it runs long.
const SLOW_AFTER_S = 100;

// How much of the knowledge base stands behind a skill (see docs/COVERAGE.md)
const TIERS = {
  tested:       { icon: '✔', hi: 'परखा हुआ', en: 'Tested', color: '#1B6B43', bg: '#E4F4EA',
                  what: 'Passed every automatic check with the real AI, using an exact anchor from the bank.' },
  ai_written:   { icon: '◐', hi: 'AI-लिखित सामग्री', en: 'AI-written content', color: '#8A5A00', bg: '#FFF1CC',
                  what: 'The plan works, but part of it (the opening activity or the passage) is adapted or written by the AI, so it is less validated.' },
  experimental: { icon: '⚠', hi: 'प्रयोगात्मक', en: 'Experimental', color: '#A12A1E', bg: '#FCE4E1',
                  what: 'It failed in testing or the checks still flag problems. Expect to edit it.' },
  untested:     { icon: '○', hi: 'अभी परखा नहीं', en: 'Not yet tested', color: '#555', bg: '#EDEDED',
                  what: 'Not yet run through the real AI.' },
};
const TIER_ORDER = ['tested', 'ai_written', 'experimental', 'untested'];
const fmtClock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

const PLAN_FAILED = { hi: 'योजना नहीं बन सकी', en: 'The plan could not be made' };

const GROUP_SHORT = { beginner: 'शु', progressor: 'प्र', proficient: 'द' };

export default function PlanScreen() {
  const { teacher, selectedDomain, setSelectedDomain, setCurrentPlan } = useAuth();
  const navigate = useNavigate();
  const [competencies, setCompetencies] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const online = useOnline();            // Generate needs the internet: it is off, with a reason, when there is none
  const [elapsed, setElapsed] = useState(0);
  const [gradeFilter, setGradeFilter] = useState(null);
  const [sessionMinutes, setSessionMinutesState] = useState(getSessionMinutes);      // today's time: the last choice on this device, 90 on first use
  const chooseMinutes = (m) => { setSessionMinutes(m); setSessionMinutesState(m); };
  // each group's skill for today, and the re-teach choice (see services/groupSkills.js)
  const [proposal, setProposal] = useState(null);
  const [ladder, setLadder] = useState(null);
  const [rows, setRows] = useState(null);
  const [reteach, setReteach] = useState({});
  const [drawerOpen, setDrawerOpen] = useState(false);          // the group panel is a drawer in the bottom bar: it opens in place, the page never scrolls
  const [panelFailed, setPanelFailed] = useState(false);
  const loadingPanel = panelStatus({ selectedId, rows, failed: panelFailed }) === 'loading';      // a skill was just chosen: its groups are still coming
  const pendingReteach = useRef([]);       // groups to tick once the skill the teacher just chose has loaded ("re-teach instead?")
  const selectSkill = (id, opts) => { pendingReteach.current = (opts && opts.reteach) || []; setSelectedId(id); };
  // today's plan in this subject, if one is already made: { status: 'checking' | 'none' | 'exists' | 'unknown', plan }. While it exists the screen is LOCKED (a status card,
  // no picker): making a new plan replaces it, so the teacher is asked first, and "हाँ, बदलें" only unlocks the picker (nothing is generated until she taps Generate).
  const [existing, setExisting] = useState({ status: 'checking', plan: null });
  const [unlocked, setUnlocked] = useState(false);
  const [dialog, setDialog] = useState(null);           // null | 'plan' | 'unknown'
  const [unlockHint, setUnlockHint] = useState(false);
  const [unknownOk, setUnknownOk] = useState(false);     // the check failed and the teacher chose to generate anyway
  const locked = existing.status === 'exists' && !unlocked;

  useEffect(() => {
    setLoading(true);
    setSelectedId(null);
    Promise.all([
      getCompetencies(selectedDomain),
      getGroups(teacher.teacher_id, selectedDomain),
    ]).then(([compData, groupData]) => {
      setCompetencies(compData.competencies || []);
      setGroups(groupData.groups || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [selectedDomain, teacher.teacher_id]);

  // is there already a plan for today in this subject? (a 404 means none; any other failure means we cannot tell, so Generate asks first)
  useEffect(() => {
    let cancelled = false;
    setExisting({ status: 'checking', plan: null }); setUnlocked(false); setDialog(null); setUnlockHint(false); setUnknownOk(false);
    getCachedPlan(teacher.teacher_id, localToday(), selectedDomain)
      .then((plan) => { if (!cancelled) setExisting({ status: 'exists', plan }); })
      .catch((e) => { if (!cancelled) setExisting({ status: e && e.status === 404 ? 'none' : 'unknown', plan: null }); });
    return () => { cancelled = true; };
  }, [selectedDomain, teacher.teacher_id]);

  // "हाँ, बदलें": unlock, with the plan's skill (and its length, when it is one of the three) already chosen, so Generate unchanged makes the same skill again
  const unlock = () => {
    setDialog(null); setUnlocked(true); setUnlockHint(true); setGradeFilter(null);
    const m = planMinutes(existing.plan);
    if (m && PRESETS.includes(m.minutes)) setSessionMinutesState(m.minutes);        // shown, not saved as the phone's choice
    if (existing.plan && existing.plan.selected_competency_id) selectSkill(existing.plan.selected_competency_id);
  };
  // "योजना खोलें →": put THIS plan in place first (the app may hold another subject's), then go to it
  const openPlan = () => { setCurrentPlan(existing.plan); navigate('/yojana'); };

  // what the teacher decided at the last review: it fills in the suggestions (if it cannot be fetched, the panel simply has none)
  useEffect(() => {
    setProposal(null);
    getGroupProposal(teacher.teacher_id, selectedDomain, today).then(setProposal).catch(() => setProposal(null));
  }, [selectedDomain, teacher.teacher_id]);

  // the skills the plan derives for the groups when this skill is selected: the panel starts from them
  useEffect(() => {
    if (!selectedId) { setLadder(null); setRows(null); setReteach({}); setPanelFailed(false); return undefined; }
    // clear the PREVIOUS skill's groups at once: until the new ones arrive nothing is shown or used (before, the bar showed them, and Generate could combine the new skill with the old groups)
    setLadder(null); setRows(null); setReteach({}); setPanelFailed(false);
    let cancelled = false;
    getLadder(selectedId).then((l) => {
      if (cancelled) return;
      const init = initialRows({ ladder: l, proposal, selectedId });
      pendingReteach.current.forEach((g) => { if (init.rows[g] && init.rows[g].previous) init.reteach[g] = true; });
      pendingReteach.current = [];
      setLadder(l); setRows(init.rows); setReteach(init.reteach);
    }).catch(() => { if (!cancelled) { setLadder(null); setRows(null); setReteach({}); setPanelFailed(true); } });
    return () => { cancelled = true; };
  }, [selectedId, proposal]);

  // tapping the Plan tab again (we are already on this screen) goes back to choosing a skill: the drawer closes and the choice is cleared. Never while a plan is being generated.
  useEffect(() => {
    const onReselect = (e) => { if (e.detail === '/' && !generating) { setDrawerOpen(false); setSelectedId(null); } };
    window.addEventListener(TAB_RESELECT_EVENT, onReselect);
    return () => window.removeEventListener(TAB_RESELECT_EVENT, onReselect);
  }, [generating]);

  // running timer while a plan is being generated (counts from the real clock, so a throttled tab stays accurate)
  useEffect(() => {
    if (!generating) { setElapsed(0); return undefined; }
    const start = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [generating]);

  const today = localToday();

  const handleGenerate = async (confirmed) => {         // confirmed === true: the teacher answered the "could not check" question with yes
    if (loadingPanel) return;
    if (!selectedId) return;
    if (locked) { setDialog('plan'); return; }
    if (existing.status === 'unknown' && !unknownOk && confirmed !== true) { setDialog('unknown'); return; }       // we could not tell whether a plan exists: never replace one silently
    setGenerating(true);
    try {
      // with the panel shown, the teacher's choices go with the request; without it (the suggestions could not be loaded) the plan decides, as before
      const options = buildGenerateOptions({ rows, reteach, groups, ready: !!(rows && ladder) });
      // replace: only when the teacher said so ("हाँ, बदलें", or "हाँ, बनाएँ" when the check failed); without it the server never replaces an existing plan
      const replace = (existing.status === 'exists' && unlocked) || (existing.status === 'unknown' && (unknownOk || confirmed === true));
      const plan = await generatePlan(teacher.teacher_id, selectedId, selectedDomain, today, { ...options, sessionMinutes, ...(replace ? { replace: true } : {}) });      // the plan is laid out for today's time
      setCurrentPlan(plan);
      setUnlockHint(false);
      navigate('/yojana');
    } catch (e) {
      if (e.code === 'plan_exists') {    // a plan appeared since this screen opened (another phone, another tab): show it and ask, never a raw error
        try {
          const found = await getCachedPlan(teacher.teacher_id, today, selectedDomain);
          setExisting({ status: 'exists', plan: found }); setUnlocked(false); setUnlockHint(false); setDrawerOpen(false); setDialog('plan');
        } catch (e2) { notify(friendlyError(e2, PLAN_FAILED), 'error'); }
      } else if (e.code === 'ai_cap') {        // the AI limit was reached: say why, and which skills still have a recorded sample plan
        const samples = (e.detail && e.detail.sample_skills) || [];
        notify(e.message + (samples.length ? `\n\n${bi('इन कौशलों की नमूना योजना उपलब्ध है', 'Sample plans are available for')}: ${samples.join(', ')}` : ''), 'error');
      } else {
        notify(friendlyError(e, PLAN_FAILED), 'error');
      }
    }
    setGenerating(false);
  };

  const tierCounts = {};
  competencies.forEach(c => { const t = c.coverage_tier || 'untested'; tierCounts[t] = (tierCounts[t] || 0) + 1; });
  const selectedSkill = competencies.find(c => c.id === selectedId);
  const selectedTier = selectedSkill ? (selectedSkill.coverage_tier || 'untested') : null;

  const filtered = gradeFilter ? competencies.filter(c => c.grade_level === gradeFilter) : competencies;
  const grouped = {};
  filtered.forEach(c => { if (!grouped[c.grade_level]) grouped[c.grade_level] = []; grouped[c.grade_level].push(c); });

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>🎯 <Bi hi="योजना बनाएँ" en="Make plan" inline /></h1>
        {/* Profile is the 👤 tab in the bottom bar, so there is no second Profile button here */}
        <button type="button" className="btn btn-secondary btn-small" onClick={() => navigate('/register')} data-testid="open-register">👥 कक्षा रजिस्टर</button>
      </div>

      {/* after "हाँ, बदलें": the screen is unlocked; nothing has been replaced yet */}
      {unlockHint && (
        <div data-testid="unlock-hint" style={{ display: 'flex', alignItems: 'flex-start', gap: 8, background: 'var(--green-bg)', borderRadius: 8, padding: '6px 10px', marginBottom: 10, fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
          <span style={{ flex: 1 }}><Bi hi="✓ अब आप बदलाव कर सकते हैं। नई योजना बनाने के लिए '📋 आज की योजना बनाएँ' दबाएँ।" en="You can now make changes. Press 'Make today's plan' to make the new plan." /></span>
          <button type="button" data-testid="unlock-hint-close" aria-label="बंद करें" onClick={() => setUnlockHint(false)}
            style={{ background: 'none', border: 'none', fontSize: '1rem', minWidth: 44, minHeight: 44, margin: '-10px -8px', cursor: 'pointer', color: 'inherit' }}>✕</button>
        </div>
      )}

      {!teacher.total_children && (
        <div className="card" style={{ borderLeft: '4px solid #C9A227', background: '#FFF8E1' }} data-testid="empty-class">
          <h3 style={{ marginBottom: 4 }}>आपकी कक्षा में अभी कोई बच्चा नहीं है</h3>
          <p style={{ fontSize: '0.8125rem', marginBottom: 8 }}>
            पहले अपनी कक्षा का रजिस्टर अपलोड करें, फिर आपके समूहों के लिए योजनाएँ बन सकेंगी।
            <span className="en" lang="en">No children in your class yet. Upload your class register first, then plans can be made for your groups.</span>
          </p>
          <button type="button" className="btn btn-primary" onClick={() => navigate('/register')} style={{ flexDirection: 'column', gap: 0 }}><Bi hi="कक्षा रजिस्टर अपलोड करें" en="Upload class register" /></button>
        </div>
      )}

      <div className="domain-tabs">
        <button className={`domain-tab ${selectedDomain === 'numeracy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('numeracy')}><Bi hi="गणित" en="Numeracy" inline /></button>
        <button className={`domain-tab ${selectedDomain === 'r1_literacy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('r1_literacy')}><Bi hi="हिंदी" en="Literacy" inline /></button>
      </div>

      {groups.length > 0 && (
        <div className="card" style={{ padding: 12 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}><Bi hi="वर्तमान समूह" en="Current Groups" inline /></div>
          <div style={{ display: 'flex', gap: 8 }}>
            {groups.map(g => (
              <div key={g.label} style={{ flex: 1, textAlign: 'center' }}>
                <span className={`badge badge-${g.label}`}>{GROUP_LABELS[g.label]?.hi}</span>
                <div className="en" lang="en">{GROUP_LABELS[g.label]?.en}</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: 4 }}>{g.count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {existing.status === 'checking' && (
        <div className="loading" data-testid="plan-checking"><div className="spinner" /><span><Bi hi="आज की योजना देखी जा रही है…" en="Checking for today's plan" inline /></span></div>
      )}

      {/* today's plan is already made: a status card instead of the picker (the plan itself is on आज की योजना) */}
      {locked && (() => {
        const p = existing.plan || {};
        const skill = competencies.find((c) => c.id === p.selected_competency_id);
        const m = planMinutes(p);
        return (
          <div className="card" data-testid="plan-status" style={{ padding: 12 }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              <Bi hi="विषय" en="Subject" inline />: {selectedDomain === 'numeracy' ? <Bi hi="गणित" en="Maths" inline /> : <Bi hi="हिंदी" en="Literacy" inline />}
            </div>
            <div data-testid="locked-skill" data-locked="true" aria-disabled="true" style={{ marginTop: 6, fontSize: '0.9375rem' }}>
              <Bi hi="कौशल" en="Skill" inline />: <b style={{ fontFamily: 'monospace' }}>{p.selected_competency_id}</b> <span aria-label="locked">🔒</span>
              {skill && skill.name_hi && <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{skill.name_hi}</div>}
            </div>
            {m && (
              <div data-testid="locked-time" data-locked="true" aria-disabled="true" style={{ marginTop: 4, fontSize: '0.9375rem' }}>
                <Bi hi="समय" en="Time" inline />: <b>{m.minutes} मिनट</b> <span aria-label="locked">🔒</span>
              </div>
            )}
            <div style={{ borderTop: '1px solid var(--border)', marginTop: 10, paddingTop: 10 }}>
              <div data-testid="plan-ready" style={{ fontWeight: 600, color: 'var(--green-dark)' }}><Bi hi="✓ आज की योजना बन चुकी है" en="Today's plan is ready" /></div>
              <button type="button" className="btn btn-primary" data-testid="open-plan" onClick={openPlan} style={{ marginTop: 8, flexDirection: 'column', gap: 0 }}>
                <Bi hi="योजना खोलें →" en="Open the plan" />
              </button>
            </div>
            <div style={{ borderTop: '1px solid var(--border)', marginTop: 10, paddingTop: 10 }}>
              <button type="button" className="btn btn-secondary" data-testid="replace-plan" onClick={() => setDialog('plan')} style={{ flexDirection: 'column', gap: 0 }}>
                <Bi hi="🪄 नई योजना बनाएँ" en="Make a new plan" />
              </button>
            </div>
          </div>
        );
      })()}

      {/* unlocked: the plan that a new one would replace is still there until Generate */}
      {existing.status === 'exists' && unlocked && (
        <div data-testid="plan-current" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 10 }}>
          <span style={{ flex: 1 }}><Bi hi={`अभी की योजना: ${existing.plan.selected_competency_id} — नई योजना बनाने पर यह बदल जाएगी`} en="Today's current plan: a new one will replace it" /></span>
          <button type="button" className="btn btn-secondary btn-small" data-testid="open-plan" onClick={openPlan}><Bi hi="योजना खोलें →" en="Open the plan" inline /></button>
        </div>
      )}
      {existing.status === 'unknown' && (
        <div data-testid="plan-check-failed" style={{ fontSize: '0.8125rem', color: '#8A5A00', background: '#FFF8E1', borderRadius: 8, padding: '6px 10px', marginBottom: 10 }}>
          <Bi hi="आज की योजना की जाँच नहीं हो सकी" en="Could not check for today's plan" />
        </div>
      )}

      {existing.status !== 'checking' && !locked && (<>
      {!loading && competencies.length > 0 && (
        // one line with the counts; the explanation and the labels' meaning open on tap (the skill list starts higher up)
        <details className="card fold" style={{ padding: '4px 12px' }} data-testid="coverage-card">
          <summary style={{ fontWeight: 400, color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
            <span style={{ fontWeight: 600 }}>ज्ञान-आधार कवरेज<span className="en en-inline" lang="en">Knowledge-base coverage</span>:</span>
            <span style={{ marginLeft: 4 }}>{TIER_ORDER.filter(t => tierCounts[t]).map(t => <span key={t} title={TIERS[t].hi} style={{ color: TIERS[t].color, fontWeight: 600, marginRight: 8 }}>{TIERS[t].icon} {tierCounts[t]}</span>)}</span>
          </summary>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '2px 0 6px' }}>
            हर कौशल के लिए योजना बनती है; लेबल बताता है कि उसके पीछे कितनी जाँची-परखी सामग्री है।
            <span className="en" lang="en">Every skill gets a plan; the label says how much checked material stands behind it.</span>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {TIER_ORDER.filter(t => tierCounts[t]).map(t => (
              <span key={t} style={{ background: TIERS[t].bg, color: TIERS[t].color, borderRadius: 10, padding: '2px 8px', fontSize: '0.7rem', fontWeight: 600 }}>
                {TIERS[t].icon} {TIERS[t].hi}<span className="en en-inline" lang="en" style={{ color: 'inherit', fontWeight: 400 }}>{TIERS[t].en}</span> · {tierCounts[t]}
              </span>
            ))}
          </div>
          <details style={{ marginTop: 6 }}>
            <summary style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', cursor: 'pointer', minHeight: 32 }}><Bi hi="इन लेबलों का मतलब" en="What the labels mean" inline /></summary>
            {TIER_ORDER.map(t => (
              <div key={t} style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                <b style={{ color: TIERS[t].color }}>{TIERS[t].icon} {TIERS[t].hi}<span className="en en-inline" lang="en" style={{ color: 'inherit' }}>{TIERS[t].en}</span></b>: <span lang="en">{TIERS[t].what}</span>
              </div>
            ))}
          </details>
        </details>
      )}

      {/* how long the teacher has today: just above the skill list, so it is set before a skill is chosen */}
      <SessionLength value={sessionMinutes} onChange={chooseMinutes} disabled={generating} />

      {/* the Progressors' skill the last review points to: one tap, instead of searching the list */}
      {!loading && <SuggestedSkill proposal={proposal} competencies={competencies} selectedId={selectedId}
        onChoose={(id) => { setDrawerOpen(false); setGradeFilter(null); selectSkill(id); }} />}

      <div style={{ display: 'flex', gap: 4, marginBottom: 12, flexWrap: 'wrap' }}>
        <button style={{ minHeight: 40, minWidth: 48, padding: '4px 12px', fontSize: '0.8125rem', borderRadius: 6, border: '1px solid var(--border)', background: !gradeFilter ? 'var(--green-dark)' : 'var(--surface)', color: !gradeFilter ? 'white' : 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}
          onClick={() => setGradeFilter(null)}><Bi hi="सभी" en="All" inline /></button>
        {GRADE_ORDER.map(g => (
          <button key={g} style={{ minHeight: 40, minWidth: 48, padding: '4px 12px', fontSize: '0.8125rem', borderRadius: 6, border: '1px solid var(--border)', background: gradeFilter === g ? 'var(--green-dark)' : 'var(--surface)', color: gradeFilter === g ? 'white' : 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}
            onClick={() => setGradeFilter(g)}>{GRADE_LABELS[g]}</button>
        ))}
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span><Bi hi="लक्ष्य लोड हो रहे हैं..." en="Loading competencies" inline /></span></div>
      ) : (
        <div>
          {GRADE_ORDER.filter(g => grouped[g]).map(grade => (
            <div key={grade}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', padding: '8px 0 4px' }}>
                {GRADE_LABELS[grade]} — {GRADE_LABELS_HI[grade]}
              </div>
              {grouped[grade].map(c => (
                <div key={c.id} className={`competency-item ${selectedId === c.id ? 'recommended' : ''}`}
                  onClick={() => { setDrawerOpen(false); setSelectedId(c.id); }}>
                  <span className="competency-id">{c.id}</span>
                  <span className="competency-name">
                    {c.name_hi || c.name_en}
                    {c.name_hi && <span className="en" lang="en">{c.name_en}</span>}
                    {(() => { const T = TIERS[c.coverage_tier || 'untested']; return (
                      <span title={c.coverage_note || T.what} style={{ display: 'inline-block', marginTop: 3, background: T.bg, color: T.color, borderRadius: 8, padding: '1px 7px', fontSize: '0.62rem', fontWeight: 600 }}>
                        {T.icon} {T.hi}
                      </span>); })()}
                  </span>
                  <span className="grade-tag">
                    {c.assessment_modality === 'observed' ? '✓' : c.assessment_modality === 'oral_reading' ? '⏱️' : '📝'}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* room for the fixed Generate bar, so it never covers the last skills in the list */}
      {selectedId && <div style={{ height: 160 }} aria-hidden="true" />}
      {selectedId && (
        <div style={{ position: 'fixed', bottom: 'calc(var(--nav-height) + var(--safe-bottom) + 8px)', left: 16, right: 16, maxWidth: 448, margin: '0 auto',
                      background: 'var(--bg)', borderRadius: 12, padding: 6, boxShadow: '0 -2px 10px rgba(0,0,0,0.08)' }}>
          {!generating && !drawerOpen && selectedTier && selectedTier !== 'tested' && (
            <div style={{ fontSize: '0.7rem', textAlign: 'center', background: TIERS[selectedTier].bg, color: TIERS[selectedTier].color, borderRadius: 8, padding: '4px 8px', marginBottom: 6 }}>
              {TIERS[selectedTier].icon} {TIERS[selectedTier].hi}: {selectedSkill.coverage_note || TIERS[selectedTier].what}
            </div>
          )}
          {!generating && rows && ladder && groups.length > 0 && (
            <GroupSkillsDrawer open={drawerOpen} onToggle={() => setDrawerOpen((o) => !o)}
              summary={summarize(rows, reteach).map((s) => `${GROUP_SHORT[s.label]} ${s.skillId}${s.reteach ? '🔄' : ''}`).join(' · ')}>
              <GroupSkillsPanel
                groups={groups} competencies={competencies} ladder={ladder} selectedId={selectedId}
                rows={rows} setRows={setRows} reteach={reteach} setReteach={setReteach}
                onSelectSkill={selectSkill} hasHistory={!!(proposal && proposal.has_history)} previousDate={proposal && proposal.previous_date} disabled={generating}
              />
            </GroupSkillsDrawer>
          )}
          {generating && (
            <div style={{ fontSize: '0.75rem', textAlign: 'center', background: 'var(--green-bg)', borderRadius: 8, padding: '6px 10px', marginBottom: 6, color: 'var(--text-secondary)' }}>
              {elapsed < SLOW_AFTER_S
                ? <Bi hi="लगभग 1–1.5 मिनट लगते हैं। कृपया इस पेज को खुला रखें।" en="Takes about 1–1.5 minutes. Please keep this page open." />
                : <Bi hi="थोड़ा और समय लग रहा है, कृपया प्रतीक्षा करें।" en="Taking a little longer. Please keep waiting." />}
            </div>
          )}
          {!online && !generating && (
            <div data-testid="generate-offline" style={{ fontSize: '0.75rem', textAlign: 'center', background: '#E8EEF4', color: '#26405A', borderRadius: 8, padding: '6px 10px', marginBottom: 6 }}>
              <Bi hi="योजना बनाने के लिए इंटरनेट चाहिए।" en="Making a plan needs the internet." />
            </div>
          )}
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating || loadingPanel || !online}
            style={generating ? { opacity: 1, cursor: 'wait' } : undefined}>
            {generating ? (
              <><div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} /> योजना बन रही है...<span className="en en-inline" lang="en">Generating</span> {fmtClock(elapsed)}</>
            ) : loadingPanel ? (
              <>समूहों के कौशल लोड हो रहे हैं…<span className="en en-inline" lang="en">Loading the groups</span></>
            ) : (
              <>📋 आज की योजना बनाएँ<span className="en en-inline" lang="en">Make today's plan</span> → {selectedId}</>
            )}
          </button>
        </div>
      )}
      </>)}

      {dialog && (
        <ReplacePlanDialog kind={dialog} evidence={existing.plan}
          onKeep={() => setDialog(null)}
          onReplace={() => { if (dialog === 'unknown') { setDialog(null); setUnknownOk(true); handleGenerate(true); } else unlock(); }} />
      )}
    </div>
  );
}
