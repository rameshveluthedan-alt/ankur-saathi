import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getCompetencies, getGroups, generatePlan, getGroupProposal, getLadder } from '../services/api';
import GroupSkillsPanel from '../components/GroupSkillsPanel';
import GroupSkillsDrawer from '../components/GroupSkillsDrawer';
import { initialRows, buildGenerateOptions, summarize, panelStatus } from '../services/groupSkills';
import { TAB_RESELECT_EVENT } from '../services/tabs';
import { useOnline } from '../components/OfflineBanner';
import { GROUP_LABELS } from '../tiers';
import Bi from '../components/Bi';

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

  const today = new Date().toISOString().split('T')[0];

  const handleGenerate = async () => {
    if (loadingPanel) return;
    if (!selectedId) return;
    setGenerating(true);
    try {
      // with the panel shown, the teacher's choices go with the request; without it (the suggestions could not be loaded) the plan decides, as before
      const options = buildGenerateOptions({ rows, reteach, groups, ready: !!(rows && ladder) });
      const plan = await generatePlan(teacher.teacher_id, selectedId, selectedDomain, today, options);
      setCurrentPlan(plan);
      navigate('/yojana');
    } catch (e) {
      if (e.code === 'ai_cap') {        // the AI limit was reached: say why, and which skills still have a recorded sample plan
        const samples = (e.detail && e.detail.sample_skills) || [];
        alert(e.message + (samples.length ? `\n\nइन कौशलों की नमूना योजना उपलब्ध है (Sample plans are available for): ${samples.join(', ')}` : ''));
      } else {
        alert('योजना बनाने में समस्या (Plan generation error): ' + e.message);
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
        <h1>🎯 <Bi hi="योजना बनाएँ" en="Select Lakshya" inline /></h1>
        <div style={{ display: 'flex', gap: 6 }}>
          <button type="button" className="btn btn-secondary btn-small" onClick={() => navigate('/register')} data-testid="open-register">👥 कक्षा रजिस्टर</button>
          <button type="button" className="btn btn-secondary btn-small" onClick={() => navigate('/account')} data-testid="open-account" aria-label="प्रोफ़ाइल (Profile)">👤</button>
        </div>
      </div>

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

      {!loading && competencies.length > 0 && (
        <div className="card" style={{ padding: 12 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
            ज्ञान-आधार कवरेज (Knowledge-base coverage): हर कौशल के लिए योजना बनती है; लेबल बताता है कि उसके पीछे कितनी जाँची हुई सामग्री है।
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {TIER_ORDER.filter(t => tierCounts[t]).map(t => (
              <span key={t} style={{ background: TIERS[t].bg, color: TIERS[t].color, borderRadius: 10, padding: '2px 8px', fontSize: '0.7rem', fontWeight: 600 }}>
                {TIERS[t].icon} {TIERS[t].hi} ({TIERS[t].en}) · {tierCounts[t]}
              </span>
            ))}
          </div>
          <details style={{ marginTop: 6 }}>
            <summary style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>इन लेबलों का मतलब (What the labels mean)</summary>
            {TIER_ORDER.map(t => (
              <div key={t} style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                <b style={{ color: TIERS[t].color }}>{TIERS[t].icon} {TIERS[t].en}</b>: {TIERS[t].what}
              </div>
            ))}
          </details>
        </div>
      )}

      <div style={{ display: 'flex', gap: 4, marginBottom: 12, flexWrap: 'wrap' }}>
        <button style={{ minHeight: 40, minWidth: 48, padding: '4px 12px', fontSize: '0.8125rem', borderRadius: 6, border: '1px solid var(--border)', background: !gradeFilter ? 'var(--green-dark)' : 'var(--surface)', color: !gradeFilter ? 'white' : 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}
          onClick={() => setGradeFilter(null)}>सभी (All)</button>
        {GRADE_ORDER.map(g => (
          <button key={g} style={{ minHeight: 40, minWidth: 48, padding: '4px 12px', fontSize: '0.8125rem', borderRadius: 6, border: '1px solid var(--border)', background: gradeFilter === g ? 'var(--green-dark)' : 'var(--surface)', color: gradeFilter === g ? 'white' : 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}
            onClick={() => setGradeFilter(g)}>{GRADE_LABELS[g]}</button>
        ))}
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>लक्ष्य लोड हो रहे हैं (Loading competencies)...</span></div>
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
                    {c.name_hi && <span style={{display:'block',fontSize:'0.7rem',color:'var(--text-light)'}}>{c.name_en}</span>}
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
                ? 'लगभग 1–1.5 मिनट लगते हैं। कृपया इस पेज को खुला रखें। (Takes about 1–1.5 minutes. Please keep this page open.)'
                : 'थोड़ा और समय लग रहा है, कृपया प्रतीक्षा करें। (Taking a little longer. Please keep waiting.)'}
            </div>
          )}
          {!online && !generating && (
            <div data-testid="generate-offline" style={{ fontSize: '0.75rem', textAlign: 'center', background: '#E8EEF4', color: '#26405A', borderRadius: 8, padding: '6px 10px', marginBottom: 6 }}>
              योजना बनाने के लिए इंटरनेट चाहिए। (Making a plan needs the internet.)
            </div>
          )}
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating || loadingPanel || !online}
            style={generating ? { opacity: 1, cursor: 'wait' } : undefined}>
            {generating ? (
              <><div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} /> योजना बन रही है (Generating)... {fmtClock(elapsed)}</>
            ) : loadingPanel ? (
              <>समूहों के कौशल लोड हो रहे हैं… (Loading the groups)</>
            ) : (
              <>📋 दैनिक योजना बनाएँ<span className="en en-inline" lang="en">Generate Plan</span> → {selectedId}</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
